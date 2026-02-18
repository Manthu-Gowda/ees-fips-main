from video.models import Citation, PaidProcessedFiles, Station, UnpaidCitation,PaidCitationsData, DuncanMasterData
# from video.utils import Sftp
import os
# import pysftp
import csv
from decimal import Decimal
from datetime import datetime
from datetime import timedelta
from django.utils import timezone
from typing import List
from zipfile import ZipFile
from django.db import transaction
from decouple import config as ENV_CONFIG
from ees.utils import s3_client, s3_create_folder, s3_check_folder_exists
import posixpath
from ..distributor import send_email_with_attachment_cassel
from video.FipsSftpClient import FipsSftpClient

def format_cassel_file(imp_file_path, txt_file_path):             
    try:
        with open(imp_file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        rows = [line.split(",") for line in content.splitlines()]
        formatted_lines = []

        for i in rows:
            i[4] = i[0]
            i[0] = i[2]
            i[1] = "9902"
            i[2] = "6"
            formatted_line = ",".join(i) + "\n"  # No extra comma at the end
            formatted_lines.append(formatted_line)

        file_exists = os.path.exists(txt_file_path)
        with open(txt_file_path, 'a', encoding='utf-8') as txt_file:
            # Write header only if the file doesn't exist yet or is empty
            if not file_exists or os.path.getsize(txt_file_path) == 0:
                txt_file.write("Payor Name,Distribution code,Payment Type,amount,date\n")
            txt_file.writelines(formatted_lines)

    except Exception as e:
        print(f"An error occurred while processing the file: {e}")
# class Command(BaseCommand):
#     help = "Process a single .imp file and store the data in the PaidCitationsData table."

#     def handle(self, *args, **kwargs):
#         # Process paid citations within a transaction
#         try:
#             process_single_imp_file(["FED-M","WBR2","HUD-C"])
#         except Exception as e:
#             print(f"Error processing payment files: {e}")
#             return  # Exit early if there's an error processing paid citations

#         # After processing, find unpaid citations (outside of transaction)
#         try:
#             find_unpaid_citations_for_sftp_stations(["FED-M","WBR2","HUD-C"])
#         except Exception as e:
#             print(f"Error finding unpaid citations: {e}")

@transaction.atomic
def process_single_imp_file(SFTP_STATIONS: List[str]):
    """`
    Process .imp files from multiple stations, and store the data in the PaidCitationsData table.
    Only new ZIP files are processed (those not in PaidProcessedFiles table).
    """
    try:
        for station in SFTP_STATIONS:
            # Load station-specific credentials from environment or configuration
            env_variable = {
                            "FED-M": "FEDM",
                            "WBR2":"WBR2",
                            "HUD-C":"HUDC",
                            "KRSY-C": "KRSYC",
                            "FPLY-C": "FPLYC"
                            }
            SFTP_HOST = ENV_CONFIG(f"{env_variable[station]}_SFTP_HOST_XPRESS_HOST")
            SFTP_PORT = 22
            SFTP_USERNAME = ENV_CONFIG(f"{env_variable[station]}_SFTP_USERNAME_XPRESS_LOGIN")
            SFTP_PASSWORD = ENV_CONFIG(f"{env_variable[station]}_SFTP_PASSWORD_XPRESS_PASSWORD")
            SFTP_REMOTE_DIR = ENV_CONFIG(f"{env_variable[station]}_SFTP_REMOTE_DIR_XPRESS")
            SFTP_ARCHIVE_DIR = ENV_CONFIG(f"{env_variable[station]}_SFTP_ARCHIVE_DIR_XPRESS")

            # Create an SFTP connection
            
                # List all ZIP files in the remote directory
            fips_session = FipsSftpClient(
                hostname=SFTP_HOST,
                port=SFTP_PORT,
                username=SFTP_USERNAME,
                password=SFTP_PASSWORD,
            )
            fips_session.connect()

            remote_files = fips_session.listdir(SFTP_REMOTE_DIR)
            # print(f"Files in {SFTP_REMOTE_DIR}: {remote_files}")
            # check if folder exists in s3
            upload_payment_file_to_s3(station=station,isUpload=False)
            for remote_file in remote_files:
                if remote_file.endswith(".zip"):
                    # Check if this file has already been processed
                    if PaidProcessedFiles.objects.filter(
                        file_name=remote_file,station_name=station
                    ).exists():
                        # print(
                        #     f"Payment File {remote_file} has already been processed. Skipping..."
                        # )
                        continue

                    # Define local paths for saving and extracting files
                    local_dir = (
                        f"C:\\Users\\EM\\Documents\\paid_payment_files\\{station}"
                    )
                    local_zip_path = os.path.join(local_dir, remote_file)
                    os.makedirs(local_dir, exist_ok=True)  # Ensure directory exists

                    # Download the ZIP file
                    fips_session.download(
                        os.path.join(SFTP_REMOTE_DIR, remote_file), local_zip_path
                    )
                    print(f"Downloaded payment file {remote_file} from station {station}")

                    # Extract the ZIP file
                    extracted_imp_files = []
                    with ZipFile(local_zip_path, "r") as zip_ref:
                        zip_ref.extractall(local_dir)
                        extracted_imp_files = [
                                                os.path.join(local_dir, f)
                                                for f in zip_ref.namelist()
                                                if f.endswith(".imp") or f.endswith(".txt")
                                            ]

                    # Assuming only one .imp file per ZIP
                    # imp_files = [
                    #     f
                    #     for f in os.listdir(local_dir)
                    #     if f.endswith(".imp") or f.endswith(".txt")
                    # ]
                    for imp_file_path in extracted_imp_files:
                        print(imp_file_path)
                        process_imp_file(
                            imp_file_path
                        )  # Process the extracted .imp file

                        if station == 'KRSY-C' and imp_file_path.endswith('.imp'):
                            
                            folder_path = os.path.dirname(imp_file_path)
                            today_str = datetime.today().strftime('%m%d%Y')
                            txt_file_name = f'payment_file_{today_str}.txt'
                            txt_file_path = os.path.join(folder_path, txt_file_name)
                            format_cassel_file(imp_file_path,txt_file_path)
                            send_email_with_attachment_cassel(txt_file_path)

                    # Mark the ZIP file as processed
                    PaidProcessedFiles.objects.create(file_name=remote_file, station_name=station)
                    print(f"Processed and marked {remote_file} as processed.")
                        # upload to s3
                    upload_payment_file_to_s3(station=station,local_zip_path=local_zip_path,isUpload=True)

                    # Move the file to the archive directory
                    source_path = posixpath.join(SFTP_REMOTE_DIR, remote_file)
                    dest_path = posixpath.join(SFTP_ARCHIVE_DIR, remote_file)

                    try:
                        # Check if the destination file exists
                        if dest_path in fips_session.listdir(SFTP_ARCHIVE_DIR):
                            # Optional: Remove the file if you want to override it
                            fips_session.remove(dest_path)
                            print(f"Removed existing file: {dest_path}")

                        # Perform the rename operation
                        fips_session.rename(source_path, dest_path)
                        print(f"Moved file from {source_path} to {dest_path}")

                    except FileNotFoundError:
                        print(f"Source file {source_path} not found.")
                    except Exception as e:
                        print(f"Failed to move file {source_path} to {dest_path}: {e}")
        # Call this function after processing paid citations

    except Exception as e:
        fips_session.disconnect()
        print(f"Error occurred in processing paid citations: {e}")


def process_imp_file(file_path):
    """
    Process a single .imp file.
    """
    try:
        with open(file_path, "r",encoding="utf-8") as f:
            reader = csv.reader(f)
            processed_citation = set()
            transaction_id_processed = set()
            for row in reader:
                try:
                    citation_id = row[1]
                    transaction_id = row[4]

                    # Skip duplicates within same file
                    if citation_id in processed_citation or transaction_id in transaction_id_processed:
                        continue

                    # Mark as processed immediately
                    processed_citation.add(citation_id)
                    transaction_id_processed.add(transaction_id)

                    paid_amount = float(row[3])

                    # Negative payment (bank settlement)
                    if paid_amount < 0:
                        PaidCitationsData.objects.filter(
                            citationID=citation_id
                        ).delete()
                        continue

                    transaction_date = datetime.strptime(row[0], "%m/%d/%Y").date()

                    citation = Citation.objects.filter(citationID=citation_id).first()
                    if not citation:
                        # print(f"Citation with ID {citation_id} not found. Skipping...")
                        continue

                    if PaidCitationsData.objects.filter(citationID=citation.citationID).exists():
                        # print(f"Ciation ID {citation.citationID} already exists. Skipping...")
                        continue
                    
                    PaidCitationsData.objects.create(
                        transaction_id=transaction_id,
                        transaction_date=transaction_date,
                        citationID=citation.citationID,
                        full_name=row[2],
                        paid_amount=paid_amount,
                        video=citation.video,
                        image=citation.image,
                        tattile = citation.tattile
                    )
                    lic_state = citation.vehicle.lic_state
                    plate = citation.vehicle.plate

                    duncan_master_object = DuncanMasterData.objects.filter(
                        state=lic_state, plate=plate
                    ).last()

                    if duncan_master_object.is_address_updated:
                        duncan_master_object.is_address_updated = False
                        duncan_master_object.save()

                except Exception as e:
                    continue
        print(f"Finished processing .imp file: {file_path}")

    except Exception as e:
        print(f"Error opening or reading file {file_path}: {e}")
        raise e
def find_unpaid_citations_for_sftp_stations(SFTP_STATIONS: List[str]):
    """
    Find unpaid citations for specific SFTP stations and store them in the UnpaidCitation table
    if they remain unpaid past their original due date. For citations already in the table,
    check if they remain unpaid and update late fees, due dates, and the pre_odr_mail_count.
    """
    try:
        print("---- Find Unpaid Citations for SFTP Stations ----")
        
        # Calculate the current date
        current_date = timezone.now().date()
        # print(f"Current Date: {current_date}")
        
        # Get the stations that match the given SFTP station names
        sftp_stations = Station.objects.filter(name__in=SFTP_STATIONS)
        # print(f"SFTP Stations: {sftp_stations}")

        # Get all approved citations for SFTP stations that are unpaid
        unpaid_citations = Citation.objects.filter(
            isApproved=True,  
            station__in=sftp_stations
        ).exclude(citationID__in=PaidCitationsData.objects.values("citationID"))
        
        # print(f"Unpaid Citations: {unpaid_citations}")
        
        for citation in unpaid_citations:
            original_due_date = citation.datetime.date() + timedelta(days=30)  # Original due date as a date object
            # print(f"Citation ID: {citation.citationID} has due date: {original_due_date}")

            # Check if citation is unpaid past its original due date
            if (current_date and original_due_date) and current_date > original_due_date:
                # print(f"Citation ID: {citation.citationID} is past due!")
                
                # Check if this citation is already in the UnpaidCitation table
                existing_unpaid_citation = UnpaidCitation.objects.filter(ticket_number=citation.citationID).first()
                
                if not existing_unpaid_citation:
                    # First time the citation is being added to the UnpaidCitation table
                    UnpaidCitation.objects.create(
                        ticket_number=citation.citationID,
                        off_date=citation.datetime.date(),  # Convert DateTimeField to date
                        arr_date=original_due_date,
                        amount=citation.fine.fine,  # Store the original fine amount
                        payment=0,  # No payment made
                        balance=citation.fine.fine,  # Full amount still unpaid
                        full_name=f"{citation.person.first_name} {citation.person.last_name}" if citation.person else "N/A",
                        video=citation.video,
                        image=citation.image,
                        tattile = citation.tattile,
                        station=citation.station,
                        isApproved=False,  # Manager will approve this later
                        pre_odr_mail_count=0,  # Initially zero
                        # first_mail_due_date = original_due_date + timedelta(days=37),
                        first_mail_fine = citation.fine.fine + (citation.fine.fine * Decimal(0.30)),
                        # second_mail_due_date = original_due_date + timedelta(days=67),
                        second_mail_fine = citation.fine.fine + (citation.fine.fine * Decimal(0.30))
                    )
                    # print(f"Unpaid citation stored for Citation ID: {citation.citationID}")
                # elif (current_date and existing_unpaid_citation.first_mail_due_date) and current_date > existing_unpaid_citation.first_mail_due_date and existing_unpaid_citation.pre_odr_mail_count == 1:
                #     # Citation already exists in UnpaidCitation, check if it is still unpaid for the new due date
                #         print(f"Citation ID: {citation.citationID} is still unpaid after the previous due date!")
                        
                #         # Apply the new late fee based on pre_odr_mail_count and station policy (e.g., 15% fee)
                #         # additional_late_fee =existing_unpaid_citation.amount + (existing_unpaid_citation.amount * Decimal(0.30))
                #         # new_balance = existing_unpaid_citation.balance + additional_late_fee
                        
                #         # Update the UnpaidCitation record
                #         existing_unpaid_citation.isApproved = False  # Manager will approve this later
                #         # existing_unpaid_citation.balance = new_balance
                #         existing_unpaid_citation.save()


                #         print(f"Updated Citation ID: {citation.citationID} with new fine and extended due date.")
                
                else:
                    pass
                    # print(f"Citation ID: {citation.citationID} is still within the current due date or already paid.")
        
    except Exception as e:
        print(f"Error finding unpaid citations for SFTP stations: {e}")
        raise e
    


def upload_payment_file_to_s3(station,local_zip_path=None,isUpload=False):
    try:
        # check if folder exists
        folder_name = f"paid_payment_files/{station}"
        if not s3_check_folder_exists(folder_name):
            s3_create_folder(folder_name)
            print(f"Folder {folder_name} created in AWS S3 bucket.")
        else:
            print(f"Folder {folder_name} already exists in AWS S3 bucket.")

        # upload zip file to s3
        if isUpload and local_zip_path:
            s3_client.upload_file(local_zip_path, ENV_CONFIG("AWS_S3_BUCKET_NAME"), f"{folder_name}/{os.path.basename(local_zip_path)}")
            print(f"Payment file uploaded to S3: {local_zip_path}")
    except Exception as e:
        print(f"Error uploading payment file to S3: {e}")
        raise e