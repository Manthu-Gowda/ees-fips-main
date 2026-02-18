from datetime import datetime,timedelta
from video.models import *
from video.views import create_csv ,save_pdf, get_cit_refactor
from decouple import config as ENV_CONFIG
import pdfkit
import os
from ees.utils import upload_to_s3
import pandas as pd
from reviewbin_view.reviewbin_utils import ReviewBinUtils
TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
csv_meta_agencies = csv_metadata.objects.all()
quick_pd_data = QuickPD.objects.all()
TEMP_ZIP_DIR = ENV_CONFIG("TEMP_ZIP_DIR")
TEMP_CSV_DIR = ENV_CONFIG("TEMP_CSV_DIR")
BASE_DIR = ENV_CONFIG("BASE_DIR")

def get_batch_id(userId):
    user_batch_id = {'47': 1703, '74': 2202, '75': 2201, '118': '0172', 
                     '144' : 2102, '186' : 'KP844', '182' : 'KP841', '283': '846'
                    }

def save_quick_pd_data(citationId, note, is_send_back=False,is_approved=False,userId=None):
    officer_badge = ""
    
    batch_id = get_batch_id(userId)
    officer_badge = batch_id
    citation_data = Citation.objects.filter(id=citationId).first()
    person_data = Person.objects.filter(id=citation_data.person_id).first()
    vehicle_data = Vehicle.objects.filter(id=citation_data.vehicle_id).first()
    get_agency_state_rs = Agency.objects.filter(station_id=citation_data.station_id).values_list('state_rs', flat=True).first()
    license_state_ab = State.objects.filter(id=vehicle_data.lic_state_id).values_list('ab', flat=True).first()

    if citation_data.video_id:
        video_data = Video.objects.filter(id=citation_data.video_id).first()
        video_data_data = Data.objects.filter(VIDEO_NO=video_data.VIDEO_NO, VIDEO_NAME = video_data.caption[:20]).first()
        formatted_date = datetime.strptime(video_data_data.DATE, "%y%m%d")
        formatted_time = datetime.strptime(video_data_data.TIME, "%H%M%S")
        if userId == 236:
            officer_badge  = '850'
        else:
            officer_badge = video_data_data.BADGE_ID.lstrip('0')
    elif citation_data.image_id:
        image_data = Image.objects.filter(id=citation_data.image_id).first()
        formatted_date = datetime.strptime(str(image_data.time), "%Y-%m-%d %H:%M:%S%z")
        formatted_time = datetime.strptime(str(image_data.time), "%Y-%m-%d %H:%M:%S%z")
        officer_badge = image_data.officer_badge
    elif citation_data.tattile_id:
        tattile_data = Tattile.objects.filter(id=citation_data.tattile_id).first()
        formatted_date = tattile_data.image_time
        formatted_time = tattile_data.image_time
        
        if str(userId) in ['182','186']:
            batch_id = get_batch_id(str(userId))
            officer_badge = batch_id
        else:
            officer_badge = '2102'
    else:
        formatted_date = None
        formatted_time = None

    supervisor_meta_data = sup_metadata.objects.filter(citation_id=citationId).first()
    now = datetime.now()
    court_date = now + timedelta(days=30)
    court_date = court_date.strftime("%m%d%Y")
    if not supervisor_meta_data and is_approved:
        quick = QuickPD(
            station=citation_data.station,
            offense_date=formatted_date.strftime("%m%d%Y"),
            offense_time=formatted_time.strftime("%H%M"),
            ticket_num=citation_data.citationID,
            first_name=person_data.first_name,
            middle=person_data.middle,
            last_name=person_data.last_name,
            address=person_data.address,
            city=person_data.city,
            state=person_data.state,
            zip=person_data.zip,
            arraignment_date=court_date,
            actual_speed=citation_data.speed,
            posted_speed=citation_data.posted_speed,
            officer_badge=officer_badge if officer_badge else '',
            plate_num=vehicle_data.plate,
            plate_state=license_state_ab,
            vin=vehicle_data.vin,
            phone_number=person_data.phone_number,
            state_rs1=get_agency_state_rs,
            notes=note
        )
        quick.save()
        return quick.id
    elif is_send_back and supervisor_meta_data:
        existing_quick_pd = QuickPD.objects.filter(ticket_num=citation_data.citationID)
        existing_quick_pd.delete()
    else:
        existing_quick_pd = QuickPD.objects.filter(ticket_num=citation_data.citationID).first()
        return existing_quick_pd.id if existing_quick_pd else None


def update_media_data(citationId, is_approved, is_rejected, is_send_back, station_id, note= '', userId=None):
    citation_data = Citation.objects.filter(id=citationId).first()
    if not citation_data:
        return

    if citation_data.video_id:
        duncan_submission_data = DuncanSubmission.objects.filter(video_id=citation_data.video_id).first()
        if duncan_submission_data:
            duncan_submission_data.isApproved = is_approved
            duncan_submission_data.isRejected = is_rejected
            duncan_submission_data.save()
        video_data = Video.objects.filter(id=citation_data.video_id, station_id=station_id).first()
        if video_data:
            video_data.isSent = is_send_back
            video_data.save()
            if station_id in [35,38,39, 42, 44, 69] and is_send_back:
                # sent to review bin
                video_obj = Video.objects.filter(id=citation_data.video_id).first()
                if video_obj  and is_send_back:
                    video_obj.isAdjudicated = False
                    video_obj.isRemoved = False
                    video_obj.save()
                agency_adj_obj = AdjudicationBin.objects.filter(video=video_obj).first()
                if agency_adj_obj:
                    agency_adj_obj.is_adjudicated_in_adjudicationbin = False
                    agency_adj_obj.note = note
                    agency_adj_obj.save()
                else:
                    fields = {
                    "station_name": citation_data.station.name,
                    "video_object": video_data,
                    "image_object": None,
                    "is_notfound": False,
                    "is_adjudicated_in_review_bin": False,
                    "is_send_adjbin": False,
                    "is_sent_back_subbin": False,
                    "license_plate": citation_data.vehicle.plate,
                    "vehicle_state": citation_data.vehicle.lic_state.ab,
                    "note": note,
                    "tattile_object":None
                }
                    ReviewBinUtils.save_reviewbin_data(**fields)
                
        else:
            return

    elif citation_data.image_id:
        duncan_submission_data = DuncanSubmission.objects.filter(image_id=citation_data.image_id).first()
        if duncan_submission_data:
            duncan_submission_data.isApproved = is_approved
            duncan_submission_data.isRejected = is_rejected
            duncan_submission_data.save()
        image_data = Image.objects.filter(id=citation_data.image_id, station_id=station_id).first()
        if image_data:
            officer_badge = ""
            batch_id = get_batch_id(userId)
            officer_badge = batch_id
            
            if not image_data.officer_badge:
                image_data.officer_badge = officer_badge
            image_data.isSent = is_send_back
            image_data.save()
            if station_id in [35,38,39, 42, 44] and is_send_back:
                # sent to review bin
                image_obj = Image.objects.filter(id=citation_data.image_id).first()
                if image_obj and is_send_back:
                    image_obj.isAdjudicated = False
                    image_obj.save()
                agency_adj_obj = AdjudicationBin.objects.filter(image=image_obj).first()
                if agency_adj_obj:
                    agency_adj_obj.is_adjudicated_in_adjudicationbin = False
                    agency_adj_obj.note = note
                    agency_adj_obj.save()
                else:
                    fields = {
                    "station_name": citation_data.station.name,
                    "video_object": None,
                    "image_object": image_data,
                    "is_notfound": False,
                    "is_adjudicated_in_review_bin": False,
                    "is_send_adjbin": False,
                    "is_sent_back_subbin": False,
                    "license_plate": citation_data.vehicle.plate,
                    "vehicle_state": citation_data.vehicle.lic_state.ab,
                    "note": note,
                    "tattile_object":None
                }
                    ReviewBinUtils.save_reviewbin_data(**fields)
        else:
            return
        
    elif citation_data.tattile_id:
        duncan_submission_data = DuncanSubmission.objects.filter(tattile_id=citation_data.tattile_id).first()
        if duncan_submission_data:
            duncan_submission_data.isApproved = is_approved
            duncan_submission_data.isRejected = is_rejected
            duncan_submission_data.save()
        tattile_data = Tattile.objects.filter(id=citation_data.tattile_id, station_id=station_id).first()
        if tattile_data:
            officer_badge = ""
            batch_id = get_batch_id(userId)
            officer_badge = '2102'
            
            if not tattile_data.officer_badge:
                tattile_data.officer_badge = officer_badge
            
            tattile_data.is_sent = is_send_back
            tattile_data.save()
            if station_id in [35,38,39, 42, 44] and is_send_back:
                # sent to review bin
                tattile_obj = Tattile.objects.filter(id=citation_data.tattile_id).first()
                if tattile_obj and is_send_back:
                    tattile_obj.is_adjudicated = False
                    tattile_obj.is_removed = False
                    tattile_obj.save()
                agency_adj_obj = AdjudicationBin.objects.filter(tattile=tattile_obj).first()
                if agency_adj_obj:
                    agency_adj_obj.is_adjudicated_in_adjudicationbin = False
                    agency_adj_obj.note = note
                    agency_adj_obj.save()
                else:
                    fields = {
                    "station_name": citation_data.station.name,
                    "video_object": None,
                    "image_object": None,
                    "is_notfound": False,
                    "is_adjudicated_in_review_bin": False,
                    "is_send_adjbin": False,
                    "is_sent_back_subbin": False,
                    "license_plate": citation_data.vehicle.plate,
                    "vehicle_state": citation_data.vehicle.lic_state.ab,
                    "note": note,
                    "tattile_object" : tattile_data
                }
                    ReviewBinUtils.save_reviewbin_data(**fields)
        else:
            return


def save_supervisor_meta_data(citationId, userId, stationId):
    existing_meta = sup_metadata.objects.filter(citation_id=citationId).first()
    if existing_meta:
        existing_meta.user_id = userId
        existing_meta.isApproved = True
        existing_meta.timeApp = datetime.now()
        existing_meta.station_id = stationId
        existing_meta.save()
    else:
        supervisor_meta_data = sup_metadata(
            user_id=userId,
            citation_id=citationId,
            isApproved=True,
            timeApp=datetime.now(),
            station_id=stationId
        )
        supervisor_meta_data.save()


def save_csv_meta_data(quickPDId, citationId, userId, stationId):
    if not quickPDId:
        raise ValueError("quickPDId is required")
    if not citationId:
        raise ValueError("Citation ID is required")
    if not userId:
        raise ValueError("User ID is required")
    if not stationId:
        raise ValueError("Station ID is required")

    csv = csv_metadata.objects.filter(quickPD_id=quickPDId, station_id=stationId).first()

    if csv:
        csv.user_id = userId
        csv.date = datetime.now()
        csv.save()
    else:
        csv = csv_metadata(
            user_id=userId,
            quickPD_id=quickPDId,
            date=datetime.now(),
            station_id=stationId
        )
        csv.save()

    return


def create_csv_and_pdf_data(citationID,stationId,stationName,image_flow,is_tattile=False):
    create_refactor_csv(stationId)


def create_refactor_csv(stationId):

    now = datetime.now()
    test_now = now.strftime("%m%d%Y")
    date = now.strftime("%Y-%m-%d")

    meta = csv_meta_agencies.filter(date__date=date, station_id=stationId).values()
    station_data = Station.objects.filter(id=stationId).values('name').first()
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
    file_path = os.path.join(BASE_DIR, "media", f"{station_data.get('name')}-Citations-{test_now}.csv")

    data_frame.to_csv(
        file_path,
        index=False,
        header=False,
        columns=cols,
    )
    with open(file_path, "rb") as csv_file:
        upload_to_s3(csv_file, f"{station_data.get('name')}-Citations-{test_now}.csv", "csvs")
        os.remove(file_path)


def update_quick_pd_data(citationId, note):
    officer_badge = ""
    citation_data = Citation.objects.filter(id=citationId).first()
    person_data = Person.objects.filter(id=citation_data.person_id).first()
    vehicle_data = Vehicle.objects.filter(id=citation_data.vehicle_id).first()
    get_agency_state_rs = Agency.objects.filter(station_id=citation_data.station_id).values_list('state_rs', flat=True).first()
    license_state_ab = State.objects.filter(id=vehicle_data.lic_state_id).values_list('ab', flat=True).first()

    if citation_data.video_id:
        video_data = Video.objects.filter(id=citation_data.video_id).first()
        video_data_data = Data.objects.filter(VIDEO_NO=video_data.VIDEO_NO, VIDEO_NAME=video_data.caption[:20]).first()
        formatted_date = datetime.strptime(video_data_data.DATE, "%y%m%d")
        formatted_time = datetime.strptime(video_data_data.TIME, "%H%M%S")
        officer_badge = video_data_data.BADGE_ID.lstrip('0')
    elif citation_data.image_id:
        image_data = Image.objects.filter(id=citation_data.image_id).first()
        formatted_date = datetime.strptime(str(image_data.time), "%Y-%m-%d %H:%M:%S%z")
        formatted_time = formatted_date
        officer_badge = image_data.officer_badge
    elif citation_data.tattile_id:
        tattile_data = Tattile.objects.filter(id=citation_data.tattile_id).first()
        formatted_date = tattile_data.image_time
        formatted_time = formatted_date
        officer_badge = tattile_data.officer_badge
    else:
        formatted_date = None
        formatted_time = None

    now = datetime.now()
    court_date = now + timedelta(days=30)
    court_date = court_date.strftime("%m%d%Y")

    quick = QuickPD(
        station=citation_data.station,
        offense_date=formatted_date.strftime("%m%d%Y") if formatted_date else "",
        offense_time=formatted_time.strftime("%H%M") if formatted_time else "",
        ticket_num=citation_data.citationID,
        first_name=person_data.first_name,
        middle=person_data.middle,
        last_name=person_data.last_name,
        address=person_data.address,
        city=person_data.city,
        state=person_data.state,
        zip=person_data.zip,
        arraignment_date=court_date,
        actual_speed=citation_data.speed,
        posted_speed=citation_data.posted_speed,
        officer_badge=officer_badge,
        plate_num=vehicle_data.plate,
        plate_state=license_state_ab,
        vin=vehicle_data.vin,
        phone_number=person_data.phone_number,
        state_rs1=get_agency_state_rs,
        notes=note
    )
    quick.save()
    return quick.id