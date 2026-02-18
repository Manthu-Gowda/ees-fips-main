from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import *
from accounts_v2.serializer import ServiceResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from ees.utils import user_information
from dashboard_view.dashboard_view_utils import *
from video.models import DuncanSubmission, AdjudicationBin, Video, Image, Tattile, ReviewBin,Citation
from dropdown.drop_down_utils import get_image_ids, get_video_ids, get_tattile_ids


class GetDashBoardDataView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body= GetDashBoardDataInputModel,
        responses={200: GetDashBoardDataResponseModel},
        tags=['DashBoard'],
        security=[{'Bearer': []}] 
    )
    def post(self, request):
        serializer = GetDashBoardDataInputModel(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data": serializer.errors}).data, status=200)
        serializer_data = serializer.validated_data

        from_date = serializer_data.get('fromDate')
        to_date = serializer_data.get('toDate')
        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')
        response = get_dashboard_data(from_date, to_date, station_id,station_name)

        return Response(ServiceResponse({"statusCode" : 200, "message" : 200, "data" : GetDashBoardDataResponseModel(response).data}).data, status=200)
    

class GetAllMediaCountView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=["DashBoard"], security=[{"Bearer": []}])
    def get(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")
        print(station_id)
        station_name = readToken.get("stationName")
        print(station_name)
        agency_name = readToken.get("agencyName")
        print("station_id", station_id, "station_name", station_name)
        try:
            # 1 submission video,image,tattile count
            video_filters = {
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
            tattile_filters = {
                "station_id": station_id,
                "is_rejected": False,
                "is_adjudicated": False,
                "is_removed": False,
                "is_sent": False,
                "is_not_found": False,
                "is_active": True
            }
            # Get video IDs already handled (to exclude)
            excluded_video_ids = DuncanSubmission.objects.filter(
                Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                station=station_name
            ).values_list("video_id", flat=True)
            
            adjudication_video_ids = AdjudicationBin.objects.filter(
                video_id__isnull=False, station=station_name
            ).values_list("video_id", flat=True)
            exclude_videos = list(adjudication_video_ids) + list(excluded_video_ids)
            
            # Get all eligible videos, excluding the ones above
            submission_video_ticket_count = Video.objects.filter(**video_filters).exclude(id__in=exclude_videos).count()
            
            # Get all image IDs that were already adjudicated or marked not found
            excluded_image_ids = DuncanSubmission.objects.filter(
                Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                station=station_name,
            ).values_list("image_id", flat=True)
            adjudication_image_ids = AdjudicationBin.objects.filter(
                image_id__isnull=False, station=station_name
            ).values_list("image_id", flat=True)
            exclude_images = list(adjudication_image_ids) + list(excluded_image_ids)
            # Filter image data with the same filters as old code
            submission_image_ticket_count = (
                Image.objects.filter(**image_filters)
                .exclude(id__in=exclude_images)
                .count()
            )

            # Get all image IDs that were already adjudicated or marked not found
            excluded_tattile_ids = (
                DuncanSubmission.objects.filter(
                    Q(is_sent_to_adjudication=True) | Q(is_notfound=True),
                    station=station_name,
                )
                .values_list("tattile_id", flat=True)
                .exclude(tattile_id__isnull=True)
            )
            adjudication_tattile_ids = AdjudicationBin.objects.filter(
                tattile_id__isnull=False, station=station_name
            ).values_list("tattile_id", flat=True)
            exclude_tattile = list(adjudication_tattile_ids) + list(
                excluded_tattile_ids
            )
            # Filter image data with the same filters as old code
            submission_tattile_ticket_count = (
                Tattile.objects.filter(**tattile_filters)
                .exclude(id__in=exclude_tattile)
                .distinct("image_time")
                .count()
            )
            # 2  adjudicator  video,image,tattile count
            video_video_filters = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSentToReviewBin": False,
                "is_notfound": False,
            }
            if station_id in [35,38,39, 42, 44,53,57,69,70,71]:
                duncan_submission = DuncanSubmission.objects.filter(station=station_name,is_sent_to_adjudication=True, isRejected= False)
                duncan_submission_video_ids = duncan_submission.values_list("video_id", flat=True)

                adjudicator_video_ticket_count = Video.objects.filter(id__in=duncan_submission_video_ids, isSent = False,isSentToReviewBin = False, isRemoved = False, isRejected= False).count()
            else:
                adjudicator_video_ticket_count =Video.objects.filter(**video_video_filters).count()

            image_filters = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSentToReviewBin": False,
                "is_notfound": False,
            }

            # if station_id in [35,38,39]:
            if station_id in [35, 38, 39, 42, 44,53,57]:
                duncan_submission = DuncanSubmission.objects.filter(
                    station=station_name, is_sent_to_adjudication=True
                )
                duncan_submission_image_ids = duncan_submission.values_list(
                    "image_id", flat=True
                )

                adjudicator_image_ticket_count = Image.objects.filter(
                    id__in=duncan_submission_image_ids,
                    isSent=False,
                    isSentToReviewBin=False,
                ).count()
            else:
                adjudicator_image_ticket_count = Image.objects.filter(
                    **image_filters
                ).count()

            tattile_filters = {
                "station_id": station_id,
                "is_rejected": False,
                "is_removed": False,
                "is_sent_to_review_bin": False,
                "is_not_found": False,
                "is_active" : True
            }

            # if station_id in [35,38,39]:
            if station_id in [35, 38, 39, 42, 44,53,57]:
                duncan_submission = DuncanSubmission.objects.filter(
                    station=station_name, is_sent_to_adjudication=True, isRejected=False
                )
                duncan_submission_tattile_ids = duncan_submission.values_list(
                    "tattile_id", flat=True
                )

                adjudicator_tattile_ticket_count = Tattile.objects.filter(
                    id__in=duncan_submission_tattile_ids,
                    is_sent=False,
                    is_sent_to_review_bin=False,
                    is_removed=False,
                    is_rejected=False,
                    is_active = True
                ).count()
            else:
                adjudicator_tattile_ticket_count = Tattile.objects.filter(
                    **tattile_filters
                ).count()
            # 3 reviewbin video,image,tattile count
            # sent from adjudicator view
            filters_review_bin = {
                "station_id": station_id,
                "isRejected": False,
                "isRemoved": False,
                "isSentToReviewBin": True,
            }
            filters_review_bin_video_ids = get_video_ids(filters_review_bin, station_id)
            # Get videos directly from ReviewBin (separately)
            review_bin_ids = ReviewBin.objects.filter(
                (Q(is_notfound=True)| Q(is_adjudicated_in_review_bin=True)), video_id__isnull=False, station = station_name, is_notfound=True,
                is_rejected = False, is_sent_back_subbin = False
            ).values_list('video_id', flat=True)
            combined_video_ids = set(filters_review_bin_video_ids) | set(review_bin_ids)
            review_bin_video_ticket_count = Video.objects.filter(
                id__in=combined_video_ids, isRejected=False, isRemoved=False
            ).count()
            # seen IDs set to ensure uniqueness
            seen_ids = set()

            # from utils.py
            seen_ids.update(get_image_ids(station_id))

            # from review bin
            review_bin_ids = ReviewBin.objects.filter(
                image_id__isnull=False,
                station=station_name,
                is_rejected=False,
                is_sent_back_subbin=False,
            ).values_list("image_id", flat=True)

            valid_review_bin_ids = Image.objects.filter(
                id__in=review_bin_ids, isRejected=False, isRemoved=False
            ).values_list("id", flat=True)

            seen_ids.update(valid_review_bin_ids)

            # final count
            review_bin_image_ticket_count = len(seen_ids)

            # collect tattile IDs from utils
            tattile_ids = get_tattile_ids(station_id)

            # from review bin
            review_bin_ids = set(
                ReviewBin.objects.filter((Q(is_notfound=True)| Q(is_adjudicated_in_review_bin=True)), tattile_id__isnull=False, station = station_name, is_rejected = False, is_sent_back_subbin = False)
                .values_list("tattile_id", flat=True)
            )

            # ensure valid tattile rows
            valid_review_bin_ids = Tattile.objects.filter(id__in=review_bin_ids, is_rejected = False, is_removed = False, is_active=True).values_list("id", flat=True)

            # unique merge
            combined_ids = set(tattile_ids) | set(valid_review_bin_ids)

            # final count
            review_bin_tattile_ticket_count = len(combined_ids)


            # 4 agency adjudication bin video,image,tattile count
            agency_adjudication_bin_videos = AdjudicationBin.objects.filter(
                station=station_name,
                video_id__isnull=False,
                is_rejected = False
            )
            agency_adjudication_video_ids = agency_adjudication_bin_videos.values_list("video_id", flat=True)
            agency_adjudication_videos = Video.objects.filter(id__in=agency_adjudication_video_ids , isRemoved = False, isRejected = False).order_by('VIDEO_NO', 'id')
            

            agency_adjudication_data_list = [
                {
                    "id": agency_adjudication_bin_video.video_id
                }
                for agency_adjudication_bin_video in agency_adjudication_bin_videos
                if not agency_adjudication_bin_video.video.isRemoved
            ]

            agency_adjudication_video_ticket_count = len(agency_adjudication_data_list)
            # image
            agency_adjudication_bin_images = AdjudicationBin.objects.filter(
                station=station_name, image_id__isnull=False, is_rejected=False
            )
            agency_adjudication_image_ids = agency_adjudication_bin_images.values_list(
                "image_id", flat=True
            )
            agency_adjudication_image_ticket_count = Image.objects.filter(
                id__in=agency_adjudication_image_ids, isRemoved=False, isRejected=False
            ).count()
            # tattile
            agency_adjudication_bin_videos = AdjudicationBin.objects.filter(
                station=station_name, tattile_id__isnull=False, is_rejected=False
            )
            agency_adjudication_video_ids = agency_adjudication_bin_videos.values_list(
                "tattile_id", flat=True
            )
            agency_adjudication_tattile_ticket_count = Tattile.objects.filter(
                id__in=agency_adjudication_video_ids,
                is_removed=False,
                is_rejected=False,
                is_active = True
            ).count()

            # 5 citation data(super view) count based on video,image,tattile
            # video
            filters = {
                "station_id": station_id,
                "isSendBack": False,
                "isRemoved": False,
                "isApproved": False,
                "isRejected": False,
                "video_id__isnull": False,
            }
            super_view_video_ticket_count = Citation.objects.filter(**filters).count()
            # image
            filters = {
                "station_id": station_id,
                "isSendBack": False,
                "isRemoved": False,
                "isApproved": False,
                "isRejected": False,
                "image_id__isnull": False,
            }
            super_view_image_ticket_count = Citation.objects.filter(**filters).count()
            # tattile
            filters = {
                "station_id": station_id,
                "isSendBack": False,
                "isRemoved": False,
                "isApproved": False,
                "isRejected": False,
                "tattile_id__isnull": False,
            }
            super_view_tattile_ticket_count = Citation.objects.filter(**filters).count()

            response_data = {
                "submissionVideoTicketCount": submission_video_ticket_count,
                "submissionImageTicketCount": submission_image_ticket_count,
                "submissionTattileTicketCount": submission_tattile_ticket_count,
                "adjudicatorVideoTicketCount": adjudicator_video_ticket_count,
                "adjudicatorImageTicketCount": adjudicator_image_ticket_count,
                "adjudicatorTattileTicketCount": adjudicator_tattile_ticket_count,
                "reviewBinVideoTicketCount": review_bin_video_ticket_count,
                "reviewBinImageTicketCount": review_bin_image_ticket_count,
                "reviewBinTattileTicketCount": review_bin_tattile_ticket_count,
                "agencyAdjudicationVideoTicketCount": agency_adjudication_video_ticket_count,
                "agencyAdjudicationImageTicketCount": agency_adjudication_image_ticket_count,
                "agencyAdjudicationTattileTicketCount": agency_adjudication_tattile_ticket_count,
                "superViewVideoTicketCount": super_view_video_ticket_count,
                "superViewImageTicketCount": super_view_image_ticket_count,
                "superViewTattileTicketCount": super_view_tattile_ticket_count,
            }
        except Exception as e:
            print(f"Error in GetAllMediaCountView: {str(e)}")
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 500,
                        "message": "Internal server error",
                        "data": [],
                    }
                ).data,
                status=500,
            )

        return Response(
            ServiceResponse(
                {"statusCode": 200, "message": "Success", "data": response_data}
            ).data,
            status=200,
        )