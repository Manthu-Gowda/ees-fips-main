from django.http import HttpResponse
from django.contrib.auth.models import auth
from .logixx import get_location_details, get_location_list, get_ticket_list_by_location, get_ticket_location_list, \
      get_zip_ticket_details, set_export_status_ticket, get_ticket_list_by_location_v4, get_zip_ticket_details_v4
from ..models import Agency, Citation, Image, ImageData, ImageLocation, adj_metadata, sup_metadata, ImageHash
from video.models import road_location
from django.utils import timezone
from django.shortcuts import redirect, render




def upload_ticket_location_data(request,ticket_id):
    if request.method == 'GET':
        ticket_id = ticket_id
        # print(ticket_id)
        try:
            ticket_details_upload = get_ticket_location_list(ticket_id)
            return HttpResponse("Ticket Details successfully saved.",status=200)
        except Exception as e:
            error_message = f"Error fetching location data: {e}"
            return HttpResponse(error_message, status=404)

#GET ZIP FILE TICKET

def upload_zip_ticket_details(request,ticket_id):
    if request.method == 'GET':
        ticket_id = ticket_id
        print(ticket_id)
        
        try:
            location_upload = get_zip_ticket_details(ticket_id)
            if location_upload:
                
                return HttpResponse("Zip file Ticket successfully saved.", status=200)
            else:
                return HttpResponse("No data found for the ticket.", status=404)
        except Exception as e:
            error_message = f"Error fetching Ticket data: {e}"
            return HttpResponse(error_message, status=500)
    



def render_images_List(agencyId):
    station = Agency.objects.get(id=agencyId).station
    
    rl = road_location.objects.filter(station_id=station)
    
    location_speed_map = {loc.trafficlogix_location_id: loc.posted_speed for loc in rl}
    
    locations = location_speed_map.keys()
    
    ticket_ids = Image.objects.filter(
        isRejected=False, isRemoved=False, location_id__in=locations
    ).order_by("time")
    
    modified_ticket_ids = []
    
    for ticket in ticket_ids:
        ticket.plate_image_filename = ticket.plate_image_filename.split('.')[0]
        
        ticket.current_speed_limit = location_speed_map.get(ticket.location_id)
        
        modified_ticket_ids.append(ticket)
    
    return modified_ticket_ids

def render_reject_images_List(agencyId):
    station = Agency.objects.get(id=agencyId).station
    
    rl = road_location.objects.filter(station_id=station)
    
    location_speed_map = {loc.trafficlogix_location_id: loc.posted_speed for loc in rl}
    
    locations = location_speed_map.keys()
    
    ticket_ids = Image.objects.filter(
        isRejected=True, location_id__in=locations
    ).order_by("time")
    
    modified_ticket_ids = []
    
    for ticket in ticket_ids:
        ticket.plate_image_filename = ticket.plate_image_filename.split('.')[0]
        
        ticket.current_speed_limit = location_speed_map.get(ticket.location_id)
        
        modified_ticket_ids.append(ticket)
    
    return modified_ticket_ids 

def fetch_logix_tickets(request):
    agencies = Agency.objects.filter(traffic_logix_client_id__isnull=False)
    for agency in agencies:
        data = get_location_list(agency.traffic_logix_client_id,agency.traffic_logix_token)
        for location in data['locations']:
            get_location_details(location['lid'],agency.traffic_logix_token)
            tickets = get_ticket_list_by_location(location['lid'],agency.traffic_logix_token)
            print(len(tickets['tickets']))
            print(location['lid'])
            for ticket in tickets['tickets']:
                ticket_details = get_zip_ticket_details(ticket['ticket_id'],agency.traffic_logix_token)

    return HttpResponse("", status=200)


def fetch_logix_tickets_Task():
    agencies = Agency.objects.filter(traffic_logix_client_id__isnull=False)
    for agency in agencies:
        data = get_location_list(agency.traffic_logix_client_id,agency.traffic_logix_token)
        for location in data['locations']:
            get_location_details(location['lid'],agency.traffic_logix_token)
            
            tickets = get_ticket_list_by_location_v4(location['lid'],agency.traffic_logix_token, agency.traffic_logix_client_id)
           
            
            for ticket in tickets['tickets']:
                ticket_details = get_zip_ticket_details_v4(ticket['ticket_id'],agency.traffic_logix_token)
               
                if ticket_details:
                    set_export_status = set_export_status_ticket(ticket['ticket_id'], agency.traffic_logix_token, 2)


def removelogix_tickets(request):
    Citation.objects.filter(video_id = None).update(image_id = None)
    sup = Citation.objects.filter(video_id = None).values()
    for s in sup:
        sup_metadata.objects.filter(citation_id = s["id"]).delete()
    adj_metadata.objects.filter(video_id = None).delete()
    Citation.objects.filter(video_id = None).delete()
    Image.objects.all().delete()
    ImageLocation.objects.all().delete()
    ImageData.objects.all().delete()
    ImageHash.objects.all().delete()
    return HttpResponse("", status=200)

def render_duncan_images(agencyId):
    station = Agency.objects.get(id=agencyId).station
    rl = road_location.objects.filter(station_id=station)
    location_speed_map = {loc.trafficlogix_location_id: loc.posted_speed for loc in rl}
    
    locations = location_speed_map.keys()
    
    ticket_ids = Image.objects.filter(
        isRejected=False, isRemoved=False,
        isAdjudicated = False,
        isSent = False, location_id__in=locations
    ).order_by("time")
    
    modified_ticket_ids = []
    
    for ticket in ticket_ids:
        ticket.plate_image_filename = ticket.plate_image_filename.split('.')[0]
        
        ticket.current_speed_limit = location_speed_map.get(ticket.location_id)
        
        modified_ticket_ids.append(ticket)
    
    return modified_ticket_ids