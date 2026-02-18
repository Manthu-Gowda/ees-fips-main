from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import get_presigned_url, user_information
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from rest_framework.views import APIView
from .agency_adjudicationbin_utils import AgencyAdjudicationBinUtils, generate_s3_file_name, update_existing_citation_data


class SubmitAgencyAdjudicationBin(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=SubmitAgencyAdjudicationBinViewInputModel,
                         tags=['AgencyAdjudicationBin'],
                         security=[{'Bearer': []}])
    def post(self, request):
        serializer = SubmitAgencyAdjudicationBinViewInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data" : serializer.errors}).data, status=200)
        
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')
        license_plate = serializer.validated_data.get('licensePlate').replace(" ","") if serializer.validated_data.get('licensePlate') else None

        is_adjudicated_in_agency_adjudication_bin = serializer.validated_data.get('isAdjudicatedInAgencyAdjudicationBin')
        is_rejected_in_agency_adjudication_bin = serializer.validated_data.get('isRejectedInAgencyAdjudicationBin')
        image_id = serializer.validated_data.get('imageId') if serializer.validated_data.get('imageId') else None
        video_id = serializer.validated_data.get('videoId') if serializer.validated_data.get('videoId') else None
        tattile_id = serializer.validated_data.get('tattileId') if serializer.validated_data.get('tattileId') else None
        submitted_date = serializer.validated_data.get('submittedDate')
        state_ab = serializer.validated_data.get('stateAB')
        citationID = serializer.validated_data.get('citationID')
        reject_id = serializer.validated_data.get('rejectId', None)

        if video_id:
            existing_agency_adjudicationbin = AdjudicationBin.objects.filter(video_id=video_id,station=station_name).first()
            if not existing_agency_adjudicationbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Video not found in agency adjudication bin"}).data, status=200)
            
            if existing_agency_adjudicationbin and existing_agency_adjudicationbin.is_rejected and is_rejected_in_agency_adjudication_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Video already rejected in agency adjudication bin"}).data, status=200)
            
            if existing_agency_adjudicationbin and existing_agency_adjudicationbin.is_adjudicated_in_adjudicationbin and is_adjudicated_in_agency_adjudication_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Video already adjudicated in agency adjudication bin"}).data, status=200)
            
            video_obj = Video.objects.filter(id=video_id).first()
            if is_rejected_in_agency_adjudication_bin:
                existing_agency_adjudicationbin.is_rejected = True
                existing_agency_adjudicationbin.save()

                if video_obj:
                    video_obj.isRejected = True
                    video_obj.reject_id = reject_id if reject_id else None
                    video_obj.save()

                citation_obj = Citation.objects.filter(citationID=citationID).first()
                if citation_obj:
                    citation_obj.isRejected = True
                    citation_obj.save()

                # duncan_submission = DuncanSubmission.objects.filter(video_id=video_id).first()
                # if duncan_submission:
                #     duncan_submission.isRejected = True
                #     duncan_submission.save()



                return Response(ServiceResponse({"statusCode": 200,"message": "Video rejected in agency adjudication bin"}).data, status=200)
            
            if is_adjudicated_in_agency_adjudication_bin:
                existing_agency_adjudicationbin.is_adjudicated_in_adjudicationbin = True
                existing_agency_adjudicationbin.save()
                
                citation = Citation.objects.filter(citationID=citationID).first()
                if not citation:
                    extracted_input_fields = AgencyAdjudicationBinUtils.extract_fields(serializer.validated_data)
                    court_date = AgencyAdjudicationBinUtils.get_court_date(station_id)
                    person = AgencyAdjudicationBinUtils.save_person_data(station_id, extracted_input_fields)
                    vehicle = AgencyAdjudicationBinUtils.save_vehicle_data(station_id, extracted_input_fields)
                    date_object = AgencyAdjudicationBinUtils.get_date_object(extracted_input_fields)
                    speed_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], video_id, station_id,
                        extracted_input_fields['speedPic'], None
                    )
                    plate_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], video_id, station_id,
                        None, extracted_input_fields['platePic']
                    )
                    citation = AgencyAdjudicationBinUtils.save_citation_data(station_name,
                        station_id, extracted_input_fields['citationID'], person, vehicle,
                        court_date, date_object, extracted_input_fields, speed_pic, plate_pic
                    )
                    AgencyAdjudicationBinUtils.update_media_data(video_id, citation, extracted_input_fields, speed_pic, plate_pic)
                    AgencyAdjudicationBinUtils.save_metadata(station_id, request.user, video_id, extracted_input_fields, citation)
                    
                else:
                    # if the citation is comin from supervisor view then we need to update it becuase
                    # any fields might get updated by the user
                    # citation.isSendBack = False
                    # citation.save()
                    extracted_input_fields = AgencyAdjudicationBinUtils.extract_fields(serializer.validated_data)
                    update_existing_citation_data(
                        extracted_input_fields, citation.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation.person_id, citation.vehicle_id, station_id, extracted_input_fields['tattile_id'],
                    )
            
                if video_obj:
                    video_obj.is_notfound = False
                    video_obj.isSentToReviewBin = False
                    video_obj.isAdjudicated = True
                    video_obj.isSent = False
                    video_obj.citation = citation
                    video_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(video_id=video_id).first()
                if duncan_submission_obj:
                    duncan_submission_obj.is_notfound = False
                    duncan_submission_obj.save()
                    

                return Response(ServiceResponse({"statusCode": 200,"message": f"Video adjudicated in agency adjudication bin. The Citaton number is {citation.citationID}"}).data, status=200)
            
        if image_id:
            existing_agency_adjudicationbin = AdjudicationBin.objects.filter(image_id=image_id,station=station_name).first()
            if not existing_agency_adjudicationbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image not found in agency adjudication bin", "data" : None}).data, status=200)
            
            if existing_agency_adjudicationbin and existing_agency_adjudicationbin.is_rejected and is_rejected_in_agency_adjudication_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already rejected in agency adjudication bin", "data" : None}).data, status=200)
            
            if existing_agency_adjudicationbin and existing_agency_adjudicationbin.is_adjudicated_in_adjudicationbin and is_adjudicated_in_agency_adjudication_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already adjudicated in agency adjudication bin", "data" : None}).data, status=200)

            image_obj = Image.objects.filter(id=image_id).first()
            if is_rejected_in_agency_adjudication_bin:
                existing_agency_adjudicationbin.is_rejected = True
                existing_agency_adjudicationbin.save()

                if image_obj:
                    image_obj.isRejected = True
                    image_obj.reject_id = reject_id if reject_id else None
                    image_obj.save()

                citation_obj = Citation.objects.filter(citationID=citationID).first()
                if citation_obj:
                    citation_obj.isRejected = True
                    citation_obj.save()
                

                return Response(ServiceResponse({"statusCode": 200,"message": "Image rejected in agency adjudication bin", "data" : None}).data, status=200)
            
            if is_adjudicated_in_agency_adjudication_bin:
                existing_agency_adjudicationbin.is_adjudicated_in_adjudicationbin = True
                existing_agency_adjudicationbin.save()


                citation = Citation.objects.filter(citationID=citationID).first()
                if not citation: # adjucator or from submissions sent to review bin
                    extracted_input_fields = AgencyAdjudicationBinUtils.extract_fields(serializer.validated_data)
                    court_date = AgencyAdjudicationBinUtils.get_court_date(station_id)
                    person = AgencyAdjudicationBinUtils.save_person_data(station_id, extracted_input_fields)
                    vehicle = AgencyAdjudicationBinUtils.save_vehicle_data(station_id, extracted_input_fields)
                    date_object = AgencyAdjudicationBinUtils.get_date_object(extracted_input_fields)
                    speed_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], image_id, station_id,
                        extracted_input_fields['speedPic'], None
                    )
                    plate_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], image_id, station_id,
                        None, extracted_input_fields['platePic']
                    )
                    citation = AgencyAdjudicationBinUtils.save_citation_data(station_name,
                        station_id, extracted_input_fields['citationID'], person, vehicle,
                        court_date, date_object, extracted_input_fields, speed_pic, plate_pic
                    )
                    AgencyAdjudicationBinUtils.update_media_data(image_id, citation, extracted_input_fields, speed_pic, plate_pic)
                    AgencyAdjudicationBinUtils.save_metadata(station_id, request.user, image_id, extracted_input_fields, citation)
                    
                else:
                    # if the citation is comin from supervisor view then we need to update it becuase
                    # any fields might get updated by the user
                    # citation.isSendBack = False
                    # citation.save()
                    extracted_input_fields = AgencyAdjudicationBinUtils.extract_fields(serializer.validated_data)
                    update_existing_citation_data(
                        extracted_input_fields, citation.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation.person_id, citation.vehicle_id, station_id, extracted_input_fields['tattile_id']
                    )
                
                if image_obj:
                    image_obj.isAdjudicated = True
                    image_obj.isSent = False
                    image_obj.citation = citation
                    image_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(image_id=image_id).first()
                if duncan_submission_obj:
                    duncan_submission_obj.is_notfound = False
                    duncan_submission_obj.save()


                return Response(ServiceResponse({"statusCode": 200,"message": f"Image adjudicated in agency adjudication bin. The citation number is {citation.citationID}.", "data" : None}).data, status=200)
            
        #for tattile
        if tattile_id:
            existing_agency_adjudicationbin = AdjudicationBin.objects.filter(tattile_id=tattile_id,station=station_name).first()
            if not existing_agency_adjudicationbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image not found in agency adjudication bin", "data" : None}).data, status=200)
            
            if existing_agency_adjudicationbin and existing_agency_adjudicationbin.is_rejected and is_rejected_in_agency_adjudication_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already rejected in agency adjudication bin", "data" : None}).data, status=200)
            
            if existing_agency_adjudicationbin and existing_agency_adjudicationbin.is_adjudicated_in_adjudicationbin and is_adjudicated_in_agency_adjudication_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already adjudicated in agency adjudication bin", "data" : None}).data, status=200)

            tattile_obj = Tattile.objects.filter(id=image_id).first()
            if is_rejected_in_agency_adjudication_bin:
                existing_agency_adjudicationbin.is_rejected = True
                existing_agency_adjudicationbin.save()

                if tattile_obj:
                    tattile_obj.is_rejected = True
                    tattile_obj.reject_id = reject_id if reject_id else None
                    tattile_obj.save()

                citation_obj = Citation.objects.filter(citationID=citationID).first()
                if citation_obj:
                    citation_obj.isRejected = True
                    citation_obj.save()
                

                return Response(ServiceResponse({"statusCode": 200,"message": "Image rejected in agency adjudication bin", "data" : None}).data, status=200)
            
            if is_adjudicated_in_agency_adjudication_bin:
                existing_agency_adjudicationbin.is_adjudicated_in_adjudicationbin = True
                existing_agency_adjudicationbin.save()


                citation = Citation.objects.filter(citationID=citationID).first()
                if not citation: # adjucator or from submissions sent to review bin
                    extracted_input_fields = AgencyAdjudicationBinUtils.extract_fields(serializer.validated_data)
                    court_date = AgencyAdjudicationBinUtils.get_court_date(station_id)
                    person = AgencyAdjudicationBinUtils.save_person_data(station_id, extracted_input_fields)
                    vehicle = AgencyAdjudicationBinUtils.save_vehicle_data(station_id, extracted_input_fields)
                    date_object = AgencyAdjudicationBinUtils.get_date_object(extracted_input_fields)
                    speed_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], image_id, station_id,
                        extracted_input_fields['speedPic'], None
                    )
                    plate_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], image_id, station_id,
                        None, extracted_input_fields['platePic']
                    )
                    citation = AgencyAdjudicationBinUtils.save_citation_data(station_name,
                        station_id, extracted_input_fields['citationID'], person, vehicle,
                        court_date, date_object, extracted_input_fields, speed_pic, plate_pic
                    )
                    AgencyAdjudicationBinUtils.update_media_data(image_id, citation, extracted_input_fields, speed_pic, plate_pic)
                    AgencyAdjudicationBinUtils.save_metadata(station_id, request.user, image_id, extracted_input_fields, citation)
                    
                else:
                    # if the citation is comin from supervisor view then we need to update it becuase
                    # any fields might get updated by the user
                    # citation.isSendBack = False
                    # citation.save()
                    extracted_input_fields = AgencyAdjudicationBinUtils.extract_fields(serializer.validated_data)
                    update_existing_citation_data(
                        extracted_input_fields, citation.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation.person_id, citation.vehicle_id, station_id, extracted_input_fields['tattile_id']
                    )
                
                if tattile_obj:
                    tattile_obj.is_adjudicated = True
                    tattile_obj.is_sent = False
                    tattile_obj.citation = citation
                    tattile_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(tattile_id=tattile_id).first()
                if duncan_submission_obj:
                    duncan_submission_obj.is_notfound = False
                    duncan_submission_obj.save()


                return Response(ServiceResponse({"statusCode": 200,"message": f"Image adjudicated in agency adjudication bin. The citation number is {citation.citationID}.", "data" : None}).data, status=200)
            
        return Response(ServiceResponse({
            "statusCode": 400,
            "message": "Neither video_id, image_id nor tattile_id provided, or no adjudication/rejection applied"
        }).data, status=200)
    

class GetAgencyAdjudicationBinMediaData(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetAgencyAdjudicationMediaDataInputModel,
        responses={
            200: GetAgencyAdjudicationViewVideoDataByIdModel,
            200: GetAgencyAdjudicationViewImageDataByIdModel,
            200: GetAgencyAdjudicationViewTattileDataByIdModel,
            204: "No content"
        },
        tags=['AgencyAdjudicationBin'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetAgencyAdjudicationMediaDataInputModel(data=request.data)
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
                vehicle_data = None
                person_data = None
                state_data = None
                vehicle_state_data = None
                note = ""
                citation_data = Citation.objects.filter(video_id=videoData.id).values("id", "citationID","person_id","vehicle_id","is_warning","note","plate_pic","speed_pic").first()
                if citation_data:
                    vehicle_data = Vehicle.objects.filter(id=citation_data["vehicle_id"]).values("plate","year","make","model","color","vin","lic_state_id").first()
                    person_data = Person.objects.filter(id=citation_data["person_id"]).values("first_name","middle","last_name","address","city","state","zip").first()
                    state_data = State.objects.filter(ab=person_data["state"]).first()
                    if person_data and person_data.get("state"):
                        state_data = State.objects.filter(ab=person_data["state"]).first()
                    vehicle_state_data = State.objects.filter(id=vehicle_data["lic_state_id"]).first() if vehicle_data else None
                note =  (AdjudicationBin.objects.filter(video_id=videoData.id).first().note if AdjudicationBin.objects.filter(video_id=videoData.id).exists() else "")
       
                data = {
                    "id": videoData.id,
                    "caption": videoData.caption,
                    "url": preSignedUrl,
                    "violatingSpeed": videoData.speed,
                    "datetime": videoData.datetime,
                    "stationId": videoData.station_id,
                    "locationId": videoData.location_id,
                    "locationName": location_info["locationName"],
                    "locationCode": location_info["locationCode"],
                    "postedSpeed": location_info["postedSpeed"],
                    "isSchoolZone": location_info["isSchoolZone"],
                    "stateRS": get_agency_state_rs,
                    "stateId": vehicle_state_data.id if vehicle_state_data else state_id,
                    "stateName": vehicle_state_data.name if vehicle_state_data else None,
                    "stateAB": vehicle_state_data.ab if vehicle_state_data else None,
                    "fineId" : fine_id,
                    "fineAmount": fine_amount,
                    "distance" : videoData.distance,
                    "licensePlate" : vehicle_data["plate"] if vehicle_data else None,
                    "firstName" : person_data["first_name"] if person_data else None,
                    "middleName" : person_data["middle"] if person_data else None,
                    "lastName" : person_data["last_name"] if person_data else None,
                    "address" : person_data["address"] if person_data else None,
                    "city" : person_data["city"] if person_data else None,
                    "personStateAB" : person_data["state"] if person_data else None,
                    "personState": state_data.name if state_data and state_data.name else None,
                    "zip" : person_data["zip"] if person_data else None,
                    "vehicleYear" : vehicle_data["year"] if vehicle_data else None,
                    "make" : vehicle_data["make"] if vehicle_data else None,
                    "model" : vehicle_data["model"] if vehicle_data else None,
                    "color" : vehicle_data["color"] if vehicle_data else None,
                    "vinNumber" : vehicle_data["vin"] if vehicle_data else None,
                    "isWarning" : citation_data["is_warning"] if citation_data else False,
                    "citationId" : citation_data["id"] if citation_data else None,
                    "citationID" : citation_data["citationID"] if citation_data else None,
                    "note" : note,
                    "platePic" : get_presigned_url(citation_data["plate_pic"]) if citation_data else None,
                    "speedPic" : get_presigned_url(citation_data["speed_pic"]) if citation_data else None,
                    "isRejected" :videoData.isRejected,
                    "isAdjudicated":videoData.isAdjudicated,
                    "isSent":videoData.isSent,
                    "isSentToReviewBin":videoData.isSentToReviewBin
                }
                serializer = GetAgencyAdjudicationViewVideoDataByIdModel(data)
        
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
                vehicle_data = None
                person_data = None
                state_data = None
                vehicle_state_data = None
                note = ""
                citation_data = Citation.objects.filter(image_id=imageData.id).values("id", "citationID","person_id","vehicle_id","is_warning","note","plate_pic","speed_pic").first()
                if citation_data:
                    vehicle_data = Vehicle.objects.filter(id=citation_data["vehicle_id"]).values("plate","year","make","model","color","vin","lic_state_id").first()
                    person_data = Person.objects.filter(id=citation_data["person_id"]).values("first_name","middle","last_name","address","city","state","zip").first()
                    if person_data and person_data.get("state"):
                        state_data = State.objects.filter(ab=person_data["state"]).first()
                    vehicle_state_data = State.objects.filter(id=vehicle_data["lic_state_id"]).first() if vehicle_data else None
                note = (AdjudicationBin.objects.filter(image_id=imageData.id).first().note if AdjudicationBin.objects.filter(image_id=imageData.id).exists() else "")
                data = {
                    "id": imageData.id,
                    "ticketId": imageData.ticket_id,
                    "time": imageData.time,
                    "data": imageData.data,
                    "speed": imageData.current_speed_limit,
                    "violatingSpeed": imageData.violating_speed,
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
                    "stateId": vehicle_state_data.id if vehicle_state_data else state_id,
                    "stateName": vehicle_state_data.name if vehicle_state_data else None,
                    "stateAB": vehicle_state_data.ab if vehicle_state_data else None,
                    "imageUrls": image_urls,
                    "fineId" : fine_id,
                    "fineAmount": fine_amount,
                    "distance" : imageData.img_distance,
                    "licensePlate" : vehicle_data["plate"] if vehicle_data else None,
                    "firstName" : person_data["first_name"] if person_data else None,
                    "middleName" : person_data["middle"] if person_data else None,
                    "lastName" : person_data["last_name"] if person_data else None,
                    "address" : person_data["address"] if person_data else None,
                    "city" : person_data["city"] if person_data else None,
                    "personStateAB" : person_data["state"] if person_data else None,
                    "personState": state_data.name if state_data and state_data.name else None,
                    "zip" : person_data["zip"] if person_data else None,
                    "vehicleYear" : vehicle_data["year"] if vehicle_data else None,
                    "make" : vehicle_data["make"] if vehicle_data else None,
                    "model" : vehicle_data["model"] if vehicle_data else None,
                    "color" : vehicle_data["color"] if vehicle_data else None,
                    "vinNumber" : vehicle_data["vin"] if vehicle_data else None,
                    "isWarning" : citation_data["is_warning"] if citation_data else False,
                    "citationId" : citation_data["id"] if citation_data else None,
                    "citationID" : citation_data["citationID"] if citation_data else None,
                    "note" : note,
                    "platePic" : get_presigned_url(citation_data["plate_pic"]) if citation_data else None,
                    "speedPic" : get_presigned_url(citation_data["speed_pic"]) if citation_data else None,
                    "isRejected" :imageData.isRejected,
                    "isAdjudicated":imageData.isAdjudicated,
                    "isSent":imageData.isSent,
                    "isSentToReviewBin":imageData.isSentToReviewBin
                }
                serializer = GetAgencyAdjudicationViewImageDataByIdModel(data)
                
        ## this is for tattile
        elif media_type == 3:
            image_urls = []
            tattile_id_get = AdjudicationBin.objects.get(tattile_id=media_id)
            tattileData = Tattile.objects.filter(
                id=tattile_id_get.tattile.id,
                station_id=station_id,
                is_rejected=False,
                is_removed=False,
            ).first()
            if tattileData:
                tattile_media_data = TattileFile.objects.filter(ticket_id=tattileData.ticket_id,file_type=2).values_list("file_url", flat=True)
                for url in tattile_media_data:
                    image_urls.append(get_presigned_url(url))

                diff = int(tattileData.measured_speed) - int(tattileData.speed_limit)
                location_info = road_location.objects.filter(station_id=station_id).first()
                location_info = get_location(tattileData.location_id)
                diff = int(tattileData.measured_speed) - int(tattileData.speed_limit)
                fine_amount, fine_id = calculate_fine(station_id, location_info["isSchoolZone"], diff)
                vehicle_data = None
                person_data = None
                state_data = None
                vehicle_state_data = None
                note = ""
                citation_data = Citation.objects.filter(tattile_id=tattileData.id).values("id", "citationID","person_id","vehicle_id","is_warning","note","plate_pic","speed_pic").first()
                if citation_data:
                    vehicle_data = Vehicle.objects.filter(id=citation_data["vehicle_id"]).values("plate","year","make","model","color","vin","lic_state_id").first()
                    person_data = Person.objects.filter(id=citation_data["person_id"]).values("first_name","middle","last_name","address","city","state","zip").first()
                    state_data = State.objects.filter(ab=person_data["state"]).first()
                    if person_data and person_data.get("state"):
                        state_data = State.objects.filter(ab=person_data["state"]).first()
                    vehicle_state_data = State.objects.filter(id=vehicle_data["lic_state_id"]).first() if vehicle_data else None
                note =  (AdjudicationBin.objects.filter(tattile_id=tattileData.id).first().note if AdjudicationBin.objects.filter(tattile_id=tattileData.id).exists() else "")

                data = {
                    "id": tattileData.id,
                    "ticketId": tattileData.ticket_id,
                    "time": tattileData.image_time,
                    "data": None,
                    "speed": tattileData.speed_limit,
                    "violatingSpeed": tattileData.measured_speed,
                    "citationId": tattileData.citation_id,
                    "licenseImageUrl": get_presigned_url(tattileData.license_image_url),
                    "speedImageUrl": get_presigned_url(tattileData.speed_image_url),
                    "stationId": tattileData.station_id,
                    "locationId": tattileData.location_id,
                    "locationName": location_info["locationName"],
                    "locationCode": location_info["locationCode"],
                    "postedSpeed": location_info["postedSpeed"],
                    "isSchoolZone": location_info["isSchoolZone"],
                    "stateRS": get_agency_state_rs,
                    "stateId": vehicle_state_data.id if vehicle_state_data else state_id,
                    "stateName": vehicle_state_data.name if vehicle_state_data else None,
                    "stateAB": vehicle_state_data.ab if vehicle_state_data else None,
                    "imageUrls": image_urls,
                    "fineId" : fine_id,
                    "fineAmount": fine_amount,
                    "distance" : tattileData.image_distance,
                    "licensePlate" : vehicle_data["plate"] if vehicle_data else None,
                    "firstName" : person_data["first_name"] if person_data else None,
                    "middleName" : person_data["middle"] if person_data else None,
                    "lastName" : person_data["last_name"] if person_data else None,
                    "address" : person_data["address"] if person_data else None,
                    "city" : person_data["city"] if person_data else None,
                    "personStateAB" : person_data["state"] if person_data else None,
                    "personState": state_data.name if state_data and state_data.name else None,
                    "zip" : person_data["zip"] if person_data else None,
                    "vehicleYear" : vehicle_data["year"] if vehicle_data else None,
                    "make" : vehicle_data["make"] if vehicle_data else None,
                    "model" : vehicle_data["model"] if vehicle_data else None,
                    "color" : vehicle_data["color"] if vehicle_data else None,
                    "vinNumber" : vehicle_data["vin"] if vehicle_data else None,
                    "isWarning" : citation_data["is_warning"] if citation_data else False,
                    "citationId" : citation_data["id"] if citation_data else None,
                    "citationID" : citation_data["citationID"] if citation_data else None,
                    "note" : note,
                    "platePic" : get_presigned_url(citation_data["plate_pic"]) if citation_data else None,
                    "speedPic" : get_presigned_url(citation_data["speed_pic"]) if citation_data else None,
                    "isRejected" :tattileData.is_rejected,
                    "isAdjudicated":tattileData.is_adjudicated,
                    "isSent":tattileData.is_sent,
                    "isSentToReviewBin":tattileData.is_sent_to_review_bin
                }
                serializer = GetAgencyAdjudicationViewTattileDataByIdModel(data)
            
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