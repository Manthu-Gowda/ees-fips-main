from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import ServiceResponse
from rest_framework.views import APIView
# Create your views here.

from .reviewbin_utils import ReviewBinUtils,generate_s3_file_name,update_existing_citation_data
from agency_adjudicationbin_view.agency_adjudicationbin_utils import AgencyAdjudicationBinUtils

class SubmitReviewBinDataView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=SubmitReviewBinViewInputModel,
                         tags=['ReviewBin'],
                         security=[{'Bearer': []}])
    def post(self, request):
        serializer = SubmitReviewBinViewInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data" : serializer.errors}).data, status=200)
        
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')

        license_plate = serializer.validated_data.get('licensePlate').replace(" ","") if serializer.validated_data.get('licensePlate') else None
        is_adjudicated_in_review_bin = serializer.validated_data.get('isAdjudicatedInReviewBin')
        is_send_adjbin = serializer.validated_data.get('isSendToAgencyAdjucationView')
        is_sent_back_subbin = serializer.validated_data.get('isSendBackToSubmissionView')
        image_id = serializer.validated_data.get('imageId') if serializer.validated_data.get('imageId') else None
        video_id = serializer.validated_data.get('videoId') if serializer.validated_data.get('videoId') else None
        tattile_id = serializer.validated_data.get('tattileId') if serializer.validated_data.get('tattileId') else None
        submitted_date = serializer.validated_data.get('submittedDate')
        state_ab = serializer.validated_data.get('stateAB')
        citationID = serializer.validated_data.get('citationID')
        rejectId = serializer.validated_data.get('rejectId', None)
        fine_id = serializer.validated_data.get('fineId')
        def get_fine_amount(fine_id):
            fine_record = Fine.objects.filter(
                id = fine_id
            ).first()
            if fine_record:
                return fine_record.fine
            return None
        fine_amount = get_fine_amount(fine_id)
        if video_id:
            existing_reviewbin = ReviewBin.objects.filter(video_id=video_id,station=station_name).first()
            if not existing_reviewbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Video not found in review bin"}).data, status=200)
            if existing_reviewbin and existing_reviewbin.is_sent_back_subbin and is_sent_back_subbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Video already sent back to submission view"}).data, status=200)

            if existing_reviewbin and existing_reviewbin.is_adjudicated_in_review_bin and is_adjudicated_in_review_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Video already adjudicated in review bin"}).data, status=200)
            
            if existing_reviewbin and existing_reviewbin.is_send_adjbin and is_send_adjbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Video already sent to agency adjudication view"}).data, status=200)
            
            # here citation wont be created yet because it will be created in adjudicator view
            video_obj = Video.objects.filter(id=video_id).first()
            if is_sent_back_subbin and existing_reviewbin:
                existing_reviewbin.is_sent_back_subbin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                if video_obj:
                    video_obj.is_notfound = False
                    video_obj.isSentToReviewBin = False
                    video_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(video_id=video_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False, isSubmitted =False)
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Video sent back to submission view"}).data, status=200)
            
            if is_adjudicated_in_review_bin and existing_reviewbin:
                existing_reviewbin.is_adjudicated_in_review_bin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_sent_back_subbin = False            

                # if the citation is coming from supervisor view then citaion is already saved in database but 
                # if the citation is coming from adjudicator view or submissions view then citation is not saved in database
                # so we need to create citation in database
                citation = Citation.objects.filter(citationID=citationID,video_id=video_id).first()
                if not citation:
                    extracted_input_fields = ReviewBinUtils.extract_fields(serializer.validated_data)
                    court_date = ReviewBinUtils.get_court_date(station_id)
                    person = ReviewBinUtils.save_person_data(station_id, extracted_input_fields)
                    vehicle = ReviewBinUtils.save_vehicle_data(station_id, extracted_input_fields)
                    date_object = ReviewBinUtils.get_date_object(extracted_input_fields)
                    speed_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], video_id, station_id,
                        extracted_input_fields['speedPic'], None
                    )
                    plate_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], video_id, station_id,
                        None, extracted_input_fields['platePic']
                    )
                    citation = ReviewBinUtils.save_citation_data(station_name,
                        station_id, extracted_input_fields['citationID'], person, vehicle,
                        court_date, date_object, extracted_input_fields, speed_pic, plate_pic, fine_amount
                    )
                    ReviewBinUtils.update_media_data(video_id, citation, extracted_input_fields, speed_pic, plate_pic)
                    ReviewBinUtils.save_metadata(station_id, request.user, video_id, extracted_input_fields, citation)
                    
                else:
                    # if the citation is comin from supervisor view then we need to update it becuase
                    # any fields might get updated by the user
                    # citation.isSendBack = False
                    # citation.save()
                    extracted_input_fields = ReviewBinUtils.extract_fields(serializer.validated_data)
                    update_existing_citation_data(
                        extracted_input_fields, citation.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation.person_id, citation.vehicle_id, station_id
                        ,fine_amount=fine_amount
                    )

                existing_reviewbin.save()

                if video_obj:
                    video_obj.is_notfound = False
                    video_obj.isSentToReviewBin = False
                    video_obj.isAdjudicated = True
                    video_obj.isSent = False
                    video_obj.citation = citation
                    video_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(video_id=video_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False)
                
                return Response(ServiceResponse({"statusCode": 200,"message": f"Video adjudicated in review bin. The citation number is {citation.citationID}"}).data, status=200)
            
            if is_send_adjbin and existing_reviewbin:
                existing_reviewbin.is_send_adjbin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_sent_back_subbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                video_obj = Video.objects.filter(id=video_id).first()
                if video_obj:
                    video_obj.is_notfound = False
                    video_obj.isSentToReviewBin = False
                    video_obj.isSent = False
                    video_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(video_id=video_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False,is_unknown = False)

                fields = {
                    "video_object": video_obj,
                    "image_object": None,
                    "station_name": station_name,
                    "vehicle_state": state_ab,
                    "license_plate": license_plate,
                    "note": serializer.validated_data.get('note', ""),
                    "tattile_object" : None
                }

                AgencyAdjudicationBinUtils.save_agency_adjudication_bin_data(**fields)
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Video sent to agency adjudication view"}).data, status=200)

            if rejectId and existing_reviewbin:
                existing_reviewbin.is_rejected = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_sent_back_subbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                video_obj = Video.objects.filter(id=video_id).first()
                if video_obj:
                    video_obj.isRejected = True
                    video_obj.reject_id = rejectId
                    video_obj.save()

                citation_obj = Citation.objects.filter(video_id=video_id).first()
                if citation_obj:
                    citation_obj.isRejected = True
                    citation_obj.save()
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Video rejected in review bin"}).data, status=200)

        elif image_id:
            existing_reviewbin = ReviewBin.objects.filter(image_id=image_id,station=station_name).first()
            if not existing_reviewbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image not found in review bin"}).data, status=200)
            
            if existing_reviewbin and existing_reviewbin.is_sent_back_subbin and is_sent_back_subbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already sent back to submission view"}).data, status=200)

            if existing_reviewbin and existing_reviewbin.is_send_adjbin and is_send_adjbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already sent to agency adjudication view"}).data, status=200)
            
            if existing_reviewbin and existing_reviewbin.is_adjudicated_in_review_bin and is_adjudicated_in_review_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already adjudicated in review bin"}).data, status=200)
            
            if is_sent_back_subbin and existing_reviewbin:
                existing_reviewbin.is_sent_back_subbin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                image_obj = Image.objects.filter(id=image_id).first()
                if image_obj:
                    image_obj.is_notfound = False
                    image_obj.isSentToReviewBin = False
                    image_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(image_id=image_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False,isSubmitted = False)
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Image sent back to submission view"}).data, status=200)
            
            if is_adjudicated_in_review_bin and existing_reviewbin:
                existing_reviewbin.is_adjudicated_in_review_bin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_sent_back_subbin = False

                citation = Citation.objects.filter(citationID=citationID,image_id=image_id).first()
                if not citation: # adjucator or from submissions sent to review bin
                    extracted_input_fields = ReviewBinUtils.extract_fields(serializer.validated_data)
                    court_date = ReviewBinUtils.get_court_date(station_id)
                    person = ReviewBinUtils.save_person_data(station_id, extracted_input_fields)
                    vehicle = ReviewBinUtils.save_vehicle_data(station_id, extracted_input_fields)
                    date_object = ReviewBinUtils.get_date_object(extracted_input_fields)
                    speed_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], image_id, station_id,
                        extracted_input_fields['speedPic'], None
                    )
                    plate_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], image_id, station_id,
                        None, extracted_input_fields['platePic']
                    )
                    citation = ReviewBinUtils.save_citation_data(station_name,
                        station_id, extracted_input_fields['citationID'], person, vehicle,
                        court_date, date_object, extracted_input_fields, speed_pic, plate_pic
                    )
                    ReviewBinUtils.update_media_data(image_id, citation, extracted_input_fields, speed_pic, plate_pic)
                    ReviewBinUtils.save_metadata(station_id, request.user, image_id, extracted_input_fields, citation)
                else: # supervisor sent to review bin for stations like fed-m hud-c oil ...
                    extracted_input_fields = ReviewBinUtils.extract_fields(serializer.validated_data)
                    update_existing_citation_data(
                        extracted_input_fields, citation.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation.person_id, citation.vehicle_id, station_id
                    )

                existing_reviewbin.save()
                image_obj = Image.objects.filter(id=image_id).first()
                if image_obj:
                    image_obj.is_notfound = False
                    image_obj.isSentToReviewBin = False
                    image_obj.isAdjudicated = True
                    image_obj.isSent = False
                    image_obj.citation = citation
                    image_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(image_id=image_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False)
                
                return Response(ServiceResponse({"statusCode": 200,"message": f"Image adjudicated in review bin. The citation number is  {citation.citationID}"}).data, status=200)

            if is_send_adjbin and existing_reviewbin:
                existing_reviewbin.is_send_adjbin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_sent_back_subbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                image_obj = Image.objects.filter(id=image_id).first()
                if image_obj:
                    image_obj.is_notfound = False
                    image_obj.isSentToReviewBin = False
                    image_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(image_id=image_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False,is_unknown = False)

                # send image to agency adjudication view
                fields = {
                    "video_object": None,
                    "image_object": image_obj,
                    "station_name": station_name,
                    "vehicle_state": state_ab,
                    "license_plate": license_plate,
                    "note": serializer.validated_data.get('note', ""),
                    "tattile_object" : None
                }

                # send image to agency adjudication view
                AgencyAdjudicationBinUtils.save_agency_adjudication_bin_data(**fields)
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Image sent to agency adjudication view"}).data, status=200)
            
            if rejectId and existing_reviewbin:
                existing_reviewbin.is_rejected = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_sent_back_subbin = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                image_obj = Image.objects.filter(id=image_id).first()
                if image_obj:
                    image_obj.isRejected  = True
                    image_obj.reject_id = rejectId
                    image_obj.save()

                citation = Citation.objects.filter(citationID=citationID,image_id=image_id).first()
                if citation:
                    citation.isRejected = True
                    citation.save()

                # duncan_submission_obj = DuncanSubmission.objects.filter(image_id=image_id).first()
                # if duncan_submission_obj:
                #     duncan_submission_obj.is_notfound = False
                #     duncan_submission_obj.save()
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Image rejected in review bin"}).data, status=200)
        
        elif tattile_id:
            existing_reviewbin = ReviewBin.objects.filter(tattile_id=tattile_id,station=station_name).first()
            if not existing_reviewbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image not found in review bin"}).data, status=200)
            
            if existing_reviewbin and existing_reviewbin.is_sent_back_subbin and is_sent_back_subbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already sent back to submission view"}).data, status=200)

            if existing_reviewbin and existing_reviewbin.is_send_adjbin and is_send_adjbin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already sent to agency adjudication view"}).data, status=200)
            
            if existing_reviewbin and existing_reviewbin.is_adjudicated_in_review_bin and is_adjudicated_in_review_bin:
                return Response(ServiceResponse({"statusCode": 400,"message": "Image already adjudicated in review bin"}).data, status=200)
            
            if is_sent_back_subbin and existing_reviewbin:
                existing_reviewbin.is_sent_back_subbin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                tattile_obj = Tattile.objects.filter(id=tattile_id)
                if tattile_obj:
                    tattile_obj.update(is_not_found = False, is_sent_to_review_bin = False)

                duncan_submission_obj = DuncanSubmission.objects.filter(tattile_id=tattile_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False,isSubmitted = False)
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Image sent back to submission view"}).data, status=200)
            
            if is_adjudicated_in_review_bin and existing_reviewbin:
                existing_reviewbin.is_adjudicated_in_review_bin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_sent_back_subbin = False

                citation = Citation.objects.filter(citationID=citationID,tattile_id=tattile_id).first()
                if not citation: # adjucator or from submissions sent to review bin
                    extracted_input_fields = ReviewBinUtils.extract_fields(serializer.validated_data)
                    court_date = ReviewBinUtils.get_court_date(station_id)
                    person = ReviewBinUtils.save_person_data(station_id, extracted_input_fields)
                    vehicle = ReviewBinUtils.save_vehicle_data(station_id, extracted_input_fields)
                    date_object = ReviewBinUtils.get_date_object(extracted_input_fields)
                    speed_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], tattile_id, station_id,
                        extracted_input_fields['speedPic'], None
                    )
                    plate_pic = generate_s3_file_name(
                        extracted_input_fields['mediaType'], tattile_id, station_id,
                        None, extracted_input_fields['platePic']
                    )
                    citation = ReviewBinUtils.save_citation_data(station_name,
                        station_id, extracted_input_fields['citationID'], person, vehicle,
                        court_date, date_object, extracted_input_fields, speed_pic, plate_pic,fine_amount
                    )
                    ReviewBinUtils.update_media_data(tattile_id, citation, extracted_input_fields, speed_pic, plate_pic)
                    ReviewBinUtils.save_metadata(station_id, request.user, tattile_id, extracted_input_fields, citation)
                else: # supervisor sent to review bin for stations like fed-m hud-c oil ...
                    extracted_input_fields = ReviewBinUtils.extract_fields(serializer.validated_data)
                    update_existing_citation_data(
                        extracted_input_fields, citation.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation.person_id, citation.vehicle_id, station_id,
                        extracted_input_fields['tattile_id'], fine_amount=fine_amount
                    )

                existing_reviewbin.save()
                tattile_obj = Tattile.objects.filter(id=tattile_id).first()
                if tattile_obj:
                    tattile_obj.is_not_found = False
                    tattile_obj.is_sent_to_review_bin = False
                    tattile_obj.is_adjudicated = True
                    tattile_obj.is_sent = False
                    tattile_obj.citation = citation
                    tattile_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(tattile_id=tattile_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False)
                
                return Response(ServiceResponse({"statusCode": 200,"message": f"Image adjudicated in review bin. The citation number is  {citation.citationID}"}).data, status=200)

            if is_send_adjbin and existing_reviewbin:
                existing_reviewbin.is_send_adjbin = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_sent_back_subbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                tattile_obj = Tattile.objects.filter(id=tattile_id).first()
                if tattile_obj:
                    tattile_obj.is_not_found = False
                    tattile_obj.is_sent_to_review_bin = False
                    tattile_obj.save()

                duncan_submission_obj = DuncanSubmission.objects.filter(tattile_id=tattile_id)
                if duncan_submission_obj:
                    duncan_submission_obj.update(is_notfound = False,is_unknown = False)

                # send image to agency adjudication view
                fields = {
                    "video_object": None,
                    "image_object": None,
                    "station_name": station_name,
                    "vehicle_state": state_ab,
                    "license_plate": license_plate,
                    "note": serializer.validated_data.get('note', ""),
                    "tattile_object" : tattile_obj
                }

                # send image to agency adjudication view
                AgencyAdjudicationBinUtils.save_agency_adjudication_bin_data(**fields)
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Image sent to agency adjudication view"}).data, status=200)
            
            if rejectId and existing_reviewbin:
                existing_reviewbin.is_rejected = True
                existing_reviewbin.is_notfound = False
                existing_reviewbin.is_sent_back_subbin = False
                existing_reviewbin.is_send_adjbin = False
                existing_reviewbin.is_adjudicated_in_review_bin = False
                existing_reviewbin.save()

                tattile_obj = Tattile.objects.filter(id=tattile_id).first()
                if tattile_obj:
                    tattile_obj.is_rejected  = True
                    tattile_obj.reject_id = rejectId
                    tattile_obj.save()

                citation = Citation.objects.filter(citationID=citationID,tattile_id=tattile_id).first()
                if citation:
                    citation.isRejected = True
                    citation.save()

                # duncan_submission_obj = DuncanSubmission.objects.filter(image_id=image_id).first()
                # if duncan_submission_obj:
                #     duncan_submission_obj.is_notfound = False
                #     duncan_submission_obj.save()
                
                return Response(ServiceResponse({"statusCode": 200,"message": "Image rejected in review bin"}).data, status=200)