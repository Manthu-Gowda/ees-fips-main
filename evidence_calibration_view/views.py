from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import *
from accounts_v2.serializer import ServiceResponse
from drf_yasg import openapi
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from ees.utils import user_information
from django.db.models import Q
import math
from video.models import (
    Video,
    Image,
    Rejects,
    Citation,
    TattileFile,
    Tattile,
    AddEvidenceCalibration,
    EvidenceCalibrationBin,
)
from video.views import get_presigned_url
from .evidence_calibration_review_utils import (
    get_evidence_calibration_view_data,
    get_evidence_details,
    get_evidence_table_data,
    get_evidence_table_graph_data,
    submit_evidence_deatails,
    get_evidence_pdf_data,
    create_evidence_pdf,
    get_pdf_base64,
)


class GetEvidenceCalibrationdMediaDataView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetEvidenceMediadataInputModel,
        responses={200: GetEvidenceMediaDataOutputModel},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        serializer = GetEvidenceMediadataInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        if not serializer.is_valid():
            return Response(
                {
                    "statusCode": 400,
                    "message": "Invalid input data",
                    "errors": serializer.errors,
                },
                status=200,
            )

        media_type = serializer.validated_data.get("mediaType", 1)
        media_id = serializer.validated_data.get("mediaId", 1)
        if media_type == 1:
            video_data = (
                Video.objects.filter(id=media_id, isRejected=True)
                .values("url", "reject_id", "id")
                .first()
            )
            reject_reason = (
                Rejects.objects.filter(id=video_data["reject_id"])
                .values("id", "description")
                .first()
            )
            citation_data = (
                Citation.objects.filter(video_id=video_data["id"], isRejected=True)
                .values("note")
                .first()
            )
            response_data = {
                "mediaType": 1,
                "mediaId": video_data["id"],
                "mediaUrl": get_presigned_url(video_data["url"]),
                "rejectId": reject_reason["id"],
                "rejectReason": reject_reason["description"],
                "note": citation_data["note"] if citation_data else None,
            }
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 200,
                        "message": "Success",
                        "data": GetEvidenceMediaDataOutputModel(response_data).data,
                    }
                ).data,
                status=200,
            )

        elif media_type == 2:
            image_data = (
                Image.objects.filter(id=media_id, isRejected=True)
                .values("lic_image_url", "reject_id", "id")
                .first()
            )
            reject_reason = (
                Rejects.objects.filter(id=image_data["reject_id"])
                .values("id", "description")
                .first()
            )
            citation_data = (
                Citation.objects.filter(image_id=image_data["id"], isRejected=True)
                .values("note")
                .first()
            )
            response_data = {
                "mediaType": 2,
                "mediaId": image_data["id"],
                "mediaUrl": get_presigned_url(image_data["lic_image_url"]) or "",
                "rejectId": reject_reason["id"],
                "rejectReason": reject_reason["description"],
                "note": citation_data["note"] if citation_data else None,
            }
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 200,
                        "message": "Success",
                        "data": GetEvidenceMediaDataOutputModel(response_data).data,
                    }
                ).data,
                status=200,
            )
        elif media_type == 3:
            media_urls = []

            tattile_data = (
                Tattile.objects.filter(id=media_id, is_rejected=True)
                .values(
                    "license_image_url",
                    "speed_image_url",
                    "reject_id",
                    "id",
                    "ticket_id",
                )
                .first()
            )
            tattile_urls = TattileFile.objects.filter(
                ticket_id=tattile_data["ticket_id"], file_type=2
            ).values_list("file_url", flat=True)
            for url in tattile_urls:
                media_urls.append(get_presigned_url(url))
            reject_reason = (
                Rejects.objects.filter(id=tattile_data["reject_id"])
                .values("id", "description")
                .first()
            )
            citation_data = (
                Citation.objects.filter(tattile_id=tattile_data["id"], isRejected=True)
                .values("note")
                .first()
            )

            response_data = {
                "mediaType": 3,
                "mediaId": tattile_data["id"],
                "imageUrls": media_urls,
                # "mediaUrl": get_presigned_url(tattile_urls["file_url"]) or "",
                "licenseImageUrl": get_presigned_url(tattile_data["license_image_url"])
                or "",
                "speedImageUrl": get_presigned_url(tattile_data["speed_image_url"])
                or "",
                "rejectId": reject_reason["id"],
                "rejectReason": reject_reason["description"],
                "note": citation_data["note"] if citation_data else None,
            }
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 200,
                        "message": "Success",
                        "data": GetEvidenceMediaDataOutputModel(response_data).data,
                    }
                ).data,
                status=200,
            )
        else:
            return Response(
                ServiceResponse(
                    {"statusCode": 500, "message": "Internal server error", "data": []}
                ).data,
                status=500,
            )


class AddEvidenceCalibrationView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=AddEvidenceCalibrationInputModel,
        responses={200: "success"},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        serializer = AddEvidenceCalibrationInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        if not serializer.is_valid():
            return Response(
                {
                    "statusCode": 400,
                    "message": "Invalid input data",
                    "errors": serializer.errors,
                },
                status=200,
            )

        # Implementation for adding evidence calibration goes here
        add_evidence = AddEvidenceCalibration.objects.create(
            license_plate=serializer.validated_data.get("licensePlate"),
            evidence_date=serializer.validated_data.get("evidenceDate"),
            evidence_time=serializer.validated_data.get("evidenceTime"),
            evidence_speed=serializer.validated_data.get("evidenceSpeed"),
            badge_id=serializer.validated_data.get("badgeID"),
        )
        return Response(
            ServiceResponse(
                {
                    "statusCode": 200,
                    "message": "Evidence calibration added successfully",
                }
            ).data,
            status=200,
        )


class GetEvidenceCalibrationView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetEvidenceCalibrationViewInputSerializer,
        responses={200: "success"},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        serializer = GetEvidenceCalibrationViewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        page = serializer.validated_data["page"]
        size = serializer.validated_data["size"]

        calibration_data = get_evidence_calibration_view_data()

        if not calibration_data:
            return Response(
                {
                    "statusCode": 204,
                    "message": "no evidence data found",
                    "page": page,
                    "size": size,
                    "totalPages": 0,
                    "totalCount": 0,
                    "hasNext": False,
                    "hasPrevious": False,
                    "data": [],
                },
                status=200,
            )

        # Pagination calculations
        total_count = len(calibration_data)
        total_pages = (total_count + size - 1) // size

        start = (page - 1) * size
        end = start + size
        response_list = calibration_data[start:end]

        return Response(
            {
                "statusCode": 200,
                "message": "Success",
                "page": page,
                "size": size,
                "totalPages": total_pages,
                "totalCount": total_count,
                "hasNext": page < total_pages,
                "hasPrevious": page > 1,
                "data": response_list,
            },
            status=200,
        )


class GetEvidenceCalibrationDetails(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetEvidenceCalibrationDetailsInputModel,
        responses={200: GetEvidenceCalibrationDetailsOutputModel},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        serializer = GetEvidenceCalibrationDetailsInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        if not serializer.is_valid():
            return Response(
                {
                    "statusCode": 400,
                    "message": "Invalid input data",
                    "errors": serializer.errors,
                },
                status=200,
            )
        media_type = serializer.validated_data.get("media_type")
        media_id = serializer.validated_data.get("media_id")
        try:
            print(
                "entered GetEvidenceCalibrationDeatils",
            )
            calibration_data = get_evidence_details(media_type, media_id)
            if not calibration_data:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 204,
                            "message": "no evidence data found",
                            "data": [],
                        }
                    ).data,
                    status=200,
                )
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 200,
                        "message": "Success",
                        "data": calibration_data,
                    }
                ).data,
                status=200,
            )
        except AddEvidenceCalibration.DoesNotExist:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Evidence data not found",
                        "data": [],
                    }
                ).data,
                status=200,
            )


class SubmitEvidenceDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=SubmitEvidenceCalibrationDetailsInputModel,
        responses={200: "success"},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        serializer = SubmitEvidenceCalibrationDetailsInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        if not serializer.is_valid():
            return Response(
                {
                    "statusCode": 400,
                    "message": "Invalid input data",
                    "errors": serializer.errors,
                },
                status=200,
            )

        evidence_id = serializer.validated_data.get("evidenceID")
        tattile_id = serializer.validated_data.get("tattileId")
        speed_pic = serializer.validated_data.get("speedPic", "")
        license_pic = serializer.validated_data.get("licensePic", "")
        try:
            calibration = AddEvidenceCalibration.objects.get(evidence_ID=evidence_id)
            return submit_evidence_deatails(
                calibration, evidence_id, tattile_id, speed_pic, license_pic
            )

        except AddEvidenceCalibration.DoesNotExist:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Evidence data not found",
                        "data": [],
                    }
                ).data,
                status=200,
            )


class GetEvidenceTableDataView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=EvidenceTableInputSerializer,
        responses={200: "success"},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        # ---------------- TOKEN ----------------
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        # ---------------- VALIDATION ----------------
        serializer = EvidenceTableInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "statusCode": 400,
                    "message": "Invalid input data",
                    "errors": serializer.errors,
                },
                status=200,
            )

        # Extract input
        search = serializer.validated_data.get("search")
        from_date = serializer.validated_data.get("fromDate")
        to_date = serializer.validated_data.get("toDate")
        page = serializer.validated_data.get("page", 1)
        size = serializer.validated_data.get("size", 10)

        # ---------------- BASE QUERY ----------------
        qs = AddEvidenceCalibration.objects.filter(
            Q(tattile_id__isnull=False)
        ).select_related("tattile")

        # ---------------- SEARCH ----------------
        if search:
            qs = qs.filter(license_plate__icontains=search)

        # ---------------- DATE RANGE ----------------
        if from_date:
            qs = qs.filter(evidence_date__date__gte=from_date)

        if to_date:
            qs = qs.filter(evidence_date__date__lte=to_date)

        total_count = qs.count()
        total_pages = math.ceil(total_count / size)

        # ----------------  PAGINATION ----------------
        start = (page - 1) * size
        end = start + size
        page_items = qs[start:end]

        # ---------------- BUILD RESPONSE ----------------
        response_list = []
        response_list = get_evidence_table_data(response_list, page_items)
        if not response_list:
            return Response(
                {
                    "statusCode": 204,
                    "message": "no evidence data ",
                    "data": [],
                },
                status=200,
            )
        # ---------------- FINAL RESPONSE ----------------
        return Response(
            {
                "statusCode": 200,
                "message": "Success",
                "page": page,
                "size": size,
                "totalPages": total_pages,
                "totalCount": total_count,
                "hasNext": page < total_pages,
                "hasPrevious": page > 1,
                "data": response_list,
            },
            status=200,
        )


class CreatePDFView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CreatePDFInputModel,
        responses={200: "success"},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_name = readToken.get("station", "")
        agnecy_id = readToken.get("agencyId", "")
        serializer = CreatePDFInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "statusCode": 400,
                    "message": "Invalid input data",
                    "errors": serializer.errors,
                },
                status=200,
            )
        evidence_ID = serializer.validated_data.get("evidenceID")
        evidence_data = AddEvidenceCalibration.objects.get(evidence_ID=evidence_ID)
        if evidence_data.tattile:
            data = get_evidence_pdf_data(
                evidence_ID, evidence_data, agnecy_id, isImage=False, isTattile=True
            )
            filename = f"{evidence_ID}.pdf"
            create_evidence_pdf(filename, data, station_name)
            base64String = get_pdf_base64(filename)
        elif evidence_data.image:
            data = get_evidence_pdf_data(
                evidence_ID, evidence_data, agnecy_id, isImage=True, isTattile=False
            )
            filename = f"{evidence_ID}.pdf"
            create_evidence_pdf(filename, data, station_name)
            base64String = get_pdf_base64(filename)
        return Response(
            ServiceResponse(
                {"statusCode": 200, "message": "Success", "data": base64String}
            ).data,
            status=200,
        )


class GetEvidenceTableGraphDataView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=None,
        responses={200: "success"},
        tags=["EvidenceCalibration"],
    )
    def post(self, request):
        # ---------------- TOKEN ----------------
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        try:
            calibration_data = get_evidence_table_graph_data()
            if not calibration_data:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 204,
                            "message": "no evidence data found",
                            "data": [],
                        }
                    ).data,
                    status=200,
                )
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 200,
                        "message": "Success",
                        "data": calibration_data,
                    }
                ).data,
                status=200,
            )
        except Exception as e:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 500,
                        "message": f"Internal server error inside graph data: {str(e)}",
                        "data": {},
                    }
                ).data,
                status=500,
            )
