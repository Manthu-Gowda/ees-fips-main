from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import *
from accounts_v2.serializer import ServiceResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from video.models import Video, Image, Rejects, Citation, TattileFile, Tattile
from video.views import get_presigned_url


class GetRejectedMediaDataView(APIView):
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        request_body=GetRejectedMediadataInputModel,
        responses={200: GetRejectedMediaDataOutputModel},
        tags=['Reject'],
    )
    def post(self, request):
        serializer = GetRejectedMediadataInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({"statusCode": 400, "message": "Invalid input data", "errors": serializer.errors}, status=400)
        
        media_type = serializer.validated_data.get('mediaType', 1)
        media_id = serializer.validated_data.get('mediaId', 1)
        if media_type == 1:
            video_data = Video.objects.filter(id=media_id,isRejected=True).values("url", "reject_id", "id").first()
            reject_reason = Rejects.objects.filter(id=video_data["reject_id"]).values("id","description").first()
            citation_data = Citation.objects.filter(video_id=video_data["id"] ,isRejected=True).values("note").first()
            response_data = {
                "mediaUrl" : get_presigned_url(video_data["url"]),
                "rejectId" : reject_reason["id"],
                "rejectReason" : reject_reason["description"],
                "note" : citation_data["note"] if citation_data else None
            }
            return Response(ServiceResponse({ "statusCode" : 200, "message" : "Success", "data" : GetRejectedMediaDataOutputModel(response_data).data}).data, status=200)
        
        elif media_type == 2:
            image_data = Image.objects.filter(id=media_id,isRejected=True).values("lic_image_url","reject_id","id").first()
            reject_reason = Rejects.objects.filter(id=image_data["reject_id"]).values("id","description").first()
            citation_data = Citation.objects.filter(image_id=image_data["id"],isRejected=True).values("note").first()
            response_data = {
                "mediaUrl" : get_presigned_url(image_data["lic_image_url"]),
                "rejectId" : reject_reason["id"],
                "rejectReason" : reject_reason["description"],
                "note" : citation_data["note"] if citation_data else None
            }
            return Response(ServiceResponse({ "statusCode" : 200, "message" : "Success", "data" : GetRejectedMediaDataOutputModel(response_data).data}).data, status=200)
        elif media_type == 3:
            tattile_data = Tattile.objects.filter(id=media_id,is_rejected=True).values("license_image_url","reject_id","id","ticket_id").first()
            tattile_urls = TattileFile.objects.filter(ticket_id=tattile_data["ticket_id"],file_type = 2).values('file_url').first()
            reject_reason = Rejects.objects.filter(id=tattile_data["reject_id"]).values("id","description").first()
            citation_data = Citation.objects.filter(tattile_id=tattile_data["id"],isRejected=True).values("note").first()
            
            response_data = {
                "mediaUrl" : get_presigned_url(tattile_urls["file_url"]),
                "rejectId" : reject_reason["id"],
                "rejectReason" : reject_reason["description"],
                "note" : citation_data["note"] if citation_data else None
            }
            return Response(ServiceResponse({ "statusCode" : 200, "message" : "Success", "data" : GetRejectedMediaDataOutputModel(response_data).data}).data, status=200)
        else:
            return Response(ServiceResponse({ "statusCode" : 400, "message" : "Invalid media type.", "data" : []}).data, status=200)

