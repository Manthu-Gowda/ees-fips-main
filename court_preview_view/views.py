from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import *
from accounts_v2.serializer import ServiceResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from video.models import Citation, Video, Image, ImageHash, ImageData, Tattile, TattileFile
from video.views import get_presigned_url


class GetCitationDataForCourtPreviewView(APIView):
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        request_body=GetCitationDataForCourtPrviewInputModel,
        responses={200: GetCitationDataForCourtPrviewOutputModel},
        tags=['CourtPreview'],
    )
    def post(self,request):
        serializer = GetCitationDataForCourtPrviewInputModel(data=request.data)
        if not serializer.is_valid():
            return Response({"statusCode": 400, "message": "Invalid input data", "errors": serializer.errors}, status=400)
        
        media_type = serializer.validated_data.get('mediaType')
        citation_id = serializer.validated_data.get('citationID')
        image_urls = []
        if media_type == 1:
            citation_data = Citation.objects.filter(citationID=citation_id,isApproved=True).values("video_id", "citationID").first()
            if citation_data and citation_data["video_id"] is not None:
                video_data = Video.objects.filter(id=citation_data["video_id"]).values("url").first()
                image_urls.append(get_presigned_url(video_data["url"]))
                response_data = {
                    "citationID" : citation_data["citationID"],
                    "mediaUrl" : image_urls
                }
                return Response(ServiceResponse({"statusCode":200, "message":"Success", "data" : GetCitationDataForCourtPrviewOutputModel(response_data).data}).data,status=200)
            return Response(ServiceResponse({"statusCode":204, "message": f"The Video Citation No. {citation_id} was not found or has no associated video. Please try again.", "data": []}).data, status=200)
        elif media_type == 2:
            citation_data = Citation.objects.filter(citationID=citation_id,isApproved=True).values("image_id","citationID").first()
            if citation_data and citation_data["image_id"] is not None:
                imgae_data = Image.objects.filter(id=citation_data["image_id"]).values("ticket_id").first()
                image_hash_urls = ImageHash.objects.filter(ticket_id=imgae_data["ticket_id"]).values_list('image_url', flat=True)
                image_data_urls = ImageData.objects.filter(ticket_id=imgae_data["ticket_id"]).values_list('image_url', flat=True)

                for image_url in list(image_hash_urls) + list(image_data_urls):
                    image_urls.append(get_presigned_url(image_url))
                response_data = {
                    "citationID" : citation_data["citationID"],
                    "mediaUrl" : image_urls
                }
                return Response(ServiceResponse({"statusCode":200, "message":"Success", "data" : GetCitationDataForCourtPrviewOutputModel(response_data).data}).data,status=200)
            return Response(ServiceResponse({"statusCode":204, "message": f"The Image Citation No. {citation_id} was not found or has no associated image. Please try again.", "data": []}).data, status=200)
        elif media_type == 3:
            citation_data = Citation.objects.filter(citationID=citation_id,isApproved=True).values("tattile_id","citationID").first()
            if citation_data and citation_data["tattile_id"] is not None:
                tattile_data = Tattile.objects.filter(id=citation_data["tattile_id"]).values("ticket_id").first()
                tattile_urls = TattileFile.objects.filter(ticket_id=tattile_data["ticket_id"],file_type__in = [1,2]).values_list('file_url', flat=True)

                for image_url in list(tattile_urls):
                    image_urls.append(get_presigned_url(image_url))
                response_data = {
                    "citationID" : citation_data["citationID"],
                    "mediaUrl" : image_urls
                }
                return Response(ServiceResponse({"statusCode":200, "message":"Success", "data" : GetCitationDataForCourtPrviewOutputModel(response_data).data}).data,status=200)
            return Response(ServiceResponse({"statusCode":204, "message": f"The Tattile Citation No. {citation_id} was not found or has no associated tattile. Please try again.", "data": []}).data, status=200)
        else:
            return Response(ServiceResponse({"statusCode":400, "message": "Invalid media type.", "data": []}).data, status=200)