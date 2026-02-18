from django.db.models import Max
from video.models import road_location, ImageLocation


def extracted_input_fields(validated_data):
    return {
        "location_name" : validated_data.get('locationName'),
        "posted_speed" : validated_data.get('postedSpeed'),
        "is_school_zone" : validated_data.get('isSchoolZone'),
        "is_traffic_logix" : validated_data.get('isTrafficLogix'),
        "traffic_logix_client_id" : validated_data.get('trafficLogixClientId'),
        "is_construction_zone" : validated_data.get('isConstructionZone')
    }

def add_road_location(extracted_fields,stationId):
        
        existing_location = road_location.objects.filter(station_id=stationId, location_name=extracted_fields["location_name"]).first()
        if existing_location:
            if existing_location.trafficlogix_location_id == extracted_fields["traffic_logix_client_id"]:
                return "Location_id already exists please select different one"
            return "Location name already exists."

        max_code = road_location.objects.filter(station_id=stationId).aggregate(Max('LOCATION_CODE'))['LOCATION_CODE__max']
        new_location_code = (max_code or 0) + 1
        new_road_location = road_location.objects.create(
            station_id = stationId,
            LOCATION_CODE = new_location_code,
            location_name = extracted_fields["location_name"],
            posted_speed = extracted_fields["posted_speed"],
            isSchoolZone = extracted_fields["is_school_zone"],
            isTrafficLogix = extracted_fields["is_traffic_logix"],
            trafficlogix_location_id = extracted_fields["traffic_logix_client_id"],
            isConstructionZone = extracted_fields["is_construction_zone"]
        )

        return "Location has been added successfully."


def update_road_location_details(extracted_fields,stationId,locationId):
    existing_location = road_location.objects.filter(station_id=stationId, location_name=extracted_fields["location_name"]).exclude(id=locationId).first()
    if existing_location:
            if existing_location.trafficlogix_location_id == extracted_fields["traffic_logix_client_id"]:
                return "Location_id already exists please select different one"
            return "Location name already exists."
    
    road_location_data = road_location.objects.filter(id=locationId).first()
    if road_location_data:
        road_location_data.location_name = extracted_fields["location_name"]
        road_location_data.posted_speed = extracted_fields["posted_speed"]
        road_location_data.isSchoolZone = extracted_fields["is_school_zone"]
        road_location_data.isTrafficLogix = extracted_fields["is_traffic_logix"]
        road_location_data.trafficlogix_location_id = extracted_fields["traffic_logix_client_id"]
        road_location_data.isConstructionZone = extracted_fields["is_construction_zone"]
        road_location_data.save()
        return f"Rod Location with Id : {locationId} has been updated successfully."
    else:
         return f"Road Location with Id : {locationId} does not exists."