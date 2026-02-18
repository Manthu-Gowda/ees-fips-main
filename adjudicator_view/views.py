from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import TokenService, get_presigned_url
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from rest_framework.views import APIView
from ees.utils import get_base64_from_presigned_url, user_information
from .adjudicator_utils import AdjudicatorUtils, update_existing_citation_data,generate_s3_file_name
data_agencies = Data.objects.all()
from reviewbin_view.reviewbin_utils import ReviewBinUtils

class SubmitAdjudicatorDataView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=SubmitAdjudicatorInputModel,
        tags=['AdjudicatorView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = SubmitAdjudicatorInputModel(data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=400)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')
        extracted_input_fields = AdjudicatorUtils.extract_fields(serializer.validated_data)

        def get_fine_amount(fine_id):
            fine_record = Fine.objects.filter(
                id = fine_id
            ).first()
            if fine_record:
                return fine_record.fine
            return None
        fine_amount = get_fine_amount(extracted_input_fields.get('fine_id'))

        # Video Adjudication Flow
        if extracted_input_fields['mediaType'] == 1:
            video_id = AdjudicatorUtils.get_video_id_for_adjudication(
                station_id, extracted_input_fields['video_id']
            )
            if not video_id:
                return Response(APIResponse({
                    "statusCode": 404,
                    "message": "No valid video found for adjudication."
                }).data, status=200)

            is_video_adjudicated = Video.objects.filter(station_id=station_id, id=video_id).first()
            if not is_video_adjudicated:
                return Response(APIResponse({
                    "statusCode": 404,
                    "message": "Video record not found for adjudication."
                }).data, status=200)

            if extracted_input_fields["violate_speed"] == 0 and extracted_input_fields['is_adjudicated'] == True:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "Violating speed should not be 0."
                }).data, status=200)
            
            if is_video_adjudicated.isAdjudicated and extracted_input_fields['is_adjudicated'] and is_video_adjudicated.isSent == False:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This video has already been adjudicated."
                }).data, status=200)

            if is_video_adjudicated.isAdjudicated and extracted_input_fields['is_rejected'] and not is_video_adjudicated.isSent:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This citation has already been adjudicated. It cannot be rejected. Please choose another citation."
                }).data, status=200)
            
            if is_video_adjudicated.isAdjudicated and extracted_input_fields['isSentToReviewBin'] and not is_video_adjudicated.isSent:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This citation has already been adjudicated. It cannot be sent to review bin. Please choose another citation."
                }).data, status=200)

            # to update if existing citation is sent back for changes from the supervisor view
            if not is_video_adjudicated.isAdjudicated and is_video_adjudicated.isSent and extracted_input_fields['is_adjudicated']:
                citation_data = Citation.objects.filter(citationID=extracted_input_fields['citationID']).first()
                if citation_data:
                    update_existing_citation_data(
                        extracted_input_fields, citation_data.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation_data.person_id, citation_data.vehicle_id, station_id, extracted_input_fields['tattile_id']
                        ,fine_amount=fine_amount
                    )
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Video citation has been successfully re-adjudicated."
                    }).data, status=200)
            
            if extracted_input_fields['is_rejected'] == True:
                if is_video_adjudicated:
                    is_video_adjudicated.isRejected = extracted_input_fields['is_rejected']
                    is_video_adjudicated.reject_id = extracted_input_fields['reject_id']
                    is_video_adjudicated.save()
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Video citation has been rejected successfully."
                    }).data, status=200)
                else:
                    return Response(APIResponse({
                        "statusCode": 404,
                        "message": "No video record found for adjudication to update as rejected."
                    }).data, status=200)
                
            if extracted_input_fields['isSentToReviewBin'] == True and station_id in [35,38,39, 42, 44]:  #[24,53]
                # fed-m = 35, hud = 38, wbr2 = 39
                if is_video_adjudicated:
                    is_video_adjudicated.isSentToReviewBin = extracted_input_fields['isSentToReviewBin']
                    is_video_adjudicated.save()

                    fields = {
                        "station_name": station_name,
                        "image_object": None,
                        "video_object": is_video_adjudicated,
                        "is_notfound": False,
                        "is_send_to_adj": False,
                        "is_send_adjbin": False,
                        "is_sent_back_subbin": False,
                        "license_plate": extracted_input_fields['license_plate'],
                        "vehicle_state": extracted_input_fields['state_ab'],
                        "note": extracted_input_fields['note'],
                        }
                    
                    print(fields)

                    ReviewBinUtils.save_reviewbin_data(**fields)
                    duncan_sub_obj = DuncanSubmission.objects.filter(video_id=video_id).first()
                    if duncan_sub_obj:
                        duncan_sub_obj.is_sent_to_adjudication = False
                        duncan_sub_obj.save()
                    
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Video citation has been sent to review bin successfully."
                    }).data, status=200)
                else:
                    return Response(APIResponse({
                        "statusCode": 404,
                        "message": "No video record found for adjudication to update as sent to review bin."
                    }).data, status=200)

            # For Fresh Adjudication
            if not is_video_adjudicated.isAdjudicated:
                court_date = AdjudicatorUtils.get_court_date(station_id)
                person = AdjudicatorUtils.save_person_data(station_id, extracted_input_fields)
                vehicle = AdjudicatorUtils.save_vehicle_data(station_id, extracted_input_fields)
                date_object = AdjudicatorUtils.get_date_object(extracted_input_fields)
                speed_pic = generate_s3_file_name(
                    extracted_input_fields['mediaType'], video_id, station_id,
                    extracted_input_fields['speedPic'], None
                )
                plate_pic = generate_s3_file_name(
                    extracted_input_fields['mediaType'], video_id, station_id,
                    None, extracted_input_fields['platePic']
                )
                citation = AdjudicatorUtils.save_citation_data(
                    station_name, station_id, extracted_input_fields['citationID'], person, vehicle,
                    court_date, date_object, extracted_input_fields, speed_pic, plate_pic, fine_amount
                )
                AdjudicatorUtils.update_media_data(video_id, citation, extracted_input_fields, speed_pic, plate_pic)
                AdjudicatorUtils.save_metadata(station_id, request.user, video_id, extracted_input_fields, citation)
                if not extracted_input_fields['is_adjudicated']:
                    message = "Video citation has been rejected successfully."
                else:
                    message = f"Video citation has been adjudicated successfully. The citation number is {citation.citationID}."
                return Response(APIResponse({
                    "statusCode": 200,
                    "message": message
                }).data, status=200)

        # Image Adjudication Flow
        elif extracted_input_fields['mediaType'] == 2:
            image_id = AdjudicatorUtils.get_image_id_for_adjudication(station_id, extracted_input_fields['image_id'])
            if not image_id:
                return Response(APIResponse({
                    "statusCode": 404,
                    "message": "No valid image found for adjudication."
                }).data, status=200)

            is_image_adjudicated = Image.objects.filter(id=image_id).first()
            if not is_image_adjudicated:
                return Response(APIResponse({
                    "statusCode": 404,
                    "message": "Image record not found for adjudication."
                }).data, status=200)

            if extracted_input_fields["violate_speed"] == 0 and extracted_input_fields['is_adjudicated'] == True:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "Violating speed should not be 0."
                }).data, status=200)
            
            if is_image_adjudicated.isAdjudicated and extracted_input_fields['isSentToReviewBin'] == True and not is_image_adjudicated.isSent:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This citation has already been adjudicated. It cannot be sent to review bin. Please choose another citation."
                }).data, status=200)
            
            if is_image_adjudicated.isAdjudicated and extracted_input_fields['is_adjudicated'] and is_image_adjudicated.isSent == False:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This image has already been adjudicated."
                }).data, status=200)

            if is_image_adjudicated.isAdjudicated and extracted_input_fields['is_rejected'] and not is_image_adjudicated.isSent:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This citation has already been adjudicated. It cannot be rejected. Please choose another citation."
                }).data, status=200)

            # to update if existing citation is sent back for changes from the supervisor view
            if not is_image_adjudicated.isAdjudicated and is_image_adjudicated.isSent and extracted_input_fields['is_adjudicated']:
                citation_data = Citation.objects.filter(citationID=extracted_input_fields['citationID']).first()
                if citation_data:
                    update_existing_citation_data(
                        extracted_input_fields, citation_data.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation_data.person_id, citation_data.vehicle_id, station_id
                    )
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Image citation has been successfully re-adjudicated."
                    }).data, status=200)
                
            if extracted_input_fields['is_rejected']:
                if is_image_adjudicated:
                    is_image_adjudicated.isRejected = extracted_input_fields['is_rejected']
                    is_image_adjudicated.reject_id = extracted_input_fields['reject_id']
                    is_image_adjudicated.save()
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Image citation has been rejected successfully."
                    }).data, status=200)
                else:
                    return Response(APIResponse({
                        "statusCode": 404,
                        "message": "No image record found for adjudication to update as rejected."
                    }).data, status=200)
            
            if extracted_input_fields['isSentToReviewBin'] == True and station_id in [35,38,39, 42, 44]:  # [24,53]
                if is_image_adjudicated:
                    is_image_adjudicated.isSentToReviewBin = extracted_input_fields['isSentToReviewBin']
                    is_image_adjudicated.save()
                    fields = {
                        'mediaType': extracted_input_fields['mediaType'],
                        'video_object': None,
                        'image_object': is_image_adjudicated,
                        "station_name": station_name,
                        "is_notfound": False,
                        "is_send_to_adj": False,
                        "is_send_adjbin": False,
                        "is_sent_back_subbin": False,
                        "license_plate": extracted_input_fields.get("licensePlate", ""),
                        "vehicle_state": extracted_input_fields.get("vehicleState", ""),
                        "note": extracted_input_fields.get("note", ""),
                        }
                    print(fields)
                    ReviewBinUtils.save_reviewbin_data(**fields)
                    duncan_sub_obj = DuncanSubmission.objects.filter(image=is_image_adjudicated).first()
                    if duncan_sub_obj:
                        duncan_sub_obj.is_sent_to_adjudication = False
                        duncan_sub_obj.save()
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Image citation has been sent to review bin successfully."
                    }).data, status=200)
                else:
                    return Response(APIResponse({
                        "statusCode": 404,
                        "message": "No image record found for adjudication to update as sent to review bin."
                    }).data, status=200)
            # For Fresh Adjudication
            if not is_image_adjudicated.isAdjudicated:
                court_date = AdjudicatorUtils.get_court_date(station_id)
                person = AdjudicatorUtils.save_person_data(station_id, extracted_input_fields)
                vehicle = AdjudicatorUtils.save_vehicle_data(station_id, extracted_input_fields)
                date_object = AdjudicatorUtils.get_date_object(extracted_input_fields)
                speed_pic = generate_s3_file_name(
                    extracted_input_fields['mediaType'], image_id, station_id,
                    extracted_input_fields['speedPic'], None
                )
                plate_pic = generate_s3_file_name(
                    extracted_input_fields['mediaType'], image_id, station_id,
                    None, extracted_input_fields['platePic']
                )
                citation = AdjudicatorUtils.save_citation_data(
                    station_name, station_id, extracted_input_fields['citationID'], person, vehicle,
                    court_date, date_object, extracted_input_fields, speed_pic, plate_pic
                )
                AdjudicatorUtils.update_media_data(image_id, citation, extracted_input_fields, speed_pic, plate_pic)
                AdjudicatorUtils.save_metadata(station_id, request.user, image_id, extracted_input_fields, citation)
                if not extracted_input_fields['is_adjudicated']:
                    message = "Image citation has been rejected successfully."
                else:
                    message = f"Image citation has been adjudicated successfully. The citation number is {citation.citationID}."
                return Response(APIResponse({
                    "statusCode": 200,
                    "message": message
                }).data, status=200)
                
        elif extracted_input_fields['mediaType'] == 3:
            tattile_id = AdjudicatorUtils.get_tattile_id_for_adjudication(station_id, extracted_input_fields['tattile_id'])
            if not tattile_id:
                return Response(APIResponse({
                    "statusCode": 404,
                    "message": "No valid image found for adjudication."
                }).data, status=200)

            is_tattile_adjudicated = Tattile.objects.filter(id=tattile_id).first()
            if not is_tattile_adjudicated:
                return Response(APIResponse({
                    "statusCode": 404,
                    "message": "Image record not found for adjudication."
                }).data, status=200)

            if extracted_input_fields["violate_speed"] == 0 and extracted_input_fields['is_adjudicated'] == True:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "Violating speed should not be 0."
                }).data, status=200)
            
            if is_tattile_adjudicated.is_adjudicated and extracted_input_fields['isSentToReviewBin'] == True and not is_tattile_adjudicated.is_sent:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This citation has already been adjudicated. It cannot be sent to review bin. Please choose another citation."
                }).data, status=200)
            
            if is_tattile_adjudicated.is_adjudicated and extracted_input_fields['is_adjudicated'] and is_tattile_adjudicated.is_sent == False:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This image has already been adjudicated."
                }).data, status=200)

            if is_tattile_adjudicated.is_adjudicated and extracted_input_fields['is_rejected'] and not is_tattile_adjudicated.is_sent:
                return Response(APIResponse({
                    "statusCode": 400,
                    "message": "This citation has already been adjudicated. It cannot be rejected. Please choose another citation."
                }).data, status=200)

            # to update if existing citation is sent back for changes from the supervisor view
            if not is_tattile_adjudicated.is_adjudicated and is_tattile_adjudicated.is_sent and extracted_input_fields['is_adjudicated']:
                citation_data = Citation.objects.filter(citationID=extracted_input_fields['citationID']).first()
                if citation_data:
                    update_existing_citation_data(
                        extracted_input_fields, citation_data.citationID,
                        extracted_input_fields['mediaType'], extracted_input_fields['video_id'],
                        extracted_input_fields['image_id'], extracted_input_fields['is_adjudicated'],
                        extracted_input_fields['isSent'], citation_data.person_id, citation_data.vehicle_id, station_id, extracted_input_fields['tattile_id']
                        ,fine_amount=fine_amount
                    )
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Image citation has been successfully re-adjudicated."
                    }).data, status=200)
                
            if extracted_input_fields['is_rejected']:
                if is_tattile_adjudicated:
                    is_tattile_adjudicated.is_rejected = extracted_input_fields['is_rejected']
                    is_tattile_adjudicated.reject_id = extracted_input_fields['reject_id']
                    is_tattile_adjudicated.save()
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Image citation has been rejected successfully."
                    }).data, status=200)
                else:
                    return Response(APIResponse({
                        "statusCode": 404,
                        "message": "No image record found for adjudication to update as rejected."
                    }).data, status=200)
            
            if extracted_input_fields['isSentToReviewBin'] == True and station_id in [35,38,39, 42, 44]: #[24,53]
                if is_tattile_adjudicated:
                    is_tattile_adjudicated.is_not_found = True
                    is_tattile_adjudicated.is_sent_to_review_bin = extracted_input_fields['isSentToReviewBin']
                    is_tattile_adjudicated.save()
                    fields = {
                        'mediaType': extracted_input_fields['mediaType'],
                        'video_object': None,
                        'image_object': None,
                        "station_name": station_name,
                        "is_notfound": True,
                        "is_send_to_adj": False,
                        "is_send_adjbin": False,
                        "is_sent_back_subbin": False,
                        "license_plate": extracted_input_fields.get("licensePlate", ""),
                        "vehicle_state": extracted_input_fields.get("vehicleState", ""),
                        "note": extracted_input_fields.get("note", ""),
                        "tattile_object" : is_tattile_adjudicated
                        }
                    print(fields)
                    ReviewBinUtils.save_reviewbin_data(**fields)
                    duncan_sub_obj = DuncanSubmission.objects.filter(tattile_id=is_tattile_adjudicated.id).first()
                    if duncan_sub_obj:
                        duncan_sub_obj.is_notfound = True
                        duncan_sub_obj.is_sent_to_adjudication = False
                        duncan_sub_obj.save()
                    return Response(APIResponse({
                        "statusCode": 200,
                        "message": "Image citation has been sent to review bin successfully."
                    }).data, status=200)
                else:
                    return Response(APIResponse({
                        "statusCode": 404,
                        "message": "No image record found for adjudication to update as sent to review bin."
                    }).data, status=200)
            # For Fresh Adjudication
            if not is_tattile_adjudicated.is_adjudicated:
                court_date = AdjudicatorUtils.get_court_date(station_id)
                person = AdjudicatorUtils.save_person_data(station_id, extracted_input_fields)
                vehicle = AdjudicatorUtils.save_vehicle_data(station_id, extracted_input_fields)
                date_object = AdjudicatorUtils.get_date_object(extracted_input_fields)
                speed_pic = generate_s3_file_name(
                    extracted_input_fields['mediaType'], tattile_id, station_id,
                    extracted_input_fields['speedPic'], None
                )
                plate_pic = generate_s3_file_name(
                    extracted_input_fields['mediaType'], tattile_id, station_id,
                    None, extracted_input_fields['platePic']
                )
                citation = AdjudicatorUtils.save_citation_data(
                    station_name, station_id, extracted_input_fields['citationID'], person, vehicle,
                    court_date, date_object, extracted_input_fields, speed_pic, plate_pic, fine_amount
                )
                AdjudicatorUtils.update_media_data(tattile_id, citation, extracted_input_fields, speed_pic, plate_pic)
                AdjudicatorUtils.save_metadata(station_id, request.user, tattile_id, extracted_input_fields, citation)
                if not extracted_input_fields['is_adjudicated']:
                    message = "Image citation has been rejected successfully."
                else:
                    message = f"Image citation has been adjudicated successfully. The citation number is {citation.citationID}."
                return Response(APIResponse({
                    "statusCode": 200,
                    "message": message
                }).data, status=200)
        
        return Response(APIResponse({
            "statusCode": 500,
            "message": "Unhandled adjudication flow."
        }).data, status=500)
    

class GetPreSignedUrls(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetPreSignedUrlBase64StringInputModel,
        responses={
            200: GetVideoBase64StringOutputModel,
            200: GetImageBase64StringOutputModel
        },
        tags=['AdjudicatorView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetPreSignedUrlBase64StringInputModel(data=request.data)
        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=200)

        media_id = serializer.validated_data.get('mediaId')
        media_type = serializer.validated_data.get('mediaType')
        read_token = user_information(request)
        if isinstance(read_token, Response):
            return read_token
        
        station_id = read_token.get('stationId')

        if media_type == 1:
            video_filters = {
                "id": media_id,
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
            }
            video_data = Video.objects.filter(**video_filters).first()
            if video_data:
                base64 = get_presigned_url(video_data.url)
                video_urls = []
                video_urls.append(base64)
                data ={
                    "imageBase64Strings":video_urls
                }
                
                response_serializer = GetVideoBase64StringOutputModel(data)
                if response_serializer:
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "Success",
                        "data": response_serializer.data
                    }).data, status=200)
                else:
                    return Response({
                        "statusCode": 500,
                        "message": "Error serializing video data",
                        "errors": response_serializer.errors
                    }, status=200)

        elif media_type == 2:
            image_data = Image.objects.filter(
                id=media_id,
                station_id=station_id,
                isRejected=False,
                isRemoved=False,
            ).first()
            if image_data:
                image_urls = []
                image_ticket_id = image_data.ticket_id
                image_hash_urls = ImageHash.objects.filter(ticket_id=image_ticket_id).values_list('image_url', flat=True)
                image_data_urls = ImageData.objects.filter(ticket_id=image_ticket_id).values_list('image_url', flat=True)
                for image_url in list(image_hash_urls) + list(image_data_urls):
                    image_urls.append(get_presigned_url(image_url))

                data = {
                    "imageBase64Strings": image_urls
                }
                response_serializer = GetImageBase64StringOutputModel(data)
                if response_serializer:
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "Success",
                        "data": response_serializer.data
                    }).data, status=200)
                else:
                    return Response({
                        "statusCode": 500,
                        "message": "Error serializing image data",
                        "errors": response_serializer.errors
                    }, status=200)

        elif media_type == 3:
            print(media_id, "media ID")
            image_urls = []
            tattile_data = Tattile.objects.filter(station_id=station_id,id=media_id).first()
            
            if tattile_data:
                tattile_media_data = TattileFile.objects.filter(ticket_id=tattile_data.ticket_id,file_type=2).values_list("file_url", flat=True)
                for url in tattile_media_data:
                    image_urls.append(get_presigned_url(url))
                
                data = {
                    "imageBase64Strings": image_urls
                }
                response_serializer = GetImageBase64StringOutputModel(data)
                if response_serializer:
                    return Response(ServiceResponse({
                        "statusCode": 200,
                        "message": "Success",
                        "data": response_serializer.data
                    }).data, status=200)
                else:
                    return Response({
                        "statusCode": 500,
                        "message": "Error serializing image data",
                        "errors": response_serializer.errors
                    }, status=200)
            
        return Response({
            "statusCode": 404,
            "message": "No valid data found for the given media ID and type"
        }, status=200)


class GenerateNewCitationIDView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=['AdjudicatorView'],
        responses={200: GetNewCitationID},
        security=[{'Bearer': []}]
    )
    def get(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get("stationId")
        station_name = readToken.get('stationName')
        station_citations = Citation.objects.filter(station__id=station_id)
        
        if station_citations.exists():
            latest_citation = station_citations.order_by("-citationID").values_list("citationID", flat=True).first()
            next_num = int(latest_citation.split("-")[-1]) + 1
        else:
            next_num = 1

        new_citation_number = f"{station_name}-{next_num:08d}"
        response = {
            "citationID" : new_citation_number
        }
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": GetNewCitationID(response).data
        }).data,status=200)
        

class GetAdjudicationMediaDataView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetAdjudicationMediaDataInputModel,
        responses={
            200: GetAdjudicationViewVideoDataByIdModel,
            200: GetAdjudicationViewImageDataByIdModel,
            200: GetAdjudicationViewTattileDataByIdModel,
            204: "No content"
        },
        tags=['AdjudicatorView'],
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
                if ReviewBin.objects.filter(video_id=videoData.id).exists() and (videoData.isSent or videoData.isSentToReviewBin):
                    note = ReviewBin.objects.filter(video_id=videoData.id).first().note
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
                    "note" : note if note else "",
                    "platePic" : get_presigned_url(citation_data["plate_pic"]) if citation_data else None,
                    "speedPic" : get_presigned_url(citation_data["speed_pic"]) if citation_data else None,
                    "isRejected" :videoData.isRejected,
                    "isAdjudicated":videoData.isAdjudicated,
                    "isSent":videoData.isSent,
                    "isSentToReviewBin":videoData.isSentToReviewBin
                }
                serializer = GetAdjudicationViewVideoDataByIdModel(data)
        
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
                if ReviewBin.objects.filter(image_id=imageData.id).exists() and (imageData.isSent or imageData.isSentToReviewBin):
                    note = ReviewBin.objects.filter(image_id=imageData.id).first().note 
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
                    "note" : note if note else "",
                    "platePic" : get_presigned_url(citation_data["plate_pic"]) if citation_data else None,
                    "speedPic" : get_presigned_url(citation_data["speed_pic"]) if citation_data else None,
                    "isRejected" :imageData.isRejected,
                    "isAdjudicated":imageData.isAdjudicated,
                    "isSent":imageData.isSent,
                    "isSentToReviewBin":imageData.isSentToReviewBin
                }
                serializer = GetAdjudicationViewImageDataByIdModel(data)
                
        elif media_type == 3:
            media_urls = []
            tattile_data = Tattile.objects.filter(id=media_id).first()
            location_info = get_location(tattile_data.location_id)
            citation_check = Citation.objects.filter(tattile= tattile_data.id)
            if citation_check.exists():
                plate_text = citation_check.first().vehicle.plate
            else:
                plate_text = ""
            if tattile_data:
                duncan_submission_tattile = DuncanSubmission.objects.filter(tattile_id=tattile_data.id).first()
                
                tattile_media_data = TattileFile.objects.filter(ticket_id=tattile_data.ticket_id,file_type=2).values_list("file_url", flat=True)
                for url in tattile_media_data:
                    media_urls.append(get_presigned_url(url))

                diff = int(tattile_data.measured_speed) - int(location_info["postedSpeed"])
                fine_amount, fine_id = calculate_fine(station_id, location_info["isSchoolZone"], diff)
                # fine_amount, fine_id = calculate_fine(station_id, location_info.isSchoolZone, diff)
                vehicle_data = None
                person_data = None
                state_data = None
                vehicle_state_data = None
                note =''
                citation_data = Citation.objects.filter(tattile_id=tattile_data.id).values("id", "citationID","person_id","vehicle_id","is_warning","note","plate_pic","speed_pic").first()
                if citation_data:
                    vehicle_data = Vehicle.objects.filter(id=citation_data["vehicle_id"]).values("plate","year","make","model","color","vin","lic_state_id").first()
                    person_data = Person.objects.filter(id=citation_data["person_id"]).values("first_name","middle","last_name","address","city","state","zip").first()
                    if person_data and person_data.get("state"):
                        state_data = State.objects.filter(ab=person_data["state"]).first()
                    vehicle_state_data = State.objects.filter(id=vehicle_data["lic_state_id"]).first() if vehicle_data else None
                if ReviewBin.objects.filter(tattile_id=tattile_data.id).exists() and (tattile_data.is_sent or tattile_data.is_sent_to_review_bin):
                    note = ReviewBin.objects.filter(tattile_id=tattile_data.id).first().note 
                data = {
                    "id": tattile_data.id,
                    "ticketId": tattile_data.ticket_id,
                    "time": tattile_data.image_time,
                    "data": None,
                    "speed": tattile_data.speed_limit,
                    "violatingSpeed": tattile_data.measured_speed,
                    "citationId": tattile_data.citation_id if tattile_data else None,
                    "licenseImageUrl": tattile_data.license_image_url,
                    "speedImageUrl": tattile_data.speed_image_url,
                    "stationId": tattile_data.station_id,
                    "locationId": tattile_data.location_id,
                    "locationName": location_info["locationName"],
                    "locationCode": location_info["locationCode"],
                    "postedSpeed": location_info["postedSpeed"],
                    "isSchoolZone": location_info["isSchoolZone"],
                    "stateRS": get_agency_state_rs,
                    "stateId": vehicle_state_data.id if vehicle_state_data else state_id,
                    "stateName": vehicle_state_data.name if vehicle_state_data else None,
                    "stateAB": vehicle_state_data.ab if vehicle_state_data else None,
                    "imageUrls": media_urls,
                    "fineId" : fine_id,
                    "fineAmount": fine_amount,
                    "distance" : tattile_data.image_distance,
                    "licensePlate" : plate_text ,
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
                    "note" : note if note else "",
                    "platePic" : get_presigned_url(citation_data["plate_pic"]) if citation_data else None,
                    "speedPic" : get_presigned_url(citation_data["speed_pic"]) if citation_data else None,
                    "isRejected" : tattile_data.is_rejected,
                    "isAdjudicated":tattile_data.is_adjudicated,
                    "isSent":tattile_data.is_sent,
                    "isSentToReviewBin": tattile_data.is_sent_to_review_bin
                }
                serializer = GetAdjudicationViewTattileDataByIdModel(data)
                

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
    

class GetBase64StringForPresignedUrlsView(APIView):
    @swagger_auto_schema(
        request_body=PresignedUrlInputModel,
        responses={200:GetBase64StringResponseModel},
        tags=['AdjudicatorView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = PresignedUrlInputModel(data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=400)
        
        preSignedUrl = serializer.validated_data.get('preSignedUrl')
        base64String = get_base64_from_presigned_url(preSignedUrl)
        if base64String:
            response_serializer = GetBase64StringResponseModel({"base64String": base64String})
            return Response(ServiceResponse({
                "statusCode":200,
                "message":"success",
                "data": response_serializer.data
            }).data, status=200)
        else:
            return Response(ServiceResponse({
                "statusCode":500,
                "message":"Error Processing the PresignedUrl",
                "data": None
            }).data, status=500)


class GetFineView(APIView):
    @swagger_auto_schema(
        request_body=GetFineViewInputModel,
        responses={200:GetFineViewResponseModel},
        tags=['AdjudicatorView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetFineViewInputModel(data=request.data,partial=True)
        
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=400)
        
        media_id = serializer.validated_data.get('mediaId')
        media_type = serializer.validated_data.get('mediaType')
        violation_speed = serializer.validated_data.get('violated_speed')
        posted_speed = serializer.validated_data.get('posted_speed')
        
        print(media_type, "medis Type")
        diff = violation_speed - posted_speed
        
        print(diff)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken 
         
        station_id = readToken.get('stationId')
        
        def get_location(location_id):
            location = road_location.objects.filter(id=location_id).first()
            return {
                "locationName": location.location_name if location else None,
                "locationCode": location.LOCATION_CODE if location else None,
                "postedSpeed": location.posted_speed if location else None,
                "isSchoolZone": location.isSchoolZone if location else None,
                "isConstructionZone": location.isConstructionZone if location else None
            }
        
        def get_image_location(image_location_id):
            image_location = road_location.objects.filter(trafficlogix_location_id=image_location_id).first()
            return {
                "locationName" : image_location.location_name if image_location else None,
                "locationCode": image_location.LOCATION_CODE if image_location else None,
                "postedSpeed": image_location.posted_speed if image_location else None,
                "isSchoolZone": image_location.isSchoolZone if image_location else None,
                "isConstructionZone": image_location.isConstructionZone if image_location else None
            }
            
        def calculate_fine(station_id, is_school_zone, is_construction_zone, diff):
            
            print(is_school_zone,'is_school_zone', is_construction_zone, 'is_construction_zone')
            # Determine the appropriate speed_diff bucket
            if is_school_zone and station_id != 42:
                if diff <= 10:
                    speed_bucket = 10
                elif diff <= 15:
                    speed_bucket = 15
                elif diff <= 20:
                    speed_bucket = 20
                else:
                    speed_bucket = 21
					
            elif is_school_zone and station_id == 44:
                if diff <= 10:
                    speed_bucket = 10
                elif diff <= 24:
                    speed_bucket = 20
                else:
                    speed_bucket = 25
            elif not is_school_zone and station_id == 44:
                if diff <= 10:
                    speed_bucket = 10
                elif diff <= 24:
                    speed_bucket = 20
                else:
                    speed_bucket = 25	
            else:
                if diff <= 10:
                    speed_bucket = 10
                elif diff <= 20:
                    speed_bucket = 20
                elif diff <= 25:
                    speed_bucket = 25
                elif diff <= 30:
                    speed_bucket = 30
                else:
                    speed_bucket = 31

            # Query the Fine model with all conditions including construction zone
            fine = Fine.objects.filter(
                station_id=station_id,
                isSchoolZone=is_school_zone,
                isConstructionZone=is_construction_zone,  # ✅ Construction zone is considered
                speed_diff=speed_bucket
            ).first()

            # Return the fine amount and its ID, or (None, None) if not found
            return (fine.fine if fine else None, fine.id if fine else None)

        
        if media_type == 1:
            print(media_type, "in Media type 1")
            videoData = Video.objects.filter(
                id=media_id,
                station_id=station_id,
                isRejected=False,
                isRemoved=False
            ).first()
            if videoData:
                print("in video data, check fine from video table")
                location_info = get_location(videoData.location_id)
                fine_amount, fine_id = calculate_fine(station_id, location_info["isSchoolZone"], location_info["isConstructionZone"],diff)
                
        elif media_type == 2:
            imageData = Image.objects.filter(
                id=media_id,
                station_id=station_id,
                isRejected=False,
                isRemoved=False,
                isSentToReviewBin=False
            ).first()
            
            if imageData:
                location_info = get_image_location(imageData.location_id)
                diff = int(imageData.violating_speed) - int(imageData.current_speed_limit)
                fine_amount, fine_id = calculate_fine(station_id, location_info["isSchoolZone"], location_info["isConstructionZone"], diff)
                
        if fine_amount and fine_id :
            response_data = {
                "fine_amount": fine_amount,
                "fine_id": fine_id,
                "posted_speed": posted_speed,       # make sure this is defined
                "violated_speed": violation_speed    # make sure this is defined
            }
            response_serializer = GetFineViewResponseModel(response_data)
            return Response(ServiceResponse({
                "statusCode":200,
                "message":"success",
                "data": response_serializer.data
            }).data, status=200)
        else:
            return Response(ServiceResponse({
                "statusCode":500,
                "message":"Error Processing the FINE",
                "data": None
            }).data, status=500)