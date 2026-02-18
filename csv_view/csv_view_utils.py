from video.models import csv_metadata
from datetime import datetime


def get_data_for_csv(stationId):
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    csv_meta_data = csv_metadata.objects.filter(date__date=date,station_id=stationId)

    quickpd_data = []
    for meta in csv_meta_data:
        quickpd_data.append(meta.quickPD)
    serialized_data = [
            {
                "quickPDId": obj.id,
                "offenseDate": obj.offense_date,
                "offenseTime": obj.offense_time,
                "ticketNumber": obj.ticket_num,
                "firstName": obj.first_name,
                "middleName": obj.middle,
                "lastName": obj.last_name,
                "generation": obj.generation,
                "address": obj.address,
                "city": obj.city,
                "state": obj.state,
                "zip": obj.zip,
                "dob": obj.dob,
                "race": obj.race,
                "sex": obj.sex,
                "height": obj.height,
                "weight": obj.weight,
                "ssn": obj.ssn,
                "dl": obj.dl,
                "dlState": obj.dl_state,
                "accident": obj.accident,
                "comm": obj.comm,
                "vehder": obj.vehder,
                "arraignmentDate": obj.arraignment_date,
                "actualSpeed": obj.actual_speed,
                "postedSpeed": obj.posted_speed,
                "officerBadge": obj.officer_badge,
                "street1Id": obj.street1_id,
                "street2Id": obj.street2_id,
                "street1Name": obj.street1_name,
                "street2Name": obj.street2_name,
                "bac": obj.bac,
                "testType": obj.test_type,
                "plateNum": obj.plate_num,
                "plateState": obj.plate_state,
                "vin": obj.vin,
                "phoneNumber": obj.phone_number,
                "radar": obj.radar,
                "stateRS1": obj.state_rs1,
                "stateRS2": obj.state_rs2,
                "stateRS3": obj.state_rs3,
                "stateRS4": obj.state_rs4,
                "stateRS5": obj.state_rs5,
                "warning": obj.warning,
                "notes": obj.notes,
                "dlClass": obj.dl_class,
                "stationId": obj.station_id,
            }
            for obj in quickpd_data
        ]
    return serialized_data