import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, time
from django.utils import timezone
from video.models import Agency, Station, Fine, adj_metadata, sup_metadata
from video.schedulers.process_paid_citations import (
    process_single_imp_file,
    find_unpaid_citations_for_sftp_stations
)
from video.schedulers.process_paid_citations_first_mailer import (
    process_single_imp_file_first_mailer,
    find_unpaid_citations_for_sftp_stations_first_mailer
)
from .distributor import dist_sftp, dist_sftp_mailer_pdfs, dist_smtp, zip_first_mailer_pdfs, zip_pdfs
from .views import (daily_report_generator, 
                    removal_of_adj, 
                    removal_of_sup, 
                    read_json_excluding_image, 
                    reject_tattile_record,
                    create_csv_and_pdf_data_for_agencies, vids
                    )


from decouple import config as ENV_CONFIG


TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
TEMP_PRE_ODR_FIRST_MAILER_PDFS = ENV_CONFIG("TEMP_PRE_ODR_FIRST_MAILER_PDFS")

LOG_FILE = r"C:\Users\Administrator\Documents\ees\logs\task_scheduler.log"

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
# ---------- TASK 1 ----------
# def run_pdf_zip_and_sftp():
#     """Daily at 04:30"""
#     now = datetime.now()
#     current_date = (now - timedelta(days=1)).strftime("%m%d%Y")

#     agencies = Agency.objects.all().order_by("name").values()

#     for x in agencies:
#         station = Station.objects.filter(id=x["station_id"]).values().first()
#         fine = Fine.objects.filter(station_id=station['id']).values_list('fine', flat=True).first()
#         issuing_agency = x['name']

#         folder = os.path.join(TEMP_PDF_DIR, station['name'])

#         if os.path.isdir(folder) and any(f.endswith(".pdf") for f in os.listdir(folder)):
#             try:
#                 zip_loc = zip_pdfs(station['name'], current_date)
#                 logging.info(f"PDF zipped for {station['name']}")

#                 dist_sftp(
#                     zip_loc, 
#                     station['name'], 
#                     x.get("isXpressPay"), 
#                     fine, 
#                     issuing_agency, 
#                     current_date
#                 )

#             except Exception as e:
#                 logging.error(f"Error zipping or sending SFTP for {station['name']} — {e}")
#         else:
#             logging.info(f"No PDFs found for {station['name']}")

#         try:
#             dist_smtp(x["emails"], station['name'], current_date, station['id'], fine, issuing_agency)
#         except Exception as e:
#             logging.error(f"CSV email failed for {station['name']} — {e}")


# ---------- TASK 2 ----------
# def run_pre_odr_mailer():
#     """Daily at 00:51"""
#     now = datetime.now()
#     current_date_pre = (now - timedelta(days=1)).strftime("%m%d%Y")

#     agencies = Agency.objects.all().order_by("name").values()

#     for x in agencies:
#         station = Station.objects.filter(id=x["station_id"]).values().first()
#         folder = os.path.join(TEMP_PRE_ODR_FIRST_MAILER_PDFS, station['name'])

#         if os.path.isdir(folder) and any(f.endswith('.pdf') for f in os.listdir(folder)):
#             zip_loc = zip_first_mailer_pdfs(station['name'], current_date_pre)

#             if x.get("isPreOdr"):
#                 dist_sftp_mailer_pdfs(
#                     zip_loc,
#                     station['name'],
#                     x["isPreOdr"],
#                     x['name'], # issuing agency
#                     current_date_pre
#                 )
#         else:
#             print('No PDFs found')
#     else:
#         print('No directory for station found')


# ---------- TASK 3 ----------
def run_midnight_cleanup():
    """Daily at 23:50"""
    try:
        logging.info("Starting midnight cleanup task")
        today = timezone.now().date()
        one_month_ago = today - timedelta(days=30)

        sup_qs = sup_metadata.objects.filter(
            timeApp__date__gte=one_month_ago,
            timeApp__date__lte=today
        )
        adj_qs = adj_metadata.objects.filter(
            timeAdj__date__gte=one_month_ago,
            timeAdj__date__lte=today
        )
        removal_of_adj(adj_qs)
        removal_of_sup(sup_qs)
        logging.info("Midnight cleanup task completed successfully")
    except Exception as e:
        logging.error(f"Midnight cleanup error — {e}")


# ---------- TASK 4 ----------
def run_daily_report():
    """Daily at 04:01"""
    logging.info("Starting daily report generation task")
    daily_report_generator()
    logging.info("Daily report generation task completed successfully")


# ---------- TASK 5 ----------
def run_citation_summary():
    """Daily at 08:01"""
    try:
        logging.info("Starting citation summary task")
        process_single_imp_file(["FED-M","WBR2","HUD-C","KRSY-C","FPLY-C"])
        find_unpaid_citations_for_sftp_stations(["FED-M","WBR2","HUD-C","KRSY-C","FPLY-C"])
        logging.info("Citation summary task completed successfully")
    except Exception as e:
        logging.error(f"Citation summary error — {e}")


# ---------- TASK 6 ----------
def run_tattile_upload():
    """Daily at 01:30"""
    try:
        logging.info("Starting Tattile upload task")
        read_json_excluding_image()
        logging.info("Tattile upload task completed successfully")
    except Exception as e:
        logging.error(f"Tattile upload error — {e}")


# ---------- TASK 7 ----------
def run_tattile_reject():
    """Daily at 02:01"""
    try:
        logging.info("Starting Tattile reject task")
        reject_tattile_record()
        logging.info("Tattile reject task completed successfully")
    except Exception as e:
        logging.error(f"Tattile reject error — {e}")


# ---------- TASK 8 ----------
# def run_generate_pdf_csv():
#     """Daily at 02:30"""
#     try:
#         create_csv_and_pdf_data_for_agencies()
#     except Exception as e:
#         logging.error(f"PDF/CSV generation error — {e}")


# ---------- TASK 9 ----------
# def run_citation_first_mailer():
#     """Daily at 07:10"""
#     try:
#         process_single_imp_file_first_mailer(["MAR"])
#         find_unpaid_citations_for_sftp_stations_first_mailer(["MAR"])
#     except Exception as e:
#         logging.error(f"First mailer citation summary error — {e}")

# ---------- TASK 10 ----------
def run_mail_to_leah_xbp_csv():
    """Daily at 23:40"""
    logging.info("Starting mail to Leah XBP CSV task")
    now = datetime.now()
    current_date = (now).date().strftime("%m%d%Y")

    agencies = Agency.objects.all().order_by("name").values()

    for x in agencies:
        station = Station.objects.filter(id=x["station_id"]).values().first()
        fine = Fine.objects.filter(station_id=station['id']).values_list('fine', flat=True).first()
        issuing_agency = x['name']
        is_express_pay = x.get("isXpressPay")
        
        try:
            dist_smtp("leah@emergentenforcement.com", station['name'], current_date, station['id'], fine, issuing_agency)
            if is_express_pay:
                print(issuing_agency, "issuing agency here")
                dist_sftp(
                    station["name"],
                    is_express_pay,
                    fine,
                    issuing_agency,
                    current_date
                )
                logging.info(
                    f"File sent to xpress_csv and SFTP on SFTP for {station['name']}"
                )
                print(f"File sent to xpress_csv and SFTP for {station['name']}")
            else:
                dist_sftp(
                    station["name"],
                    False,
                    None,
                    None,
                    current_date
                )
                logging.info(f"File sent to leah and xbp SFTP for {station['name']}")
                
        except Exception as e:
            logging.error(f"CSV email failed for {station['name']} — {e}")

# ---------- TASK 11 ----------         
def run_video_upload():
    """Daily every 1 minute"""
    logging.info("Starting video upload task")
    vids()
    logging.info("Video upload task completed successfully")