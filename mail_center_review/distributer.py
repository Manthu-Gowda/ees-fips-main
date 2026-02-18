import os
import csv
import smtplib
from decouple import config as ENV_CONFIG
from video.models import Citation
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import defaultdict
from ees.utils import s3_download_file
from video.SESClient import SESClient

TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
TEMP_ZIP_DIR = ENV_CONFIG("TEMP_ZIP_DIR")
TEMP_CSV_DIR = ENV_CONFIG("TEMP_CSV_DIR")
TEMP_PRE_ODR_FIRST_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_FIRST_MAILER_PDFS")
TEMP_ZIP_PRE_ODR_FIRST_MAILER_PDFS= ENV_CONFIG("TEMP_ZIP_PRE_ODR_FIRST_MAILER_PDFS")
TEMP_PRE_ODR_SECOND_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_SECOND_MAILER_PDFS")
TEMP_ZIP_PRE_ODR_SECOND_MAILER_PDFS = ENV_CONFIG("TEMP_ZIP_PRE_ODR_SECOND_MAILER_PDFS")
TEMP_PRE_ODR__FIRST_MAILER_CSVS_DIR="/Users/EM/Documents/pre_odr_first_mailer_csvs"

def dist_smtp_mail_center_review(email_to, station, current_date,station_id,date_type):
    source_csvs = os.path.join(TEMP_CSV_DIR, station)

    if not os.path.exists(source_csvs):
        os.makedirs(source_csvs)

    email_cc = ENV_CONFIG("SMTP_EMAIL_CC")

    # Look for file with current date in name
    formatted_date =current_date.strftime("%m%d%Y")
    if date_type == 1:
        csv_location_or = os.path.join(source_csvs, f"{station}-Citations-{formatted_date}.csv")
        csv_name = f"{station}-Citations-{formatted_date}.csv"
        email_subject = f"EES CSV {station}-Citations-{formatted_date}"
    else:
        csv_name = f"Edited-{station}-Citations-{formatted_date}.csv"
        csv_location_edited = os.path.join(source_csvs, f"Edited-{station}-Citations-{formatted_date}.csv")
        email_subject = f"EES CSV Edited {station}-Citations-{formatted_date}"
        
    csv_location = os.path.join(source_csvs, csv_name)
    
    has_csv_today = s3_download_file(csv_name, "csvs", source_csvs)
    
    or_rows = []
    edited_rows = []

    CITATION_ID_INDEX = 2 if station != 'FED-M' else 3

    all_rows = []
    with open(csv_location, "r") as file:
        reader = csv.reader(file)
        all_rows = list(reader) 
        citation_ids = [row[CITATION_ID_INDEX].strip() for row in all_rows]

    # Step 2: bulk query DB
    citations_qs = Citation.objects.filter(citationID__in=citation_ids).only("citationID", "current_citation_status")
    status_lookup = {c.citationID: c.current_citation_status for c in citations_qs}

    # Step 3: split rows using lookup
    for row in all_rows:
        citation_id = row[CITATION_ID_INDEX].strip()
        status = status_lookup.get(citation_id)
        if status == "OR":
            or_rows.append(row)
        elif status:  # found in DB but not OR
            edited_rows.append(row)
        else:
            print(f"Warning: Citation ID {citation_id} not found in DB.")

    email_body = "Please find the CSV file attached."
    if has_csv_today:
        try:
            fips_ses_client = SESClient()
            to_email = email_to
            cc_email = email_cc

            if date_type == 1:
                fips_ses_client.send_email_with_attachment(
                    subject=email_subject,
                    body=email_body,
                    to_addresses=to_email.split(","),
                    cc_addresses=cc_email.split(","),
                    attachment_path=csv_location_or,
                )
            if date_type == 2:
                if station in ['HUD-C', 'FPLY-C', 'KRSY-C','WBR2']:
                    with open(csv_location_edited, "r", newline='', encoding="utf-8") as csvfile:
                        reader = csv.reader(csvfile)
                        lines = list(reader)

                    if len(lines) >= 1:
                        fips_ses_client.send_email_with_attachment(
                            subject=email_subject,
                            body=email_body,
                            to_addresses=to_email.split(","),
                            cc_addresses=cc_email.split(","),
                            attachment_path=csv_location_edited,
                        )
                        
        except Exception as email_err:
            print(f"Error sending primary CSV email: {email_err}")
            
        return 0
    
    else:
        print(f"Citations-{current_date}.csv not found.")
        return -1