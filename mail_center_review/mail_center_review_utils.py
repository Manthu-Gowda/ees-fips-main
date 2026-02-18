import os
import base64
import logging
import shutil
import zipfile
import pdfkit
import pandas as pd
from typing import Optional
from collections import defaultdict
from django.db.models import Value
from django.db.models.functions import Concat, Lower
from datetime import datetime, timedelta,date, time
from django.db.models import Q
from datetime import timedelta
from PyPDF2 import PdfReader
from django.db.models.functions import TruncDate

from video.models import PaidCitationsData, Citation, QuickPD, Station, Agency, Fine, csv_metadata,sup_metadata
from video.FipsSftpClient import FipsSftpClient
from video.views import get_cit_refactor
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.template.loader import get_template
from ees.utils import s3_get_file, upload_to_s3
from video.utils import xpress_csv
from .distributer import dist_smtp_mail_center_review
from decouple import config as ENV_CONFIG
from video.citations.versioning_utils import get_snapshot_by_version, get_latest_version_number
from rest_framework.response import Response
from approved_tables.approved_table_utils import patch_pdf_data_from_snapshot
from video.pdf_creation import save_pdf

logger = logging.getLogger(__name__)
TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
TEMP_CSV_DIR = ENV_CONFIG("TEMP_CSV_DIR")
TEMP_ZIP_DIR = ENV_CONFIG("TEMP_ZIP_DIR")
BASE_DIR = ENV_CONFIG("BASE_DIR")
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

def get_all_approved_dates(station_id: int,is_edited: Optional[bool] = False):
    try:
        qs = (
            sup_metadata.objects.filter(
                station_id=station_id, isApproved=True, isEdited=is_edited, isMailCitationApproved=False,
            isMailCitationRejected=False,
            )
            .annotate(d=TruncDate("timeApp"))
            .values_list("d", flat=True)
            .distinct()
            .order_by("-d")
        )
        return [{"date": f"{d.strftime('%B')} {d.day}, {d.year}"} for d in qs if d]
    except Exception as e:
        print(f"Error in get_all_approved_dates: {e}")
        return []


def citation_data_for_mail_center_review(
    station_id, approved_date, is_edited, search_string=None, page_index=1, page_size=10
):
    if isinstance(approved_date, str):
        approved_date = datetime.strptime(approved_date, "%Y-%m-%d")
    sup_query = (
        Q(isApproved=True)
        & Q(isEdited=is_edited)
        & Q(isMailCitationApproved=False)
        & Q(isMailCitationRejected=False)
    )
    if approved_date:
        sup_query &= Q(timeApp__date=approved_date)
    if station_id:
        sup_query &= Q(station_id=station_id)
    sup_metadata_objects = sup_metadata.objects.filter(sup_query).values_list(
        "citation_id", flat=True
    )
    query = Q(id__in=sup_metadata_objects)
    # unpaid citations only
    paid_citation_ids_query = PaidCitationsData.objects.values_list(
        "citationID", flat=True
    )
    query &= ~Q(citationID__in=paid_citation_ids_query)
    print("applied unpaid filter")
    citations_queryset = Citation.objects.filter(query)
    if search_string:
        search_string_lower = search_string.lower()
        citations_queryset = citations_queryset.annotate(
            full_name=Concat(
                Lower("person__first_name"), Value(" "), Lower("person__last_name")
            )
        ).filter(
            Q(full_name__icontains=search_string_lower)
            | Q(citationID__icontains=search_string_lower)
            | Q(vehicle__plate__icontains=search_string_lower)
        )
    # Always add select_related and ordering at the end
    citations_queryset = citations_queryset.select_related("person", "fine").order_by(
        "-datetime"
    )
    #  Get total count (efficiently)
    total_records = citations_queryset.count()
    print("Total records found:", total_records)
    #  Pagination logic
    start_index = (page_index - 1) * page_size
    end_index = start_index + page_size
    paginated_queryset = citations_queryset[start_index:end_index]
    citation_ids = [c.citationID for c in paginated_queryset]

    quick_pd_data = {
        qpd.ticket_num: qpd
        for qpd in QuickPD.objects.filter(ticket_num__in=citation_ids)
    }
    data = []
    for citation in paginated_queryset:
        person = citation.person
        quick_pd = quick_pd_data.get(citation.citationID)
        record = {
            "citationId": citation.id,
            "citationID": citation.citationID,
            "licenseState": quick_pd.plate_state if quick_pd else None,
            "licensePlate": quick_pd.plate_num if quick_pd else None,
            "firstName": person.first_name if person else None,
            "lastName": person.last_name if person else None,
            "capturedDate": (
                citation.captured_date.strftime("%B %#d, %Y")
                if citation.captured_date
                else None
            ),
        }
        data.append(record)

    return {
        "pageIndex": page_index,
        "pageSize": page_size,
        "total_records": total_records,
        "hasNextPage": (page_index * page_size) < total_records,
        "hasPreviousPage": page_index > 1,
        "data": data,
    }


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


template = get_template("pdf_final.html")
template_maryland = get_template("maryland-pdf.html")
template_kersey = get_template("kersey-pdf.html")
template_hud_c = get_template("hudson-pdf.html")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
options = {
    "page-size": "Letter",
    "enable-local-file-access": "",
    "load-error-handling": "ignore",
    "load-media-error-handling": "ignore",
    "no-stop-slow-scripts": "",
    "javascript-delay": "3000", 
    "debug-javascript": "", 
}


def create_pdf(filename, data, station_name):
    try:
        if station_name in ["FED-M", "HUD"]:
            html = template_maryland.render(data)
        elif station_name in ["KRSY-C"]:
            html = template_kersey.render(data)
        elif station_name in ["HUD-C"]:
            html = template_hud_c.render(data)
        else:
            html = template.render(data)

        location = os.path.join(BASE_DIR, "media", filename)
        pdfkit.from_string(html, location, configuration=config, options=options)

        with open(location, "rb") as pdf_file:
            upload_to_s3(pdf_file, filename, "pdfs")

    except OSError as e:
        print(f"wkhtmltopdf error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise
    finally:
        if location and os.path.exists(location):
            os.remove(location)


def citation_data_for_mail_center_pdf(station_id="", station_name="", citationID="", base64String=""):

    citation_data = Citation.objects.filter(
        citationID=citationID, station_id=station_id
    ).first()
    if not citation_data:
        return None
    citation_version =  get_latest_version_number(citation_data)
    version_data = get_snapshot_by_version(citation_data, citation_version)
    if not version_data:
        return Response({
            "statusCode": 404,
            "message": "Version not found"
        }, status=404)

    snapshot = version_data["snapshot"]
    status = snapshot.get("status")

    if citation_data.video_id:
        data = get_cit_refactor(
            citationID, station_id, status, image_flow=False, is_tattile=False
        )
    elif citation_data.image_id:
        data = get_cit_refactor(
            citationID, station_id, status, image_flow=True, is_tattile=False
        )
        
    elif citation_data.tattile_id:
        data = get_cit_refactor(
            citationID, station_id, status, image_flow=False, is_tattile=True
        )

    data = patch_pdf_data_from_snapshot(data, snapshot)
    filename = f"{citationID}_mail_center.pdf"
    create_pdf(filename, data, station_name)
    get_pdf_base64(filename)
    base64String = get_pdf_base64(filename)
    return base64String


# updated approach for generating pdfs and csvs for agencies
def create_csv_and_pdf_data_for_agencies(citationid,date_type,target_date=None, max_workers=10):
    """
    Generate PDFs and CSVs for all approved citations across all stations for a given date.
    Parallelized using ThreadPoolExecutor for faster processing.
    """
    if target_date is None:
        target_date = datetime.now()
    print(f"Starting PDF & CSV generation for {target_date}...")

    # Keep last 20 seconds
    start_dt = target_date - timedelta(seconds=20)
    end_dt = target_date

    print("Filtering records between:")
    print("START:", start_dt)
    print("END  :", end_dt)

    approved_citations = sup_metadata.objects.filter(
        isMailCitationApproved=True,
        mailCitationApprovedTime__gte=start_dt,
        mailCitationApprovedTime__lte=end_dt,
    ).select_related("station", "citation")

    if not approved_citations.exists():
        print(f" No approved citations found for {target_date}.")
        return
    print(f" Found {approved_citations.count()} approved citations.")
    station_ids = approved_citations.values_list("station_id", flat=True).distinct()
    for station_id in station_ids:
        station_obj = Station.objects.filter(id=station_id).first()
        if not station_obj:
            continue

        station_name = station_obj.name
        station_citations = approved_citations.filter(station_id=station_id)

        print(
            f"Processing {station_citations.count()} citations for station: {station_name}"
        )
        batches = defaultdict(list)
        # ADD TIMEAPP BATCHING HERE (THIS IS THE ONLY CHANGE)
        for meta in station_citations:
            if meta.timeApp:
                batch_date = meta.timeApp.date()
                batches[batch_date].append(meta)
        #  Now process each timeApp batch exactly like before
        for batch_date, batch_citations in batches.items():
            print(
                f"\n Batch (timeApp): {batch_date} - {len(batch_citations)} citations"
            )
            #  Thread pool for PDFs
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_citation = {
                    executor.submit(
                        process_single_pdf, meta, station_id, station_name, batch_date,date_type
                    ): meta
                    for meta in batch_citations
                }

                for future in as_completed(future_to_citation):
                    meta = future_to_citation[future]
                    try:
                        future.result()
                    except Exception as e:
                        print(
                            f" Error processing citation {meta.citation.citationID}: {e}"
                        )

            #  Generate CSV after all PDFs are complete
            try:
                create_mail_center_csv(station_id, citationid,batch_date,date_type)
                print(f"CSV file generated for station: {station_name}")
            except Exception as e:
                print(f"Failed to generate CSV for station {station_name}: {e}")
            try:
                send_to_sftp_mail_center_review(station_id=station_id, batch_date = batch_date,date_type=date_type)
            except Exception as e:
                print(f"Failed to generate CSV for station {station_name}: {e}")
            try:
                agency_data = Agency.objects.get(station_id = station_id)
                email_to = agency_data.emails
                dist_smtp_mail_center_review(email_to, station_name, batch_date,station_id,date_type)
            except Exception as e:
                print(f"Failed to generate CSV for station {station_name}: {e}")

    print(f" PDF & CSV generation completed for {target_date}")

def create_mail_center_csv(stationId,citationid,batch_date, date_type):
    
    if isinstance(batch_date, str):
        converted = datetime.strptime(batch_date, "%m%d%Y").date()
    elif isinstance(batch_date, datetime):
        converted = batch_date.date()
    elif isinstance(batch_date, date):
        converted = batch_date
    else:
        raise ValueError(f"Invalid batch_date type: {type(batch_date)}")
    sup_data = Citation.objects.filter(id__in = citationid).values_list('citationID', flat=True)
    quick_pd_data_check = QuickPD.objects.filter(ticket_num__in=sup_data).values_list('id', flat=True)
    csv_metadata_check = csv_metadata.objects.filter(date__date=converted, station_id=stationId, quickPD_id__in=quick_pd_data_check)
        
        
    meta = list(csv_metadata_check.values_list('quickPD_id', flat=True))
    station_data = Station.objects.filter(id=stationId).values('name').first()
    citations = []

    cols = [
        "offense_date", "offense_time", "ticket_num", "first_name", "middle",
        "last_name", "generation", "address", "city", "state", "zip", "dob",
        "race", "sex", "height", "weight", "ssn", "dl", "dl_state", "accident",
        "comm", "vehder", "arraignment_date", "actual_speed", "posted_speed",
        "officer_badge", "street1_id", "street2_id", "street1_name",
        "street2_name", "bac", "test_type", "plate_num", "plate_state", "vin",
        "phone_number", "radar", "state_rs1", "state_rs2", "state_rs3",
        "state_rs4", "state_rs5", "warning", "notes", "dl_class",
    ]

    quickpd_map = {
        row["id"]: row 
        for row in QuickPD.objects.filter(id__in=meta).values()
    }
    
    for qpd_id in meta:
        data = quickpd_map.get(qpd_id)
        if data:
            citations.append(data)

    if not citations:
        print(f"[Scheduler] ⚠️ No citation data found for station {stationId} on {batch_date}.")
        return

    data_frame = pd.DataFrame(data=citations)
    valid_cols = [c for c in cols if c in data_frame.columns]
    formatted_date =converted.strftime("%m%d%Y")
    if date_type == 1:
        file_name = f"{station_data.get('name')}-Citations-{formatted_date}.csv"
    else:
        file_name = f"Edited-{station_data.get('name')}-Citations-{formatted_date}.csv"
    file_path = os.path.join(BASE_DIR, "media", file_name)

    data_frame.to_csv(
        file_path,
        index=False,
        header=False,
        columns=valid_cols,
    )

    with open(file_path, "rb") as csv_file:
        upload_to_s3(csv_file, file_name, "csvs")
        os.remove(file_path)

    print(f"[Scheduler] ✅ CSV {file_name} uploaded to S3 successfully.")

def process_single_pdf(meta, station_id, station_name, batch_date,date_type):
    """
    Generates PDF for a single citation.
    Runs inside a thread.
    """
    citation = meta.citation
    citation_id = str(citation.citationID)
    citation_version = get_latest_version_number(citation)
    version_data = get_snapshot_by_version(citation, citation_version)
    if not version_data:
        return Response({
            "statusCode": 404,
            "message": "Version not found"
        }, status=404)

    snapshot = version_data["snapshot"]
    status = snapshot.get("status")
    try:
        if citation.video_id:
            data = get_cit_refactor(
                citation_id, station_id, status,image_flow=False, is_tattile=False
            )
        elif citation.image_id:
            data = get_cit_refactor(
                citation_id, station_id, status, image_flow=True, is_tattile=False
            )
        elif citation.tattile_id:
            data = get_cit_refactor(
                citation_id, station_id,status, image_flow=False, is_tattile=True
            )
        else:
            print(f"Citation {citation_id} has no media reference. Skipping.")
            return

        filename = f"{citation_id}.pdf"
        data = patch_pdf_data_from_snapshot(data, snapshot)
        result = save_pdf(filename, station_name, data,date_type)

        if result:
            print(f" PDF generated for citation {citation_id} ({station_name})")
        else:
            print(f" PDF generation failed for citation {citation_id} ({station_name})")

    except Exception as e:
        print(f" Error generating PDF for citation {citation_id}: {e}")


def create_refactor_csv(
    stationId, batch_citations, station_name, batch_date, target_date=None
):
    print("Generating CSV...")
    if target_date is None:
        target_date = datetime.now()

    test_now = target_date.strftime("%m%d%Y")  
    citations = []

    cols = [
        "offense_date",
        "offense_time",
        "ticket_num",
        "first_name",
        "middle",
        "last_name",
        "generation",
        "address",
        "city",
        "state",
        "zip",
        "dob",
        "race",
        "sex",
        "height",
        "weight",
        "ssn",
        "dl",
        "dl_state",
        "accident",
        "comm",
        "vehder",
        "arraignment_date",
        "actual_speed",
        "posted_speed",
        "officer_badge",
        "street1_id",
        "street2_id",
        "street1_name",
        "street2_name",
        "bac",
        "test_type",
        "plate_num",
        "plate_state",
        "vin",
        "phone_number",
        "radar",
        "state_rs1",
        "state_rs2",
        "state_rs3",
        "state_rs4",
        "state_rs5",
        "warning",
        "notes",
        "dl_class",
    ]

    for meta in batch_citations:
        citation = meta.citation
        citationID = str(citation.citationID)
        print(citationID,"Citaiton ID Check")
        data = QuickPD.objects.filter(ticket_num=citationID).values().first()
        if data:
            citations.append(data)

    if not citations:
        print(f"No citation data found for station {stationId} on {target_date}.")
        return
    print(data, "quickPD data")
    data_frame = pd.DataFrame(data=citations)
    valid_cols = [c for c in cols if c in data_frame.columns]
    csv_path_new = os.path.join(TEMP_CSV_DIR,station_name)
    directory = csv_path_new
    print('Here testing for data 2')
    # Ensure directory exists
    if not os.path.exists(csv_path_new):
        os.makedirs(directory, exist_ok=True)
    file_batch_date =  batch_date.strftime("%m%d%Y")
    file_name = f"{station_name}_Citations_{file_batch_date}.csv"
    file_path = os.path.join(directory, file_name)
    data_frame.to_csv(
        file_path,
        index=False,
        header=False,
        columns=valid_cols,
    )
    print('Here testing for data 3')
    with open(file_path, "rb") as csv_file:
        current_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_file_name = f"{station_name}_batch_{batch_date}_{current_date_time}.csv"
        upload_to_s3(csv_file, s3_file_name, "csvs")


def send_to_sftp_mail_center_review(station_id: int, batch_date, date_type):
    """
    Send generated PDFs and CSVs to SFTP for Mail Center Review.
    """
    print(f"Sending files to SFTP for station ID: {station_id}...")
    # Implement SFTP transfer logic here
    try:
        current_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        print("current_date_time", current_date_time)
        agency = Agency.objects.filter(station_id=station_id).first()
        station = Station.objects.filter(id=station_id).values().first()
        fine = (
            Fine.objects.filter(station_id=station["id"])
            .values_list("fine", flat=True)
            .first()
        )
        issuing_agency = agency.name
        if date_type == 1:
            pdf_path = os.path.isdir(os.path.join(TEMP_PDF_DIR, station["name"],"Original"))
            list_pdf_file = os.listdir(os.path.join(TEMP_PDF_DIR, station["name"],"Original"))
        else:
            pdf_path = os.path.isdir(os.path.join(TEMP_PDF_DIR, station["name"],"Edited"))
            list_pdf_file = os.listdir(os.path.join(TEMP_PDF_DIR, station["name"],"Edited"))
        if pdf_path:
            if any(file.endswith(".pdf") for file in list_pdf_file):
                try:
                    zip_loc = zip_pdfs_mail_center_review(station["name"], batch_date,date_type)
                    logging.info(f"PDF zipped for {station['name']}")
                    print("zip_loc", zip_loc)
                except Exception as e:
                    logging.error(f"An error occurred for {station['name']} reason {e}")
            else:
                print("No PDFs found")
    except Exception as e:
        print(f"Failed to send files to SFTP for station ID {station_id}: {e}")


#     return zip_location
def dist_sftp_mail_center_review(
    zip_location, station, isXpressPay, fine, issuing_agency, current_date_time, batch_date):
    print("Inside dist_sftp_mail_center_review function")
    print("station", station)
    print("fine", fine)
    print("zip_location", zip_location)
    formatted_batch_date =batch_date.strftime("%m%d%Y")
    transport = None
    sftp = None
    # SFTP
    sftp_host = ENV_CONFIG("SFTP_HOST")
    sftp_port = int(ENV_CONFIG("SFTP_PORT"))
    sftp_username = ENV_CONFIG("SFTP_USERNAME")
    sftp_password = ENV_CONFIG("SFTP_PASSWORD")
    sftp_remote_dir = ENV_CONFIG("SFTP_REMOTE_DIR")

    sftp_xpress_host = ENV_CONFIG("SFTP_HOST_XPRESS_HOST")
    sftp_xpress_port = int(ENV_CONFIG("SFTP_PORT_XPRESS_PORT"))
    sftp_xpress_remote_dir = ENV_CONFIG("SFTP_REMOTE_DIR_XPRESS")

    max_retries = 3
    retry_delay = 2
    attempts = 0

    if station == "FED-M":
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_FED-M")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_FED-M")
    elif station == "WBR2":
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_WBR2")
        sftp_xpress_password = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_WBR2")
    elif station == "HUD-C":
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_HUD-C")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_HUD-C")
    elif station == "FPLY-C":
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_FPLY-C")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_FPLY-C")
    elif station == "KRSY-C":
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_KRSY-C")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_KRSY-C")
    elif station == "AULT":
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_AULT")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_AULT")
    elif station == "WALS":
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_WALS")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_WALS")
    print("before while loop for xpresspay sftp")

    while attempts < max_retries:
        print("entered into while loop for xpresspay sftp")
        try:
            if isXpressPay and station in [
                "FED-M",
                "WBR2",
                "HUD-C",
                "FPLY-C",
                "KRSY-C",
                "AULT",
                "WALS",
            ]:
                file_station = "WBR" if station == "WBR2" else station
                print("TEMP_CSV_DIR", TEMP_CSV_DIR)
                temp_csv_dir=os.path.join(TEMP_CSV_DIR,station)
                csv_file_name = f"{station}_Citations_{formatted_batch_date}.csv"
                original_csv_path = os.path.join(temp_csv_dir, csv_file_name)

                print("Using CSV:", original_csv_path)

                # Run xpress_csv on this file
                xpress_csv(original_csv_path, fine, issuing_agency)
                print(f"CSV processed: {csv_file_name}")

                distribution_code = 101 if station == "FED-M" else 1002
                # Create directories like PDF style
                station_zip_path = os.path.join(TEMP_CSV_DIR, file_station)
                os.makedirs(station_zip_path, exist_ok=True)
                # ZIP name same style as PDF
                zip_filename = f"{file_station}-Citations{distribution_code}-{formatted_batch_date}.zip"
                zip_full_path = os.path.join(station_zip_path, zip_filename)
                # TXT filename = original CSV name
                txt_name = csv_file_name.replace(".csv", ".txt")
                txt_path = os.path.join(station_zip_path, txt_name)
                shutil.copyfile(original_csv_path, txt_path)

                # ZIP must contain ORIGINAL CSV NAME
                print("Zipping to:", zip_full_path)

                # ZIP must contain the TXT file (not CSV)
                with zipfile.ZipFile(zip_full_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(txt_path, os.path.basename(txt_path))
                print("Generated ZIP:", zip_full_path)
                # ---- Upload via SFTP ----
                try:
                    print("Attempting to upload via SFTP...")

                    sftp = FipsSftpClient(
                        hostname=sftp_xpress_host,
                        port=sftp_xpress_port,
                        username=sftp_xpress_username,
                        password=sftp_xpress_password,
                    )

                    sftp.connect()

                    local_path = zip_full_path
                    remote_path = sftp_xpress_remote_dir + "/" + zip_filename

                    sftp.upload_file(local_path, remote_path)
                    print(f"Uploaded {zip_filename} successfully.")

                    sftp.disconnect()
                    break

                except Exception as e:
                    print(f"Failed to upload {zip_filename}. Error: {e}")
                    logging.error(f"Upload failed for {station} reason {e}")

                    attempts += 1
                    if attempts >= max_retries:
                        print("Max retries reached. Upload failed.")
                        return -1

                    time.sleep(retry_delay)

            else:
                print("Station not valid for XpressPay or isXpressPay is False.")
                break

        except Exception as e:
            attempts += 1
            print(f"Attempt {attempts} failed. Error: {e}")
            logging.error(f"An error occurred for {station} reason {e}")

            if attempts >= max_retries:
                print("Max retries reached. Upload failed.")
                return -1

        time.sleep(retry_delay)
    # SFTP files
    try:
        # print("Starting SFTP transfer...")
        # transport = paramiko.Transport((sftp_host, sftp_port))
        # print("Transport created")
        # transport.connect(username=sftp_username, password=sftp_password)
        # print("Transport connected")
        # sftp = paramiko.SFTPClient.from_transport(transport)
        # print("SFTP client created")
        sftp = FipsSftpClient(
                        hostname=sftp_host,
                        port=sftp_port,
                        username=sftp_username,
                        password=sftp_password,
                    )

        sftp.connect()
        # with open(zip_location, "rb") as file:
        if zip_location:
            print(f"Uploading {zip_location} to SFTP...")
            file_name = os.path.basename(zip_location)
            dir_path = sftp_remote_dir 
            remote_path = dir_path + "/" + file_name
            sftp.upload_file(zip_location, remote_path)
            print(f"{file_name} uploaded successfully!")

        # Close connection
        if sftp:
            sftp.disconnect()
        # if transport:
        #     transport.disconnect()
        return 0 
    except Exception as e:
        print(f"Failed to upload {file_name}.")
        print(f"Error: {e}")

        # Close connection
        if sftp:
            sftp.disconnect()
        # if transport:
        #     transport.disconnect()
        return -1 




def is_valid_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            reader.pages[0]
        return True
    except (ValueError, TypeError, Exception) as e:
        return False
    
def zip_files_with_validation(zip_name, source_pdfs, wait_time):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(source_pdfs):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                if is_valid_pdf(file_path):
                    zipf.write(file_path, os.path.relpath(file_path, source_pdfs))
            
            # Reduce resource usage with a small delay
            if wait_time > 0:
                time.sleep(wait_time)

def zip_pdfs_mail_center_review(station, current_date, date_type):
    source_pdfs = os.path.join(TEMP_PDF_DIR, station)
    zip_dest = TEMP_ZIP_DIR
    formatted_date =current_date.strftime("%m%d%Y")
    # Define zip name
    if date_type == 1:
        zip_name = os.path.join(zip_dest, station, f"{station}-batch-{formatted_date}.zip")
        source_pdfs = os.path.join(TEMP_PDF_DIR, station,"Original")
    else:
        zip_name = os.path.join(zip_dest, station, f"Edited-{station}-batch-{formatted_date}.zip")
        source_pdfs = os.path.join(TEMP_PDF_DIR, station,"Edited")
    zip_path = os.path.join(zip_dest, station)
    if not os.path.exists(zip_path):
        os.makedirs(zip_path)

    # Zip pdfs
    print(f"Zipping {station}-batch-{current_date}.zip...")
    # shutil.make_archive(zip_name, "zip", source_pdfs)   
    zip_files_with_validation(zip_name, source_pdfs, wait_time =0)

    # Define zip location
    zip_location = zip_name

    # If pdfs were successfully zipped, delete pdfs
    if os.path.exists(zip_location):
        for file_name in os.listdir(source_pdfs):
            if file_name.endswith(".pdf"):
                file_path = os.path.join(source_pdfs, file_name)
                os.remove(file_path)
        print("PDF files deleted.")

    try:
        sftp_host = ENV_CONFIG("SFTP_HOST")
        sftp_port = int(ENV_CONFIG("SFTP_PORT"))
        sftp_username = ENV_CONFIG("SFTP_USERNAME")
        sftp_password = ENV_CONFIG("SFTP_PASSWORD")
        sftp_remote_dir = ENV_CONFIG("SFTP_REMOTE_DIR")
        
        sftp = FipsSftpClient(
                        hostname=sftp_host,
                        port=sftp_port,
                        username=sftp_username,
                        password=sftp_password,
                    )
        if zip_location:
            sftp.connect()
            print(f"Uploading {zip_location} to SFTP...")
            file_name = os.path.basename(zip_location)
            dir_path = sftp_remote_dir
            remote_path = dir_path + "/" + file_name
            sftp.upload_file(zip_location, remote_path)
            print(f"{file_name} uploaded successfully!")

        # Close connection
        if sftp:
            sftp.disconnect()
        return zip_location 
    
    except Exception as e:
        print(f"Failed to upload {file_name}.")
        print(f"Error: {e}")
        # Close connection
        if sftp:
            sftp.disconnect()
        return -1 