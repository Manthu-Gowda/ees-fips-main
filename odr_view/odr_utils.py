from datetime import datetime, timedelta
from video.models import Person, UnpaidCitation, Vehicle, Citation, Video, Image, CourtDates, adj_metadata, Data, OdrCSVdata, \
    Odr_csv_metadata, OdrCitation, sup_metadata, Station
data_agencies = Data.objects.all()
from ees.utils import s3_get_file, upload_to_s3
from django.template.loader import get_template
from datetime import datetime
from decouple import config as ENV_CONFIG
import base64
import io,os
import pdfkit
from django.db.models import Q
from video.models import QuickPD, road_location
from django.core.paginator import Paginator
from decimal import Decimal

TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
BASE_DIR= ENV_CONFIG("BASE_DIR")
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

class AdjudicatorUtils:
    @staticmethod
    def extract_fields(validated_data):
        """
        Extract and return input fields from serializer data.
        """
        return {
            "video_id": validated_data.get('videoId', None),
            "image_id": validated_data.get('imageId', None),
            "is_adjudicated": validated_data.get('isAdjudicated', False),
            "is_rejected": validated_data.get('isRejected', False),
            "first_name": validated_data.get('firstName', ""),
            "middle_name": validated_data.get('middleName', ""),
            "last_name": validated_data.get('lastName', ""),
            "phone_number": validated_data.get('phoneNumber', ""),
            "address": validated_data.get('address', ""),
            "city": validated_data.get('city', ""),
            "state_ab": validated_data.get('stateAB', ""),
            "zip_code": validated_data.get('zip', ""),
            "vehicle_year": validated_data.get('vehicleYear', ""),
            "make": validated_data.get('make', ""),
            "model": validated_data.get('model', ""),
            "color": validated_data.get('color', ""),
            "vin_number": validated_data.get('vinNumber', ""),
            "note": validated_data.get('note', ""),
            "is_warning": validated_data.get('isWarning', True),
            "reject_id": validated_data.get('rejectId', None),
            "license_plate": validated_data.get('licensePlate', None),
            "speedPic": validated_data.get('speedPic', None),
            "platePic": validated_data.get('platePic', None),
            "license_state_id": validated_data.get('licenseStateId', None),
            "location_id": validated_data.get('locationId', None),
            "violate_speed": validated_data.get('violatedSpeed', None),
            "posted_speed": validated_data.get('postedSpeed', None),
            "distance": validated_data.get('distance', None),
            "fine_id": validated_data.get('fineId', None),
            "mediaType" : validated_data.get('mediaType'),
            "citationID" : validated_data.get('citationID'),
            "isSent" : validated_data.get('isSent')
        }

    @staticmethod
    def save_person_data(station_id, fields):
        person = Person(
            first_name=fields.get('first_name', "") or "",
            middle=fields.get('middle_name', "") or "",
            last_name=fields.get('last_name', "") or "",
            phone_number=fields.get('phone_number', "") or "",
            address=fields.get('address', "") or "",
            city=fields.get('city', "") or "",
            state=fields.get('state_ab', "") or "",
            zip=fields.get('zip_code', "") or "",
            station_id=station_id
        )
        person.save()
        return person
    

    @staticmethod
    def save_vehicle_data(station_id, fields):
        vehicle = Vehicle(
            station_id=station_id,
            vehicle_id=Vehicle.objects.filter(station=station_id).count() + 1,
            year=fields.get('vehicle_year', "") or "",
            make=fields.get('make', "") or "",
            model=fields.get('model', "") or "",
            color=fields.get('color', "") or "",
            plate=fields.get('license_plate', "") or "",
            lic_state_id=fields.get('license_state_id'),
            vin=fields.get('vin_number', "") or "",
        )
        vehicle.save()
        return vehicle

    @staticmethod
    def get_date_object(fields):
        """
        Fetch and process the date object for a video.
        """
        if fields['mediaType'] == 1:
            VIDEO_NO = Video.objects.filter(id=fields['video_id']).values_list('VIDEO_NO',flat=True).first()
            video_data = Data.objects.filter(VIDEO_NO=VIDEO_NO).first()
            date = data_agencies.filter(
                VIDEO_NO=video_data.VIDEO_NO
                # VIDEO_NAME=video_data.caption[:20]
            ).values_list('DATE', flat=True).first()
            return datetime.strptime(date, "%y%m%d").strftime("%Y-%m-%d")
        elif fields['mediaType'] == 2:
            image_data = Image.objects.filter(id=fields['image_id']).values_list('time',flat=True).first()
            return image_data.date().strftime("%Y-%m-%d")
        else:
            return datetime.now().strftime("%Y-%m-%d")
        
    @staticmethod
    def get_court_date(station_id):
        """
        Fetch and return court date.
        """
        court_date = CourtDates.objects.filter(station=station_id).values_list('id',flat=True).first()
        return court_date

    @staticmethod
    def save_citation_data(station_id, citation_id, person, vehicle, court_date, date_object, fields, speed_pic, plate_pic):
        """
        Save and return Citation data.
        """
        video_id = None
        image_id = None
        if fields['mediaType'] == 1:

            if fields['video_id'] != 0:
                video_id = fields['video_id']
            
            citation = Citation(
            id=Citation.objects.order_by("-id").first().id + 1 if Citation.objects.exists() else 1,
            person=person,
            station_id=station_id,
            vehicle=vehicle,
            video_id=video_id,
            image_id=image_id,
            location_id=fields['location_id'],
            court_date_id=court_date,
            fine_id=fields['fine_id'],
            citationID=citation_id,
            datetime=datetime.now(),
            posted_speed=fields['posted_speed'],
            speed=fields['violate_speed'],
            speed_pic=speed_pic,
            plate_pic=plate_pic,
            note=fields['note'],
            dist=fields['distance'],
            is_warning=fields['is_warning'],
            captured_date=date_object,
            isRejected=fields['is_rejected'],
            isSendBack=False,
            image_location = None
            )
            citation.save()
            return citation
        elif fields['mediaType'] == 2:
            if fields['image_id'] != 0:
                image_id = fields['image_id']
            citation = Citation(
                id=Citation.objects.order_by("-id").first().id + 1 if Citation.objects.exists() else 1,
                person=person,
                station_id=station_id,
                vehicle=vehicle,
                video_id=video_id,
                image_id=image_id,
                location_id=None,
                court_date_id=court_date,
                fine_id=fields['fine_id'],
                citationID=citation_id,
                datetime=datetime.now(),
                posted_speed=fields['posted_speed'],
                speed=fields['violate_speed'],
                speed_pic=speed_pic,
                plate_pic=plate_pic,
                note=fields['note'],
                dist=fields['distance'],
                is_warning=fields['is_warning'],
                captured_date=date_object,
                isRejected=fields['is_rejected'],
                isSendBack=False,
                image_location=fields['location_id']
            )
            citation.save()
            return citation

    @staticmethod
    def update_media_data(media_id, citation, fields,speed_pic,plate_pic):
        reject_id = fields['reject_id']
        
        if reject_id == 0:
            reject_id = None 
    
        if fields['mediaType'] == 1:
            media = Video.objects.get(id=media_id)
            media.citation_id = citation.id
            media.isAdjudicated = fields['is_adjudicated']
            media.isRejected = fields['is_rejected']
            media.isSent = False
            media.reject_id = reject_id if reject_id else None
            media.save()
        elif fields['mediaType'] == 2:
            media = Image.objects.get(id=media_id)
            media.speed_image_url = speed_pic
            media.lic_image_url = plate_pic
            media.citation_id = citation.id
            media.isAdjudicated = fields['is_adjudicated']
            media.isSent = False
            media.isRejected = fields['is_rejected']
            media.reject_id = reject_id if reject_id else None
            media.save()

    @staticmethod
    def save_metadata(station_id, user, media_id ,fields ,citation):
        if fields['mediaType'] == 1:
            metadata = adj_metadata(
                station_id=station_id,
                user=user,
                video=Video.objects.get(id=media_id),
                image=None,
                citationID=citation.citationID,
                citation_id=citation.id,
                timeAdj=datetime.now(),
            )
            metadata.save()
        elif fields['mediaType'] == 2:
            metadata = adj_metadata(
                station_id=station_id,
                user=user,
                video=None,
                image=Image.objects.get(id=media_id),
                citationID=citation.citationID,
                citation_id=citation.id,
                timeAdj=datetime.now(),
            )
            metadata.save()

    @staticmethod
    def get_video_id_for_adjudication(station_id, initial_video_id):

        video_data = Video.objects.filter(
            id=initial_video_id,
            station=station_id,
            isRejected=False,
            isRemoved=False
        ).first()
        print(video_data.id)

        return video_data.id if video_data.id else None
    
    @staticmethod

    def get_image_id_for_adjudication(station_id, initial_image_id):
        image_data = Image.objects.filter(
            station=station_id,
            id=initial_image_id,
            isRejected=False,
            isRemoved=False
        ).first()

        return image_data.id if image_data.id else None
    

def update_existing_citation_data(fields, citationID, mediaType, videoId=None, imageId=None, 
                                  isAdjudicated=False, isSent=False, personId=None, vehicleId=None, station_id=None):
    citation = Citation.objects.filter(citationID=citationID).first()
    if not citation:
        raise ValueError(f"No citation found with ID {citationID}")

    if mediaType == 1:
        video_data = Video.objects.filter(id=citation.video_id).first()
        video_data.isSent = False
        video_data.isAdjudicated = True
        video_data.save()
        citation.video_id = videoId
        citation.location_id = fields.get('locationId', citation.location_id)
        citation.plate_pic = generate_s3_file_name(mediaType, videoId, station_id, None, fields.get('platePic')) or citation.plate_pic
        citation.speed_pic = generate_s3_file_name(mediaType, videoId, station_id, fields.get('speedPic'), None) or citation.speed_pic
        meta_data = adj_metadata.objects.filter(citationID=citation.citationID).update(
            timeAdj = datetime.now()
        )
    elif mediaType == 2:
        image_data = Image.objects.filter(id=citation.image_id).first()
        image_data.isSent = False
        image_data.isAdjudicated = True
        image_data.save()
        citation.image_id = imageId
        citation.image_location = fields.get('location_id', citation.image_location)
        citation.plate_pic = generate_s3_file_name(mediaType, imageId, station_id, None, fields.get('platePic')) or citation.plate_pic
        citation.speed_pic = generate_s3_file_name(mediaType, imageId, station_id, fields.get('speedPic'), None) or citation.speed_pic
        meta_data = adj_metadata.objects.filter(citationID=citation.citationID).update(
            timeAdj = datetime.now()
        )

    if personId and citation.person_id == personId:
        Person.objects.filter(id=personId).update(
            first_name=fields.get('first_name', ''),
            middle=fields.get('middle_name', ''),
            last_name=fields.get('last_name', ''),
            phone_number=fields.get('phone_number', ''),
            address=fields.get('address', ''),
            city=fields.get('city', ''),
            state=fields.get('state_ab', ''),
            zip=fields.get('zip_code', '')
        )

    if vehicleId and citation.vehicle_id == vehicleId:
        Vehicle.objects.filter(id=vehicleId).update(
            year=fields.get('vehicle_year', ''),
            make=fields.get('make', ''),
            model=fields.get('model', ''),
            color=fields.get('color', ''),
            plate=fields.get('license_plate', ''),
            lic_state_id=fields.get('license_state_id', ''),
            vin=fields.get('vin_number', '')
        )

    video_id = fields.get('video_id') if fields['mediaType'] == 1 and fields.get('video_id', 0) != 0 else None
    image_id = fields.get('image_id') if fields['mediaType'] == 2 and fields.get('image_id', 0) != 0 else None
    citation.person_id = personId if personId else citation.person_id
    citation.station_id = station_id
    citation.vehicle_id = vehicleId if vehicleId else citation.vehicle_id
    citation.court_date_id = fields.get('court_date', citation.court_date_id)
    citation.fine_id = fields.get('fine_id', citation.fine_id)
    citation.datetime = datetime.now()
    citation.posted_speed = fields.get('posted_speed', citation.posted_speed)
    citation.speed = fields.get('violate_speed', citation.speed)
    citation.note = fields.get('note', citation.note)
    citation.dist = fields.get('distance', citation.dist)
    citation.is_warning = fields.get('is_warning', citation.is_warning)
    citation.captured_date = fields.get('date_object', citation.captured_date)
    citation.isRejected = fields.get('is_rejected', citation.isRejected)
    citation.isSendBack = False
    citation.save()




def generate_s3_file_name(media_type, media_id, station_id, speed_pic=None, plate_pic=None):
    s3_bucket_prefix = "https://ee-prod-s3-bucket.s3.amazonaws.com/"
    if speed_pic and speed_pic.startswith(s3_bucket_prefix):
        return speed_pic.split("?")[0]
    if plate_pic and plate_pic.startswith(s3_bucket_prefix):
        return plate_pic.split("?")[0] 
    if media_type == 1:
        video_data = Video.objects.filter(id=media_id, station_id=station_id).first()
        print(video_data)
        if not video_data:
            raise ValueError("Video data not found for the given mediaId and stationId")
        date_now = datetime.now()
        formatted_date = date_now.strftime("%m%d%Y%H%M%S.%f")
        if speed_pic:
            file_data = base64.b64decode(speed_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{video_data.caption}_speed_{formatted_date}.png"
            speed_pic_url = upload_to_s3(file_obj, file_name, "images")
            return speed_pic_url
        
        elif plate_pic:
            file_data = base64.b64decode(plate_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{video_data.caption}_plate_{formatted_date}.png"
            plate_pic_url = upload_to_s3(file_obj, file_name, "images")
            return plate_pic_url
    elif media_type == 2:
        image_data = Image.objects.filter(id=media_id, station_id=station_id).first()
        print(image_data)
        if not image_data:
            raise ValueError("Image data not found for the given mediaId and stationId")
        date_now = datetime.now()
        formatted_date = date_now.strftime("%m%d%Y%H%M%S.%f")
        if speed_pic:
            file_data = base64.b64decode(speed_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{image_data.plate_image_filename}.png"
            speed_pic_url = upload_to_s3(file_obj, file_name, "PGM2/speed")
            return speed_pic_url
        
        elif plate_pic:
            file_data = base64.b64decode(plate_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{image_data.plate_image_filename}.jpg"
            plate_pic_url = upload_to_s3(file_obj, file_name, "PGM2/plates")
            return plate_pic_url
    else:
        raise ValueError("Invalid media type")
    
template = get_template("pdf_final.html")
template_maryland = get_template("maryland-pdf.html")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
options = {
    "page-size": "Letter",
    "enable-local-file-access": "",
}



def create_pdf(filename, data, station_name):
    try:
        if station_name in ['FED-M', 'HUD']:
            html = template_maryland.render(data)
        else:
            html = template.render(data)
        
        location = os.path.join(BASE_DIR, "media", filename)

        pdfkit.from_string(html, location, configuration=config, options=options)

        with open(location, "rb") as pdf_file:
            upload_to_s3(pdf_file, filename, "pdfs")
        os.remove(location)

    except OSError as e:
        print(f"wkhtmltopdf error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise
    
def get_pdf_base64(filename):
    path = "pdfs/" + filename
    try:
        pdf_content = s3_get_file(path)
    except FileNotFoundError:
        return "File not found.."
    if pdf_content:
        base64_pdf=base64.b64encode(pdf_content).decode('utf-8')
        return base64_pdf
    else:
        return None
    
def get_odr_data_for_csv(stationId):
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    csv_meta_data = Odr_csv_metadata.objects.filter(date__date=date,station_id=stationId)

    quickpd_data = []
    for meta in csv_meta_data:
        quickpd_data.append(meta.odr_meta)
    serialized_data = [
            {
                "odr_id": obj.id,
                "agency_name": obj.agency_name,
                "state_program_code": obj.state_program_code,
                "state_funding_code": obj.state_funding_code,
                "agency_id": obj.agency_id,
                "louisiana_taxpayer_number": obj.louisiana_taxpayer_number,
                "latoga_agency_code": obj.latoga_agency_code,
                "latoga_program_code": obj.latoga_program_code,
                "latoga_region_code": obj.latoga_region_code,
                "odr_debt_type": obj.odr_debt_type,
                "agency_debt_id": obj.agency_debt_id,
                "debtor_type": obj.debtor_type,
                "delinquency_date": obj.delinquency_date,
                "finalized_date": obj.finalized_date,
                "interest_rate": obj.interest_rate,
                "interest_type": obj.interest_type,
                "interest_to_date": obj.interest_to_date,
                "prescription_expiration_date": obj.prescription_expiration_date,
                "prescription_amount": obj.prescription_amount,
                "ssn": obj.ssn,
                "fein": obj.fein,
                "drivers_license_number": obj.drivers_license_number,
                "drivers_license_state": obj.drivers_license_state,
                "business_name": obj.business_name,
                "full_name": obj.full_name,
                "last_name": obj.last_name,
                "first_name": obj.first_name,
                "middle_name": obj.middle_name,
                "suffix": obj.suffix,
                "dba": obj.dba,
                "address": obj.address,
                "address_2": obj.address_2,
                "unit_type": obj.unit_type,
                "unit": obj.unit,
                "city": obj.city,
                "state": obj.state,
                "zip_code": obj.zip_code,
                "country": obj.country,
                "address_type": obj.address_type,
                "date_of_birth": obj.date_of_birth,
                "phone1_type": obj.phone1_type,
                "home_area_code": obj.home_area_code,
                "home_phone_number": obj.home_phone_number,
                "phone2_type": obj.phone2_type,
                "business_area_code": obj.business_area_code,
                "business_phone_number": obj.business_phone_number,
                "phone3_type": obj.phone3_type,
                "cell_area_code": obj.cell_area_code,
                "cell_phone_number": obj.cell_phone_number,
                "phone4_type": obj.phone4_type,
                "fax_area_code": obj.fax_area_code,
                "fax_number": obj.fax_number,
                "email_address": obj.email_address,
                "debt_short_description": obj.debt_short_description,
                "debt_long_description": obj.debt_long_description,
                "day_60_letter_mail_date": obj.day_60_letter_mail_date,
                "judgement_date": obj.judgement_date,
                "passback_information_1": obj.passback_information_1,
                "passback_information_2": obj.passback_information_2,
                "passback_information_3": obj.passback_information_3,
                "passback_information_4": obj.passback_information_4,
                "agency_last_payment_date": obj.agency_last_payment_date,
                "agency_last_payment_amt": obj.agency_last_payment_amt,
                "fees_prior_to_plc": obj.fees_prior_to_plc,
                "fees_by_OCA_ECA": obj.fees_by_OCA_ECA,
                "line_item_code_1": obj.line_item_code_1,
                "line_item_incurred_date_1": obj.line_item_incurred_date_1,
                "line_item_amount_1": obj.line_item_amount_1,
                "line_item_code_2": obj.line_item_code_2,
                "line_item_incurred_date_2": obj.line_item_incurred_date_2,
                "line_item_amount_2": obj.line_item_amount_2
            }
            for obj in quickpd_data
        ]
    return serialized_data

def save_odr_csv_data(citationId, user_station_id):
    
    citation_data = Citation.objects.filter(citationID=citationId).first()
    person_data = Person.objects.filter(id=citation_data.person_id).first()
    vehicle_data = Vehicle.objects.filter(id=citation_data.vehicle_id).first()
    
    odr_data = UnpaidCitation.objects.filter(ticket_number=citationId).first()
    
    sup_data = sup_metadata.objects.filter(citation=citation_data.id).first()
    
    dt = sup_data.timeApp + timedelta(days=30)
    
    second_mail_date = odr_data.second_mail_due_date
    date_obj = datetime.strptime(second_mail_date, "%Y-%m-%d")
    final_date = date_obj + timedelta(days = 60)
    day_60_date = date_obj + timedelta(days = 120)
    
    delinquency_date = datetime.strftime(dt, "%Y-%m-%d")
    finalized_date = datetime.strftime(final_date, "%Y-%m-%d")
    day_60_letter_mail_date = datetime.strftime(day_60_date, "%Y-%m-%d")
    fees_prior_to_plc = odr_data.second_mail_fine - odr_data.amount
    
    if person_data.middle: 
        full_name = person_data.first_name + ' ' + person_data.middle + ' ' + person_data.last_name
    else:
        full_name = person_data.first_name + ' ' + person_data.last_name
    agency_name = 'City of Marksville PD - EE'
    debt_short_description = "Citation No: " + citation_data.citationID
    debt_long_description = "Speed Violation; Citation No: " +  citation_data.citationID
    get_user_station_id = Station.objects.get(id = user_station_id)
    
    quick = OdrCSVdata(
        station = get_user_station_id,
        odr_debt_type = 'Speed Violation',
        debtor_type = 'I',
        agency_name = agency_name,
        state_program_code = 50,
        state_funding_code = 999,
        agency_id = 'MI6',
        louisiana_taxpayer_number ='2153779',
        latoga_agency_code = 0,
        latoga_program_code = 0,
        latoga_region_code = 0,
        agency_debt_id = citation_data.citationID,
        delinquency_date = delinquency_date,
        finalized_date = finalized_date,
        interest_rate = None,
        interest_type = "",
        interest_to_date = None,
        prescription_expiration_date = None,
        prescription_amount = 0,
        ssn = "",
        fein = "",
        drivers_license_number = "",
        drivers_license_state = "",
        business_name = "",
        full_name = full_name,
        last_name = person_data.last_name,
        first_name = person_data.first_name,
        middle_name = person_data.middle,
        suffix = "",
        dba = "",
        address = person_data.address,
        address_2 = "",
        unit_type = "",
        unit = "",
        city = person_data.city,
        state = person_data.state,
        zip_code = person_data.zip,
        country = 'US',
        address_type = "",
        date_of_birth = None,
        phone1_type = "",
        home_area_code = "",
        home_phone_number = "",
        phone2_type = "",
        business_area_code = "",
        business_phone_number = "",
        phone3_type = "",
        cell_area_code = "",
        cell_phone_number = "",
        phone4_type = "",
        fax_area_code = "",
        fax_number = "",
        email_address = "",
        debt_short_description = debt_short_description,
        debt_long_description = debt_long_description,
        day_60_letter_mail_date = day_60_letter_mail_date,
        judgement_date = None,
        passback_information_1 = "",
        passback_information_2 = "",
        passback_information_3 = "",
        passback_information_4 = "",
        agency_last_payment_date = None,
        agency_last_payment_amt = 0,
        fees_prior_to_plc = fees_prior_to_plc,
        fees_by_OCA_ECA = fees_prior_to_plc,
        line_item_code_1 = "Principal",
        line_item_incurred_date_1 = day_60_letter_mail_date,
        line_item_amount_1 = odr_data.amount,
        line_item_code_2 = 'ECA Fee',
        line_item_incurred_date_2 = day_60_letter_mail_date,
        line_item_amount_2 = fees_prior_to_plc
        )
    
    quick.save()
        
    return quick.id

def save_odr_csv_meta_data(quickPDId, citationId, userId, stationId):
    if not quickPDId:
        raise ValueError("quickPDId is required")
    if not citationId:
        raise ValueError("Citation ID is required")
    if not userId:
        raise ValueError("User ID is required")
    if not stationId:
        raise ValueError("Station ID is required")
    quickPDID = OdrCSVdata.objects.get(id=quickPDId)
    csv = Odr_csv_metadata.objects.filter(odr_meta=quickPDID, station_id=stationId).first()

    if csv:
        csv.user_id = userId
        csv.date = datetime.now()
        csv.save()
        print(f"Updated CSV metadata: {csv}")
    else:
        csv = Odr_csv_metadata(
            user_id=userId,
            odr_meta=quickPDID,
            date=datetime.now(),
            station_id=stationId
        )
        csv.save()
        print(f"Created new CSV metadata: {csv}")

    return

# def create_odr_csv_and_pdf_data(citationID,stationId,stationName,image_flow):
#     citation_ID = str(citationID)
#     data = get_cit_refactor(citation_ID, stationId,image_flow)
#     filename = f"{citation_ID}.pdf"
#     save_pdf(filename,stationName,data)
#     create_refactor_csv(stationId)
    
    
def citation_data_for_odr_approved_table(from_date, to_date, search_string, page_index=1, page_size=10, station_id=None):
    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    from_date_str = from_date if from_date else None
    to_date_str = to_date if to_date else None

    query = Q()
    query_odr = Q()
    if from_date:
        query_odr &= Q(created_at__gte=from_date_str)
    if to_date:
        query_odr &= Q(datetime__lte=to_date_str)

    if search_string:
        search_string = search_string.lower().replace(" ", "")
        query &= (
            Q(citationID__icontains=search_string) |
            Q(person__first_name__icontains=search_string) |
            Q(person__last_name__icontains=search_string) |
            Q(vehicle__plate__icontains=search_string)
        )
        
    odr_citation_id = UnpaidCitation.objects.filter(query_odr, isApproved = True, pre_odr_mail_count =3).values_list('ticket_number', flat=True)
    print(list(odr_citation_id))
    citations = Citation.objects.filter(citationID__in = odr_citation_id, isApproved=True, station_id=station_id) \
        .select_related('person', 'fine') \
        .order_by('-datetime')

    citation_ids = [citation.citationID for citation in citations]
    quick_pd_data = {
        qpd.ticket_num: qpd for qpd in QuickPD.objects.filter(ticket_num__in=citation_ids)
    }

    citation_data = []
    for citation in citations:
        media_data = None
        person_data = citation.person
        fine_data = citation.fine
        odr_amount = UnpaidCitation.objects.filter(ticket_number= citation.citationID, 
                                                   isApproved= True, pre_odr_mail_count =3 ).first()
        
        odr_fine_amount = odr_amount.amount + ((odr_amount.amount) * Decimal('0.15'))
        
        quick_pd_entry = quick_pd_data.get(citation.citationID)
        
        if quick_pd_entry.middle: 
            full_name = quick_pd_entry.first_name + ' ' + quick_pd_entry.middle + ' ' + quick_pd_entry.last_name
        else:
            full_name = quick_pd_entry.first_name + ' ' + quick_pd_entry.last_name
        
        date_obj = quick_pd_entry.arraignment_date
        initial_due_date = datetime.strptime(date_obj, "%m%d%Y")
        
        odr_due_date = odr_amount.odr_due_date
        odr_due_date = datetime.strftime(odr_due_date, "%B %#d, %Y")
        if citation.video_id:
            media_data = {
                'citationId': citation.id,
                'citationID': citation.citationID,
                'mediaId': f'V-{citation.video_id}',
                'fine': fine_data.fine if fine_data else None,
                'fullName': full_name,
                'capturedDate': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
                'initialDueDate': initial_due_date.strftime("%B %#d, %Y") if initial_due_date else None,
                'odrFine': odr_fine_amount,
                'odrMailCount': 3,
                'odrDueDate': odr_due_date
            }

        elif citation.image_id: 
            media_data = {
                'citationId': citation.id,
                'citationID': citation.citationID,
                'mediaId': f'I-{citation.image_id}',
                'fine': fine_data.fine if fine_data else None,
                'fullName': full_name,
                'capturedDate': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
                'initialDueDate': initial_due_date.strftime("%B %#d, %Y") if initial_due_date else None,
                'odrFine': odr_fine_amount,
                'odrMailCount': 3,
                'odrDueDate': odr_due_date
            }

        if media_data:
            citation_data.append(media_data)

    paginator = Paginator(citation_data, page_size)
    page = paginator.get_page(page_index)

    return {
        "data": list(page.object_list),
        "total_records": paginator.count,
        "has_next_page": page.has_next(),
        "has_previous_page": page.has_previous(),
        "current_page": page.number,
        "total_pages": paginator.num_pages,
    }
    
def citation_data_for_odr_approved_table_download(from_date, to_date, search_string, page_index=1, page_size=10, station_id=None):
    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    from_date_str = from_date if from_date else None
    to_date_str = to_date if to_date else None

    query = Q()
    query_odr = Q()
    if from_date:
        query_odr &= Q(created_at__gte=from_date_str)
    if to_date:
        query_odr &= Q(datetime__lte=to_date_str)

    if search_string:
        search_string = search_string.lower().replace(" ", "")
        query &= (
            Q(citationID__icontains=search_string) |
            Q(person__first_name__icontains=search_string) |
            Q(person__last_name__icontains=search_string) |
            Q(vehicle__plate__icontains=search_string)
        )
        
    odr_citation_id = OdrCitation.objects.filter(query_odr, isApproved = True).values_list('citation', flat=True)
    print(list(odr_citation_id))
    citations = Citation.objects.filter(id__in = odr_citation_id, isApproved=True, station_id=station_id) \
        .select_related('person', 'fine') \
        .order_by('-datetime')

    citation_ids = [citation.citationID for citation in citations]
    quick_pd_data = {
        qpd.ticket_num: qpd for qpd in QuickPD.objects.filter(ticket_num__in=citation_ids)
    }

    citation_data = []
    for citation in citations:
        media_data = None
        person_data = citation.person
        fine_data = citation.fine
        odr_amount = OdrCitation.objects.filter(citation= citation.id).first()
        
        odr_fine_amount = odr_amount.initial_amount + ((odr_amount.initial_amount) * Decimal('0.15'))
        
        quick_pd_entry = quick_pd_data.get(citation.citationID)
        
        if quick_pd_entry.middle: 
            full_name = quick_pd_entry.first_name + ' ' + quick_pd_entry.middle + ' ' + quick_pd_entry.last_name
        else:
            full_name = quick_pd_entry.first_name + ' ' + quick_pd_entry.last_name
        
        date_obj = quick_pd_entry.arraignment_date
        initial_due_date = datetime.strptime(date_obj, "%m%d%Y")
        
        odr_due_date = odr_amount.created_date + timedelta(days=60)
        odr_due_date = datetime.strftime(odr_due_date, "%B %#d, %Y")
        if citation.video_id:
            media_data = {
                'Citation ID': citation.citationID,
                'Video/Image ID': f'V-{citation.video_id}',
                'Fine': fine_data.fine if fine_data else None,
                'Full Name': full_name,
                'Captured Date': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
                'Initial Due Date': initial_due_date.strftime("%B %#d, %Y") if initial_due_date else None,
                'ODR Fine': odr_fine_amount,
                'ODR Mail Count': 3,
                'ODR Due Date': odr_due_date
            }

        elif citation.image_id: 
            media_data = {
                'Citation ID': citation.citationID,
                'Video/Image ID': f'I-{citation.image_id}',
                'Fine': fine_data.fine if fine_data else None,
                'Full Name': full_name,
                'Captured Date': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
                'Initial Due Date': initial_due_date.strftime("%B %#d, %Y") if initial_due_date else None,
                'ODR Fine': odr_fine_amount,
                'ODR Mail Count': 3,
                'ODR Due Date': odr_due_date
            }

        if media_data:
            citation_data.append(media_data)

    paginator = Paginator(citation_data, page_size)
    page = paginator.get_page(page_index)

    return {
        "data": list(page.object_list),
        "total_records": paginator.count,
        "has_next_page": page.has_next(),
        "has_previous_page": page.has_previous(),
        "current_page": page.number,
        "total_pages": paginator.num_pages,
    }

import csv
from datetime import datetime, date
from django.http import HttpResponse

def format_value(val):
    if val is None:
        return None
    if isinstance(val, (int, float)) and val == 0:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime('%m/%d/%Y')
    return val

def download_odr_csv(queryset):
    filename = f"EE_PLC_{datetime.now().strftime('%Y%m%d')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    headers = [
        "Agency Name", "State Program Code", "State Funding Code", "Agency ID", "Louisiana Taxpayer Number (LTN)",
        "LATOGA Agency Code", "LATOGA Program Code", "LATOGA Region Code", "ODR Debt Type", "Agency Debt ID",
        "Debtor Type", "Delinquency Date", "Finalized Date", "Interest Rate", "Interest Type", "Interest To Date",
        "Prescription/Expiration Date", "Prescription Amount", "SSN", "FEIN", "Driver's License Number",
        "Driver's License State", "Business Name", "Full Name", "Last Name", "First Name", "Middle Name", "Suffix",
        "DBA", "Address", "Address 2", "Unit Type", "Unit", "City", "State", "Zip Code", "Country", "Address Type",
        "Date of Birth", "Phone1 Type", "Home Area Code", "Home Phone Number", "Phone2 Type", "Business Area Code",
        "Business Phone Number", "Phone3 Type", "Cell Area Code", "Cell Phone Number", "Phone4 Type", "Fax Area Code",
        "Fax Number", "Email Address", "Debt Short Description", "Debt Long Description", "60 Day Letter Mail Date",
        "Judgement Date", "Passback Information 1", "Passback Information 2", "Passback Information 3",
        "Passback Information 4", "Agency Last Payment Date", "Agency Last Payment Amt", "Fees prior to plc",
        "Fees by OCA + ECA", "Line Item Code", "Line Item Incurred Date", "Line Item Amount",
        "Line Item Code", "Line Item Incurred Date", "Line Item Amount"
    ]
    writer.writerow(headers)

    for obj in queryset:
        writer.writerow([
            format_value(obj.agency_name),
            format_value(obj.state_program_code),
            format_value(obj.state_funding_code),
            format_value(obj.agency_id),
            format_value(obj.louisiana_taxpayer_number),
            format_value(obj.latoga_agency_code),
            format_value(obj.latoga_program_code),
            format_value(obj.latoga_region_code),
            format_value(obj.odr_debt_type),
            format_value(obj.agency_debt_id),
            format_value(obj.debtor_type),
            format_value(obj.delinquency_date),
            format_value(obj.finalized_date),
            format_value(obj.interest_rate),
            format_value(obj.interest_type),
            format_value(obj.interest_to_date),
            format_value(obj.prescription_expiration_date),
            format_value(obj.prescription_amount),
            format_value(obj.ssn),
            format_value(obj.fein),
            format_value(obj.drivers_license_number),
            format_value(obj.drivers_license_state),
            format_value(obj.business_name),
            format_value(obj.full_name),
            format_value(obj.last_name),
            format_value(obj.first_name),
            format_value(obj.middle_name),
            format_value(obj.suffix),
            format_value(obj.dba),
            format_value(obj.address),
            format_value(obj.address_2),
            format_value(obj.unit_type),
            format_value(obj.unit),
            format_value(obj.city),
            format_value(obj.state),
            format_value(obj.zip_code),
            format_value(obj.country),
            format_value(obj.address_type),
            format_value(obj.date_of_birth),
            format_value(obj.phone1_type),
            format_value(obj.home_area_code),
            format_value(obj.home_phone_number),
            format_value(obj.phone2_type),
            format_value(obj.business_area_code),
            format_value(obj.business_phone_number),
            format_value(obj.phone3_type),
            format_value(obj.cell_area_code),
            format_value(obj.cell_phone_number),
            format_value(obj.phone4_type),
            format_value(obj.fax_area_code),
            format_value(obj.fax_number),
            format_value(obj.email_address),
            format_value(obj.debt_short_description),
            format_value(obj.debt_long_description),
            format_value(obj.day_60_letter_mail_date),
            format_value(obj.judgement_date),
            format_value(obj.passback_information_1),
            format_value(obj.passback_information_2),
            format_value(obj.passback_information_3),
            format_value(obj.passback_information_4),
            format_value(obj.agency_last_payment_date),
            format_value(obj.agency_last_payment_amt),
            format_value(obj.fees_prior_to_plc),
            format_value(obj.fees_by_OCA_ECA),
            format_value(obj.line_item_code_1),
            format_value(obj.line_item_incurred_date_1),
            format_value(obj.line_item_amount_1),
            format_value(obj.line_item_code_2),
            format_value(obj.line_item_incurred_date_2),
            format_value(obj.line_item_amount_2),
        ])

    return response
