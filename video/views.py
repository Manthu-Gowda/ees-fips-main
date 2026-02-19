import json
import os
import threading
from datetime import datetime, time, timedelta, timezone
from tkinter import SE
from django.utils import timezone as tz
from io import BytesIO
from django.http import JsonResponse
import csv
import pandas as pd
from decouple import config as ENV_CONFIG
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
# from accounts.models import PermissionLevel
from ees.utils import (get_presigned_url, s3_get_file, s3_upload_file, upload_to_s3, upload_non_violation_folder_to_s3)
from odr_view.odr_utils import download_odr_csv
# from video.schedulers.process_paid_citations import find_unpaid_citations_for_sftp_stations, process_single_imp_file
# from video.schedulers.process_paid_citations_first_mailer import find_unpaid_citations_for_sftp_stations_first_mailer, process_single_imp_file_first_mailer
from .utils import xpress_csv
from .distributor import dist_sftp
# import logging
from .models import (
    Agency,
    Citation,
    CitationsWithEditFine,
    CitationsWithTransferOfLiabilty,
    CitationsWithUpdatedAddress,
    CourtDates,
    Data,
    DuncanSubmission,
    Fine,
    Image,
    OdrCSVdata,
    Person,
    QuickPD,
    State,
    Station,
    Vehicle,
    Video,
    adj_metadata,
    csv_metadata,
    road_location,
    sup_metadata,
    VideoFailedLog,
    DuncanMasterData,
    Tattile,
    TattileFile
)
# from .OCR import OCRImage
from .pdf_creation import save_combined_pdf, save_pdf, save_pdf_manual, save_reminder_hudc_pdf
from django.utils import timezone
from django.db.models import Exists, OuterRef
from datetime import date, datetime
from django.utils.timezone import make_aware
from calendar import month_name
import re
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from video.SESClient import SESClient

BASE_URL = ENV_CONFIG("BASE_URL")
BASE_DIR = ENV_CONFIG("BASE_DIR")
TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
TEMP_ZIP_DIR = ENV_CONFIG("TEMP_ZIP_DIR")
TEMP_CSV_DIR = ENV_CONFIG("TEMP_CSV_DIR")
AWS_S3_BUCKET_NAME = ENV_CONFIG("AWS_S3_BUCKET_NAME")
AWS_REGION = ENV_CONFIG("AWS_REGION")
MAR_SECURE_PAY_QR= ENV_CONFIG("MAR-SECURE-PAY-QR")
MAR_BADGE = ENV_CONFIG("MAR-BADGE")
TEMP_PRE_ODR_FIRST_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_FIRST_MAILER_PDFS")
TEMP_ZIP_PRE_ODR_FIRST_MAILER_PDFS= ENV_CONFIG("TEMP_ZIP_PRE_ODR_FIRST_MAILER_PDFS")
TEMP_PRE_ODR_SECOND_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_SECOND_MAILER_PDFS")
TEMP_ZIP_PRE_ODR_SECOND_MAILER_PDFS = ENV_CONFIG("TEMP_ZIP_PRE_ODR_SECOND_MAILER_PDFS")


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

workaround = ""
last_email_sent = None

import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE =os.path.join(LOG_DIR, "ees_app_logs.log")

if not os.path.exists(os.path.dirname(LOG_FILE)):
    os.makedirs(os.path.dirname(LOG_FILE))

# Setup Rotating Handler: 5MB per file, keeps 3 old backups
# 5 * 1024 * 1024 bytes = 5MB
rotating_handler = RotatingFileHandler(
    LOG_FILE, 
    maxBytes=5*1024*1024, 
    backupCount=5, 
    encoding="utf-8"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        rotating_handler,
        logging.StreamHandler()
    ]
) 
logger = logging.getLogger(__name__)

# def index():
#     global last_email_sent

#     print("inside index")
#     # user_id = request.user.id
#     # context = {
#     #     'list_of_ids': [149, 152, 151, 153],
#     #     'user_id': user_id
#     # }
#     # print(user_id,'user_id')

#     thread_name = "video_upload_thread"
#     existing_threads = [t for t in threading.enumerate() if t.name == thread_name]
#     if existing_threads:
#         print(
#             f"\033[32m ------------ Thread '{thread_name}' is already running. \033[0m ",
#         )
#     else:
#         # If the thread doesn't exist, start a new one
#         threading.Thread(target=vids, name=thread_name).start()
#         print(f"\033[32m ------------ Started new thread '{thread_name}'. \033[0m")

#     now = datetime.now()
#     current_date = now.strftime("%m%d%Y")
#     current_date_pre_odr = now - timedelta(days = 1)
#     current_date_pre_odr = current_date_pre_odr.strftime("%m%d%Y")
#     mid = time(23, 50, now.second, now.microsecond)
#     mid_str = mid.strftime("%H:%M")

#     reset_ticket = time(3, 50, now.second, now.microsecond)
#     reset_tick_num = reset_ticket.strftime("%H:%M")

#     daily_report_runner = time(4, 1, now.second, now.microsecond)
#     print("Running daily report runner ------------")
#     daily_ticket_counter = daily_report_runner.strftime("%H:%M")

#     # dist_time = time(23, 40, now.second, now.microsecond)
#     dist_time = time(4, 59)
#     current_time = now.time().replace(second=0, microsecond=0)
#     current_date = (now - timedelta(days=1)).date().strftime("%m%d%Y")
#     print(current_date,"current date in here ")

#     first_mailer_dist_time = time(0, 51, now.second, now.microsecond)

#     agencies = Agency.objects.all().order_by("name").values()

#     citation_summary_report_runner = time(8, 1, now.second, now.microsecond)
#     citation_summary_scheduler = citation_summary_report_runner.strftime("%H:%M")

#     tattile_ticket = time(1, 30, now.second, now.microsecond)
#     tattile_ticket_scheduler = tattile_ticket.strftime("%H:%M")

#     tattile_ticket_reject = time(2, 1, now.second, now.microsecond)
#     tattile_ticket_reject_scheduler = tattile_ticket_reject.strftime("%H:%M")

#     pdf_generation_and_csv_creation_process = time(2, 30, now.second, now.microsecond)
#     pdf_generation_and_csv_scheduler = pdf_generation_and_csv_creation_process
#     citation_summary_report_runner_first_mailer = time(7, 10, now.second, now.microsecond)
#     citation_summary_scheduler_for_first_mailer = citation_summary_report_runner_first_mailer.strftime("%H:%M")

#     if current_time == dist_time:
#         for x in agencies:
#             station = Station.objects.filter(id=x["station_id"]).values().first()
#             fine = Fine.objects.filter(station_id=station['id']).values_list('fine', flat=True).first()
#             issuing_agency = x['name']
#             is_express_pay = x.get("isXpressPay")
#             # if os.path.isdir(os.path.join(TEMP_PDF_DIR, station['name'])):
#             #     if any(
#             #         file.endswith(".pdf")
#             #         for file in os.listdir(os.path.join(TEMP_PDF_DIR, station['name']))
#             #     ):
#             #         try:
#             #             zip_loc = zip_pdfs(station['name'], current_date)
#             #             logging.info(f'PDF zipped for {station["name"]}')
#             #             # Check if the agency uses XpressPay
#             #             if x.get("isXpressPay"):
#             #                 print(issuing_agency, "issuing agency here")
#             #                 dist_sftp(zip_loc, station['name'], x["isXpressPay"], fine, issuing_agency, current_date)
#             #                 logging.info(f'File send on SFTP for {station["name"]}')
#             #             else:
#             #                 dist_sftp(zip_loc, station['name'], False, None, None, current_date)
#             #                 logging.info(f'File send on SFTP for {station["name"]}')
#             #         except Exception as e:
#             #             logging.error(f'An error occurred for {station["name"]} reason {e}')
#             #     else:
#             #         print('No PDFs found')
#             #         # dist_sftp(None, station['name'], False, None, None, current_date)
#             # print('No directory for station found')
#             try:
#                 # dist_smtp(x["emails"], station['name'], current_date, station['id'], fine, issuing_agency)
#                 if is_express_pay:
#                         print(issuing_agency, "issuing agency here")
#                         dist_sftp(
#                             station["name"],
#                             is_express_pay,
#                             fine,
#                             issuing_agency,
#                             current_date
#                         )
#                         print(f"File sent to xpress_csv and SFTP for {station['name']}")
#                 else:
#                     dist_sftp(
#                         station["name"],
#                         False,
#                         None,
#                         None,
#                         current_date
#                     )
#                     print(f"File sent to SFTP for {station['name']}")
#             except Exception as e:
#                 return (f'Mail sent failed for {station["name"]} reason {e}')
        
    # elif now.time() == first_mailer_dist_time:
    #     print("inside first mailer zipping process")
    #     for x in agencies:
    #         station = Station.objects.filter(id=x["station_id"]).values().first()
    #         print(station, "station in here")
    #         issuing_agency = x['name']
            
    #         print(station, "station is here")
    #         if os.path.isdir(os.path.join(TEMP_PRE_ODR_FIRST_MAILER_PDFS, station['name'])):
    #             print(1)
    #             if any(
    #                 file.endswith(".pdf")
    #                 for file in os.listdir(os.path.join(TEMP_PRE_ODR_FIRST_MAILER_PDFS, station['name']))):
                    
    #                 zip_loc = zip_first_mailer_pdfs(station['name'], current_date_pre_odr)
    #                 print(zip_loc, "zip_loc here")
    #                 if x.get("isPreOdr"):
    #                 # Distribute via SFTP
    #                     print("Distributing to csv")
    #                     dist_sftp_mailer_pdfs(zip_loc, station['name'], x["isPreOdr"], issuing_agency, current_date_pre_odr)
    #                 else:
    #                     pass
    #         else:
    #             print('No PDFs found')
    #             # dist_sftp_mailer_pdfs(None, station['name'], False, None, current_date)
    #     else:
    #         print('No directory for station found')
    #         # dist_smtp(x["emails"], station['name'], current_date, station['id'], fine, issuing_agency)

    # #Checks at Midnight
    # if now.time() == mid or now.strftime("%H:%M") == mid_str:
    #     station_adj_metadata = adj_metadata.objects.all()
    #     station_sup_metadata = sup_metadata.objects.all()
    #     removal_of_adj(station_adj_metadata)
    #     removal_of_sup(station_sup_metadata)

    # if now.time() == daily_report_runner or now.strftime("%H:%M") == daily_ticket_counter:
    #     # Check if the email has been sent today
    #     if last_email_sent is None or last_email_sent.date() < now.date():
    #         daily_report_generator()
    #         print("Generating Daily report and sending email.")
    #         # Set the flag to the current date after sending the email
    #         last_email_sent_date = now
    #     else:
    #         print("Email already sent today.")

    # if now.time() == citation_summary_report_runner or now.strftime("%H:%M") == citation_summary_scheduler:
    #     print("running--------------")
    #     try:
    #         process_single_imp_file(["FED-M","WBR2","HUD-C","KRSY-C","FPLY-C"])
    #         find_unpaid_citations_for_sftp_stations(["FED-M","WBR2","HUD-C","KRSY-C","FPLY-C"])
    #     except Exception as e:
    #         print(f"Error processing payment files: {e}")
    #         return  # Exit early if there's an error processing paid citations

    # if now.time() == tattile_ticket or now.strftime("%H:%M") == tattile_ticket_scheduler:
    #     try:
    #         print("Running Tattile File upload")
    #         read_json_excluding_image()
    #     except Exception as e:
    #         print(f"Error processing tattile files: {e}")
    #         return 
        
    # if now.time() == tattile_ticket_reject or now.strftime("%H:%M") == tattile_ticket_reject_scheduler:
    #     try:
    #         print("Running Tattile reject File upload")
    #         reject_tattile_record()
    #     except Exception as e:
    #         print(f"Error processing tattile files: {e}")
    #         return 
    
    # if now.time() == pdf_generation_and_csv_creation_process or now.strftime("%H:%M") == pdf_generation_and_csv_scheduler:
    #     try:
    #         print("[Scheduler] Triggering midnight PDF & CSV generation job...")
    #         create_csv_and_pdf_data_for_agencies()
    #     except Exception as e:
    #         print(f"Error generating pdf and csv files: {e}")

    # if now.time() == citation_summary_report_runner_first_mailer or now.strftime("%H:%M") == citation_summary_scheduler_for_first_mailer:
    #     print("running------first_mailer_reports------------------")
    #     try:
    #         process_single_imp_file_first_mailer(["MAR"])
    #         find_unpaid_citations_for_sftp_stations_first_mailer(["MAR"])
    #     except Exception as e:
    #         print(f"Error processing payment files: {e}")

    # station_adj_metadata = adj_metadata.objects.all()
    # station_sup_metadata = sup_metadata.objects.all()
    # removal_of_adj(station_adj_metadata)
    # removal_of_sup(station_sup_metadata)

    # global permissions    
    # global workaround
    # template_name = "index.html"
    # if request.user.is_authenticated:
    #     permissions = PermissionLevel.objects.filter(user_id=request.user.id).values()[
    #         0
    #     ]
    #     print(permissions)

    #     if request.user.agency is not None:
    #         permissions["station"] = request.user.agency.station.name
    #         permissions["isPreOdr"] = request.user.agency.isPreOdr
    #     else:
    #         permissions["station"] = None
    #         permissions["isPreOdr"] = False
    #     if permissions is not None:
    #         print(permissions['station'])
    #         if request.user.agency is not None and request.user.agency.station is not None:
    #             agency_station = Agency.objects.filter(station = request.user.agency.station.id).values()[0]
    #             station_api_key = agency_station['api_key']
    #         else:
    #             station_api_key = None
    #         return render(
    #             request,
    #             template_name,
    #             {"permissions": permissions,'station_api_key':station_api_key, "BASE_URL": BASE_URL, "context" : context},
    #             )
    #     else:
    #         return render(request, template_name, {"BASE_URL": BASE_URL})
    # else:
    #     return render(request, template_name, {"BASE_URL": BASE_URL})


def removal_of_adj(station_metadata):

    meta_df = station_metadata.filter(isRemoved=False).values()
    for x in meta_df:
        station_metadata.filter(id=x["id"]).update(isRemoved=True)

    removal = station_metadata.filter(isRemoved=True).values()
    for x in removal:
        if x['video_id'] != None:
            video_agencies.filter(id=x["video_id"], isSent = False).update(isRemoved=True)
            station_metadata.filter(id=x["id"]).update(
                timeRemoved=tz.make_aware(datetime.now(None))
            )
        elif x['image_id'] != None:
            image_agencies.filter(id=x["image_id"], isSent = False).update(isRemoved=True)
            station_metadata.filter(id=x["id"]).update(
                timeRemoved=tz.make_aware(datetime.now(None))
            )
        elif x['tattile_id'] != None:
            Tattile.objects.filter(id=x["tattile_id"], is_sent = False).update(is_removed=True)
            station_metadata.filter(id=x["id"]).update(
                timeRemoved=tz.make_aware(datetime.now(None))
            )
    print('Removal for ADJ ran')

def removal_of_sup(station_metadata):
    print("in removal")

    pending = station_metadata.filter(isRemoved=False).values("id", "citation_id")
    pending_list = list(pending)

    for x in pending_list:
        station_metadata.filter(id=x["id"]).update(isRemoved=True)
    for x in pending_list:
        cit_agencies.filter(id=x["citation_id"]).update(isRemoved=True)

        station_metadata.filter(id=x["id"]).update(
            timeRemoved=tz.make_aware(datetime.now())
        )
    cit_agencies.filter(isRejected = True,isSendBack = False, isRemoved = False).update(isRemoved=True)
    print("Removal for SUP ran")


def process_station_data(station_name, not_present_list):
    video_record = {}
    for vid in set(not_present_list):
        queried = Data.objects.filter(VIDEO_NAME=vid, STATION=station_name).values()
        new_video_data = None
        for i in range(queried.count()):
            got = queried[i]
            if new_video_data is not None:
                if abs(int(got["SPEED"])) > abs(int(new_video_data["SPEED"])):
                    new_video_data = got
            else:
                new_video_data = got
        if new_video_data:
            date = new_video_data["DATE"] + " " + new_video_data["TIME"]
            the_date_time = datetime.strptime(date, "%y%m%d %H%M%S")
            aware_date_time = timezone.make_aware(the_date_time)
            station_instance = Station.objects.get(name=station_name)

            road_location_check = road_location.objects.filter(
                LOCATION_CODE=new_video_data["LOCATION_CODE"],station=station_instance).exists()
            
            loc = f"media/mov/{new_video_data['STATION']}/{new_video_data['VIDEO_NAME']}_{new_video_data['VIDEO_NO']}.mov"
            file_path = os.path.join(BASE_DIR,loc)
            file_present= os.path.exists(file_path)

            log_present = VideoFailedLog.objects.filter(video_no=new_video_data["VIDEO_NO"],
                    video_name=new_video_data["VIDEO_NAME"],
                    video_date= new_video_data["DATE"],
                    station = station_instance.name).exists()
            
            if (road_location_check == False) and (file_present == False) and (log_present == False):
                log = VideoFailedLog.objects.create(
                        video_no=new_video_data["VIDEO_NO"],
                        video_name=new_video_data["VIDEO_NAME"],
                        video_date= new_video_data["DATE"],
                        station = station_instance.name,
                        reason = 'Video "station code" does not exist and .mov files not present',
                        status = False,
                        location_code = new_video_data["LOCATION_CODE"],
                        ).save()
                
            if road_location_check:
                location_instance = road_location.objects.get(
                    LOCATION_CODE=new_video_data["LOCATION_CODE"],
                    station=station_instance,
                )
            else:
                # Create a new record in the VideoLog table
                if (road_location_check == False) and (file_present == True) and (log_present == False):
                    log = VideoFailedLog.objects.create(
                        video_no=new_video_data["VIDEO_NO"],
                        video_name=new_video_data["VIDEO_NAME"],
                        video_date= new_video_data["DATE"],
                        station = station_instance.name,
                        reason = 'Video "station code"  does not match with the database road location table',
                        status = False,
                        location_code = new_video_data["LOCATION_CODE"],
                        ).save() 

            if file_present:
                loc = s3_upload_file(
                    loc,
                    f"{new_video_data['VIDEO_NAME']}_{new_video_data['VIDEO_NO']}.mov",
                    f"videos/{new_video_data['STATION']}",
                    bucket_name= AWS_S3_BUCKET_NAME 
                )
                video_record[new_video_data["VIDEO_NO"]] = {
                    "VIDEO_NO": new_video_data["VIDEO_NO"],
                    "caption": f"{new_video_data['VIDEO_NAME']}_{new_video_data['VIDEO_NO']}",
                    "url": loc,
                    "posted_speed": new_video_data["SPEED_LIMIT"],
                    "speed": abs(int(new_video_data["SPEED"])),
                    "speed_time": int(new_video_data["FRAMES"]) * (1 / 25),
                    "location": location_instance,
                    "distance": new_video_data["DISTANCE"],
                    "datetime": aware_date_time,
                    "officer_badge": new_video_data["BADGE_ID"].lstrip('0'),
                    "station": station_instance,
                }
            else:
                # Create a new record in the VideoLog table
                if (road_location_check == True) and (file_present == False) and (log_present == False):
                    log = VideoFailedLog.objects.create(
                        video_no=new_video_data["VIDEO_NO"],
                        video_name=new_video_data["VIDEO_NAME"],
                        video_date= new_video_data["DATE"],
                        station = station_instance.name,
                        reason = 'Video not present in local storage',
                        status = False,
                        location_code = new_video_data["LOCATION_CODE"],
                        ).save()

    return video_record



def vids():
    logging.info("Starting vids function to process video uploads")
    try:
        data = Data.objects.all().order_by("-PK")
        station_mapping = list(Station.objects.all().values_list("name", flat=True))

        all_video_data = {}
        for station_name in station_mapping:
            not_present_list = filter_not_present_videos(data, station_name)
            all_video_data.update(process_station_data(station_name, not_present_list))

        for video_id, video_info in all_video_data.items():
            # Video(**video_info).save()
            id_value = video_info.pop("VIDEO_NO", None)
            station_value = video_info.pop("station", None)
            Video.objects.create(
                VIDEO_NO=id_value, 
                station=station_value, 
                caption = video_info['caption'],
                url = video_info['url'], 
                posted_speed = video_info['posted_speed'], 
                speed = video_info['speed'], 
                location = video_info['location'],
                distance = video_info['distance'], 
                datetime = video_info['datetime'],
                officer_badge = video_info['officer_badge'],
                speed_time= video_info['speed_time']
            )
    except Exception as e:
        logging.error(f"Error in vids function: {e}")


def filter_not_present_videos(data, station_name):
    logging.info(f"Filtering videos for station: {station_name}")
    try:
        not_present_list = []
        for x in data:
            caption = x.VIDEO_NAME + '_' + x.VIDEO_NO
            if x.STATION == station_name:
                if not Video.objects.filter(
                    VIDEO_NO=x.VIDEO_NO, station__name=x.STATION, caption = caption
                ).exists():
                    not_present_list.append(x.VIDEO_NAME)
        return not_present_list
    except Exception as e:
        logging.error(f"Error filtering videos for station {station_name}: {e}")
        return []

def get_cit(citation_id, user_station , image_flow=False):
        
        fply_address_part = ''
        citation_obj = Citation.objects.get(citationID=citation_id)
        total = quick_pd_data.filter(ticket_num=citation_id, station=user_station).values()[
            0
        ]
        cit_choice = cit_agencies.filter(
            citationID=citation_id, station=user_station
        ).values()[0]
        if image_flow:
            adj_choice = image_agencies.filter(id = cit_choice["image_id"]).values()[0]
            offence_time = adj_choice['time']
        else:
            adj_choice = video_agencies.filter(
                id=cit_choice["video_id"], station=user_station
            ).values()[0]
            offence_time = adj_choice['datetime'] 

        veh_choice = veh_agencies.filter(
            id=cit_choice["vehicle_id"], station=user_station
        ).values()[0]
        per_choice = per_agencies.filter(id=cit_choice["person_id"]).values()[0]
        sup_data = sup_agencies.filter(citation=citation_obj, station=user_station).values()[0]
        dt = sup_data["timeApp"] + timedelta(days=30)
        date_app = sup_data["timeApp"] + timedelta(days=1)
        if citation_id in ['HUD-C-00000085', 'HUD-C-00000365']:
            due_date = '01/30/2025'
        elif citation_id in ['HUD-C-00000290', 'HUD-C-00000179', 'HUD-C-00000183', 
							'HUD-C-00000468', 'HUD-C-00000180', 'HUD-C-00000348']:
            due_date = '01/19/2025'
        elif citation_id in ['HUD-C-00001128', 'HUD-C-00000590', 
                             'HUD-C-00001081' , 'HUD-C-00000863', 'HUD-C-00001056']:
            due_date = '2/25/25'
        elif citation_id in ['HUD-C-00002777','HUD-C-00002783','HUD-C-00002408',
                            'HUD-C-00002723','HUD-C-00002705','HUD-C-00002685',
                            'HUD-C-00002597','HUD-C-00002627']:
            due_date = '06/30/2025'
        else:
            due_date = datetime.strftime(dt, "%m/%d/%Y")
        agency = Agency.objects.filter(station=user_station).values()[0]
        agency_name =  Station.objects.get(name = user_station)
        sig_img = None
        address_part_1 = None
        address_part_2 = None
        if agency_name.name == 'MOR-C':
            qr_code = ENV_CONFIG('MOR-C-QR-CODE')
        elif agency_name.name == 'FED-M':
            qr_code = ENV_CONFIG('FED-M-QR-CODE')
            sig_off = ENV_CONFIG('FED-M-SIG-OFFICER')
            sig_img = get_presigned_url(sig_off)
        elif agency_name.name == 'WBR2':
            qr_code = ENV_CONFIG('WBR2-QR-CODE')
            address_parts = agency['address'].split('Drive')
            address_part_1 = address_parts[0].strip() + " Drive"
            address_part_2 = address_parts[1].strip()
        elif agency_name.name == 'HUD-C':
            qr_code = ENV_CONFIG('HUD-C-QR-CODE')
        elif agency_name.name == 'MAR':
            qr_code = ENV_CONFIG('MAR-QR-CODE')
        elif agency_name.get('name') == 'WALS':
            qr_code = ENV_CONFIG('WALS-QR-CODE')
        elif agency_name.name == 'CLA':
            qr_code = ENV_CONFIG('CLA-QR-CODE')
        elif agency_name.name == 'FPLY-C':
            qr_code = ENV_CONFIG('FPLY-C-QR-CODE')
            address = per_choice['address']  
            if len(address) >= 27 or "PO" in address:
                person_address_part = address.split(",")
                if len(person_address_part) >= 2:
                    fply_address_part = person_address_part[0].strip() + ", <br>" + person_address_part[1].strip()
                else:
                    fply_address_part = address  
            else:
                fply_address_part = address
        elif agency_name.name == "KRSY-C":
            qr_code = ENV_CONFIG('KRSY-C-QR-CODE')
        else:
            qr_code = None
            sig_img = None
            
        
        if qr_code != None:
            s3_url_qr_code = get_presigned_url(qr_code)
        else:
            s3_url_qr_code = None

        if image_flow:
            plate_pic_base_url="" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
            'address_part_1': address_part_1,
            'address_part_2': address_part_2,
            'offence_time': offence_time,
            'date_app' : date_app,
            'fply_address_part' : fply_address_part
            }
        else:
            speed_pic_base_url = "" if cit_choice["speed_pic"].startswith("https") else BASE_URL
            plate_pic_base_url = "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
                'address_part_1': address_part_1,
                'address_part_2': address_part_2,
                'offence_time': offence_time,
                'date_app' : date_app,
                'fply_address_part' : fply_address_part
            }
        if image_flow:
            data["cit"]["location_name"] = Image.objects.get(id = data["cit"]["image_id"]).location_name
        else:
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
        # Decimals
        data["cit"]["fine"] = str(fine_instance.fine)
        if image_flow == False:
            data["vid"]["speed_time"] = str(data["vid"]["speed_time"])
            data["vid"]["datetime"] = str(data["vid"]["datetime"])
        # DateTime
        data["cit"]["datetime"] = str(data["cit"]["datetime"])
        data["agency"]["onboarding_dt"] = str(data["agency"]["onboarding_dt"])
        data["cit"]["speed_pic"] = get_presigned_url(data["cit"]["speed_pic"])
        if image_flow:
            data["cit"]["speed_pic"] = get_presigned_url(Image.objects.get(id = data["cit"]["image_id"]).speed_image_url)
            data["cit"]["plate_pic"] = get_presigned_url(Image.objects.get(id = data["cit"]["image_id"]).lic_image_url)
        else:
            data["cit"]["plate_pic"] = get_presigned_url(data["cit"]["plate_pic"])
        data["agency"]["badge_url"] = get_presigned_url(data["agency"]["badge_url"])
        print("")
        return data

def get_cit_refactor(citation_id, user_station ,status, image_flow=False, is_tattile=False):
        citation_obj = Citation.objects.get(citationID=citation_id)
        total = quick_pd_data.filter(ticket_num=citation_id, station=user_station).values()[
            0
        ]
        cit_choice = cit_agencies.filter(
            citationID=citation_id, station=user_station
        ).values()[0]
        if image_flow and is_tattile==False:
            adj_choice = image_agencies.filter(id = cit_choice["image_id"]).values()[0]
            offence_time = adj_choice['time']
        elif image_flow==False and is_tattile==False:
            adj_choice = video_agencies.filter(
                id=cit_choice["video_id"], station=user_station
            ).values()[0]
            offence_time = adj_choice['datetime'] 
        elif image_flow == False and is_tattile:
            adj_choice = Tattile.objects.filter(id=cit_choice["tattile_id"], station=user_station).values()[0]
            offence_time = adj_choice['image_time']
            

        veh_choice = veh_agencies.filter(
            id=cit_choice["vehicle_id"], station=user_station
        ).values()[0]
        per_choice = per_agencies.filter(id=cit_choice["person_id"]).values()[0]
        sup_data = sup_agencies.filter(citation=citation_obj, station=user_station).values()[0]
        dt = sup_data["timeApp"] + timedelta(days=30)
        date_app = sup_data["timeApp"] + timedelta(days=1)
        if citation_id in ['HUD-C-00000085', 'HUD-C-00000365']:
            due_date = '01/30/2025'
        elif citation_id in ['HUD-C-00000290', 'HUD-C-00000179', 'HUD-C-00000183', 
							'HUD-C-00000468', 'HUD-C-00000180', 'HUD-C-00000348']:
            due_date = '01/19/2025'
        elif citation_id in ['HUD-C-00001128', 'HUD-C-00000590', 
                             'HUD-C-00001081' , 'HUD-C-00000863', 'HUD-C-00001056']:
            due_date = '2/25/25'
        else:
            due_date = datetime.strftime(dt, "%m/%d/%Y")
        agency = Agency.objects.filter(station=user_station).values()[0]
        agency_name =  Station.objects.filter(id=user_station).values('name').first()
        sig_img = None
        address_part_1 = None
        address_part_2 = None
        fply_address_part = None
        if agency_name.get('name') == 'MOR-C':
            qr_code = ENV_CONFIG('MOR-C-QR-CODE')
        elif agency_name.get('name') == 'FED-M':
            qr_code = ENV_CONFIG('FED-M-QR-CODE')
            sig_off = ENV_CONFIG('FED-M-SIG-OFFICER')
            sig_img = get_presigned_url(sig_off)
        elif agency_name.get('name') == 'WBR2':
            qr_code = ENV_CONFIG('WBR2-QR-CODE')
            address_parts = agency['address'].split('Drive')
            address_part_1 = address_parts[0].strip() + " Drive"
            address_part_2 = address_parts[1].strip()
        elif agency_name.get('name') == 'HUD-C':
            qr_code = ENV_CONFIG('HUD-C-QR-CODE')
        elif agency_name.get('name') == 'MAR':
            qr_code = ENV_CONFIG('MAR-QR-CODE')
        elif agency_name.get('name') == 'WALS':
            qr_code = ENV_CONFIG('WALS-QR-CODE')
        elif agency_name.get('name') == 'FPLY-C':
            qr_code = ENV_CONFIG('FPLY-C-QR-CODE')
            address = per_choice.get('address', '')  
            if len(address) >= 27 or "PO" in address:
                person_address_part = address.split(",")
                if len(person_address_part) >= 2:
                    fply_address_part = person_address_part[0].strip() + ", <br>" + person_address_part[1].strip()
                else:
                    fply_address_part = address  
            else:
                fply_address_part = address
        elif agency_name.get('name') == "KRSY-C":
            qr_code = ENV_CONFIG('KRSY-C-QR-CODE')
            # else:
            #     address_lines = agency['address'].splitlines()
            #     address_part_1 = address_lines[0].strip() if len(address_lines) > 0 else ''
            #     address_part_2 = address_lines[1].strip() if len(address_lines) > 1 else ''
        else:
            qr_code = None
            sig_img = None
            
        
        if qr_code != None:
            s3_url_qr_code = get_presigned_url(qr_code)
        else:
            s3_url_qr_code = None

        if image_flow and is_tattile==False:
            plate_pic_base_url="" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
            'address_part_1': address_part_1,
            'address_part_2': address_part_2,
            'offence_time': offence_time,
            'date_app' : date_app,
            'fply_address_part': fply_address_part
            }
        elif image_flow == False and is_tattile==False:
            speed_pic_base_url = "" if cit_choice["speed_pic"].startswith("https") else BASE_URL
            plate_pic_base_url = "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
                'address_part_1': address_part_1,
                'address_part_2': address_part_2,
                'offence_time': offence_time,
                'date_app' : date_app,
                'fply_address_part': fply_address_part
            }
        elif image_flow == False and is_tattile == True:
            speed_pic_base_url = "" if cit_choice["speed_pic"].startswith("https") else BASE_URL
            plate_pic_base_url = "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
                'address_part_1': address_part_1,
                'address_part_2': address_part_2,
                'offence_time': offence_time,
                'date_app' : date_app,
                'fply_address_part': fply_address_part
            }
        if image_flow and is_tattile == False:
            data["cit"]["location_name"] = Image.objects.get(id = data["cit"]["image_id"]).location_name
        elif image_flow == False and is_tattile == False:
            location_instance = rl_agencies.get(id=data["cit"]["location_id"])
            data["cit"]["location_name"] = location_instance.location_name
        elif image_flow == False and is_tattile == True:
            location_instance = rl_agencies.get(id=data["cit"]["location_id"])
            data["cit"]["location_name"] = location_instance.location_name
            # data["cit"]["location_name"] = Tattile.objects.get(id = data["cit"]["tattile_id"]).location_name
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

        if fine_instance:
            data["cit"]["fine"] = str(fine_instance.fine)

        #data["cit"]["fine"] = str(fine_instance.fine) if data['cit']['current_citation_status'] != "EF" else CitationsWithEditFine.objects.filter(id=data["cit"]["id"]).first().new_fine
        if image_flow == False and is_tattile==False:
            data["vid"]["speed_time"] = str(data["vid"]["speed_time"])
            data["vid"]["datetime"] = str(data["vid"]["datetime"])
        # DateTime
        data["cit"]["datetime"] = str(data["cit"]["datetime"])
        data["agency"]["onboarding_dt"] = str(data["agency"]["onboarding_dt"])
        data["cit"]["speed_pic"] = get_presigned_url(data["cit"]["speed_pic"])
        if image_flow and is_tattile==False:
            data["cit"]["speed_pic"] = get_presigned_url(Image.objects.get(id = data["cit"]["image_id"]).speed_image_url)
            data["cit"]["plate_pic"] = get_presigned_url(Image.objects.get(id = data["cit"]["image_id"]).lic_image_url)
        elif image_flow == False and is_tattile==False:
            data["cit"]["plate_pic"] = get_presigned_url(data["cit"]["plate_pic"])
        elif image_flow==False and is_tattile==True :
            data["cit"]["speed_pic"] = get_presigned_url(Tattile.objects.get(id = data["cit"]["tattile_id"]).speed_image_url)

            data["cit"]["plate_pic"] = get_presigned_url(Tattile.objects.get(id = data["cit"]["tattile_id"]).license_image_url)
            
        badge_url = data.get("agency", {}).get("badge_url", "")
        data["agency"]["badge_url"] = get_presigned_url(badge_url) if badge_url else ""
        print("")
        if status == 'WARN-A':
            data["cit"]['is_warning'] = True
        else:
            data["cit"]['is_warning'] = False
        return data


def get_fine_by_id(fine_id):
    try:
        # Assuming fine_id is the primary key of the Fine model
        fine = Fine.objects.get(pk=fine_id)
        return fine
    except Fine.DoesNotExist:
        return None

def create_csv(stat):

    now = datetime.now()
    test_now = now.strftime("%m%d%Y")
    date = now.strftime("%Y-%m-%d")

    meta = csv_meta_agencies.filter(date__date=date, station=stat).values()
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
    for i in meta:
        citations.append(quick_pd_data.filter(id=int(i["quickPD_id"])).values()[0])
    data_frame = pd.DataFrame(data=citations)
    file_path = os.path.join(BASE_DIR, "media", f"{stat.name}-Citations-{test_now}.csv")

    data_frame.to_csv(
        file_path,
        index=False,
        header=False,
        columns=cols,
    )
    with open(file_path, "rb") as csv_file:
        upload_to_s3(csv_file, f"{stat.name}-Citations-{test_now}.csv", "csvs")
        os.remove(file_path)

def update_capture_date(request):
    citations = cit_agencies.filter(isApproved=True).order_by("-citationID")
    video_ids = citations.values_list('video_id',flat=True)
    video_details = video_agencies.filter(id__in=video_ids).values_list('VIDEO_NO', flat=True)

    for video_no in video_details:
        date = data_agencies.filter(VIDEO_NO=video_no).values_list('DATE', flat=True).first()
        if date:
            date_object = datetime.strptime(date, "%y%m%d")
            formatted_date = date_object.strftime("%Y-%m-%d")
            citations.filter(video_id__in=video_ids, video__VIDEO_NO=video_no).update(captured_date=formatted_date)
    return HttpResponse("", status=200)

def update_station_name_to_csv(request):
    csv_path = r'C:\Users\EM\Documents\file_converter\csv_file\Commercial Solution (Responses) - Form Responses 1.csv'
    
    if os.path.exists(csv_path):
        # now = datetime.datetime.now()
        df = pd.read_csv(csv_path)
        df = df.fillna(0)
        
        specific_column=df["Video No"]
        
        float_to_int = specific_column.astype(int)
        int_to_str = float_to_int.astype(str)
        test = list(int_to_str)
        location_name = []
        
        for j in range(len(test)):
            video_data = data_agencies.filter(VIDEO_NO__contains=test[j]).first()
            if test[j] != '0' and video_data != None:
                df.loc[j,"Station_name"] = video_data.STATION
            else:
                df.loc[j,"Station_name"] = "n/a"

        df_json = df.to_json(orient='records')

        response_data = {
            'status': 200,
            'data': df_json,
            'message': "Success"
        }

        return JsonResponse(response_data, status=200)

# generate_pdf_based on date code ------------------
def genrate_required_pdf(request, date):
    try:
        date_object = datetime.strptime(date, '%d-%m-%Y')
        date_corrected = date_object.strftime("%Y-%m-%d")

        station = csv_meta_agencies.filter(date__date=date_corrected).values('quickPD_id')
        
        quickPD_id_list = [] 
        for i in station:
            quickPD_id_list.append(i['quickPD_id'])
        
        citation_data_called_date = quick_pd_data.filter(id__in = quickPD_id_list).values()

        failed_drive = []

        for date_in in citation_data_called_date:
            cit_id = date_in['ticket_num']
            user_station = date_in['station_id']
            try:
                
                data = get_cit_refactor(cit_id, user_station, False, True)
                filename = f"{cit_id}.pdf"

                print(cit_id,'true')

                # if len(cit_id) == 12:
                #     station_name = cit_id[:3]
                if len(cit_id) == 13:
                    station_name = cit_id[:4]
                elif len(cit_id) == 14:
                    station_name = cit_id[:5]
                elif len(cit_id) == 15:
                    station_name = cit_id[:6]
                save_pdf_manual(filename, station_name,data)

            except Exception as e:
                print(e)
                failed_drive.append(cit_id)  

        print(failed_drive,f"failed_citation {len(failed_drive)} ")      
        message = {
            'message':"Successful"
        }
        return JsonResponse(message, status=200)
    
    except Exception as e:
        print(e)
        message = {
            'message':f"Something went wrong {e}"
        }
        return JsonResponse(message, status=400)

#generate pdf based on provided list of citataions
# def genrate_required_pdf(request):
#     try:
#         # date_object = datetime.strptime(date, '%d-%m-%Y')
#         # date_corrected = date_object.strftime("%Y-%m-%d")

#         # station = csv_meta_agencies.filter(date__date=date_corrected).values('quickPD_id')
        
#         # quickPD_id_list = [] 
#         # for i in station:
#         #     quickPD_id_list.append(i['quickPD_id'])
#         ticket_num = [
#             'KRSY-C-00006962',
#             'KRSY-C-00006971',
#             'KRSY-C-00007320',
#             'KRSY-C-00007512',
#             'KRSY-C-00007552',
#             'KRSY-C-00008077',
#             'KRSY-C-00008086',
#             'KRSY-C-00008096',
#             'KRSY-C-00008103',
#             'KRSY-C-00007106',
#             'KRSY-C-00007461',
#             'KRSY-C-00008060',
#             'KRSY-C-00009132'
#         ]
        
#         citation_data_called_date = quick_pd_data.filter(ticket_num__in = ticket_num).values()

#         failed_drive = []

#         for date_in in citation_data_called_date:
#             cit_id = date_in['ticket_num']
#             user_station = date_in['station_id']
#             try:
                
#                 data = get_cit_refactor(cit_id, user_station, False, True)
#                 filename = f"{cit_id}.pdf"

#                 print(cit_id,'true')

#                 # if len(cit_id) == 12:
#                 #     station_name = cit_id[:3]
#                 if len(cit_id) == 13:
#                     station_name = cit_id[:4]
#                 elif len(cit_id) == 14:
#                     station_name = cit_id[:5]
#                 elif len(cit_id) == 15:
#                     station_name = cit_id[:6]
#                 save_pdf_manual(filename, station_name,data)

#             except Exception as e:
#                 print(e)
#                 failed_drive.append(cit_id)  

#         print(failed_drive,f"failed_citation {len(failed_drive)} ")      
#         message = {
#             'message':"Successful"
#         }
#         return JsonResponse(message, status=200)
    
#     except Exception as e:
#         print(e)
#         message = {
#             'message':f"Something went wrong {e}"
#         }
#         return JsonResponse(message, status=400)
    
def create_manual_csv(stat,date):

    now = datetime.now()

    date_object = datetime.strptime(date, '%d-%m-%Y')
    test_now = date_object.strftime('%m%d%Y')

    date_corrected = date_object.strftime("%Y-%m-%d")

    meta = csv_meta_agencies.filter(date__date=date_corrected, station=stat).values()
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
    for i in meta:
        citations.append(quick_pd_data.filter(id=int(i["quickPD_id"])).values()[0])
    data_frame = pd.DataFrame(data=citations)
    file_path = os.path.join(BASE_DIR, "media", f"{stat.name}-Citations-{test_now}.csv")

    folder_path_new = fr'C:\Users\EM\Documents\manual_csv\{stat.name}'
    file_path_new = f'{stat.name}-Citations-{test_now}.csv'
    file_path_HUD_C = r'C:\Users\EM\Documents\csvs\HUD-C\HUD-C-paid_citations.csv'
    # file_path_KRSY_C = r'C:\Users\EM\Documents\manual_csv\KRSY-C\KRSY-C-Citations-06112025.csv'

    # if stat.name == 'KRSY-C':
    #     file_path = file_path_KRSY_C
    #     fine = 0.00
    #     agency_name = 'Kersey Colorado'
    #     xpress_csv(file_path,fine,agency_name)
    if stat.name in ['FED-M','WBR2','HUD-C']:
        file_path = folder_path_new + "\\" + file_path_new
        if stat.name == 'FED-M':
            fine = 40.00
            agency_name = 'Federalsburg Police Department'
        elif stat.name =='WBR2':
            fine = 150.00
            agency_name = 'Ward 2 West Baton Rouge Parish'
        elif stat.name =='HUD-C':
            fine = 40.00
            agency_name = 'Hudson Colorado'
            xpress_csv(file_path,fine,agency_name)
    
    else:  
        data_frame.to_csv(
            file_path,
            index=False,
            header=False,
            columns=cols,
        )
    with open(file_path, "rb") as csv_file:
        # upload_to_s3(csv_file, f"{stat.name}-Citations-{test_now}-manual.csv", "csvs")
        upload_to_s3(csv_file, f"{stat.name}-Citations-paid_citations.csv", "csvs")
        if stat.name in  ['MOR-C', 'FED-M']:
            pass

def genrate_required_csv(request,date):
    try:
        date_object = datetime.strptime(date, '%d-%m-%Y')
        date_corrected = date_object.strftime("%Y-%m-%d")

        station = csv_meta_agencies.filter(date__date=date_corrected).values('station_id')
        station_id = []

        for i in station:
            if i not in station_id:
                station_id.append(i)
        
        for stat in station_id:
            print(stat['station_id'])
            station_object = Station.objects.get(id = stat['station_id'])
            print(station_object,"station_object here ==============")
            create_manual_csv(station_object,date)

        message = {
            'message':"Successful"
        }
        return JsonResponse(message, status=200)
    
    except Exception as e:
        print(e)
        message = {
            'message':f"Something went wrong {e}"
        }
        return JsonResponse(message, status=400)       
    
def populate_station_id_view(request):
    output = []
    output.append("Populating station_id in Image table<br>")

    # Fetch all images where station is not set
    images = Image.objects.filter(station__isnull=True)

    for image in images:
        try:
            # Find the corresponding road_location using trafficlogix_location_id
            location = road_location.objects.get(trafficlogix_location_id=image.location_id)
            image.station = location.station  # Set the station in the Image table
            image.save()
            output.append(f"Set station_id {location.station.id} for image {image.id}<br>")
        except road_location.DoesNotExist:
            output.append(f"No matching road_location found for image {image.id} with trafficlogix_location_id {image.location_id}<br>")
        except road_location.MultipleObjectsReturned:
            output.append(f"Multiple road_locations found for image {image.id} with trafficlogix_location_id {image.location_id}<br>")

    output.append("Successfully populated station_id in Image table<br>")
    return HttpResponse("".join(output))

def daily_report_generator():
    csv_directory = r'C:\Users\EM\Documents\daily_report_csv'
   
    # Ensure the directory exists
    if not os.path.exists(csv_directory):
        os.makedirs(csv_directory)
    yesterday = datetime.now() - timedelta(days=1)
    specific_date_str = yesterday.strftime('%Y-%m-%d')
    specific_date = yesterday.strftime('%Y%m%d')
   
    csv_file = os.path.join(csv_directory, f'daily_report_{specific_date}.csv')
    if os.path.exists(csv_file):
        os.remove(csv_file)
 
    station_agency_data = []
 
    for station in Station.objects.all():
        agencies = Agency.objects.filter(station=station,is_active=True)
        for agency in agencies:
            adjudicated_count_images = adj_metadata.objects.filter(
                station=station, image__isnull=False, timeAdj__date=specific_date_str
            ).count()
            adjudicated_count_videos = adj_metadata.objects.filter(
                station=station, video__isnull=False, timeAdj__date=specific_date_str
            ).count()
           
            adjudicated_count_tattile = adj_metadata.objects.filter(
                station=station, tattile__isnull=False, timeAdj__date=specific_date_str
            ).count()
 
            approved_count_images = sup_metadata.objects.filter(
                station=station, citation__image__isnull=False, timeApp__date=specific_date_str, isApproved=True
            ).count()
            approved_count_videos = sup_metadata.objects.filter(
                station=station, citation__video__isnull=False, timeApp__date=specific_date_str, isApproved=True
            ).count()
            approved_count_tattile = sup_metadata.objects.filter(
                station=station, citation__tattile__isnull=False, timeApp__date=specific_date_str, isApproved=True
            ).count()
 
            isSkipped_count = DuncanSubmission.objects.filter(
                station=station, image__isnull=False, video__isnull=False,
                isSkipped=True, submitted_date=specific_date_str
            ).count()
 
            videos_inserted_today = Data.objects.filter(
                            DATE=specific_date[2:], STATION = station.name
                        ).values('VIDEO_NAME').distinct().count()
 
            images_inserted_today = Image.objects.filter(
                station=station, time__date=specific_date_str
            ).count()
           
            tattile_ticket_upload = Tattile.objects.filter(
                station=station, image_time__date=specific_date_str,is_active = True
            ).count()
           
            station_agency_data.append({
                "station_id": station.id,
                "agency_name": agency.name,
                "adjudicated_count_videos": adjudicated_count_videos,
                "adjudicated_count_images": adjudicated_count_images,
                "approved_count_videos": approved_count_videos,
                "approved_count_images": approved_count_images,
                "isSkipped_count": isSkipped_count,
                "videos_inserted_today": videos_inserted_today,
                "images_inserted_today": images_inserted_today,
                "tattile_ticket_upload" : tattile_ticket_upload,
                "adjudicated_tattile" : adjudicated_count_tattile,
                "approved_tattile" : approved_count_tattile
            })
 
    # Write the data to a CSV file
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
       
        # Write the header
        writer.writerow(['', '', '','', f"Ticket and Citation Report for {specific_date}"])
        writer.writerow([])
        writer.writerow(["Agency_name",
                         "Docker Videos Uploaded","TrafficLogix Images Uploaded", "Tattile Ticket Upload" ,
                         "Adjudicated Videos", "Adjudicated Images", "Adjudicated Tattile" ,
                         "Approved Videos", "Approved Images", "Approved Tattile",
                         "Skipped Count"
                        ])
 
        # Write the data rows
        for data in station_agency_data:
            writer.writerow([ data["agency_name"],
                             data["videos_inserted_today"],data["images_inserted_today"] , data["tattile_ticket_upload"],
                             data["adjudicated_count_videos"], data["adjudicated_count_images"], data["adjudicated_tattile"],
                             data["approved_count_videos"], data["approved_count_images"], data["approved_tattile"],
                             data["isSkipped_count"],
                             ])
           
    subject = f"Daily Report for {specific_date}"
    body = f"Please find attached the daily report for {specific_date}."
    cc_emails = "karthik.k@globaldigitalnext.com,sumith.b@globaldigitalnext.com,tejas.g@globaldigitalnext.com,raju.v@globaldigitalnext.com"    
    to_email = "leahsarpy@gmail.com,craig@emergentenforcement.com,rsarpy@emergentenforcement.com,russeljr@emergentenforcement.com,leah@emergentenforcement.com"
    ses_client = SESClient()
    ses_client.send_email_with_attachment(
        subject=subject, body=body, attachment_path=csv_file, to_addresses=to_email.split(","), cc_addresses=cc_emails.split(","))    
 
    return HttpResponse(f"Data saved to {csv_file}", content_type='text/plain')


def update_master_date(request):
    try:
        entries = DuncanMasterData.objects.all()
        for entry in entries:
            entry.lic_plate = entry.lic_plate.strip()
            entry.save()
        
        message = {
                'message':"Successful"
            }
        return JsonResponse(message, status=200)
    
    except Exception as e:
        print(e)
        message = {
            'message':f"Something went wrong {e}"
        }
        return JsonResponse(message, status=400)

def see_notice_pdf(request, filename):
    """
    Serves the generated PDF file as a response to the user.
    This function retrieves the file from the local storage directory.
    """
    if "first-mailer" in filename:
        path = "pre_odr_first_mailer_pdfs/" + filename
    elif "second-mailer" in filename:
        path = "pre_odr_second_mailer_pdfs/" + filename
    else:
        path = ""
    pdf_content = s3_get_file(path)
    if request.user.is_authenticated:
        return FileResponse(BytesIO(pdf_content), content_type="application/pdf")
    else:
        return render(request, "diff-base.html")
    
def process_unpaid_doc_files(file_data):
    ticket_pattern = re.compile(r'(?P<ticket_number>\S+)\s+(?P<off_date>\d{2}/\d{2}/\d{4})\s+(?P<arr_date>\d{2}/\d{2}/\d{4})\s+(?P<amount>\d+\.\d{2})\s+(?P<payment>\d+\.\d{2})\s+(?P<balance>\d+\.\d{2})')
    return extract_citations(file_data, ticket_pattern)

def process_unpaid_txt_files(file_data):
    ticket_pattern = re.compile(r'(\S+)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+(\d+\.\d{2})\s+(\d+\.\d{2})\s+(\d+\.\d{2})')
    return extract_citations(file_data, ticket_pattern)

def extract_citations(file_data, ticket_pattern):
    citations = []
    for line in file_data:
        match = ticket_pattern.match(line.strip())
        if match:
            original_citation = Citation.objects.filter(citationID = match.group(1)).first()
            citation = {
                'ticket_number': match.group(1),
                'off_date': datetime.strptime(match.group(2), '%m/%d/%Y').date(),
                'arr_date': datetime.strptime(match.group(3), '%m/%d/%Y').date(),
                'amount': Decimal(match.group(4)),
                'payment': Decimal(match.group(5)),
                'balance': Decimal(match.group(6)),
                'pre_odr_mail_count': 0,
                'isApproved': False,
                'video' : original_citation.video,
                'image' : original_citation.image,
                'full_name' : original_citation.person.first_name + " " + original_citation.person.middle + " " + original_citation.person.last_name,
                'station': original_citation.station,
            }
            citations.append(citation)
    return citations


def date_hirerachy(citation_dates):
    date_hierarchy = {}
    for date in citation_dates:
        year = date.year
        month = month_name[date.month]  # Full month name like "January"
        day = date.day
        
        if year not in date_hierarchy:
            date_hierarchy[year] = {}
        
        if month not in date_hierarchy[year]:
            date_hierarchy[year][month] = []
        
        date_hierarchy[year][month].append(day)
    return date_hierarchy
 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
import os

UPLOAD_DIR_NON_VIOLATION = r"C:\Users\Administrator\Documents\ees\media\upload\uploads\non_violation"
UPLOAD_DIR_VIOLATION = r"C:\Users\Administrator\Documents\ees\media\upload\uploads\violation"
UPLOAD_DIR_DAILY_CSV = r"C:\Users\Administrator\Documents\ees\media\upload\uploads\dailycsv"
DIAGONISTIC_DIR_VIOLATION = r"C:\Users\Administrator\Documents\ees\media\upload\uploads\Diagnostic"
def extract_filename_from_headers(request):
    # Get the Content-Disposition header
    content_disposition = request.headers.get('Content-Disposition', '')

    # Try to find the filename using a regular expression
    match = re.search(r'filename="([^"]+)"', content_disposition)
    if match:
        return match.group(1)  # Return the filename if found
    else:
        return None 
class FileUploadViewNonViolation(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content_type = request.content_type

        if content_type.startswith("image/") or content_type.startswith("application/"):
            filename = extract_filename_from_headers(request)
            print("File Name: " , filename)
            if not filename:
                return Response({"error": "Missing 'X-Filename' header for raw uploads"}, status=400)

            file_path = os.path.join(UPLOAD_DIR_NON_VIOLATION, filename)
            with open(file_path, "wb") as f:
                f.write(request.body)

            return Response({"message": "File uploaded successfully (raw)", "filename": filename})
        
        return Response({"error": "Unsupported Media Type"}, status=415)

class FileUploadViewViolation(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content_type = request.content_type
        print(content_type, "Content type")
        if content_type.startswith("image/") or content_type.startswith("application/") or content_type.startswith("video/"):
            filename = extract_filename_from_headers(request)
            print("File Name: " , filename)
            if not filename:
                return Response({"error": "Missing 'X-Filename' header for raw uploads"}, status=400)

            file_path = os.path.join(UPLOAD_DIR_VIOLATION, filename)
            with open(file_path, "wb") as f:
                f.write(request.body)

            return Response({"message": "File uploaded successfully (raw)", "filename": filename})
        
        return Response({"error": "Unsupported Media Type"}, status=415)
    
class FileUploadViewDailyCSV(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content_type = request.content_type
        print(content_type, "Content type")
        if content_type.startswith("image/") or content_type.startswith("application/") or content_type.startswith("video/"):
            filename = extract_filename_from_headers(request)
            print("File Name: " , filename)
            if not filename:
                return Response({"error": "Missing 'X-Filename' header for raw uploads"}, status=400)

            file_path = os.path.join(UPLOAD_DIR_DAILY_CSV, filename)
            with open(file_path, "wb") as f:
                f.write(request.body)

            return Response({"message": "File uploaded successfully (raw)", "filename": filename})
        
        return Response({"error": "Unsupported Media Type"}, status=415)

class FileUploadViewDiagonistic(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content_type = request.content_type

        if content_type.startswith("application/"):
            filename = extract_filename_from_headers(request)
            print("File Name: " , filename)
            if not filename:
                return Response({"error": "Missing 'X-Filename' header for raw uploads"}, status=400)

            file_path = os.path.join(DIAGONISTIC_DIR_VIOLATION, filename)
            with open(file_path, "wb") as f:
                f.write(request.body)

            return Response({"message": "File uploaded successfully (raw)", "filename": filename})
        
        return Response({"error": "Unsupported Media Type"}, status=415)

def update_capture_date(request):
    try:
        
        # results = Citation.objects.filter(
        #     captured_date__year=2024,
        #     citationID__icontains='HUD-C',
        #     citationID__gte='HUD-C-00001829',
        #     isApproved=True,
        #     isRejected=False,
        #     isSendBack=False,
        #     isRemoved=True
        # ).order_by('-citationID')
        
        # for i in results:
        #     video_no = Video.objects.get(id=i.video.id)
        #     date = data_agencies.filter(VIDEO_NO=video_no.VIDEO_NO, VIDEO_NAME = video_no.caption[:20]).values_list('DATE', flat=True).first() 
        #     date_object = datetime.strptime(date, "%y%m%d")
        #     formatted_date = date_object.strftime("%Y-%m-%d")
            
        #     i.captured_date = formatted_date
            
        results = Citation.objects.select_related('video').filter(
            captured_date__year=2024,
            citationID__icontains='HUD-C',
            citationID__gte='HUD-C-00001829',
            isApproved=True,
            isRejected=False,
            isSendBack=False,
            isRemoved=True
        ).order_by('-citationID')

        for citation in results:
            video = citation.video  
            caption_snippet = video.caption[:20] if video.caption else ""
            
            date_str = data_agencies.filter(
                VIDEO_NO=video.VIDEO_NO,
                VIDEO_NAME=caption_snippet
            ).values_list('DATE', flat=True).first()

            if date_str:
                try:
                    date_object = datetime.strptime(date_str, "%y%m%d")
                    formatted_date = date_object.strftime("%Y-%m-%d")
                    citation.captured_date = formatted_date
                    citation.save()
                except ValueError:
                    print(f"Invalid date format: {date_str}")
            else:
                print(f"No date found for VIDEO_NO={video.VIDEO_NO}, VIDEO_NAME={caption_snippet}")
            
        message = {
            'message':"Successful"
        }
        return JsonResponse(message, status=200)
    
    except Exception as e:
        print(e)
        message = {
            'message':f"Something went wrong {e}"
        }
        return JsonResponse(message, status=400)


def get_reminder_hud_c_cit(citation_id, user_station , image_flow=False):
        
        citation_obj = Citation.objects.get(citationID=citation_id)
        total = quick_pd_data.filter(ticket_num=citation_id, station=user_station).values()[
            0
        ]
        cit_choice = cit_agencies.filter(
            citationID=citation_id, station=user_station
        ).values()[0]
        
        adj_choice = video_agencies.filter(
            id=cit_choice["video_id"], station=user_station
        ).values()[0]
        offence_time = adj_choice['datetime'] 

        veh_choice = veh_agencies.filter(
            id=cit_choice["vehicle_id"], station=user_station
        ).values()[0]
        
        per_choice = per_agencies.filter(id=cit_choice["person_id"]).values()[0]
        sup_data = sup_agencies.filter(citation=citation_obj, station=user_station).values()[0]
        
        approve_date = datetime.now()
        date_app = approve_date.strftime("%m/%d/%Y")
        due_date_dt = approve_date + timedelta(days=30)
        due_date = due_date_dt.strftime("%m/%d/%Y")
        
        agency = Agency.objects.filter(station=user_station).values()[0]
        agency_name =  Station.objects.get(name = user_station)
        sig_img = None
        address_part_1 = None
        address_part_2 = None
        
        if agency_name.name == 'HUD-C':
            qr_code = ENV_CONFIG('HUD-C-QR-CODE')
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
            'address_part_1': address_part_1,
            'address_part_2': address_part_2,
            'offence_time': offence_time,
            'date_app' : date_app,
        }
        
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
        data["agency"]["badge_url"] = get_presigned_url(data["agency"]["badge_url"])
        return data

def hud_c_reminder_mail(request):
    try:
        station_id = Station.objects.get(id= 38)
        user_station = 38
        station_name = "HUD-C"
        cit_ids = ['HUD-C-00001474',
                'HUD-C-00001426',
                'HUD-C-00001233',
                'HUD-C-00001549',
                'HUD-C-00001333',
                'HUD-C-00001556',
                'HUD-C-00000181',
                'HUD-C-00001325',
                'HUD-C-00001342',
                'HUD-C-00001515',
                'HUD-C-00001531',
                'HUD-C-00001602'
                ]
        for cit_id in cit_ids:
            data = get_reminder_hud_c_cit(cit_id, station_id)
            filename = f"{cit_id}.pdf"
            check_pdf = save_reminder_hudc_pdf(filename, station_name, data)
            message = {
                'message':"Successful"
            }
        return JsonResponse(message, status=200)
    except Exception as e:
        print(e)
        message = {
            'message':f"Something went wrong {e}"
        }
        return JsonResponse(message, status=400)
    

folder_path =r'C:\Users\Administrator\Documents\ees\media\upload\uploads\violation'

def fix_json_structure_in_place(folder_path):
    for dirpath, _, filenames in os.walk(folder_path):
        for filename in filenames:
            if filename.endswith('.json'):
                json_path = os.path.join(dirpath, filename)
                with open(json_path, 'r', encoding='utf-8') as file:
                    raw = file.read()
                fixed = re.sub(r'(\})\s*(")', r'\1,\n\2', raw)
                try:
                    json.loads(fixed)
                    with open(json_path, 'w', encoding='utf-8') as file:
                        file.write(fixed)
                except json.JSONDecodeError:
                    continue


def make_aware_datetime(ts_str):
    dt_str = ts_str.replace('_', ' ')
    dt_obj = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S.%f')
    return make_aware(dt_obj)


def extract_base_filename(filename):
    if not filename.endswith('.json'):
        return None
    return os.path.splitext(filename)[0]  # Remove .json


def process_single_json(json_path, base_filename, all_files):
    try:
        with open(json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        data['transit'].pop('image', None)
        data['transit'].pop('image_ctx', None)
        location_name=data['device']['site']['name']

        if location_name == 'KRSY WCR49 north':
            station = Station.objects.get(id = 44)
            location_id = 158
        elif location_name == 'HUD WRC49':
            station = Station.objects.get(id = 38)
            location_id = 127
        else:
            station = None
            location_id = None
        plate_text = data['transit']['plate']['text']  # ✅ Extract plate from JSON
        tattile_check = Tattile.objects.filter(ticket_id = data['transit']['uuid']).exists()
        if not tattile_check:
            tattile_data, created  = Tattile.objects.get_or_create(
                version=data['device']['version']['application'],
                camera_name=data['device']['site']['name'],
                serial_number=data['device']['serial_number'],
                time_zone=data['device']['time_zone'],
                ticket_id=data['transit']['uuid'],
                start_date=make_aware_datetime(data['transit']['timestamps']['start']),
                end_date=make_aware_datetime(data['transit']['timestamps']['end']),
                image_time=make_aware_datetime(data['transit']['timestamps']['image']),
                country=data['transit']['plate']['country'],
                plate_text=plate_text,
                score=data['transit']['plate']['score'],
                measured_speed=data['transit']['violation_data']['measured_speed'],
                speed_limit=data['transit']['violation_data']['speed_limit'],
                speed_unit='mi/h',
                location_id = location_id,
                location_name=location_name,
                station=station,
                custom_counter=1,
            )

            tattile_files = []
            for file in all_files:
                if file.startswith(base_filename):
                    local_path = os.path.join(os.path.dirname(json_path), file)
                    s3_file_name = file
                    s3_folder_name = ENV_CONFIG("AWS_TATTILE_FOLDER")
                    s3_bucket_name = ENV_CONFIG("AWS_S3_BUCKET_NAME")
                    file_url = s3_upload_file(local_path, s3_file_name, s3_folder_name, s3_bucket_name)
                    file_type_num = (
                                3 if s3_file_name.endswith(".json")
                                else 1 if s3_file_name.endswith(".mp4")
                                else 2 
                            )
                    tattile_files.append(TattileFile(
                        ticket_id=data['transit']['uuid'],
                        file_name=s3_file_name,
                        file_url=file_url,
                        file_type=file_type_num,
                        station=station,
                        tattile=tattile_data
                    ))

            TattileFile.objects.bulk_create(tattile_files)
        else:
            print("Ticket ID Present in Records")
    except Exception as e:
        print(f"Failed processing {json_path}: {e}")


def read_json_excluding_image():
    folder_path = r'C:\Users\Administrator\Documents\ees\media\upload\uploads\violation'
    fix_json_structure_in_place(folder_path)

    station = Station.objects.get(id=44)
    all_files = []
    json_files = []

    for dirpath, _, filenames in os.walk(folder_path):
        all_files.extend(filenames)
        for filename in filenames:
            if filename.endswith(".json"):
                json_path = os.path.join(dirpath, filename)
                base_filename = extract_base_filename(filename)
                if base_filename:
                    json_files.append((json_path, base_filename))

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_single_json, json_path, base_filename, all_files)
                   for json_path, base_filename in json_files]
        for future in as_completed(futures):
            future.result()

    return JsonResponse({"status": "success", "message": "Bulk upload completed"})


# def genrate_required_pdf(request,date):
#     try:
#         date_object = datetime.strptime(date, '%d-%m-%Y')
#         date_corrected = date_object.strftime("%Y-%m-%d")

#         station = csv_meta_agencies.filter(date__date=date_corrected).values('quickPD_id')
        
#         quickPD_id_list = [] 
#         for i in station:
#             quickPD_id_list.append(i['quickPD_id'])

#         citation_data_called_date = quick_pd_data.filter(id__in = quickPD_id_list).values()

#         failed_drive = []

#         for date_in in citation_data_called_date:
#             cit_id = date_in['ticket_num']
#             user_station = date_in['station_id']
#             try:
                
#                 data = get_cit_refactor(cit_id, user_station, False, True)
#                 filename = f"{cit_id}.pdf"

#                 print(cit_id,'true')

#                 # if len(cit_id) == 12:
#                 #     station_name = cit_id[:3]
#                 if len(cit_id) == 13:
#                     station_name = cit_id[:4]
#                 elif len(cit_id) == 14:
#                     station_name = cit_id[:5]
#                 elif len(cit_id) == 15:
#                     station_name = cit_id[:6]
#                 save_pdf_manual(filename, station_name,data)

#             except Exception as e:
#                 print(e)
#                 failed_drive.append(cit_id)  

#         print(failed_drive,f"failed_citation {len(failed_drive)} ")      
#         message = {
#             'message':"Successful"
#         }
#         return JsonResponse(message, status=200)
    
#     except Exception as e:
#         print(e)
#         message = {
#             'message':f"Something went wrong {e}"
#         }
#         return JsonResponse(message, status=400)


import boto3
import requests
import tempfile
from urllib.parse import urlparse
from PIL import Image as PilImage
from ees.utils import s3_client

# s3 = S3Client().client

BUCKET_NAME = AWS_S3_BUCKET_NAME
AWS_S3_EXPECTED_OWNER = ENV_CONFIG("AWS_ACCOUNT_OWNER_ID")

def delete_s3_file(s3_url):
    key = urlparse(s3_url).path.lstrip('/')
    try:
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=key, ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER)
        print(f"Deleted: {key}")
    except Exception as e:
        print(f"Error deleting {key}: {e}")

def update_speed_frame_tattile(request):
    try:
        citation_ids = sup_metadata.objects.filter(
            timeApp__date=date(2025, 6, 13),
            station_id=38,
            isApproved = True
        ).values_list('citation_id', flat=True)
        tattile_citation = []
        # citations = Citation.objects.filter(
        #     id__in=citation_ids,
        #     tattile_id__isnull=False
        # )
        citations = Citation.objects.filter(
            citationID__in=tattile_citation,
            tattile_id__isnull=False
        )
        tattile_ids = citations.values_list('tattile_id', flat=True)
        tattile_data = Tattile.objects.filter(id__in=tattile_ids)

        failed_citations = []
        print(tattile_data.count(), "citation count")
        for tattile in tattile_data:
            try:
                image_time = tattile.image_time 
                
                image_time_only = image_time.time()
                timestamp_str = image_time.strftime('%Y-%m-%d_%H-%M-%S-%f')[:-3] 
                ticket_id = tattile.ticket_id

                # 1. Get TattileFile for this ticket_id (file_type=2 is speed image)
                
                # if time(5, 0) <= image_time_only < time(20, 0):
                tfile = TattileFile.objects.filter(
                    ticket_id=ticket_id,
                    file_type=2,
                    is_active=True,
                    file_name__icontains='_CTX'
                ).first()
                # else:
                    # Night (6PM–6AM): get file WITHOUT '_CTX' (black & white)
                # tfile = TattileFile.objects.filter(
                #     ticket_id=ticket_id,
                #     file_type=2,
                #     is_active=True
                # ).exclude(file_name__icontains='_CTX').first()

                if not tfile:
                    raise Exception(f"No TattileFile found for ticket_id={ticket_id}")

                file_url = get_presigned_url(tfile.file_url)

                # 2. Delete old speed image if present
                if tattile.speed_image_url:
                    delete_s3_file(tattile.speed_image_url)

                # 3. Download the image
                response = requests.get(file_url)
                if response.status_code != 200:
                    raise Exception(f"Failed to download file for ticket_id={ticket_id}")

                image_bytes = BytesIO(response.content)
                img = Image.open(image_bytes).convert("RGB")  # Ensure no alpha/transparency issues

                # Always convert and upload as PNG
                extension = 'png'
                content_type = 'image/png'
                new_filename = f"{ticket_id}.{extension}"
                s3_key = f"PGM2/speed/{new_filename}"

                # 4. Save and upload
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp:
                    img.save(tmp, format=img.format)
                    temp_path = tmp.name

                s3_client.upload_file(
                    Filename=temp_path,
                    Bucket=BUCKET_NAME,
                    Key=s3_key,
                    ExtraArgs={'ContentType': content_type}
                )
                new_speed_url = f"https://ee-prod-s3-bucket.s3.us-east-2.amazonaws.com/PGM2/speed/{new_filename}"
                # 5. Update Citation
                Citation.objects.filter(tattile=tattile).update(speed_pic=new_speed_url)

                os.remove(temp_path)

            except Exception as e:
                print(f"❌ Error for Tattile ID {tattile.id}: {e}")
                failed_citations.append(tattile.id)

        return JsonResponse({
            "message": "Speed frame updated successfully",
            "failed_ids": failed_citations
        }, status=200)

    except Exception as e:
        return JsonResponse({
            "message": f"Something went wrong: {e}"
        }, status=400)
    
def get_original_cit_refactor_approved_table(citation_id, user_station , image_flow=False, is_tattile=False):
    citation_obj = Citation.objects.get(citationID=citation_id)
    total = quick_pd_data.filter(ticket_num=citation_id, station=user_station).values()[
        0
    ]
    cit_choice = cit_agencies.filter(
        citationID=citation_id, station=user_station
    ).values()[0]
    if image_flow and is_tattile==False:
        adj_choice = image_agencies.filter(id = cit_choice["image_id"]).values()[0]
        offence_time = adj_choice['time']
    elif image_flow==False and is_tattile==False:
        adj_choice = video_agencies.filter(
            id=cit_choice["video_id"], station=user_station
        ).values()[0]
        offence_time = adj_choice['datetime'] 
    elif image_flow == False and is_tattile:
        adj_choice = Tattile.objects.filter(id=cit_choice["tattile_id"], station=user_station).values()[0]
        offence_time = adj_choice['image_time']

    veh_choice = veh_agencies.filter(
        id=cit_choice["vehicle_id"], station=user_station
    ).values()[0]
    if cit_choice["current_citation_status"] == "UA":
        print("Inside person, Original address ")
        cwua = CitationsWithUpdatedAddress.objects.filter(
            citation=citation_obj
        ).values()[0]
        
        per_choice = Person(
            station  = citation_obj.station,
            first_name = citation_obj.person.first_name,
            last_name = citation_obj.person.last_name,
            address = cwua.get('old_address', ''),
            city = cwua.get('old_city', ''),
            state = cwua.get('old_person_state', ''),
            zip = cwua.get('old_zip', '')
        )
    elif cit_choice["current_citation_status"] == "TL":
        cwtl = CitationsWithTransferOfLiabilty.objects.filter(
            citation=citation_obj
        ).first()
        per_choice = cwtl.old_person
    else:
        per_choice = per_agencies.filter(id=cit_choice["person_id"]).values()[0]
    sup_data = sup_agencies.filter(citation=citation_obj, station=user_station).values()[0]
    dt = sup_data["originalTimeApp"] + timedelta(days=30)
    date_app = sup_data["originalTimeApp"] + timedelta(days=1)
    if citation_id in ['HUD-C-00000085', 'HUD-C-00000365']:
        due_date = '01/30/2025'
    elif citation_id in ['HUD-C-00000290', 'HUD-C-00000179', 'HUD-C-00000183', 
          'HUD-C-00000468', 'HUD-C-00000180', 'HUD-C-00000348']:
        due_date = '01/19/2025'
    elif citation_id in ['HUD-C-00001128', 'HUD-C-00000590', 
                         'HUD-C-00001081' , 'HUD-C-00000863', 'HUD-C-00001056']:
        due_date = '2/25/25'
    else:
        due_date = datetime.strftime(dt, "%m/%d/%Y")
    agency = Agency.objects.filter(station=user_station).values()[0]
    agency_name =  Station.objects.filter(id=user_station).values('name').first()
    sig_img = None
    address_part_1 = None
    address_part_2 = None
    fply_address_part = None
    if agency_name.get('name') == 'MOR-C':
        qr_code = ENV_CONFIG('MOR-C-QR-CODE')
    elif agency_name.get('name') == 'FED-M':
        qr_code = ENV_CONFIG('FED-M-QR-CODE')
        sig_off = ENV_CONFIG('FED-M-SIG-OFFICER')
        sig_img = get_presigned_url(sig_off)
    elif agency_name.get('name') == 'WBR2':
        qr_code = ENV_CONFIG('WBR2-QR-CODE')
        address_parts = agency['address'].split('Drive')
        address_part_1 = address_parts[0].strip() + " Drive"
        address_part_2 = address_parts[1].strip()
    elif agency_name.get('name') == 'HUD-C':
        qr_code = ENV_CONFIG('HUD-C-QR-CODE')
    elif agency_name.get('name') == 'MAR':
        qr_code = ENV_CONFIG('MAR-QR-CODE')
    elif agency_name.get('name') == 'CLA':
        qr_code = ENV_CONFIG('CLA-QR-CODE')
    elif agency_name.get('name') == 'WALS':
        qr_code = ENV_CONFIG('WALS-QR-CODE')
    elif agency_name.get('name') == 'FPLY-C':
        qr_code = ENV_CONFIG('FPLY-C-QR-CODE')
        if cit_choice["current_citation_status"] == "UA":
            address = cwua.get('old_address', '')
            if len(address) >= 27 or "PO" in address:
                person_address_part = address.split(",")
                if len(person_address_part) >= 2:
                    fply_address_part = person_address_part[0].strip() + ", <br>" + person_address_part[1].strip()
                else:
                    fply_address_part = address
            else:
                fply_address_part = address 
        elif cit_choice["current_citation_status"] == "TL":
            # address = cwtl.old_person
            person_address = cwtl.old_person.address
            if len(person_address) >= 27 or "PO" in person_address:
                person_address_part = person_address.split(",")
                if len(person_address_part) >= 2:
                    fply_address_part = person_address_part[0].strip() + ", <br>" + person_address_part[1].strip()
                else:
                    fply_address_part = person_address  
            else:
                fply_address_part = person_address
        else:
            pass
    elif agency_name.get('name') == "KRSY-C":
        qr_code = ENV_CONFIG('KRSY-C-QR-CODE')
        # else:
        #     address_lines = agency['address'].splitlines()
        #     address_part_1 = address_lines[0].strip() if len(address_lines) > 0 else ''
        #     address_part_2 = address_lines[1].strip() if len(address_lines) > 1 else ''
    else:
        qr_code = None
        sig_img = None


    if qr_code != None:
        s3_url_qr_code = get_presigned_url(qr_code)
    else:
        s3_url_qr_code = None

    if image_flow and is_tattile==False:
        plate_pic_base_url="" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
        'address_part_1': address_part_1,
        'address_part_2': address_part_2,
        'offence_time': offence_time,
        'date_app' : date_app,
        'fply_address_part': fply_address_part
        }
    elif image_flow == False and is_tattile==False:
        speed_pic_base_url = "" if cit_choice["speed_pic"].startswith("https") else BASE_URL
        plate_pic_base_url = "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
            'address_part_1': address_part_1,
            'address_part_2': address_part_2,
            'offence_time': offence_time,
            'date_app' : date_app,
            'fply_address_part': fply_address_part
        }
    elif image_flow == False and is_tattile == True:
        speed_pic_base_url = "" if cit_choice["speed_pic"].startswith("https") else BASE_URL
        plate_pic_base_url = "" if cit_choice["plate_pic"].startswith("https") else BASE_URL
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
            'address_part_1': address_part_1,
            'address_part_2': address_part_2,
            'offence_time': offence_time,
            'date_app' : date_app,
            'fply_address_part': fply_address_part
        }
    if image_flow and is_tattile == False:
        data["cit"]["location_name"] = Image.objects.get(id = data["cit"]["image_id"]).location_name
    elif image_flow == False and is_tattile == False:
        location_instance = rl_agencies.get(id=data["cit"]["location_id"])
        data["cit"]["location_name"] = location_instance.location_name
    elif image_flow == False and is_tattile == True:
        location_instance = rl_agencies.get(id=data["cit"]["location_id"])
        data["cit"]["location_name"] = location_instance.location_name
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
    data["cit"]["fine"] = str(citation_obj.fine_amount)
    # Decimals
    # if data['cit']['current_citation_status'] != "EF":
    # else:
    #     data["cit"]["fine"] = str(CitationsWithEditFine.objects.filter(citation_id=data["cit"]["id"]).last().new_fine)
    #data["cit"]["fine"] = str(fine_instance.fine) if data['cit']['current_citation_status'] != "EF" else CitationsWithEditFine.objects.filter(id=data["cit"]["id"]).first().new_fine
    if image_flow == False and is_tattile==False:
        data["vid"]["speed_time"] = str(data["vid"]["speed_time"])
        data["vid"]["datetime"] = str(data["vid"]["datetime"])
        # DateTime
    data["cit"]["datetime"] = str(data["cit"]["datetime"])
    data["agency"]["onboarding_dt"] = str(data["agency"]["onboarding_dt"])
    data["cit"]["speed_pic"] = get_presigned_url(data["cit"]["speed_pic"])
    if image_flow and is_tattile==False:
        data["cit"]["speed_pic"] = get_presigned_url(Image.objects.get(id = data["cit"]["image_id"]).speed_image_url)
        data["cit"]["plate_pic"] = get_presigned_url(Image.objects.get(id = data["cit"]["image_id"]).lic_image_url)
    elif image_flow == False and is_tattile==False:
        data["cit"]["plate_pic"] = get_presigned_url(data["cit"]["plate_pic"])
    elif image_flow==False and is_tattile==True :
        data["cit"]["speed_pic"] = get_presigned_url(Tattile.objects.get(id = data["cit"]["tattile_id"]).speed_image_url)

        data["cit"]["plate_pic"] = get_presigned_url(Tattile.objects.get(id = data["cit"]["tattile_id"]).license_image_url)
        
    badge_url = data.get("agency", {}).get("badge_url", "")
    data["agency"]["badge_url"] = get_presigned_url(badge_url) if badge_url else ""
    return data

def upload_folder_to_s3(request):
    """
    Uploads all files in a local folder to the specified S3 folder.
    """
    local_folder_path = r'C:\Users\Administrator\Documents\ees\media\upload\uploads\non_violation'
    s3_folder_name = ''
    bucket_name = ''
    uploaded_files = []

    for root, _, files in os.walk(local_folder_path):
        for file_name in files:
            local_file_path = os.path.join(root, file_name)

            # Remove BASE_DIR prefix from local path if needed
            relative_path = os.path.relpath(local_file_path, BASE_DIR)

            try:
                file_url = s3_upload_file(
                    local_file_path=relative_path,
                    file_name=file_name,
                    folder_name=s3_folder_name,
                    bucket_name=bucket_name
                )
                uploaded_files.append(file_url)
                print(f"✅ Uploaded: {file_name}")
            except Exception as e:
                print(f"❌ Failed to upload {file_name}: {e}")

    return uploaded_files


def download_odr_csv_file(request, date):
    try:
        # Parse the input date string (dd-mm-yyyy format)
        date_object = datetime.strptime(date, '%d-%m-%Y')
        
        # Filter records by the date portion of created_at
        queryset = OdrCSVdata.objects.filter(created_at__date=date_object.date())
        
        # If no records found, optionally return 404
        if not queryset.exists():
            return JsonResponse({'message': 'No data found for this date'}, status=404)
        
        return download_odr_csv(queryset)
    
    except ValueError as e:
        return JsonResponse({'message': f'Invalid date format. Expected DD-MM-YYYY. Error: {e}'}, status=400)
    
    except Exception as e:
        return JsonResponse({'message': f'Something went wrong: {e}'}, status=500)

def upload_file_to_s3(request):
    try:
        folder_path = r'C:\Users\Administrator\Documents\ees\media\upload\uploads\non_violation'
        bucket_name = 'ee-prod-s3-bucket'
        s3_prefix = 'tattile/non-violation'

        upload_non_violation_folder_to_s3(folder_path, bucket_name, s3_prefix)
        return JsonResponse({'message': "successful"}, status=200)

    except ValueError as e:
        return JsonResponse({'message': f'Invalid date format. Expected DD-MM-YYYY. Error: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Something went wrong: {e}'}, status=500)

def generate_hud_pdfs(request):
    try:
        # List of citation IDs
        cit_ids = []  # fill with citation IDs
        station_id = Station.objects.get(id=38)
        station_name = "HUD-C"
        failed_drive = []

        # Query citation data
        citation_data = quick_pd_data.filter(ticket_num__in=cit_ids).values()

        for date_in in citation_data:
            cit_id = date_in['ticket_num']
            user_station = date_in['station_id']

            try:
                # === Get reminder data ===
                print(1)
                data_reminder = get_reminder_hud_c_cit_manual(cit_id, station_id, False,False)
                # === Get initial citation data ===
                print(5)
                data_initial = get_cit_refactor(cit_id, user_station, False, False)

                # === Combined PDF filename ===
                filename = f"{cit_id}-"
                print(9)
                # === Generate and Save Combined PDF ===
                success = save_combined_pdf(filename, station_name, data_initial, data_reminder)

                if success:
                    print(f"{cit_id} ✅ combined PDF generated")
                else:
                    raise Exception("PDF generation failed validation")

            except Exception as e:
                print(f"Failed for citation {cit_id}: {e}")
                failed_drive.append(cit_id)

        message = {
            'message': "Successful",
            'failed_citations': failed_drive,
            'total_failed': len(failed_drive),
        }
        return JsonResponse(message, status=200)

    except Exception as e:
        print(f"Outer Exception: {e}")
        message = {
            'message': f"Something went wrong {e}"
        }
        return JsonResponse(message, status=400)

def safe_parse_date(date_value, formats):
    """Try parsing date_value with multiple formats, return datetime or None."""
    if isinstance(date_value, datetime):
        return date_value
    if not date_value:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(str(date_value), fmt)
        except Exception:
            continue
    return None
    

def get_reminder_hud_c_cit_manual(citation_id, user_station, image_flow=False,is_tattile=True ):
    print(6)
    citation_obj = Citation.objects.get(citationID=citation_id)
    total = quick_pd_data.filter(ticket_num=citation_id, station=user_station).values()[0]

    cit_choice = cit_agencies.filter(
        citationID=citation_id, station=user_station
    ).values()[0]

    citation_data = citation_obj.citationID

    quickpd_data = QuickPD.objects.filter(
        ticket_num=citation_data, station=user_station
    ).values().last()

    if image_flow and not is_tattile:
        adj_choice = image_agencies.filter(id=cit_choice["image_id"]).values().first()
        offence_time = adj_choice['time'] if adj_choice else None
    elif not image_flow and not is_tattile:
        adj_choice = video_agencies.filter(id=cit_choice["video_id"], station_id=user_station).values().first()
        offence_time = adj_choice['datetime'] if adj_choice else None
    elif not image_flow and is_tattile:
        adj_choice = Tattile.objects.filter(id=cit_choice["tattile_id"], station_id=user_station).values().first()
        offence_time = adj_choice['image_time'] if adj_choice else None
    else:
        adj_choice = None
        offence_time = None

    veh_choice = veh_agencies.filter(
        id=cit_choice["vehicle_id"], station=user_station
    ).values()[0]
    print(7)

    per_choice = per_agencies.filter(id=cit_choice["person_id"]).values()[0]
    sup_data = sup_agencies.filter(
        citation=citation_obj, station=user_station
    ).values()[0]

    # --- Dates ---
    # App date (datetime from DB)
    original_app_date_data = sup_data["timeApp"]
    original_app_date = original_app_date_data.strftime("%m/%d/%y")

    approve_date = datetime.now()
    date_app = approve_date.strftime("%m/%d/%y")
    due_date_dt = approve_date + timedelta(days=30)
    due_date = due_date_dt.strftime("%m/%d/%y")

    # Violation date
    date_violation_raw = cit_choice["captured_date"]
    date_violation_dt = safe_parse_date(
        date_violation_raw, ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]
    )
    date_violation = (
        date_violation_dt.strftime("%m/%d/%y")
        if date_violation_dt
        else str(date_violation_raw)
    )

    # Original due date (from QuickPD)
    if not quickpd_data:
        raise ValueError(
            f"No QuickPD record found for {citation_data}, {user_station}"
        )

    original_due_date_raw = quickpd_data["arraignment_date"]

    if (
        isinstance(original_due_date_raw, str)
        and len(original_due_date_raw) == 8
        and original_due_date_raw.isdigit()
    ):
        # Compact MMDDYYYY format
        original_due_date_dt = datetime.strptime(original_due_date_raw, "%m%d%Y")
    else:
        original_due_date_dt = safe_parse_date(
            original_due_date_raw, ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"]
        )

    original_due_date = (
        original_due_date_dt.strftime("%m/%d/%y")
        if original_due_date_dt
        else str(original_due_date_raw)
    )

    # --- Agency & station ---
    agency = Agency.objects.filter(station=user_station).values()[0]
    agency_name = Station.objects.get(name=user_station)
    sig_img = None
    address_part_1 = None
    address_part_2 = None

    if agency_name.name == "HUD-C":
        qr_code = ENV_CONFIG("HUD-C-QR-CODE")
    else:
        qr_code = None
        sig_img = None

    if qr_code:
        s3_url_qr_code = get_presigned_url(qr_code)
    else:
        s3_url_qr_code = None

    # --- Build data dict ---
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
        "date_violation": date_violation,
        "original_app_date": original_app_date,
        "original_due_date": original_due_date,
    }

    # --- Location & vehicle state ---
    location_instance = rl_agencies.get(id=data["cit"]["location_id"])
    data["cit"]["location_name"] = location_instance.location_name

    license_state_instance = State.objects.get(id=data["veh"]["lic_state_id"])
    data["veh"]["lic_state"] = license_state_instance.ab

    # --- Agency/citation states ---
    agency_station = Station.objects.get(id=agency["station_id"])
    agency_state = State.objects.get(id=agency_station.state.id)
    citation_station = Station.objects.get(id=cit_choice["station_id"])
    citation_state = State.objects.get(id=citation_station.state.id)

    data["agency"]["state"] = agency_state.ab
    data["cit"]["state"] = citation_state.name

    # --- Fine ---
    fine_instance = get_fine_by_id(data["cit"]["fine_id"])
    data["cit"]["fine"] = str(fine_instance.fine)

    # --- Normalize datetime fields ---
    data["cit"]["datetime"] = str(data["cit"]["datetime"])
    data["agency"]["onboarding_dt"] = str(data["agency"]["onboarding_dt"])
    data["agency"]["badge_url"] = get_presigned_url(data["agency"]["badge_url"])

    print(8)
    return data

def get_cit_refactor_manual(citation_id, user_station, image_flow=False, is_tattile=False):
    print(2)

    # --- Safer Queries ---
    try:
        citation_obj = Citation.objects.get(citationID__iexact=citation_id)
    except Citation.DoesNotExist:
        raise Exception(f"Citation {citation_id} not found in Citation table")

    total_qs = quick_pd_data.filter(ticket_num__iexact=citation_id, station_id=user_station).values()
    if not total_qs.exists():
        raise Exception(f"No quick_pd_data for {citation_id} at station {user_station}")
    total = total_qs[0]

    cit_qs = cit_agencies.filter(citationID__iexact=citation_id, station_id=user_station).values()
    if not cit_qs.exists():
        raise Exception(f"No cit_agencies data for {citation_id} at station {user_station}")
    cit_choice = cit_qs[0]

    # --- Handle offence_time based on source ---
    if image_flow and not is_tattile:
        adj_choice = image_agencies.filter(id=cit_choice["image_id"]).values().first()
        offence_time = adj_choice['time'] if adj_choice else None
    elif not image_flow and not is_tattile:
        adj_choice = video_agencies.filter(id=cit_choice["video_id"], station_id=user_station).values().first()
        offence_time = adj_choice['datetime'] if adj_choice else None
    elif not image_flow and is_tattile:
        adj_choice = Tattile.objects.filter(id=cit_choice["tattile_id"], station_id=user_station).values().first()
        offence_time = adj_choice['image_time'] if adj_choice else None
    else:
        adj_choice = None
        offence_time = None

    # --- Other linked tables ---
    veh_choice = veh_agencies.filter(id=cit_choice["vehicle_id"], station_id=user_station).values().first()
    if not veh_choice:
        raise Exception(f"No vehicle data for {citation_id}")

    per_choice = per_agencies.filter(id=cit_choice["person_id"]).values().first()
    if not per_choice:
        raise Exception(f"No person data for {citation_id}")

    sup_data = sup_agencies.filter(citation=citation_obj, station_id=user_station).values().first()
    if not sup_data:
        raise Exception(f"No sup_agencies data for {citation_id}")

    # --- Dates ---
    dt = sup_data["timeApp"] + timedelta(days=30)
    date_app = sup_data["timeApp"] + timedelta(days=1)

    if citation_id in ['HUD-C-00000085', 'HUD-C-00000365']:
        due_date = '01/30/2025'
    elif citation_id in ['HUD-C-00000290', 'HUD-C-00000179', 'HUD-C-00000183',
                         'HUD-C-00000468', 'HUD-C-00000180', 'HUD-C-00000348']:
        due_date = '01/19/2025'
    elif citation_id in ['HUD-C-00001128', 'HUD-C-00000590',
                         'HUD-C-00001081', 'HUD-C-00000863', 'HUD-C-00001056']:
        due_date = '02/25/2025'
    else:
        due_date = datetime.strftime(dt, "%m/%d/%Y")

    agency = Agency.objects.filter(station_id=user_station).values().first()
    if not agency:
        raise Exception(f"No agency found for station {user_station}")

    print(3)

    agency_name = Station.objects.filter(id=user_station).values('name').first()
    station_name = agency_name.get('name') if agency_name else ""

    # --- Handle QR, signatures, addresses ---
    sig_img = None
    address_part_1 = None
    address_part_2 = None
    fply_address_part = None

    if station_name == 'MOR-C':
        qr_code = ENV_CONFIG('MOR-C-QR-CODE')
    elif station_name == 'FED-M':
        qr_code = ENV_CONFIG('FED-M-QR-CODE')
        sig_off = ENV_CONFIG('FED-M-SIG-OFFICER')
        sig_img = get_presigned_url(sig_off)
    elif station_name == 'WBR2':
        qr_code = ENV_CONFIG('WBR2-QR-CODE')
        address_parts = agency['address'].split('Drive')
        address_part_1 = address_parts[0].strip() + " Drive"
        address_part_2 = address_parts[1].strip()
    elif station_name == 'HUD-C':
        qr_code = ENV_CONFIG('HUD-C-QR-CODE')
    elif station_name == 'MAR':
        qr_code = ENV_CONFIG('MAR-QR-CODE')
    elif station_name == 'CLA':
        qr_code = ENV_CONFIG('CLA-QR-CODE')
    elif station_name == 'FPLY-C':
        qr_code = ENV_CONFIG('FPLY-C-QR-CODE')
        address = per_choice.get('address', '')
        if len(address) >= 27 or "PO" in address:
            person_address_part = address.split(",")
            if len(person_address_part) >= 2:
                fply_address_part = person_address_part[0].strip() + ", <br>" + person_address_part[1].strip()
            else:
                fply_address_part = address
        else:
            fply_address_part = address
    elif station_name == "KRSY-C":
        qr_code = ENV_CONFIG('KRSY-C-QR-CODE')
    else:
        qr_code = None
        sig_img = None

    s3_url_qr_code = get_presigned_url(qr_code) if qr_code else None

    # --- Build data dict ---
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
        "fply_address_part": fply_address_part
    }

    # --- Add state & fine info ---
    license_state_instance = State.objects.get(id=data["veh"]["lic_state_id"])
    data["veh"]["lic_state"] = license_state_instance.ab

    agency_station = Station.objects.get(id=agency["station_id"])
    agency_state = State.objects.get(id=agency_station.state.id)

    citation_station = Station.objects.get(id=cit_choice["station_id"])
    citation_state = State.objects.get(id=citation_station.state.id)

    data["agency"]["state"] = agency_state.ab
    data["cit"]["state"] = citation_state.name

    fine_instance = get_fine_by_id(data["cit"]["fine_id"])
    if data['cit']['current_citation_status'] != "EF":
        data["cit"]["fine"] = str(fine_instance.fine)
    else:
        data["cit"]["fine"] = str(
            CitationsWithEditFine.objects.filter(citation_id=data["cit"]["id"]).last().new_fine
        )

    # --- Convert datetimes to str ---
    if not image_flow and not is_tattile and "vid" in data and data["vid"]:
        data["vid"]["speed_time"] = str(data["vid"].get("speed_time", ""))
        data["vid"]["datetime"] = str(data["vid"].get("datetime", ""))

    data["cit"]["datetime"] = str(data["cit"]["datetime"])
    data["agency"]["onboarding_dt"] = str(data["agency"]["onboarding_dt"])

    # --- Images ---
    data["cit"]["speed_pic"] = get_presigned_url(data["cit"]["speed_pic"])
    if image_flow and not is_tattile:
        img_obj = Image.objects.get(id=data["cit"]["image_id"])
        data["cit"]["speed_pic"] = get_presigned_url(img_obj.speed_image_url)
        data["cit"]["plate_pic"] = get_presigned_url(img_obj.lic_image_url)
    elif not image_flow and not is_tattile:
        data["cit"]["plate_pic"] = get_presigned_url(data["cit"]["plate_pic"])
    elif not image_flow and is_tattile:
        tattile_obj = Tattile.objects.filter(id=data["cit"]["tattile_id"]).first()
    if tattile_obj:
        data["cit"]["speed_pic"] = get_presigned_url(tattile_obj.speed_image_url)
        data["cit"]["plate_pic"] = get_presigned_url(tattile_obj.license_image_url)
    else:
        # fallback if Tattile row missing
        data["cit"]["speed_pic"] = get_presigned_url(data["cit"]["speed_pic"])
        data["cit"]["plate_pic"] = get_presigned_url(data["cit"]["plate_pic"])

    # --- Badge ---
    badge_url = data.get("agency", {}).get("badge_url", "")
    data["agency"]["badge_url"] = get_presigned_url(badge_url) if badge_url else ""

    print(4)
    return data

AWS_REGION = "us-east-2"                 # Change if needed
BUCKET_NAME = "ee-prod-s3-bucket"         # Replace with your bucket name
PREFIX = "tattile/violation/2025-09-12"                    # File prefix to filter
DOWNLOAD_DIR = r"C:\Users\Administrator\Documents\ees\media\upload\uploads\download_s3" 
from ees.utils import s3_client
def download_files_from_s3(request):
    try:
        # s3_client = S3Client().fips_client

        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        paginator = s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX)

        for page in page_iterator:
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    filename = os.path.basename(key)
                    local_path = os.path.join(DOWNLOAD_DIR, filename)

                    print(f"Downloading {key} to {local_path}")
                    s3_client.download_file(BUCKET_NAME, key, local_path, ExtraArgs={"ExpectedBucketOwner": AWS_S3_EXPECTED_OWNER})

        print("Download completed")
        message = {
            'message': f"Sucessfull"
        }
        return JsonResponse(message, status=200)
    
    except Exception as e:
        print(f"Outer Exception: {e}")
        message = {
            'message': f"Something went wrong {e}"
        }
        return JsonResponse(message, status=400)


def reject_tattile_record():
    today = timezone.now().date()
    yesterday = today - timedelta(days=2)

    qs = (
        Tattile.objects.filter(
            station_id__in =  [38,44],
            image_time__date__range=[yesterday, today]
        )
        .exclude(
            Exists(
                TattileFile.objects.filter(tattile_id=OuterRef("id"))
            )
        )
    )

    # Instead of delete, mark as rejected
    updated_count = qs.update(is_active=False)
    print(f"Marked {updated_count} Tattile records as rejected")

def create_csv_and_pdf_data_for_agencies(target_date=None, max_workers=10):
    """
    ✅ Generate PDFs and CSVs for all approved citations across all stations for a given date.
    Parallelized using ThreadPoolExecutor for faster processing.
    """
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).date()

    print(f"[Scheduler] Starting PDF & CSV generation for agencies on {target_date}...")

    approved_citations = sup_metadata.objects.filter(
        isApproved=True,
        timeApp__date=target_date
    ).select_related('station', 'citation')

    if not approved_citations.exists():
        print(f"[Scheduler] No approved citations found for {target_date}.")
        return

    station_ids = approved_citations.values_list('station_id', flat=True).distinct()

    for station_id in station_ids:
        station_obj = Station.objects.filter(id=station_id).first()
        if not station_obj:
            continue

        station_name = station_obj.name
        station_citations = approved_citations.filter(station_id=station_id)

        print(f"[Scheduler] Processing {station_citations.count()} citations for station: {station_name}")

        # 🧵 Thread pool for PDFs
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_citation = {
                executor.submit(process_single_pdf, meta, station_id, station_name): meta
                for meta in station_citations
            }

            for future in as_completed(future_to_citation):
                meta = future_to_citation[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"[Scheduler] ❌ Error processing citation {meta.citation.citationID}: {e}")

        # 📝 Generate CSV after all PDFs are complete
        try:
            create_refactor_csv(station_id)
            print(f"[Scheduler] 📄 CSV file generated for station: {station_name}")
        except Exception as e:
            print(f"[Scheduler] ❌ Failed to generate CSV for station {station_name}: {e}")

    print(f"[Scheduler] ✅ PDF & CSV generation completed for {target_date}")


# ------------------------------------------------------------------------
# ⬇️ Define the helper below it
# ------------------------------------------------------------------------

def process_single_pdf(meta, station_id, station_name,date_type=None):
    """
    Generates PDF for a single citation.
    Runs inside a thread.
    """
    citation = meta.citation
    citation_id = str(citation.citationID)

    try:
        if citation.video_id:
            data = get_cit_refactor(citation_id, station_id, image_flow=False, is_tattile=False)
        elif citation.image_id:
            data = get_cit_refactor(citation_id, station_id, image_flow=True, is_tattile=False)
        elif citation.tattile_id:
            data = get_cit_refactor(citation_id, station_id, image_flow=False, is_tattile=True)
        else:
            print(f"[Scheduler] Citation {citation_id} has no media reference. Skipping.")
            return

        filename = f"{citation_id}.pdf"
        result = save_pdf(filename, station_name, data,date_type=None)

        if result:
            print(f"[Scheduler] ✅ PDF generated for citation {citation_id} ({station_name})")
        else:
            print(f"[Scheduler] ⚠️ PDF generation failed for citation {citation_id} ({station_name})")

    except Exception as e:
        print(f"[Scheduler] ❌ Error generating PDF for citation {citation_id}: {e}")

def create_refactor_csv(stationId, target_date=None):
    # Use previous day if not provided
    if target_date is None:
        target_date = (datetime.now() - timedelta(days=1)).date()

    test_now = target_date.strftime("%m%d%Y")  # <-- correct date for filename
    date = target_date.strftime("%Y-%m-%d")

    meta = csv_meta_agencies.filter(date__date=target_date, station_id=stationId).values()
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

    for i in meta:
        data = quick_pd_data.filter(id=int(i["quickPD_id"])).values().first()
        if data:
            citations.append(data)

    if not citations:
        print(f"[Scheduler] ⚠️ No citation data found for station {stationId} on {target_date}.")
        return

    data_frame = pd.DataFrame(data=citations)
    valid_cols = [c for c in cols if c in data_frame.columns]

    file_name = f"{station_data.get('name')}-Citations-{test_now}.csv"
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


def custom_404(request):
    return render(request, "not_found.html", status=404)