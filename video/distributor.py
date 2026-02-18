import os
import shutil
import smtplib
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import zipfile
import csv
from collections import defaultdict
from .utils import format_csv,xpress_csv, xpress_csv_pre_odr
from video.models import Citation
# import pysftp
import paramiko
from decouple import config as ENV_CONFIG
from PyPDF2 import PdfReader
import time
from zipfile import ZipFile, ZIP_DEFLATED
from ees.utils import s3_download_file
import logging

from datetime import timedelta
from django.db.models import F
from django.db.models.functions import Cast, TruncDate
from django.db.models import TimeField, DateField
from .models import Citation, sup_metadata
from django.db.models.functions import TruncSecond
from .SESClient import SESClient
from .FipsSftpClient import FipsSftpClient

TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
TEMP_ZIP_DIR = ENV_CONFIG("TEMP_ZIP_DIR")
TEMP_CSV_DIR = ENV_CONFIG("TEMP_CSV_DIR")
TEMP_PRE_ODR_FIRST_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_FIRST_MAILER_PDFS")
TEMP_ZIP_PRE_ODR_FIRST_MAILER_PDFS= ENV_CONFIG("TEMP_ZIP_PRE_ODR_FIRST_MAILER_PDFS")
TEMP_PRE_ODR_SECOND_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_SECOND_MAILER_PDFS")
TEMP_ZIP_PRE_ODR_SECOND_MAILER_PDFS = ENV_CONFIG("TEMP_ZIP_PRE_ODR_SECOND_MAILER_PDFS")
TEMP_PRE_ODR__FIRST_MAILER_CSVS_DIR="/Users/EM/Documents/pre_odr_first_mailer_csvs"

# Define zip location
# zip_location = "/home/ethanmanco/Documents/Coding/EES_SAVED/test.txt" # Returned from zip_pdfs()
# Define station
station = "EST"

# Define folders/filenames
source_pdfs = TEMP_PDF_DIR
zip_dest = TEMP_ZIP_DIR

# Define folder
source_csvs = TEMP_CSV_DIR

# SMTP dynamic info
# email_to = 'mailto:estherwoodpd@yahoo.com, mailto:erin@quickpd.com, mailto:dbertrand2020@yahoo.com'

def is_valid_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            reader = PdfReader(f)
            reader.pages[0]
        return True
    except (ValueError, TypeError, Exception) as e:
        return False
    
def zip_files_with_validation(zip_name, source_pdfs, wait_time):
    with ZipFile(zip_name, 'w', ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(source_pdfs):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                if is_valid_pdf(file_path):
                    zipf.write(file_path, os.path.relpath(file_path, source_pdfs))
            
            # Reduce resource usage with a small delay
            if wait_time > 0:
                time.sleep(wait_time)

def zip_pdfs(station, current_date):
    source_pdfs = os.path.join(TEMP_PDF_DIR, station)
    zip_dest = TEMP_ZIP_DIR
    formatted_date = current_date
    # Define zip name
    zip_name = os.path.join(zip_dest, station, f"{station}-batch-{formatted_date}.zip")
    zip_path = os.path.join(zip_dest, station)
    if not os.path.exists(zip_path):
        os.makedirs(zip_path)

    # Zip pdfs
    print(f"Zipping {station}-batch-{formatted_date}.zip...")
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

    return zip_location


# zip_pdfs(source_pdfs, zip_dest, station)

def write_csv_no_header(data, path):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(data)

def dist_smtp(email_to, station, current_date,station_id, fine, issuing_agency):
    source_csvs = os.path.join(TEMP_CSV_DIR, station)

    if not os.path.exists(source_csvs):
        os.makedirs(source_csvs)

    # SMTP static info
    email_cc = ENV_CONFIG("SMTP_EMAIL_CC")
    email_subject = f"EES CSV {station}-Citations-{current_date}"
    # Look for file with current date in name
    csv_name = f"{station}-Citations-{current_date}.csv"
    csv_location = os.path.join(source_csvs, csv_name)

    has_csv_today = s3_download_file(csv_name, "csvs", source_csvs)
    
    or_rows = []
    edited_rows = []

    CITATION_ID_INDEX = 2 if station != 'FED-M' else 3

    # Step 1: collect all citation IDs from CSV
    if not has_csv_today:
        print(f"Citations-{current_date}.csv not found in S3 bucket.")
        return -1
    all_rows = []
    with open(csv_location, "r") as file:
        reader = csv.reader(file)
        all_rows = list(reader)  # store full rows for second pass
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
            # Optional: edited_rows.append(row)

    # Step 4: write CSVs
    csv_location_or = os.path.join(source_csvs, f"{station}-Citations-{current_date}.csv")
    csv_location_edited = os.path.join(source_csvs, f"Edited-{station}-Citations-{current_date}.csv")

    write_csv_no_header(or_rows, csv_location_or)
    write_csv_no_header(edited_rows, csv_location_edited)
    
    if station == 'MOR-C':
        format_csv(csv_location_or)
        format_csv(csv_location_edited)
        email_body = "Please upload to Caselle and Xpress Bill Pay. Thank you"
    elif station == 'FED-M':
        xpress_csv(csv_location_or, fine, issuing_agency)
        xpress_csv(csv_location_edited, fine, issuing_agency)
        email_body = "Please upload to Xpress Bill Pay. Thank you"
    else:
        email_body = "Please find the CSV file attached."
    

    if has_csv_today:
        try:
            print(f"Sending {station}-Citations-{current_date}.csv")

            fips_ses_client = SESClient()
            attachments = []

            # ORIGINAL CSV
            if os.path.exists(csv_location_or):
                with open(csv_location_or, "r", encoding="utf-8") as f:
                    if sum(1 for _ in f) >= 1:  # header + data
                        attachments.append(csv_location_or)

            # EDITED CSV (station specific)
            if station in ['HUD-C', 'FPLY-C', 'KRSY-C', 'WBR2'] and os.path.exists(csv_location_edited):
                with open(csv_location_edited, "r", encoding="utf-8") as f:
                    if sum(1 for _ in f) >= 1:
                        attachments.append(csv_location_edited)

            # Send ONLY if something exists
            if attachments:
                fips_ses_client.send_email_with_attachment(
                    subject=email_subject,
                    body=email_body,
                    to_addresses=email_to.split(","),
                    cc_addresses=email_cc.split(","),
                    attachment_path=attachments,
                )    
        except Exception as email_err:
            print(f"Error sending primary CSV email: {email_err}")
        
        # Duplicate detection
        try:
            get_duplicate_tattile_records(current_date, station, station_id=station_id)
            
        except Exception as dup_err:
            print(f"Error processing duplicate data: {dup_err}")
            return -1
        
        return 0 

    else:
        print(f"Citations-{current_date}.csv not found.")
        return -1


def dist_sftp(station, isXpressPay, fine, issuing_agency, current_date):
    from .tasks import logging
    sftp_xpress_host = ENV_CONFIG("SFTP_HOST_XPRESS_HOST")
    sftp_xpress_port = int(ENV_CONFIG("SFTP_PORT_XPRESS_PORT"))
    sftp_xpress_remote_dir = ENV_CONFIG("SFTP_REMOTE_DIR_XPRESS")

    max_retries = 3
    retry_delay = 2
    attempts = 0

    if station == 'FED-M':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_FED-M")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_FED-M")
    elif station == 'WBR2':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_WBR2")
        sftp_xpress_password = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_WBR2")
    elif station == 'HUD-C':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_HUD-C")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_HUD-C")
    elif station == 'FPLY-C':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_FPLY-C")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_FPLY-C")
    elif station == 'KRSY-C':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_KRSY-C")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_KRSY-C")
    elif station == 'AULT':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_AULT")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_AULT")
    elif station == 'WALS':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_WALS")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_WALS")
    else:
        sftp_xpress_username = None
        sftp_xpress_password = None


    if sftp_xpress_username and sftp_xpress_password:
        fips_sftp_client = None
        fips_sftp_client = FipsSftpClient(sftp_xpress_host, sftp_xpress_port, sftp_xpress_username, sftp_xpress_password)
        fips_sftp_client.connect()
        while attempts < max_retries:
            try:
                if isXpressPay and station in ['FED-M', 'WBR2', 'HUD-C', 'FPLY-C', 'KRSY-C','AULT', 'WALS']:
                    file_station = 'WBR' if station == 'WBR2' else station
                    source_csvs = os.path.join(TEMP_CSV_DIR, station)
                    if not os.path.exists(source_csvs):
                        os.makedirs(source_csvs)

                    distribution_code = 101 if station == 'FED-M' else 1002
                    csv_name = f"{file_station}-Citations-{current_date}.csv"
                    csv_location = os.path.join(source_csvs, csv_name)
                    logging.info(f"{csv_location} - inside csv location")

                    has_csv_today = s3_download_file(csv_name, "csvs", source_csvs)
                    xpress_csv(csv_location, fine, issuing_agency)

                    zip_name = f"{file_station}-Citations{distribution_code}-{current_date}.zip"
                    new_csv = f"{file_station}-Citations{distribution_code}-{current_date}.txt"
                    csv_zip_location = os.path.join(source_csvs, zip_name)
                    new_csv_location = os.path.join(source_csvs, new_csv)

                    shutil.copyfile(csv_location, new_csv_location)

                    with zipfile.ZipFile(csv_zip_location, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(new_csv_location, os.path.basename(new_csv_location))
                        logging.info(f"{csv_name} zipped as {zip_name}")

                    
                    remote_path = sftp_xpress_remote_dir + '/' + zip_name
                    try:
                        fips_sftp_client.upload_file(csv_zip_location, remote_path)
                        fips_sftp_client.disconnect()
                        logging.info(f"Uploaded {zip_name} successfully.")
                        break
                    except Exception as e:
                        logging.info(f"Failed to upload {zip_name}.")
                        logging.info(f"Error: {e}")
                        attempts += 1
                        logging.error(f'An error occurred for {station} reason {e}')
                        
                        if attempts >= max_retries:
                            logging.info("Max retries reached. Upload failed.")
                            return -1

                        time.sleep(retry_delay)  

                else:
                    logging.info("Station not valid for XpressPay or isXpressPay is False.")
                    break  

            except Exception as e:
                attempts += 1
                logging.info(f"Attempt {attempts} failed to upload {csv_zip_location}.")
                logging.info(f"Error: {e}")
                logging.error(f'An error occurred for {station} reason {e}')
                
                if attempts >= max_retries:
                    logging.info("Max retries reached. Upload failed.")
                    return -1
                time.sleep(retry_delay)


        if fips_sftp_client:
            fips_sftp_client.disconnect()
        
        return -1  # Return -1 for failure

    else:
        from .tasks import logging
        logging.info(f"sftp credentials not found for station {station}")

# def send_email_with_attachment(subject, body, attachment_path, to_email, cc_emails):
#     ses_client = SESClient()
#     ses_client.send_email_with_attachment(
#         subject=subject,
#         body=body, 
#         to_addresses=to_email, 
#         cc_addresses=cc_emails, 
#         attachment_path=attachment_path
#     )
    # # Set up the MIME
    # msg = MIMEMultipart()
    # msg['From'] = from_email
    # msg['To'] = to_email
    # msg['Cc'] = cc_emails
    # msg['Subject'] = subject

    # # Add body to the email
    # msg.attach(MIMEText(body, 'plain'))

    # # Attach the file
    # with open(attachment_path, "rb") as attachment:
    #     part = MIMEBase("application", "octet-stream")
    #     part.set_payload(attachment.read())
    #     encoders.encode_base64(part)
    #     part.add_header(
    #         "Content-Disposition",
    #         f"attachment; filename= {os.path.basename(attachment_path)}",
    #     )
    #     msg.attach(part)

    # # Convert message to string and send the email
    # try:
    #     server = smtplib.SMTP(smtp_host, smtp_port)
    #     server.starttls()
    #     server.login(smtp_username, smtp_password)
    #     server.sendmail(from_email, [to_email] + cc_emails.split(','), msg.as_string())
    #     server.quit()
    #     print("Email sent successfully")
    # except Exception as e:
    #     print(f"Failed to send email: {str(e)}")

# dist_smtp(source_csvs, email_to, station)
# dist_sftp(zip_location, station)

def zip_files_with_validation_for_first_mailer(zip_first_mailer_name, source_first_mailer_pdfs, wait_time):
    with ZipFile(zip_first_mailer_name, 'w', ZIP_DEFLATED) as zipf:
        for foldername, subfolders, filenames in os.walk(source_first_mailer_pdfs):
            for filename in filenames:
                file_path = os.path.join(foldername, filename)
                if is_valid_pdf(file_path):
                    zipf.write(file_path, os.path.relpath(file_path, source_first_mailer_pdfs))
            
            # Reduce resource usage with a small delay
            if wait_time > 0:
                time.sleep(wait_time)

def zip_first_mailer_pdfs(station, current_date):
    # Get current date in MMDDYYYY format
    # current_date = datetime.now()
    # current_date = current_date.strftime("%m%d%Y")

    print(235)
    # Define source pdf station location
    source_first_mailer_pdfs = os.path.join(TEMP_PRE_ODR_FIRST_MAILER_PDFS, station)
    zip_first_mailer_dest = TEMP_ZIP_PRE_ODR_FIRST_MAILER_PDFS

    # Define zip name
    zip_first_mailer_name = os.path.join(zip_first_mailer_dest,station, f"{station}-FirstMailer-{current_date}.zip")
    zip_first_mailer_path = os.path.join(zip_first_mailer_dest, station)
    
    if not os.path.exists(zip_first_mailer_path):
        os.makedirs(zip_first_mailer_path)

    # Zip pdfs
    print(f"Zipping {station}-batch-{current_date}.zip...")
    # shutil.make_archive(zip_name, "zip", source_pdfs)   
    zip_files_with_validation_for_first_mailer(zip_first_mailer_name, source_first_mailer_pdfs, wait_time =0)

    # Define zip location
    zip_first_mailer_location = zip_first_mailer_name
    print()
    # If pdfs were successfully zipped, delete pdfs
    if os.path.exists(zip_first_mailer_location):
        for file_name in os.listdir(source_first_mailer_pdfs):
            if file_name.endswith(".pdf"):
                file_path = os.path.join(source_first_mailer_pdfs, file_name)
                os.remove(file_path)
        print("PDF files deleted.")

    return zip_first_mailer_location
    
def dist_sftp_mailer_pdfs(zip_location, station, isXpressPay, issuing_agency, current_date):
    from .tasks import logging
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

    if station == 'MAR':
        sftp_xpress_username = ENV_CONFIG("SFTP_USERNAME_XPRESS_LOGIN_MAR_ODR")
        sftp_xpress_password = ENV_CONFIG("SFTP_PASSWORD_XPRESS_PASSWORD_MAR_ODR")
        


    while attempts < max_retries:
        try:
            if isXpressPay and station in ['MAR']:
                file_station = station
                source_csvs = os.path.join(TEMP_PRE_ODR__FIRST_MAILER_CSVS_DIR, station)
                if not os.path.exists(source_csvs):
                    os.makedirs(source_csvs)

                distribution_code = 1002
                csv_name = f"{file_station}-Citations-{current_date}.csv"
                csv_location = os.path.join(source_csvs, csv_name)
                print(csv_location, "inside csv location")

                has_csv_today = s3_download_file(csv_name, "pre_odr_csvs", source_csvs)
                xpress_csv_pre_odr(csv_location, issuing_agency)

                zip_name = f"{file_station}-Citations{distribution_code}-{current_date}.zip"
                new_csv = f"{file_station}-Citations{distribution_code}-{current_date}.txt"
                csv_zip_location = os.path.join(source_csvs, zip_name)
                new_csv_location = os.path.join(source_csvs, new_csv)

                shutil.copyfile(csv_location, new_csv_location)

                with zipfile.ZipFile(csv_zip_location, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(new_csv_location, os.path.basename(new_csv_location))
                    print(f"{csv_name} zipped as {zip_name}")
                    print("sending zip files ---------------")

                try:
                    
                    sftp = FipsSftpClient(
                        hostname=sftp_xpress_host,
                        port=sftp_xpress_port,
                        username=sftp_xpress_username,
                        password=sftp_xpress_password,
                       
                    )

                    sftp.connect()
                    local_path = csv_zip_location
                    remote_path = sftp_xpress_remote_dir + '/' + zip_name
                    sftp.upload_file(local_path, remote_path)
                    print(f"Uploaded {zip_name} successfully.")
                    sftp.disconnect()
                    break  

                except Exception as e:
                    print(f"Failed to upload {zip_name}.")
                    print(f"Error: {e}")
                    attempts += 1
                    logging.error(f'An error occurred for {station} reason {e}')
                    
                    if attempts >= max_retries:
                        print("Max retries reached. Upload failed.")
                        return -1

                    time.sleep(retry_delay)  

            else:
                print("Station not valid for XpressPay or isXpressPay is False.")
                break  

        except Exception as e:
            attempts += 1
            print(f"Attempt {attempts} failed to upload {csv_zip_location}.")
            print(f"Error: {e}")
            logging.error(f'An error occurred for {station} reason {e}')
            
            if attempts >= max_retries:
                print("Max retries reached. Upload failed.")
                return -1
            time.sleep(retry_delay)

    
    # SFTP files
    try:
        transport = paramiko.Transport((sftp_host, sftp_port))
        transport.connect(username=sftp_username, password=sftp_password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        # with open(zip_location, "rb") as file:
        if zip_location:
            file_name = os.path.basename(zip_location)
            dir_path = sftp_remote_dir  # + '/' + station

            # Check if directory exists and create if it doesn't
            # try:
            # sftp.stat(dir_path)
            # except IOError:
            # sftp.mkdir(dir_path)

            sftp.put(zip_location, dir_path + "/" + file_name)
            print(f"{file_name} uploaded successfully!")

        # Close connection
        if sftp:
            sftp.close()
        if transport:
            transport.close()
        return 0  # Return 0 for successful upload
    except Exception as e:
        print(f"Failed to upload.")
        print(f"Error: {e}")

    # Close connection
        if sftp:
            sftp.close()
        if transport:
            transport.close()
        return -1
    
def send_email_with_attachment_cassel(attachment_path):
    try:
        to_email = ['rehrlick@kerseygov.com','JPiper@kerseygov.com','HCurtis@kerseygov.com']
        cc_emails = ["craig@emergentenforcement.com", "leah@emergentenforcement.com", "gdn@emergentenforcement.com"]

        yesterday = datetime.today() - timedelta(days=1)
        yesterday_str = yesterday.strftime('%m/%d/%Y')

        subject = f"PAYMENT FILE FOR {yesterday_str}"
        body = f"Please find the attached payment file for {yesterday_str}"

        ses_client = SESClient()
        ses_client.send_email_with_attachment(
            subject=subject,
            body=body, 
            to_addresses=to_email,
            cc_addresses=cc_emails, 
            attachment_path=attachment_path
        )
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

def load_citation_data_from_csv(file_path):
    citation_data = []
    
    with open(file_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.reader(file, delimiter=',') 
        
        for row in reader:
            try:
                plate = row[32].strip()   # Column AG
                state = row[33].strip()   # Column AH
                if plate and state:        # only if both values exist
                    citation_data.append((state, plate))
            except IndexError:
                # skip rows that don't have enough columns
                continue

    return citation_data

def get_duplicate_tattile_records(
    current_date,       
    station,
    station_id,
):
    days_range = 45

    if isinstance(current_date, str):
        target_date = datetime.strptime(current_date, "%m%d%Y").date()
    else:
        target_date = current_date

    past_date = target_date - timedelta(days=days_range)

    Q1_queryset = (
        sup_metadata.objects.filter(
            station_id=station_id,
            isApproved=True,
            timeApp__date=target_date,
        )
        .select_related(
            "citation",
            "citation__vehicle",
            "citation__vehicle__lic_state",
            "citation__tattile",
        )
        .annotate(
            citationID=F("citation__citationID"),
            approved_date=Cast("timeApp", DateField()),
            plate=F("citation__vehicle__plate"),
            state=F("citation__vehicle__lic_state__ab"),
            capture_date=TruncDate("citation__tattile__image_time"),
            capture_time=Cast(TruncSecond("citation__tattile__image_time"),output_field=TimeField()),
        )
        .values(
            "citationID",
            "approved_date",
            "plate",
            "state",
            "capture_date",
            "capture_time",
        )
    )

    Q1_list = list(Q1_queryset)

    if not Q1_list:
        return "No citations found for target date."

    q1_plates = {r["plate"] for r in Q1_list}
    q1_states = {r["state"] for r in Q1_list}

    Q2_queryset = (
        Citation.objects.filter(
            station_id=station_id,
            vehicle__plate__in=q1_plates,
            vehicle__lic_state__ab__in=q1_states,
            citation_sup_metadata__station_id=station_id,
            citation_sup_metadata__isApproved=True,
            citation_sup_metadata__timeApp__date__range=[past_date, target_date],
            tattile__isnull=False,
        )
        .select_related(
            "vehicle",
            "vehicle__lic_state",
            "tattile",
            "citation_sup_metadata",
        )
        .annotate(
            citation_ID=F("citationID"),
            approved_date=Cast("citation_sup_metadata__timeApp", DateField()),
            plate=F("vehicle__plate"),
            state=F("vehicle__lic_state__ab"),
            capture_date=TruncDate("tattile__image_time"),
            capture_time = Cast(TruncSecond("tattile__image_time"),output_field=TimeField()),
        )
        .values(
            "citationID",
            "approved_date",
            "plate",
            "state",
            "capture_date",
            "capture_time",
        )
    )

    Q2_list = list(Q2_queryset)

    def find_duplicates(rows, target_date):
        groups = defaultdict(list)
        duplicates = []
        
        for rec in rows:
            key = (
                rec["capture_date"],
                rec["capture_time"],
                rec["plate"],
                rec["state"]
            )
            groups[key].append(rec)

        for key, recs in groups.items():
            if len(recs) > 1:
                has_target_date = any(r["approved_date"] == target_date for r in recs)
                
                if has_target_date:
                    duplicates.extend(recs)

        return duplicates

    duplicate_Q1 = find_duplicates(Q1_list, target_date)
    duplicate_Q2 = find_duplicates(Q2_list, target_date)
    combined = duplicate_Q1 + duplicate_Q2

    unique_records = []
    seen = set()

    for rec in combined:
        cid = rec["citationID"]
        if cid not in seen:
            seen.add(cid)
            unique_records.append(rec)

    if not unique_records:
        return "No duplicate timestamp citations found."
    output_dir = fr"C:\Users\EM\Documents\Duplicate_citation_csv\{station}"
    os.makedirs(output_dir, exist_ok=True)

    file_name = f"Duplicate_citation_{station}_{target_date.strftime('%Y%m%d')}.csv"
    csv_path = os.path.join(output_dir, file_name)

    # --- Write to CSV ---
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "State",
            "Plate",
            "Captured Date",
            "Capture Time",
            "Citation ID",
            "Approved Date",
        ])

        for r in unique_records:
            writer.writerow([
                r["state"],
                r["plate"],
                r["capture_date"],
                r["capture_time"],
                r["citationID"],
                r["approved_date"],
            ])

    print(f"Duplicate CSV generated: {csv_path}")

    recipients = [
        "leah@emergentenforcement.com",
        "craig@emergentenforcement.com",
        "gdn@emergentenforcement.com"
    ]
    body = (
        f"Hello,\n\n"
        f"Please find attached the duplicate/repeated licence plate records "
        f"for station '{station}' captured on {target_date.strftime('%Y-%m-%d')}.\n\n"
        f"Total duplicate entries found: {len(unique_records)}\n\n"
        f"Regards,\nEES System"
    )


    ses_client = SESClient()
    ses_client.send_email_with_attachment(
        subject=f"Duplicate Licence Plate Report - {station} ({target_date.strftime('%Y-%m-%d')})",
        body=body,
        to_addresses=recipients,
        attachment_path=csv_path
    )

    # msg = MIMEMultipart()
    # msg["From"] = email_from
    # msg["To"] = ", ".join(recipients)
    # msg["Subject"] = f"Duplicate Licence Plate Report - {station} ({target_date.strftime('%Y-%m-%d')})"

    # body = (
    #     f"Hello,\n\n"
    #     f"Please find attached the duplicate/repeated licence plate records "
    #     f"for station '{station}' captured on {target_date.strftime('%Y-%m-%d')}.\n\n"
    #     f"Total duplicate entries found: {len(combined)}\n\n"
    #     f"Regards,\nEES System"
    # )
    # msg.attach(MIMEText(body, "plain"))

    # # --- Attach CSV file ---
    # with open(csv_path, "rb") as attachment:
    #     part = MIMEBase("application", "octet-stream")
    #     part.set_payload(attachment.read())
    #     encoders.encode_base64(part)
    #     part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(csv_path)}"')
    #     msg.attach(part)

    # # --- Send email ---
    # try:
    #     with smtplib.SMTP(smtp_host, smtp_port) as server:
    #         server.starttls()
    #         server.login(smtp_username, smtp_password)
    #         server.sendmail(email_from, recipients, msg.as_string())
    #     print("Email sent successfully.")
    # except Exception as e:
    #     print(f"Email sending failed: {e}")
    #     return f"Email sending failed: {e}"

    return f"Duplicate report generated and emailed successfully ({len(combined)} records)."