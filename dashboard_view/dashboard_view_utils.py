from datetime import datetime
from django.db.models import Q
from video.models import adj_metadata, Data, Image, Tattile, sup_metadata

def get_dashboard_data(from_date, to_date,stationId,station_name):
    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%Y-%m-%d")
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%Y-%m-%d")

    from_date_str = from_date.strftime("%y%m%d") if from_date else None
    to_date_str = to_date.strftime("%y%m%d") if to_date else None

    query = Q()
    if from_date:
        query &= Q(timeAdj__gte=from_date)
    if to_date:
        query &= Q(timeAdj__lte=to_date)
    adjudication_video_data = adj_metadata.objects.filter(query, station_id = stationId, video_id__isnull=False).count()
    adjudication_image_data = adj_metadata.objects.filter(query, station_id = stationId, image_id__isnull=False).count()
    adjudication_tattile_data = adj_metadata.objects.filter(query, station_id = stationId, tattile_id__isnull=False).count()

    citation_query = Q()
    if from_date:
        citation_query &= Q(datetime__gte=from_date)
    if to_date:
        citation_query &= Q(datetime__lte=to_date)
        
    # citation_tattile_query = Q()
    # if from_date:
    #     citation_query &= Q(timeApp__gte=from_date)
    # if to_date:
    #     citation_query &= Q(timeApp__lte=to_date)

    # # citation_video_data = Citation.objects.filter(citation_query,station_id=stationId,video_id__isnull=False,isApproved=True,isSendBack=False).count()
    # # citation_image_data = Citation.objects.filter(citation_query,station_id=stationId,image_id__isnull=False,isApproved=True,isSendBack=False).count()
    # # citation_tattile_data = Citation.objects.filter(citation_query,station_id=stationId,tattile_id__isnull=False,isApproved=True,isSendBack=False).count()
    # citation_video_data = sup_metadata.objects.filter(citation_tattile_query,station_id=stationId,citation__video__isnull=False,isApproved=True).count()
    # citation_image_data = sup_metadata.objects.filter(citation_tattile_query,station_id=stationId,citation__image__isnull=False,isApproved=True).count()
    # citation_tattile_data= sup_metadata.objects.filter(citation_tattile_query,station=stationId, citation__tattile__isnull=False, isApproved=True).count()
    
    
    citation_filter = Q()
    if from_date:
        citation_filter &= Q(timeApp__gte=from_date)
    if to_date:
        citation_filter &= Q(timeApp__lte=to_date)

    # Ensure you're using the correct FK and station fields
    citation_video_data = sup_metadata.objects.filter(
        citation_filter,
        station_id=stationId,
        citation__video_id__isnull=False,
        isApproved=True
    ).count()
    
    citation_image_data = sup_metadata.objects.filter(
        citation_filter,
        station_id=stationId,
        citation__image_id__isnull=False,
        isApproved=True
    ).count()
    
    citation_tattile_data = sup_metadata.objects.filter(
        citation_filter,
        station_id=stationId,
        citation__tattile_id__isnull=False,
        isApproved=True
    ).count()
        
    docker_video_query = Q()
    if from_date_str:
        docker_video_query &= Q(DATE__gte=from_date_str)
    if to_date_str:
        docker_video_query &= Q(DATE__lte=to_date_str)
    docker_video_query &= Q(STATION__iexact=station_name)
    
    video_data = Data.objects.filter(docker_video_query).values('VIDEO_NAME').distinct().count()


    image_query = Q()
    if from_date:
        image_query &= Q(time__gte=from_date)
    if to_date:
        image_query &= Q(time__lte=to_date)

    image_data = Image.objects.filter(image_query,station_id=stationId).count()
    
    tattile_query = Q()
    if from_date:
        tattile_query &= Q(image_time__gte=from_date)
    if to_date:
        tattile_query &= Q(image_time__lte=to_date)

    tattile_data = Tattile.objects.filter(tattile_query,station_id=stationId, is_active= True).distinct('ticket_id').count()

    return {
        "dockerUploadedVideos" : video_data,
        "trafficLogixUploadedImage" : image_data,
        "adjudicatedVideoCount" : adjudication_video_data,
        "adjudicatedImageCount" : adjudication_image_data,
        "approvedVideoCount" : citation_video_data,
        "approvedImageCount" : citation_image_data,
        "tattileImageUploadCount" : tattile_data,
        "tattileImageAdjudicatedCount" : adjudication_tattile_data,
        "tattileImageApprovedCount" : citation_tattile_data
    }