from datetime import date, datetime
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from video.models import *
from .serializer import *
from accounts_v2.serializer import ServiceResponse
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated,AllowAny
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from ees.utils import user_information
from collections import defaultdict
from django.db.models import Q
from .drop_down_utils import *
from django.db.models.functions import TruncDate
from django.db.models import Case, When, When, Count, Subquery
import calendar


class GetStateDropDownView(APIView):
    permission_classes=[AllowAny]
    @swagger_auto_schema(
        responses={200: StateDropDownModel(many=True),
                   204: "No Content"},
        tags=['DropDown'],
    )
    def get(self, request):
        states = State.objects.all()

        if not states.exists():
            return Response(ServiceResponse({
            "statusCode": 204,
            "message": "No Content",
            "data": []
        }).data,status=200)

        serializer = StateDropDownModel(states, many=True)
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": serializer.data
        }).data,status=200)


class GetSubmissionDatesDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'requestType',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: GetSubmissionDateDropDownModel(many=True),
            204: 'No Content'
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        request_type = request.query_params.get('requestType', None)

        try:
            request_type = int(request_type) if request_type is not None else 1
        except ValueError:
            return Response({
                "statusCode": 400,
                "message": "Invalid requestType. Must be an integer."
            }, status=400)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_name = readToken.get('stationName', None)

        duncan_data = DuncanSubmission.objects.filter(
            isSubmitted=True,
            isRejected=False,
            isSkipped=False,
            station=station_name,
            isApproved=False
        ).annotate(
            truncated_date=TruncDate('submitted_date')
        ).values('truncated_date').annotate(
            is_sent_count=Count(Case(When(isSent=True, then=1))),
            total_count=Count('id')
        )
        submission_dates = [
            {
                "date": item['truncated_date'].strftime('%B %#d, %Y'),
                "isSent": item['is_sent_count'] == item['total_count'] if request_type == 1 else False
            }
            for item in duncan_data
        ]

        response_dates = sorted(
            submission_dates,
            key=lambda x: datetime.strptime(x["date"], '%B %d, %Y')
        )

        if not response_dates:
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No Content",
                "data": []
            }).data, status=200)

        response_data = GetSubmissionDateDropDownModel(response_dates, many=True)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)
    

class GetRejectReasonsDropDownView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
            manual_parameters=[
            openapi.Parameter(
                'requestType',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        responses= {
            200 : GetRejectReasonsDropDownModel(many=True),
            204 : "No Content"
        },
        tags=['DropDown']
    )
    def get(self, request):
        request_type = request.query_params.get('requestType', None)

        try:
            request_type = int(request_type) if request_type is not None else 1
        except ValueError:
            return Response({
                "statusCode": 400,
                "message": "Invalid requestType. Must be an integer."
            }, status=400)
        if request_type == 3:
            rejectReasons  = Rejects.objects.filter(rejection_type__in= [2,3]).all()
        else:
            rejectReasons  = Rejects.objects.filter(rejection_type=request_type).all()

        if not rejectReasons.exists():
            return Response(ServiceResponse({
            "statusCode": 204,
            "message": "No Content",
            "data": []
            }).data,status=200)

        serializer = GetRejectReasonsDropDownModel(rejectReasons, many=True)
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": serializer.data
        }).data,status=200)
    

class GetSubmissionViewMediaDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMediaDropDownInputModel,
        responses={ 
            200: GetAllVideoDataModel(many=True),
            200: GetAllImageDataModel(many=True),
            200: GetAllTattileDataModel(many=True),
            204: "No Content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetMediaDropDownInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)
        
        date = serializer.validated_data.get('date')
        data_type = serializer.validated_data.get('type')
        filtered_date = None
        if date:
            try:
                normalized_date = date.replace(',', ', ')
                parsed_date = datetime.strptime(normalized_date, "%B %d, %Y")
                filtered_date = parsed_date.strftime("%Y-%m-%d")
                print("Filtered Date:", filtered_date)
            except ValueError:
                return Response({
                    "statusCode": 400,
                    "message": "Invalid date format. Expected 'Month Day, Year'."
                }, status=400)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')
        agency_id = readToken.get('agencyId')
        state_id = readToken.get('stateId')
        state_name = readToken.get('stateName')
        agency_name = readToken.get('agencyName')

        get_agency_state_rs = Agency.objects.filter(id=agency_id).values_list('state_rs', flat=True).first()
        state_ab = State.objects.filter(id=state_id).values_list('ab', flat=True).first()  
        video_data_list = []
        image_data_list = []
        tattile_data_list = []

        if data_type == 1:
            video_filters = {
                "station_id": station_id,
                "isRejected": False,
                "isAdjudicated": False,
                "isRemoved": False,
                "isSent": False,
                "is_notfound": False,
                "speed__lte" : 69
            }

            if station_id == 44:
                video_filters["speed__lte"] = 69

            # Get video IDs already handled (to exclude)
            excluded_video_ids = DuncanSubmission.objects.filter(
                Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                station=station_name
            ).values_list("video_id", flat=True)
            adjudication_video_ids = AdjudicationBin.objects.filter(
                video_id__isnull=False,
                station=station_name
            ).values_list('video_id', flat=True)
            exclude_videos = list(adjudication_video_ids) + list(excluded_video_ids)
            # Get all eligible videos, excluding the ones above
            videoData = Video.objects.filter(**video_filters).exclude(id__in=exclude_videos).order_by("VIDEO_NO", "id")

            # Get location mapping
            video_location_ids = videoData.values_list("location_id", flat=True)
            road_location_data = road_location.objects.filter(id__in=video_location_ids)
            location_map = {location.id: location for location in road_location_data}

            # If needed, map any duncan submissions to these videos
            duncan_submission_data = DuncanSubmission.objects.filter(video_id__in=videoData.values_list("id", flat=True))
            duncan_map = {submission.video_id: submission for submission in duncan_submission_data}
            review_bin_data =  ReviewBin.objects.filter(video_id__in=videoData.values_list("id", flat=True), is_sent_back_subbin = True)
            review_bin_map = {reviewbin.video_id: reviewbin for reviewbin in review_bin_data}

            video_data_list = [
                {
                    "id": video.id,
                    "label": f"{agency_name}_{location_map.get(video.location_id).location_name if video.location_id in location_map else 'Unknown'}_{video.datetime.date().strftime('%m%d%Y')}_{video.datetime.strftime('%I:%M:%S %p')}_{video.VIDEO_NO}",
                    "isRejected": video.isRejected,
                    "isSubmitted": duncan_map.get(video.id).isSubmitted if video.id in duncan_map else False,
                    "isSkipped": duncan_map.get(video.id).isSkipped if video.id in duncan_map else False,
                    "isAdjudicated": video.isAdjudicated,
                    "isUnknown": duncan_map.get(video.id).is_unknown if video.id in duncan_map else False,
                    "isSentBackSubbin" : review_bin_map.get(video.id).is_sent_back_subbin if video.id in review_bin_map else False
                }
                for video in videoData
            ]

        elif data_type == 2:
            image_filters = {
                "station_id": station_id,
                "isRejected": False,
                "isAdjudicated": False,
                "isRemoved": False,
                "isSent": False,
                "is_notfound": False,
            }  

            image_filters = {
                "station_id": station_id,
                "isRejected": False,
                "isAdjudicated": False,
                "isRemoved": False,
                "isSent": False,
                "is_notfound": False,
            }

            # Get all image IDs that were already adjudicated or marked not found
            excluded_image_ids = DuncanSubmission.objects.filter(
                Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                station=station_name
            ).values_list("image_id", flat=True)
            adjudication_image_ids = AdjudicationBin.objects.filter(
                image_id__isnull=False,
                station=station_name
            ).values_list('image_id', flat=True)
            exclude_images = list(adjudication_image_ids) + list(excluded_image_ids)
            # Filter image data with the same filters as old code
            imageData = Image.objects.filter(**image_filters).exclude(id__in=exclude_images).order_by("time", "id")

            image_location_ids = imageData.values_list("location_id", flat=True)
            image_location_data = ImageLocation.objects.filter(location_id__in=image_location_ids)
            image_location_map = {loc.location_id: loc.name for loc in image_location_data}

            # Optional: load submission data if needed for display
            submission_data = DuncanSubmission.objects.filter(image_id__in=imageData.values_list("id", flat=True))
            duncan_map = {submission.image_id: submission for submission in submission_data}
            review_bin_data = ReviewBin.objects.filter(image_id__in=imageData.values_list("id", flat=True),is_sent_back_subbin =  True)
            review_bin_map = {submission.image_id: submission for submission in review_bin_data}

            image_data_list = [
                {
                    "id": image.id,
                    "label": f"{agency_name}_{image_location_map.get(image.location_id, 'Unknown')}_{image.time.date().strftime('%m%d%Y')}_{image.time.strftime('%I:%M %p')}_{image.custom_counter}",
                    "isRejected": image.isRejected,
                    "isSubmitted": duncan_map.get(image.id).isSubmitted if image.id in duncan_map else None,
                    "isSkipped": duncan_map.get(image.id).isSkipped if image.id in duncan_map else None,
                    "isAdjudicated": image.isAdjudicated,
                    "isUnknown": duncan_map.get(image.id).is_unknown if image.id in duncan_map else None,
                    "isSentBackSubbin" : review_bin_map.get(image.id).is_sent_back_subbin if image.id in review_bin_map else False
                }
                for image in imageData
            ]
            
        elif data_type == 3:
            tattile_filters = {
                "station_id": station_id,
                "is_rejected": False,
                "is_adjudicated": False,
                "is_removed": False,
                "is_sent": False,
                "is_not_found": False,
                "is_active" :True,
            }
            if station_id == 44:
                tattile_filters["measured_speed__lte"] = 69
            # Get all image IDs that were already adjudicated or marked not found
            excluded_tattile_ids = DuncanSubmission.objects.filter(
                Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                station=station_name
            ).values_list("tattile_id", flat=True).exclude(tattile_id__isnull=True)
            adjudication_tattile_ids = AdjudicationBin.objects.filter(
                tattile_id__isnull=False,
                station=station_name
            ).values_list('tattile_id', flat=True)
            exclude_tattile = list(adjudication_tattile_ids) + list(excluded_tattile_ids)
            # Filter image data with the same filters as old code
            tattileData = Tattile.objects.filter(**tattile_filters).exclude(id__in=exclude_tattile
                                                                            ).order_by("image_time").distinct("image_time")

            tattile_location_ids = tattileData.values_list("location_id", flat=True)
            road_location_data = road_location.objects.filter(id__in=tattile_location_ids)
            location_map = {location.id: location for location in road_location_data}

            # Optional: load submission data if needed for display
            submission_data = DuncanSubmission.objects.filter(tattile_id__in=tattileData.values_list("id", flat=True))
            duncan_map = {submission.tattile_id: submission for submission in submission_data}
            review_bin_data = ReviewBin.objects.filter(tattile_id__in=tattileData.values_list("id", flat=True),is_sent_back_subbin =  True)
            review_bin_map = {submission.tattile_id: submission for submission in review_bin_data}

            tattile_data_list = [
                {
                    "id": tattile.id,
                    "label": f"{agency_name}_{location_map[tattile.location_id].location_name if tattile.location_id in location_map else None}_{tattile.image_time.date().strftime('%m%d%Y')}_{tattile.image_time.strftime('%I:%M:%S %p')}",
                    "isRejected": tattile.is_rejected,
                    "isSubmitted": duncan_map.get(tattile.id).isSubmitted if tattile.id in duncan_map else None,
                    "isSkipped": duncan_map.get(tattile.id).isSkipped if tattile.id in duncan_map else None,
                    "isAdjudicated": tattile.is_adjudicated,
                    "isUnknown": duncan_map.get(tattile.id).is_unknown if tattile.id in duncan_map else None,
                    "isSentBackSubbin" : review_bin_map.get(tattile.id).is_sent_back_subbin if tattile.id in review_bin_map else False
                }
                for tattile in tattileData
            ] 
           
        if data_type == 1:
            response_data = GetAllVideoDataModel(video_data_list, many=True)
            if not video_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 2:
            response_data = GetAllImageDataModel(image_data_list, many=True)
            if not image_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 3:
            response_data = GetAllTattileDataModel(tattile_data_list, many=True)
            if not tattile_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid type",
                "data": []
            }).data, status=200)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)


class GetAdjudicatorViewMediaDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMediaDropDownInputModel,
        responses={ 
            200: GetAllAdjudicatorVideoDataModel(many=True),
            200: GetAllAdjudicatorImageDataModel(many=True),
            200: GetAllAdjudicatorTattileDataModel(many=True),
            204: "No Content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        serializer = GetMediaDropDownInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)
        
        date = serializer.validated_data.get('date', None)
        data_type = serializer.validated_data.get('type')

        readToken = user_information(request)

        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        stationName = readToken.get('stationName')
        agency_name = readToken.get('agencyName')

        if data_type == 1:
            video_video_filters = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSentToReviewBin": False,
                "is_notfound" : False
            }

            #if station_id in [35,38,39]:
            if station_id in [35,38,39, 42, 44, 69]:
                duncan_submission = DuncanSubmission.objects.filter(station=stationName,is_sent_to_adjudication=True)
                duncan_submission_video_ids = duncan_submission.values_list("video_id", flat=True)

                videoData = Video.objects.filter(id__in=duncan_submission_video_ids, isSent = False,isSentToReviewBin = False, isRejected = False).order_by('VIDEO_NO','id').all()
                video_location_ids = videoData.values_list("location_id", flat=True)
                road_location_data = road_location.objects.filter(id__in=video_location_ids)
                location_map = {location.id: location for location in road_location_data}
                video_data_list = [
                    {
                        "id": video.id,
                        "label" : f"{agency_name}_{location_map[video.location_id].location_name if video.location_id in location_map else None}_{video.datetime.date().strftime('%m%d%Y')}_{video.datetime.strftime('%I:%M:%S %p')}_{video.VIDEO_NO}",
                        "isRejected" : video.isRejected if video.isRejected else False,
                        "isAdjudicated" : video.isAdjudicated,
                        "isSent" : video.isSent
                    }
                    for video in videoData
                    if not video.isRemoved
                ]

            else:
                videoData = Video.objects.filter(**video_video_filters).order_by('VIDEO_NO','id').all()
                video_location_ids = videoData.values_list("location_id", flat=True)
                road_location_data = road_location.objects.filter(id__in=video_location_ids)
                location_map = {location.id: location for location in road_location_data}
                video_data_list = [
                    {
                        "id": video.id,
                        "label" : f"{agency_name}_{location_map[video.location_id].location_name if video.location_id in location_map else None}_{video.datetime.date().strftime('%m%d%Y')}_{video.datetime.strftime('%I:%M:%S %p')}_{video.VIDEO_NO}",
                        "isRejected" : video.isRejected if video.isRejected else False,
                        "isAdjudicated" : video.isAdjudicated,
                        "isSent" : video.isSent
                    }
                    for video in videoData
                    if not video.isRemoved
                ]

        elif data_type == 2:
            image_filters = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSentToReviewBin": False,
                "is_notfound" : False
            }

            #if station_id in [35,38,39]:
            if station_id in [35,38,39, 42, 44, 69]:
                duncan_submission = DuncanSubmission.objects.filter(station=stationName,is_sent_to_adjudication=True)
                duncan_submission_image_ids = duncan_submission.values_list("image_id", flat=True)

                imageData = Image.objects.filter(id__in=duncan_submission_image_ids, isSent = False, isSentToReviewBin = False).order_by('time','id').all()
                image_location_ids = imageData.values_list("location_id", flat=True)
                image_location_data = ImageLocation.objects.filter(location_id__in=image_location_ids)
                image_location_map = {location.location_id: location.name for location in image_location_data}
                road_location_data = road_location.objects.filter(id__in=image_location_ids)
                location_map = {location.id: location for location in road_location_data}
                image_data_list = [
                    {
                        "id": image.id,
                        "label" : f"{agency_name}_{image_location_map[image.location_id]}_{image.time.date().strftime('%m%d%Y')}_{image.time.strftime('%I:%M %p')}_{image.custom_counter}",
                        "isRejected" : image.isRejected,
                        "isAdjudicated" : image.isAdjudicated,
                        "isSent" : image.isSent
                    }
                    for image in imageData
                    if not image.isRemoved
                ]
            else:
                imageData = Image.objects.filter(**image_filters).order_by('time','id').all()
                image_location_ids = imageData.values_list("location_id", flat=True)
                image_location_data = ImageLocation.objects.filter(location_id__in=image_location_ids)
                image_location_map = {location.location_id: location.name for location in image_location_data}
                road_location_data = road_location.objects.filter(id__in=image_location_ids)
                location_map = {location.id: location for location in road_location_data}
                image_data_list = [
                    {
                        "id": image.id,
                        "label" : f"{agency_name}_{ImageLocation.objects.filter(location_id=image.location_id).values_list('name', flat=True).first()}_{image.time.date().strftime('%m%d%Y')}_{image.time.strftime('%I:%M %p')}_{image.custom_counter}",
                        "isRejected" : image.isRejected,
                        "isAdjudicated" : image.isAdjudicated,
                        "isSent" : image.isSent
                    }
                    for image in imageData
                    if not image.isRemoved
                ]
        
        elif data_type == 3:
            date_fmt = "%m%d%Y"
            time_fmt = "%I:%M:%S %p"
            agency_prefix = f"{agency_name}_"

            tattile_data_list = []

            #if station_id in [35,38,39]:
            if station_id in [35,38,39, 42, 44, 69]:
                duncan_submission = DuncanSubmission.objects.filter(
                    station=stationName,
                    is_sent_to_adjudication=True,
                    isRejected=False
                ).values("tattile_id")

                tattileData = (
                    Tattile.objects
                    .filter(
                        id__in=Subquery(duncan_submission),
                        is_sent=False,
                        is_sent_to_review_bin=False,
                        is_removed=False,
                        is_rejected=False,
                        is_active=True,
                    )
                    .order_by("image_time", "id")
                    .values(
                        "id",
                        "location_id",
                        "image_time",
                        "is_rejected",
                        "is_adjudicated",
                        "is_sent",
                    )
                )

            else:
                tattileData = (
                    Tattile.objects
                    .filter(
                        station_id=station_id,
                        is_rejected=False,
                        is_removed=False,
                        is_sent_to_review_bin=False,
                        is_not_found=False,
                        is_active=True,
                    )
                    .order_by("image_time", "id")
                    .values(
                        "id",
                        "location_id",
                        "image_time",
                        "is_rejected",
                        "is_adjudicated",
                        "is_sent",
                    )
                )

            location_ids = {t["location_id"] for t in tattileData if t["location_id"]}
            location_map = {
                loc["id"]: loc["location_name"]
                for loc in road_location.objects
                    .filter(id__in=location_ids)
                    .values("id", "location_name")
            }

            tattile_data_list = [
                {
                    "id": t["id"],
                    "label": (
                        f"{agency_prefix}"
                        f"{location_map.get(t['location_id'])}_"
                        f"{t['image_time'].strftime(date_fmt)}_"
                        f"{t['image_time'].strftime(time_fmt)}"
                    ),
                    "isRejected": t["is_rejected"] or False,
                    "isAdjudicated": t["is_adjudicated"],
                    "isSent": t["is_sent"],
                }
                for t in tattileData
            ]
           
        if data_type == 1:
            response_data = GetAllAdjudicatorVideoDataModel(video_data_list, many=True)
            if not video_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 2:
            response_data = GetAllAdjudicatorImageDataModel(image_data_list, many=True)
            if not image_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 3:
            response_data = GetAllAdjudicatorTattileDataModel(tattile_data_list, many=True)
            if not tattile_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid type",
                "data" : []
            }).data, status=200)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)
    

class GetAdjudicationDatesDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetAdjudicationDatesInputModel,
        responses={200: GetAllAdjudicationDatesDropDown(many=True)},
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetAdjudicationDatesInputModel(data=request.data)

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
        media_type = serializer.validated_data.get('mediaType')
        date_type = serializer.validated_data.get('dateType')
        
        if date_type == 1:
            check_date = 'captured_date'
        elif date_type == 2:
            check_date = 'datetime'
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid date type",
                "data": []
            }).data, status=400)
        if media_type == 1:
            citation_dates = Citation.objects.filter(
                station_id=station_id,
                isRemoved=False,
                isSendBack=False,
                video_id__isnull=False
            ).values_list(check_date, flat=True).all()
        elif media_type == 2:
            citation_dates = Citation.objects.filter(
                station_id=station_id,
                isRemoved=False,
                isSendBack=False,
                image_id__isnull=False
            ).values_list(check_date, flat=True).all()
        elif media_type == 3:
            citation_dates = Citation.objects.filter(
                station_id=station_id,
                isRemoved=False,
                isSendBack=False,
                tattile__isnull=False
            ).values_list(check_date, flat=True).all()
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid media type",
                "data": []
            }).data, status=400)

        grouped_dates = defaultdict(list)
        adjudication_dates = []

        for adjudication_date in citation_dates:
            if adjudication_date:
                date_str = adjudication_date.strftime("%B %#d, %Y")
                grouped_dates[date_str]

        for date_str in grouped_dates.keys():
            adjudication_dates.append({"date": date_str})

        response_dates = sorted(adjudication_dates,
                                key=lambda x: datetime.strptime(x["date"], '%B %d, %Y'))
        
        if not response_dates:
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No Content",
                "data": []
            }).data, status=200)
        
        response_data = GetAllAdjudicationDatesDropDown(response_dates, many=True)
        
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)
    

class GetAllCitationsIDsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetAllCitationIdsInputModel,
        responses={
            200: GetAllCitationIdsOutputModel(many=True),
            204: 'No Content'
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetAllCitationIdsInputModel(data=request.data)

        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get('stationId')
        media_type = serializer.validated_data.get('mediaType')
        request_date = serializer.validated_data.get('date')
        is_approved = serializer.validated_data.get('isApproved', None)
        is_rejected = serializer.validated_data.get('isRejected', None)
        date_type = serializer.validated_data.get('dateType',None)

        filtered_date = None
        if request_date:
            try:
                normalized_date = request_date.replace(',', ', ')
                parsed_date = datetime.strptime(normalized_date, "%B %d, %Y")
                filtered_date = parsed_date.date()
            except ValueError:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid date format. Expected 'Month Day, Year'."
                }).data, status=200)

        filters = {
            "station_id": station_id,
            "isSendBack": False,
            "isRemoved": False,
        }

        if filtered_date:
            if date_type == 1:
                filters["captured_date"] = filtered_date
            elif date_type == 2:
                filters["datetime__date"] = filtered_date
            else:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid date type",
                    "data": []
                }).data, status=400)

        if media_type == 1:
            filters["video_id__isnull"] = False
        elif media_type == 2:
            filters["image_id__isnull"] = False
        elif media_type == 3:
            filters["tattile_id__isnull"] = False
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid media type."
            }).data, status=200)

        if is_approved is not None:
            filters["isApproved"] = is_approved
            filters["isRejected"] = is_rejected

        citation_data = Citation.objects.filter(**filters).order_by('citationID')
        if not citation_data.exists():
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No Content",
                "data": []
            }).data, status=200)

        getAllCitationIdsOutputModel = [
            {"citationId": citation.id, "citationID": citation.citationID, "isApproved": citation.isApproved, "isRejected" : citation.isRejected, "isSendBack" : citation.isSendBack}
            for citation in citation_data
        ]
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": GetAllCitationIdsOutputModel(getAllCitationIdsOutputModel, many=True).data
        }).data, status=200)
    

class GetAllRejectedMediaDropDownView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        manual_parameters=[openapi.Parameter('mediaType',openapi.IN_QUERY,type=openapi.TYPE_INTEGER)],
        responses={200: GetAllRejectsOutputModel(many=True), 204: 'No Content'},
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        media_type = request.query_params.get('mediaType', None)

        try:
            media_type = int(media_type) if media_type is not None else 1
        except ValueError:
            return Response({"statusCode": 400, "message": "Invalid requestType. Must be an integer."}, status=400)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_id = readToken.get("stationId")
        agency_name = readToken.get("agencyName")
        
        if media_type==1:
            response_data = get_video_rejects(station_id)
            if response_data:
                return Response(ServiceResponse({"statusCode": 200, "message": "Success", "data": GetAllRejectsOutputModel(response_data,many=True).data}).data, status=200)
            else:
                return Response(ServiceResponse({"statusCode": 204, "message": "No content", "data": []}).data, status=200)
        elif media_type==2:
            response_data = get_image_rejects(station_id)
            if response_data:
                return Response(ServiceResponse({"statusCode": 200, "message": "Success", "data": GetAllRejectsOutputModel(response_data,many=True).data}).data, status=200)
            else:
                return Response(ServiceResponse({"statusCode": 204, "message": "No content", "data": []}).data, status=200)
        elif media_type==3:
            response_data = get_tattile_rejects(agency_name,station_id)
            if response_data:
                return Response(ServiceResponse({"statusCode": 200, "message": "Success", "data": GetAllRejectsOutputModel(response_data,many=True).data}).data, status=200)
            else:
                return Response(ServiceResponse({"statusCode": 204, "message": "No content", "data": []}).data, status=200)
        else:
            return Response(ServiceResponse({"statusCode": 400, "message": "Invalid Request Type", "data": []}).data, status=200)
        

class GetTrafficLogixDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: GetTrafficLogixLocationResponseModel(many=True)},
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def get(self,request):
        response_data = get_traffix_logix_client_ids()
        if response_data:
            return Response(ServiceResponse({
                "statusCode" : 200,
                "message" : "Success",
                "data" : GetTrafficLogixLocationResponseModel(response_data,many=True).data
            }).data, status=200)
        
        return Response(ServiceResponse({
            "statusCode" : 204,
            "message" : "No content",
            "data" : []
        }).data, status=200)
        
        
class GetOdrDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetOdrDropDownInputModel,
        responses={ 
            200: GetOdrAllCitationResponseModel(many=True),
            204: "No Content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetOdrDropDownInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)
        
        from_date = serializer.validated_data.get('fromDate')
        to_date = serializer.validated_data.get('toDate')
        is_approved = serializer.validated_data.get('isApproved')
        
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        
        try:
            odr_data = get_odr_citation(
                station_id=station_id,
                from_date=from_date,
                to_date=to_date,
                is_approved=is_approved
            )

            if odr_data is not None:
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "Success" if odr_data else "No data found",
                    "data": GetOdrAllCitationResponseModel(odr_data, many=True).data if odr_data else []
                }).data)

        except ValueError:
            return Response({
                "statusCode": 400,
                "message": "Invalid date format. Expected 'Month Day, Year'."
            }, status=400)
            
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "No data found",
            "data": []
        }).data, status=200)


class GetReviewBinViewMediaDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMediaDropDownInputModel,
        responses={ 
            200: GetAllReviewBinVideoDataModel(many=True),
            200: GetAllReviewBinImageDataModel(many=True),
            204: "No Content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        serializer = GetMediaDropDownInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)
        
        date = serializer.validated_data.get('date', None)
        data_type = serializer.validated_data.get('type')
        print('Hello Here')
        readToken = user_information(request)

        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        stationName = readToken.get('stationName')
        agency_name = readToken.get('agencyName')
        tattile_data_list = []

        if data_type == 1:
            # sent from adjudicator view
            filters_review_bin = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSentToReviewBin": True,
            }
            ## sent from supvisor view
            filters_review_bin_supervisor = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSent":True
            }
            ## sent from submission bin 
            filters_notfound = {
                "station_id": station_id,
                "is_notfound": True,
                "isRemoved": False,
                "isRejected": False,
            }
            filters_review_bin_data = get_video_data(filters_review_bin, agency_name, station_id)

            # Get videos directly from ReviewBin (separately)
            review_bin_ids = ReviewBin.objects.filter(
                (Q(is_notfound=True)| Q(is_adjudicated_in_review_bin=True)), video_id__isnull=False, station = stationName, is_notfound=True,
                is_rejected = False, is_sent_back_subbin = False
            ).values_list('video_id', flat=True)

            review_bin_videos = Video.objects.filter(id__in=review_bin_ids, isRejected = False,isRemoved = False).order_by('VIDEO_NO', 'id')
            review_bin_location_ids = review_bin_videos.values_list("location_id", flat=True)
            review_bin_locations = road_location.objects.filter(id__in=review_bin_location_ids)
            location_map = {loc.id: loc for loc in review_bin_locations}

            review_bin_data = [
                {
                    "id": video.id,
                    "label": f"{agency_name}_{location_map.get(video.location_id).location_name if video.location_id in location_map else None}_{video.datetime.date().strftime('%m%d%Y')}_{video.datetime.strftime('%I:%M:%S %p')}_{video.VIDEO_NO}",
                    "isRejected": video.isRejected or False,
                    "isAdjudicated": video.isAdjudicated,
                    "isSent": video.isSent,
                    "isSentToReviewBin": video.isSentToReviewBin,
                    "isNotFound": video.is_notfound,
                    "citationID": video.citation.citationID if video.citation else None
                }
                for video in review_bin_videos
            ]

            # Combine and remove duplicates by video ID
            combined_video_map = {}

            for item in filters_review_bin_data + review_bin_data:
                combined_video_map[item["id"]] = item

            video_data_list = list(combined_video_map.values())


            

        elif data_type == 2:
            filters_review_bin = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSentToReviewBin": True,
            }

            filters_notfound = {
                "station_id": station_id,
                "is_notfound": True,
                "isRemoved": False,
                "isRejected": False,
            }

            filters_review_bin_supervisor = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSent":True
            }

            data_sources = [
                get_image_data(agency_name, station_id)
            ]    
            review_bin_ids = set(
                ReviewBin.objects.filter(is_adjudicated_in_review_bin=True, image_id__isnull=False, station = stationName,is_rejected = False, is_sent_back_subbin = False)
                .values_list("image_id", flat=True)
            )
            if review_bin_ids:
                review_bin_images = Image.objects.filter(id__in=review_bin_ids, isRejected = False, isRemoved = False).order_by("id")
                image_location_ids = review_bin_images.values_list("location_id", flat=True)
                image_location_data = ImageLocation.objects.filter(location_id__in=image_location_ids)
                image_location_map = {location.location_id: location.name for location in image_location_data}
                
                review_bin_data = [
                    {
                        "id": image.id,
                        "label": f"{agency_name}_{image_location_map.get(image.location_id, 'Unknown')}_{image.time.date().strftime('%m%d%Y')}_{image.time.strftime('%I:%M %p')}_{image.custom_counter}",
                        "isRejected": image.isRejected or False,
                        "isAdjudicated": image.isAdjudicated,
                        "isSent": image.isSent,
                        "isSentToReviewBin": image.isSentToReviewBin,
                        "isNotFound": image.is_notfound,
                        "citationID": image.citation.citationID if image.citation else None
                    }
                    for image in review_bin_images
                ]
                data_sources.append(review_bin_data)
                
            print(len(data_sources), 'data sources len 2') 
            seen_ids = set()
            image_data_list = []

            for source in data_sources:
                for item in source:
                    if item["id"] not in seen_ids:
                        seen_ids.add(item["id"])
                        image_data_list.append(item)
                    
        elif data_type == 3:
            filters_review_bin = {
                "station_id": station_id,
                "is_rejected": False,
                "is_removed": False,
                "is_sent_to_review_bin": True,
            }

            filters_notfound = {
                "station_id": station_id,
                "is_not_found": True,
                "is_removed": False,
                "is_rejected": False,
            }

            filters_review_bin_supervisor = {
                "station_id": station_id,
                "is_rejected": False,
                "is_removed": False,
                "is_sent":True
            }

            data_sources = [
                get_tattile_data(agency_name,station_id)
            ]

                 
            review_bin_ids = set(
                ReviewBin.objects.filter((Q(is_notfound=True)| Q(is_adjudicated_in_review_bin=True)), tattile_id__isnull=False, station = stationName, is_rejected = False, is_sent_back_subbin = False)
                .values_list("tattile_id", flat=True)
            )
            if review_bin_ids:
                review_bin_images = Tattile.objects.filter(id__in=review_bin_ids, is_rejected = False, is_removed = False, is_active = True).order_by("image_time", "id")
                tattile_location_ids = review_bin_images.values_list("location_id", flat=True)
                location_map = {loc.id: loc for loc in road_location.objects.filter(id__in=tattile_location_ids)}
                
                review_bin_data = [
                    {
                        "id": image.id,
                        "label": f"{agency_name}_{location_map.get(image.location_id).location_name if image.location_id in location_map else None}_{image.image_time.date().strftime('%m%d%Y')}_{image.image_time.strftime('%I:%M:%S %p')}",
                        "isRejected": image.is_rejected or False,
                        "isAdjudicated": image.is_adjudicated,
                        "isSent": image.is_sent,
                        "isSentToReviewBin": image.is_sent_to_review_bin,
                        "isNotFound": image.is_not_found,
                        "citationID": image.citation_id if image.citation_id else None
                    }
                    for image in review_bin_images
                ]
                data_sources.append(review_bin_data)
                
            print(len(data_sources), 'data sources len 2') 
            seen_ids = set()
            image_data_list = []

            for source in data_sources:
                for item in source:
                    if item["id"] not in seen_ids:
                        seen_ids.add(item["id"])
                        image_data_list.append(item)

        if data_type == 1:
            response_data = GetAllReviewBinVideoDataModel(video_data_list, many=True)
            if not video_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 2:
            response_data = GetAllReviewBinImageDataModel(image_data_list, many=True)
            if not image_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 3:
            response_data = GetAllReviewBinImageDataModel(image_data_list, many=True)
            if not image_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid type",
                "data" : []
            }).data, status=200)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)
    

class GetAgencyAdjudicationMediaDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMediaDropDownInputModel,
        responses={ 
            200: GetAllAgencyAdjudicationVideoDataModel(many=True),
            200: GetAllAgencyAdjudicationImageDataModel(many=True),
            204: "No Content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetMediaDropDownInputModel(data=request.data)
        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)
        
        date = serializer.validated_data.get('date', None)
        data_type = serializer.validated_data.get('type')

        readToken = user_information(request)

        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')
        agency_name = readToken.get('agencyName')

        if data_type == 1:
            agency_adjudication_bin_videos = AdjudicationBin.objects.filter(
                station=station_name,
                video_id__isnull=False,
                is_rejected = False
            )
            agency_adjudication_video_ids = agency_adjudication_bin_videos.values_list("video_id", flat=True)
            agency_adjudication_videos = Video.objects.filter(id__in=agency_adjudication_video_ids , isRemoved = False, isRejected = False).order_by('VIDEO_NO', 'id')
            agency_adjudication_videos_location_ids = agency_adjudication_videos.values_list("location_id", flat=True)
            agency_adjudication_videos_location_idsbin_locations = road_location.objects.filter(id__in=agency_adjudication_videos_location_ids)
            location_map = {loc.id: loc for loc in agency_adjudication_videos_location_idsbin_locations}

            agency_adjudication_data_list = [
                {
                    "id": agency_adjudication_bin_video.video_id,
                    "label": f"{agency_name}__{location_map.get(agency_adjudication_bin_video.video.location_id).location_name if agency_adjudication_bin_video.video.location_id in location_map else None}_{agency_adjudication_bin_video.video_id}_{agency_adjudication_bin_video.video.datetime.date().strftime('%m%d%Y')}_{agency_adjudication_bin_video.video.datetime.strftime('%I:%M:%S %p')}_{agency_adjudication_bin_video.video.VIDEO_NO}",
                    "isRejectedInAgnecyAdjudicationBin": agency_adjudication_bin_video.is_rejected,
                    "isAdjudicatedInAgencyAdjudicationBin": agency_adjudication_bin_video.is_adjudicated_in_adjudicationbin,
                    "citationID": agency_adjudication_bin_video.video.citation.citationID if agency_adjudication_bin_video.video.citation else None,
                    "isSent": agency_adjudication_bin_video.video.isSent
                }
                for agency_adjudication_bin_video in agency_adjudication_bin_videos
                if not agency_adjudication_bin_video.video.isRemoved
            ]


        if data_type == 2:
            agency_adjudication_bin_images = AdjudicationBin.objects.filter(
                station=station_name,
                image_id__isnull=False,
                is_rejected = False
            )
            agency_adjudication_image_ids = agency_adjudication_bin_images.values_list("image_id", flat=True)
            agency_adjudication_images = Image.objects.filter(id__in=agency_adjudication_image_ids, isRemoved = False, isRejected = False).order_by('id')
            agency_adjudication_images_location_ids = agency_adjudication_images.values_list("location_id", flat=True)
            image_location_data = ImageLocation.objects.filter(location_id__in=agency_adjudication_images_location_ids)
            image_location_map = {loc.location_id: loc.name for loc in image_location_data}


            agency_adjudication_data_list = [
                {
                    "id": agency_adjudication_bin_image.image_id,
                    "label": f"{agency_name}_{image_location_map.get(agency_adjudication_bin_image.image.location_id, 'Unknown')}_{agency_adjudication_bin_image.image.time.date().strftime('%m%d%Y')}_{agency_adjudication_bin_image.image.time.strftime('%I:%M %p')}_{agency_adjudication_bin_image.image.custom_counter}",
                    "isRejectedInAgnecyAdjudicationBin": agency_adjudication_bin_image.is_rejected,
                    "isAdjudicatedInAgencyAdjudicationBin": agency_adjudication_bin_image.is_adjudicated_in_adjudicationbin,
                    "citationID": agency_adjudication_bin_image.image.citation.citationID if agency_adjudication_bin_image.image.citation else None,
                    "isSent": agency_adjudication_bin_image.image.isSent 
 
             }
                for agency_adjudication_bin_image in agency_adjudication_bin_images
                if not agency_adjudication_bin_image.image.isRemoved
            ]

        if data_type == 3:
            agency_adjudication_bin_videos = AdjudicationBin.objects.filter(
                station=station_name,
                tattile_id__isnull=False,
                is_rejected = False
            )
            agency_adjudication_video_ids = agency_adjudication_bin_videos.values_list("tattile_id", flat=True)
            agency_adjudication_videos = Tattile.objects.filter(id__in=agency_adjudication_video_ids , is_removed = False, is_rejected = False, is_active = True).order_by('image_time', 'id')
            agency_adjudication_videos_location_ids = agency_adjudication_videos.values_list("location_id", flat=True)
            agency_adjudication_videos_location_idsbin_locations = road_location.objects.filter(id__in=agency_adjudication_videos_location_ids)
            location_map = {loc.id: loc for loc in agency_adjudication_videos_location_idsbin_locations}

            agency_adjudication_data_list = [
                {
                    "id": agency_adjudication_bin_video.tattile_id,
                    "label": f"{agency_name}_{location_map.get(agency_adjudication_bin_video.tattile.location_id).location_name if agency_adjudication_bin_video.tattile.location_id in location_map else None}_{agency_adjudication_bin_video.tattile_id}_{agency_adjudication_bin_video.tattile.image_time.date().strftime('%m%d%Y')}_{agency_adjudication_bin_video.tattile.image_time.strftime('%I:%M:%S %p')}",
                    "isRejectedInAgnecyAdjudicationBin": agency_adjudication_bin_video.is_rejected,
                    "isAdjudicatedInAgencyAdjudicationBin": agency_adjudication_bin_video.is_adjudicated_in_adjudicationbin,
                    "citationID": agency_adjudication_bin_video.tattile.citation_id if agency_adjudication_bin_video.tattile.citation_id else None,
                    "isSent": agency_adjudication_bin_video.tattile.is_sent
                }
                for agency_adjudication_bin_video in agency_adjudication_bin_videos
                if not agency_adjudication_bin_video.tattile.is_removed
            ]

        if data_type == 1:
            response_data = GetAllAgencyAdjudicationVideoDataModel(agency_adjudication_data_list, many=True)
            if not agency_adjudication_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 2:
            response_data = GetAllAgencyAdjudicationImageDataModel(agency_adjudication_data_list, many=True)
            if not agency_adjudication_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        elif data_type == 3:
            response_data = GetAllAgencyAdjudicationImageDataModel(agency_adjudication_data_list, many=True)
            if not agency_adjudication_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)   
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid type",
                "data" : []
            }).data, status=200)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)
    

class GetAllYearsDropDownForPreOdrView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        responses={
            200: GetAllYearsForPreOdrResponseModel(many=True),
            204: "No content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get('stationId')

        unpaid_citation_years = UnpaidCitation.objects.filter(
            station_id=station_id,
            arr_date__isnull=False,
            is_deleted=False
        ).values_list('arr_date', flat=True)
        unique_years = sorted({int(date.year) for date in unpaid_citation_years})

        if not unique_years:
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No content",
                "data": []
            }).data, status=200)
        year_data = [{"year": y} for y in unique_years]

        serializer = GetAllYearsForPreOdrResponseModel(year_data, many=True)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": serializer.data
        }).data, status=200)


class GetAllMonthsDropDownForPreOdrView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=GetAllMonthsForPreOdrInputModel,
        responses={
            200: GetAllMonthsForPreOdrResponseModel(many=True),
            204: "No content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        serializer = GetAllMonthsForPreOdrInputModel(data=request.data)

        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data,status=400)
        year = serializer.validated_data.get('year')
        station_id = readToken.get('stationId')

        unpaid_citation_months = UnpaidCitation.objects.filter(
            station_id=station_id,
            arr_date__isnull=False,
            arr_date__year=int(year),
            is_deleted=False,
        ).values_list('arr_date', flat=True)

        unique_months = sorted({int(date.month) for date in unpaid_citation_months})

        if not unique_months:
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No content",
                "data": []
            }).data, status=200)
        month_data = [
            {"month": m, "monthName": calendar.month_name[m]}
            for m in unique_months
        ]
        serializer = GetAllMonthsForPreOdrResponseModel(month_data, many=True)
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": serializer.data
        }).data, status=200)
    

class GetAllDaysDropDownForPreOdrView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=GetAllDaysForPreOdrInputModel,
        responses={
            200: GetAllDaysForPreOdrResponseModel(many=True),
            204: "No content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        serializer = GetAllDaysForPreOdrInputModel(data=request.data)

        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data,status=400)
        year = serializer.validated_data.get('year')
        month = serializer.validated_data.get('month')
        station_id = readToken.get('stationId')

        unpaid_citation_months = UnpaidCitation.objects.filter(
            station_id=station_id,
            arr_date__isnull=False,
            arr_date__year=int(year),
            arr_date__month=int(month),
            is_deleted=False,
        ).values_list('arr_date', flat=True)

        unique_days = sorted({int(date.day) for date in unpaid_citation_months})

        if not unique_days:
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No content",
                "data": []
            }).data, status=200)
        days_data = [
            {"day": d}
            for d in unique_days
        ]
        serializer = GetAllDaysForPreOdrResponseModel(days_data, many=True)
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": serializer.data
        }).data, status=200)


class GetAllCitationsForPreOdrView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=GetAllPreOdrCitationIdsInputModel,
        responses={
            200: GetAllCitationIdsOutputModel,
            204: "No content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        serializer = GetAllPreOdrCitationIdsInputModel(data=request.data)

        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data,status=400)
        
        stationId = readToken.get("stationId")
    
        extracted_input_fields = extract_input_fields_for_pre_odr_view(serializer.validated_data)

        citation_response_data = get_pre_odr_view_citations(extracted_input_fields,stationId)
        
        citations=citation_response_data['data']
        total_records = citation_response_data['total_records']
        page_index = extracted_input_fields.get('pageIndex')
        page_size = extracted_input_fields.get('pageSize')
        
        paged_response = PagedResponse(
            page_index=page_index,
            page_size=page_size,
            total_records=total_records,
            data=citations
        )
        response_data = {
            "data": paged_response.data,
            "pageIndex": paged_response.pageIndex,
            "pageSize": paged_response.pageSize,
            "totalRecords": paged_response.totalRecords,
            "hasNextPage": paged_response.hasNextPage,
            "hasPreviousPage": paged_response.hasPreviousPage,
            "statusCode": 200,
            "message": "Success"
        }
        
        if not citation_response_data:
            return Response(ServiceResponse({
                "statusCode" : 204,
                "message" : "No content",
                "data" : []
            }).data ,status=200)
        
        return Response(response_data)
    
    
class GetAllPermissionLevelView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'agencyId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: GetAllPermissionLevelResponseModel,
            204: "No content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        agency_id = request.query_params.get('agencyId', None)

        try:
            agency_id = int(agency_id) if agency_id is not None else readToken.get("agencyId")
        except ValueError:
            return Response({
                "statusCode": 400,
                "message": "Invalid requestType. Must be an integer."
            }, status=400)
        
        if agency_id == 1:
            response_data = {
                "permissions": 
                {
                    "isAdjudicator" : "Adjudicator",
                    "isSupervisor" : "Supervisor",
                    "isApprovedTableView" : "Approved Table",
                    "isRejectView" : "Reject View",
                    "isCourtPreview" : "Court Preview",
                    "isCSVView" :  "CSV View",
                    "isAddUserView" : "Add User",
                    "isAddRoadLocationView" : "Road Locations",
                    "isEditFineView" : "Edit Fine",
                    "isAddCourtDate" : "Add Court Date",
                    "isViewReportView" : "View Report",
                    "isPreODRView" : "Pre ODR",
                    "isODRView" : "ODR"
                }
            }
        else:
            response_data = {
                "permissions": 
                {
                    "isSubmissionView" : "Submissions",
                    "isAgencyAdjudicationBinView" : "Agency Adjudication Bin",
                    "isReviewBinView" : "Review Bin",
                    "isAdjudicator" : "Adjudicator",
                    "isSupervisor" : "Supervisor",
                    "isApprovedTableView" : "Approved Table",
                    "isRejectView" : "Reject View",
                    "isCourtPreview" : "Court Preview",
                    "isCSVView" :  "CSV View",
                    "isAddUserView" : "Add User",
                    "isAddRoadLocationView" : "Road Locations",
                    "isEditFineView" : "Edit Fine",
                    "isAddCourtDate" : "Add Court Date",
                    "isViewReportView" : "View Report",
                    "isReminderView" : "Reminder View",
                    # "isTotalTicket" : "Total Ticket",
                    # "isDailyReport" : "Daily Report"
                }
            }

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": GetAllPermissionLevelResponseModel(response_data).data
        }).data, status=200)

class GetFineAmountDropDownView(APIView):
    permission_classes=[AllowAny]
    @swagger_auto_schema(
        responses={200: FineDropDownModel(many=True),
                   204: "No Content"},
        tags=['DropDown'],
    )
    def get(self, request):
        
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        
        fine_amount = Citation.objects.filter(station_id=station_id).values("fine_amount").distinct()

        if not fine_amount.exists():
            return Response(ServiceResponse({
            "statusCode": 204,
            "message": "No Content",
            "data": []
        }).data,status=200)

        serializer = FineDropDownModel(fine_amount, many=True)
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": serializer.data
        }).data,status=200)
    

class GetSeventyPlusTicketsDropdownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMediaDropDownInputModel,
        responses={ 
            200: GetAllVideoDataModel(many=True),
            200: GetAllTattileDataModel(many=True),
            204: "No Content"
        },
        tags=['DropDown'],
        security=[{'Bearer': []}]
    )

    def post(self, request):
        serializer = GetMediaDropDownInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }, status=400)
        
        date = serializer.validated_data.get('date')
        data_type = serializer.validated_data.get('type')
        filtered_date = None
        if date:
            try:
                normalized_date = date.replace(',', ', ')
                parsed_date = datetime.strptime(normalized_date, "%B %d, %Y")
                filtered_date = parsed_date.strftime("%Y-%m-%d")
                print("Filtered Date:", filtered_date)
            except ValueError:
                return Response({
                    "statusCode": 400,
                    "message": "Invalid date format. Expected 'Month Day, Year'."
                }, status=400)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')
        agency_id = readToken.get('agencyId')
        state_id = readToken.get('stateId')
        state_name = readToken.get('stateName')
        agency_name = readToken.get('agencyName')

        cutoff_date = datetime(2025, 5, 10)

        get_agency_state_rs = Agency.objects.filter(id=agency_id).values_list('state_rs', flat=True).first()
        state_ab = State.objects.filter(id=state_id).values_list('ab', flat=True).first()  
        video_data_list = []
        image_data_list = []
        tattile_data_list = []

        if data_type == 1:
            video_filters = {
                "station_id": station_id,
                "isRejected": False,  
                "isAdjudicated": False,
                "isRemoved": False,
                "isSent": False,
                "is_notfound": False,
                "speed__gte": 70,
                "datetime__date__gte": cutoff_date.date(),
            }
            
            excluded_video_ids = DuncanSubmission.objects.filter(
                Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                station=station_name
            ).values_list("video_id", flat=True)
            adjudication_video_ids = AdjudicationBin.objects.filter(
                video_id__isnull=False,
                station=station_name
            ).values_list('video_id', flat=True)
            exclude_videos = list(adjudication_video_ids) + list(excluded_video_ids)
            # Get all eligible videos, excluding the ones above
            videoData = Video.objects.filter(**video_filters).exclude(id__in=exclude_videos).order_by("VIDEO_NO", "id")

            # Get location mapping
            video_location_ids = videoData.values_list("location_id", flat=True)
            road_location_data = road_location.objects.filter(id__in=video_location_ids)
            location_map = {location.id: location for location in road_location_data}

            # If needed, map any duncan submissions to these videos
            duncan_submission_data = DuncanSubmission.objects.filter(video_id__in=videoData.values_list("id", flat=True))
            duncan_map = {submission.video_id: submission for submission in duncan_submission_data}
            review_bin_data =  ReviewBin.objects.filter(video_id__in=videoData.values_list("id", flat=True), is_sent_back_subbin = True)
            review_bin_map = {reviewbin.video_id: reviewbin for reviewbin in review_bin_data}

            video_data_list = [
                {
                    "id": video.id,
                    "label": f"{agency_name}_{location_map.get(video.location_id).location_name if video.location_id in location_map else 'Unknown'}_{video.datetime.date().strftime('%m%d%Y')}_{video.datetime.strftime('%I:%M:%S %p')}_{video.VIDEO_NO}",
                    "isRejected": video.isRejected,
                    "isSubmitted": duncan_map.get(video.id).isSubmitted if video.id in duncan_map else False,
                    "isSkipped": duncan_map.get(video.id).isSkipped if video.id in duncan_map else False,
                    "isAdjudicated": video.isAdjudicated,
                    "isUnknown": duncan_map.get(video.id).is_unknown if video.id in duncan_map else False,
                    "isSentBackSubbin" : review_bin_map.get(video.id).is_sent_back_subbin if video.id in review_bin_map else False
                }
                for video in videoData
            ]

        elif data_type == 3:
            tattile_filters = {
                "is_rejected": False,
                "is_adjudicated": False,
                "is_removed": False,
                "is_sent": False,
                "is_not_found": False,
                "is_active" :True,
                "station_id" : station_id,
                "measured_speed__gte" : 70,
                "image_time__date__gte": cutoff_date.date()
            }

            # Get all image IDs that were already adjudicated or marked not found
            excluded_tattile_ids = DuncanSubmission.objects.filter(
                Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                station=station_name
            ).values_list("tattile_id", flat=True).exclude(tattile_id__isnull=True)
            adjudication_tattile_ids = AdjudicationBin.objects.filter(
                tattile_id__isnull=False,
                station=station_name
            ).values_list('tattile_id', flat=True)
            exclude_tattile = list(adjudication_tattile_ids) + list(excluded_tattile_ids)
            # Filter image data with the same filters as old code
            tattileData = Tattile.objects.filter(**tattile_filters) \
                             .exclude(id__in=exclude_tattile) \
                             .order_by("image_time")

            tattile_location_ids = tattileData.values_list("location_id", flat=True)
            road_location_data = road_location.objects.filter(id__in=tattile_location_ids)
            location_map = {location.id: location for location in road_location_data}

            # Optional: load submission data if needed for display
            submission_data = DuncanSubmission.objects.filter(tattile_id__in=tattileData.values_list("id", flat=True))
            duncan_map = {submission.tattile_id: submission for submission in submission_data}
            review_bin_data = ReviewBin.objects.filter(tattile_id__in=tattileData.values_list("id", flat=True),is_sent_back_subbin =  True)
            review_bin_map = {submission.tattile_id: submission for submission in review_bin_data}

            tattile_data_list = [
                {
                    "id": tattile.id,
                    "label": f"{agency_name}_{location_map[tattile.location_id].location_name if tattile.location_id in location_map else None}_{tattile.image_time.date().strftime('%m%d%Y')}_{tattile.image_time.strftime('%I:%M:%S %p')}",
                    "isRejected": tattile.is_rejected,
                    "isSubmitted": duncan_map.get(tattile.id).isSubmitted if tattile.id in duncan_map else None,
                    "isSkipped": duncan_map.get(tattile.id).isSkipped if tattile.id in duncan_map else None,
                    "isAdjudicated": tattile.is_adjudicated,
                    "isUnknown": duncan_map.get(tattile.id).is_unknown if tattile.id in duncan_map else None,
                    "isSentBackSubbin" : review_bin_map.get(tattile.id).is_sent_back_subbin if tattile.id in review_bin_map else False
                }
                for tattile in tattileData
            ]
        
        if data_type == 1:
            response_data = GetAllVideoDataModel(video_data_list, many=True)
            if not video_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
            
        
        elif data_type == 3:
            response_data = GetAllTattileDataModel(tattile_data_list, many=True)
            if not tattile_data_list:
                return Response(ServiceResponse({
                    "statusCode": 204,
                    "message": "No content",
                    "data": []
                }).data, status=200)
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": response_data.data
        }).data, status=200)
        
class GetEvidenceCalibrationMediaDropDownView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("mediaType", openapi.IN_QUERY, type=openapi.TYPE_INTEGER)
        ],
        responses={200: GetAllRejectsOutputModel(many=True), 204: "No Content"},
        tags=["DropDown"],
        security=[{"Bearer": []}],
    )
    def get(self, request):

        media_type = request.query_params.get("mediaType", None)

        try:
            media_type = int(media_type) if media_type is not None else 1
        except ValueError:
            return Response(
                {
                    "statusCode": 400,
                    "message": "Invalid requestType. Must be an integer.",
                },
                status=400,
            )

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")
        agency_name = readToken.get("agencyName")

        if media_type == 1:
            response_data = get_rejects_evidence(agency_name, station_id, media_type=1)
            if response_data:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 200,
                            "message": "Success",
                            "data": GetAllRejectsOutputModel(
                                response_data, many=True
                            ).data,
                        }
                    ).data,
                    status=200,
                )
            else:
                return Response(
                    ServiceResponse(
                        {"statusCode": 204, "message": "No content", "data": []}
                    ).data,
                    status=200,
                )
        elif media_type == 2:
            response_data = get_rejects_evidence(agency_name, station_id, media_type=2)
            if response_data:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 200,
                            "message": "Success",
                            "data": GetAllRejectsOutputModel(
                                response_data, many=True
                            ).data,
                        }
                    ).data,
                    status=200,
                )
            else:
                return Response(
                    ServiceResponse(
                        {"statusCode": 204, "message": "No content", "data": []}
                    ).data,
                    status=200,
                )
        elif media_type == 3:
            response_data = get_rejects_evidence(agency_name, station_id, media_type=3)
            if response_data:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 200,
                            "message": "Success",
                            "data": GetAllRejectsOutputModel(
                                response_data, many=True
                            ).data,
                        }
                    ).data,
                    status=200,
                )
            else:
                return Response(
                    ServiceResponse(
                        {"statusCode": 204, "message": "No content", "data": []}
                    ).data,
                    status=200,
                )
        else:
            return Response(
                ServiceResponse(
                    {"statusCode": 400, "message": "Invalid Request Type", "data": []}
                ).data,
                status=200,
            )
        
