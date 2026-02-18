from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime
from django.db import transaction
from .serializers import GetApprovedDatesDropdownInputModel, GetMailCenterTableDataInputModel,GetMailCenterTableDataModel,GetMailCenterPDFInputModel,GetMailCenterPDFModel,DeleteMailCenterReviewInputModel,ApproveMailCenterReviewInputModel
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from .mail_center_review_utils import *
from django_q.tasks import async_task
from django_q.models import Task, Failure

class GetApprovedDatesDropdown(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetApprovedDatesDropdownInputModel,
        responses={200: "Success"},
        tags=["MailCenterReview"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        #  Validate token
        serializer = GetApprovedDatesDropdownInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        serializer.is_valid(raise_exception=True)
        if not serializer.is_valid():
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid input data",
                        "data": serializer.errors,
                    }
                ).data,
                status=200,
            )
        serializer_data = serializer.validated_data
        date_type = serializer_data.get("dateType", None) 
        if date_type not in [1, 2]:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid dateType. Must be 1 or 2.",
                        "data": [],
                    }
                ).data,
                status=400,
            )   
            
        if date_type == 1:
            is_edited=False
        else:
            is_edited=True
        try:
            station_id = readToken.get("stationId")
            print("station_id", station_id)
            if not station_id:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 400,
                            "message": "Station ID is required",
                            "data": [],
                        }
                    ).data,
                    status=400,
                )
            # Get flat list of year/month records
            response_data = get_all_approved_dates(station_id,is_edited)
            print("response_data", response_data)
            print("totalDataCount", len(response_data))
            if response_data:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 200,
                            "message": "Success",
                            "data": response_data,
                        }
                    ).data,
                    status=200,
                )

            return Response(
                ServiceResponse(
                    {"statusCode": 204, "message": "No content", "data": []}
                ).data,
                status=200,
            )

        except Exception as e:
            print("Error in GetRemainderNoticeYearAndMonthView:", str(e))
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


# Create your views here.
class MailCenterReviewTableView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMailCenterTableDataInputModel,
        responses={200: GetMailCenterTableDataModel},
        tags=["MailCenterReview"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = GetMailCenterTableDataInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        serializer.is_valid(raise_exception=True)
        if not serializer.is_valid():
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid input data",
                        "data": serializer.errors,
                    }
                ).data,
                status=200,
            )
        print("entered into mail center review view")
        station_id = readToken.get("stationId")
        print("station id:", station_id)
        serializer_data = serializer.validated_data
        search_string = serializer_data.get("searchString", None)
        page_index = serializer_data.get("pageIndex", 1)
        page_size = serializer_data.get("pageSize", 10)
        approved_date = serializer_data.get("approvedDate")
        date_type = serializer_data.get("dateType", None)
        
        if date_type == 1:
            is_edited=False
        else:
            is_edited=True
            
        query_result = citation_data_for_mail_center_review(
            station_id=station_id,
            approved_date=approved_date,
            search_string=search_string,
            page_index=page_index,
            page_size=page_size,
            is_edited=is_edited,
        )
        citations = query_result.get("data", [])
        serialized_data = GetMailCenterTableDataModel(citations, many=True).data
        response_data = {
            "statusCode": 200,
            "message": "Success",
            "totalRecords": query_result.get("total_records"),
            "pageIndex": query_result.get("pageIndex"),
            "pageSize": query_result.get("pageSize"),
            "hasNextPage": query_result.get("hasNextPage"),
            "hasPreviousPage": query_result.get("hasPreviousPage"),
            "data": serialized_data,
        }
        if not serialized_data:
            return Response(
                ServiceResponse(
                    {"statusCode": 204, "message": "No content", "data": None}
                ).data,
                status=200,
            )
        return Response(response_data)


class MailCenterPDFView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetMailCenterPDFInputModel,
        responses={200: GetMailCenterPDFModel},
        tags=["MailCenterReview"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = GetMailCenterPDFInputModel(data=request.data)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        serializer.is_valid(raise_exception=True)
        if not serializer.is_valid():
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid input data",
                        "data": serializer.errors,
                    }
                ).data,
                status=400,
            )
        print("entered into mail center review PDF view")
        station_id = readToken.get("stationId")
        station_name = readToken.get("stationName")
        base64String = ""
        serializer_data = serializer.validated_data
        citationID = serializer_data.get("citationID", None)
        print("citationID:", citationID)
        try:
            base64String = citation_data_for_mail_center_pdf(
                station_id=station_id,
                station_name=station_name,
                citationID=citationID,
            )
            if not base64String:
                return Response(
                    ServiceResponse(
                        {"StatusCode": 204, "message": "No content", "data": None}
                    ).data,
                    status=200,
                )
            return Response(
                ServiceResponse(
                    {"statusCode": 200, "message": "Success", "data": base64String}
                ).data,
                status=200,
            )
        except Exception as e:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 500,
                        "message": "Something went wrong inside mail_center_pdf_view",
                        "data": str(e),
                    }
                ).data,
                status=500,
            )


class ApproveMailCenterReview(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ApproveMailCenterReviewInputModel,
        responses={200: "Success"},
        tags=["MailCenterReview"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")
        if not station_id:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Station ID not found in token",
                        "data": None,
                    }
                ).data,
                status=400,
            )

        serializer = ApproveMailCenterReviewInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid input data",
                        "data": serializer.errors,
                    }
                ).data,
                status=400,
            )

        citation_ids = serializer.validated_data["citationIds"]
        date_type = serializer.validated_data["dateType"]
        now = datetime.now()

        with transaction.atomic():
            updated_count = sup_metadata.objects.filter(
                citation_id__in=citation_ids,
                station_id=station_id,
            ).update(
                isMailCitationApproved=True,
                mailCitationApprovedTime=now,
            )

        task_id = async_task(
            "mail_center_review.task.generate_mailcenter_pdfs_and_csvs",
            citation_ids,
            date_type,
        )

        return Response(
            {
                "statusCode": 202,
                "message": "Citations approved. PDF/CSV generation started.",
                "approvedCount": updated_count,
                "taskId": task_id,
            },
            status=202,
        )

class JobStatus(APIView):
    @swagger_auto_schema(
        responses={
            200: "Completed",
            202: "Running",
            500: "Failed",
        },
        tags=["MailCenterReview"],
        security=[{"Bearer": []}],
    )
    def get(self, request, task_id):
        # 1️⃣ Completed task
        try:
            task = Task.objects.get(id=task_id)
            if task.success:
                return Response(
                    {
                        "statusCode": 200,
                        "status": "COMPLETED",
                        "message": "PDF and CSV generated successfully",
                    },
                    status=200,
                )
        except Task.DoesNotExist:
            pass

        # 2️⃣ Failed task
        if Failure.objects.filter(id=task_id).exists():
            return Response(
                {
                    "statusCode": 500,
                    "status": "FAILED",
                    "message": "PDF/CSV generation failed. Please retry.",
                },
                status=500,
            )

        # 3️⃣ Still running / queued
        return Response(
            {
                "statusCode": 202,
                "status": "RUNNING"
             },
            status=202,
        )


class DeleteMailCenterReview(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=DeleteMailCenterReviewInputModel,
        responses={200: "Success"},
        tags=["MailCenterReview"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")
        if not station_id:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Station ID not found in token",
                        "data": None,
                    }
                ).data,
                status=400,
            )

        serializer = DeleteMailCenterReviewInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Invalid input data",
                        "data": serializer.errors,
                    }
                ).data,
                status=400,
            )

        citation_ids = serializer.validated_data["citationIds"]
        now = datetime.now()

        with transaction.atomic():
            deleted_count = sup_metadata.objects.filter(
                citation_id__in=citation_ids,
                station_id=station_id,
            ).update(
                isMailCitationRejected=True,
                mailCitationRejectedTime=now,
            )
        response_data = {
            "statusCode": 200,
            "message": "Citations marked as rejected successfully",
            "deletedCount": deleted_count,
        }
        return Response(response_data)  # No Content


class GeneratePDFAndCSVForMailCenterCitations(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},  # no params
        ),
        responses={200: "Success"},
        tags=["MailCenterReview"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_id = readToken.get("stationId")
        if not station_id:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "Station ID not found in token",
                        "data": None,
                    }
                ).data,
                status=400,
            )
        print("entered into GeneratePDFAndCSVForMailCenterCitations view")
        try:
            create_csv_and_pdf_data_for_agencies()
            return Response(
                ServiceResponse(
                    {"statusCode": 200, "message": "Success", "data": None}
                ).data,
                status=200,
            )

        except Exception as e:
            print("Error in GeneratePDFAndCSVForMailCenterReview:", str(e))
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 500,
                        "message": "Internal server error",
                        "data": str(e),
                    }
                ).data,
                status=500,
            )
