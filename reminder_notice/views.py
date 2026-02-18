from reminder_notice.reminder_notice_utils import citation_data_for_reminder_approved_table, get_cit_refactor, get_reminder_hud_c_cit, get_reminder_pdf_base64, save_combined_pdf
from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import ServiceResponse
from rest_framework.views import APIView
from .reminder_notice_utils import *

# Import the missing function


# get the distinct years from sup_metadata table where isApproved is true
class GetReminderNoticeYearsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={},  # no params
        ),
        responses={200: "Success"},
        tags=["ReminderNotice"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        #  Validate token
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

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
            response_data = get_reminder_notice_years(station_id)
            print("response_data", response_data)
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


# get the months for a given year from sup_metadata table where isApproved is true
class GetReminderNoticeMonthsByYearView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "year": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Year (required)"
                ),
            },
            required=["year"],
        ),
        responses={200: "Success"},
        tags=["ReminderNotice"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        #  Validate token
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        try:
            station_id = readToken.get("stationId")
            print("station_id", station_id)
            user_name = readToken.get("username")
            print("user_name", user_name)
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
            year = request.data.get("year")
            if not year:
                return Response(
                    ServiceResponse(
                        {"statusCode": 400, "message": "Year is required", "data": []}
                    ).data,
                    status=400,
                )
            # Get flat list of year/month records
            response_data = get_reminder_notice_months_by_year(station_id, year)
            print("response_data", response_data)

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


class ReminderNoticeCitationIDView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "year": openapi.Schema(type=openapi.TYPE_INTEGER, description="Year",nullable=True),
                "month": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Month (1-12)",nullable=True
                ),
                "isRemainderSent": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Whether reminder sent",
                    nullable=True,
                    default=None,
                ),
            },
        ),
        responses={200: "Success"},
        tags=["ReminderNotice"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        #  Validate token
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        try:
            station_id = readToken.get("stationId")
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

            year = request.data.get("year")
            month = request.data.get("month")
            isRemainderSent = request.data.get("isRemainderSent")

            # Get Citation IDs from sup_metadata
            sup_metadata_citaion_ids = citation_IDs_from_sup_metadata(
                station_id,
                year,
                month,
            )
            if not sup_metadata_citaion_ids:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 400,
                            "message": "No citation IDs found in sup_metadata for given year and month.",
                        }
                    ).data,
                    status=400,
                )
            print("sup_metadata_citaion_ids", sup_metadata_citaion_ids)
            # Get Citation IDs from citation table
            citation_table_citaionIDs = citationIDs_from_citation_table(
                station_id, sup_metadata_citaion_ids, isRemainderSent
            )
            if not citation_table_citaionIDs:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 400,
                            "message": "No matching citations found in Citation for given year and month.",
                        }
                    ).data,
                    status=400,
                )
            # print("citation_table_citaionIDs", citation_table_citaionIDs)

            # Get unpaid citation IDs
            unpaid_citation_ids = citaionIDs_from_paid_citaion(
                citation_table_citaionIDs
            )
            if not unpaid_citation_ids:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 400,
                            "message": "No unpaid citations found for given year and month.",
                        }
                    ).data,
                    status=400,
                )

            response_data = {
                "totalRecords": len(unpaid_citation_ids),
                "unpaidCitationIDs": unpaid_citation_ids,
            }

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

        except Exception as e:
            print("Error in GetRemainderNoticeCitationIDView:", str(e))
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 500,
                        "message": f"Internal server error {str(e)}",
                        "data": [],
                    }
                ).data,
                status=500,
            )


class SubmitReminderNoticeAndPDFView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "citationIDs": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description="citationIDs array",
                ),
            },
            required=["citationIDs"],
        ),
        responses={200: "Success"},
        tags=["ReminderNotice"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        failed_update_ids = []
        failed_drive_cit_refactor = []
        failed_drive_hud_c_cit = []
        failed_combined_pdf = []
        combined_remainder_notice_pdf_path = None
        #  Validate token
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")
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
        citationIDs = request.data.get("citationIDs", [])
        if not citationIDs:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "citationIDs are required",
                        "data": [],
                    }
                ).data,
                status=400,
            )
        data_initial_cit = None
        data_remainder_hud_c = None
        # cit_id = ""
        try:
            # -------------------
            # PART 1: cit_refactor flow
            # -------------------
            print("enetered into get reminder notice and pdf view")
            try:
                citation_data_called_date = quick_pd_data.filter(
                    ticket_num__in=citationIDs
                ).values()

                for date_in in citation_data_called_date:
                    cit_id = date_in["ticket_num"]
                    user_station = date_in["station_id"]
                    # Fetch the citation record
                    citation_obj = Citation.objects.filter(citationID=cit_id).first()
                    print("Processing cit_id:", cit_id)
                    if citation_obj:
                        if citation_obj.video_id:
                            data_initial_cit = get_cit_refactor(
                                cit_id, user_station, False, False
                            )
                            data_remainder_hud_c = get_reminder_hud_c_cit(
                                cit_id, station_id, False, False
                            )
                        elif citation_obj.tattile_id:
                            data_initial_cit = get_cit_refactor(
                                cit_id, user_station, False, True
                            )
                            data_remainder_hud_c = get_reminder_hud_c_cit(
                                cit_id, station_id, False, True
                            )
                        elif citation_obj.image_id:
                            data_initial_cit = get_cit_refactor(
                                cit_id, user_station, True, False
                            )
                            data_remainder_hud_c = get_reminder_hud_c_cit(
                                cit_id, station_id, True, False
                            )

                    staion_name = "HUD-C"
                    # data_initial_cit = data_initial_cit["data"]
                    if data_initial_cit is None:
                        failed_drive_cit_refactor.append(
                            {
                                "id": cit_id,
                                "message": "Failed to generate initial citation data",
                            }
                        )
                        print(
                            f"Failed to generate initial citation data for cit_id: {cit_id}"
                        )
                        continue  # skip further processing for this failed ID
                    if data_remainder_hud_c is None:
                        failed_drive_hud_c_cit.append(
                            {
                                "id": cit_id,
                                "message": "Failed to generate HUD-C reminder data",
                            }
                        )
                        print(
                            f"Failed to generate HUD-C reminder data for cit_id: {cit_id}"
                        )
                        continue  # skip further processing for this failed ID
                    combined_remainder_notice_pdf_path = save_combined_pdf(
                        cit_id, staion_name, data_initial_cit, data_remainder_hud_c
                    )
                    print(
                        "combined_remainder_notice_pdf_path:",
                        combined_remainder_notice_pdf_path,
                    )
                    if not combined_remainder_notice_pdf_path:
                        failed_combined_pdf.append(
                            {
                                "id": cit_id,
                                "message": "Failed to combine and save PDF",
                            }
                        )
                        continue  # skip this failed one

                    if combined_remainder_notice_pdf_path:
                        try:
                            print(
                                "Updating citation is_reminder_sent for cit_id:",
                                cit_id,
                            )
                            # Update is_reminder_sent and remainder_sent_date in Citation table
                            Citation.objects.filter(citationID=cit_id).update(
                                isRemainderSent=True,
                                remainderSentDate=datetime.now(),
                                remainderCombinedPdfPath=combined_remainder_notice_pdf_path,
                            )
                        except Exception as e:
                            print(
                                f"Error updating citation is_remainder_sent status {cit_id}: {e}"
                            )
                            failed_update_ids.append(
                                {"id": cit_id, "message": f"Update failed: {str(e)}"}
                            )  # collect failed IDs
            except Exception as e:
                print("data flow error:", e)
                raise Exception("Something went wrong while generating data for PDF")
            # -------------------
            # Final Response
            # -------------------
            if len(failed_drive_cit_refactor) == len(citationIDs):
                response_data = {
                    "failedDriveHudcCit": failed_drive_hud_c_cit,
                    "failedDriveCitRefactor": failed_drive_cit_refactor,
                    "failedCombinedPDF": failed_combined_pdf,
                    "failedReminderUpdateIDs": failed_update_ids,
                }
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 400,
                            "message": "Submission Failed",
                            "data": response_data,
                        }
                    ).data,
                    status=400,
                )
            else:
                response_data = {
                    "failedDriveHudcCit": failed_drive_hud_c_cit,
                    "failedDriveCitRefactor": failed_drive_cit_refactor,
                    "failedCombinedPDF": failed_combined_pdf,
                    "failedReminderUpdateIDs": failed_update_ids,
                    "failedSubmissionCount": len(failed_drive_cit_refactor),
                }
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 200,
                            "message": "Citation IDs have been submitted successfully",
                            "data": response_data,
                        }
                    ).data,
                    status=200,
                )

        except Exception as e:
            print("exception:", e)
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 500,
                        "message": f"Something went wrong {e}",
                        "data": [],
                    }
                ).data,
                status=500,
            )


class GetCitationDataForReminderApprovedTableView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetReminderNoticeCitationsInputModel,
        responses={200: GetReminderCitationData(many=True)},
        tags=["ReminderNotice"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = GetReminderNoticeCitationsInputModel(data=request.data)
        readToken = user_information(request)

        if isinstance(readToken, Response):
            return readToken

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
        station_id = readToken.get("stationId")
        serializer_data = serializer.validated_data

        date_type = serializer_data.get("dateType")
        from_date = serializer_data.get("fromDate")
        to_date = serializer_data.get("toDate")
        search_string = serializer_data.get("searchString", None)
        page_index = serializer_data.get("pageIndex", 1)
        page_size = serializer_data.get("pageSize", 10)
        query_result = citation_data_for_reminder_approved_table(
            date_type,
            from_date,
            to_date,
            search_string,
            page_index,
            page_size,
            station_id,
            isDownload=False,
        )
        citations = query_result["data"]
        total_records = query_result["total_records"]

        serialized_data = GetReminderCitationData(citations, many=True).data

        response_data = {
            "data": serialized_data,
            "pageIndex": page_index,
            "pageSize": page_size,
            "totalRecords": total_records,
            "hasNextPage": (page_index * page_size) < total_records,
            "hasPreviousPage": page_index > 1,
            "statusCode": 200,
            "message": "Success",
        }
        if response_data["data"] is None:
            return Response(
                ServiceResponse(
                    {"statusCode": 204, "message": "No content", "data": None}
                ).data,
                status=200,
            )

        return Response(response_data)


class ViewReminderPDFView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["citationID"],
            properties={
                "citationID": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Citation ID"
                ),
            },
        ),
        responses={200: "success"},
        tags=["ReminderNotice"],
        security=[{"Bearer": []}],
    )
    def post(self, request):
        citation_id = request.data.get("citationID")
        if not citation_id:
            return Response(
                ServiceResponse(
                    {
                        "statusCode": 400,
                        "message": "citationID is required in body",
                        "data": [],
                    }
                ).data,
                status=400,
            )

        try:
            citation = Citation.objects.filter(citationID=citation_id).first()
            if not citation:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 204,
                            "message": "Citation not found",
                            "data": [],
                        }
                    ).data,
                    status=404,
                )

            if not citation.remainderCombinedPdfPath:
                return Response(
                    ServiceResponse(
                        {
                            "statusCode": 204,
                            "message": "No reminder notice PDF found for this citation",
                            "data": [],
                        }
                    ).data,
                    status=404,
                )

            base64_string = get_reminder_pdf_base64(citation.remainderCombinedPdfPath)

            response_data = {
                "citationID": citation_id,
                "base64String": base64_string,
            }

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

        except Exception as e:
            print("Error in ViewReminderPDFView:", str(e))
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
