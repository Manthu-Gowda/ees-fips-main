from video.models import (
    AddEvidenceCalibration,
    EvidenceCalibrationBin,
    Tattile,
    Video,
    Agency,
    TattileFile,
)
from datetime import datetime
from rest_framework.response import Response
from accounts_v2.serializer import ServiceResponse
from django.db.models import Q
import os
from django.template.loader import get_template
import pdfkit
from ees.utils import s3_get_file, upload_to_s3
from django.utils import timezone
from decouple import config as ENV_CONFIG
import base64
from ees.utils import get_presigned_url
import io
import os

TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
BASE_DIR = ENV_CONFIG("BASE_DIR")
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
# template_evidence_calibration = get_template("hudson_evidence_calibration.html")
hudson_evidence_calibration_template = get_template(
    "hudson_evidence_calibration_view_pdf.html"
)
krsy_evidence_calibration_template = get_template(
    "krsy_evidence_calibration_view_pdf.html"
)
# config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
# options = {
#     "page-size": "Letter",
#     "enable-local-file-access": "",
#     "load-error-handling": "ignore",
#     "load-media-error-handling": "ignore",
#     "no-stop-slow-scripts": "",
#     "javascript-delay": "3000",  # 3-second delay to allow images to load
#     "debug-javascript": "",  # Optional, for verbose output
# }
options = {
    "page-size": "Letter",
    "encoding": "UTF-8",
    "quiet": "",
}


def get_evidence_calibration_view_data():
    calibration_data = (
        AddEvidenceCalibration.objects.all()
        .values(
            "id",
            "license_plate",
            "evidence_date",
            "evidence_time",
            "evidence_speed",
            "evidence_ID",
            "badge_id",
            "tattile_id",
        )
        .order_by("id")
    )
    if not calibration_data:
        return None
    formatted_data = []
    # formatted_data.append({"totalRecords": calibration_data.count()})
    for row in calibration_data:
        formatted_data.append(
            {
                "id": row["id"],
                "licensePlate": row["license_plate"],
                "evidenceDate": (
                    row["evidence_date"].strftime("%B %d, %y")
                    if row["evidence_date"]
                    else None
                ),
                "evidenceTime": (
                    row["evidence_time"].strftime("%I:%M %p")
                    if row["evidence_time"]
                    else None
                ),
                "evidenceSpeed": row["evidence_speed"],
                "evidenceID": row["evidence_ID"],
                "badgeID": row["badge_id"],
                "tattileID": row["tattile_id"],
            }
        )
    return formatted_data


def get_evidence_details(media_type, media_id):
    try:
        if media_type != 3:  # tattile_Image
            return None

        evidence_details = EvidenceCalibrationBin.objects.filter(
            tattile_id=media_id
        ).values("license_plate", "vehicle_state", "camera_date", "tattile_id")

        if not evidence_details:
            return None

        # ---- Prepare containers ----
        evidence_ids = []
        detail = {}

        for item in evidence_details:
            plate_value = item["license_plate"]
            date_value = item["camera_date"].date()  # datetime → date

            results = AddEvidenceCalibration.objects.filter(
                license_plate=plate_value, evidence_date__date=date_value
            ).values("id", "evidence_ID")

            evidence_ids.extend(list(results))  #  collect all

            # Fill static details once
            detail.update(
                {
                    "licensePlate": item["license_plate"],
                    "state": item["vehicle_state"],
                    "tattileId": item["tattile_id"],
                }
            )

        tattile_data = (
            Tattile.objects.filter(id=media_id)
            .values("measured_speed", "location_id", "location_name")
            .first()
        )

        if not tattile_data:
            return None

        detail.update(
            {
                "speed": tattile_data["measured_speed"],
                "locationCode": tattile_data["location_id"],
                "locationName": tattile_data["location_name"],
                "evidenceIds": evidence_ids,
            }
        )

        return [detail]

    except Exception as e:
        print("Error in get_evidence_details:", e)
        return None


def submit_evidence_deatails(
    calibration, evidence_id, tattile_id, speed_pic="", license_pic=""
):
    # ------------------------------------------------------------------
    # CASE 1: tattile_id provided
    # ------------------------------------------------------------------
    if tattile_id:
        print("tattile_id provided", tattile_id)
        print("evidence_id:", evidence_id)

        # Check if this tattile_id is used for another evidence_id
        exists_ticket = AddEvidenceCalibration.objects.filter(
            tattile_id=tattile_id
        ).exclude(evidence_ID=evidence_id)
        exists_evidence = AddEvidenceCalibration.objects.filter(
            evidence_ID=evidence_id, tattile_id__isnull=False
        )

        if exists_ticket.exists():
            print("tattile_id exists")
            id_name = exists_ticket.values_list("evidence_ID", flat=True).first()
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": f"Tattile ticket already submitted in the evidence table with {id_name}",
                    }
                ).data,
                status=200,
            )
        if exists_evidence.exists():
            print("tattile_id exists")
            # id_name = exists_evidence.values_list("evidence_ID", flat=True).first()
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": f"Evidence ID already submitted with Tattile ticket, please select different evidence ID",
                    }
                ).data,
                status=200,
            )
        tattile_object = Tattile.objects.filter(id=tattile_id).first()
        if not tattile_object:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid tattile_id provided.",
                    }
                ).data,
                status=200,
            )
        speed_pic_url, license_pic_url = get_s3_file_name_url(
            media_id=tattile_id,
            station_id=tattile_object.station_id,
            speed_pic=speed_pic,
            license_pic=license_pic,
        )
        # Save
        tattile_object.speed_image_url = speed_pic_url
        tattile_object.license_image_url = license_pic_url
        tattile_object.save()

        calibration.tattile_id = tattile_id
        calibration.evidence_mapped_date = datetime.now()
        calibration.save()

    else:
        return Response(
            ServiceResponse(
                {
                    "statusCode": 400,
                    "message": "Provide tattile_id.",
                }
            ).data,
            status=200,
        )

    # Success
    return Response(
        ServiceResponse(
            {
                "statusCode": 200,
                "message": "Evidence details submitted successfully",
            }
        ).data,
        status=200,
    )


def get_s3_file_name_url(media_id, station_id, speed_pic="", license_pic=""):
    tattile_data = Tattile.objects.filter(id=media_id, station_id=station_id).first()
    if not tattile_data:
        raise ValueError("Image data not found for the given mediaId and stationId")
    date_now = datetime.now()
    formatted_date = date_now.strftime("%m%d%Y%H%M%S.%f")
    file_name = TattileFile.objects.filter(ticket_id=tattile_data.ticket_id).first()
    speed_pic_url = ""
    license_pic_url = ""
    if speed_pic:
        file_data = base64.b64decode(speed_pic)
        file_obj = io.BytesIO(file_data)
        file_name = f"{tattile_data.ticket_id}.png"
        speed_pic_url = upload_to_s3(file_obj, file_name, "PGM2/speed")

    if license_pic:
        file_data = base64.b64decode(license_pic)
        file_obj = io.BytesIO(file_data)
        file_name = f"{tattile_data.ticket_id}.jpg"
        license_pic_url = upload_to_s3(file_obj, file_name, "PGM2/plates")
    return speed_pic_url, license_pic_url


def get_evidence_table_data(response_list, page_items):
    tattile_ids = []
    for cal in page_items:
        if cal.tattile_id:
            tattile_ids.append(cal.tattile_id)

    tattile_camera_map = {
        row["tattile_id"]: {
            "date": row["camera_date"],
            "time": row["camera_time"],
        }
        for row in EvidenceCalibrationBin.objects.filter(
            tattile_id__in=tattile_ids
        ).values("tattile_id", "camera_date", "camera_time")
    }

    for cal in page_items:

        base_speed = cal.evidence_speed
        measured_speed = 0
        camera_datetime = None

        row = {
            "evidenceID": cal.evidence_ID,
            "licensePlate": cal.license_plate,
            "evidenceTime": (
                cal.evidence_time.strftime("%I:%M %p") if cal.evidence_time else None
            ),
            "evidenceDate": cal.evidence_date.strftime("%B %d, %Y"),
            "evidenceSpeed": base_speed,
            "badgeID": cal.badge_id if cal.badge_id else "",
        }

        # ----------- TATTILE -----------
        if cal.tattile:
            measured_speed = cal.tattile.measured_speed
            camera_datetime = tattile_camera_map.get(cal.tattile_id)
            if camera_datetime:

                row["cameraTime"] = (
                    camera_datetime["time"].strftime("%I:%M %p")
                    if camera_datetime["time"]
                    else None
                )
                row["cameraDate"] = (
                    camera_datetime["date"].strftime("%B %d, %Y")
                    if camera_datetime["date"]
                    else None
                )

        # -------- SPEED DIFF ------------
        speed_diff = abs(base_speed - measured_speed)
        row["measuredSpeed"] = measured_speed
        row["speedDifference"] = speed_diff

        # -------- ACCURACY --------------
        if base_speed:
            accuracy = 100 - ((speed_diff / base_speed) * 100)
            row["accuracy"] = round(accuracy, 2)
        else:
            row["accuracy"] = 0

        response_list.append(row)
    return response_list


def get_evidence_table_graph_data():
    submitted_tattile_ids = AddEvidenceCalibration.objects.filter(
        tattile_id__isnull=False
    ).order_by("-id")

    if not submitted_tattile_ids.exists():
        return {
            "totalRecords": 0,
            "overallAccuracy": 0,
            "highDeviationCount": 0,
        }

    accuracy_list = []
    high_deviation_count = 0

    for cal in submitted_tattile_ids:
        base_speed = cal.evidence_speed or 0
        measured_speed = cal.tattile.measured_speed if cal.tattile else 0

        speed_diff = abs(base_speed - measured_speed)

        if speed_diff > 1:
            high_deviation_count += 1

        accuracy = (
            round(100 - ((speed_diff / base_speed) * 100), 2) if base_speed else 0
        )

        accuracy_list.append(accuracy)

    overall_accuracy = (
        round(sum(accuracy_list) / len(accuracy_list), 2) if accuracy_list else 0
    )

    return {
        "totalRecords": submitted_tattile_ids.count(),
        "overallAccuracy": overall_accuracy,
        "highDeviationCount": high_deviation_count,
    }


def get_evidence_pdf_data(
    evidence_id, evidence_data, agnecy_id, isImage=False, isTattile=False
):
    data = {}

    if isTattile:

        badge_url = Agency.objects.get(id=agnecy_id).badge_url

        tattile_data = Tattile.objects.filter(id=evidence_data.tattile_id).first()

        if evidence_data.evidence_date:
            evidence_date = evidence_data.evidence_date.strftime("%m%d%Y")
        else:
            evidence_date = ""
        data = {
            "evidence_ID": evidence_id,
            "plate": evidence_data.license_plate,
            "evidence_time": evidence_data.evidence_time,
            "evidence_date": evidence_date,
            "evidence_speed": evidence_data.evidence_speed,
            "camera_speed": tattile_data.measured_speed if tattile_data else 0,
            "badge_id": evidence_data.badge_id if evidence_data.badge_id else "",
            "badge_url": get_presigned_url(badge_url) if badge_url else "",
        }

        data["difference"] = abs(data["evidence_speed"] - data["camera_speed"])
        data["speed_pic"] = (
            get_presigned_url(tattile_data.speed_image_url)
            if tattile_data.speed_image_url
            else ""
        )
        data["license_pic"] = (
            get_presigned_url(tattile_data.license_image_url)
            if tattile_data.license_image_url
            else ""
        )
        if data["evidence_speed"]:
            data["accuracy"] = round(
                100 - ((data["difference"] / data["evidence_speed"]) * 100), 2
            )
        else:
            data["accuracy"] = 0
        print("data:", data)
        return data


def create_evidence_pdf(filename, data, station_name):
    try:
        #  Render template correctly
        if station_name == "HUD-C":
            html = hudson_evidence_calibration_template.render({"data": data})
        elif station_name == "KRSY-C":
            html = krsy_evidence_calibration_template.render({"data": data})
        else:
            html = hudson_evidence_calibration_template.render({"data": data})
        location_path = rf"C:\Users\EM\Documents\evidence_calibration\{station_name}"
        # Correct output path
        location = os.path.join(location_path, "media", filename)

        #  MUST ensure directory exists
        os.makedirs(os.path.dirname(location), exist_ok=True)

        print("PDF location:", location)

        #  SAFE options (Windows)
        safe_options = {
            "page-size": "Letter",
            "encoding": "UTF-8",
            "quiet": "",
        }

        #  Generate PDF
        pdfkit.from_string(html, location, configuration=config, options=safe_options)
        print(f"PDF {filename} created successfully at {location}.")
        #  Upload to S3
        with open(location, "rb") as pdf_file:
            upload_to_s3(pdf_file, filename, "pdfs")
            print(f"PDF {filename} uploaded to S3 successfully.")
            os.remove(location)

    except OSError as e:
        print("wkhtmltopdf error:", e)
        raise
    except Exception as e:
        print("Unexpected error:", e)
        raise


def get_pdf_base64(filename):
    path = "pdfs/" + filename
    try:
        pdf_content = s3_get_file(path)
    except FileNotFoundError:
        return "File not found.."
    if pdf_content:
        base64_pdf = base64.b64encode(pdf_content).decode("utf-8")
        return base64_pdf
    else:
        return None
