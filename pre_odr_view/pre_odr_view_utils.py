from video.models import UnpaidCitation, Citation, Person, Vehicle, Video, Image, ImageLocation, PreOdrXpressBillPay, PreOdrCSVMetadata, sup_metadata, PreOdrFineScheduler, Agency, Station, road_location
from ees.utils import upload_to_s3, get_presigned_url
import base64
from io import BytesIO
from datetime import datetime, timedelta
from accounts_v2.serializer import ServiceResponse, APIResponse
from rest_framework.response import Response
import re
from docx import Document
from decimal import Decimal, ROUND_DOWN
from django.db import transaction
from pre_odr_view.serializer import UploadUnpiadCitationDataResponseModel, GetMailerPDFBase64StringOutputModel
from video.pdf_creation import save_pre_odr_mailer_notice_pdf, create_pre_odr_mailer_notice_pdf
from video.views import xpress_csv
from decouple import config as ENV_CONFIG
from django.db.models import Q
from django.core.paginator import Paginator
from django.template.loader import get_template
import base64
import pdfkit
import os
import io
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
options = {"page-size": "Letter"}
template_first_mailer = get_template("pre_odr_mailer_notice_pdf.html")
template_second_mailer = get_template("pre_odr_second_mailer_notice_pdf.html")

MAR_SECURE_PAY_QR= ENV_CONFIG("MAR-SECURE-PAY-QR")
MAR_BADGE = ENV_CONFIG("MAR-BADGE")
BASE_DIR= ENV_CONFIG("BASE_DIR")

def upload_unpaid_citation_data(base64StringDocxFile, base64StringTxtFile):
    current_date = datetime.now().date()
    unproceed_citation_ids = []
    
    if not base64StringDocxFile and not base64StringTxtFile:
        return Response(ServiceResponse({
            "statusCode": 400,
            "message": "File not found",
            "data": None
        }).data, status=200)
    txt_decoded = ""
    docx_decoded = None
    docx_document = None

    if base64StringTxtFile:
        try:
            txt_decoded = base64.b64decode(base64StringTxtFile).decode('utf-8')
        except (base64.binascii.Error, UnicodeDecodeError):
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid base64 string for TXT file",
                "data": None
            }).data, status=200)

    if base64StringDocxFile:
        try:
            docx_decoded = base64.b64decode(base64StringDocxFile)
            docx_document = Document(BytesIO(docx_decoded))
        except (base64.binascii.Error, UnicodeDecodeError, Exception):
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid base64 string or DOCX file",
                "data": None
            }).data, status=200)

    txt_citations = extract_citations_from_txt_content(txt_decoded if txt_decoded else None)
    docx_citations = extract_citations_from_docx_document(docx_document if docx_document else None)

    all_citations = txt_citations + docx_citations
    all_ticket_ids = [c['citationID'] for c in all_citations]

    existing_ticket_ids = set(
        UnpaidCitation.objects.filter(ticket_number__in=all_ticket_ids)
        .values_list('ticket_number', flat=True)
    )
    
    if existing_ticket_ids:
        existing_citations = UnpaidCitation.objects.filter(ticket_number__in=existing_ticket_ids)
        for citation in existing_citations:
            if citation.first_mail_due_date:
                try:
                    first_mail_due_date = citation.first_mail_due_date
                    if isinstance(first_mail_due_date, str):
                        first_mail_due_date = datetime.strptime(first_mail_due_date, '%Y-%m-%d').date()

                    if current_date > first_mail_due_date and citation.pre_odr_mail_count == 1:
                        citation.isApproved = False
                        citation.save(update_fields=['isApproved'])
                except (ValueError, TypeError):
                    unproceed_citation_ids.append(citation.ticket_number)
        

    new_citations = [c for c in all_citations if c['citationID'] not in existing_ticket_ids]

    unpaid_objs = [
        UnpaidCitation(
            ticket_number=c['citationID'],
            off_date=c['offenseDate'],
            arr_date=c['arraignmentDate'],
            amount=c['amount'],
            payment=c['payment'],
            balance=c['balance'],
            pre_odr_mail_count=c['preOdrMailCount'],
            isApproved=c['isApproved'],
            video=c['video'],
            image=c['image'],
            full_name=c['fullName'],
            station=c['station']
        ) for c in new_citations
    ]

    with transaction.atomic():
        UnpaidCitation.objects.bulk_create(unpaid_objs)

    return Response(ServiceResponse({
        "statusCode": 200,
        "message": "Processed successfully",
        "data": UploadUnpiadCitationDataResponseModel({
            "processedCitationCount": len(new_citations),
            "unprocessedCitationCount": len(unproceed_citation_ids)
        }).data
    }).data, status=200)


def extract_citations_from_txt_content(txt_content=None):
    citations = []
    if not txt_content :
        return citations
    ticket_pattern = re.compile(
        r'([A-Z]+-\d{8})\s+'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'(\d+\.\d{2})\s+'
        r'(\d+\.\d{2})\s+'
        r'(\d+\.\d{2})'
    )
    lines = txt_content.splitlines()
    for line in lines:
        match = ticket_pattern.match(line.strip())
        if match:
            original = Citation.objects.filter(citationID=match.group(1)).first()
            citations.append({
                'citationID': match.group(1),
                'offenseDate': datetime.strptime(match.group(2), '%m/%d/%Y').date(),
                'arraignmentDate': datetime.strptime(match.group(3), '%m/%d/%Y').date(),
                'amount': Decimal(match.group(4)),
                'payment': Decimal(match.group(5)),
                'balance': Decimal(match.group(6)),
                'preOdrMailCount': 0,
                'isApproved': False,
                'video': original.video if original else None,
                'image': original.image if original else None,
                'fullName': (
                    f"{original.person.first_name} {original.person.middle} {original.person.last_name}"
                    if original and original.person else None
                ),
                'station': original.station if original else None
            })
    return citations


def extract_citations_from_docx_document(docx_document=None):
    citations = []

    if not docx_document:
        return citations
    
    ticket_pattern = re.compile(
        r'([A-Z]+-\d{8})\s+'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'(\d+\.\d{2})\s+'
        r'(\d+\.\d{2})\s+'
        r'(\d+\.\d{2})'
    )
    
    for para in docx_document.paragraphs:
        match = ticket_pattern.match(para.text.strip())
        if match:
            original = Citation.objects.filter(citationID=match.group(1)).first()
            citations.append({
                'citationID': match.group(1),
                'offenseDate': datetime.strptime(match.group(2), '%m/%d/%Y').date(),
                'arraignmentDate': datetime.strptime(match.group(3), '%m/%d/%Y').date(),
                'amount': Decimal(match.group(4)),
                'payment': Decimal(match.group(5)),
                'balance': Decimal(match.group(6)),
                'preOdrMailCount': 0,
                'isApproved': False,
                'video': original.video if original else None,
                'image': original.image if original else None,
                'fullName': (
                    f"{original.person.first_name} {original.person.middle} {original.person.last_name}"
                    if original and original.person else None
                ),
                'station': original.station if original else None
            })
    return citations


def get_batch_id(userId):
    user_batch_id = {'47': 1703, '74': 2202, '75': 2201, '118': '0172'}


def extract_media_data(citationID, userId):
    location_name = ""
    officer_badge = ""
    formatted_date = ""
    formatted_time = ""

    if citationID.video_id:
        video_data = Video.objects.filter(id=citationID.video_id).first()
        location_data = road_location.objects.filter(id=video_data.location_id).first()
        location_name = location_data.location_name
        try:
            datetime_obj = datetime.strptime(str(video_data.datetime), "%Y-%m-%d %H:%M:%S.%f%z")
        except ValueError:
            try:
                datetime_obj = datetime.strptime(str(video_data.datetime), "%Y-%m-%d %H:%M:%S%z")
            except ValueError:
                datetime_obj = None

        formatted_date = datetime_obj.strftime("%m%d%Y") if datetime_obj else ""
        formatted_time = datetime_obj.strftime("%H%M") if datetime_obj else ""
        officer_badge = video_data.officer_badge.lstrip("0")

    elif citationID.image_id:
        image_data = Image.objects.filter(id=citationID.image_id).first()
        image_location_data = ImageLocation.objects.filter(location_id=image_data.location_id).first()
        location_name = image_location_data.name
        if image_data.officer_badge:
            officer_badge = image_data.officer_badge
        else:
            batch_id = get_batch_id(userId)
            officer_badge = batch_id
            image_data.save()

    return location_name, officer_badge, formatted_date, formatted_time


def create_xpress_bill_pay(stationId, citationID, person_data, vehicle_data, location_name, formatted_date, formatted_time, officer_badge):
    existingPreOdrXpressBillPay = PreOdrXpressBillPay.objects.filter(ticket_num=citationID).first()
    
    if existingPreOdrXpressBillPay:
        return existingPreOdrXpressBillPay
    else:
        return PreOdrXpressBillPay.objects.create(
            station_id=stationId,
            offense_date=formatted_date,
            offense_time=formatted_time,
            ticket_num=citationID.citationID,
            first_name=person_data.first_name,
            middle=person_data.middle,
            last_name=person_data.last_name,
            address=person_data.address,
            city=person_data.city,
            state=person_data.state,
            zip=person_data.zip,
            arraignment_date=(datetime.now() + timedelta(days=30)).strftime("%m%d%Y"),
            actual_speed=citationID.speed,
            posted_speed=citationID.posted_speed,
            officer_badge=officer_badge,
            notes=location_name,
            plate_num=vehicle_data.plate,
            plate_state=vehicle_data.lic_state.ab,
            vin=vehicle_data.vin,
            phone_number=person_data.phone_number,
        )


def process_first_mail(unpaid_citation, pre_odr_fine_scheduler):
    unpaid_citation.isApproved = True
    unpaid_citation.pre_odr_mail_count += 1
    first_mail_days = 30
    first_mail_fine = unpaid_citation.amount + (unpaid_citation.amount * 20 / Decimal(100))
    unpaid_citation.first_mail_due_date = (datetime.now() + timedelta(days=first_mail_days)).strftime('%Y-%m-%d')
    unpaid_citation.first_mail_fine = first_mail_fine
    unpaid_citation.save()


def process_second_mail(unpaid_citation, citationID, pre_odr_fine_scheduler):
    unpaid_citation.isApproved = True
    unpaid_citation.pre_odr_mail_count += 1
    second_mail_days = 30
    second_mail_fine = unpaid_citation.amount + (unpaid_citation.amount * 30 / Decimal(100))
    unpaid_citation.second_mail_due_date = (datetime.now() + timedelta(days=second_mail_days)).strftime('%Y-%m-%d')
    unpaid_citation.second_mail_fine = second_mail_fine
    unpaid_citation.save()

    if not citationID.captured_date:
        citationID.captured_date = datetime.now().strftime("%Y-%m-%d")
        citationID.save()


def create_csv_metadata(userId, xpress_pay, stationId):
    existingPreOdrCsvMetaData = PreOdrCSVMetadata.objects.filter(xpress_bill_pay_id=xpress_pay.id).first()
    if existingPreOdrCsvMetaData:
        return
    else:
        PreOdrCSVMetadata.objects.create(
            user_id=userId,
            xpress_bill_pay=xpress_pay,
            date=datetime.now(),
            station_id=stationId,
        )


def generate_pdf_and_handle_rollback(citationID, stationId, stationName, unpaid_citation, context, xpress_pay):
    filename = f"{citationID.citationID}_first-mailer-notice.pdf" if unpaid_citation.pre_odr_mail_count == 1 else f"{citationID.citationID}_second-mailer-notice.pdf"
    check_pdf = save_pre_odr_mailer_notice_pdf(filename, stationName, context)
    if check_pdf:
        station_object = Station.objects.filter(id=stationId).first()
        xpress_csv(station_object)
    else:
        PreOdrCSVMetadata.objects.filter(xpress_bill_pay=xpress_pay).delete()
        xpress_pay.delete()


def process_pre_odr_citation(citationIDs, stationId, userId, stationName, agencyId):
    try:
        citation_list = Citation.objects.filter(citationID__in=citationIDs)
        agencyData = Agency.objects.filter(id=agencyId).first()
        pre_odr_fine_scheduler = PreOdrFineScheduler.objects.filter(agency_id=agencyId).first()

        for citationID in citation_list:
            person_data = Person.objects.filter(id=citationID.person_id).first()
            vehicle_data = Vehicle.objects.filter(id=citationID.vehicle_id).first()

            location_name, officer_badge, formatted_date, formatted_time = extract_media_data(citationID, userId)
            xpress_pay = create_xpress_bill_pay(stationId, citationID, person_data, vehicle_data, location_name, formatted_date, formatted_time, officer_badge)
            pre_ode_csv_meta_data = create_csv_metadata(userId, xpress_pay, stationId)
            unpaid_citation = UnpaidCitation.objects.filter(ticket_number=citationID.citationID).first()
            if unpaid_citation:
                if unpaid_citation.pre_odr_mail_count == 0:
                    
                    process_first_mail(unpaid_citation, pre_odr_fine_scheduler)
                    first_mail_date_time_app = (
                    datetime.strptime(unpaid_citation.first_mail_due_date, "%Y-%m-%d").date() - timedelta(days=30)
                )
                    second_mail_date_time_app = (
                        datetime.strptime(unpaid_citation.first_mail_due_date, "%Y-%m-%d").date() + timedelta(days=1)
                    )
                    
                    if not pre_odr_fine_scheduler:
                        return Response(ServiceResponse({
                            "statusCode" : 400,
                            "message" : "Agency is not yet filled pre odr data",
                            "data" : []
                        }).data, status=200)
                    first_mail_due_dates = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.first_mailer_day_gap)
                    first_mail_due_date_with_discount = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.second_mailer_day_gap)

                    base_fine = citationID.fine.fine
                    first_mailer_fine_with_discount = base_fine + (base_fine * 20 / 100)
                    first_mailer_fine_without_discount = base_fine + (base_fine * 30 / 100)
                    transfer_to_odr_amount_due = (base_fine * Decimal("1.55")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
                    transfer_to_odr_issue_date = first_mail_due_dates + timedelta(days=1)

                    try:
                        metadata = sup_metadata.objects.filter(citation=citationID).first()
                        initial_time_app = metadata.timeApp.date() if metadata else ""
                    except sup_metadata.DoesNotExist:
                        initial_time_app = ""

                    try:
                        first_mail_due_date_obj = datetime.strptime(unpaid_citation.first_mail_due_date, "%Y-%m-%d") + timedelta(days=30)
                        formatted_first_mail_due_date = first_mail_due_date_obj.strftime("%b. %d, %Y").replace(" 0", " ")
                    except ValueError:
                        formatted_first_mail_due_date = "Invalid Date"

                    mar_secure_pay = get_presigned_url(MAR_SECURE_PAY_QR)
                    mar_badge = get_presigned_url(MAR_BADGE)

                    context = {
                        "citation": citationID,
                        "unpaidcitation": unpaid_citation,
                        "date": first_mail_date_time_app,
                        "agency_phone_number": agencyData.phone,
                        "agency_name": agencyData.name,
                        "agency_address": agencyData.address,
                        "agency_address_2": agencyData.address_2,
                        "first_mailer": unpaid_citation.pre_odr_mail_count == 1,
                        "second_mailer": unpaid_citation.pre_odr_mail_count == 2,
                        "first_mail_date_time_app": first_mail_date_time_app,
                        "initial_time_app": initial_time_app,
                        "second_mail_date_time_app": second_mail_date_time_app,
                        "first_mail_due_date_with_discount": first_mail_due_date_with_discount,
                        "first_mailer_fine_without_discount": first_mailer_fine_without_discount,
                        "first_mailer_fine_amount_discount": first_mailer_fine_with_discount,
                        "transfer_to_odr_amount_due": transfer_to_odr_amount_due,
                        "formatted_first_mail_due_date": formatted_first_mail_due_date,
                        "pre_odr_fine_scheduler": pre_odr_fine_scheduler,
                        "transfer_to_odr_issue_date": transfer_to_odr_issue_date,
                        "mar_secure_pay": mar_secure_pay,
                        "mar_badge": mar_badge,
                    }
                    generate_pdf_and_handle_rollback(citationID, stationId, stationName, unpaid_citation, context, xpress_pay)
                elif unpaid_citation.pre_odr_mail_count == 1:
                    process_second_mail(unpaid_citation, citationID, pre_odr_fine_scheduler)
                    citation = Citation.objects.get(citationID=citationID.citationID)
                    station = citation.station
                    agency_fine_schedular = station.station_agencies.first()
                    pre_odr_fine_scheduler = PreOdrFineScheduler.objects.get(agency= agency_fine_schedular)
                    #unpaid_citation = UnpaidCitation.objects.get(ticket_number=chosen)
                    first_mail_date_time_app = (
                                datetime.strptime(unpaid_citation.first_mail_due_date, "%Y-%m-%d").date() -
                                timedelta(days=30)
                            )
                    second_mail_date_time_app = (
                        datetime.strptime(unpaid_citation.second_mail_due_date, "%Y-%m-%d").date() -
                        timedelta(days=30)
                    )
                    first_mail_due_dates = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.first_mailer_day_gap) ## here we will assign 60 days

                    first_mail_due_date_with_discount = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.second_mailer_day_gap) ## first mailer days gap +30
                    
                    base_fine = citation.fine.fine
                    first_mailer_fine_with_discount = base_fine + (base_fine * 20 / 100)

                    first_mailer_fine_without_discount = base_fine + (base_fine * 30 / 100)
                    transfer_to_odr_amount_due = (base_fine * Decimal("1.55")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

                    transfer_to_odr_issue_date = first_mail_due_dates + timedelta(days=1)
                    try:
                        metadata = sup_metadata.objects.filter(citation=citation).first()
                        initial_time_app = metadata.timeApp.date()
                    except sup_metadata.DoesNotExist:
                        initial_time_app = ""

                    try:
                        first_mail_due_date_obj = datetime.strptime(unpaid_citation.first_mail_due_date, "%Y-%m-%d") + timedelta(days=30)
                        # Format the date to "Jan. 11, 2025"
                        formatted_first_mail_due_date = first_mail_due_date_obj.strftime("%b. %d, %Y").replace(" 0", " ")
                    except ValueError:
                        # Handle case where the date format is invalid or empty
                        formatted_first_mail_due_date = "Invalid Date"

                    try:
                        second_mail_due_date_obj = datetime.strptime(unpaid_citation.second_mail_due_date, "%Y-%m-%d")
                        # Format the date to "Jan. 11, 2025"
                        formatted_second_mail_due_date = second_mail_due_date_obj.strftime("%b. %d, %Y").replace(" 0", " ")
                    except ValueError:
                        # Handle case where the date format is invalid or empty
                        formatted_second_mail_due_date = "Invalid Date"
                    
                    # File name for the PDF
                    #filename = f"{citation.citationID}_second-mailer-notice.pdf"
                    mar_secure_pay = get_presigned_url(MAR_SECURE_PAY_QR)
                    mar_badge = get_presigned_url(MAR_BADGE)
                    context = {
                                "citation": citation,
                                "unpaidcitation": unpaid_citation,
                                "date": second_mail_date_time_app,
                                "agency_phone_number": agencyData.phone,
                                "agency_name": agencyData.name,
                                "agency_address": agencyData.address,
                                "agency_address_2": agencyData.address_2,
                                "first_mailer": unpaid_citation.pre_odr_mail_count == 1,
                                "second_mailer": unpaid_citation.pre_odr_mail_count == 2,
                                "first_mail_date_time_app":first_mail_date_time_app,
                                "initial_time_app": initial_time_app,
                                "second_mail_date_time_app": second_mail_date_time_app,
                                "first_mail_due_date_with_discount" : first_mail_due_date_with_discount,
                                "first_mailer_fine_without_discount" : first_mailer_fine_without_discount,
                                "first_mailer_fine_amount_discount" : first_mailer_fine_with_discount,
                                "transfer_to_odr_amount_due": transfer_to_odr_amount_due, 
                                "formatted_first_mail_due_date" : formatted_first_mail_due_date,
                                "pre_odr_fine_scheduler" : pre_odr_fine_scheduler,
                                "transfer_to_odr_issue_date": transfer_to_odr_issue_date,
                                "mar_secure_pay": mar_secure_pay,
                                "mar_badge" : mar_badge,
                                "formatted_second_mail_due_date" : formatted_second_mail_due_date,
                            }
                    generate_pdf_and_handle_rollback(citationID, stationId, stationName, unpaid_citation, context, xpress_pay)
                

                

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": None
        }).data, status=200)

    except Exception as ex:
        return Response(ServiceResponse({
            "statusCode": 500,
            "message": str(ex),
            "data": None
        }).data, status=200)
    

def get_data_for_pre_odr_table(fromDate, toDate, searchString, pageIndex=1, pageSize=10, stationId=None):
    if isinstance(fromDate, str):
        fromDate = datetime.strptime(fromDate, "%Y-%m-%d")
    if isinstance(toDate, str):
        toDate = datetime.strptime(toDate, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    from_date_str = fromDate if fromDate else None
    to_date_str = toDate if toDate else None
    query = Q()
    
    if fromDate:
            query &= Q(arr_date__gte=from_date_str)
    if toDate:
            query &= Q(arr_date__lte=to_date_str)

    if searchString:
        searchString = searchString.lower().replace(" ", "")
        query &= (
            Q(ticket_number__icontains=searchString) |
            Q(full_name__icontains=searchString)
        )
    
    unpaidCitations = UnpaidCitation.objects.filter(query,pre_odr_mail_count__in=[1,2], station_id=stationId,is_deleted=False)

    citation_ids = [citation.ticket_number for citation in unpaidCitations]
    citations = Citation.objects.filter(citationID__in=citation_ids).select_related('fine', 'person')
    citation_map = {c.citationID: c for c in citations}
    unpaid_citations = {
        preOdrxpressBillPay.ticket_num: preOdrxpressBillPay for preOdrxpressBillPay in PreOdrXpressBillPay.objects.filter(ticket_num=citation_ids)
    }

    constructed_data = []

    for citation in unpaidCitations:
        citation_obj = citation_map.get(citation.ticket_number)
        fine_data = citation_obj.fine
        media_data = {}
        if citation.video_id:
            media_data = {
                'id' : citation.id,
                'citationId': citation_obj.id,
                'citationID': citation.ticket_number,
                'mediaId': f'V-{citation.video_id}',
                'fine': fine_data.fine if fine_data else None,
                'fullName': citation.full_name if citation.full_name else None,
                'capturedDate': citation.off_date.strftime("%B %#d, %Y") if citation.off_date else None,
                'intialDueDate': citation.arr_date.strftime("%B %#d, %Y") if citation.arr_date else None,
                'preODRMailCount': citation.pre_odr_mail_count,
                'firstMailDueDate' : citation.first_mail_due_date if citation.first_mail_due_date else None,
                'secondMailDueDate' : citation.second_mail_due_date if citation.second_mail_due_date else None,
                "firstMailerFine" : citation.first_mail_fine if citation.first_mail_fine else 0,
                "secondMailerFine" : citation.second_mail_fine if citation.second_mail_fine else 0,
                "isFirstMailerPDF" : True if (citation.pre_odr_mail_count == 1 or citation.pre_odr_mail_count == 2) else False,
                "isSecondMailerPDF" : True if citation.pre_odr_mail_count == 2 else False
            }

        elif citation.image_id:
            media_data = {
                'id' : citation.id,
                'citationId': citation_obj.id,
                'citationID': citation.citationID,
                'mediaId': f'I-{citation.image_id}',
                'fine': fine_data.fine if fine_data else None,
                'fullName': citation.full_name if citation.full_name else None,
                'capturedDate': citation.off_date.strftime("%B %#d, %Y") if citation.off_date else None,
                'intialDueDate': citation.arr_date.strftime("%B %#d, %Y") if citation.arr_date else None,
                'preODRMailCount': citation.pre_odr_mail_count,
                'firstMailDueDate' : citation.first_mail_due_date if citation.first_mail_due_date else None,
                'secondMailDueDate' : citation.second_mail_due_date if citation.second_mail_due_date else None,
                "firstMailerFine" : citation.first_mail_fine if citation.first_mail_fine else 0,
                "secondMailerFine" : citation.second_mail_fine if citation.second_mail_fine else 0,
                "isFirstMailerPDF" : True if (citation.pre_odr_mail_count == 1 or citation.pre_odr_mail_count == 2) else False,
                "isSecondMailerPDF" : True if citation.pre_odr_mail_count == 2 else False
            }
        if media_data:
            constructed_data.append(media_data)
            
    constructed_data.sort(key=lambda x: x['citationID'])
    paginator = Paginator(constructed_data, pageSize)
    page = paginator.get_page(pageIndex)

    return {
        "data": list(page.object_list),
        "total_records": paginator.count,
        "has_next_page": page.has_next(),
        "has_previous_page": page.has_previous(),
        "current_page": page.number,
        "total_pages": paginator.num_pages,
    }


def get_pre_odr_data_for_csv(stationId):
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    csv_meta_data = PreOdrCSVMetadata.objects.filter(date__date=date,station_id=stationId)

    quickpd_data = []
    for meta in csv_meta_data:
        quickpd_data.append(meta.xpress_bill_pay)
    serialized_data = [
            {
                "preODRXpressBillPayId": obj.id,
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


def get_first_mailer_pdf(stationId,citationID,agencyId):
    agencyData = Agency.objects.filter(id=agencyId).first()
    citation = Citation.objects.get(citationID=citationID)
    unpaidcitation = UnpaidCitation.objects.get(ticket_number=citationID)
    station = citation.station
    agency_fine_schedular = station.station_agencies.first()
    pre_odr_fine_scheduler = PreOdrFineScheduler.objects.get(agency= agency_fine_schedular)
    first_mail_date_time_app = (
        datetime.strptime(unpaidcitation.first_mail_due_date, "%Y-%m-%d").date() -
        timedelta(days=30)
    )
    second_mail_date_time_app = (
        datetime.strptime(unpaidcitation.first_mail_due_date, "%Y-%m-%d").date() +
        timedelta(days=1)
    )
    
    first_mail_due_dates = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.first_mailer_day_gap) ## here we will assign 60 da
    first_mail_due_date_with_discount = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.second_mailer_day_gap) ## first mailer days gap +
    base_fine = citation.fine.fine
    first_mailer_fine_without_discount = base_fine + (base_fine * 30 / 100)
    first_mailer_fine_with_discount =  base_fine + (base_fine * 20 / 100)
    transfer_to_odr_amount_due = (base_fine * Decimal("1.55")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    transfer_to_odr_issue_date = first_mail_due_dates + timedelta(days=1)
    try:
        metadata = sup_metadata.objects.filter(citation=citation).first()
        initial_time_app = metadata.timeApp.date()
    except sup_metadata.DoesNotExist:
        initial_time_app = ""
    try:
        first_mail_due_date_obj = datetime.strptime(unpaidcitation.first_mail_due_date, "%Y-%m-%d") + timedelta(days=30)
        formatted_first_mail_due_date = first_mail_due_date_obj.strftime("%b. %d, %Y").replace(" 0", " ")
    except ValueError:
        formatted_first_mail_due_date = "Invalid Date"
    filename = f"{citationID}_first-mailer-notice.pdf"
    mar_secure_pay = get_presigned_url(MAR_SECURE_PAY_QR)
    mar_badge = get_presigned_url(MAR_BADGE)
    context = {
        "first_mailer":True,
        "citation": citation,
        "unpaidcitation": unpaidcitation,
        "date": first_mail_date_time_app,
        "agency_phone_number": agencyData.phone,
        "agency_name": agencyData.name,
        "agency_address": agencyData.address,
        "agency_address_2": agencyData.address_2,
        "first_mail_date_time_app":first_mail_date_time_app,
        "initial_time_app": initial_time_app,
        "second_mail_date_time_app": second_mail_date_time_app,
        "first_mail_due_date_with_discount" : first_mail_due_date_with_discount,
        "first_mailer_fine_without_discount" : first_mailer_fine_without_discount,
        "first_mailer_fine_amount_discount" : first_mailer_fine_with_discount,
        "transfer_to_odr_amount_due": transfer_to_odr_amount_due, 
        "formatted_first_mail_due_date" : formatted_first_mail_due_date,
        "pre_odr_fine_scheduler" : pre_odr_fine_scheduler,
        "transfer_to_odr_issue_date": transfer_to_odr_issue_date,
        "mar_secure_pay": mar_secure_pay,
        "mar_badge" : mar_badge,  
    } 
    create_pre_odr_mailer_notice_pdf(filename, context)
    response_data = create_pre_odr_mailer_notice_pdf(filename, context)
    return response_data
    

def get_second_mailer_pdf(stationId,citationID,agencyId):
    agencyData = Agency.objects.filter(id=agencyId).first()
    citation = Citation.objects.get(citationID=citationID)
    unpaid_citation = UnpaidCitation.objects.get(ticket_number=citationID)
    station = citation.station
    agency_fine_schedular = station.station_agencies.first()
    pre_odr_fine_scheduler = PreOdrFineScheduler.objects.get(agency= agency_fine_schedular)
    first_mail_date_time_app = (
                                datetime.strptime(unpaid_citation.first_mail_due_date, "%Y-%m-%d").date() -
                                timedelta(days=30)
                            )
    second_mail_date_time_app = (
        datetime.strptime(unpaid_citation.second_mail_due_date, "%Y-%m-%d").date() -
        timedelta(days=30)
    )
    first_mail_due_dates = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.first_mailer_day_gap) ## here we will assign 60 days

    first_mail_due_date_with_discount = first_mail_date_time_app + timedelta(days=pre_odr_fine_scheduler.second_mailer_day_gap) ## first mailer days gap +30
    
    base_fine = citation.fine.fine
    first_mailer_fine_with_discount = base_fine + (base_fine * 20 / 100)

    first_mailer_fine_without_discount = base_fine + (base_fine * 30 / 100)
    transfer_to_odr_amount_due = (base_fine * Decimal("1.55")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    transfer_to_odr_issue_date = first_mail_due_dates + timedelta(days=1)
    try:
        metadata = sup_metadata.objects.filter(citation=citation).first()
        initial_time_app = metadata.timeApp.date()
    except sup_metadata.DoesNotExist:
        initial_time_app = ""

    try:
        first_mail_due_date_obj = datetime.strptime(unpaid_citation.first_mail_due_date, "%Y-%m-%d") + timedelta(days=30)
        # Format the date to "Jan. 11, 2025"
        formatted_first_mail_due_date = first_mail_due_date_obj.strftime("%b. %d, %Y").replace(" 0", " ")
    except ValueError:
        # Handle case where the date format is invalid or empty
        formatted_first_mail_due_date = "Invalid Date"

    try:
        second_mail_due_date_obj = datetime.strptime(unpaid_citation.second_mail_due_date, "%Y-%m-%d")
        # Format the date to "Jan. 11, 2025"
        formatted_second_mail_due_date = second_mail_due_date_obj.strftime("%b. %d, %Y").replace(" 0", " ")
    except ValueError:
        # Handle case where the date format is invalid or empty
        formatted_second_mail_due_date = "Invalid Date"
    
    # File name for the PDF
    #filename = f"{citation.citationID}_second-mailer-notice.pdf"
    filename = f"{citation.citationID}_first-mailer-notice.pdf" if unpaid_citation.pre_odr_mail_count == 1 else f"{citation.citationID}_second-mailer-notice.pdf"
    mar_secure_pay = get_presigned_url(MAR_SECURE_PAY_QR)
    mar_badge = get_presigned_url(MAR_BADGE)
    context = {
            "citation": citation,
            "unpaidcitation": unpaid_citation,
            "date": second_mail_date_time_app,
            "agency_phone_number": agencyData.phone,
            "agency_name": agencyData.name,
            "agency_address": agencyData.address,
            "agency_address_2": agencyData.address_2,
            "first_mailer": unpaid_citation.pre_odr_mail_count == 1,
            "second_mailer": unpaid_citation.pre_odr_mail_count == 2,
            "first_mail_date_time_app":first_mail_date_time_app,
            "initial_time_app": initial_time_app,
            "second_mail_date_time_app": second_mail_date_time_app,
            "first_mail_due_date_with_discount" : first_mail_due_date_with_discount,
            "first_mailer_fine_without_discount" : first_mailer_fine_without_discount,
            "first_mailer_fine_amount_discount" : first_mailer_fine_with_discount,
            "transfer_to_odr_amount_due": transfer_to_odr_amount_due, 
            "formatted_first_mail_due_date" : formatted_first_mail_due_date,
            "pre_odr_fine_scheduler" : pre_odr_fine_scheduler,
            "transfer_to_odr_issue_date": transfer_to_odr_issue_date,
            "mar_secure_pay": mar_secure_pay,
            "mar_badge" : mar_badge,
            "formatted_second_mail_due_date" : formatted_second_mail_due_date,
        }
    create_pre_odr_mailer_notice_pdf(filename, context)
    response_data = create_pre_odr_mailer_notice_pdf(filename, context)
    return response_data


def create_pre_odr_mailer_notice_pdf(filename, context):
    try:
        html = template_first_mailer.render(context) if "first-mailer" in filename else template_second_mailer.render(context)
        
        directory = os.path.join(BASE_DIR, "media")
        location = os.path.join(directory, filename)

        if not os.path.exists(directory):
            os.makedirs(directory)

        pdfkit.from_string(html, location, configuration=config, options=options)

        with open(location, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
            file_obj = io.BytesIO(pdf_bytes)

            if "first-mailer" in filename:
                upload_to_s3(file_obj, filename, "pre_odr_first_mailer_pdfs")
            elif "second-mailer" in filename:
                upload_to_s3(file_obj, filename, "pre_odr_second_mailer_pdfs")
            else:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid file name"
                }).data, status=200)

        os.remove(location)

        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        response_data = {"base64String" : base64_pdf}
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": GetMailerPDFBase64StringOutputModel(response_data).data
        }).data, status=200)

    except Exception as ex:
        return Response(ServiceResponse({
            "statusCode": 500,
            "message": f"Something went wrong: {str(ex)}"
        }).data, status=200)
        

def delete_unpaid_citation_data(unpaidCitationId):
    try:
        unpaid_citation_data = UnpaidCitation.objects.filter(id=unpaidCitationId).first()
        if not unpaid_citation_data:
            return Response(APIResponse({
                "statusCode" : 204,
                "message" : "Invalid ID"
            }).data,status=200)
        
        remove_pdf(unpaid_citation_data.ticket_number)
        unpaid_citation_data.is_deleted = True
        unpaid_citation_data.save()
        
        return Response(APIResponse({
            "statusCode" : 200,
            "message" : "Data deleted successfully"
        }).data, status=200)
        
    except Exception as ex:
        return Response(ServiceResponse({
            "statusCode": 500,
            "message": f"Something went wrong: {str(ex)}"
        }).data, status=200)


def remove_pdf(citationID):

    first_mailer_pdf_path = rf"C:\Users\EM\Documents\pre_odr_first_mailer_pdfs\MAR\{citationID}_first-mailer-notice.pdf"
    if os.path.exists(first_mailer_pdf_path):
        os.remove(first_mailer_pdf_path)
    second_mailer_pdf_path = rf"C:\Users\EM\Documents\pre_odr_second_mailer_pdfs\MAR\{citationID}_second-mailer-notice.pdf"
    if os.path.exists(second_mailer_pdf_path):
        os.remove(second_mailer_pdf_path)