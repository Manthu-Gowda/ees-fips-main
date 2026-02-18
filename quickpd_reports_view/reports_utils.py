from video.models import AdjudicationBin, ReviewBin, adj_metadata, sup_metadata, PaidCitationsData
from datetime import datetime,timedelta
from django.db.models.functions import TruncDate, TruncMonth, Coalesce
from django.db.models import Sum
import calendar
from django.core.paginator import Paginator
from datetime import datetime, timedelta, date
from django.db import connection
from .sqlqueries import *
from collections import defaultdict

def Xpress_bill_pay_report(filter_type, start_date, end_date, search_string, page_index=1, page_size=10, station_id=None,isDownload=False):
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
 
    CUTOFF_DATE = date(2025, 12, 1)
    JAN_2026 = date(2026, 1, 1)

    approved_citations = (
        sup_metadata.objects
        .filter(
            isApproved=True,
            citation__station_id=station_id
        )
        .annotate(
            final_time=Coalesce('originalTimeApp', 'timeApp')
        )
        .filter(
            Q(final_time__lt=CUTOFF_DATE) |
            Q(final_time__gte=CUTOFF_DATE, isMailCitationRejected=False, isEdited=False) | 
            Q(final_time__gte=JAN_2026)
        )
        .annotate(
            approved_month=TruncMonth('final_time'),
            approved_date=TruncDate('final_time')
        )
    )
 
    if start_date and end_date:
        approved_citations = approved_citations.filter(approved_date__range=[start_date, end_date])
    elif start_date:
        approved_citations = approved_citations.filter(approved_date__gte=start_date)
    elif end_date:
        approved_citations = approved_citations.filter(approved_date__lte=end_date)
 
    report_data = []
    citation_cache = {}  # To store citation IDs and prevent multiple DB hits
    # approved_citations = approved_citations.filter(
    #     citation__current_citation_status="OR"
    # )
    if filter_type == 2:  # Monthly
        grouped_data = (
            approved_citations.values('approved_month')
            .order_by('approved_month')
            .distinct()
        )
 
        for group in grouped_data:
            approved_month = group['approved_month']
            approved_year = approved_month.year
            approved_month_num = approved_month.month
 
            latest_approved_date = approved_citations.filter(
                timeApp__month=approved_month_num,
                timeApp__year=approved_year
            ).order_by('-final_time').values_list('final_time', flat=True).first()
 
            citation_ids = list(approved_citations.filter(
                final_time__month=approved_month_num,
                final_time__year=approved_year
            ).values_list('citation__citationID', flat=True))
 
            citation_cache[(approved_year, approved_month_num)] = citation_ids
 
            total_citations = len(citation_ids)
            total_paid_citations = PaidCitationsData.objects.filter(citationID__in=citation_ids).count()
 
            paid_percentage = (total_paid_citations / total_citations) * 100 if total_citations else 0
            unpaid_percentage = 100 - paid_percentage if total_citations else 0
 
            report_data.append({
                'year': str(approved_year),
                'month': calendar.month_name[approved_month_num],
                'approvedDate': latest_approved_date.strftime("%B {day} %Y").format(day=latest_approved_date.day) if latest_approved_date else None,
                'totalApproved': total_citations,
                'paid': total_paid_citations,
                'unPaid': total_citations - total_paid_citations,
                'paidPercentage': f"{paid_percentage:.2f}%",
                'unPaidPercentage': round(unpaid_percentage, 2),
                'amountreceived': PaidCitationsData.objects.filter(citationID__in=citation_ids).aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
                'amountDues': 0,
            })
 
    elif filter_type == 1:  # Daily
        grouped_data = (
            approved_citations.values('approved_date')
            .order_by('approved_date')
            .distinct()
        )
 
        for group in grouped_data:
            approved_date = group['approved_date']
            approved_year = approved_date.year
            approved_month_num = approved_date.month
            approved_day = approved_date.day
 
            # Use final_time for filtering
            citation_ids = list(
                approved_citations.filter(
                    final_time__year=approved_year,
                    final_time__month=approved_month_num,
                    final_time__day=approved_day
                ).values_list('citation__citationID', flat=True)
            )
 
            total_citations = len(citation_ids)
            total_paid_citations = PaidCitationsData.objects.filter(citationID__in=citation_ids).count()
 
            paid_percentage = (total_paid_citations / total_citations) * 100 if total_citations else 0
            unpaid_percentage = 100 - paid_percentage if total_citations else 0
 
            report_data.append({
                'year': str(approved_year),
                'month': calendar.month_name[approved_month_num],
                'approvedDate': approved_date.strftime("%B {day} %Y").format(day=approved_date.day) if approved_date else None,
                'approved_date_obj': approved_date,
                'totalApproved': total_citations,
                'paid': total_paid_citations,
                'unPaid': total_citations - total_paid_citations,
                'paidPercentage': f"{paid_percentage:.2f}%",
                'unPaidPercentage': round(unpaid_percentage, 2),
                'amountreceived': PaidCitationsData.objects.filter(citationID__in=citation_ids).aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
                'amountDues': 0,
            })
 
    # Sort the data in **ascending order**
    report_data = sorted(report_data, key=lambda x: x['approved_date_obj']) if filter_type == 1 else sorted(report_data, key=lambda x: (x['year'], list(calendar.month_name).index(x['month']), x['approvedDate']))
 
    if isDownload:
        return {
            "data": report_data,
            "total_records": len(report_data),
            "has_next_page": False,
            "has_previous_page": False,
            "current_page": 1,
            "total_pages": 1,
        }
    # Apply Pagination
    paginator = Paginator(report_data, page_size)
    page_obj = paginator.get_page(page_index)
 
    return {
        "data": list(page_obj.object_list),
        "total_records": paginator.count,
        "has_next_page": page_obj.has_next(),
        "has_previous_page": page_obj.has_previous(),
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
    }

def dictfetchall(cursor):
    "Return all rows from a cursor as a list of dicts"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def format_date(date_obj):
    return date_obj.strftime('%Y-%m-%d') if date_obj else None

def xpress_bill_pay_citation_level_report_api(start_date, end_date, search_string,
                                               page_index=1, page_size=10, station_id=None, payment_status_type=0):
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    sql = """
    SELECT 
        EXTRACT(YEAR FROM sm."timeApp") AS "Year",
        EXTRACT(MONTH FROM sm."timeApp") AS "Month",
        sm."timeApp" AS "Approved Date",
        c."citationID" AS "Citation ID",
        st."ab" AS "State",
        v."plate" AS "Lic Plate",
        p."first_name" AS "First Name",
        p."last_name" AS "Last Name",
        f."fine" AS "Due Amount",
        qpd."arraignment_date" AS "Due Date",
        CASE 
            WHEN pc."citationID" IS NOT NULL THEN 'Paid' 
            ELSE 'Pending' 
        END AS "Payment Status",
        NULL AS "Sent to Pre-Odr 2"
    FROM citation c
    LEFT JOIN (
        SELECT DISTINCT ON ("citation_id") * FROM sup_metadata 
        WHERE "isApproved" = TRUE
    ) sm ON c."id" = sm."citation_id"
    LEFT JOIN vehicle v ON c."vehicle_id" = v."id"
    LEFT JOIN person p ON c."person_id" = p."id"
    LEFT JOIN fine f ON c."fine_id" = f."id"
    LEFT JOIN state st ON v."lic_state_id" = st."id"
    LEFT JOIN (
        SELECT DISTINCT ON ("ticket_num") * FROM quickpd
    ) qpd ON c."citationID" = qpd."ticket_num"
    LEFT JOIN paid_citations pc ON c."citationID" = pc."citationID"
    WHERE c."isApproved" = TRUE 
      AND c."isRejected" = FALSE
      AND c."station_id" = %s
    """
    params = [station_id]

    if start_date:
        sql += " AND sm.\"timeApp\" >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND sm.\"timeApp\" <= %s"
        params.append(end_date)
    if search_string:
        sql += """
        AND (
            c."citationID" ILIKE %s OR 
            p."first_name" ILIKE %s OR 
            p."last_name" ILIKE %s OR 
            v."plate" ILIKE %s
        )
        """
        search_param = f"%{search_string}%"
        params.extend([search_param] * 4)

    if payment_status_type == 1:
        sql += " AND pc.\"citationID\" IS NOT NULL"
    elif payment_status_type == 2:
        sql += " AND pc.\"citationID\" IS NULL"
    
    sql += " ORDER BY sm.\"timeApp\" ASC"

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        all_rows = dictfetchall(cursor)

    # Transform data
    transformed = []
    for row in all_rows:
        approved_date_obj = row.get("Approved Date")
        if approved_date_obj:
            formatted_date = approved_date_obj.strftime("%B {day} %Y").format(day=approved_date_obj.day)
            formatted_month = approved_date_obj.strftime("%B")
        else:
            formatted_date = None
            formatted_month = row.get("Month")
        # Format due date correctly
        due_date_raw = row.get("Due Date")
        due_date_formatted = None
        if isinstance(due_date_raw, (datetime, date)):
            due_date_formatted = due_date_raw.strftime("%Y-%m-%d")
        elif isinstance(due_date_raw, str):
            try:
                parsed_due_date = datetime.strptime(due_date_raw, "%m%d%Y")  # e.g., "08292024"
                due_date_formatted = parsed_due_date.strftime("%Y-%m-%d")
            except ValueError:
                due_date_formatted = None 
        transformed.append({
            "year": row.get("Year"),
            "month": formatted_month,
            "approvedDate": formatted_date,
            "citationId": row.get("Citation ID"),
            "state": row.get("State"),
            "licencePlate": row.get("Lic Plate"),
            "firstName": row.get("First Name"),
            "lastName": row.get("Last Name"),
            "dueAmount": row.get("Due Amount"),
            "dueDate": due_date_formatted,
            "paymentStatus": row.get("Payment Status"),
        })

        
    return transformed
def Xpress_bill_pay_split_csv_reports(filter_type, start_date, end_date, search_string, page_index=1, page_size=10, station_id=None, isDownload=False):
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    approved_citations = (
        sup_metadata.objects.filter(
            isApproved=True,
            citation__station_id=station_id
        )
        .annotate(
            final_time=Coalesce('originalTimeApp', 'timeApp')
        )
        .annotate(
            approved_month=TruncMonth('final_time'),
            approved_date=TruncDate('final_time')
        )
    )

    if start_date and end_date:
        approved_citations = approved_citations.filter(approved_date__range=[start_date, end_date])
    elif start_date:
        approved_citations = approved_citations.filter(approved_date__gte=start_date)
    elif end_date:
        approved_citations = approved_citations.filter(approved_date__lte=end_date)

    # Split into New Approved and Edited Approved
    # new_approved = approved_citations.filter(citation__current_citation_status='OR')
    # edited_approved = approved_citations.exclude(citation__current_citation_status='OR')

    def group_data(queryset, filter_type):
        report_data = []

        if filter_type == 2:  # Monthly
            grouped = queryset.values('approved_month').distinct().order_by('approved_month')
            for group in grouped:
                date_val = group['approved_month']
                year = date_val.year
                month = date_val.month

                filtered = queryset.filter(final_time__year=year, final_time__month=month)
                citation_ids = list(filtered.values_list('citation__citationID', flat=True))
                paid_count = PaidCitationsData.objects.filter(citationID__in=citation_ids).count()
                total = len(citation_ids)
                paid_percent = (paid_count / total * 100) if total else 0

                latest_date = filtered.order_by('-final_time').values_list('final_time', flat=True).first()

                report_data.append({
                    'year': str(year),
                    'month': calendar.month_name[month],
                    'approvedDate': latest_date.strftime("%B {day} %Y").format(day=latest_date.day) if latest_date else None,
                    'totalApproved': total,
                    'paid': paid_count,
                    'paidPercentage': f"{paid_percent:.2f}%",
                    'approved_date_obj': latest_date
                })

        else:  # Daily
            grouped = queryset.values('approved_date').distinct().order_by('approved_date')
            for group in grouped:
                date_val = group['approved_date']
                year = date_val.year
                month = date_val.month
                day = date_val.day

                filtered = queryset.filter(
                    final_time__year=year,
                    final_time__month=month,
                    final_time__day=day
                )
                citation_ids = list(filtered.values_list('citation__citationID', flat=True))
                paid_count = PaidCitationsData.objects.filter(citationID__in=citation_ids).count()
                total = len(citation_ids)
                paid_percent = (paid_count / total * 100) if total else 0

                report_data.append({
                    'year': str(year),
                    'month': calendar.month_name[month],
                    'approvedDate': date_val.strftime("%B {day} %Y").format(day=day),
                    'totalApproved': total,
                    'paid': paid_count,
                    'paidPercentage': f"{paid_percent:.2f}%",
                    'approved_date_obj': date_val
                })

        # Sort the results
        if filter_type == 1:
            report_data.sort(key=lambda x: x['approved_date_obj'])
        else:
            report_data.sort(key=lambda x: (x['year'], list(calendar.month_name).index(x['month']), x['approvedDate']))

        return report_data

    return {
        "approvedCount": group_data(approved_citations, filter_type),
        # "editedApproved": group_data(edited_approved, filter_type)
    }

## GRAPH FUNCTIONS

from dateutil.relativedelta import relativedelta
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.db.models.functions import TruncMonth
from django.db.models import Sum
import calendar

def month_wise_citation_payment_status(month_filter, view_type, station_id):
    from django.db import connection
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    current_date = datetime.now()

    try:
        duration_months = int(month_filter) if month_filter else 6
    except ValueError:
        raise ValueError("Invalid monthFilter. Must be a number.")

    start_date = (current_date - relativedelta(months=duration_months - 1)).replace(day=1)
    end_date = current_date

    sql = """
    WITH month_series AS (
        SELECT generate_series(
            date_trunc('month', %s::date),
            date_trunc('month', %s::date),
            interval '1 month'
        )::date AS month_start
    ),
    approved_data AS (
        SELECT 
            date_trunc('month', COALESCE(sm."originalTimeApp", sm."timeApp"))::date AS approved_month,
            COUNT(DISTINCT c."citationID") AS total_approved,
            COUNT(DISTINCT pcd."citationID") AS total_paid,
            COALESCE(SUM(pcd.paid_amount), 0) AS amount_received
        FROM sup_metadata sm
        JOIN citation c ON sm.citation_id = c.id
        LEFT JOIN paid_citations pcd ON pcd."citationID" = c."citationID"
        WHERE sm."isApproved" = TRUE
        AND (
            COALESCE(sm."originalTimeApp", sm."timeApp") < DATE '2025-12-01'
        OR (
                COALESCE(sm."originalTimeApp", sm."timeApp") >= DATE '2025-12-01'
                AND sm."isEdited" = FALSE
                AND sm."isMailCitationRejected" = FALSE
            )
        OR (
            COALESCE(sm."originalTimeApp", sm."timeApp") >= DATE '2026-01-01'
            )
        )
          AND c.station_id = %s
          AND date_trunc('month', COALESCE(sm."originalTimeApp", sm."timeApp")) 
              BETWEEN date_trunc('month', %s::date) AND date_trunc('month', %s::date)
        GROUP BY date_trunc('month', COALESCE(sm."originalTimeApp", sm."timeApp"))
    )
    SELECT
        ms.month_start,
        EXTRACT(YEAR FROM ms.month_start)::text AS year,
        TO_CHAR(ms.month_start, 'FMMonth') AS month,
        COALESCE(ad.total_approved, 0) AS totalApproved,
        COALESCE(ad.total_paid, 0) AS paid,
        COALESCE(ad.total_approved, 0) - COALESCE(ad.total_paid, 0) AS unPaid,
        ad.amount_received AS amountreceived,
        0 AS amountDues,
        CASE 
            WHEN ad.total_approved > 0 
            THEN ROUND((ad.total_paid::numeric / ad.total_approved::numeric) * 100, 2)
            ELSE 0
        END AS paidPercentage,
        CASE 
            WHEN ad.total_approved > 0 
            THEN ROUND(100 - ((ad.total_paid::numeric / ad.total_approved::numeric) * 100), 2)
            ELSE 0
        END AS unPaidPercentage
    FROM month_series ms
    LEFT JOIN approved_data ad ON ms.month_start = ad.approved_month
    ORDER BY ms.month_start;
    """

    params = [start_date, end_date, station_id, start_date, end_date]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    report_data = []
    for row in rows:
        report_data.append({
            "year": row[1],
            "month": row[2],
            "totalApproved": row[3],
            "paid": row[4],
            "unPaid": row[5],
            "amountreceived": float(row[6] or 0),  # Fix NoneType issue
            "amountDues": row[7],
            "paidPercentage": f"{row[8]:.2f}%" if view_type == 1 else None,
            "unPaidPercentage": f"{row[9]:.2f}%" if view_type == 1 else None,
        })

    return report_data

def approved_date_analysis_graph(start_date, end_date, station_id, view_type):
    today = datetime.now().date()

    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid start_date format, expected YYYY-MM-DD")
    else:
        start_date = today - timedelta(days=29)

    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError("Invalid end_date format, expected YYYY-MM-DD")
    else:
        end_date = today

    sql = approved_date_analysis_graph_query

    params = [
        start_date,
        end_date,
        station_id,
        start_date,
        end_date
    ]

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    report_data = []
    for row in rows:
        if view_type == 0:  # Original flow
            report_data.append({
                "approvedDate": " ".join(word if word else "" for word in str(row[3]).split()),
                "year": row[1],
                "month": row[2].strip(),
                "totalApproved": row[4],
                "paid": row[5],
                "unPaid": row[6],
                "paidPercentage": row[7],
                "unPaidPercentage": row[8],
                "amountreceived": float(row[9]) if row[9] is not None else 0,
                "amountDues": row[10]
            })
        elif view_type == 1:  # Show only percentages
            report_data.append({
                "approvedDate": " ".join(word if word else "" for word in str(row[3]).split()),
                "totalApproved": row[4],
                "year": row[1],
                "month": row[2].strip(),
                "paidPercentage": f"{row[7]}%",
                "unPaidPercentage": f"{row[8]}%"
            })

    return report_data

from datetime import datetime, timedelta
from django.db.models import Q, Count
from video.models import Data, Tattile

def ticket_summary_graph(dataType, start_date, end_date, station_id, station_name):
    today = datetime.today().date()

    if not start_date:
        start_date = today - timedelta(days=29)
    elif isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = today
    elif isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    date_range = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    video_data_map = {}
    tattile_data_map = {}

    if dataType in [0, 1]:
        start_date_str = start_date.strftime('%y%m%d')
        end_date_str = end_date.strftime('%y%m%d')    

        video_qs = Data.objects.filter(
            DATE__gte=start_date_str,
            DATE__lte=end_date_str,
            STATION__iexact=station_name
        )

        video_per_day = video_qs.values('DATE').annotate(
            count=Count('VIDEO_NAME', distinct=True)
        )

        video_data_map = {
            datetime.strptime(entry['DATE'], '%y%m%d').date(): entry['count']
            for entry in video_per_day
        }

    if dataType in [0, 2]:
        tattile_qs = Tattile.objects.filter(
            station_id=station_id,
            image_time__date__gte=start_date,
            image_time__date__lte=end_date
        )

        tattile_per_day = tattile_qs.values('image_time__date').annotate(
            count=Count('ticket_id', distinct=True)
        )

        tattile_data_map = {
            entry['image_time__date']: entry['count']
            for entry in tattile_per_day
        }

    result = []
    for single_date in date_range:
        result.append({
            "approvedDate": single_date.strftime('%Y-%m-%d'),
            "dockerUploadedVideos": video_data_map.get(single_date, 0),
            "tattileImageUploadCount": tattile_data_map.get(single_date, 0)
        })

    return result


def duncan_activity_summary(start_date, end_date, station_id, station_name):
    today = datetime.now().date()

    if not start_date or str(start_date).strip() == "":
        start_date = today - timedelta(days=29)
    elif isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date or str(end_date).strip() == "":
        end_date = today
    elif isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    adj_entries = adj_metadata.objects.filter(
        station__id=station_id,
        station__name__iexact=station_name,
        timeAdj__date__gte=start_date,
        timeAdj__date__lte=end_date
    ).values(
        "id", "timeAdj", "video_id", "image_id", "tattile_id", "citation_id"
    )

    if not adj_entries:
        return []  # No records → empty list

    # Step 2: Collect all IDs for batch lookups
    image_ids = {e["image_id"] for e in adj_entries if e["image_id"]}
    video_ids = {e["video_id"] for e in adj_entries if e["video_id"]}
    tattile_ids = {e["tattile_id"] for e in adj_entries if e["tattile_id"]}

    # Step 3: Batch fetch Review Bin and Agency Bin matches
    review_bin_set = set(
        ReviewBin.objects.filter(
            image_id__in=image_ids,
            video_id__in=video_ids,
            tattile_id__in=tattile_ids,
            is_adjudicated_in_review_bin=True
        ).values_list("image_id", "video_id", "tattile_id")
    )

    agency_bin_set = set(
        AdjudicationBin.objects.filter(
            image_id__in=image_ids,
            video_id__in=video_ids,
            tattile_id__in=tattile_ids,
            is_adjudicated_in_adjudicationbin=True
        ).values_list("image_id", "video_id", "tattile_id")
    )

    # Step 4: Prepare date-wise counts only for dates with data
    counts_by_date = defaultdict(lambda: {
        "approvedDate": "",
        "ticketsAdjudicatedInAgencyAdjudicationBin": 0,
        "ticketsAdjudicatedInAdjudicatorViewBin": 0,
        "ticketsAdjudicatedInReviewBin": 0
    })

    for e in adj_entries:
        approved_date = e["timeAdj"].date().strftime('%Y-%m-%d')
        key_tuple = (e["image_id"], e["video_id"], e["tattile_id"])

        if key_tuple in review_bin_set:
            counts_by_date[approved_date]["ticketsAdjudicatedInReviewBin"] += 1
        elif key_tuple in agency_bin_set:
            counts_by_date[approved_date]["ticketsAdjudicatedInAgencyAdjudicationBin"] += 1
        else:
            counts_by_date[approved_date]["ticketsAdjudicatedInAdjudicatorViewBin"] += 1

        counts_by_date[approved_date]["approvedDate"] = approved_date

    # Step 5: Return results sorted by date (only with data)
    return [counts_by_date[d] for d in sorted(counts_by_date)]

def paid_summary_in_days_table(start_date, end_date, station_id, station_name, view_type):
    today = datetime.now().date()

    if not start_date or str(start_date).strip() == "":
        start_date = today - timedelta(days=29)
    elif isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date or str(end_date).strip() == "":
        end_date = today
    elif isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    
    #   AND c."current_citation_status" = 'OR'

    query = """
    WITH approved_data AS (
        SELECT 
            DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) AS approved_date,
            COUNT(DISTINCT c."citationID") AS total_approved
        FROM sup_metadata sm
        JOIN citation c ON sm.citation_id = c.id
        WHERE sm."isApproved" = TRUE
        AND (
            COALESCE(sm."originalTimeApp", sm."timeApp") < DATE '2025-12-01'
        OR (
                COALESCE(sm."originalTimeApp", sm."timeApp") >= DATE '2025-12-01'
                AND sm."isEdited" = FALSE
                AND sm."isMailCitationRejected" = FALSE
            )
        OR (
            COALESCE(sm."originalTimeApp", sm."timeApp") >= DATE '2026-01-01'
            )
        )
          AND c.station_id = %s
          AND DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) BETWEEN %s AND %s
        GROUP BY DATE(COALESCE(sm."originalTimeApp", sm."timeApp"))
    ),
    paid_buckets AS (
        SELECT 
            DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) AS approved_date,
            COUNT(DISTINCT CASE WHEN p.transaction_date BETWEEN DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) 
                                  AND DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '7 days'
                                THEN p."citationID" END) AS paid_0_7,
            COUNT(DISTINCT CASE WHEN p.transaction_date > DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '7 days'
                                 AND p.transaction_date <= DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '15 days'
                                THEN p."citationID" END) AS paid_8_15,
            COUNT(DISTINCT CASE WHEN p.transaction_date > DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '15 days'
                                 AND p.transaction_date <= DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '30 days'
                                THEN p."citationID" END) AS paid_16_30,
            COUNT(DISTINCT CASE WHEN p.transaction_date > DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '30 days'
                                 AND p.transaction_date <= DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '60 days'
                                THEN p."citationID" END) AS paid_31_60,
            COUNT(DISTINCT CASE WHEN p.transaction_date > DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) + INTERVAL '60 days'
                                THEN p."citationID" END) AS paid_after_60
        FROM sup_metadata sm
        JOIN citation c ON sm.citation_id = c.id
        LEFT JOIN paid_citations p ON p."citationID" = c."citationID"
        WHERE sm."isApproved" = TRUE
          AND c.station_id = %s
          AND DATE(COALESCE(sm."originalTimeApp", sm."timeApp")) BETWEEN %s AND %s
        GROUP BY DATE(COALESCE(sm."originalTimeApp", sm."timeApp"))
    )
    SELECT
        ad.approved_date AS "approvedDate",
        ad.total_approved AS "totalApprovedCitations",
        pb.paid_0_7 AS "paidBetweenZeroToSevenDays",
        pb.paid_8_15 AS "paidBetweenEightToFifteenDays",
        pb.paid_16_30 AS "paidBetweenSixteenToThirtyDays",
        pb.paid_31_60 AS "paidBetweenThirtyToSixtyDays",
        pb.paid_after_60 AS "paidAfterSixtyDays",
        (pb.paid_0_7 + pb.paid_8_15 + pb.paid_16_30 + pb.paid_31_60 + pb.paid_after_60) AS "totalPaid",
        CASE 
            WHEN ad.total_approved > 0 THEN 
                ROUND(
                    ((pb.paid_0_7 + pb.paid_8_15 + pb.paid_16_30 + pb.paid_31_60 + pb.paid_after_60)::numeric 
                    / ad.total_approved::numeric) * 100, 
                    2
                )
            ELSE 0 
        END AS "totalPaidPercentage"
    FROM approved_data ad
    JOIN paid_buckets pb ON ad.approved_date = pb.approved_date
    ORDER BY ad.approved_date;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [station_id, start_date, end_date, station_id, start_date, end_date])
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for row in results:
        if view_type == 0:
            row["totalPaidPercentage"] = f"{row['totalPaidPercentage']}%"
        elif view_type == 1:
            total_approved = row["totalApprovedCitations"] or 0
            if total_approved > 0:
                row["paidBetweenZeroToSevenDays"] = f"{round((row['paidBetweenZeroToSevenDays']/total_approved)*100, 2)}%"
                row["paidBetweenEightToFifteenDays"] = f"{round((row['paidBetweenEightToFifteenDays']/total_approved)*100, 2)}%"
                row["paidBetweenSixteenToThirtyDays"] = f"{round((row['paidBetweenSixteenToThirtyDays']/total_approved)*100, 2)}%"
                row["paidBetweenThirtyToSixtyDays"] = f"{round((row['paidBetweenThirtyToSixtyDays']/total_approved)*100, 2)}%"
                row["paidAfterSixtyDays"] = f"{round((row['paidAfterSixtyDays']/total_approved)*100, 2)}%"
                row["totalPaid"] = f"{round((row['totalPaid']/total_approved)*100, 2)}%"
                row["totalPaidPercentage"] = f"{row['totalPaidPercentage']}%"
            else:
                row["paidBetweenZeroToSevenDays"] = "0%"
                row["paidBetweenEightToFifteenDays"] = "0%"
                row["paidBetweenSixteenToThirtyDays"] = "0%"
                row["paidBetweenThirtyToSixtyDays"] = "0%"
                row["paidAfterSixtyDays"] = "0%"
                row["totalPaid"] = "0%"
                row["totalPaidPercentage"] = "0%"

    return results


def seventy_plus_ticket_summary_graph(dataType, start_date, end_date, station_id, station_name):

    cutoff_date = datetime(2025, 5, 8).date()
    today = datetime.today().date()
    DEFAULT_WINDOW_DAYS = 30

    user_start = start_date
    user_end = end_date

    if user_start:
        start_date = datetime.strptime(user_start, "%Y-%m-%d").date()
    else:
        start_date = None

    if user_end:
        end_date = datetime.strptime(user_end, "%Y-%m-%d").date()
    else:
        end_date = None

    if not user_start and not user_end:

        thirty_days_back = today - timedelta(days=DEFAULT_WINDOW_DAYS)

        start_date = max(cutoff_date, thirty_days_back)
        end_date = today

    elif user_start and user_end:
        pass

    else:
        if user_start and not user_end:
            end_date = today

        if user_end and not user_start:
            start_date = cutoff_date

    date_range = [
        start_date + timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]

    video_data_map = {}
    tattile_data_map = {}

    if dataType in [0, 1]:
        start_str = start_date.strftime('%y%m%d')
        end_str = end_date.strftime('%y%m%d')

        video_qs = Data.objects.filter(
            DATE__gte=start_str,
            DATE__lte=end_str,
            STATION__iexact=station_name,
            SPEED__gte=70
        )

        video_per_day = video_qs.values("DATE").annotate(
            count=Count("VIDEO_NAME", distinct=True)
        )

        video_data_map = {
            datetime.strptime(entry["DATE"], "%y%m%d").date(): entry["count"]
            for entry in video_per_day
        }

    if dataType in [0, 2]:
        tattile_qs = Tattile.objects.filter(
            station_id=station_id,
            measured_speed__gte=70,
            image_time__date__gte=start_date,
            image_time__date__lte=end_date
        )

        tattile_per_day = tattile_qs.values("image_time__date").annotate(
            count=Count("id", distinct=True)
        )

        tattile_data_map = {
            entry["image_time__date"]: entry["count"]
            for entry in tattile_per_day
        }

    result = []
    for day in date_range:
        result.append({
            "approvedDate": day.strftime('%Y-%m-%d'),
            "dockerUploadedVideos": video_data_map.get(day, 0),
            "tattileImageUploadCount": tattile_data_map.get(day, 0)
        })

    return result