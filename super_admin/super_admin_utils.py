from django.core.paginator import Paginator
from django.db.models import Q, Value
from django.db.models.functions import Lower, Replace, Trim
from video.models import Agency, State, Station, City, CourtDates, PreOdrFineScheduler
from ees.utils import upload_to_s3
from accounts.models import PermissionLevel, User
from accounts_v2.views import s3_create_folder, add_station_default_fines
import io
import base64
from ees.utils import get_presigned_url


def extracted_fields_for_add_customer(validated_data):
    return {
        "name" : validated_data.get('name'),
        "code" : validated_data.get('code'),
        "cityName" : validated_data.get('cityName'),
        "stateAB" : validated_data.get('stateAB'),
        "location" : validated_data.get('location'),
        "deviceId" : validated_data.get('deviceId'),
        "stateRS" : validated_data.get('stateRS'),
        "apiKey" : validated_data.get('apiKey'),
        "oRI" : validated_data.get('oRI'),
        "address" : validated_data.get('address'),
        "address2" : validated_data.get('address2'),
        "phone" : validated_data.get('phone'),
        "payPortal" : validated_data.get('payPortal'),
        "emails" : validated_data.get('emails'),
        "courtComments" : validated_data.get('courtComments'),
        "badgePicture" : validated_data.get('badgePicture'),
        "userName" : validated_data.get('userName'),
        "email" : validated_data.get('email'),
        "password" : validated_data.get('password'),
        "isXpressPay" : validated_data.get('isXpressPay'),
        "isQuickPd" : validated_data.get('isQuickPd'),
        "trafficLogixClientId" : validated_data.get('trafficLogixClientId'),
        "trafficLogixToken" : validated_data.get('trafficLogixToken'),
        "isPreOdr" : validated_data.get('isPreOdr'),
        "firstMailerFinePercentage": validated_data.get('firstMailerFinePercentage'),
        "secondMailerFinePercentage": validated_data.get('secondMailerFinePercentage'),
        "firstMailDaysGap": validated_data.get('firstMailDaysGap'),
        "secondMailerDaysGap": validated_data.get('secondMailerDaysGap'),
        "isZill": validated_data.get('isZill')
    }
    

def AddCustomerDetails(extracted_input_fields,badge_url,station):

    agency_data = {
        "name": extracted_input_fields.get('name', ''),
        "location": extracted_input_fields.get('location',''),
        "device_id": extracted_input_fields.get('deviceId',''),
        "state_rs": extracted_input_fields.get('stateRS',''),
        "api_key": extracted_input_fields.get('apiKey',''),
        "ORI": extracted_input_fields.get('oRI',''),
        "address": extracted_input_fields.get('address',''),
        "address_2": extracted_input_fields.get('address2',''),
        "phone": extracted_input_fields.get('phone',''),
        "pay_portal": f"https://securepaydirect.com/payments/{extracted_input_fields.get('code')}" 
                      if extracted_input_fields.get('isZill') else extracted_input_fields.get('payPortal', ''),
        "emails": extracted_input_fields.get('emails',''),
        "court_comments": extracted_input_fields.get('courtComments',''),
        "badge_url": badge_url,
        "station": station,
        "isXpressPay": extracted_input_fields.get('isXpressPay', False),
        "isQuickPd": extracted_input_fields.get('isQuickPd', False),
        "traffic_logix_client_id": extracted_input_fields.get('trafficLogixClientId') if extracted_input_fields['trafficLogixClientId'] else None,
        "traffic_logix_token": extracted_input_fields.get('trafficLogixToken') if extracted_input_fields['trafficLogixToken'] else None,
        "isPreOdr": extracted_input_fields.get('isPreOdr'),
        "isZill": extracted_input_fields.get('isZill')
    }
    agency = Agency.objects.create(**agency_data)

    CourtDates.objects.create(station=station, date_string='CUSTOM', phone=extracted_input_fields['phone'], location=extracted_input_fields['name'])
    user = User.objects.create_user(username=extracted_input_fields['userName'],
                                        password=extracted_input_fields['password'],
                                        email=extracted_input_fields['email'],
                                        first_name=extracted_input_fields['name'],
                                        last_name="User",
                                        agency=agency)
    user.save()
    PermissionLevel.objects.create(user=user,
                                isAdjudicator=False,
                                isSupervisor=True,
                                isCourt=False,
                                isAdmin=True,
                                isSuperAdmin=False,
                                isSubmissionView=False,
                                isRejectView=True,
                                isCSVView=True,
                                isAddUserView=True,
                                isAddRoadLocationView=True,
                                isEditFineView=True,
                                isCourtPreview=True,
                                isAddCourtDate=True)
    
    if(extracted_input_fields.get('isPreOdr') == True):
        PreOdrFineScheduler.objects.create(
                        first_mailer_fine_per=extracted_input_fields.get('firstMailerFinePercentage'),
                        second_mailer_fine_per=extracted_input_fields.get('secondMailerFinePercentage'),
                        first_mailer_day_gap=extracted_input_fields.get('firstMailDaysGap'),
                        second_mailer_day_gap=extracted_input_fields.get('secondMailerDaysGap'),
                        agency=agency)

    code = extracted_input_fields['code']
    s3_create_folder(f'videos/{code}/')
    add_station_default_fines(extracted_input_fields['code'], extracted_input_fields['stateRS'])
    

def get_all_agency_data(search_string, page_index=1, page_size=10):
    query = Q()
    if search_string:
        search_string = search_string.lower()
        query &= (
            Q(name__icontains=search_string) |
            Q(location__icontains=search_string) |
            Q(station__name__icontains=search_string)
        )

    agency_data = (
    Agency.objects.annotate(
        trimmed_name=Trim("name"),
        lower_name=Lower("name"),
        no_space_name=Replace("name", Value(" "), Value(""))
    )
    .filter(
        Q(lower_name__icontains=search_string.lower()) |
        Q(trimmed_name__icontains=search_string.strip()) |
        Q(no_space_name__icontains=search_string.replace(" ", ""))
    )
    .order_by("id")
    ).distinct()
    paginator = Paginator(agency_data, page_size)
    page = paginator.get_page(page_index)
    data = [
        {
            "agencyId": agency.id,
            "agencyName": agency.name,
            "location": agency.location,
            "station": agency.station.name if agency.station else "",
            "isActive":agency.is_active
        }
        for agency in sorted(page.object_list, key=lambda a: a.id)
    ]

    return {
        "data": data,
        "total_records": paginator.count,
        "has_next_page": page.has_next(),
        "has_previous_page": page.has_previous(),
        "current_page": page.number,
        "total_pages": paginator.num_pages,
    }


def get_agency_data_by_id(agencyId):
    agency_data = Agency.objects.filter(id=agencyId).first()
    station_data = Station.objects.filter(id=agency_data.station_id).first()
    state_data = State.objects.filter(id=station_data.state_id).first()
    city_data = City.objects.filter(id=station_data.city_id).first()
    pre_odr_fine_scheduler = PreOdrFineScheduler.objects.filter(agency_id=agency_data.id).first()

    response_data ={
        "agencyId":agency_data.id,
        "agencyName":agency_data.name,
        "location":agency_data.location,
        "deviceId":agency_data.device_id,
        "stateRS":agency_data.state_rs,
        "apiKey":agency_data.api_key,
        "oRI":agency_data.ORI,
        "address":agency_data.address,
        "address2":agency_data.address_2,
        "phone":agency_data.phone,
        "payPortal":agency_data.pay_portal,
        "emails":agency_data.emails,
        "courtComments":agency_data.court_comments,
        "isXpressPay":agency_data.isXpressPay,
        "isQuickPd":agency_data.isQuickPd,
        "stateId":state_data.id if state_data else None,
        "stateName":state_data.name if state_data else None,
        "stateAB":state_data.ab if state_data else None,
        "cityId":city_data.id if city_data else None,
        "cityName":city_data.name if city_data else None,
        "stationId":station_data.id,
        "stationName":station_data.name,
        "isActive":agency_data.is_active,
        "badgePicture":get_presigned_url(agency_data.badge_url),
        "trafficLogixClientId":agency_data.traffic_logix_client_id,
        "trafficLogixToken":agency_data.traffic_logix_token,
        "isPreOdr":agency_data.isPreOdr,
        "isZill": agency_data.isZill,
        "firstMailerFinePercentage":pre_odr_fine_scheduler.first_mailer_fine_per if pre_odr_fine_scheduler else 0,
        "secondMailerFinePercentage":pre_odr_fine_scheduler.second_mailer_fine_per if pre_odr_fine_scheduler else 0,
        "firstMailDaysGap":pre_odr_fine_scheduler.first_mailer_day_gap if pre_odr_fine_scheduler else 0,
        "secondMailerDaysGap":pre_odr_fine_scheduler.second_mailer_day_gap if pre_odr_fine_scheduler else 0
    }
    return response_data


def extract_fields_to_update_agency_details(serializer_data):
    return {
        "agencyId":serializer_data.get('agencyId'),
        "agencyName":serializer_data.get('agencyName'),
        "location":serializer_data.get('location'),
        "deviceId":serializer_data.get('deviceId'),
        "stateRS":serializer_data.get('stateRS'),
        "apiKey":serializer_data.get('apiKey'),
        "oRI":serializer_data.get('oRI'),
        "address":serializer_data.get('address'),
        "address2":serializer_data.get('address2'),
        "phone":serializer_data.get('phone'),
        "payPortal":serializer_data.get('payPortal'),
        "emails":serializer_data.get('emails'),
        "courtComments":serializer_data.get('courtComments'),
        "isXpressPay":serializer_data.get('isXpressPay'),
        "isQuickPd":serializer_data.get('isQuickPd'),
        "stateAB":serializer_data.get('stateAB'),
        "cityName":serializer_data.get('cityName'),
        "badgePicture":serializer_data.get('badgePicture'),
        "trafficLogixClientId":serializer_data.get('trafficLogixClientId'),
        "trafficLogixToken":serializer_data.get('trafficLogixToken'),
        "isPreOdr" : serializer_data.get('isPreOdr'),
        "firstMailerFinePercentage" : serializer_data.get('firstMailerFinePercentage'),
        "secondMailerFinePercentage" : serializer_data.get('secondMailerFinePercentage'),
        "firstMailDaysGap" : serializer_data.get('firstMailDaysGap'),
        "secondMailerDaysGap" : serializer_data.get('secondMailerDaysGap'),
        "isZill": serializer_data.get('isZill')
    }


def update_agency_details(extracted_input_fields):
    agency_data = Agency.objects.filter(id=extracted_input_fields['agencyId']).first()
    agency_data.name = extracted_input_fields.get('agencyName', '')
    agency_data.location = extracted_input_fields.get('location', '')
    agency_data.device_id = extracted_input_fields.get('deviceId', '')
    agency_data.state_rs = extracted_input_fields.get('stateRS', '')
    agency_data.api_key = extracted_input_fields.get('apiKey', '')
    agency_data.ORI = extracted_input_fields.get('oRI', '')
    agency_data.address = extracted_input_fields.get('address', '')
    agency_data.address_2 = extracted_input_fields.get('address2', '')
    agency_data.phone = extracted_input_fields.get('phone', '')
    agency_data.pay_portal = extracted_input_fields.get('payPortal', '')
    agency_data.emails = extracted_input_fields.get('emails', '')
    agency_data.court_comments = extracted_input_fields.get('courtComments', '')
    agency_data.isXpressPay = extracted_input_fields.get('isXpressPay', '')
    agency_data.isQuickPd = extracted_input_fields.get('isQuickPd', '')
    agency_data.traffic_logix_client_id = extracted_input_fields.get('trafficLogixClientId', None)
    agency_data.traffic_logix_token = extracted_input_fields.get('trafficLogixToken', None)
    agency_data.isPreOdr = extracted_input_fields.get('isPreOdr')
    agency_data.isZill = extracted_input_fields.get('isZill')

    if extracted_input_fields.get('isPreOdr'):
        pre_odr_fine_scheduler = PreOdrFineScheduler.objects.filter(agency_id=agency_data.id).first()
        if pre_odr_fine_scheduler:
            pre_odr_fine_scheduler.first_mailer_fine_per = extracted_input_fields.get('firstMailerFinePercentage', pre_odr_fine_scheduler.first_mailer_fine_per)
            pre_odr_fine_scheduler.second_mailer_fine_per = extracted_input_fields.get('secondMailerFinePercentage', pre_odr_fine_scheduler.second_mailer_fine_per)
            pre_odr_fine_scheduler.first_mailer_day_gap = extracted_input_fields.get('firstMailDaysGap', pre_odr_fine_scheduler.first_mailer_day_gap)
            pre_odr_fine_scheduler.second_mailer_day_gap = extracted_input_fields.get('secondMailerDaysGap', pre_odr_fine_scheduler.second_mailer_day_gap)
            pre_odr_fine_scheduler.save()
        else:
            PreOdrFineScheduler.objects.create(
                        first_mailer_fine_per=extracted_input_fields.get('firstMailerFinePercentage'),
                        second_mailer_fine_per=extracted_input_fields.get('secondMailerFinePercentage'),
                        first_mailer_day_gap=extracted_input_fields.get('firstMailDaysGap'),
                        second_mailer_day_gap=extracted_input_fields.get('secondMailerDaysGap'),
                        agency_id=extracted_input_fields.get('agencyId'))


    badge_url = None
    badge_picture = extracted_input_fields.get('badgePicture')
    if badge_picture:
        if badge_picture.startswith("https://ee-prod-s3-bucket.s3.amazonaws.com/"):
            badge_url = badge_picture
        else:
            try:
                file_data = base64.b64decode(badge_picture)
                file_obj = io.BytesIO(file_data)
                badge_url = upload_to_s3(file_obj, f"{agency_data.station.name}-badge.png", "images")
            except Exception as e:
                print(f"Error decoding or uploading badge picture: {e}")
                badge_url = None

    agency_data.badge_url = badge_url
    agency_data.save()


def get_all_user_details(agency_id, search_string, page_index=1, page_size=10):
    users = User.objects.filter(agency_id=agency_id)

    if search_string:
        cleaned_search_string = search_string.lower().replace(" ", "")

        users = users.annotate(
            clean_username=Replace(Lower('username'), Value(" "), Value("")),
            clean_first_name=Replace(Lower('first_name'), Value(" "), Value("")),
            clean_last_name=Replace(Lower('last_name'), Value(" "), Value("")),
            clean_email=Replace(Lower('email'), Value(" "), Value("")),
            clean_agency_name=Replace(Lower('agency__name'), Value(" "), Value("")),
        )
        query = (
            Q(clean_username__icontains=cleaned_search_string) |
            Q(clean_first_name__icontains=cleaned_search_string) |
            Q(clean_last_name__icontains=cleaned_search_string) |
            Q(clean_email__icontains=cleaned_search_string) |
            Q(clean_agency_name__icontains=cleaned_search_string)
        )
        users = users.filter(query).distinct()
    paginator = Paginator(users, page_size)
    page = paginator.get_page(page_index)
    user_data = list(
        map(
            lambda user: {
                "userId": user.id,
                "userName": user.username,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": user.email,
                "agencyId":user.agency_id,
                "agencyName": user.agency.name if user.agency else "",
            },
            page.object_list
        )
    )
    return {
        "data": user_data,
        "total_records": paginator.count,
        "has_next_page": page.has_next(),
        "has_previous_page": page.has_previous(),
        "current_page": page.number,
        "total_pages": paginator.num_pages,
    }


def get_user_details_by_id(user_id,agency_id):
    user_data = User.objects.filter(id=user_id,agency_id=agency_id).first()
    permission_level_data = PermissionLevel.objects.filter(user_id=user_id).first()

    response_data ={
        "userId":user_data.id,
        "userName":user_data.username,
        "password":user_data.password,
        "email":user_data.email,
        "firstName":user_data.first_name,
        "lastName":user_data.last_name,
        "agencyName":user_data.agency.name,
        "isSubmissionView":permission_level_data.isSubmissionView,
        "isAdjudicator":permission_level_data.isAdjudicator,
        "isCourt":permission_level_data.isCourt,
        "isAdmin":permission_level_data.isAdmin,
        "isSuperAdmin":permission_level_data.isSuperAdmin,
        "isApprovedTableView":permission_level_data.isApprovedTableView,
        "isRejectView":permission_level_data.isRejectView,
        "isCSVView":permission_level_data.isCSVView,
        "isAddUserView":permission_level_data.isAddUserView,
        "isAddRoadLocationView":permission_level_data.isAddRoadLocationView,
        "isEditFineView":permission_level_data.isEditFineView,
        "isCourtPreview":permission_level_data.isCourtPreview,
        "isAddCourtDate":permission_level_data.isAddCourtDate,
        "isActive":user_data.is_active,
        "isSupervisor":permission_level_data.isSupervisor,
        "isAgencyAdjudicationBinView":permission_level_data.isAgencyAdjudicationBinView,
        "isReviewBinView":permission_level_data.isReviewBinView,
        "isPreODRView":permission_level_data.isPreODRView,
        "isODRView":permission_level_data.isODRView,
        "isViewReportView":permission_level_data.isViewReportView
    }
    return response_data


def extract_fields_to_update_user_details(serializer_data):
    return {
        "userId":serializer_data.get('userId'),
        "agencyId":serializer_data.get('agencyId'),
        "userName":serializer_data.get('userName'),
        "password":serializer_data.get('password'),
        "email":serializer_data.get('email'),
        "firstName":serializer_data.get('firstName'),
        "lastName":serializer_data.get('lastName'),
        "isActive":serializer_data.get('isActive'),
        "isSubmissionView":serializer_data.get('isSubmissionView'),
        "isAdjudicator":serializer_data.get('isAdjudicator'),
        "isCourt":serializer_data.get('isCourt'),
        "isAdmin":serializer_data.get('isAdmin'),
        "isSuperAdmin":serializer_data.get('isSuperAdmin'),
        "isApprovedTableView":serializer_data.get('isApprovedTableView'),
        "isRejectView":serializer_data.get('isRejectView'),
        "isCSVView":serializer_data.get('isCSVView'),
        "isAddUserView":serializer_data.get('isAddUserView'),
        "isAddRoadLocationView":serializer_data.get('isAddRoadLocationView'),
        "isEditFineView":serializer_data.get('isEditFineView'),
        "isCourtPreview":serializer_data.get('isCourtPreview'),
        "isAddCourtDate":serializer_data.get('isAddCourtDate'),
        "isAddUserView":serializer_data.get('isAddUserView'),
        "isSupervisor":serializer_data.get('isSupervisor'),
        "isAgencyAdjudicationBinView" : serializer_data.get('isAgencyAdjudicationBinView'),
        "isReviewBinView" : serializer_data.get('isReviewBinView'),
        "isPreOdrView" : serializer_data.get('isPreOdrView'),
        "isODRView" : serializer_data.get('isODRView'),
        "isViewReportView" : serializer_data.get('isViewReportView')
    }


def update_user_details(extracted_fields):
    user_data = User.objects.filter(id=extracted_fields['userId'], agency_id=extracted_fields['agencyId']).first()
    user_permission = PermissionLevel.objects.filter(user_id=extracted_fields['userId']).first()
    if not user_data:
        raise ValueError(f"User with ID {extracted_fields['userId']} and Agency ID {extracted_fields['agencyId']} does not exist.")
    if not user_permission:
        raise ValueError(f"PermissionLevel for User ID {extracted_fields['userId']} does not exist.")

    user_data.username = extracted_fields.get('userName', user_data.username)
    user_data.email = extracted_fields.get('email', user_data.email)
    user_data.first_name = extracted_fields.get('firstName', user_data.first_name)
    user_data.last_name = extracted_fields.get('lastName', user_data.last_name)
    user_data.is_active = extracted_fields.get('isActive', user_data.is_active)

    if extracted_fields.get('password'):
        user_data.set_password(extracted_fields['password'])

    user_permission.isSubmissionView = extracted_fields.get('isSubmissionView', user_permission.isSubmissionView)
    user_permission.isAdjudicator = extracted_fields.get('isAdjudicator', user_permission.isAdjudicator)
    user_permission.isCourt = extracted_fields.get('isCourt', user_permission.isCourt)
    user_permission.isAdmin = extracted_fields.get('isAdmin', user_permission.isAdmin)
    user_permission.isSuperAdmin = extracted_fields.get('isSuperAdmin', user_permission.isSuperAdmin)
    user_permission.isApprovedTableView = extracted_fields.get('isApprovedTableView', user_permission.isApprovedTableView)
    user_permission.isRejectView = extracted_fields.get('isRejectView', user_permission.isRejectView)
    user_permission.isCSVView = extracted_fields.get('isCSVView', user_permission.isCSVView)
    user_permission.isAddUserView = extracted_fields.get('isAddUserView', user_permission.isAddUserView)
    user_permission.isAddRoadLocationView = extracted_fields.get('isAddRoadLocationView', user_permission.isAddRoadLocationView)
    user_permission.isEditFineView = extracted_fields.get('isEditFineView', user_permission.isEditFineView)
    user_permission.isCourtPreview = extracted_fields.get('isCourtPreview', user_permission.isCourtPreview)
    user_permission.isAddCourtDate = extracted_fields.get('isAddCourtDate', user_permission.isAddCourtDate)
    user_permission.isSupervisor = extracted_fields.get('isSupervisor', user_permission.isSupervisor)
    user_permission.isAgencyAdjudicationBinView = extracted_fields.get('isAgencyAdjudicationBinView', user_permission.isAgencyAdjudicationBinView)
    user_permission.isReviewBinView = extracted_fields.get('isReviewBinView', user_permission.isReviewBinView)
    user_permission.isPreODRView = extracted_fields.get('isPreODRView', user_permission.isPreODRView)
    user_permission.isODRView = extracted_fields.get('isODRView', user_permission.isODRView)
    user_permission.isViewReportView = extracted_fields.get('isViewReportView', user_permission.isViewReportView)
    user_data.save()
    user_permission.save()