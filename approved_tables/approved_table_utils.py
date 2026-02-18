from datetime import datetime,timedelta
from django.db.models import Q, Exists, OuterRef
from django.core.paginator import Paginator
from video.citations.versioning_utils import get_latest_fine_from_versioning
from video.models import *
from ees.utils import s3_get_file, upload_to_s3
import base64
from django.template.loader import get_template
import os
from decouple import config as ENV_CONFIG
import pdfkit
from typing import Optional
from django.db.models import Value
from django.db.models.functions import Concat, Lower
 
TEMP_PDF_DIR = ENV_CONFIG("TEMP_PDF_DIR")
BASE_DIR= ENV_CONFIG("BASE_DIR")
path_to_wkhtmltopdf = ENV_CONFIG("PATH_TO_WKHTMLTOPDF")
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
template_hudson = get_template("hudson-pdf.html")

# def citation_data_for_approved_table(date_type, from_date, to_date, search_string, page_index=1, page_size=10, station_id=None):
#     if isinstance(from_date, str):
#         from_date = datetime.strptime(from_date, "%Y-%m-%d")
#     if isinstance(to_date, str):
#         to_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

#     from_date_str = from_date if from_date else None
#     to_date_str = to_date if to_date else None

#     query = Q()
#     if date_type == 1:
#         if from_date:
#             query &= Q(captured_date__gte=from_date_str)
#         if to_date:
#             query &= Q(captured_date__lte=to_date_str)
#     elif date_type == 2:
#         if from_date:
#             query &= Q(datetime__gte=from_date_str)
#         if to_date:
#             query &= Q(datetime__lte=to_date_str)
#     else:
#         return "Invalid date type. It should be 1 or 2."

#     if search_string:
#         search_string = search_string.lower().replace(" ", "")
#         query &= (
#             Q(citationID__icontains=search_string) |
#             Q(person__first_name__icontains=search_string) |
#             Q(person__last_name__icontains=search_string) |
#             Q(vehicle__plate__icontains=search_string)
#         )
#     citations = Citation.objects.filter(query, isApproved=True, station_id=station_id) \
#         .select_related('person', 'fine') \
#         .order_by('-datetime')

#     citation_ids = [citation.citationID for citation in citations]
#     quick_pd_data = {
#         qpd.ticket_num: qpd for qpd in QuickPD.objects.filter(ticket_num__in=citation_ids)
#     }
#     location_ids = {c.location_id for c in citations if c.video_id}
#     image_location_ids = {c.image_location for c in citations if c.image_id}

#     road_location_data = {
#         loc['id']: loc for loc in road_location.objects.filter(id__in=location_ids)
#         .values("id", "LOCATION_CODE", "location_name")
#     }
#     image_location_data = {
#         loc['trafficlogix_location_id']: loc for loc in road_location.objects.filter(
#             trafficlogix_location_id__in=image_location_ids
#         ).values("trafficlogix_location_id", "LOCATION_CODE", "location_name")
#     }

#     citation_data = []
#     for citation in citations:
#         media_data = None
#         person_data = citation.person
#         fine_data = citation.fine

#         quick_pd_entry = quick_pd_data.get(citation.citationID)
#         state = quick_pd_entry.plate_state if quick_pd_entry else None
#         plate = quick_pd_entry.plate_num if quick_pd_entry else None

#         if citation.video_id:
#             location = road_location_data.get(citation.location_id, {})
#             #sup_meta_data_approved_date = sup_metadata.objects.filter(citation_id=citation.id).first()
#             sup_meta_data_approved_date = sup_metadata.objects.filter(citation_id=citation.id).values('timeApp').first()
#             approved_date = sup_meta_data_approved_date.get('timeApp') if sup_meta_data_approved_date else None
#             media_data = {
#                 'citationId': citation.id,
#                 'citationID': citation.citationID,
#                 'mediaId': f'V-{citation.video_id}',
#                 'fine': fine_data.fine if fine_data else None,
#                 'speed': citation.speed,
#                 'locationCode': location.get("LOCATION_CODE"),
#                 'locationName': location.get("location_name"),
#                 'firstName': person_data.first_name if person_data else None,
#                 'lastName': person_data.last_name if person_data else None,
#                 'state': state,
#                 'plate': plate,
#                 'capturedDate': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
#                 #'approvedDate': sup_meta_data_approved_date.timeApp.strftime("%B %#d, %Y")  if sup_meta_data_approved_date else None   # citation.datetime.strftime("%B %#d, %Y") if citation.datetime else None,
#                 'approvedDate': approved_date.strftime("%B %#d, %Y") if approved_date else None
#             }
        
#         elif citation.image_id:
#             location = image_location_data.get(citation.image_location, {})
#             #sup_meta_data_approved_date = sup_metadata.objects.filter(citation_id=citation.id).first()
#             sup_meta_data_approved_date = sup_metadata.objects.filter(citation_id=citation.id).values('timeApp').first()
#             approved_date = sup_meta_data_approved_date.get('timeApp') if sup_meta_data_approved_date else None
#             media_data = {
#                 'citationId': citation.id,
#                 'citationID': citation.citationID,
#                 'mediaId': f'I-{citation.image_id}',
#                 'fine': fine_data.fine if fine_data else None,
#                 'speed': citation.speed,
#                 'locationCode': location.get("LOCATION_CODE"),
#                 'locationName': location.get("location_name"),
#                 'firstName': person_data.first_name if person_data else None,
#                 'lastName': person_data.last_name if person_data else None,
#                 'state': state,
#                 'plate': plate,
#                 'capturedDate': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
#                 #'approvedDate': sup_meta_data_approved_date.timeApp.strftime("%B %#d, %Y")  if sup_meta_data_approved_date else None  #citation.datetime.strftime("%B %#d, %Y") if citation.datetime else None,
#                 'approvedDate': approved_date.strftime("%B %#d, %Y") if approved_date else None
#             }
        
#         elif citation.tattile_id:
#             location = road_location_data.get(citation.location_id, {})
#             #sup_meta_data_approved_date = sup_metadata.objects.filter(citation_id=citation.id).first()
#             sup_meta_data_approved_date = sup_metadata.objects.filter(citation_id=citation.id).values('timeApp').first()
#             approved_date = sup_meta_data_approved_date.get('timeApp') if sup_meta_data_approved_date else None
#             media_data = {
#                 'citationId': citation.id,
#                 'citationID': citation.citationID,
#                 'mediaId': f'T-{citation.tattile_id}',
#                 'fine': fine_data.fine if fine_data else None,
#                 'speed': citation.speed,
#                 'locationCode': location.get("LOCATION_CODE"),
#                 'locationName': location.get("location_name"),
#                 'firstName': person_data.first_name if person_data else None,
#                 'lastName': person_data.last_name if person_data else None,
#                 'state': state,
#                 'plate': plate,
#                 'capturedDate': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
#                 #'approvedDate': sup_meta_data_approved_date.timeApp.strftime("%B %#d, %Y")  if sup_meta_data_approved_date else None  #citation.datetime.strftime("%B %#d, %Y") if citation.datetime else None,
#                 'approvedDate': approved_date.strftime("%B %#d, %Y") if approved_date else None
#             }

#         if media_data:
#             citation_data.append(media_data)

#     paginator = Paginator(citation_data, page_size)
#     page = paginator.get_page(page_index)

#     return {
#         "data": list(page.object_list),
#         "total_records": paginator.count,
#         "has_next_page": page.has_next(),
#         "has_previous_page": page.has_previous(),
#         "current_page": page.number,
#         "total_pages": paginator.num_pages,
#     }


          
def citation_data_for_approved_table(
    date_type, from_date, to_date, search_string,
    page_index=1, page_size=10,
    station_id=None, isDownload=False,
    paid_filter=1, edit_filter=1, fine_amount=None
):

    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%Y-%m-%d")

    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%Y-%m-%d")

    # ---------------- BASE QUERY ---------------- #

    query = Q(isApproved=True)

    if station_id:
        query &= Q(station_id=station_id)

    if date_type == 1:
        if from_date:
            query &= Q(captured_date__gte=from_date)
        if to_date:
            query &= Q(captured_date__lte=to_date)

    elif date_type == 2:
        # handled using Exists join below
        pass

    else:
        return "Invalid date type. It should be 1 or 2."

    if fine_amount is not None:
        query &= Q(fine_amount=fine_amount)

    citations_queryset = Citation.objects.filter(query).select_related(
        'person',
        'fine'
    )

    # ---------------- SEARCH ---------------- #

    full_name_search = False

    if search_string:
        search_string = search_string.lower()

        if " " in search_string:
            full_name_search = True
        else:
            search_string = search_string.replace(" ", "")
            citations_queryset = citations_queryset.filter(
                Q(citationID__icontains=search_string) |
                Q(person__first_name__icontains=search_string) |
                Q(person__last_name__icontains=search_string) |
                Q(vehicle__plate__icontains=search_string)
            )

    if full_name_search:
        citations_queryset = citations_queryset.annotate(
            full_name=Concat(
                Lower('person__first_name'),
                Value(' '),
                Lower('person__last_name')
            )
        ).filter(full_name__icontains=search_string)

    # ---------------- SUP_METADATA JOIN (DATE TYPE 2) ---------------- #

    if date_type == 2:

        sup_subquery = sup_metadata.objects.filter(
            citation_id=OuterRef('id')
        )

        if from_date:
            sup_subquery = sup_subquery.filter(timeApp__gte=from_date)

        if to_date:
            sup_subquery = sup_subquery.filter(timeApp__lte=to_date)

        citations_queryset = citations_queryset.annotate(
            has_sup=Exists(sup_subquery)
        ).filter(has_sup=True)

    # ---------------- PAID FILTER ---------------- #

    paid_subquery = PaidCitationsData.objects.filter(
        citationID=OuterRef('citationID')
    )

    if paid_filter == 2:
        citations_queryset = citations_queryset.annotate(
            is_paid=Exists(paid_subquery)
        ).filter(is_paid=True)

    elif paid_filter == 3:
        citations_queryset = citations_queryset.annotate(
            is_paid=Exists(paid_subquery)
        ).filter(is_paid=False)

    # ---------------- EDIT FILTER ---------------- #

    edit_map = {
        2: "OR",
        3: "PIH",
        4: 'RTS',
        5: "UA",
        6: "TL",
        7: "EF",
        14: "WARN-A"
    }

    if edit_filter != 1:

        if edit_filter == 8:
            citations_queryset = citations_queryset.filter(
                current_citation_status="CE"
            )

        elif edit_filter == 9:
            citations_queryset = citations_queryset.filter(
                current_citation_status="X"
            )

        elif edit_filter == 10:
            citations_queryset = citations_queryset.filter(
                current_citation_status="CE",
                citation_error_type="DMV"
            )

        elif edit_filter == 11:
            citations_queryset = citations_queryset.filter(
                current_citation_status="CE",
                citation_error_type="ADJ"
            )

        elif edit_filter == 12:
            citations_queryset = citations_queryset.filter(
                current_citation_status="X",
                citation_dissmissal_type="AD"
            )

        elif edit_filter == 13:
            citations_queryset = citations_queryset.filter(
                current_citation_status="X",
                citation_dissmissal_type="DUPC"
            )

        else:
            status = edit_map.get(edit_filter)
            if status:
                citations_queryset = citations_queryset.filter(
                    current_citation_status=status
                )

    # ---------------- ORDER BEFORE PAGINATION ---------------- #

    citations_queryset = citations_queryset.order_by('-datetime')

    # ---------------- DOWNLOAD (NO PAGINATION) ---------------- #

    if isDownload:
        citations_page = list(citations_queryset)
        total_records = len(citations_page)
        has_next = has_prev = False
        current_page = total_pages = 1

    else:
        paginator = Paginator(citations_queryset, page_size)
        page = paginator.get_page(page_index)

        citations_page = list(page.object_list)

        total_records = paginator.count
        has_next = page.has_next()
        has_prev = page.has_previous()
        current_page = page.number
        total_pages = paginator.num_pages

    # ---------------- BATCH FETCH RELATED DATA ---------------- #

    citation_ids = [c.citationID for c in citations_page]
    citation_db_ids = [c.id for c in citations_page]

    quick_pd_data = {
        q.ticket_num: q
        for q in QuickPD.objects.filter(ticket_num__in=citation_ids)
    }

    sup_meta_data = {
        m.citation_id: m
        for m in sup_metadata.objects.filter(citation_id__in=citation_db_ids)
    }

    paid_ids = set(
        PaidCitationsData.objects.filter(
            citationID__in=citation_ids
        ).values_list('citationID', flat=True)
    )

    citation_versioning_map = {
        cv.citation_id: cv.current_version_number
        for cv in CitationVersioning.objects.filter(
            citation_id__in=citation_db_ids
        )
    }

    # location batching
    location_ids = {c.location_id for c in citations_page if c.location_id}
    image_location_ids = {c.image_location for c in citations_page if c.image_location}

    road_location_data = {
        loc['id']: loc
        for loc in road_location.objects.filter(id__in=location_ids)
        .values("id", "LOCATION_CODE", "location_name")
    }

    image_location_data = {
        loc['trafficlogix_location_id']: loc
        for loc in road_location.objects.filter(
            trafficlogix_location_id__in=image_location_ids
        ).values("trafficlogix_location_id", "LOCATION_CODE", "location_name")
    }

    # ---------------- BUILD RESPONSE ---------------- #

    full_citation_data = []

    for citation in citations_page:

        person = citation.person
        fine_value = get_latest_fine_from_versioning(citation)

        quick_pd = quick_pd_data.get(citation.citationID)
        sup_meta = sup_meta_data.get(citation.id)

        paid_status_display = (
            "Paid" if citation.citationID in paid_ids else "Unpaid"
        )

        media_data = build_edit_media_data(
            citation,
            person,
            quick_pd,
            fine_value,
            road_location_data,
            image_location_data,
            sup_meta,
            paid_status_display,
            citation_versioning_map.get(citation.id)
        )

        full_citation_data.append(media_data)

    return {
        "data": full_citation_data,
        "total_records": total_records,
        "has_next_page": has_next,
        "has_previous_page": has_prev,
        "current_page": current_page,
        "total_pages": total_pages,
    }



def get_pdf_base64(filename):
    path = "pdfs/" + filename
    try:
        pdf_content = s3_get_file(path)
    except FileNotFoundError:
        return "File not found.."
    if pdf_content:
        base64_pdf=base64.b64encode(pdf_content).decode('utf-8')
        return base64_pdf
    else:
        return None
    
template = get_template("pdf_final.html")
template_maryland = get_template("maryland-pdf.html")
template_kersey = get_template("kersey-pdf.html")
template_hudson = get_template("hudson-pdf.html")
template_walsenburg = get_template("wals-pdf.html")
template_fairplay = get_template("fairplay-pdf.html")

config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
options = {
    "page-size": "Letter",
    "enable-local-file-access": "",
    "load-error-handling": "ignore",
    "load-media-error-handling": "ignore",
    "no-stop-slow-scripts": "",
    "javascript-delay": "3000",  # 3-second delay to allow images to load
    "debug-javascript": "",      # Optional, for verbose output
}


def create_pdf(filename, data, station_name):
    try:
        if station_name in ['FED-M']:
            html = template_maryland.render(data)
        elif station_name in ['KRSY-C']:
            html = template_kersey.render(data)
        elif station_name in ['HUD-C']:
            html = template_hudson.render(data)
        elif station_name in ['WALS']:
            html = template_walsenburg.render(data)
        elif station_name in ['FPLY-C']:
            html = template_fairplay.render(data) 
        else:
            html = template.render(data)
        
        location = os.path.join(BASE_DIR, "media", filename)

        pdfkit.from_string(html, location, configuration=config, options=options)

        with open(location, "rb") as pdf_file:
            upload_to_s3(pdf_file, filename, "pdfs")
        os.remove(location)

    except OSError as e:
        print(f"wkhtmltopdf error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

def build_edit_media_data(citation, person, quick_pd, fine, road_location_data, image_location_data, sup_meta, paid_status, citation_version):
    media_id = None
    location = {}
    citation_status = citation.current_citation_status or "OR"
    if citation.is_warning:
        citation_status = "Warning Admin"
    elif citation_status == "RTS":
        citation_status = "RS"
    elif citation_status == "CE":
        citation_status = f"CE-{citation.citation_error_type or ''}"
    elif citation_status == "X":
        citation_status = f"X-{citation.citation_dissmissal_type or ''}"

    if citation.video_id:
        media_id = f'V-{citation.video_id}'
        location = road_location_data.get(citation.location_id, {})
    elif citation.image_id:
        media_id = f'I-{citation.image_id}'
        location = image_location_data.get(citation.image_location, {})
    elif citation.tattile_id:
        media_id = f'T-{citation.tattile_id}'
        location = road_location_data.get(citation.location_id, {})

    approved_date = sup_meta.timeApp.strftime("%B %#d, %Y") if sup_meta and sup_meta.timeApp else None

    return {
        'citationId': citation.id,
        'citationID': citation.citationID,
        'mediaId': media_id,
        'fine': fine,
        'speed': citation.speed,
        'locationCode': location.get("LOCATION_CODE"),
        'locationName': location.get("location_name"),
        'firstName': person.first_name if person else None,
        'lastName': person.last_name if person else None,
        'state': quick_pd.plate_state if quick_pd else None,
        'plate': quick_pd.plate_num if quick_pd else None,
        'capturedDate': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
        'approvedDate': approved_date,
        'citationStatus': citation_status,
        'paidStatus': paid_status,
        'address': f"{person.address},{person.city},{person.state} {person.zip}" if person else None,
        'citationVersion': citation_version
    }

def build_original_media_data(citation, location, first_name, last_name, state, plate, approved_date, citation_status="OR-U"):
    if citation.video_id:
        media_id = f'V-{citation.video_id}'
    elif citation.image_id:
        media_id = f'I-{citation.image_id}'
    elif citation.tattile_id:
        media_id = f'T-{citation.tattile_id}'
    return {
        'citationId': citation.id,
        'citationID': citation.citationID,
        'mediaId': media_id,
        'fine': citation.fine_amount if citation.fine_amount else None,
        'speed': citation.speed,
        'locationCode': location.get("LOCATION_CODE"),
        'locationName': location.get("location_name"),
        'firstName': first_name,
        'lastName': last_name,
        'state': state,
        'plate': plate,
        'capturedDate': citation.captured_date.strftime("%B %#d, %Y") if citation.captured_date else None,
        'approvedDate': approved_date.strftime("%B %#d, %Y") if approved_date else None,
        'citationStatus': citation_status,
        "paidStatus": "Paid" if PaidCitationsData.objects.filter(citationID=citation.citationID).exists() else "Unpaid",
        "address": f"{citation.person.address}, {citation.person.city}, {citation.person.state} {citation.person.zip}"
    }

def get_original_citation_data(citation: Citation,
                               road_location_data=None,
                               image_location_data=None,
                               person_data=None,
                               state=None,
                               plate=None):
    # Get location
   
    location =   image_location_data.get(citation.image_location, {}) if citation.image_id else road_location_data.get(citation.location_id, {})
    sup_meta = sup_metadata.objects.filter(citation_id=citation.id).first()
    approved_date = sup_meta.originalTimeApp if sup_meta else None

    if citation.current_citation_status == "UA":
        old_data = CitationsWithUpdatedAddress.objects.filter(citation_id=citation.id).last()
        return build_original_media_data(
            citation,
            location,
            person_data.first_name if person_data else None,
            person_data.last_name if person_data else None,
            state,
            plate,
            approved_date
        )

    if citation.current_citation_status == "TL":
        old_data = CitationsWithTransferOfLiabilty.objects.filter(citation_id=citation.id).last()
        return build_original_media_data(
            citation,
            location,
            old_data.old_person.first_name if old_data and old_data.old_person else None,
            old_data.old_person.last_name if old_data and old_data.old_person else None,
            state,
            plate,
            approved_date
        )

    if citation.current_citation_status == "EF":
        return build_original_media_data(
            citation,
            location,
            person_data.first_name if person_data else None,
            person_data.last_name if person_data else None,
            state,
            plate,
            approved_date
        )

    return {}

def save_citation_edit_log(
        citation_object: Citation,
        user: User,
        editType: str,
        citationErrorType: Optional[str] = None,
        citationDismissalType: Optional[str] = None
):
    citation_edit_log = CitationEditLog.objects.create(
        station=citation_object.station,
        citation=citation_object,
        edited_by=user,
        previous_citation_status=citation_object.current_citation_status,
        edited_at=timezone.now(),
        current_citation_status=editType
    )
    if editType=="CE":
        citation_edit_log.citation_error_type = citationErrorType
    if editType=="X":
        citation_edit_log.citation_dismissal_type = citationDismissalType
    citation_edit_log.save()


def update_supervisor_metadata(citationObject: Citation, user: User):
      existing_sup_meta = sup_metadata.objects.filter(citation_id=citationObject.id).first()
      if existing_sup_meta:
          existing_sup_meta.user_id = user.id
          existing_sup_meta.isApproved = True
          existing_sup_meta.originalTimeApp = existing_sup_meta.timeApp
          existing_sup_meta.timeApp = datetime.now()
          existing_sup_meta.isEdited = True
          existing_sup_meta.isMailCitationApproved = False
          existing_sup_meta.save()
      else:
          print(f"Citation not found in sup_metadata table {citationObject.citationID}")
    
def patch_pdf_data_from_snapshot(pdf_data, snapshot):
    """
    Safely overwrite PDF data using snapshot
    """

    person = snapshot.get("person", {})
    status = snapshot.get("status", {})
    if "per" in pdf_data:
        pdf_data["per"]["first_name"] = person.get("first_name", pdf_data["per"].get("first_name"))
        pdf_data["per"]["last_name"] = person.get("last_name", pdf_data["per"].get("last_name"))
        pdf_data["per"]["address"] = person.get("address", pdf_data["per"].get("address"))
        pdf_data["per"]["city"] = person.get("city", pdf_data["per"].get("city"))
        pdf_data["per"]["state"] = person.get("state", pdf_data["per"].get("state"))
        pdf_data["per"]["zip"] = person.get("zip", pdf_data["per"].get("zip"))
        pdf_data["per"]["phone_number"] = person.get("phone_number", pdf_data["per"].get("phone_number"))

    fine = snapshot.get("fine", {})
    print(status,"----------------- status in patching -------------------")
    if "cit" in pdf_data and fine.get("amount") is not None:
        pdf_data["cit"]["fine"] = str("{:.2f}".format(fine.get("amount", {})))

    if "cit" in pdf_data:
        pdf_data["cit"]["current_citation_status"] = snapshot.get(
            "status", pdf_data["cit"].get("current_citation_status")
        )

    location = snapshot.get("location", {})
    if "cit" in pdf_data and location.get("location_name"):
        pdf_data["cit"]["location_name"] = location["location_name"]


    return pdf_data