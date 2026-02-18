from video.citations.versioning_service import update_citation_versioning_after_approval
from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information, get_presigned_url
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from rest_framework.views import APIView
from drf_yasg import openapi
from .supervisor_utils import *


class GetCitationDataByIdView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'citationId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={200: GetCitationByIdOuputModel},
        tags=['SupervisorView'],
        security=[{'Bearer': []}]
    )

    def get(self, request):
        citation_id = request.query_params.get('citationId', None)

        try:
            citation_id = int(citation_id) if citation_id is not None else 1
        except ValueError:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid requestType. Must be an integer."
            }).data, status=200)
        image_urls = []
        citation_data = Citation.objects.filter(id=citation_id).first()
        video_data = Video.objects.filter(id=citation_data.video_id).first()
        road_location_data = road_location.objects.filter(id=citation_data.location_id).first()
        person_data = Person.objects.filter(id=citation_data.person_id).first()
        vehicle_data = Vehicle.objects.filter(id=citation_data.vehicle_id).first()
        fine_data = Fine.objects.filter(id=citation_data.fine_id).first()
        get_agency_state_rs = Agency.objects.filter(station_id=citation_data.station_id).values_list('state_rs', flat=True).first()
        license_state_ab = State.objects.filter(id=vehicle_data.lic_state_id).values_list('ab', flat=True).first()
        if citation_data.video_id:
            getCitationByIdOuputModel = {
                "citationId" : citation_data.id,
                "videoUrl" : get_presigned_url(video_data.url),
                "imageUrls" : [],
                "speedPic" : get_presigned_url(citation_data.speed_pic),
                "platePic" : get_presigned_url(citation_data.plate_pic),
                "licensePlateState" : license_state_ab,
                "licensePlateNumber" : vehicle_data.plate,
                "postedSpeed" : citation_data.posted_speed,
                "violatingSpeed" : citation_data.speed,
                "locationCode" : road_location_data.LOCATION_CODE,
                "locationName" : road_location_data.location_name,
                "stateRS" : get_agency_state_rs,
                "distance" : citation_data.dist,
                "fine" : fine_data.fine,
                "citationID" : citation_data.citationID,
                "firstName" : person_data.first_name,
                "middleName" : person_data.middle,
                "lastName" : person_data.last_name,
                "phoneNumber" : person_data.phone_number,
                "address" : person_data.address,
                "city" : person_data.city,
                "personStateAB" : person_data.state,
                "zip" : person_data.zip,
                "vehicleYear" : vehicle_data.year,
                "vehicleMake" : vehicle_data.make,
                "vehicleModel" : vehicle_data.model,
                "vehicleColor" : vehicle_data.color,
                "vinNumber" : vehicle_data.vin,
                "note" : citation_data.note,
                "isWarning" : citation_data.is_warning,
                "address" : person_data.address
            }

            return Response(ServiceResponse({
                "statusCode" : 200,
                "message" : "Success",
                "data" : GetCitationByIdOuputModel(getCitationByIdOuputModel).data
            }).data,status=200)
        
        elif citation_data.image_id:
            image_data = Image.objects.filter(id=citation_data.image_id).first()
            image_location_id = road_location.objects.filter(trafficlogix_location_id=citation_data.image_location).first()
            image_ticket_id = image_data.ticket_id
            image_hash_urls = ImageHash.objects.filter(ticket_id=image_ticket_id).values_list('image_url', flat=True)
            image_data_urls = ImageData.objects.filter(ticket_id=image_ticket_id).values_list('image_url', flat=True)
            for image_url in list(image_hash_urls) + list(image_data_urls):
                    image_urls.append(get_presigned_url(image_url))
            getCitationByIdOuputModel = {
                "citationId" : citation_data.id,
                "videoUrl" : None,
                "imageUrls" : image_urls,
                "speedPic" : get_presigned_url(citation_data.speed_pic),
                "platePic" : get_presigned_url(citation_data.plate_pic),
                "licensePlateState" : license_state_ab,
                "licensePlateNumber" : vehicle_data.plate,
                "postedSpeed" : citation_data.posted_speed,
                "violatingSpeed" : citation_data.speed,
                "locationCode" : image_location_id.LOCATION_CODE,
                "locationName" : image_location_id.location_name,
                "stateRS" : get_agency_state_rs,
                "distance" : citation_data.dist,
                "fine" : fine_data.fine,
                "citationID" : citation_data.citationID,
                "firstName" : person_data.first_name,
                "middleName" : person_data.middle,
                "lastName" : person_data.last_name,
                "phoneNumber" : person_data.phone_number,
                "address" : person_data.address,
                "city" : person_data.city,
                "personStateAB" : person_data.state,
                "zip" : person_data.zip,
                "vehicleYear" : vehicle_data.year,
                "vehicleMake" : vehicle_data.make,
                "vehicleModel" : vehicle_data.model,
                "vehicleColor" : vehicle_data.color,
                "vinNumber" : vehicle_data.vin,
                "note" : citation_data.note,
                "isWarning" : citation_data.is_warning
            }

            return Response(ServiceResponse({
                "statusCode" : 200,
                "message" : "Success",
                "data" : GetCitationByIdOuputModel(getCitationByIdOuputModel).data
            }).data,status=200)
        
        elif citation_data.tattile_id:
            tattile_data = Tattile.objects.filter(id=citation_data.tattile_id).first()
            tattile_location_id = road_location.objects.filter(id=citation_data.location_id).first()
            image_ticket_id = tattile_data.ticket_id
            image_data_urls = TattileFile.objects.filter(ticket_id=image_ticket_id,file_type= 2).values_list('file_url', flat=True)
            for image_url in list(image_data_urls):
                    image_urls.append(get_presigned_url(image_url))
            getCitationByIdOuputModel = {
                "citationId" : citation_data.id,
                "videoUrl" : None,
                "imageUrls" : image_urls,
                "speedPic" : get_presigned_url(citation_data.speed_pic),
                "platePic" : get_presigned_url(citation_data.plate_pic),
                "licensePlateState" : license_state_ab,
                "licensePlateNumber" : vehicle_data.plate,
                "postedSpeed" : citation_data.posted_speed,
                "violatingSpeed" : citation_data.speed,
                "locationCode" : tattile_location_id.LOCATION_CODE if tattile_location_id else 2 ,
                "locationName" : tattile_location_id.location_name if tattile_location_id else  "WCR 49 (45 MPH)",
                "stateRS" : get_agency_state_rs,
                "distance" : citation_data.dist if citation_data.dist else None,
                "fine" : fine_data.fine,
                "citationID" : citation_data.citationID,
                "firstName" : person_data.first_name,
                "middleName" : person_data.middle,
                "lastName" : person_data.last_name,
                "phoneNumber" : person_data.phone_number,
                "address" : person_data.address,
                "city" : person_data.city,
                "personStateAB" : person_data.state,
                "zip" : person_data.zip,
                "vehicleYear" : vehicle_data.year,
                "vehicleMake" : vehicle_data.make,
                "vehicleModel" : vehicle_data.model,
                "vehicleColor" : vehicle_data.color,
                "vinNumber" : vehicle_data.vin,
                "note" : citation_data.note,
                "isWarning" : citation_data.is_warning
            }
            distance = getCitationByIdOuputModel['distance']

            if distance is None or str(distance).strip() == "":
                getCitationByIdOuputModel['distance'] = 0
            else:
                getCitationByIdOuputModel['distance'] = int(distance)
                
            return Response(ServiceResponse({
                "statusCode" : 200,
                "message" : "Success",
                "data" : GetCitationByIdOuputModel(getCitationByIdOuputModel).data
            }).data,status=200)
        
        
        return Response(ServiceResponse({
            "statusCode" : 204,
            "message" : "No content",
            "data" : []
        }).data,status=200)
    

class CitationStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body = CitationStatusUpdateInputModel,
        responses={200: ApprovedCitationIDsOutputModel},
        tags=['SupervisorView'],
        security=[{'Bearer' : []}]
    )
    def post(self, request):
        serializer = CitationStatusUpdateInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data" : serializer.errors
            }).data, status=200)
        
        serializer_data = serializer.validated_data
        citation_ids = serializer_data.get('citationIds')
        is_approved = serializer_data.get('isApproved')
        is_send_back = serializer_data.get('isSendBack')
        is_rejected = serializer_data.get('isRejected')
        note = serializer_data.get('note', "")
        user_id = readToken.get('user_id')
        station_id = readToken.get('stationId')
        approved_citation_ids = []

        citation_data = Citation.objects.filter(id__in=citation_ids)
        already_approved_citations = citation_data.filter(isApproved=True)
        if already_approved_citations.exists():
            approved_ids = already_approved_citations.values_list('citationID', flat=True)
            return Response(ServiceResponse({
                "statusCode": 409,
                "message": f"These Citations are already approved and cannot be updated. Please choose valid CitationIDs",
                "data" : ApprovedCitationIDsOutputModel({"citationID" : approved_ids}).data
            }).data, status=200)
        already_rejected_citation = citation_data.filter(isRejected=True)
        if already_rejected_citation.exists() and is_rejected == True | is_approved == True:
            return Response(ServiceResponse({
                "statusCode": 409,
                "message": f"These Citation has been rejected cannot be updated. Please choose valid CitationID",
                "data" : []
                }).data, status=200)
        for citation in citation_data:
            quick_pd_id = save_quick_pd_data(citation.id,note,is_send_back,is_approved,user_id)
            citation.isApproved = is_approved
            citation.isRejected = is_rejected
            citation.isSendBack = is_send_back
            citation.note = note
            citation.save()
            update_media_data(citation.id, is_approved, is_rejected, is_send_back, station_id, note, user_id)
            if is_send_back:
                if citation.video_id:
                    agency_adj_bin_obj = AdjudicationBin.objects.filter(video_id=citation.video_id).first()
                else:
                    agency_adj_bin_obj = AdjudicationBin.objects.filter(image_id=citation.image_id).first()
                    
                if agency_adj_bin_obj:
                    message = "Citation sent back to agency adjudication bin successfully."
                else:
                    message = "Citation sent back to review bin successfully."
                return Response(APIResponse({
                    "statusCode" : 200,
                    "message" : message,
                    "data" : []
                }).data,status=200)
            if is_approved:
                save_supervisor_meta_data(citation.id,user_id,citation.station_id)
                save_csv_meta_data(quick_pd_id,citation.id,user_id,citation.station_id)
                update_citation_versioning_after_approval(citation)
            stationName = Station.objects.filter(id=citation.station_id).values_list('name',flat=True).first()
            if citation.video_id and is_approved:
                create_csv_and_pdf_data(citation.citationID,citation.station_id,stationName,image_flow = False, is_tattile=False)
            elif citation.image_id and is_approved:
                create_csv_and_pdf_data(citation.citationID,citation.station_id,stationName,image_flow = True, is_tattile=False)
            elif citation.tattile_id and is_approved:
                create_csv_and_pdf_data(citation.citationID,citation.station_id,stationName,image_flow = False, is_tattile=True)
            
            else:
                return Response(APIResponse({
                    "statusCode" : 400,
                    "message" : "Citation id did not process successfully.",
                    "data" : []
                }).data,status=200)

        status_messages = []
        if is_approved:
            status_messages.append("approved")
        if is_rejected:
            status_messages.append("rejected")
        if is_send_back:
            status_messages.append("sent back")
        update_message = "Citations have been "+ "".join(status_messages) + " successfully."   
        return Response(ServiceResponse({
            "statusCode" : 200,
            "message" : update_message,
            "data" : []
        }).data,status=200)