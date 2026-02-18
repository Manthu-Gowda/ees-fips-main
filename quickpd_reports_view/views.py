import io
import base64
import calendar
import os
from decimal import Decimal
import traceback
import pandas as pd
from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from quickpd_reports_view.serializer import *
from accounts_v2.serializer import APIResponse, ServiceResponse
from ees.utils import user_information
from video.models import QuickPdPaidCitationFiles, QuickPdPaidCitations, Citation, Station, \
sup_metadata, adj_metadata, ReviewBin, AdjudicationBin
from accounts.models import User
from ees.utils import upload_to_s3
from drf_yasg import openapi
from django.db.models.functions import ExtractYear, ExtractMonth
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Case, When, Value, F, Exists, DecimalField, CharField, OuterRef, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
# from datetime import datetime, timedelta
from .reports_utils import *
from approved_tables.serializer import PagedResponse, GetCSVBase64StringOutputModel
import datetime
from collections import defaultdict

class UploadQuickPdPaidCitationsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetQuickPdPaidFileInputModel,
        responses={200: GetQuickPdPaidFileOutputModel},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        user_id = readToken.get('user_id')
        station_id = readToken.get('stationId')

        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response(APIResponse({
                "statusCode": 404,
                "message": "User not found",
                "errors": None
            }).data, status=404)

        station = Station.objects.filter(id=station_id).first()
        if not station:
            return Response(APIResponse({
                "statusCode": 404,
                "message": "Station not found",
                "errors": None
            }).data, status=404)
        
        serializer = GetQuickPdPaidFileInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "errors": serializer.errors
            }).data, status=400)

        csv_data_base64 = serializer.validated_data.get('base64String')
        try:
            csv_data = base64.b64decode(csv_data_base64).decode('utf-8')
        except (base64.binascii.Error, UnicodeDecodeError):
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid base64 string",
                "data": None
            }).data, status=400)

        # Generate a dynamic file name and store the CSV file
        file_name = f"quick_pd_paid_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        upload_path = os.path.join(settings.MEDIA_ROOT, "csv_uploads",station.name)
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(csv_data)


        # Read CSV data using pandas
        try:
            df = pd.read_csv(io.StringIO(csv_data))
        except Exception as e:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Error reading CSV data.",
            }).data, status=400)

        with open(file_path, "rb") as report_file:
            s3_file_name = f"{station.name}/{file_name}"
            upload_to_s3(report_file, s3_file_name, "quick_pd_paid_citations_csv")

        os.remove(file_path)
        # Validate expected columns (order doesn't matter)
        expected_columns = [
            "Date Paid", "Batch Date", "Ticket Number", "First Name", 
            "Last Name", "Total Paid", "Court ID", "Court Name", "E.E.S. Amount"
        ]
        if not set(expected_columns).issubset(df.columns):
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": f"CSV header does not match expected columns. Expected: {', '.join(expected_columns)}",
            }).data, status=400)

        # Wrap the processing in a try-except block for graceful error handling
        try:
            # Check for duplicate ticket numbers in the database
            df["Ticket Number"] = df["Ticket Number"].astype(str).str.rstrip('A').str.rstrip('a')
            ticket_numbers = df["Ticket Number"].dropna().unique().tolist()
            existing_duplicates = list(
                QuickPdPaidCitations.objects.filter(ticket_number__in=ticket_numbers)
                .values_list("ticket_number", flat=True)
            )
            if existing_duplicates:
                response_data = {
                    "rowsProcessed": 0,
                    "duplicateTicketNumbers": existing_duplicates
                }
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Duplicate ticket numbers found in the database.",
                    "data": response_data

                }).data, status=200)

            # Convert date columns (any invalid formats will become NaT)
            df['Date Paid'] = pd.to_datetime(df['Date Paid'], format='%m/%d/%Y', errors='coerce').dt.date
            df['Batch Date'] = pd.to_datetime(df['Batch Date'], format='%m/%d/%Y', errors='coerce').dt.date
            
            # Prepare QuickPdPaidCitations instances for bulk creation
            records = []
            for _, row in df.iterrows():
                try:
                    total_paid = Decimal(str(row["Total Paid"])) if pd.notnull(row["Total Paid"]) else None
                    court_id = int(row["Court ID"]) if pd.notnull(row["Court ID"]) else None
                    ees_amount = Decimal(str(row["E.E.S. Amount"])) if pd.notnull(row["E.E.S. Amount"]) else None

                    # Get related Citation once to avoid multiple queries per row
                    citation_instance = Citation.objects.filter(citationID=row["Ticket Number"]).first()

                    record = QuickPdPaidCitations(
                        ticket_number=row["Ticket Number"],
                        paid_date=row["Date Paid"],
                        batch_date=row["Batch Date"],
                        first_name=row["First Name"],
                        last_name=row["Last Name"],
                        total_paid=total_paid,
                        court_id=court_id,
                        court_name=row["Court Name"],
                        ees_amount=ees_amount,
                        station=citation_instance.station if citation_instance else None,
                        video=citation_instance.video if citation_instance else None,
                        image=citation_instance.image if citation_instance else None
                    )
                    records.append(record)
                except Exception as e:
                    # Log the error if needed and skip the row
                    print(f"Error processing row: {row} with error: {e}")
                    continue

            rows_processed = len(records)
            if records:
                QuickPdPaidCitations.objects.bulk_create(records)

            # Log the file upload details
            QuickPdPaidCitationFiles.objects.create(
                file_name=file_name,
                station=station,
                user=user,
                rows_processed=rows_processed
            )

            output_serializer = GetQuickPdPaidFileOutputModel({'rowsProcessed': rows_processed,
                                                               'errors': [],
                                                                'duplicateTicketNumbers': []})
            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Success",
                "data": output_serializer.data
            }).data, status=200)
        
        except Exception as e:
            # Log the exception for debugging purposes
            print(f"Unexpected error during processing: {e}")
            return Response(ServiceResponse({
                "statusCode": 500,
                "message": "An internal error occurred while processing the file.",
            }).data, status=500)

from django.db import connection
def dictfetchall(cursor):
    "Return all rows from a cursor as a list of dicts"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# Function to parse date from "YYYY-MM" or "YYYY-MM-DD"


class QuickPdCitationLevelReportView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CitationLevelReportInputSerializer,
        responses={200: CitationReportItemSerializer(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = CitationLevelReportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        start_date_str = filters.get("startDate")
        end_date_str = filters.get("endDate")
        search_string = filters.get("searchString")
        page = filters.get("pageIndex", 1)
        page_size = filters.get("pageSize", 10)
        mailer_type = filters.get("mailerType", 0)  # Expecting mailerType = 1 or 2 for raw SQL
        payment_status_type = filters.get("paymentStatusType", 0)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_id = readToken.get("stationId")
        station = Station.objects.filter(id=station_id).first()
        if not station:
            return Response({"statusCode": 404, "message": "Station not found", "errors": None}, status=404)
        def parse_date(date_str, is_end_date=False):
            if date_str and len(date_str) == 7:  # "YYYY-MM" format
                year, month = map(int, date_str.split('-'))
                # If it's the end date, get the last day of the month
                if is_end_date:
                    last_day = calendar.monthrange(year, month)[1]
                    return datetime.date(year, month, last_day)
                # If it's the start date, use the first day of the month
                return datetime.date(year, month, 1)
            elif date_str:  # handle full date format "YYYY-MM-DD"
                return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return None
        # Parse the dates to proper date format
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str, is_end_date=True)

        # Check if mailer_type is 1 or 2 for raw SQL
        if mailer_type in [1, 2]:
            params = []

            if mailer_type == 1:
                date_field = "first_mail_due_date"
                fine_field = "first_mail_fine"
                mail_count_condition = 'u."pre_odr_mail_count" >= 1'
                sent_to_pre_odr = "CASE WHEN u.\"pre_odr_mail_count\" = 2 THEN 'Yes' ELSE 'No' END AS \"Sent to Pre-Odr 2\""
            elif mailer_type == 2:
                date_field = "second_mail_due_date"
                fine_field = "second_mail_fine"
                mail_count_condition = 'u."pre_odr_mail_count" = 2'
                sent_to_pre_odr = "NULL AS \"Sent to Pre-Odr 2\""

            sql = f"""
                SELECT  
                    EXTRACT(YEAR FROM (u."{date_field}"::DATE - INTERVAL '30 days')) AS "year",
                    TO_CHAR((u."{date_field}"::DATE - INTERVAL '30 days'), 'Month') AS "month",
                    (u."{date_field}"::DATE - INTERVAL '30 days') AS "approvedDate",
                    u."ticket_number" AS "citationId",
                    st."ab" AS "state",
                    v."plate" AS "licencePlate",
                    p."first_name" AS "firstName",
                    p."last_name" AS "lastName",
                    u."{fine_field}" AS "dueAmount",
                    u."{date_field}" AS "dueDate",
                    CASE 
                        WHEN pay."citationID" IS NOT NULL THEN 'Paid' 
                        ELSE 'Pending'
                    END AS "paymentStatus",
                    {sent_to_pre_odr}
                FROM unpaid_citation u
                LEFT JOIN citation c ON u."ticket_number" = c."citationID"
                LEFT JOIN vehicle v ON c."vehicle_id" = v."id"
                LEFT JOIN person p ON c."person_id" = p."id"
                LEFT JOIN state st ON v."lic_state_id" = st."id"
                LEFT JOIN paid_citations pay ON pay."citationID" = c."citationID"
                WHERE {mail_count_condition}
            """

            # Add date filter
            if start_date:
                sql += f' AND (u."{date_field}"::DATE - INTERVAL \'30 days\') >= %s'
                params.append(start_date)
            if end_date:
                sql += f' AND (u."{date_field}"::DATE - INTERVAL \'30 days\') <= %s'
                params.append(end_date)

            # Add search filter
            if search_string:
                sql += """
                    AND (
                        u."ticket_number" ILIKE %s OR 
                        p."first_name" ILIKE %s OR 
                        p."last_name" ILIKE %s OR 
                        v."plate" ILIKE %s
                    )
                """
                search_param = f"%{search_string}%"
                params.extend([search_param] * 4)
                
            if payment_status_type == 1:
                sql += ' AND pay."citationID" IS NOT NULL'
            elif payment_status_type == 2:
                sql += ' AND pay."citationID" IS NULL'

            sql += f' ORDER BY (u."{date_field}"::DATE - INTERVAL \'30 days\') ASC'

            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                raw_data = dictfetchall(cursor)

            for row in raw_data:
                approved_date = row.get("approvedDate")
                if approved_date:
                    if isinstance(approved_date, str):
                        try:
                            approved_date = datetime.datetime.fromisoformat(approved_date)
                        except ValueError:
                            approved_date = datetime.datetime.strptime(approved_date.split("T")[0], "%Y-%m-%d")
                    row["approvedDate"] = approved_date.strftime("%B %d %Y")

            paginator = Paginator(raw_data, page_size)
            page_index = int(page) if str(page).isdigit() else 1
            page_obj = paginator.get_page(page_index)

            return Response({
                "data": page_obj.object_list,
                "pageIndex": page_obj.number,
                "pageSize": page_size,
                "totalRecords": paginator.count,
                "hasNextPage": page_obj.has_next(),
                "hasPreviousPage": page_obj.has_previous(),
                "statusCode": 200,
                "message": "Success"
            })

        # Default ORM approach if mailer_type == 0
        if mailer_type == 0:
            qs = sup_metadata.objects.filter(
                citation__station=station,
                isApproved=True
            ).select_related(
                'citation', 'citation__person', 'citation__vehicle', 'citation__fine'
            )

            if start_date_str and end_date_str:
                try:
                    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
                except Exception as e:
                    return Response({"statusCode": 400, "message": "Invalid date format. Expected YYYY-MM-DD.", "errors": str(e)}, status=400)
                qs = qs.filter(timeApp__date__gte=start_date, timeApp__date__lte=end_date)

            if search_string:
                qs = qs.filter(
                    Q(citation__citationID__icontains=search_string) |
                    Q(citation__person__first_name__icontains=search_string) |
                    Q(citation__person__last_name__icontains=search_string) |
                    Q(citation__vehicle__plate__icontains=search_string)
                )

            from django.db.models.functions import ExtractYear, ExtractMonth
            from django.db.models import Case, When, Value, F, Exists, OuterRef, DecimalField, CharField

            qs = qs.annotate(
                year=ExtractYear('timeApp'),
                month=ExtractMonth('timeApp')
            )

            paid_exists = Exists(
                QuickPdPaidCitations.objects.filter(ticket_number=OuterRef('citation__citationID'))
            )

            qs = qs.annotate(
                due_amount=Case(
                    When(paid_exists, then=Value(Decimal('0.00'))),
                    default=F('citation__fine__fine'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ),
                payment_status=Case(
                    When(paid_exists, then=Value("Paid")),
                    default=Value("Pending"),
                    output_field=CharField()
                )
            )
            
            if payment_status_type == 1:
                qs = qs.filter(payment_status="Paid")
            elif payment_status_type == 2:
                qs = qs.filter(payment_status="Pending")

            qs = qs.order_by('-timeApp')
            paginator = Paginator(qs, page_size)
            try:
                page_index = int(page)
            except Exception:
                page_index = 1
            page_obj = paginator.get_page(page_index)
            output_serializer = CitationReportItemSerializer(page_obj.object_list, many=True)
            return Response({
                "data": output_serializer.data,
                "pageIndex": page_obj.number,
                "pageSize": page_size,
                "totalRecords": paginator.count,
                "hasNextPage": page_obj.has_next(),
                "hasPreviousPage": page_obj.has_previous(),
                "statusCode": 200,
                "message": "Success"
            })

        else:
            return Response({
                "statusCode": 400,
                "message": "Invalid mailerType. Expected 0, 1, or 2.",
                "errors": None
            }, status=400)
        
class QuickPdCitationLevelReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=CitationLevelReportDownloadInputSerializer,
        responses={200: "CSV file in base64 string"},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = CitationLevelReportDownloadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        start_date_str = filters.get("startDate")
        end_date_str = filters.get("endDate")
        search_string = filters.get("searchString")
        mailer_type = filters.get("mailerType", 0)
        page_index = filters.get('pageIndex', 1)
        page_size = filters.get('pageSize', 10)
        payment_status_type = filter.get('paymentStatusType', 0)
          # default to 0

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_id = readToken.get("stationId")
        station = Station.objects.filter(id=station_id).first()
        if not station:
            return JsonResponse({"statusCode":404, "message": "Station not found", "errors": None}, status=404)
        def parse_date(date_str, is_end_date=False):
            if date_str and len(date_str) == 7:  # "YYYY-MM" format
                year, month = map(int, date_str.split('-'))
                # If it's the end date, get the last day of the month
                if is_end_date:
                    last_day = calendar.monthrange(year, month)[1]
                    return datetime.date(year, month, last_day)
                # If it's the start date, use the first day of the month
                return datetime.date(year, month, 1)
            elif date_str:  # handle full date format "YYYY-MM-DD"
                return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return None
        # Parse the dates to proper date format
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str, is_end_date=True)
        rows = []  # Will populate rows for CSV

        if mailer_type in [1, 2]:
            params = []

            if mailer_type == 1:
                date_field = "first_mail_due_date"
                fine_field = "first_mail_fine"
                mail_count_condition = 'u."pre_odr_mail_count" >= 1'
                sent_to_pre_odr = "CASE WHEN u.\"pre_odr_mail_count\" = 2 THEN 'Yes' ELSE 'No' END AS \"Sent to Pre-Odr 2\""
            elif mailer_type == 2:
                date_field = "second_mail_due_date"
                fine_field = "second_mail_fine"
                mail_count_condition = 'u."pre_odr_mail_count" = 2'
                sent_to_pre_odr = "NULL AS \"Sent to Pre-Odr 2\""

            sql = f"""
                SELECT  
                    EXTRACT(YEAR FROM (u."{date_field}"::DATE - INTERVAL '30 days')) AS "Year",
                    EXTRACT(MONTH FROM (u."{date_field}"::DATE - INTERVAL '30 days')) AS "Month",
                    (u."{date_field}"::DATE - INTERVAL '30 days') AS "Approved Date",
                    u."ticket_number" AS "Citation ID",
                    st."ab" AS "State",
                    v."plate" AS "Lic Plate",
                    p."first_name" AS "First Name",
                    p."last_name" AS "Last Name",
                    u."{fine_field}" AS "Due Amount",
                    u."{date_field}" AS "Due Date",
                    CASE 
                        WHEN pay."citationID" IS NOT NULL THEN 'Paid' 
                        ELSE 'Pending'
                    END AS "Payment Status",
                    {sent_to_pre_odr}
                FROM unpaid_citation u
                LEFT JOIN citation c ON u."ticket_number" = c."citationID"
                LEFT JOIN vehicle v ON c."vehicle_id" = v."id"
                LEFT JOIN person p ON c."person_id" = p."id"
                LEFT JOIN state st ON v."lic_state_id" = st."id"
                LEFT JOIN paid_citations pay ON pay."citationID" = c."citationID"
                WHERE {mail_count_condition}
            """

            # Add date filter
            if start_date_str:
                sql += f' AND (u."{date_field}"::DATE - INTERVAL \'30 days\') >= %s'
                params.append(start_date)
            if end_date_str:
                sql += f' AND (u."{date_field}"::DATE - INTERVAL \'30 days\') <= %s'
                params.append(end_date)

            # Add search filter
            if search_string:
                sql += """
                    AND (
                        u."ticket_number" ILIKE %s OR 
                        p."first_name" ILIKE %s OR 
                        p."last_name" ILIKE %s OR 
                        v."plate" ILIKE %s
                    )
                """
                search_param = f"%{search_string}%"
                params.extend([search_param] * 4)
                
            if payment_status_type == 1:
                sql += ' AND pay."citationID" IS NOT NULL'
            elif payment_status_type == 2:
                sql += ' AND pay."citationID" IS NULL'

            sql += f' ORDER BY (u."{date_field}"::DATE - INTERVAL \'30 days\') ASC'

            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                raw_data = dictfetchall(cursor)

            rows = raw_data
            for row in rows:
                month_number = row.get("Month")
                if month_number:
                    row["Month"] = calendar.month_name[int(month_number)]

        elif mailer_type == 0:
            qs = sup_metadata.objects.filter(
                citation__station=station,
                isApproved=True
            ).select_related('citation', 'citation__person', 'citation__vehicle', 'citation__fine')

            if start_date_str and end_date_str:
                try:
                    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
                except Exception as e:
                    return JsonResponse({"statusCode":400, "message": "Invalid date format. Expected YYYY-MM-DD.", "errors": str(e)}, status=400)
                qs = qs.filter(timeApp__date__gte=start_date, timeApp__date__lte=end_date)

            if search_string:
                qs = qs.filter(
                    Q(citation__citationID__icontains=search_string) |
                    Q(citation__person__first_name__icontains=search_string) |
                    Q(citation__person__last_name__icontains=search_string) |
                    Q(citation__vehicle__plate__icontains=search_string)
                )

            qs = qs.annotate(
                year=ExtractYear('timeApp'),
                month=ExtractMonth('timeApp')
            )

            paid_exists = Exists(
                QuickPdPaidCitations.objects.filter(ticket_number=OuterRef('citation__citationID'))
            )

            qs = qs.annotate(
                due_amount=Case(
                    When(paid_exists, then=Value(Decimal('0.00'))),
                    default=F('citation__fine__fine'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                ),
                payment_status=Case(
                    When(paid_exists, then=Value("Paid")),
                    default=Value("Pending"),
                    output_field=CharField()
                )
            )
            
            if payment_status_type == 1:
                qs = qs.filter(payment_status="Paid")
            elif payment_status_type == 2:
                qs = qs.filter(payment_status="Pending")

            qs = qs.order_by('-timeApp')

            for record in qs:
                row = {
                    "Year": record.year,
                    "Month": calendar.month_name[int(record.month)] if record.month else "",
                    "Approved Date": record.timeApp.date(),
                    "Citation ID": record.citation.citationID,
                    "State": record.citation.person.state if record.citation.person and hasattr(record.citation.person, 'state') else "",
                    "Lic Plate": record.citation.vehicle.plate if record.citation.vehicle and hasattr(record.citation.vehicle, 'license_plate') else "",
                    "First Name": record.citation.person.first_name if record.citation.person else "",
                    "Last Name": record.citation.person.last_name if record.citation.person else "",
                    "Due Amount": record.due_amount,
                    "Due Date": record.timeApp.date() + timedelta(days=30) if record.timeApp else None,
                    "Payment Status": record.payment_status,
                }
                rows.append(row)


        else:
            return JsonResponse({"statusCode": 400, "message": "Invalid mailerType. Expected 0, 1, or 2.", "errors": None}, status=400)

        paginator = Paginator(rows, page_size)
        try:
            page_index = int(page_index)
        except Exception:
            page_index = 1
        page_obj = paginator.get_page(page_index)
        paginated_rows = page_obj.object_list
        # Generate CSV from paginated_rows
        if not rows:
            return Response(ServiceResponse({
                "statusCode" : 204,
                "message" : "No Content",
                "data" : None
            }))
        df = pd.DataFrame(rows)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        csv_buffer.close()
        base64_string = base64.b64encode(csv_string.encode("utf-8")).decode("utf-8")

        serializer = GetCSVBase64StringOutputModel({"base64String": base64_string})
        return Response(ServiceResponse({"statusCode":200, "message":"Success", "data": serializer.data}).data, status=200)


class GetXpressBillPaySummaryLevelReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=XpressBillPaySummaryLevelInputModel,
        responses={200: GetSummaryLevelReportDataResponseModel(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = XpressBillPaySummaryLevelInputModel(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)
        station_id = readToken.get('stationId')
        serializer_data = serializer.validated_data

        filter_type = serializer_data.get('filterType')
        start_date = serializer_data.get('startDate')
        end_date = serializer_data.get('endDate')
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)

        query_result = Xpress_bill_pay_report(filter_type, start_date, end_date, search_string,page_index,page_size,station_id,isDownload=False)
        reports = query_result['data']
        total_records = query_result['total_records']
        
        serialized_data = GetSummaryLevelReportDataResponseModel(reports, many=True).data
        paged_response = PagedResponse(
            page_index=page_index,
            page_size=page_size,
            total_records=total_records,
            data=serialized_data
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
        if paged_response.data is None:
            return Response(ServiceResponse({
                "statusCode" : 204,
                "message" : "No content",
                "data" : None
            }).data,status=200)
        
        return Response(response_data)
    

class GetXpressBillPayReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=XpressBillPaySummaryLevelInputModel,
        responses={200: GetCSVBase64StringOutputModel},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = XpressBillPaySummaryLevelInputModel(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)
        station_id = readToken.get('stationId')
        serializer_data = serializer.validated_data

        filter_type = serializer_data.get('filterType')
        start_date = serializer_data.get('startDate')
        end_date = serializer_data.get('endDate')
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)

        query_result = Xpress_bill_pay_report(filter_type, start_date, end_date, search_string,page_index,page_size,station_id,isDownload=True)
        reports = query_result['data']
        total_records = query_result['total_records']
        
        serialized_data = GetSummaryLevelReportDataResponseModel(reports, many=True).data
        paged_response = PagedResponse(
            page_index=page_index,
            page_size=page_size,
            total_records=total_records,
            data=serialized_data
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
        if not serialized_data:
            return Response(ServiceResponse({
                "statusCode" : 204,
                "message" : "No content",
                "data" : None
            }).data,status=200)
        
        df = pd.DataFrame(serialized_data)

        df.rename(columns={
            "year": "Year",
            "month": "Month",
            "approvedDate": "Approved Date",
            "totalApproved": "Total Approved",
            "paid": "Paid",
            "paidPercentage": "Paid Percentage"
        }, inplace=True)
        if filter_type == 1:
            df["Approved Date"] = pd.to_datetime(df["Approved Date"], format="%B %d %Y")
            df = df[["Year", "Month","Approved Date", "Total Approved", "Paid","Paid Percentage"]]
        elif filter_type == 2:
            df["Approved Date"] = pd.to_datetime(df["Approved Date"], format="%B %d %Y")
            df = df[["Year", "Month","Total Approved", "Paid","Paid Percentage"]]
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        csv_buffer.close()
        base64_string = base64.b64encode(csv_string.encode("utf-8")).decode("utf-8")
        serializer = GetCSVBase64StringOutputModel({"base64String": base64_string})

        return Response(ServiceResponse({"statusCode":200, "message":"Success", "data": serializer.data}).data, status=200)
    
class GetXpressBillPayCitationlevelReportView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=XpressBillPayCitationLevelReportInputSerializer,
        responses={200: CitationlevelReportItemSerializer},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        serializers = XpressBillPayCitationLevelReportInputSerializer(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializers.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializers.errors
            }).data, status=200)
        station_id = readToken.get('stationId')
        serializers_data = serializers.validated_data

        start_date = serializers_data.get('startDate')
        end_date = serializers_data.get('endDate')
        search_string = serializers_data.get('searchString', None)
        page_index = serializers_data.get('pageIndex', 1)
        page_size = serializers_data.get('pageSize', 10)
        payment_status_type = serializers_data.get('paymentStatusType', 0)

        query_result = xpress_bill_pay_citation_level_report_api(start_date, end_date, search_string,page_index,page_size,station_id,payment_status_type)
        
        paginator = Paginator(query_result, page_size)
        page_index = page_index if page_index <= paginator.num_pages else paginator.num_pages
        page_obj = paginator.get_page(page_index)
        
        return Response({
                "data": page_obj.object_list,
                "pageIndex": page_obj.number,
                "pageSize": page_size,
                "totalRecords": paginator.count,
                "hasNextPage": page_obj.has_next(),
                "hasPreviousPage": page_obj.has_previous(),
                "statusCode": 200,
                "message": "Success"
            })
    
class GetXpressBillPayCitationlevelReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=XpressBillPayCitationLevelReportInputSerializer,
        responses={200: "CSV file in base64 string"},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = XpressBillPayCitationLevelReportInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        start_date_str = filters.get("startDate")
        end_date_str = filters.get("endDate")
        search_string = filters.get("searchString")
        page_index = filters.get('pageIndex', 1)
        page_size = filters.get('pageSize', 10)
        payment_status_type =filters.get('paymentStatusType', 0)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")

        # Use same API that returns transformed data
        report_data = xpress_bill_pay_citation_level_report_api(
            start_date=start_date_str,
            end_date=end_date_str,
            search_string=search_string,
            page_index=page_index,
            page_size=page_size, 
            station_id=station_id,
            payment_status_type=payment_status_type
        )
        paginator = Paginator(report_data, page_size)
        page_index = page_index if page_index <= paginator.num_pages else paginator.num_pages
        page_obj = paginator.get_page(page_index)

        if not report_data:
            return Response(ServiceResponse({
                "statusCode":204,
                "message" : "No content",
                "data" : None
            }).data, status=200)
        # Then use only the current page's data
        df = pd.DataFrame(report_data)


        # Rename columns if necessary to human-readable format
        df.columns = [col.replace('_', ' ').title() for col in df.columns]

        # Convert to base64-encoded CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        csv_buffer.close()

        base64_string = base64.b64encode(csv_string.encode("utf-8")).decode("utf-8")

        output_serializer = GetCSVBase64StringOutputModel({"base64String": base64_string})
        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": output_serializer.data
        }).data, status=200)
    
class QuickPdReportSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=SummaryLevelInputModel,
        responses={200: "Summary report"},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        from django.db import connection
        import calendar

        serializer = SummaryLevelInputModel(data=request.data)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        start_date_str = filters.get("startDate")
        end_date_str = filters.get("endDate")
        filter_type = int(filters.get("filterType", 1))  # 1=day, 2=month
        mailer_type = filters.get("mailerType", 0)
        page_index = filters.get("pageIndex", 1)
        page_size = filters.get("pageSize", 10)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")
        station = Station.objects.filter(id=station_id).first()
        if not station:
            return Response({"statusCode": 404, "message": "Station not found", "errors": None}, status=404)

        def parse_date(date_str):
            try:
                # Handling both year-month format and full date format
                if date_str and len(date_str) == 7:  # Format like "YYYY-MM"
                    return datetime.datetime.strptime(date_str, "%Y-%m").date()
                return datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            except ValueError:
                return None

        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        if mailer_type in [0, 1, 2]:
            params = []
            date_filter = ""

            if mailer_type == 0:
                due_field = '"timeApp"'
                paid_table = 'quick_pd_paid_citations'
                mailer_count_condition = 'sm."isApproved" = TRUE AND c."station_id" = %s'
                params.append(station.id)
                join_condition = 'qpc."ticket_number" = c."citationID"'
            elif mailer_type == 1:
                due_field = '"first_mail_due_date"'
                paid_table = 'paid_citations'
                mailer_count_condition = 'u."pre_odr_mail_count" = 1'
                join_condition = 'pcd."citationID" = u."ticket_number"'
            elif mailer_type == 2:
                due_field = '"second_mail_due_date"'
                paid_table = 'paid_citations'
                mailer_count_condition = 'u."pre_odr_mail_count" = 2'
                join_condition = 'pcd."citationID" = u."ticket_number"'

            if filter_type == 1:
                group_by = "approved_date"
                date_format = "TO_CHAR(approved_date, 'MM/DD/YYYY')"
            else:
                group_by = "DATE_TRUNC('month', approved_date)"
                date_format = "TO_CHAR(DATE_TRUNC('month', approved_date), 'MM/YYYY')"

            if mailer_type == 0:
                sql = f"""
                WITH approved_data AS (
                    SELECT
                        ({due_field}::DATE) AS approved_date,
                        c."citationID",
                        CASE
                            WHEN qpc."ticket_number" IS NOT NULL THEN 'Paid'
                            ELSE 'Pending'
                        END AS payment_status,
                        CASE
                            WHEN qpc."ticket_number" IS NOT NULL THEN qpc."total_paid"
                            ELSE f."fine"
                        END AS amount
                    FROM sup_metadata sm
                    JOIN citation c ON sm."citation_id" = c."id"
                    JOIN fine f ON c."fine_id" = f."id"
                    LEFT JOIN {paid_table} qpc ON {join_condition}
                    WHERE {mailer_count_condition}
                )
                SELECT
                    {date_format} AS "approvedDate",
                    COUNT(*) AS "totalApproved",
                    COUNT(*) FILTER (WHERE payment_status = 'Paid') AS "paid",
                    COUNT(*) FILTER (WHERE payment_status = 'Pending') AS "unpaid",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Paid') * 100.0 / COUNT(*), 2) AS "paidPercentage",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Pending') * 100.0 / COUNT(*), 2) AS "unpaidPercentage",
                    SUM(CASE WHEN payment_status = 'Paid' THEN amount ELSE 0 END) AS "amountReceived",
                    SUM(CASE WHEN payment_status = 'Pending' THEN amount ELSE 0 END) AS "amountDues",
                    EXTRACT(MONTH FROM MIN(approved_date)) AS "month",
                    EXTRACT(YEAR FROM MIN(approved_date)) AS "year"
                FROM approved_data
                WHERE 1=1
                """
            else:
                sql = f"""
                WITH approved_data AS (
                    SELECT
                        ({due_field}::DATE - INTERVAL '30 days') AS approved_date,
                        u."ticket_number",
                        CASE
                            WHEN pcd."citationID" IS NOT NULL THEN 'Paid'
                            ELSE 'Pending'
                        END AS payment_status
                    FROM unpaid_citation u
                    LEFT JOIN citation c ON u."ticket_number" = c."citationID"
                    LEFT JOIN {paid_table} pcd ON {join_condition}
                    WHERE {mailer_count_condition}
                )
                SELECT
                    {date_format} AS "approvedDate",
                    COUNT(*) AS "totalApproved",
                    COUNT(*) FILTER (WHERE payment_status = 'Paid') AS "paid",
                    COUNT(*) FILTER (WHERE payment_status = 'Pending') AS "unpaid",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Paid') * 100.0 / COUNT(*), 2) AS "paidPercentage",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Pending') * 100.0 / COUNT(*), 2) AS "unpaidPercentage",
                    NULL AS "amountReceived",
                    NULL AS "amountDues",
                    EXTRACT(MONTH FROM MIN(approved_date)) AS "month",
                    EXTRACT(YEAR FROM MIN(approved_date)) AS "year"
                FROM approved_data
                WHERE 1=1
                """

            # Apply the date filters
            if start_date:
                date_filter += " AND approved_date >= %s"
                params.append(start_date)
            if end_date:
                # Ensure that if the end date is the last day of the month, we include the whole month
                end_date_adjusted = end_date.replace(day=calendar.monthrange(end_date.year, end_date.month)[1])
                date_filter += " AND approved_date <= %s"
                params.append(end_date_adjusted)

            sql += date_filter + f"""
            GROUP BY {group_by}
            ORDER BY {group_by} DESC
            """

            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                analysis_list = [dict(zip(columns, row)) for row in rows]

            for item in analysis_list:
                month_val = item.get("month")
                try:
                    month_num = int(month_val) if month_val else 0
                except:
                    month_num = 0
                item["month"] = calendar.month_name[month_num] if month_num and month_num <= 12 else "N/A"

                if "paidPercentage" in item and item["paidPercentage"] is not None:
                    item["paidPercentage"] = f"{item['paidPercentage']}%"
                if "unpaidPercentage" in item and item["unpaidPercentage"] is not None:
                    item["unpaidPercentage"] = f"{item['unpaidPercentage']}%"

        else:
            return Response({"statusCode": 400, "message": "Invalid mailerType.", "errors": None}, status=400)

        # Pagination
        paginator = Paginator(analysis_list, page_size)
        try:
            paginated_analysis = paginator.page(page_index)
        except PageNotAnInteger:
            paginated_analysis = paginator.page(1)
        except EmptyPage:
            paginated_analysis = paginator.page(paginator.num_pages)

        response_data = {
            "data": paginated_analysis.object_list,
            "pageIndex": paginated_analysis.number,
            "pageSize": page_size,
            "totalRecords": paginator.count,
            "hasNextPage": paginated_analysis.has_next(),
            "hasPreviousPage": paginated_analysis.has_previous(),
            "statusCode": 200,
            "message": "Success",
        }
        return Response(response_data)

class QuickPdReportSummaryDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=QuickPdReportSummaryDownloadInputSerializer,
        responses={200: GetCSVBase64StringOutputModel},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        from django.db import connection
        import calendar

        serializer = QuickPdReportSummaryDownloadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data

        start_date_str = filters.get("startDate")
        end_date_str = filters.get("endDate")
        filter_type = int(filters.get("filterType", 1))
        mailer_type = filters.get("mailerType", 0)

        readToken = user_information(request)
        if not isinstance(readToken, dict):
            return readToken

        station_id = readToken.get("stationId")
        station = Station.objects.filter(id=station_id).first()
        if not station:
            return JsonResponse({"statusCode": 404, "message": "Station not found", "errors": None}, status=404)

        def parse_date(date_str):
            try:
                # Handling both year-month format and full date format
                if date_str and len(date_str) == 7:  # Format like "YYYY-MM"
                    return datetime.datetime.strptime(date_str, "%Y-%m").date()
                return datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            except ValueError:
                return None

        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)

        if mailer_type in [0, 1, 2]:
            params = []
            date_filter = ""

            if mailer_type == 0:
                due_field = '"timeApp"'
                paid_table = 'quick_pd_paid_citations'
                mailer_count_condition = 'sm."isApproved" = TRUE AND c."station_id" = %s'
                params.append(station.id)
                join_condition = 'qpc."ticket_number" = c."citationID"'
            elif mailer_type == 1:
                due_field = '"first_mail_due_date"'
                paid_table = 'paid_citations'
                mailer_count_condition = 'u."pre_odr_mail_count" = 1'
                join_condition = 'pcd."citationID" = u."ticket_number"'
            elif mailer_type == 2:
                due_field = '"second_mail_due_date"'
                paid_table = 'paid_citations'
                mailer_count_condition = 'u."pre_odr_mail_count" = 2'
                join_condition = 'pcd."citationID" = u."ticket_number"'

            if filter_type == 1:
                group_by = "approved_date"
                date_format = "TO_CHAR(approved_date, 'MM/DD/YYYY')"
            else:
                group_by = "DATE_TRUNC('month', approved_date)"
                date_format = "TO_CHAR(DATE_TRUNC('month', approved_date), 'MM/YYYY')"

            if mailer_type == 0:
                sql = f"""
                WITH approved_data AS (
                    SELECT
                        ({due_field}::DATE) AS approved_date,
                        c."citationID",
                        CASE
                            WHEN qpc."ticket_number" IS NOT NULL THEN 'Paid'
                            ELSE 'Pending'
                        END AS payment_status,
                        CASE
                            WHEN qpc."ticket_number" IS NOT NULL THEN qpc."total_paid"
                            ELSE f."fine"
                        END AS amount
                    FROM sup_metadata sm
                    JOIN citation c ON sm."citation_id" = c."id"
                    JOIN fine f ON c."fine_id" = f."id"
                    LEFT JOIN {paid_table} qpc ON {join_condition}
                    WHERE {mailer_count_condition}
                )
                SELECT
                    {date_format} AS "approvedDate",
                    COUNT(*) AS "totalApproved",
                    COUNT(*) FILTER (WHERE payment_status = 'Paid') AS "paid",
                    COUNT(*) FILTER (WHERE payment_status = 'Pending') AS "unpaid",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Paid') * 100.0 / COUNT(*), 2) AS "paidPercentage",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Pending') * 100.0 / COUNT(*), 2) AS "unpaidPercentage",
                    SUM(CASE WHEN payment_status = 'Paid' THEN amount ELSE 0 END) AS "amountReceived",
                    SUM(CASE WHEN payment_status = 'Pending' THEN amount ELSE 0 END) AS "amountDues",
                    EXTRACT(MONTH FROM MIN(approved_date)) AS "month",
                    EXTRACT(YEAR FROM MIN(approved_date)) AS "year"
                FROM approved_data
                WHERE 1=1
                """
            else:
                sql = f"""
                WITH approved_data AS (
                    SELECT
                        ({due_field}::DATE - INTERVAL '30 days') AS approved_date,
                        u."ticket_number",
                        CASE
                            WHEN pcd."citationID" IS NOT NULL THEN 'Paid'
                            ELSE 'Pending'
                        END AS payment_status
                    FROM unpaid_citation u
                    LEFT JOIN citation c ON u."ticket_number" = c."citationID"
                    LEFT JOIN {paid_table} pcd ON {join_condition}
                    WHERE {mailer_count_condition}
                )
                SELECT
                    {date_format} AS "approvedDate",
                    COUNT(*) AS "totalApproved",
                    COUNT(*) FILTER (WHERE payment_status = 'Paid') AS "paid",
                    COUNT(*) FILTER (WHERE payment_status = 'Pending') AS "unpaid",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Paid') * 100.0 / COUNT(*), 2) AS "paidPercentage",
                    ROUND(COUNT(*) FILTER (WHERE payment_status = 'Pending') * 100.0 / COUNT(*), 2) AS "unpaidPercentage",
                    NULL AS "amountReceived",
                    NULL AS "amountDues",
                    EXTRACT(MONTH FROM MIN(approved_date)) AS "month",
                    EXTRACT(YEAR FROM MIN(approved_date)) AS "year"
                FROM approved_data
                WHERE 1=1
                """

            if start_date:
                date_filter += " AND approved_date >= %s"
                params.append(start_date)
            if end_date:
                # Ensure that if the end date is the last day of the month, we include the whole month
                end_date_adjusted = end_date.replace(day=calendar.monthrange(end_date.year, end_date.month)[1])
                date_filter += " AND approved_date <= %s"
                params.append(end_date_adjusted)
            sql += date_filter + f"""
            GROUP BY {group_by}
            ORDER BY {group_by} DESC
            """

            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                analysis_list = [dict(zip(columns, row)) for row in rows]

            for item in analysis_list:
                month_val = item.get("month")
                try:
                    month_num = int(month_val) if month_val else 0
                except:
                    month_num = 0
                item["monthName"] = calendar.month_name[month_num] if month_num and month_num <= 12 else "N/A"

                if "paidPercentage" in item and item["paidPercentage"] is not None:
                    item["paidPercentage"] = f"{item['paidPercentage']}%"
                if "unpaidPercentage" in item and item["unpaidPercentage"] is not None:
                    item["unpaidPercentage"] = f"{item['unpaidPercentage']}%"
        else:
            return JsonResponse({"statusCode": 400, "message": "Invalid mailerType.", "errors": None}, status=400)

        df = pd.DataFrame(analysis_list)

        if df.empty:
            return JsonResponse({"statusCode": 404, "message": "No records found.", "errors": None}, status=404)

        # Rename columns for clarity in CSV
        df.rename(columns={
            "approvedDate": "Approved Date",
            "totalApproved": "Total Approved",
            "paid": "Paid",
            "unpaid": "Unpaid",
            "paidPercentage": "Paid Percentage",
            "unpaidPercentage": "Unpaid Percentage",
            "amountReceived": "Amount Received",
            "amountDues": "Amount Dues",
            "monthName": "Month",
            "year": "Year"
        }, inplace=True)

        if filter_type == 2:
            df = df[["Year", "Month", "Total Approved", "Paid", "Unpaid", "Paid Percentage", "Unpaid Percentage", "Amount Received", "Amount Dues"]]
        else:
            df = df[["Year", "Month", "Approved Date", "Total Approved", "Paid", "Unpaid", "Paid Percentage", "Unpaid Percentage", "Amount Received", "Amount Dues"]]

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        csv_buffer.close()

        base64_string = base64.b64encode(csv_string.encode("utf-8")).decode("utf-8")
        output_serializer = GetCSVBase64StringOutputModel({"base64String": base64_string})

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": output_serializer.data,
            "totalRecords": len(analysis_list),
            "totalPages": 1,
            "currentPage": 1,
        }).data, status=200)
    
class GetAdjudicatedCitationCountView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetAdjudicatedCitationCountViewInputModel,
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        serializer = GetAdjudicatedCitationCountViewInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)

        data = serializer.validated_data
        from_date = data.get('adjFromDate')
        to_date = data.get('adjToDate')
        station_name = readToken.get('stationName')

        station = Station.objects.filter(name=station_name).first()
        if not station:
            return Response(ServiceResponse({
                "statusCode": 404,
                "message": "Station not found",
                "data": {}
            }).data, status=200)

        # Convert date strings to datetime objects if needed
        if isinstance(from_date, str) and from_date:
            from_date = datetime.datetime.strptime(from_date, "%Y-%m-%d")
        if isinstance(to_date, str) and to_date:
            to_date = datetime.datetime.strptime(to_date, "%Y-%m-%d") 

        query = Q(station=station)
        if from_date:
            query &= Q(timeAdj__gte=from_date)
        if to_date:
            query &= Q(timeAdj__lte=to_date)

        # Fetch relevant adj_metadata
        citation_qs = adj_metadata.objects.filter(query).values('video', 'image', 'tattile', 'citation')

        # Extract IDs
        video_ids = [item['video'] for item in citation_qs if item['video'] is not None]
        image_ids = [item['image'] for item in citation_qs if item['image'] is not None]
        tattile_ids = [item['tattile'] for item in citation_qs if item['tattile'] is not None]
        citation_ids = [item['citation'] for item in citation_qs if item['citation'] is not None]

        # Review bin and adjudication bin data
        review_bin_adj_data = ReviewBin.objects.filter(
            image__in=image_ids, video__in=video_ids, tattile__in=tattile_ids, is_adjudicated_in_review_bin=True
        )
        agency_adj_bin_data = AdjudicationBin.objects.filter(
            image__in=image_ids, video__in=video_ids, tattile__in=tattile_ids, is_adjudicated_in_adjudicationbin=True
        )

        # Collect IDs to exclude
        excluded_image_ids = set(review_bin_adj_data.values_list('image', flat=True)) | set(agency_adj_bin_data.values_list('image', flat=True))
        excluded_video_ids = set(review_bin_adj_data.values_list('video', flat=True)) | set(agency_adj_bin_data.values_list('video', flat=True))
        excluded_tattile_ids = set(review_bin_adj_data.values_list('tattile', flat=True)) | set(agency_adj_bin_data.values_list('tattile', flat=True))

        # Final adjudication_bin_data query with exclusions
        adjudication_bin_data = Citation.objects.filter(id__in=citation_ids).exclude(
            Q(image__in=excluded_image_ids) &
            Q(video__in=excluded_video_ids) &
            Q(tattile__in=excluded_tattile_ids)
        )

        # Aggregate results
        result = {
            "review_bin_adj_count": review_bin_adj_data.count(),
            "agency_adj_bin_data_count": agency_adj_bin_data.count(),
            "adjudication_bin_data_count": adjudication_bin_data.count()
        }

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": result
        }).data, status=200)
    
class GetXpressBillPaySplitCSVReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=XpressBillPaySummaryLevelInputModel,
        responses={200: GetSplitCSVBase64OutputModel},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = XpressBillPaySummaryLevelInputModel(data=request.data)
        readToken = user_information(request)

        if isinstance(readToken, Response):
            return readToken

        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)

        station_id = readToken.get('stationId')
        serializer_data = serializer.validated_data

        filter_type = serializer_data.get('filterType')
        start_date = serializer_data.get('startDate')
        end_date = serializer_data.get('endDate')

        query_result = Xpress_bill_pay_split_csv_reports(
            filter_type, start_date, end_date,
            search_string=None, page_index=1, page_size=100000,  # large page size to avoid pagination
            station_id=station_id, isDownload=True
        )

        new_approved = query_result.get("approvedCount", [])
        # edited_approved = query_result.get("editedApproved", [])
        if not new_approved:
            return Response(ServiceResponse({
                "statusCode": 204,
                "message": "No content",
                "data": None
            }).data, status=200)
        def generate_csv_base64(data, filter_type):
            if not data:
                return ""
            df = pd.DataFrame(data)
            df.rename(columns={
                "year": "Year",
                "month": "Month",
                "approvedDate": "Approved Date",
                "totalApproved": "Total Approved",
                "paid": "Paid",
                "paidPercentage": "Paid Percentage"
            }, inplace=True)
            if filter_type == 1:
                df["Approved Date"] = pd.to_datetime(df["Approved Date"], format="%B %d %Y")
                df = df[["Year", "Month", "Approved Date", "Total Approved", "Paid", "Paid Percentage"]]
            else:
                df = df[["Year", "Month", "Total Approved", "Paid", "Paid Percentage"]]
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_string = csv_buffer.getvalue()
            return base64.b64encode(csv_string.encode("utf-8")).decode("utf-8")

        new_csv_base64 = generate_csv_base64(new_approved, filter_type)
        # edited_csv_base64 = generate_csv_base64(edited_approved, filter_type)

        output_serializer = GetSplitCSVBase64OutputModel({
            "approvedCSV": new_csv_base64
        })

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": output_serializer.data
        }).data, status=200)
    
## GRAPH APIS

class MonthWiseCitationPaymentStatusGraph(APIView):

    @swagger_auto_schema(
        request_body=MonthWiseCitationPaymentStatusInputSerializer,
        responses={200: MonthWiseCitationPaymentStatusOutputSerializer(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = MonthWiseCitationPaymentStatusInputSerializer(data=request.data)
            readToken = user_information(request)
            if isinstance(readToken, Response):
                return readToken

            if not serializer.is_valid():
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid Request",
                    "data": serializer.errors
                }).data, status=200)

            station_id = readToken.get('stationId')
            serializer_data = serializer.validated_data
            month_filter = serializer_data.get('monthFilter')
            view_type = serializer_data.get('viewType', 0)

            data = month_wise_citation_payment_status(month_filter, view_type, station_id)

            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Success",
                "data": MonthWiseCitationPaymentStatusOutputSerializer(data, many=True).data
            }).data, status=200)

        except Exception as e:
            return Response(ServiceResponse({
                "statusCode": 500,
                "message": "Internal Server Error",
                "data": str(e)
            }).data, status=200)
        
class ApprovedDateAnalysisGraph(APIView):
    @swagger_auto_schema(
        request_body=ApprovedDateAnalysisInputSerializer,
        responses={200: ApprovedDateAnalysisOutputSerializer(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = ApprovedDateAnalysisInputSerializer(data=request.data)
            readToken = user_information(request)
            if isinstance(readToken, Response):
                return readToken
            if not serializer.is_valid():
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid Request",
                    "data": serializer.errors
                }).data, status=200)

            station_id = readToken.get('stationId')
            print(station_id,"station_id in here ")
            serializer_data = serializer.validated_data

            start_date = serializer_data.get('startDate')
            end_date = serializer_data.get('endDate')
            view_type = serializer_data.get('viewType', 0)

            data = approved_date_analysis_graph(start_date, end_date, station_id, view_type)

            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Success",
                "data": ApprovedDateAnalysisOutputSerializer(data, many=True).data
            }).data, status=200)

        except Exception as e:
            print(e,traceback.format_exc())
            return Response(ServiceResponse({
                "statusCode": 500,
                "message": "Internal Server Error",
                "data": str(e)
            }).data, status=200)
        
class TicketSummaryGraph(APIView):
    @swagger_auto_schema(
        request_body=TicketSummaryInputSerializer,
        responses={200: TicketSummaryOutputSerializer(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = TicketSummaryInputSerializer(data=request.data)
            readToken = user_information(request)
            if isinstance(readToken, Response):
                return readToken
            if not serializer.is_valid():
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid Request",
                    "data": serializer.errors
                }).data, status=200)

            station_id = readToken.get('stationId')
            serializer_data = serializer.validated_data
            dataType = serializer_data.get('dataType', 0)
            startDate = serializer_data.get('startDate')
            endDate = serializer_data.get('endDate')
            stationName = readToken.get('stationName')

            data = ticket_summary_graph(dataType, startDate, endDate, station_id, stationName)

            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Success",
                "data": TicketSummaryOutputSerializer(data, many=True).data
            }).data, status=200)

        except Exception as e:
            return Response(ServiceResponse({
                "statusCode": 500,
                "message": "Internal Server Error",
                "data": str(e)
            }).data, status=200)

class DuncanActivitySummaryGraph(APIView):
    @swagger_auto_schema(
        request_body=DuncanActivitySummaryInputSerializer,
        responses={200: DuncanActivitySummaryOutputSerializer(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
        )
    def post(self, request):
        try:
            serializer = DuncanActivitySummaryInputSerializer(data=request.data)
            readToken = user_information(request)
            if isinstance(readToken, Response):
                return readToken
            if not serializer.is_valid():
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid Request",
                    "data": serializer.errors
                }).data, status=200)

            station_id = readToken.get('stationId')
            serializer_data = serializer.validated_data
            startDate = serializer_data.get('startDate')
            endDate = serializer_data.get('endDate')
            stationName = readToken.get('stationName')

            data = duncan_activity_summary(startDate, endDate, station_id,stationName)

            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Success",
                "data": DuncanActivitySummaryOutputSerializer(data, many=True).data
            }).data, status=200)

        except Exception as e:
            return Response(ServiceResponse({
                "statusCode": 500,
                "message": "Internal Server Error",
                "data": str(e)
            }).data, status=200)
        
class PaidSummaryInDaysTableView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=PaidSummaryInputSerializer,
        responses={200: PaidSummaryOutputSerializer(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = PaidSummaryInputSerializer(data=request.data)
            readToken = user_information(request)
            if isinstance(readToken, Response):
                return readToken
            if not serializer.is_valid():
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid Request",
                    "data": serializer.errors
                }).data, status=200)

            station_id = readToken.get('stationId')
            serializer_data = serializer.validated_data
            startDate = serializer_data.get('startDate')
            endDate = serializer_data.get('endDate')
            stationName = readToken.get('stationName')
            view_type = serializer_data.get('viewType', 0)

            data = paid_summary_in_days_table(startDate, endDate, station_id, stationName,view_type)

            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Success",
                "data": data
            }).data, status=200)
        except Exception as e:
            return Response(ServiceResponse({
                "statusCode": 500,
                "message": "Internal Server Error",
                "data": str(e)
            }).data, status=200)
        
class SeventyPlusTicketSummaryGraph(APIView):
    @swagger_auto_schema(
        request_body=TicketSummaryInputSerializer,
        responses={200: TicketSummaryOutputSerializer(many=True)},
        tags=['QuickPDReports'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        try:
            serializer = TicketSummaryInputSerializer(data=request.data)
            readToken = user_information(request)

            if isinstance(readToken, Response):
                return readToken

            if not serializer.is_valid():
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "Invalid Request",
                    "data": serializer.errors
                }).data, status=200)

            station_id = readToken.get('stationId')
            station_name = readToken.get('stationName') 
            print(station_name,"station_name")

            serializer_data = serializer.validated_data
            dataType = serializer_data.get('dataType', 0)
            startDate = serializer_data.get('startDate')
            endDate = serializer_data.get('endDate')

            data = seventy_plus_ticket_summary_graph(
                dataType,
                startDate,
                endDate,
                station_id,
                station_name
            )

            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Success",
                "data": TicketSummaryOutputSerializer(data, many=True).data
            }).data, status=200)

        except Exception as e:
            return Response(ServiceResponse({
                "statusCode": 500,
                "message": "Internal Server Error",
                "data": str(e)
            }).data, status=200)
