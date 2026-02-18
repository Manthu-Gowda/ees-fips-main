from video.models import *
from django.db.models import F, Value, CharField, Func
from django.db.models.functions import Concat
from django.db.models import Q
from django.utils.timezone import now
from django.core.paginator import Paginator

def get_video_rejects(stationId):
    video_response_data = list(
        Video.objects.filter(isRejected=True, station_id=stationId)
        .annotate(
            mediaId=F('id'),
            label=Concat(
                Func(
                    F('datetime'),
                    Value('FMMonth DD, YYYY, HH12:MI AM'),
                    function='TO_CHAR',
                    output_field=CharField()
                ),
                Value(" - "),
                F('caption'),
                output_field=CharField()
            )
        )
        .values("mediaId", "label")
        .order_by("VIDEO_NO", "id")
    )

    return video_response_data


def get_image_rejects(stationId):
    image_response_data = list(
        Image.objects.filter(isRejected=True, isRemoved=False, station_id=stationId)
        .annotate(
            mediaId=F('id'),
            formatted_time=Func(
                F('time'),
                Value('FMMonth DD, YYYY, HH12:MI AM'),
                function='TO_CHAR',
                output_field=CharField()
            ),
            truncated_filename=Func(
                F('plate_image_filename'),
                Value('.'),
                Value(1),
                function='SPLIT_PART',
                output_field=CharField()
            ),
            label=Concat(
                Func(
                    F('time'),
                    Value('FMMonth DD, YYYY, HH12:MI AM'),
                    function='TO_CHAR',
                    output_field=CharField()
                ),
                Value(" - "),
                Func(
                    F('plate_image_filename'),
                    Value('.'),
                    Value(1),
                    function='SPLIT_PART',
                    output_field=CharField()
                ),
                output_field=CharField()
            )
        )
        .values("mediaId", "label")
        .order_by("time", "id")
    )
    return image_response_data


def get_tattile_rejects(agency_name, stationId):
    tattile_response_data = list(
        Tattile.objects.filter(is_rejected=True, station_id=stationId, reject_id__isnull=False)
        .annotate(
            mediaId=F('id'),
            label=Concat(
                Value(agency_name),
                Value(" - "),
                Func(
                    F('image_time'),
                    Value('FMMonth DD, YYYY, HH12:MI AM'),
                    function='TO_CHAR',
                    output_field=CharField()
                ),
                Value(" - "),
                F('location_name'),
                output_field=CharField()
            )
        )
        .values("mediaId", "label")
        .order_by("image_time", "id")
    )

    return tattile_response_data


def get_traffix_logix_client_ids():
    image_location_data = ImageLocation.objects.all()

    response_data = [{
        "trafficLogixClientId" : location.location_id,
        "locationName" : location.name
    }
    for location in image_location_data]
    return response_data


def get_video_data(filters,agency_name, station_id):
    video_queryset = Video.objects.filter((Q(is_notfound= True)| Q(isSent= True) | Q(isSentToReviewBin = True)) & Q(
                                             isRejected = False, isRemoved = False,station = station_id)).order_by('VIDEO_NO', 'id')
    video_location_ids = video_queryset.values_list("location_id", flat=True)
    location_queryset = road_location.objects.filter(id__in=video_location_ids)
    location_map = {loc.id: loc for loc in location_queryset}
    agency_adjudication_video_id = AdjudicationBin.objects.filter(is_adjudicated_in_adjudicationbin = False, station = station_id).values_list('video_id',flat=True)
    
    
    # get review bin data where is is_adjudicated_in_review_bin
    return [
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
        for video in video_queryset if video.id not in agency_adjudication_video_id
    ]


def get_image_data(agency_name,station_id):
    image_queryset = Image.objects.filter((Q(is_notfound= True)| Q(isSent= True) | Q(isSentToReviewBin = True)) & Q(
                                             isRejected = False, isRemoved = False,station = station_id)).order_by('time', 'id')
    image_location_ids = image_queryset.values_list("location_id", flat=True)
    location_queryset = ImageLocation.objects.filter(location_id__in=image_location_ids)
    location_map =  {location.location_id: location.name for location in location_queryset}
    agency_adjudication_image_id = AdjudicationBin.objects.filter(is_adjudicated_in_adjudicationbin = False,station = station_id).values_list('image_id',flat=True)

    return [
        {
            "id": image.id,
            "label": f"{agency_name}_{location_map.get(image.location_id, 'Unknown')}_{image.time.date().strftime('%m%d%Y')}_{image.time.strftime('%I:%M %p')}_{image.custom_counter}",
            "isRejected": image.isRejected or False,
            "isAdjudicated": image.isAdjudicated,
            "isSent": image.isSent,
            "isSentToReviewBin": image.isSentToReviewBin,
            "isNotFound": image.is_notfound,
            "citationID": image.citation.citationID if image.citation else None
        }
        for image in image_queryset if image.id not in agency_adjudication_image_id
    ]
    
    
def get_tattile_data(agency_name,station_id):
    tattile_queryset = Tattile.objects.filter((Q(is_sent_to_review_bin= True)| Q(is_not_found= True) | Q(is_sent = True)) & Q(
                                             is_rejected = False, is_removed = False,station = station_id, is_active = True)).order_by('image_time', 'id')
    tattile_location_ids = tattile_queryset.values_list("location_id", flat=True)
    location_queryset = road_location.objects.filter(id__in=tattile_location_ids)
    location_map = {loc.id: loc for loc in location_queryset}
    agency_adjudication_video_id = AdjudicationBin.objects.filter(is_adjudicated_in_adjudicationbin = False, station = station_id).values_list('tattile_id',flat=True)
    
    
    # get review bin data where is is_adjudicated_in_review_bin
    return [
        {
            "id": tattile.id,
            "label": f"{agency_name}_{location_map.get(tattile.location_id).location_name if tattile.location_id in location_map else None}_{tattile.image_time.date().strftime('%m%d%Y')}_{tattile.image_time.strftime('%I:%M:%S %p')}",
            "isRejected": tattile.is_rejected or False,
            "isAdjudicated": tattile.is_adjudicated,
            "isSent": tattile.is_sent,
            "isSentToReviewBin": tattile.is_sent_to_review_bin,
            "isNotFound": tattile.is_not_found,
            "citationID": tattile.citation_id if tattile.citation_id else None
        }
        for tattile in tattile_queryset if tattile.id not in agency_adjudication_video_id
    ]


def get_odr_citation(station_id, from_date=None, to_date=None, is_approved=None):
    citations = UnpaidCitation.objects.filter(station=station_id, pre_odr_mail_count = 3)

    if is_approved is False:
        citations = citations.filter(isApproved=False)

    if from_date and to_date:
        citations = citations.filter(second_mail_due_date__range=(from_date, to_date))
    elif from_date:
        citations = citations.filter(second_mail_due_date__gte=from_date)
    elif to_date:
        citations = citations.filter(second_mail_due_date__lt=to_date)

    citations = citations.order_by("ticket_number")

    response_data = [
        {
            "citationID": odr_cit.ticket_number,
            "isApproved": odr_cit.isApproved,
            "citationId": odr_cit.id
        }
        for odr_cit in citations
    ]

    return response_data


def extract_input_fields_for_pre_odr_view(validated_data):
    return {
            "mailerType": validated_data.get('mailerType'),
            "isApproved": validated_data.get('isApproved'),
            "year": validated_data.get('year'),
            "month": validated_data.get('month'),
            "day": validated_data.get('day'),
            "searchString" : validated_data.get('searchString'),
            "pageIndex" : validated_data.get('pageIndex'),
            "pageSize" : validated_data.get('pageSize')
    }


def get_pre_odr_view_citations(validated_data, station_id):
    filters = Q()

    if validated_data.get('year'):
        filters &= Q(arr_date__year=validated_data.get('year'))
    if validated_data.get('month'):
        filters &= Q(arr_date__month=validated_data.get('month'))
    if validated_data.get('day'):
        filters &= Q(arr_date__day=validated_data.get('day'))

    if validated_data.get('isApproved') is not None:
        filters &= Q(isApproved=validated_data.get('isApproved'))

    if validated_data.get('mailerType') == 1:
        today_date = now().date()
    
        # Basic first mailer filter
        base_first_mailer = Q(pre_odr_mail_count__in=[0, 1]) & (
            Q(first_mail_due_date__isnull=True) | Q(first_mail_due_date__lt=today_date)
        )
    
        # Exclude citations that qualify for second mailer
        second_mailer_qualified = Q(
            pre_odr_mail_count=1,
            isApproved=False,
            second_mail_due_date__isnull=True,
            first_mail_due_date__lt=today_date,
            is_deleted=False
        )
    
        filters &= base_first_mailer & ~second_mailer_qualified

    elif validated_data.get('mailerType') == 2:
        # filters &= Q(pre_odr_mail_count=1, 
        #               isApproved=False, 
        #               second_mail_due_date__isnull=True, 
        #               is_deleted=False)

        # today_date = now().date()
        # filters &= Q(first_mail_due_date__lt=today_date)
        
        today_date = now().date()

        # Citations waiting for second mailer (first mailer failed, not approved again)
        waiting_second_mailer = Q(
            pre_odr_mail_count=1,
            isApproved=False,
            second_mail_due_date__isnull=True,
            first_mail_due_date__lt=today_date,
            is_deleted=False
        )

        # Citations already in second mailer and approved
        approved_second_mailer = Q(
            pre_odr_mail_count=2,
            isApproved=True,
            is_deleted=False
        )

        filters &= (waiting_second_mailer | approved_second_mailer)

    filters &= Q(station_id=station_id,is_deleted=False)

    unpaid_citation_data = UnpaidCitation.objects.filter(filters).order_by('ticket_number').values('id', 'ticket_number', 'isApproved').distinct()

    response_data = list(map(lambda citation: {
        "citationId": citation["id"],
        "citationID": citation["ticket_number"],
        "isApproved": citation["isApproved"],
        "isRejected": False,
        "isSendBack": False,
    }, unpaid_citation_data))

    paginator = Paginator(response_data, validated_data.get('pageSize'))
    page = paginator.get_page(validated_data.get('pageIndex'))

    return {
        "data": list(page.object_list),
        "total_records": paginator.count,
        "has_next_page": page.has_next(),
        "has_previous_page": page.has_previous(),
        "current_page": page.number,
        "total_pages": paginator.num_pages,
    }

def get_video_ids(filters, station_id):
    video_queryset = Video.objects.filter((Q(is_notfound= True)| Q(isSent= True) | Q(isSentToReviewBin = True)) & Q(
                                             isRejected = False, isRemoved = False,station = station_id))
    agency_adjudication_video_id =  AdjudicationBin.objects.filter(is_adjudicated_in_adjudicationbin = False, station = station_id).values_list('video_id',flat=True)

    # exclude adjudicated ones and return IDs instead of count
    return video_queryset.exclude(id__in=agency_adjudication_video_id).values_list(
        "id", flat=True
    )


def get_image_ids(station_id):
    """Return valid image IDs for a station (excluding adjudicated)."""
    image_queryset = Image.objects.filter(
        (Q(is_notfound=True) | Q(isSent=True) | Q(isSentToReviewBin=True)),
        isRejected=False,
        isRemoved=False,
        station=station_id,
    ).values_list("id", flat=True)

    agency_adjudication_image_id = AdjudicationBin.objects.filter(
        is_adjudicated_in_adjudicationbin=False, station=station_id
    ).values_list("image_id", flat=True)

    # Exclude adjudicated ones
    return image_queryset.exclude(id__in=agency_adjudication_image_id)


def get_tattile_ids(station_id):
    """Return valid tattile IDs for a station (excluding adjudicated ones)."""
    tattile_queryset = Tattile.objects.filter((Q(is_sent_to_review_bin= True)| Q(is_not_found= True) | Q(is_sent = True)) & Q(
                                             is_rejected = False, is_removed = False,station = station_id, is_active = True)).order_by('image_time', 'id')
    
    agency_adjudication_tattile_id = AdjudicationBin.objects.filter(is_adjudicated_in_adjudicationbin = False, station = station_id).values_list('tattile_id',flat=True)
    # Exclude adjudicated tattile IDs
    return tattile_queryset.exclude(id__in=agency_adjudication_tattile_id)

def get_rejects_evidence(agency_name, stationId, media_type):
    if media_type == 1:
        evidence_calibration_videos = EvidenceCalibrationBin.objects.filter(
            video__isnull=False
        ).values_list("video_id", flat=True)

        video_response_data = list(
            Video.objects.filter(
                isRejected=True,
                station_id=stationId,
                id__in=evidence_calibration_videos,
            )
            .annotate(
                mediaId=F("id"),
                label=Concat(
                    Func(
                        F("datetime"),
                        Value("FMMonth DD, YYYY, HH12:MI AM"),
                        function="TO_CHAR",
                        output_field=CharField(),
                    ),
                    Value(" - "),
                    F("caption"),
                    output_field=CharField(),
                ),
            )
            .values("mediaId", "label")
            .order_by("VIDEO_NO", "id")
        )

        return video_response_data
    elif media_type == 2:
        evidence_calibration_images = EvidenceCalibrationBin.objects.filter(
            image__isnull=False
        ).values_list("image_id", flat=True)
        image_response_data = list(
            Image.objects.filter(
                isRejected=True,
                isRemoved=False,
                station_id=stationId,
                id__in=evidence_calibration_images,
            )
            .annotate(
                mediaId=F("id"),
                formatted_time=Func(
                    F("time"),
                    Value("FMMonth DD, YYYY, HH12:MI AM"),
                    function="TO_CHAR",
                    output_field=CharField(),
                ),
                truncated_filename=Func(
                    F("plate_image_filename"),
                    Value("."),
                    Value(1),
                    function="SPLIT_PART",
                    output_field=CharField(),
                ),
                label=Concat(
                    Func(
                        F("time"),
                        Value("FMMonth DD, YYYY, HH12:MI AM"),
                        function="TO_CHAR",
                        output_field=CharField(),
                    ),
                    Value(" - "),
                    Func(
                        F("plate_image_filename"),
                        Value("."),
                        Value(1),
                        function="SPLIT_PART",
                        output_field=CharField(),
                    ),
                    output_field=CharField(),
                ),
            )
            .values("mediaId", "label")
            .order_by("time", "id")
        )
        return image_response_data
    elif media_type == 3:
        evidence_calibration_tattile = EvidenceCalibrationBin.objects.filter(
            tattile__isnull=False
        ).values_list("tattile_id", flat=True)
        tattile_response_data = list(
            Tattile.objects.filter(
                is_rejected=True,
                station_id=stationId,
                id__in=evidence_calibration_tattile,
            )
            .annotate(
                mediaId=F("id"),
                label=Concat(
                    Value(agency_name),
                    Value(" - "),
                    Func(
                        F("image_time"),
                        Value("FMMonth DD, YYYY, HH12:MI AM"),
                        function="TO_CHAR",
                        output_field=CharField(),
                    ),
                    Value(" - "),
                    F("location_name"),
                    output_field=CharField(),
                ),
            )
            .values("mediaId", "label")
            .order_by("image_time", "id")
        )

        return tattile_response_data