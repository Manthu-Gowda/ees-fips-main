from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import get_presigned_url, user_information
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from accounts.models import Station
from datetime import datetime
import csv
from rest_framework.views import APIView
import csv
import io
import base64
from django.db import transaction
from .submission_view_utils import create_submission,process_media_rejection, \
      process_tattile_media_rejection, classify_vehicle_owner
from reviewbin_view.reviewbin_utils import ReviewBinUtils
from django.db.models import Q
from video.datamax import getTextContent, parse_query 
from openai import RateLimitError

class GetSubmissionCountView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=SubmitSubmissionViewDataInputModel,
        responses={200: GetSubmissionViewDataModel,
                   204: "No content"},
        tags=['SubmissionView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = SubmitSubmissionViewDataInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)

        date = serializer.validated_data.get('date', None)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_name = readToken.get('stationName', None)
        stationName = Station.objects.filter(name=station_name).values_list('name', flat=True).first()
        duncanData = DuncanSubmission.objects.filter(station=stationName)

        if date:
            try:
                normalized_date = date.replace(',', ', ')
                parsed_date = datetime.strptime(normalized_date, "%B %d, %Y")
                filtered_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                return Response({
                    "statusCode": 400,
                    "message": "Invalid date format. Expected 'Month Day, Year'."
                }, status=400)

            totalSubmission = duncanData.filter(
                isSubmitted=True, submitted_date__date=filtered_date).count()
            totalRejection = duncanData.filter(
                isRejected=True, submitted_date__date=filtered_date).count()
            totalSkipped = duncanData.filter(
                isSkipped=True, submitted_date__date=filtered_date).count()
            totalReviewBin = duncanData.filter(
                is_notfound=True, submitted_date__date=filtered_date).count()
            totalUnknown = duncanData.filter(
                is_unknown=True, submitted_date__date=filtered_date).count()
            totalSentToAdjucation = duncanData.filter(
                is_sent_to_adjudication=True, submitted_date__date=filtered_date).count()
            

        else:
            totalSubmission = duncanData.filter(isSubmitted=True).count()
            totalRejection = duncanData.filter(isRejected=True).count()
            totalSkipped = duncanData.filter(isSkipped=True).count()
            totalReviewBin = duncanData.filter(is_notfound=True).count()
            totalUnknown = duncanData.filter(is_unknown=True).count()
            totalSentToAdjucation = duncanData.filter(is_sent_to_adjudication=True).count()

        video_response_data = {
            "totalSubmission": totalSubmission,
            "totalRejection": totalRejection,
            "totalSkipped": totalSkipped,
            "totalReviewBin": totalReviewBin,
            "totalUnknown": totalUnknown,
            "totalSentToAdjucation": totalSentToAdjucation
        }
        response_data = GetSubmissionViewDataModel(video_response_data)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)
      

class DownloadTSVFileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=SubmitSubmissionViewDataInputModel,
        responses={200 : DownloadTsvFileReturnModel},
        tags=['SubmissionView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = SubmitSubmissionViewDataInputModel(data=request.data)

        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400, "message": "Invalid input data", "data": serializer.errors}).data, status=400)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        date = serializer.validated_data.get('date', None)
        stationId = readToken.get('stationId')
         
        stationName = Station.objects.filter(id=stationId).values_list('name', flat=True).first()

        if date:
            try:
                normalized_date = date.replace(',', ', ')
                parsed_date = datetime.strptime(normalized_date, "%B %d, %Y")
                filtered_date = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                return Response(ServiceResponse({"statusCode": 400, "message": "Invalid date format. Expected 'Month Day, Year'.", "data" : None}).data, status=400)
            duncan_data = DuncanSubmission.objects.filter(station=stationName, isSubmitted=True, submitted_date__date=filtered_date,isSent = False)
        else:
            duncan_data = DuncanSubmission.objects.filter(station=stationName, isSubmitted=True)

        output = io.StringIO()
        writer = csv.writer(output, delimiter='\t', lineterminator='\n')

        station_replacements = {
            'MOR-C': 'MORR',
            'FED-M': 'FEDB',
            'OIL': 'OILC',
            'OBR': 'OBER',
            'ELZ': 'ELIZ',
            'HUD-C': 'HUDS',
            'WALS': 'WALS',
            'KRSY-C': 'KERS',
            'FPLY-C': 'FPLY',
            'WBR2': 'WBRC',
        }
        stationName = station_replacements.get(stationName, stationName)

        for row in duncan_data:
            date = row.submitted_date
            formatted_date = date.strftime('%m/%d/%Y')
            required_date = formatted_date.replace('/', '')[:4]

            if row.image and not row.video:
                plate_image_filename = row.image.plate_image_filename
                file_name = required_date + '_' + plate_image_filename.split('_', 1)[1][:-4]
            elif row.video and not row.image:
                plate_image_filename = row.video.VIDEO_NO
                file_name = required_date + '_' + plate_image_filename
            else:
                file_name = None

            writer.writerow([row.veh_state, row.lic_plate, '', '', '', '', formatted_date,
                            '', '', '', '', '', '', '', '', stationName, file_name])

            row.isSent = True
            row.save()

        output.seek(0)
        tsv_content = output.getvalue()
        base64_encoded_tsv = base64.b64encode(tsv_content.encode()).decode()
        response_body = {
            "base64String" : base64_encoded_tsv
        }
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": DownloadTsvFileReturnModel(response_body).data
        }).data, status=200)
   

class FetchDuncanMasterRecordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetDuncanMasterDataModel,
        responses={
            200: DuncanMasterDataOutputModel,
            204: "No content"
        },
        tags=['SubmissionView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetDuncanMasterDataModel(data=request.data)
        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        station_modified_name = readToken.get('stationModifiedName')
        station_name = readToken.get('stationName')
        station_id = readToken.get('stationId')
        state_id = readToken.get('stateId')
        agency_id = readToken.get('agencyId')
        data = serializer.validated_data
        license_plate = data.get('licensePlate')
        state_abbrevation = data.get('stateAB')
        view_type = data.get('viewType')
        default_state_ab = None
        if not state_abbrevation:
            state_ab_by_state_id = State.objects.filter(id=state_id).first()
            default_state_ab = state_ab_by_state_id.ab
            duncan_master_data = DuncanMasterData.objects.filter(lic_plate=license_plate,
                                                                state=default_state_ab).last()
        else:
            duncan_master_data = DuncanMasterData.objects.filter(lic_plate=license_plate,
                                                                state=state_abbrevation).last()
            
        isDataMaxApi = Agency.objects.filter(
                                            Q(id=agency_id) &
                                            ~Q(api_key__iexact='n/a') &
                                            ~Q(api_key__iexact='null') &
                                            ~Q(api_key='') &
                                            ~Q(api_key__isnull=True)
                                        ).values('api_key').first()
        
        if view_type == 1:
            duncan_submission_data = DuncanSubmission.objects.filter(lic_plate=license_plate,veh_state=state_abbrevation).last()
            if duncan_master_data:
                submission_view_dict = {
                    "fullName": duncan_master_data.full_name.strip() if duncan_master_data.full_name else None,
                    "address": duncan_master_data.address.strip() if duncan_master_data.address else None,
                    "city": duncan_master_data.city.strip() if duncan_master_data.city else None,
                    "stateName": State.objects.filter(ab=duncan_master_data.state).values_list('name',flat=True).first(),
                    "stateAB": duncan_master_data.state if duncan_master_data.state else None,
                    "zip": duncan_master_data.zip if duncan_master_data.zip else None,
                    "model": duncan_master_data.vehicle_modle.strip() if duncan_master_data.vehicle_modle else None, 
                    "make": duncan_master_data.vehicle_make.strip() if duncan_master_data.vehicle_make else None,
                    "color": duncan_master_data.color.strip() if duncan_master_data.color else None,
                    "vehicleYear": duncan_master_data.vehicle_year if duncan_master_data.vehicle_year else None,
                    "vinNumber" : duncan_master_data.vin_number if duncan_master_data.vin_number else None,
                    "firstName" : duncan_master_data.first_name.strip() if duncan_master_data.first_name else None,
                    "middleName" : duncan_master_data.middle_name.strip() if duncan_master_data.middle_name else None,
                    "lastName" : duncan_master_data.last_name.strip() if duncan_master_data.last_name else None,
                    "phoneNumber" : None,
                    "vehicleModel2" : duncan_master_data.vehicle_model_2.strip() if duncan_master_data.vehicle_model_2 else None,
                    "personStateAB":duncan_master_data.person_state,
                    "personStateName": State.objects.filter(ab=duncan_master_data.person_state).values_list('name', flat=True).first()
                }

                if duncan_master_data.is_invalid_address and duncan_master_data.is_address_updated == False:
                    return Response(ServiceResponse(
                        {"statusCode": 200, 
                         "message": "RETURN TO SENDER ADDRESS.",
                         "data": DuncanMasterDataOutputModel(submission_view_dict).data
                        }).data, status=200)
                if  duncan_master_data.is_address_updated == True:
                    return Response(ServiceResponse(
                        {"statusCode": 200, 
                         "message": "RETURN TO SENDER, PENDING.",
                         "data": DuncanMasterDataOutputModel(submission_view_dict).data
                        }).data, status=200)
                
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This is a Positive hit in the Master database. Below are the details",
                    "data": DuncanMasterDataOutputModel(submission_view_dict).data
                }).data, status=200)
            
            if duncan_submission_data:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "Positive hit. This tag has been previously submitted. Please skip.",
                    "data": None
                }).data, status=200)
            
            if not duncan_master_data and view_type == 1:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No data found, Please submit",
                    "data": None
                }).data, status=200)
        
        elif view_type == 2:
            if isDataMaxApi and isDataMaxApi.get("api_key"):
                state_ab = state_abbrevation or default_state_ab
                dataMaxData = getTextContent(license_plate, state_ab, station_name)

                if dataMaxData:
                    dataMaxResponseData = parse_query(dataMaxData, state_ab)

                    if not dataMaxResponseData:
                        return Response(ServiceResponse({
                            "statusCode": 204,
                            "message": "Please re-run this query, the state switch did not return properly.",
                            "data": None
                        }).data, status=200)

                    state_name = State.objects.filter(ab=dataMaxResponseData.get("STATE")).values_list('name', flat=True).first()
                    owner_parts = dataMaxResponseData.get("OWNER", "").strip().split()
                    owner_parts = [p for p in owner_parts if p]

                    first_name = owner_parts.pop(0) if owner_parts else ''
                    last_name = owner_parts.pop(-1) if owner_parts else ''
                    middle_name = " ".join(owner_parts).strip()

                    submission_view_dict = {
                        "fullName": f"{first_name} {middle_name} {last_name}".strip(),
                        "address": dataMaxResponseData.get("STREET", "").strip(),
                        "city": dataMaxResponseData.get("CITY", "").strip(),
                        "stateName": state_name,
                        "stateAB": dataMaxResponseData.get("STATE"),
                        "zip": dataMaxResponseData.get("ZIP"),
                        "model": dataMaxResponseData.get("VMO"),
                        "make": dataMaxResponseData.get("VMA"),
                        "color": dataMaxResponseData.get("VCO"),
                        "vehicleYear": dataMaxResponseData.get("VYR"),
                        "vinNumber": dataMaxResponseData.get("VIN"),
                        "firstName": first_name,
                        "middleName": middle_name,
                        "lastName": last_name,
                        "phoneNumber": None,
                        "vehicleModel2": None,
                        "personStateAB": dataMaxResponseData.get("STATE"),
                        "personStateName": state_name,
                    }
                    dmv.objects.create(
                        station_id=station_id,
                        state_ab_id=State.objects.filter(id=state_id).values_list('id', flat=True).first(),
                        plate=license_plate,
                        raw=dataMaxData
                    )
                    
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "This is a Positive hit in the Master database. Below are the details",
                        "data": DuncanMasterDataOutputModel(submission_view_dict).data
                    }).data, status=200)

            if duncan_master_data:
                submission_view_dict = {
                    "fullName": duncan_master_data.full_name.strip() if duncan_master_data.full_name else None,
                    "address": duncan_master_data.address.strip() if duncan_master_data.address else None,
                    "city": duncan_master_data.city.strip() if duncan_master_data.city else None,
                    "stateName": State.objects.filter(ab=duncan_master_data.state).values_list('name', flat=True).first(),
                    "stateAB": duncan_master_data.state,
                    "zip": duncan_master_data.zip,
                    "model": duncan_master_data.vehicle_modle.strip() if duncan_master_data.vehicle_modle else None,
                    "make": duncan_master_data.vehicle_make.strip() if duncan_master_data.vehicle_make else None,
                    "color": duncan_master_data.color.strip() if duncan_master_data.color else None,
                    "vehicleYear": duncan_master_data.vehicle_year,
                    "vinNumber": duncan_master_data.vin_number,
                    "firstName": duncan_master_data.first_name.strip() if duncan_master_data.first_name else None,
                    "middleName": duncan_master_data.middle_name.strip() if duncan_master_data.middle_name else None,
                    "lastName": duncan_master_data.last_name.strip() if duncan_master_data.last_name else None,
                    "phoneNumber": None,
                    "vehicleModel2": duncan_master_data.vehicle_model_2.strip() if duncan_master_data.vehicle_model_2 else None,
                    "personStateAB": duncan_master_data.person_state,
                    "personStateName": State.objects.filter(ab=duncan_master_data.person_state).values_list('name', flat=True).first()
                }

                if duncan_master_data.is_invalid_address and duncan_master_data.is_address_updated == False:
                    return Response(ServiceResponse(
                        {"statusCode": 200, 
                         "message": "RETURN TO SENDER ADDRESS.",
                         "data": DuncanMasterDataOutputModel(submission_view_dict).data
                        }).data, status=200)
                
                if  duncan_master_data.is_address_updated == True:
                    return Response(ServiceResponse(
                        {"statusCode": 200, 
                         "message": "RETURN TO SENDER, PENDING.",
                         "data": DuncanMasterDataOutputModel(submission_view_dict).data
                        }).data, status=200)
                
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This is a Positive hit in the Master database. Below are the details",
                    "data": DuncanMasterDataOutputModel(submission_view_dict).data
                }).data, status=200)

        return Response(ServiceResponse({
            "statusCode": 204,
            "message": "Please re-run this query, the state switch did not return properly.",
            "data": None
        }).data, status=200)


class GetMediaDataView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMediaDataInputModel,
        responses={
            200: GetVideoDataByIdModel,
            200: GetImageDataByIdModel,
            204: "No content"
        },
        tags=['SubmissionView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetMediaDataInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }).data, status=200)
        
        media_id = serializer.validated_data.get('mediaId')
        media_type = serializer.validated_data.get('mediaType')

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get('stationId')
        agency_id = readToken.get('agencyId')
        state_name = readToken.get('stateName')
        state_id = readToken.get('stateId')
        state_ab = State.objects.filter(id=state_id).values_list('ab', flat=True).first()
        get_agency_state_rs = Agency.objects.filter(id=agency_id).values_list('state_rs', flat=True).first()
        
        def get_location(location_id):
            location = road_location.objects.filter(id=location_id).first()
            return {
                "locationName": location.location_name if location else None,
                "locationCode": location.LOCATION_CODE if location else None,
                "postedSpeed": location.posted_speed if location else None,
                "isSchoolZone": location.isSchoolZone if location else None
            }
        
        def get_image_location(image_location_id):
            image_location = road_location.objects.filter(trafficlogix_location_id=image_location_id).first()
            return {
                "locationName" : image_location.location_name if image_location else None,
                "locationCode": image_location.LOCATION_CODE if image_location else None,
                "postedSpeed": image_location.posted_speed if image_location else None,
                "isSchoolZone": image_location.isSchoolZone if image_location else None
            }

        def calculate_fine(station_id, is_school_zone, diff):
            fine_filter = Fine.objects.filter(station_id=station_id, isSchoolZone=is_school_zone)
            if station_id != 44:
                if diff <= 10:
                    fine = fine_filter.filter(speed_diff=10).first()
                elif diff <= 15 if is_school_zone else 20:
                    fine = fine_filter.filter(speed_diff=15 if is_school_zone else 20).first()
                elif diff <= 20 if is_school_zone else 30:
                    fine = fine_filter.filter(speed_diff=20 if is_school_zone else 30).first()
                else:
                    fine = fine_filter.filter(speed_diff__gte=21 if is_school_zone else 31).first()
            else:
                if diff <= 10:
                    fine = fine_filter.filter(speed_diff=10).first()
                elif (diff <= 15 and is_school_zone) or (diff <= 24 and not is_school_zone):
                    fine = fine_filter.filter(speed_diff=15 if is_school_zone else 20).first()
                else:
                    fine = fine_filter.filter(speed_diff__gte=25 if is_school_zone else 25).first()
            return (fine.fine if fine else None, fine.id if fine else None)

        data = None

        if media_type == 1:
            videoData = Video.objects.filter(
                id=media_id,
                station_id=station_id,
                isRejected=False,
                isRemoved=False,
            ).first()
            if videoData:
                preSignedUrl = get_presigned_url(videoData.url)
                location_info = get_location(videoData.location_id)
                diff = int(videoData.speed) - int(videoData.posted_speed)
                fine_amount, fine_id = calculate_fine(station_id, location_info["isSchoolZone"], diff)
                is_submitted_lic_plate = DuncanSubmission.objects.filter(
                    video_id=videoData.id,
                    isSubmitted=True,
                    isRejected=False,
                    isSkipped=False
                ).values_list("lic_plate", flat=True).first()
                data = {
                    "id": videoData.id,
                    "caption": videoData.caption,
                    "url": preSignedUrl,
                    "speed": videoData.speed,
                    "datetime": videoData.datetime,
                    "stationId": videoData.station_id,
                    "locationId": videoData.location_id,
                    "locationName": location_info["locationName"],
                    "locationCode": location_info["locationCode"],
                    "postedSpeed": location_info["postedSpeed"],
                    "isSchoolZone": location_info["isSchoolZone"],
                    "stateRS": get_agency_state_rs,
                    "stateId": state_id,
                    "stateName": state_name,
                    "stateAB": state_ab,
                    "fineId" : fine_id,
                    "fineAmount": fine_amount,
                    "distance" : videoData.distance,
                    "licensePlate" : is_submitted_lic_plate
                }
                serializer = GetVideoDataByIdModel(data)
        
        elif media_type == 2:
            imageData = Image.objects.filter(
                id=media_id,
                station_id=station_id,
                isRejected=False,
                isRemoved=False
            ).first()
            if imageData:
                image_urls = []
                image_ticket_id = imageData.ticket_id
                image_hash_urls = ImageHash.objects.filter(ticket_id=image_ticket_id).values_list('image_url', flat=True)
                image_data_urls = ImageData.objects.filter(ticket_id=image_ticket_id).values_list('image_url', flat=True)
                
                for image_url in list(image_hash_urls) + list(image_data_urls):
                    image_urls.append(get_presigned_url(image_url))
                
                location_info = get_image_location(imageData.location_id)
                diff = int(imageData.violating_speed) - int(imageData.current_speed_limit)
                fine_amount, fine_id = calculate_fine(station_id, location_info["isSchoolZone"], diff)
                is_submitted_lic_plate = DuncanSubmission.objects.filter(
                    image_id=imageData.id,
                    isSubmitted=True,
                    isRejected=False,
                    isSkipped=False
                ).values_list("lic_plate", flat=True).first()

                data = {
                    "id": imageData.id,
                    "ticketId": imageData.ticket_id,
                    "time": imageData.time,
                    "data": imageData.data,
                    "speed": imageData.current_speed_limit,
                    "violatingSpeed": imageData.violating_speed,
                    "plateText": imageData.plate_text,
                    "citationId": imageData.citation_id,
                    "licenseImageUrl": get_presigned_url(imageData.lic_image_url),
                    "speedImageUrl": get_presigned_url(imageData.speed_image_url),
                    "stationId": imageData.station_id,
                    "locationId": imageData.location_id,
                    "locationName": location_info["locationName"],
                    "locationCode": location_info["locationCode"],
                    "postedSpeed": location_info["postedSpeed"],
                    "isSchoolZone": location_info["isSchoolZone"],
                    "stateRS": get_agency_state_rs,
                    "stateId": state_id,
                    "stateName": state_name,
                    "stateAB": state_ab,
                    "imageUrls": image_urls,
                    "fineId" : fine_id,
                    "fineAmount": fine_amount,
                    "distance" : imageData.img_distance,
                    "licensePlate" : is_submitted_lic_plate
                }
                serializer = GetImageDataByIdModel(data)

        elif media_type == 3:
            media_urls = []
            tattile_data = Tattile.objects.filter(id=media_id).first()
            duncan_check = DuncanSubmission.objects.filter(tattile = tattile_data.id, isSubmitted = True)
            if duncan_check.exists():
                plate= duncan_check.first().lic_plate
            else:
                plate = ""
            if tattile_data:
                tattile_media_data = TattileFile.objects.filter(ticket_id=tattile_data.ticket_id,file_type__in=[2]).values_list("file_url", flat=True)
                for url in tattile_media_data:
                    media_urls.append(get_presigned_url(url))

                    diff = int(tattile_data.measured_speed) - int(tattile_data.speed_limit)
                    location_info = road_location.objects.filter(station_id=station_id).first()
                    fine_amount, fine_id = calculate_fine(station_id, location_info.isSchoolZone, diff)
                    data = {
                        "id": tattile_data.id,
                        "ticketId": 0,
                        "time": tattile_data.image_time,
                        "data": None,
                        "speed": tattile_data.speed_limit,
                        "violatingSpeed": tattile_data.measured_speed,
                        "plateText": plate,
                        "citationId": tattile_data.citation_id if tattile_data.citation_id else None,
                        "licenseImageUrl": get_presigned_url(tattile_data.license_image_url),
                        "speedImageUrl": get_presigned_url(tattile_data.speed_image_url),
                        "stationId": 53,
                        "locationId": tattile_data.location_id,
                        "locationName": tattile_data.location_name,
                        "locationCode": 2,
                        "postedSpeed": 45,
                        "isSchoolZone": False,
                        "stateRS": get_agency_state_rs,
                        "stateId": state_id,
                        "stateName": state_name,
                        "stateAB": state_ab,
                        "imageUrls": media_urls,
                        "fineId" : fine_id,
                        "fineAmount": fine_amount,
                        "distance" : tattile_data.image_distance,
                        "licensePlate" : plate
                    }
                    serializer = GetImageDataByIdModel(data)
            
        if not data:
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No content",
                "data": None
            }).data, status=200)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": serializer.data
        }).data, status=200)


class UploadCSVView(APIView):
    permission_classes = [IsAuthenticated]
    EXPECTED_COLUMNS = [
        'uploaded_date', 'state', 'lic_plate', 'station', 'full_name', 'address',
        'city', 'state_code', 'zipcode', 'year', 'make', 'model', 'model-2',
        'color', 'vin', 'duncan_status', 'Source'
    ]

    @swagger_auto_schema(
        request_body=UploadCSVFileModel,
        responses={200: UploadCSVFileResponseModel},
        tags=['SubmissionView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = UploadCSVFileModel(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }).data, status=400)

        csv_data_base64 = serializer.validated_data.get('base64String')
        try:
            csv_data = base64.b64decode(csv_data_base64).decode('utf-8')
        except (base64.binascii.Error, UnicodeDecodeError):
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid base64 string",
                "data": None
            }).data, status=400)

        csv_file = io.StringIO(csv_data)
        csv_reader = csv.reader(csv_file)

        errors = []
        record_count = 0
        duplicate_plates = []

        for idx, row in enumerate(csv_reader):
            if idx == 0 or row[0].strip().lower() == 'uploaded_date':
                continue

            if len(row) < len(self.EXPECTED_COLUMNS):
                missing_columns = [
                    self.EXPECTED_COLUMNS[j] for j in range(len(row), len(self.EXPECTED_COLUMNS))
                ]
                errors.append(f"Row {idx + 1} is missing columns: {', '.join(missing_columns)}")
                continue

            uploaded_date_str = row[0].strip()
            try:
                try:
                    submission_datetime = datetime.strptime(uploaded_date_str, "%m/%d/%Y")
                except ValueError:
                    submission_datetime = datetime.strptime(uploaded_date_str, "%d-%m-%Y")
                uploaded_date = submission_datetime.strftime("%Y-%m-%d")
            except ValueError as e:
                errors.append(f"Row {idx + 1} has an invalid submission date: {e}")
                continue

            lic_plate = row[2].strip().upper().replace(' ', '')
            state = row[1].strip()
            if not lic_plate:
                errors.append(f"Row {idx + 1} has an empty lic_plate.")
                continue

            with transaction.atomic():
                if DuncanMasterData.objects.filter(lic_plate=lic_plate, state=state).exists():
                    duplicate_plates.append(lic_plate)
                    errors.append(f"Row {idx + 1} has a duplicate lic_plate: {row[2].strip()}")
                    continue

                name_parts = row[4].split(',')
                first_name_d = name_parts[1].strip() if len(name_parts) > 1 else name_parts[0].strip()
                last_name_d = name_parts[0].strip() if len(name_parts) > 1 else ''

                # Create MasterData entry first
                DuncanMasterData.objects.create(
                    uploaded_date=uploaded_date,
                    state=state,
                    lic_plate=lic_plate,
                    station=row[3].strip(),
                    full_name=row[4].strip() if row[4].strip() else None,
                    address=row[5].strip() if row[5].strip() else None,
                    city=row[6].strip() if row[6].strip() else None,
                    person_state=row[7].strip() if row[7].strip() else None,
                    zip=row[8].strip() if row[8].strip() else None,
                    vehicle_year=row[9].strip() if row[9].strip() else None,
                    vehicle_make=row[10].strip() if row[10].strip() else None,
                    vehicle_modle=row[11].strip() if row[11].strip() else None,
                    vehicle_model_2=row[12].strip() if row[12].strip() else None,
                    vin_number=row[14].strip() if row[14].strip() else None,
                    dunccan_data_status=row[15].strip() if row[15].strip() else None,
                    color=row[13].strip() if row[13].strip() else None,
                    last_name=last_name_d if last_name_d else None,
                    first_name=first_name_d if first_name_d else None
                )

                record_count += 1

                # Now fetch the latest master record
                try:
                    duncan_master = DuncanMasterData.objects.filter(
                        lic_plate=lic_plate, state=state
                    ).latest("created_at")
                except DuncanMasterData.DoesNotExist:
                    duncan_master = None

                submission_qs = DuncanSubmission.objects.filter(
                    (Q(isSubmitted=True) | Q(isSkipped=True)),
                    lic_plate=lic_plate,
                    veh_state=state,
                )
                for submission in submission_qs:
                    print(f"Processing submission ID: {submission.id}, lic_plate: {submission.lic_plate}, isSubmitted: {submission.isSubmitted}")
                    print(123)
                    if duncan_master and (submission.isSubmitted or submission.isSkipped):
                        print(456)
                        full_name_cleaned = (duncan_master.full_name or "").strip().upper()
                        print(f"Full name from master data: '{duncan_master.full_name}' -> Cleaned: '{full_name_cleaned}'")

                        if full_name_cleaned != "NOT FOUND":
                            print(789)
                            submission.is_sent_to_adjudication = True
                            submission.save()
                            print(f"Submission {submission.id} marked as sent to adjudication.")
                        else:
                            print(101112)
                            submission.is_notfound = True
                            submission.save()
                            print(f"Submission {submission.id} marked as not found.")

                            filters = Q()
                            if submission.image:
                                filters |= Q(image=submission.image)
                            if submission.video:
                                filters |= Q(video=submission.video)
                            if submission.tattile:
                                filters |= Q(tattile=submission.tattile)

                            if not ReviewBin.objects.filter(filters).exists():
                                ReviewBin.objects.create(
                                    image=submission.image,
                                    video=submission.video,
                                    license_plate=submission.lic_plate,
                                    vehicle_state=submission.veh_state,
                                    submitted_date=submission.submitted_date,
                                    station=submission.station,
                                    is_notfound=True,
                                    tattile = submission.tattile,
                                )
                                print(f"ReviewBin created for submission {submission.id}.@#$%^&*(...........................................")
                            else:
                                print(f"ReviewBin already exists for submission {submission.id}.")

        response_data = {
            "fileProcessedCount": record_count,
            "errors": errors if errors else None,
            "duplicatePlates": duplicate_plates if duplicate_plates else None
        }

        return Response(ServiceResponse({
            "statusCode": 400 if duplicate_plates else 200,
            "message": f"{record_count} Records processed successfully" if record_count > 0 else "No valid records processed",
            "data": response_data
        }).data, status=200)
    

class SubmitDuncanSubmissionDataView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=SubmitSubmissionViewInputModel,
        tags=['SubmissionView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = SubmitSubmissionViewInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }).data, status=400)
        
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        data = serializer.validated_data
        state_name = readToken.get('stateName')
        station_name = readToken.get('stationName')
        station_id = readToken.get('stationId')
        
        license_plate = data.get('licensePlate').replace(" ","") if data.get('licensePlate') else None
        is_rejected = data.get('isRejected')
        is_submitted = data.get('isSubmitted')
        is_skipped = data.get('isSkipped')
        image_id = data.get('imageId') if data.get('imageId') else None
        video_id = data.get('videoId') if data.get('videoId') else None
        tattile_id = data.get('tattileId') if data.get('tattileId') else None
        reject_id = data.get('rejectId')
        state_ab = data.get('stateAB') if data.get('stateAB') else None
        is_notfound = data.get('isNotFound') if data.get('isNotFound') else None
        is_sent_to_adjudication = data.get("isSendToAdjudicatorView") if data.get("isSendToAdjudicatorView") else None
        is_unknown = data.get("isUnknown") if data.get("isUnknown") else None
        camera_date = data.get("cameraDate") if data.get("cameraDate") else None
        camera_time = data.get("cameraTime") if data.get("cameraTime") else None

        if video_id:
            existing_submission = DuncanSubmission.objects.filter(station=station_name,lic_plate=license_plate,veh_state=state_ab).first()
            if existing_submission and existing_submission.isSubmitted and is_submitted ==True and is_skipped == False:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": f"The Lic Plate {license_plate} has already been processed, and we are awaiting the returns.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.video_id == video_id and existing_submission.isSubmitted == True and is_rejected == True:
                process_media_rejection(Video,video_id,is_rejected,reject_id)
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was previously submitted and it has been rejected successfully.",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.video_id == video_id and existing_submission.isSkipped and is_skipped == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously skipped please choose another tag.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.video_id == video_id and existing_submission.is_notfound and is_notfound == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously not found please choose another tag.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.video_id == video_id and existing_submission.is_sent_to_adjudication and is_sent_to_adjudication == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag is already sent to adjudicator view.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.video_id == video_id and existing_submission.is_unknown and is_unknown == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag is already marked as unknown.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.video_id == video_id and existing_submission.isSkipped == False and existing_submission.isSubmitted == True and is_skipped == True and is_submitted == True:
                existing_submission.isSkipped = is_skipped
                existing_submission.isSubmitted = existing_submission.isSubmitted
                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was submitted previously and it has been skipped successfully",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.video_id == video_id and existing_submission.isSkipped == True and existing_submission.isSubmitted == False and is_submitted == True:
                existing_submission.isSubmitted = is_submitted
                existing_submission.isSkipped = is_skipped
                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was skipped previously and it has been submitted successfully",
                    "data": None
                }).data, status=200)
            

            
            if is_rejected == True:
                process_media_rejection(Video,video_id,is_rejected,reject_id)
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been rejected successfully",
                    "data": None
                }).data, status=200)

            if not existing_submission and is_submitted or is_skipped:
                create_submission(data, state_ab, station_name)
                review_bin_obj = ReviewBin.objects.filter(video_id=video_id).first()

                if review_bin_obj and review_bin_obj.is_sent_back_subbin:
                    review_bin_obj.is_sent_back_subbin = False
                    review_bin_obj.save()
                
                status_message = "submitted" if is_submitted else "skipped"
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": f"This tag has been {status_message} successfully",
                    "data": None
                    }).data, status=200)

            # the tag was previously submitted and sent to review bin and again we are submitting in the submissions bin
            # after coming back from review bin

            if existing_submission and is_submitted == True:
                existing_submission.isSubmitted = is_submitted
                existing_submission.is_unknown = False
                review_bin_obj = ReviewBin.objects.filter(video_id=video_id).first()
                if review_bin_obj and review_bin_obj.is_sent_back_subbin:
                    review_bin_obj.is_sent_back_subbin = False
                    review_bin_obj.save()

                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was previously submitted and it has been submitted successfully.",
                    "data": None
                }).data, status=200)
            
            
            if is_notfound == True:
                print("In Not found ")
                # update video table is not found
                # update submission table is not found
                submission_obj = DuncanSubmission.objects.filter(video_id=video_id).first()
                if not submission_obj:
                    print("In Not found, Not Submission object ---------------")
                    duncan_master = DuncanMasterData.objects.filter(lic_plate=license_plate,state=state_ab).first()
                    if duncan_master and duncan_master.full_name == "NOT FOUND":
                        create_submission(data, state_ab, station_name)

                        video_obj = Video.objects.filter(id=video_id).first()
                        video_obj.is_notfound = is_notfound
                        video_obj.save()

                        fields = {
                            "station_name": station_name,
                            "video_object": video_obj,
                            "image_object": None,
                            "is_notfound": is_notfound,
                            "is_adjudicated_in_review_bin": False,
                            "is_send_adjbin": False,
                            "is_sent_back_subbin": False,
                            "license_plate": license_plate,
                            "vehicle_state": state_ab,
                            "tattile_object" : None
                        }

                        print(video_obj,"initiating saving process for review bin ----------------")
                        ReviewBinUtils.save_reviewbin_data(**fields)
                        return Response(ServiceResponse({
                            "statusCode": 200,
                            "message": "This tag has been marked as not found and sent to review bin successfully",
                            "data": None
                        }).data, status=200)
                    else:
                        return Response(ServiceResponse({
                            "statusCode": 400,
                            "message": "This tag is not submitted previously. Please submit the tag first",
                            "data": None
                        }).data, status=200)
                    
                submission_obj.is_notfound = is_notfound
                if submission_obj.is_unknown:
                    submission_obj.is_unknown = False    
                video_obj = Video.objects.filter(id=video_id).first()
                video_obj.is_notfound = is_notfound


                video_obj.save()
                submission_obj.save()

                fields = {
                    "station_name": station_name,
                    "video_object": video_obj,
                    "image_object": None,
                    "is_notfound": is_notfound,
                    "is_adjudicated_in_review_bin": False,
                    "is_send_adjbin": False,
                    "is_sent_back_subbin": False,
                    "license_plate": license_plate,
                    "vehicle_state": state_ab,
                    "tattile_object" : None
                }
                print("In Not found, All Submission object ---------------")
                print(video_obj,"initiating saving process for review bin ----------------")
                ReviewBinUtils.save_reviewbin_data(**fields)
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been marked as not found and sent to review bin successfully",
                    "data": None
                }).data, status=200)

            if is_sent_to_adjudication == True:
                submission_obj = DuncanSubmission.objects.filter(video_id=video_id).first()
                if not submission_obj:
                    create_submission(data, state_ab, station_name)

                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "This tag has been sent to adjudicator view successfully",
                        "data": None
                    }).data, status=200)

                submission_obj.is_sent_to_adjudication = is_sent_to_adjudication
                if submission_obj.is_unknown:
                    submission_obj.is_unknown = False
                
                submission_obj.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been sent to adjudicator view successfully",
                    "data": None
                }).data, status=200)
                
            if is_unknown == True:
                submission_obj = DuncanSubmission.objects.filter(video_id=video_id).first()
                if not submission_obj:
                    create_submission(data, state_ab, station_name)

                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "This tag has been marked as unknown successfully",
                        "data": None
                    }).data, status=200)
                
                submission_obj.is_unknown = is_unknown
                
                submission_obj.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been marked as unknown Successfully",
                    "data": None
                }).data, status=200)
        elif image_id:
            existing_submission = DuncanSubmission.objects.filter(station=station_name,lic_plate=license_plate,veh_state=state_ab).first()
            if existing_submission and existing_submission.isSubmitted and is_submitted ==True and is_skipped == False:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": f"The Lic Plate {license_plate} has already been processed, and we are awaiting the returns.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.image_id == image_id and existing_submission.isSubmitted == True and is_rejected == True:
                process_media_rejection(Image,image_id,is_rejected,reject_id)
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously submitted and it has been rejected successfully.",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.image_id == image_id and existing_submission.isSkipped and is_skipped == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously skipped please choose another tag.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.image_id == image_id and existing_submission.is_notfound and is_notfound == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously not found please choose another tag.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.image_id == image_id and existing_submission.is_sent_to_adjudication and is_sent_to_adjudication == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously sent to adjudicator view please choose another tag.",
                    "data": None
            }).data, status=200)


            if existing_submission and existing_submission.image_id == image_id and existing_submission.is_unknown and is_unknown == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag is already marked as unknown.",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.image_id == image_id and existing_submission.isSkipped == False and existing_submission.isSubmitted == True and is_skipped == True and is_submitted == True:
                existing_submission.isSkipped = is_skipped
                existing_submission.isSubmitted = existing_submission.isSubmitted
                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was submitted previously and it has been skipped successfully",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.isSkipped == True and existing_submission.isSubmitted == False and is_submitted == True:
                existing_submission.isSubmitted = is_submitted
                existing_submission.isSkipped = is_skipped
                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was skipped previously and it has been submitted successfully",
                    "data": None
                }).data, status=200)
            
            if is_rejected == True:
                process_media_rejection(Image,image_id,is_rejected,reject_id)
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been rejected successfully",
                    "data": None
                }).data, status=200)

            if not existing_submission and is_submitted or is_skipped:
                create_submission(data, state_ab, station_name)
                review_bin_obj = ReviewBin.objects.filter(image_id=image_id).first()
                if review_bin_obj and review_bin_obj.is_sent_back_subbin:
                    review_bin_obj.is_sent_back_subbin = False
                    review_bin_obj.save()
                
                status_message = "submitted" if is_submitted else "skipped"
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": f"This tag has been {status_message} successfully",
                    "data": None
                    }).data, status=200)
            
            if existing_submission and is_submitted:
                existing_submission.isSubmitted = is_submitted
                existing_submission.is_unknown = False
                
                review_bin_obj = ReviewBin.objects.filter(image_id=image_id).first()
                if review_bin_obj and review_bin_obj.is_sent_back_subbin:
                    review_bin_obj.is_sent_back_subbin = False
                    review_bin_obj.save()

                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was previously submitted and it has been submitted successfully.",
                    "data": None
                }).data, status=200)


            if is_notfound:
                # update submission table is not found
                submission_obj = DuncanSubmission.objects.filter(image_id=image_id).first()
                if not submission_obj:
                    # if not found in submission table
                    duncan_master = DuncanMasterData.objects.filter(lic_plate=license_plate,state=state_ab).first()
                    if duncan_master and duncan_master.full_name == 'NOT FOUND':
                        create_submission(data, state_ab, station_name)

                        image_obj = Image.objects.filter(id=image_id).first()
                        image_obj.is_notfound = is_notfound
                        image_obj.save()

                        ReviewBinUtils.save_reviewbin_data(**{
                            "image_object": image_obj,
                            "station_name": station_name,
                            "is_notfound": is_notfound,
                            "is_adjudicated_in_review_bin": False,
                            "is_send_adjbin": False,
                            "is_sent_back_subbin": False,
                            "license_plate": license_plate,
                            "vehicle_state": state_ab,
                            "video_object": None,
                            "tattile_object" : None
                        })
                        # print("")

                        return Response(ServiceResponse({
                            "statusCode": 200,
                            "message": "This tag has been marked as not found and sent to review bin successfully",
                            "data": None
                        }).data, status=200)
                    else:
                        return Response(ServiceResponse({
                            "statusCode": 400,
                            "message": "This tag cannot be marked as not found. Please submit the tag first.",
                            "data": None
                        }).data, status=200)
                

                image_obj = Image.objects.filter(id=image_id).first()
                image_obj.is_notfound = is_notfound
                submission_obj.is_notfound = is_notfound
                if submission_obj.is_unknown:
                    submission_obj.is_unknown = False
                image_obj.save()
                submission_obj.save()

                ReviewBinUtils.save_reviewbin_data(**{
                    "image_object": image_obj,
                    "station_name": station_name,
                    "is_notfound": is_notfound,
                    "is_adjudicated_in_review_bin": False,
                    "is_send_adjbin": False,
                    "is_sent_back_subbin": False,
                    "license_plate": license_plate,
                    "vehicle_state": state_ab,
                    "video_object": None,
                    "tattile_object" : None
                })

                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been marked as not found and sent to review bin successfully",
                    "data": None
                    }).data, status=200)

            if is_sent_to_adjudication:
                submission_obj = DuncanSubmission.objects.filter(image_id=image_id).first()
                if not submission_obj:
                    create_submission(data, state_ab, station_name)
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "This tag has been sent to adjudication successfully",
                        "data": None
                    }).data, status=200)
                submission_obj.is_sent_to_adjudication = is_sent_to_adjudication
                if submission_obj.is_unknown:
                    submission_obj.is_unknown = False
                submission_obj.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been sent to adjudicator view successfully",
                    "data": None
                }).data, status=200)
                
            if is_unknown:
                submission_obj = DuncanSubmission.objects.filter(image_id=image_id).first()
                if not submission_obj:
                    create_submission(data, state_ab, station_name)
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "This tag has been marked as unknown successfully",
                        "data": None
                    }).data, status=200)
                
                submission_obj.is_unknown = is_unknown
                
                
                submission_obj.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been marked as unknown successfully",
                    "data": None
                }).data, status=200)
        elif tattile_id:
            existing_submission = DuncanSubmission.objects.filter(station=station_name,lic_plate=license_plate,veh_state=state_ab).first()
            if existing_submission and existing_submission.isSubmitted and is_submitted ==True and is_skipped == False:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": f"The Lic Plate {license_plate} has already been processed, and we are awaiting the returns.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.tattile_id == tattile_id and existing_submission.isSubmitted == True and is_rejected == True:
                process_tattile_media_rejection(Tattile,tattile_id,is_rejected,reject_id)
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously submitted and it has been rejected successfully.",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.tattile_id == tattile_id and existing_submission.isSkipped and is_skipped == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously skipped please choose another tag.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.tattile_id == tattile_id and existing_submission.is_notfound and is_notfound == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously not found please choose another tag.",
                    "data": None
                }).data, status=200)
            
            if existing_submission and existing_submission.tattile_id == tattile_id and existing_submission.is_sent_to_adjudication and is_sent_to_adjudication == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag was previously sent to adjudicator view please choose another tag.",
                    "data": None
            }).data, status=200)


            if existing_submission and existing_submission.tattile_id == tattile_id and existing_submission.is_unknown and is_unknown == True:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "This tag is already marked as unknown.",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.tattile_id == tattile_id and existing_submission.isSkipped == False and existing_submission.isSubmitted == True and is_skipped == True and is_submitted == True:
                existing_submission.isSkipped = is_skipped
                existing_submission.isSubmitted = existing_submission.isSubmitted
                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was submitted previously and it has been skipped successfully",
                    "data": None
                }).data, status=200)

            if existing_submission and existing_submission.isSkipped == True and existing_submission.isSubmitted == False and is_submitted == True:
                existing_submission.isSubmitted = is_submitted
                existing_submission.isSkipped = is_skipped
                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was skipped previously and it has been submitted successfully",
                    "data": None
                }).data, status=200)
            
            if is_rejected == True:
                process_tattile_media_rejection(Tattile,tattile_id,is_rejected,reject_id,license_plate,
                    state_ab,
                    station_name,
                    camera_date,
                    camera_time)
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been rejected successfully",
                    "data": None
                }).data, status=200)

            if not existing_submission and is_submitted or is_skipped:
                create_submission(data, state_ab, station_name)
                status_message = "submitted" if is_submitted else "skipped"
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": f"This tag has been {status_message} successfully",
                    "data": None
                    }).data, status=200)
            
            if existing_submission and is_submitted:
                existing_submission.isSubmitted = is_submitted
                existing_submission.is_unknown = False
                
                review_bin_obj = ReviewBin.objects.filter(tattile_id=tattile_id).first()
                if review_bin_obj and review_bin_obj.is_sent_back_subbin:
                    review_bin_obj.is_sent_back_subbin = False
                    review_bin_obj.save()

                existing_submission.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag was previously submitted and it has been submitted successfully.",
                    "data": None
                }).data, status=200)

            if is_notfound:
                # update submission table is not found
                submission_obj = DuncanSubmission.objects.filter(image_id=image_id).first()
                if not submission_obj:
                    # if not found in submission table
                    duncan_master = DuncanMasterData.objects.filter(lic_plate=license_plate,state=state_ab).first()
                    if duncan_master and duncan_master.full_name == 'NOT FOUND':
                        create_submission(data, state_ab, station_name)

                        tattile_obj = Tattile.objects.filter(id=tattile_id).first()
                        tattile_obj.is_not_found = is_notfound
                        tattile_obj.save()

                        ReviewBinUtils.save_reviewbin_data(**{
                            "image_object": None,
                            "station_name": station_name,
                            "is_notfound": is_notfound,
                            "is_adjudicated_in_review_bin": False,
                            "is_send_adjbin": False,
                            "is_sent_back_subbin": False,
                            "license_plate": license_plate,
                            "vehicle_state": state_ab,
                            "video_object": None,
                            "tattile_object" : tattile_obj
                        })

                        return Response(ServiceResponse({
                            "statusCode": 200,
                            "message": "This tag has been marked as not found and sent to review bin successfully",
                            "data": None
                        }).data, status=200)
                    else:
                        return Response(ServiceResponse({
                            "statusCode": 400,
                            "message": "This tag cannot be marked as not found. Please submit the tag first.",
                            "data": None
                        }).data, status=200)
                

                tattile_obj = Tattile.objects.filter(id=tattile_id).first()
                tattile_obj.is_not_found = is_notfound
                submission_obj.is_notfound = is_notfound
                if submission_obj.is_unknown:
                    submission_obj.is_unknown = False

                tattile_obj.save()
                submission_obj.save()

                ReviewBinUtils.save_reviewbin_data(**{
                    "image_object": None,
                    "station_name": station_name,
                    "is_notfound": is_notfound,
                    "is_adjudicated_in_review_bin": False,
                    "is_send_adjbin": False,
                    "is_sent_back_subbin": False,
                    "license_plate": license_plate,
                    "vehicle_state": state_ab,
                    "video_object": None,
                    "tattile_object": tattile_obj
                })

                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been marked as not found and sent to review bin successfully",
                    "data": None
                    }).data, status=200)

            if is_sent_to_adjudication:
                submission_obj = DuncanSubmission.objects.filter(tattile_id=tattile_id).first()
                if not submission_obj:
                    create_submission(data, state_ab, station_name)
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "This tag has been sent to adjudication successfully",
                        "data": None
                    }).data, status=200)
                submission_obj.is_sent_to_adjudication = is_sent_to_adjudication
                if submission_obj.is_unknown:
                    submission_obj.is_unknown = False
                submission_obj.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been sent to adjudicator view successfully",
                    "data": None
                }).data, status=200)
                
            if is_unknown:
                submission_obj = DuncanSubmission.objects.filter(tattile_id=tattile_id).first()
                if not submission_obj:
                    create_submission(data, state_ab, station_name)
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "This tag has been marked as unknown successfully",
                        "data": None
                    }).data, status=200)
                
                submission_obj.is_unknown = is_unknown
                
                
                submission_obj.save()
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "This tag has been marked as unknown successfully",
                    "data": None
                }).data, status=200)
            
class VehicleClassificationView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=VehicleClassificationInputModel,
        tags=["SubmissionView"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = VehicleClassificationInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(
                APIResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid input data",
                        "errors": serializer.errors,
                    }
                ).data,
                status=400,
            )

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        first_name = serializer.validated_data["firstName"]
        last_name = serializer.validated_data["lastName"]
        message_text = ""
        try:
            result = classify_vehicle_owner(first_name, last_name)
            print(f"Vehicle Owner Classification Result: {result}")
            classification = result["classification"]

            if classification in ["GOVERNMENT", "EMERGENCY", "PRIVATE_FIRE_SAFETY"]:
                action = "REJECT"
            elif classification == "UNCERTAIN":
                action = "MANUAL_REVIEW"
            else:
                action = "ALLOW"

            if action == "REJECT":
                message_text = "This vehicle appears to be a government or emergency service vehicle.Are you sure you want to submit this citation?"
            return Response(
                {
                    "statusCode": 200,
                    "message": "Vehicle classification completed successfully.",
                    "classification": classification,
                    "confidence": result.get("confidence"),
                    "reason": result.get("reason"),
                    "action": action,
                    "messageText": message_text,
                    "source": "GPT-4.1-mini",
                }
            )
        except RateLimitError:
            return Response(
                {
                    "statusCode": 204,
                    "message": (
                        "Vehicle classification is temporarily unavailable due to usage limits. Please try again later."
                    ),
                    "action": "MANUAL_REVIEW",
                    "source": "OPENAI",
                },
                status=200,
            )
        except Exception as e:
            return Response(
                {
                    "statusCode": 500,
                    "message": "An error occurred during vehicle classification.",
                    "error": str(e),
                },
                status=500,
            )