import requests
import hmac
import hashlib
import base64
import datetime
from datetime import timezone
import regex
from .models import Agency
from decouple import config as ENVCONFIG

prod_endpoint = ENVCONFIG("PROD_ENDPOINT")


# JSON template for vehicle license plate query on prod
new_dict = {
    "API_REQUEST": {
        "HEADER": {
            "FUNCTION": "SEND_RECV",
            "LOCATION_IDENTIFIER": "",
            "TIMESTAMP": "",
            "SIGNATURE": "",
            "IDENTIFIER": "",
            "RECV_WAIT": "5",
            "RECV_COUNT": "10",
        },
        "DATA": {
            "HEADER": {
                "SUMMARY": "VEHICLE QUERY",
                "CATEGORY": "VEHICLES",
                "FUNCTION": "QUERY",
                "DEVICE": "",
                "ORI": "",
                "REFERENCE": "",
                "USERID": "",
                "USERCODE": "",
            },
            "PARAMETERS": {
                "VEHICLE_LIC_NUMBER": "",
                "VEHICLE_REGISTRATION_STATE": "",
                "VEHICLE_QUERY_DATA_1": "",
                "VEHICLE_IMAGE_REQ": "",
            },
        },
    }
}


def ComputeBase64Signature(
    LOCATION_KEY, REQUEST_TIMESTAMP, REQUEST_FUNCTION, REQUEST_IDENTIFIER
):
    secret_key = bytes("OMNIXXEdgeAPI" + LOCATION_KEY, "ascii")
    HashedToken1 = hmac.new(
        secret_key, bytes(REQUEST_TIMESTAMP, "ascii"), hashlib.sha256
    ).digest()
    HashedToken2 = hmac.new(
        HashedToken1, bytes(REQUEST_FUNCTION, "ascii"), hashlib.sha256
    ).digest()
    HashedToken3 = hmac.new(
        HashedToken2, bytes(REQUEST_IDENTIFIER, "ascii"), hashlib.sha256
    ).digest()
    return base64.b64encode(HashedToken3).decode()


def get_response(license_plate, state_plate, loc, api_key, device_id, ori):
    dt = datetime.datetime.now(timezone.utc)
    utc_timestamp = dt.replace(tzinfo=timezone.utc).strftime("%Y%m%d%H%M%S")
    new_dict["API_REQUEST"]["HEADER"]["SIGNATURE"] = ComputeBase64Signature(
        api_key, utc_timestamp, "SEND_RECV", loc
    )  # SIGNATURE
    new_dict["API_REQUEST"]["HEADER"]["LOCATION_IDENTIFIER"] = loc
    new_dict["API_REQUEST"]["HEADER"]["TIMESTAMP"] = utc_timestamp
    new_dict["API_REQUEST"]["HEADER"]["IDENTIFIER"] = "REF1234567"
    new_dict["API_REQUEST"]["DATA"]["HEADER"]["DEVICE"] = device_id
    new_dict["API_REQUEST"]["DATA"]["HEADER"]["ORI"] = ori
    new_dict["API_REQUEST"]["DATA"]["HEADER"]["REFERENCE"] = "VEHLIC00001"
    new_dict["API_REQUEST"]["DATA"]["HEADER"]["USERID"] = "TESTER"
    new_dict["API_REQUEST"]["DATA"]["HEADER"]["USERCODE"] = "123456789"
    new_dict["API_REQUEST"]["DATA"]["PARAMETERS"]["VEHICLE_LIC_NUMBER"] = license_plate
    new_dict["API_REQUEST"]["DATA"]["PARAMETERS"][
        "VEHICLE_REGISTRATION_STATE"
    ] = state_plate
    new_dict["API_REQUEST"]["DATA"]["PARAMETERS"]["VEHICLE_QUERY_DATA_1"] = "DMXTEXT"
    new_dict["API_REQUEST"]["DATA"]["PARAMETERS"]["VEHICLE_IMAGE_REQ"] = "N"
    r = requests.post(
        prod_endpoint, json=new_dict, headers={"Content-Type": "application/json"}
    )
    return r.json()


def getTextContent(plate, state_ab, station_name):
    """
    Reterns a text response to a DMV DataMax query

    PARAMETERS:
    plate (str): Upper or Lower case of license plate
    state_abb (str): UPPERCASE ONLY 2 letter abb of the state
    """
    info = Agency.objects.filter(station__name=station_name).values()[0]
    resp = get_response(
        plate,
        state_ab,
        info["location"],
        info["api_key"],
        info["device_id"],
        info["ORI"],
    )
    # dl = resp["API_RESPONSE"]["DATA"]["MESSAGE"]
    if "API_RESPONSE" in resp and resp["API_RESPONSE"] is not None:
        api_response = resp["API_RESPONSE"]

        if "DATA" in api_response and api_response["DATA"] is not None:
            data = api_response["DATA"]

            if "MESSAGE" in data and data["MESSAGE"] is not None:
                dl = data["MESSAGE"]
            else:
                return None
        else:
            return None
    else:
        return None

    is_first = True
    data = None
    for i in dl:
        nl = {"source": i["HEADER"]["SOURCE"], "data": i["DATA"]["TXT"]}
        if is_first and (nl["source"] == "DMV" or nl["source"] == "NLETS"):
            data = nl["data"]
            is_first = False
    print(f"{station_name}: {info['location']}")
    return data


def parse_query(QueryResponse, state):
    LA_regex = r"(?P<CODE1>\w*\d*)\\r\\nCTL\/(?P<CTL>\w*\d*)\\r\\nATN\/(?P<ATN>\w*\d*)(\\r\\n)*(?P<CODE2>[^\\r\\n]*)(\\r\\n)*VYR\/(?P<VYR>\d*)\s*VMA\/(?P<VMA>\w*)\s*VMO\/(?P<VMO>\w*)\s*VST\/(?P<VST>\w*)\s*VCO\/(?P<VCO>\w*)\s*(\\r\\n)*VIN\/\s*(?P<VIN>\w*\d*)\s*LIC\/\s*(?P<LIC>\w*\d*)\s*EXP\/(?P<EXP>\d*)(\\r\\n)*(?P<OWNER>.*?(?=OLN)|([^\\r\\n]*))(\\r\\n)*(OLN\/\s*(?P<OLN>\d*))?(\\r\\n)*(?P<STREET>[^\\r\\n]*)\n*(\\r\\n)*(?P<CITY>.*?(?=\s{2}))\s+(?P<STATE>\w*)\s*(?P<ZIP>\d+)(\\r\\n)*\s*.*?(?=\\r\\n)(\\r\\n)*FLAGS\s*(?P<FLAGS>.*?(?=\s{2}))\s*S?N?\s*TITLE\s*(?P<TITLE>\w*\d*)\s*(\\r\\n)*\s*(\\r\\n)*TRACKING:\s*(?P<TRACKING_DATE>[^\,]*),\s*(?P<TRACKING_TIME>[^\\r\\n]*)(\\r\\n)*-\sMKE:\s(?P<MKE>[^\\r\\n]*)(\\r\\n)*-\sSource:\s(?P<SOURCE>[^\\r\\n]*)(\\r\\n)*-\sTo:\s(?P<TO>[^\\r\\n]*)(\\r\\n)*-\sREF:\s(?P<REF>\w*\d*)(\\r\\n)-\sISN:\s(?P<ISN>[^\\r\\n]*)"
    TX_regex = r"ODOMETER[^\\r\\n]*(\\r\\n)*(?P<VYR>\w*\d*)\s*(?P<VMA>\w*\d*)\s*\w*\s*(?P<VIN>\w*\d*).*?(?=COLOR:)COLOR:\s*(?P<VCO>\w*).*?(?=\\r\\nOWNER)\\r\\nOWNER\s*(?P<OWNER>.*?(?=,)).*?(?=\\r\\n)(\\r\\n)*\s*(?P<STREET>[^,]*),*(?P<CITY>\w*),(?P<STATE>\w*)\s*(?P<ZIP>\d+)"
    AR_regex = r"VIN:\s*(?P<VIN>\w*)\s*COLOR:\s*(?P<VCO>\w*)\s*YEAR:\s*(?P<VYR>\d*)(?:\\r\\n)*\s*MAKE:\s*(?P<VMA>\w*)\s*MODEL:\s*(?P<VMO>\w*)\s*\w*\W*\w*\s*(?:\\r\\n)*\s*\w*\W*\w*\s*\w*\W*\w*\s*\w*\s*\w*\W*\w*\W*\w*\W*\w*\s*\w*\W*\w*\s*(?:\\r\\n)*\s*\w*\W*\w*\s*(?:\\r\\n)*\W*\w*\s*\w*\s*(?:\\r\\n)*\s*(BUSINESS|OWNER):?\s*(?P<OWNER>\w*\s*\w*\s*\w*\s*\w*)\s*(?:\\r\\n)*\s*ADDR:\s*(?P<STREET>\w*\s*\w*\s*\w*\s*\w*)\s*CITY:\s*(?P<CITY>\w*)\s*(?:\\r\\n)*\s*\w*\W*ZIP:\s*(?P<STATE>\w*)\s*(?P<ZIP>\d*)"
    AL_regex = r"nOWNER:(?P<OWNER>\w*\s*\w*)(?:\\r\\n)*\w*\W*(?P<STREET>\w*\s*\w*\s*\w*\s*\w*)\s*\W(?<CITY>\w*)\W*(?<STATE>\w*)\W*(?P<ZIP>\d*)\W*\w*(?:\\r\\n)*\w*\W*(?<VIN>\w*)\s*\w*\W*(?P<VYR>\d*)\s*\w*\W*(?P<VMA>\w*)\s*(?:\\r\\n)*\s*\w*\W*(?<VMO>\w*)(?:\s*\w*)*\W*\w*\s*\w*\W*(?P<VCO>\w*)"
    FL_regex = r"RECORD\s*\W\s*(?:\\r\\n)*\w*\s*(?P<VIN>\w*)\s*(?P<VMA>\w*)\s*(?P<VMO>\w*)\s*(?P<VYR>\d*)(?:\s*\w*)*(?:\\r\\n)*\s*\w*\W*(?P<VCO>\w*)\s*(?:\\r\\n)*\s*(?P<OWNER>(?:\w*\s*)*)(?:\s*\\r\\n)*(?P<STREET>(?:\w*\s)*)\w*\W(?:\s\w*)*\W*\w*(?:\\r\\n)*\s*(?P<CITY>\w*)\s*(?P<STATE>\w*)\s*(?P<ZIP>\w*)"
    MS_regex = r"nVIN\W*(?P<VIN>\w*)\s*(?P<VYR>\d*)\s*(?P<VMA>\w*)\s*(?P<VMO>\w*)\s*\w*\s*(?P<VCO>\w*)\s*(?:\\r\\n)*\w*\W*\w*\W*\w*\s*\w*\W*\w*\W*\w*\s*\w*\W*\w*\W*\w*\s*(?:\\r\\n)*\w*\W*(?P<OWNER>(?:\w*\W*)(?:\w*\s*)*)\W*\w*\W*\w*\W*(?:\w*\s*)*\W\s*(?:\\r\\n\s*)*(?P<STREET>\d*\s*\w*\s*\w*)\s*(?P<STREET2>\d*\s*\w*\s*\w*)?\s*(?:\\r\\n)*\s*(?P<CITY>\w*)\s*(?P<STATE>\w*)\s*(?P<ZIP>\w*)\s*(?P<CITY2>\w*)?\s*(?P<STATE2>\w*)?\s*(?P<ZIP2>\w*)?"
    QueryResponse = repr(QueryResponse)
    # apply the regex to the data

    if state == "TX":
        match = regex.search(TX_regex, QueryResponse, regex.DOTALL, timeout=1)
    elif state == "LA":
        match = regex.search(LA_regex, QueryResponse, regex.DOTALL, timeout=1)
    elif state == "AR":
        match = regex.search(AR_regex, QueryResponse, regex.DOTALL, timeout=1)
    elif state == "AL":
        match = regex.search(AL_regex, QueryResponse, regex.DOTALL, timeout=1)
    elif state == "FL":
        match = regex.search(FL_regex, QueryResponse, regex.DOTALL, timeout=1)
    elif state == "MS":
        match = regex.search(MS_regex, QueryResponse, regex.DOTALL, timeout=1)
    else:
        match = None

    result = {}
    # if a match was found, print the variables
    if match:
        # create a dictionary to store the variables
        result = match.groupdict()

    return result
