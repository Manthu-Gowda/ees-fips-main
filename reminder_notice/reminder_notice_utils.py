from datetime import datetime, timezone, timedelta, date
from accounts_v2.serializer import *
from rest_framework.response import Response
import pdfkit
import os
import io
import calendar
from django.db.models.functions import ExtractYear, ExtractMonth
from video.models import *
from django.conf import settings
from django.db.models import Q, Exists, OuterRef
from django.db.models import Value
from django.db.models.functions import Concat, Lower, ExtractYear
from django.core.paginator import Paginator
from decouple import config as ENV_CONFIG
from ees.utils import (
    get_presigned_url,
)
from django.template.loader import get_template
from ees.utils import upload_to_s3, s3_get_file
from django.utils.timezone import now

template = get_template("pdf_final.html")
template_maryland = get_template("maryland-pdf.html")
template_reminder_hud_c = get_template("reminder-mail-hud-c.html")
template_kersey = get_template("kersey-pdf.html")
new_initial_template = get_template("new-initial-pdf.html")
new_hudson_template = get_template("new-hudson-pdf.html")
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
options = {"page-size": "Letter"}
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

BASE_URL = ENV_CONFIG("BASE_URL")
TEMP_REMINDER_PDF_DIR = ENV_CONFIG("TEMP_REMINDER_PDF_DIR")

adj_agencies = adj_metadata.objects.all()
video_agencies = Video.objects.all()
image_agencies = Image.objects.all()
data_agencies = Data.objects.all()
sup_agencies = sup_metadata.objects.all()
cit_agencies = Citation.objects.all()
ct_agency = CourtDates.objects.all()
per_agencies = Person.objects.all()
rl_agencies = road_location.objects.all()
fine_agencies = Fine.objects.all()
quick_pd_data = QuickPD.objects.all()
csv_meta_agencies = csv_metadata.objects.all()
veh_agencies = Vehicle.objects.all()


def get_reminder_notice_years(station_id: int):
    """
    Fetch unique years from sup_metadata where:
    - isApproved=True, isEdited=False
    - Has at least one related Citation with isApproved=True & current_citation_status='OR'

    Business Logic:
      1. If current month = January or February:
         - Exclude current year.
         - Exclude previous year if it only has December citations.
      2. If current month >= March:
         - Include current year if it has any data (e.g., Jan/Feb).
         - Include all other years normally.

    Returns sorted list of years as strings.
    """
    try:
        today = date.today()
        current_year = today.year
        current_month = today.month
        previous_year = current_year - 1

        # Subquery: check Citation existence
        citation_exists = Citation.objects.filter(
            id=OuterRef("citation_id"),
            station_id=station_id,
            isApproved=True,
            current_citation_status="OR",
        )

        # Main query: fetch (year, month)
        qs = (
            sup_metadata.objects.filter(
                station_id=station_id,
                isApproved=True,
                isEdited=False,
            )
            .annotate(year=ExtractYear("timeApp"))
            .annotate(month=ExtractMonth("timeApp"))
            .annotate(has_citation=Exists(citation_exists))
            .filter(has_citation=True)
            .values_list("year", "month")
            .distinct()
        )

        # Build year → months map
        year_months_map = {}
        for year, month in qs:
            year_months_map.setdefault(year, set()).add(month)

        valid_years = set(year_months_map.keys())

        # --- Apply exclusion logic ---
        if current_month in (1, 2):  # January or February
            # Exclude current year
            valid_years.discard(current_year)

            # Exclude previous year only if it has *only* December data
            if previous_year in year_months_map:
                if year_months_map[previous_year] == {12}:
                    valid_years.discard(previous_year)

        # For months >= March, keep all (including current year if it has any data)
        # Nothing to exclude beyond above conditions

        # Return sorted list
        return sorted(map(str, valid_years))

    except Exception as e:
        print(f"Error in get_reminder_notice_years: {e}")
        return []


def get_reminder_notice_months_by_year(station_id: int, year: int):
    """
    Fetch unique months for a given year from sup_metadata where:
    - isApproved=True, isEdited=False
    - At least one related Citation exists with isApproved=True & current_citation_status='OR'
    - Excludes the current and previous months (previous month may belong to previous year if current month is January)
    Returns a sorted list of dicts with month number and month name.
    Example: [{"month": 6, "monthName": "June"}, {"month": 7, "monthName": "July"}]
    """
    try:
        today = date.today()
        current_month = today.month
        current_year = today.year
        previous_month = 12 if current_month == 1 else current_month - 1
        previous_month_year = current_year - 1 if current_month == 1 else current_year

        # Subquery: check if at least one Citation exists
        citation_exists = Citation.objects.filter(
            id=OuterRef("citation_id"),
            station_id=station_id,
            isApproved=True,
            current_citation_status="OR",
        )

        # Main query
        qs = (
            sup_metadata.objects.filter(
                station_id=station_id,
                isApproved=True,
                isEdited=False,
            )
            .annotate(month=ExtractMonth("timeApp"))
            .annotate(has_citation=Exists(citation_exists))
            .filter(has_citation=True)
            .values_list("month", "timeApp__year")
            .distinct()
        )

        valid_months = []

        for month, record_year in qs:
            # Exclude current and previous month (cross-year aware)
            if record_year == current_year and month == current_month:
                continue
            if record_year == previous_month_year and month == previous_month:
                continue
            valid_months.append((month, record_year))

        # Filter only records matching the target `year`
        valid_months = [m for m, y in valid_months if y == year]

        # Build response
        response_data = [
            {"month": m, "monthName": calendar.month_name[m]}
            for m in sorted(set(valid_months))
        ]

        return response_data

    except Exception as e:
        print(f"Error in get_reminder_notice_months_by_year: {e}")
        return []


def citation_IDs_from_sup_metadata(station_id, year=None, month=None):
    """
    Fetch citation IDs from sup_metadata for a given year and optional month.
    If both year and month are None, fetch all citation IDs.
    Matches year and month based on the datetime's actual value (ignores timezone).
    """
    try:
        qs = (
            sup_metadata.objects.filter(
                station_id=station_id,
                isApproved=True,
                isEdited=False,
            )
            .values("citation_id", "timeApp")
            .distinct()
        )

        citation_ids = []
        for record in qs:
            time_app = record["timeApp"]  # This is a Python datetime object

            # ✅ If both year and month are None → fetch all
            if year is None and month is None:
                citation_ids.append(record["citation_id"])
                continue

            # ✅ If year is specified, match it
            if year is not None and time_app.year != int(year):
                continue

            # ✅ If month is specified, match it
            if month is not None and time_app.month != int(month):
                continue

            citation_ids.append(record["citation_id"])

        return citation_ids

    except Exception as e:
        print(f"Error in citation_IDs_from_sup_metadata: {e}")
        return []



def citationIDs_from_citation_table(
    station_id, sup_metadata_citation_ids, isRemainderSent=None
):
    """
    Fetch citationId (id), citationID, and isRemainderSent
    from Citation table where id is in sup_metadata_citation_ids
    and current_citation_status is 'OR'.
    """
    try:
        filter_criteria = {
            "station_id": station_id,
            "id__in": sup_metadata_citation_ids,
            "current_citation_status": "OR",
        }
        if isRemainderSent is not None:
            filter_criteria["isRemainderSent"] = False
        qs = (
            Citation.objects.filter(**filter_criteria)
            .values("id", "citationID", "isRemainderSent")
            .distinct()
        )

        # Rename 'id' to 'citationId' and isRemainderSent to isApproved
        citation_data = [
            {
                "citationId": row["id"],
                "citationID": row["citationID"],
                "isApproved": row["isRemainderSent"],
            }
            for row in qs
        ]

        # print("citation_data from citation table", citation_data)
        return citation_data

    except Exception as e:
        print(f"Error in citationIDs_from_citation_table: {e}")
        return []


def citaionIDs_from_paid_citaion(citation_table_data):
    """
    From citation_table_data, filter out citations that are present in PaidCitationsData.
    Returns unpaid citation details with citationId, citationID, and isRemainderSent.
    """
    try:
        # Extract all citationIDs
        citation_ids = [c["citationID"] for c in citation_table_data]

        # Get paid citation IDs
        paid_citation_ids = list(
            PaidCitationsData.objects.filter(citationID__in=citation_ids).values_list(
                "citationID", flat=True
            )
        )
        # print("paid_citation_ids", paid_citation_ids)

        # Keep only unpaid citations
        unpaid_citation_data = [
            c for c in citation_table_data if c["citationID"] not in paid_citation_ids
        ]
        # print("unpaid_citation_data", unpaid_citation_data)

        return unpaid_citation_data

    except Exception as e:
        print(f"Error in citationIDs_from_paid_citation: {e}")
        return []


def get_cit_refactor(citation_id, user_station, image_flow=False, is_tattile=False):
    print(f"Generating cit_refactor data for citation_id: {citation_id}")
    try:
        citation_obj = Citation.objects.get(citationID=citation_id)
    except Citation.DoesNotExist:
        return {"id": citation_id, "success": False, "message": "Citation not found"}

    total = (
        quick_pd_data.filter(ticket_num=citation_id, station=user_station)
        .values()
        .first()
    )
    if not total:
        return {
            "id": citation_id,
            "success": False,
            "message": "No QuickPD data found",
        }

    cit_choice = (
        cit_agencies.filter(citationID=citation_id, station=user_station)
        .values()
        .first()
    )
    if not cit_choice:
        return {
            "id": citation_id,
            "success": False,
            "message": "No Citation data found",
        }

    # -------- image/video/tattile logic --------
    if image_flow and not is_tattile:
        adj_choice = image_agencies.filter(id=cit_choice["image_id"]).values().first()
        if not adj_choice:
            return {
                "id": citation_id,
                "success": False,
                "message": f"No Image data found for image_id: {cit_choice['image_id']}",
            }
        offence_time = adj_choice["time"]

    elif not image_flow and not is_tattile:
        adj_choice = (
            video_agencies.filter(id=cit_choice["video_id"], station=user_station)
            .values()
            .first()
        )
        if not adj_choice:
            return {
                "id": citation_id,
                "success": False,
                "message": f"No Video data found for video_id: {cit_choice['video_id']}",
            }
        offence_time = adj_choice["datetime"]

    elif not image_flow and is_tattile:
        adj_choice = (
            Tattile.objects.filter(id=cit_choice["tattile_id"], station=user_station)
            .values()
            .first()
        )
        if not adj_choice:
            return {
                "id": citation_id,
                "success": False,
                "message": f"No Tattile data found for tattile_id: {cit_choice['tattile_id']}",
            }
        offence_time = adj_choice["image_time"]

    # -------- vehicle --------
    veh_choice = (
        veh_agencies.filter(id=cit_choice["vehicle_id"], station=user_station)
        .values()
        .first()
    )
    if not veh_choice:
        return {
            "id": citation_id,
            "success": False,
            "message": f"No Vehicle data found for vehicle_id: {cit_choice['vehicle_id']}",
        }

    # -------- person --------
    per_choice = per_agencies.filter(id=cit_choice["person_id"]).values().first()
    if not per_choice:
        return {
            "id": citation_id,
            "success": False,
            "message": f"No Person data found for person_id: {cit_choice['person_id']}",
        }

    # -------- supervisor --------
    sup_data = (
        sup_agencies.filter(citation=citation_obj, station=user_station)
        .values()
        .first()
    )
    if not sup_data:
        return {
            "id": citation_id,
            "success": False,
            "message": "No Supervisor metadata found",
        }
    dt = sup_data["timeApp"] + timedelta(days=30)
    date_app = sup_data["timeApp"] + timedelta(days=1)
    if citation_id in ["HUD-C-00000085", "HUD-C-00000365"]:
        due_date = "01/30/2025"
    elif citation_id in [
        "HUD-C-00000290",
        "HUD-C-00000179",
        "HUD-C-00000183",
        "HUD-C-00000468",
        "HUD-C-00000180",
        "HUD-C-00000348",
    ]:
        due_date = "01/19/2025"
    elif citation_id in [
        "HUD-C-00001128",
        "HUD-C-00000590",
        "HUD-C-00001081",
        "HUD-C-00000863",
        "HUD-C-00001056",
    ]:
        due_date = "2/25/25"
    else:
        due_date = datetime.strftime(dt, "%m/%d/%Y")
    agency = Agency.objects.filter(station=user_station).values().first()
    if not agency:  # Added check for agency
        print(f"No Agency data found for station: {user_station}")
        return {
            "id": citation_id,
            "success": False,
            "message": f"No Agency data found for station: {user_station}",
        }

    agency_name = Station.objects.filter(id=user_station).values("name").first()
    if not agency_name:  # Added check for agency_name
        print(f"No Station data found for station: {user_station}")
        return {
            "id": citation_id,
            "success": False,
            "message": f"No Station data found for station: {user_station}",
        }
    sig_img = None
    address_part_1 = None
    address_part_2 = None
    fply_address_part = None
    if agency_name.get("name") == "MOR-C":
        qr_code = ENV_CONFIG("MOR-C-QR-CODE")
    elif agency_name.get("name") == "FED-M":
        qr_code = ENV_CONFIG("FED-M-QR-CODE")
        sig_off = ENV_CONFIG("FED-M-SIG-OFFICER")
        sig_img = get_presigned_url(sig_off)
    elif agency_name.get("name") == "WBR2":
        qr_code = ENV_CONFIG("WBR2-QR-CODE")
        address_parts = agency["address"].split("Drive")
        address_part_1 = address_parts[0].strip() + " Drive"
        address_part_2 = address_parts[1].strip()
    elif agency_name.get("name") == "HUD-C":
        qr_code = ENV_CONFIG("HUD-C-QR-CODE")
    elif agency_name.get("name") == "MAR":
        qr_code = ENV_CONFIG("MAR-QR-CODE")
    elif agency_name.get("name") == "CLA":
        qr_code = ENV_CONFIG("CLA-QR-CODE")
    elif agency_name.get("name") == "FPLY-C":
        qr_code = ENV_CONFIG("FPLY-C-QR-CODE")
        address = per_choice.get("address", "")
        if len(address) >= 27 or "PO" in address:
            person_address_part = address.split(",")
            if len(person_address_part) >= 2:
                fply_address_part = (
                    person_address_part[0].strip()
                    + ", <br>"
                    + person_address_part[1].strip()
                )
            else:
                fply_address_part = address
        else:
            fply_address_part = address
    elif agency_name.get("name") == "KRSY-C":
        qr_code = ENV_CONFIG("KRSY-C-QR-CODE")
    else:
        qr_code = None
        sig_img = None

    if qr_code != None:
        s3_url_qr_code = get_presigned_url(qr_code)
    else:
        s3_url_qr_code = None

    if image_flow and is_tattile == False:
        plate_pic_base_url = (
            "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
        )
        data = {
            "total": total,
            "per": per_choice,
            "veh": veh_choice,
            "cit": cit_choice,
            "vid": adj_choice,
            "due_date": due_date,
            "agency": agency,
            "plate_pic_base_url": plate_pic_base_url,
            "s3_url_qr_code": s3_url_qr_code,
            "sig_img": sig_img,
            "address_part_1": address_part_1,
            "address_part_2": address_part_2,
            "offence_time": offence_time,
            "date_app": date_app,
            "fply_address_part": fply_address_part,
        }
    elif image_flow == False and is_tattile == False:
        speed_pic_base_url = (
            "" if cit_choice["speed_pic"].startswith("https") else BASE_URL
        )
        plate_pic_base_url = (
            "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
        )

        data = {
            "total": total,
            "per": per_choice,
            "veh": veh_choice,
            "cit": cit_choice,
            "vid": adj_choice,
            "due_date": due_date,
            "agency": agency,
            "speed_pic_base_url": speed_pic_base_url,
            "plate_pic_base_url": plate_pic_base_url,
            "s3_url_qr_code": s3_url_qr_code,
            "sig_img": sig_img,
            "address_part_1": address_part_1,
            "address_part_2": address_part_2,
            "offence_time": offence_time,
            "date_app": date_app,
            "fply_address_part": fply_address_part,
        }
    elif image_flow == False and is_tattile == True:
        speed_pic_base_url = (
            "" if cit_choice["speed_pic"].startswith("https") else BASE_URL
        )
        plate_pic_base_url = (
            "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
        )
        data = {
            "total": total,
            "per": per_choice,
            "veh": veh_choice,
            "cit": cit_choice,
            "vid": adj_choice,
            "due_date": due_date,
            "agency": agency,
            "speed_pic_base_url": speed_pic_base_url,
            "plate_pic_base_url": plate_pic_base_url,
            "s3_url_qr_code": s3_url_qr_code,
            "sig_img": sig_img,
            "address_part_1": address_part_1,
            "address_part_2": address_part_2,
            "offence_time": offence_time,
            "date_app": date_app,
            "fply_address_part": fply_address_part,
        }
    if image_flow and is_tattile == False:
        data["cit"]["location_name"] = Image.objects.get(
            id=data["cit"]["image_id"]
        ).location_name
    elif image_flow == False and is_tattile == False:
        location_instance = rl_agencies.get(id=data["cit"]["location_id"])
        data["cit"]["location_name"] = location_instance.location_name
    elif image_flow == False and is_tattile == True:
        print("tattile_id:", data["cit"]["tattile_id"])
        data["cit"]["location_name"] = Tattile.objects.get(
            id=data["cit"]["tattile_id"]
        ).location_name
    else:
        return "No Data Found"

    license_state_instance = State.objects.get(id=data["veh"]["lic_state_id"])
    data["veh"]["lic_state"] = license_state_instance.ab

    agency_station = Station.objects.get(id=agency["station_id"])

    agency_state = State.objects.get(id=agency_station.state.id)

    citation_station = Station.objects.get(id=cit_choice["station_id"])
    citation_state = State.objects.get(id=citation_station.state.id)

    data["agency"]["state"] = agency_state.ab
    data["cit"]["state"] = citation_state.name
    fine_instance = get_fine_by_id(data["cit"]["fine_id"])
    # Decimals
    if data["cit"]["current_citation_status"] != "EF":
        data["cit"]["fine"] = str(fine_instance.fine)
    else:
        data["cit"]["fine"] = str(
            CitationsWithEditFine.objects.filter(citation_id=data["cit"]["id"])
            .last()
            .new_fine
        )
    if image_flow == False and is_tattile == False:
        data["vid"]["speed_time"] = str(data["vid"]["speed_time"])
        data["vid"]["datetime"] = str(data["vid"]["datetime"])
    # DateTime
    data["cit"]["datetime"] = str(data["cit"]["datetime"])
    data["agency"]["onboarding_dt"] = str(data["agency"]["onboarding_dt"])
    data["cit"]["speed_pic"] = get_presigned_url(data["cit"]["speed_pic"])
    if image_flow and is_tattile == False:
        data["cit"]["speed_pic"] = get_presigned_url(
            Image.objects.get(id=data["cit"]["image_id"]).speed_image_url
        )
        data["cit"]["plate_pic"] = get_presigned_url(
            Image.objects.get(id=data["cit"]["image_id"]).lic_image_url
        )
    elif image_flow == False and is_tattile == False:
        data["cit"]["plate_pic"] = get_presigned_url(data["cit"]["plate_pic"])
    elif image_flow == False and is_tattile == True:
        data["cit"]["speed_pic"] = get_presigned_url(
            Tattile.objects.get(id=data["cit"]["tattile_id"]).speed_image_url
        )

        data["cit"]["plate_pic"] = get_presigned_url(
            Tattile.objects.get(id=data["cit"]["tattile_id"]).license_image_url
        )

    badge_url = data.get("agency", {}).get("badge_url", "")
    print("initial_badge_url:", badge_url)
    data["agency"]["badge_url"] = get_presigned_url(badge_url) if badge_url else ""
    print("generated data for citation refactor:")
    return data


def get_fine_by_id(fine_id):
    try:
        # Assuming fine_id is the primary key of the Fine model
        fine = Fine.objects.get(pk=fine_id)
        return fine
    except Fine.DoesNotExist:
        return None


def get_reminder_hud_c_cit(
    citation_id, user_station, image_flow=False, is_tattile=False
):
    print(f"Generating HUD-C reminder data for citation_id: {citation_id}")
    try:
        citation_obj = Citation.objects.get(citationID=citation_id)
    except Citation.DoesNotExist:
        return {"id": citation_id, "success": False, "message": "No Citation found"}

    total = (
        quick_pd_data.filter(ticket_num=citation_id, station=user_station)
        .values()
        .first()
    )
    if not total:
        print("No QuickPD data found")
        return None

    cit_choice = (
        cit_agencies.filter(citationID=citation_id, station=user_station)
        .values()
        .first()
    )
    if not cit_choice:
        print("No Citation data found")
        return None
    if image_flow and not is_tattile:
        adj_choice = image_agencies.filter(id=cit_choice["image_id"]).values().first()
        if not adj_choice:
            print(f"No Image data found for image_id: {cit_choice['image_id']}")
            return None
        offence_time = adj_choice["time"]

    elif not image_flow and not is_tattile:
        adj_choice = (
            video_agencies.filter(id=cit_choice["video_id"], station=user_station)
            .values()
            .first()
        )
        if not adj_choice:
            print(f"No Video data found for video_id: {cit_choice['video_id']}")
            return None
        offence_time = adj_choice["datetime"]

    elif not image_flow and is_tattile:
        adj_choice = (
            Tattile.objects.filter(id=cit_choice["tattile_id"], station=user_station)
            .values()
            .first()
        )
        if not adj_choice:
            print(f"No Tattile data found for tattile_id: {cit_choice['tattile_id']}")
            return None
        offence_time = adj_choice["image_time"]

    veh_choice = (
        veh_agencies.filter(id=cit_choice["vehicle_id"], station=user_station)
        .values()
        .first()
    )
    if not veh_choice:
        print(f"No Vehicle data found for vehicle_id: {cit_choice['vehicle_id']}")
        return None

    per_choice = per_agencies.filter(id=cit_choice["person_id"]).values().first()
    if not per_choice:
        print(f"No Person data found for person_id: {cit_choice['person_id']}")
        return None

    sup_data = (
        sup_agencies.filter(citation=citation_obj, station=user_station)
        .values()
        .first()
    )
    if not sup_data:
        print("No Supervisor metadata found")
        return None
    cit_choice_fine = cit_agencies.filter(
        citationID=citation_id, station=user_station
    ).first()

    if cit_choice_fine and cit_choice_fine.fine:
        print("Fine amount:", cit_choice_fine.fine.fine)
    # original_citation_dates
    captured_date = cit_choice.get("captured_date")
    voilation_date = ""

    if captured_date:
        if isinstance(captured_date, (datetime, date)):
            voilation_date = (
                f"{captured_date.month}/{captured_date.day}/{captured_date.year}"
            )
        else:
            try:
                dt = datetime.strptime(str(captured_date), "%Y-%m-%d")
                voilation_date = f"{dt.month}/{dt.day}/{dt.year}"
            except Exception as e:
                print("Invalid captured_date format:", e)
                voilation_date = ""

    print("voilation_date:", voilation_date)
    time_app = sup_data.get("timeApp")

    issued_date = None
    if time_app:
        # If time_app is a datetime object already
        if isinstance(time_app, datetime):
            issued_date = time_app.strftime("%m/%d/%Y")  # → 06/16/2023
        else:
            # If it's a string, parse then format
            issued_date = datetime.fromisoformat(str(time_app)).strftime("%m/%d/%Y")

    print("Issued Date:", issued_date)
    original_due_date = None
    if total and total.get("arraignment_date"):
        raw_date = total["arraignment_date"]  # e.g. "08212023"
        try:
            # parse MMDDYYYY → datetime
            dt = datetime.strptime(raw_date, "%m%d%Y")
            # subtract one day
            dt = dt - timedelta(days=1)
            # finally format to MM/DD/YYYY
            original_due_date = dt.strftime("%m/%d/%Y")
        except Exception as e:
            print("Invalid date format:", e)

    print("Due Date:", original_due_date)
    approve_date = datetime.now()
    date_app = approve_date.strftime("%m/%d/%Y")
    due_date_dt = approve_date + timedelta(days=30)
    due_date = due_date_dt.strftime("%m/%d/%Y")

    agency = Agency.objects.filter(station=user_station).values().first()
    if not agency:
        print(f"No Agency data found for station: {user_station}")
        return None
    agency_name = Station.objects.filter(id=user_station).first()
    if not agency_name:
        print(f"No Station found for id: {user_station}")
        return None
    print("agency_name:", agency_name)
    sig_img = None
    address_part_1 = None
    address_part_2 = None

    if agency_name.name == "HUD-C":
        qr_code = ENV_CONFIG("HUD-C-QR-CODE")
    else:
        qr_code = None
        sig_img = None

    if qr_code != None:
        s3_url_qr_code = get_presigned_url(qr_code)
    else:
        s3_url_qr_code = None
    data = {
        "total": total,
        "per": per_choice,
        "veh": veh_choice,
        "cit": cit_choice,
        "vid": adj_choice,
        "due_date": due_date,
        "agency": agency,
        "s3_url_qr_code": s3_url_qr_code,
        "sig_img": sig_img,
        "address_part_1": address_part_1,
        "address_part_2": address_part_2,
        "offence_time": offence_time,
        "date_app": date_app,
        "date_violation": voilation_date,
        "original_app_date": issued_date,
        "original_due_date": original_due_date,
    }
    if image_flow == False and is_tattile == False:
        location_instance = rl_agencies.get(id=data["cit"]["location_id"])
        data["cit"]["location_name"] = location_instance.location_name

    license_state_instance = State.objects.get(id=data["veh"]["lic_state_id"])
    data["veh"]["lic_state"] = license_state_instance.ab

    agency_station = Station.objects.get(id=agency["station_id"])
    agency_state = State.objects.get(id=agency_station.state.id)
    citation_station = Station.objects.get(id=cit_choice["station_id"])
    citation_state = State.objects.get(id=citation_station.state.id)

    data["agency"]["state"] = agency_state.ab
    data["cit"]["state"] = citation_state.name

    fine_instance = get_fine_by_id(data["cit"]["fine_id"])
    data["cit"]["fine"] = str(fine_instance.fine)

    data["cit"]["datetime"] = str(data["cit"]["datetime"])
    data["agency"]["onboarding_dt"] = str(data["agency"]["onboarding_dt"])
    # data["agency"]["badge_url"] = get_presigned_url(data["agency"]["badge_url"])
    badge_url = data["agency"].get("badge_url")
    print("remainder_badge_url:", badge_url)
    if badge_url:
        data["agency"]["badge_url"] = get_presigned_url(badge_url)
    else:
        data["agency"]["badge_url"] = None
    print("generated data for reminder hud_c_cit")
    return data



import io
import os


def save_combined_pdf(cit_id, station_name, data_initial, data_reminder):
    """
    Generate one combined PDF (reminder + initial citation),
    save locally and upload to S3.
    """
    print("Generating combined PDF for cit_id:", cit_id)

    # Render reminder
    html_reminder = new_hudson_template.render(data_reminder)

    # Render initial citation
    if station_name in ["FED-M"]:
        html_initial = template_maryland.render(data_initial)
    elif station_name in ["KRSY-C"]:
        html_initial = template_kersey.render(data_initial)
    elif station_name in ["HUD-C"]:
        html_initial = new_initial_template.render(data_initial)
    else:
        html_initial = template.render(data_initial)

    # Wrap both templates in isolated containers
    html_combined = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
            }}
            .page-break {{
                page-break-before: always;
            }}
            .reminder-section table, .reminder-section th, .reminder-section td {{
                border: 1px solid black;
                border-collapse: collapse;
                padding: 4px;
            }}
            .initial-section table, .initial-section th, .initial-section td {{
                border: 1px solid black;
                border-collapse: collapse;
                padding: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="reminder-section">
            {html_reminder}
        </div>
        <div class="initial-section page-break">
            {html_initial}
        </div>
    </body>
    </html>
    """

    filename = f"{cit_id}combined_reminder.pdf"

    # Generate PDF as bytes
    pdf_bytes = pdfkit.from_string(
        html_combined, False, configuration=config, options=options
    )

    # -----------------------------
    # 1) Save locally
    # -----------------------------
    local_dir = r"C:\Users\EM\Documents\reminder_mailer_pdfs\HUD-C"
    os.makedirs(local_dir, exist_ok=True)  # make sure dir exists
    local_path = os.path.join(local_dir, filename)

    with open(local_path, "wb") as f:
        f.write(pdf_bytes)

    print(f"Saved locally at: {local_path}")

    # -----------------------------
    # 2) Upload to S3
    # -----------------------------
    pdf_fileobj = io.BytesIO(pdf_bytes)

    combined_reminder_notice_pdf_path = upload_to_s3(
        pdf_fileobj, filename, "reminder_notice_pdfs"
    )

    print("Uploaded to S3 at:", combined_reminder_notice_pdf_path)

    return combined_reminder_notice_pdf_path


import base64
from urllib.parse import urlparse


def get_reminder_pdf_base64(s3_url: str) -> str:
    """
    Given an S3 URL, fetch the PDF and return it as a base64 string.
    """
    try:
        # Extract the S3 key from the URL
        parsed = urlparse(s3_url)
        s3_key = parsed.path.lstrip("/")  # remove leading "/"
        print("Extracted S3 key:", s3_key)
        # Download PDF from S3
        pdf_bytes = s3_get_file(s3_key)  # uses your existing helper

        if not pdf_bytes:
            raise ValueError("Failed to fetch PDF from S3")

        # Convert PDF bytes → base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        return pdf_base64

    except Exception as e:
        print(f"Error in get_reminder_pdf_base64: {e}")
        return ""


def citation_data_for_reminder_approved_table(
    date_type,
    from_date,
    to_date,
    search_string,
    page_index=1,
    page_size=10,
    station_id=None,
    isDownload=False,
):
    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%Y-%m-%d")

    query = Q(isApproved=True) & Q(isRemainderSent=True)
    if station_id:
        query &= Q(station_id=station_id)
    # Date filtering
    if date_type == 1:
        if from_date:
            query &= Q(captured_date__gte=from_date)
        if to_date:
            query &= Q(captured_date__lte=to_date)
    elif date_type == 2:
        pass
    else:
        return "Invalid date type. It should be 1 or 2."
    citations_with_meta = []
    sup_query = Q()
    # Search filtering
    full_name_search = False
    if search_string:
        search_string = search_string.lower()
        if " " in search_string:
            full_name_search = True  # flag to annotate later
        else:
            search_string = search_string.replace(" ", "")
            query &= (
                Q(citationID__icontains=search_string)
                | Q(person__first_name__icontains=search_string)
                | Q(person__last_name__icontains=search_string)
                | Q(vehicle__plate__icontains=search_string)
            )
    if date_type == 2:
        # When sorting by approval date, sort by its remainderSentDate
        sup_query = Q(isRemainderSent=True)
        if station_id:
            sup_query &= Q(station_id=station_id)
        if from_date:
            sup_query &= Q(remainderSentDate__gte=from_date)
        if to_date:
            sup_query &= Q(remainderSentDate__lte=to_date)
        if search_string:
            sup_query &= (
                Q(citationID__icontains=search_string)
                | Q(person__first_name__icontains=search_string)
                | Q(person__last_name__icontains=search_string)
                | Q(vehicle__plate__icontains=search_string)
            )
        citations_queryset = (
            Citation.objects.filter(sup_query)
            .select_related("person", "fine")
            .order_by("-datetime")
        )
        if full_name_search:
            citations_queryset = citations_queryset.annotate(
                full_name=Concat(
                    Lower("person__first_name"), Value(" "), Lower("person__last_name")
                )
            ).filter(Q(full_name__icontains=search_string))
        citations_with_meta = list(citations_queryset)
    else:
        citations_queryset = Citation.objects.filter(query)

        if full_name_search:
            citations_queryset = citations_queryset.annotate(
                full_name=Concat(
                    Lower("person__first_name"), Value(" "), Lower("person__last_name")
                )
            ).filter(Q(full_name__icontains=search_string))

        # Always add select_related and ordering at the end
        citations_queryset = citations_queryset.select_related(
            "person", "fine"
        ).order_by("-datetime")
        citations_with_meta = list(citations_queryset)

    all_citations = citations_with_meta
    citation_ids = [c.citationID for c in all_citations]
    quick_pd_data = {
        qpd.ticket_num: qpd
        for qpd in QuickPD.objects.filter(ticket_num__in=citation_ids)
    }
    sup_meta_data = {
        meta.citation_id: meta
        for meta in sup_metadata.objects.filter(
            citation_id__in=[c.id for c in all_citations]
        )
    }
    paid_citation_ids = set(
        PaidCitationsData.objects.filter(citationID__in=citation_ids).values_list(
            "citationID", flat=True
        )
    )

    location_ids = {c.location_id for c in all_citations if c.video_id or c.tattile_id}
    image_location_ids = {c.image_location for c in all_citations if c.image_id}

    road_location_data = {
        loc["id"]: loc
        for loc in road_location.objects.filter(id__in=location_ids).values(
            "id", "LOCATION_CODE", "location_name"
        )
    }
    image_location_data = {
        loc["trafficlogix_location_id"]: loc
        for loc in road_location.objects.filter(
            trafficlogix_location_id__in=image_location_ids
        ).values("trafficlogix_location_id", "LOCATION_CODE", "location_name")
    }
    full_citation_data = []
    for citation in all_citations:
        person = citation.person
        fine_value = (
            citation.fine.fine
            if citation.current_citation_status != "EF"
            else CitationsWithEditFine.objects.filter(
                station=citation.station, citation=citation
            )
            .last()
            .new_fine
        )
        quick_pd = quick_pd_data.get(citation.citationID)
        sup_meta = sup_meta_data.get(citation.id)
        paid_status_display = (
            "Paid" if citation.citationID in paid_citation_ids else "Unpaid"
        )

        media_data = build_media_data(
            citation,
            person,
            quick_pd,
            fine_value,
            road_location_data,
            image_location_data,
            paid_status_display,
        )
        full_citation_data.append(media_data)
    # Paginate the final expanded list
    if isDownload:
        return {
            "data": full_citation_data,
            "total_records": len(full_citation_data),
            "has_next_page": False,
            "has_previous_page": False,
            "current_page": 1,
            "total_pages": 1,
        }

    paginator = Paginator(full_citation_data, page_size)
    page = paginator.get_page(page_index)

    return {
        "data": list(page.object_list),
        "total_records": paginator.count,
        "has_next_page": page.has_next(),
        "has_previous_page": page.has_previous(),
        "current_page": page.number,
        "total_pages": paginator.num_pages,
    }


def build_media_data(
    citation,
    person,
    quick_pd,
    fine,
    road_location_data,
    image_location_data,
    paid_status,
):
    media_id = None
    location = {}
    citation_status = citation.current_citation_status or "OR"

    if citation.video_id:
        media_id = f"V-{citation.video_id}"
        location = road_location_data.get(citation.location_id, {})
    elif citation.image_id:
        media_id = f"I-{citation.image_id}"
        location = image_location_data.get(citation.image_location, {})
    elif citation.tattile_id:
        media_id = f"T-{citation.tattile_id}"
        location = road_location_data.get(citation.location_id, {})

    return {
        "citationId": citation.id,
        "citationID": citation.citationID,
        "mediaId": media_id,
        "fine": fine,
        "speed": citation.speed,
        "locationCode": location.get("LOCATION_CODE"),
        "locationName": location.get("location_name"),
        "firstName": person.first_name if person else None,
        "lastName": person.last_name if person else None,
        "state": quick_pd.plate_state if quick_pd else None,
        "plate": quick_pd.plate_num if quick_pd else None,
        "capturedDate": (
            citation.captured_date.strftime("%B %#d, %Y")
            if citation.captured_date
            else None
        ),
        "approvedDate": citation.remainderSentDate.strftime("%B %#d, %Y"),
        "citationStatus": citation_status,
        "paidStatus": paid_status,
        "address": (
            f"{person.address},{person.city},{person.state} {person.zip}"
            if person
            else None
        ),
        "combinedPdfPath": citation.remainderCombinedPdfPath,
    }
