import os
import requests
import json
import datetime 
from datetime import timezone
import xml.etree.ElementTree as ET
from decouple import config as ENV_CONFIG
from ..models import  ImageData, Image, ImageHash, ImageLocation, road_location
from django.core.management.base import BaseCommand, CommandError
import zipfile
from django.conf import settings
from ees.utils import s3_upload_file, upload_to_s3,get_presigned_url
from django.shortcuts import render , redirect

#GET LOCATION LIST API 

def get_location_list(company_id,api_key):
    location_url = ENV_CONFIG('GET_LOCATION_LIST')
    location_uri = f"{location_url}/{company_id}"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
    }
    try:
        response = requests.get(location_uri, headers=headers)
        api_response = response.json()
        
        locations_data = {
            'company_id': company_id,
            'locations': []
        }
        
        locations = api_response.get('locations', [])
        
        if locations:
            for location in locations:
                lid_value = location.get('lid')
                location_name = location.get('name')
                zip_code = location.get('zip')
                location_dict = {
                    'lid': lid_value,
                    'location_name': location_name,
                    'zip': zip_code,
                }
                locations_data['locations'].append(location_dict)
                
            print("Locations successfully retrieved.")
        else:
            print("No locations found for the company ID.")

        return locations_data

    except Exception as e:
        print(f"Error fetching location data: {e}")
        return None



#GET TICKET LOCATION DETAILS 

def get_ticket_location_list(ticket_id,api_key):
    ticket_location_url = ENV_CONFIG('GET_TICKET_DETAILS')
    ticket_location_uri = f"{ticket_location_url}/{ticket_id}"
    
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
    }
    try:
        ticket_response = requests.get(ticket_location_uri, headers=headers)
        api_response = ticket_response.json()
        # print(api_response)
        
        ticket_data = {
            'ticket_id': ticket_id,
            'ticket': []
        }
        
        ticket = api_response.get('ticket', [])

        
        if ticket:
            # print(ticket)


            id_value = ticket.get('id')
            speed_limit_value = ticket.get('current_speed_limit')
            violating_speed_value = ticket.get('violating_speed')
            plate_img_file = ticket.get('plate_image_filename')
            plate_text = ticket.get('plate_text')
            location_id = ticket.get('location_id')
            location_name = ticket.get('location_name')

            ticket_dict = {
                'id': id_value,
                'current_speed_limit': speed_limit_value,
                'violating_speed': violating_speed_value,
                'plate_image_filename': plate_img_file,
                'plate_text': plate_text,
                'location_id': location_id,
                'location_name': location_name,
            }
            ticket_data['ticket'].append(ticket_dict)
            print(ticket_data)

            print("Ticket locations successfully retrieved.")
        else:
            print("No ticket locations found for the ticket ID.")

        return ticket_data

    except Exception as e:
        print(f"Error fetching ticket location data: {e}")
        return None



def get_zip_ticket_details(ticket_id,api_key):
    save_path = r"C:\dev_EES\zip_files_extracted"  
    location_url = ENV_CONFIG('GET_ZIP_TICKET_DETAIL_ZIP')
    location_uri = f"{location_url}/{ticket_id}"

    ticket_url = ENV_CONFIG('GET_TICKET_DETAILS')
    ticket_uri = f"{ticket_url}/{ticket_id}"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
    }
    try:
        highest_distance = 0
        entry_check=Image.objects.filter(ticket_id=ticket_id).exists()
        if not entry_check:
            response = requests.get(location_uri, headers=headers)

            if response:
                os.makedirs(save_path, exist_ok=True)
                file_path = os.path.join(save_path,str(ticket_id)+ ".zip")
                with open(file_path, "wb") as file:
                    file.write(response.content)

                print("ZIP File with Ticket Details has been downloaded successfully.")

                with zipfile.ZipFile(file_path, 'r') as zip_ref: 
                    zip_file_path= f"{save_path}\\{ticket_id}"
                    zip_ref.extractall(zip_file_path)
                os.remove(zip_file_path+".zip")

                s3_image_urls = []
                files_present=[]
                s3_image_name=[]

                for root, _ ,files in os.walk(save_path):
                    files_present.append(files)
        
                for file in files_present[1]:
                    if file.endswith(('.png' ,'.jpg')):
                        local_file_path = os.path.join(root, file)
                        s3_file_name = os.path.basename(file) 

                        s3_image_name.append(s3_file_name)
                        s3_folder_name = ENV_CONFIG("AWS_IMAGES_FOLDER_NAME")
                        s3_bucket_name = ENV_CONFIG("AWS_S3_BUCKET_NAME_IMAGE")
                        if s3_upload_file(local_file_path, s3_file_name, s3_folder_name, s3_bucket_name):
                            s3_url = f"https://{s3_bucket_name}.s3.amazonaws.com/{s3_folder_name}/{s3_file_name}"
                            s3_image_urls.append(s3_url)
                        else:
                            print(f"Failed to upload{file} to S3")
                        # return s3_image_urls
                    elif file == 'event.xml':
                        highest_distance=extract_xml(zip_file_path)
                        os.remove(os.path.join(root, file))
                    else:
                        os.remove(os.path.join(root, file))
                os.removedirs(zip_file_path)
                    
                for s3_url in range(len(s3_image_urls)):
                    # for s3_file in s3_file_name[1]:
                    image_data_obj = ImageData.objects.create(
                        ticket_id=ticket_id,
                        image_name=s3_image_name[s3_url].split("/")[-1],
                        image_url =s3_image_urls[s3_url]
                    )
                    image_data_obj.save()
                print("Image files from ZIP file have been uploaded to S3 and URLs have been updated in the database.")

                ticket_details = requests.get(ticket_uri, headers=headers)
                api_response = ticket_details.json()

                ticket_details_to_insert = api_response.get('ticket')
                for hash in ticket_details_to_insert.get('images'):
                    if ticket_details_to_insert.get('location_id') == "71511":
                        fetch_beam_image_v2(ticket_details_to_insert.get('id'),hash,api_key)
                    else:
                        fetch_beam_image(ticket_details_to_insert.get('id'),hash,api_key)

                if ticket_details_to_insert.get('speed_unit') == 'km/h':
                    speed_unit_change = 'mi/h'
                    violating_speed_change = round(int(float(ticket_details_to_insert.get('violating_speed'))) * 0.621371)
                    current_speed_limit_change = round(int(float(ticket_details_to_insert.get('current_speed_limit'))) * 0.621371)
                else:
                    speed_unit_change = ticket_details_to_insert.get('speed_unit')
                    violating_speed_change = ticket_details_to_insert.get('violating_speed')
                    current_speed_limit_change = ticket_details_to_insert.get('current_speed_limit')
                location = road_location.objects.get(trafficlogix_location_id = ticket_details_to_insert.get('location_id'))
                image_obj = Image.objects.create(
                    ticket_id = ticket_details_to_insert.get('id'),
                    location_id = ticket_details_to_insert.get('location_id'),
                    time = ticket_details_to_insert.get('time'),
                    data = ticket_details_to_insert.get('data'),
                    current_speed_limit = current_speed_limit_change, 
                    violating_speed = violating_speed_change,
                    plate_text = ticket_details_to_insert.get('plate_text'),
                    locked = ticket_details_to_insert.get('locked'),
                    ocr_status = ticket_details_to_insert.get('ocr_status'),
                    user_id = ticket_details_to_insert.get('user_id'),
                    modelId = ticket_details_to_insert.get('modelId'),
                    hash = ticket_details_to_insert.get('hash'),
                    password = ticket_details_to_insert.get('password'),
                    validation_status_name = ticket_details_to_insert.get('validation_status_name'),
                    validation_name_color = ticket_details_to_insert.get('validation_name_color'),
                    camera_name = ticket_details_to_insert.get('camera_name'),
                    serial = ticket_details_to_insert.get('serial'),
                    plate_image_filename = ticket_details_to_insert.get('plate_image_filename'),
                    speed_unit = speed_unit_change,
                    location_name = ticket_details_to_insert.get('location_name'),
                    static_url = ticket_details_to_insert.get('static_url'),
                    officer_badge = "",
                    img_distance= highest_distance,
                    station = location.station
                    )
                image_obj.save()
                return True
            else:
                print("No data found for the ticket.")
                return False
        else:
            print("Ticket already present")
            return False
            
    except Exception as e:
        print(e)
    return f"{ticket_id}.zip"

def get_zip_ticket_details_v4(ticket_id,api_key):
    ticket_id = str(ticket_id)
    save_path = r"C:\dev_EES\zip_files_extracted"  
    location_url = ENV_CONFIG('GET_ZIP_TICKET_DETAIL_ZIP')
    location_uri = f"{location_url}/{ticket_id}"
    ticket_url = ENV_CONFIG('GET_TICKET_DETAILS_V2')

    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json', 
    }
    try:
        highest_distance = 0
        entry_check=Image.objects.filter(ticket_id=ticket_id).exists()
        if not entry_check:
            response = requests.get(location_uri, headers=headers)
            print(response)
            # response.raise_for_status()

            if response:
                os.makedirs(save_path, exist_ok=True)
                file_path = os.path.join(save_path,ticket_id+ ".zip")
                with open(file_path, "wb") as file:
                    file.write(response.content)

                print("ZIP File with Ticket Details has been downloaded successfully.")

                with zipfile.ZipFile(file_path, 'r') as zip_ref: 
                    zip_file_path= f"{save_path}\\{ticket_id}"
                    print(zip_file_path)
                    zip_ref.extractall(zip_file_path)
                os.remove(zip_file_path+".zip")

                s3_image_urls = []
                files_present=[]
                s3_image_name=[]

                for root, _ ,files in os.walk(save_path):
                    files_present.append(files)
        
                for file in files_present[1]:
                    if file.endswith(('.png' ,'.jpg')):
                        local_file_path = os.path.join(root, file)
                        # print(local_file_path)
                        s3_file_name = os.path.basename(file)  #local_file_path, save_path
                        print(s3_file_name,"s3_file_name") 

                        s3_image_name.append(s3_file_name)
                        s3_folder_name = ENV_CONFIG("AWS_IMAGES_FOLDER_NAME")
                        s3_bucket_name = ENV_CONFIG("AWS_S3_BUCKET_NAME_IMAGE")
                        if s3_upload_file(local_file_path, s3_file_name, s3_folder_name, s3_bucket_name):
                            print(f"Uploaded {file} to S3.")
                            s3_url = f"https://{s3_bucket_name}.s3.amazonaws.com/{s3_folder_name}/{s3_file_name}"
                            s3_image_urls.append(s3_url)
                        else:
                            print(f"Failed to upload{file} to S3")
                        # return s3_image_urls
                    elif file == 'event.xml':
                        highest_distance=extract_xml(zip_file_path)
                        os.remove(os.path.join(root, file))
                    else:
                        os.remove(os.path.join(root, file))
                os.removedirs(zip_file_path)
                    
                for s3_url in range(len(s3_image_urls)):
                    # for s3_file in s3_file_name[1]:
                    image_data_obj = ImageData.objects.create(
                        ticket_id=ticket_id,
                        image_name=s3_image_name[s3_url].split("/")[-1],
                        image_url =s3_image_urls[s3_url]
                    )
                    image_data_obj.save()
                print("Image files from ZIP file have been uploaded to S3 and URLs have been updated in the database.")
                
                headers1 = {
                        'x-api-key': api_key,
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                
                url_ticket = ticket_url + '/' + ticket_id
                ticket_details = requests.get(url_ticket, headers=headers1)
                api_response = ticket_details.json()
                ticket_details_to_insert = api_response.get('ticket')
                ticket_ids = int(ticket_id)
                for hash in ticket_details_to_insert.get('images'):
                    fetch_beam_image_v2(ticket_details_to_insert.get('id'),hash,api_key)

                if ticket_details_to_insert.get('speed_unit') == 'km/h':
                    print("Inside Change")
                    speed_unit_change = 'mi/h'
                    violating_speed_change = round(int(float(ticket_details_to_insert.get('violating_speed'))) * 0.621371)
                    current_speed_limit_change = round(int(float(ticket_details_to_insert.get('current_speed_limit'))) * 0.621371)
                else:
                    speed_unit_change = ticket_details_to_insert.get('current_speed_limit')
                    violating_speed_change = float(ticket_details_to_insert.get('violating_speed'))
                    current_speed_limit_change = ticket_details_to_insert.get('speedLimit')
                location = road_location.objects.get(trafficlogix_location_id = ticket_details_to_insert.get('location_id'))
                image_obj = Image.objects.create(
                    ticket_id = ticket_details_to_insert.get('id'),
                    location_id = ticket_details_to_insert.get('location_id'),
                    time = ticket_details_to_insert.get('time'),
                    data = ticket_details_to_insert.get('data'),
                    current_speed_limit = current_speed_limit_change, 
                    violating_speed = violating_speed_change,
                    plate_text = ticket_details_to_insert.get('plate_text'),
                    locked = ticket_details_to_insert.get('locked'),
                    ocr_status = ticket_details_to_insert.get('ocr_status'),
                    user_id = ticket_details_to_insert.get('user_id'),
                    modelId = ticket_details_to_insert.get('modelId'),
                    hash = ticket_details_to_insert.get('hash'),
                    password = ticket_details_to_insert.get('password'),
                    validation_status_name = ticket_details_to_insert.get('validation_status_name'),
                    validation_name_color = ticket_details_to_insert.get('validation_name_color'),
                    camera_name = ticket_details_to_insert.get('camera_name'),
                    serial = ticket_details_to_insert.get('serial'),
                    plate_image_filename = ticket_details_to_insert.get("plate_image_filename"),
                    speed_unit = speed_unit_change,
                    location_name = ticket_details_to_insert.get('location_name'),
                    static_url = ticket_details_to_insert.get('static_url'),
                    officer_badge = "",
                    img_distance= highest_distance,
                    station = location.station
                    )
                image_obj.save()
                return True
            else:
                print("No data found for the ticket.")
                return False
        else:
            print("Ticket already present")
            return False
            
    except Exception as e:
        print(e)
    return f"{ticket_id}.zip"

def extract_xml(request): 

    main_directory = r'C:\dev_EES\zip_files_extracted'

    highest_distance = float('-inf')  
    for root, dirs, _ in os.walk(main_directory):
        for folder_name in dirs:
            folder_path = os.path.join(root, folder_name)
            filepath = os.path.join(folder_path, 'event.xml')

            if os.path.isfile(filepath):
                try:
                    tree = ET.parse(filepath)
                    root_element = tree.getroot()  

                    for sample in root_element.findall('.//sample'):  
                        distance_m_element = sample.find('distance_m')
                        if distance_m_element is not None:
                            distance_m = float(distance_m_element.text)
                            if distance_m > highest_distance: 
                                highest_distance = distance_m
                    if highest_distance != float('-inf'):  
                        print("Highest distance (m):", highest_distance)
                        return highest_distance 
                    else:
                        print("No distance values found in the XML file.")
                except Exception as e:
                    print("Error:", e)
            else:
                print("File 'event.xml' not found in the specified folder.")

    if highest_distance == float('-inf'):
        print("No folder path found")


def fetch_beam_image(ticket_id,image_hash,api_key):
    save_path = "C:\dev_EES_Images\Beam_Images"  
    s3_folder_name = ENV_CONFIG("AWS_IMAGES_FOLDER_NAME")
    s3_bucket_name = ENV_CONFIG("AWS_S3_BUCKET_NAME_IMAGE")
    hash_image_url = ENV_CONFIG('GET_HASH_IMAGE')
    hash_image_url = f"{hash_image_url}/{image_hash}"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
    }
    response = requests.get(hash_image_url, headers=headers)
    print(response)
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path,ticket_id+'-'+image_hash+'.png')
    with open(file_path, "wb") as file:
        file.write(response.content)

    if s3_upload_file(file_path, ticket_id+'-'+image_hash+'.png', s3_folder_name, s3_bucket_name):
        print(f"Uploaded {file} to S3.")
    else:
        print(f"Failed to upload{file} to S3")

    image = ImageHash.objects.create(
        ticket_id = ticket_id,
        image_hash = image_hash,
        image_url = f"https://{s3_bucket_name}.s3.amazonaws.com/{s3_folder_name}/{ticket_id+'-'+image_hash+'.png'}"
    )
    image.save()

    print("image File with Ticket Details has been downloaded successfully.")

def fetch_beam_image_v2(ticket_id,image_hash,api_key):
    save_path = "C:\dev_EES_Images\Beam_Images"  
    s3_folder_name = ENV_CONFIG("AWS_IMAGES_FOLDER_NAME")
    s3_bucket_name = ENV_CONFIG("AWS_S3_BUCKET_NAME_IMAGE")
    hash_image_url = ENV_CONFIG('GET_HASH_IMAGE_V2')
    hash_image_url = f"{hash_image_url}/{image_hash}"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'image/jpg',
    }
    response = requests.get(hash_image_url, headers=headers)
    print(response)
    os.makedirs(save_path, exist_ok=True)
    ticket_id =str(ticket_id)
    file_path = os.path.join(save_path,ticket_id+ '-' + image_hash +'.png')
    with open(file_path, "wb") as file:
        file.write(response.content)

    if s3_upload_file(file_path, ticket_id+'-'+image_hash+'.png', s3_folder_name, s3_bucket_name):
        print(f"Uploaded {file} to S3.")
    else:
        print(f"Failed to upload{file} to S3")

    image = ImageHash.objects.create(
        ticket_id = ticket_id,
        image_hash = image_hash,
        image_url = f"https://{s3_bucket_name}.s3.amazonaws.com/{s3_folder_name}/{ticket_id+'-'+image_hash+'.png'}"
    )
    image.save()

    print("image File with Ticket Details has been downloaded successfully.")


def get_ticket_list_by_location(location_id,api_key):
    
    todays_date = datetime.datetime.now()
    todays_date = todays_date.date()
    days_gap = datetime.timedelta(days = 9)
    past_date = todays_date - days_gap
    past_date = past_date

    ticket_list_url = ENV_CONFIG('GET_TICKET_LIST_BY_LOCATION')
    ticket_list_url = f"{ticket_list_url}/{location_id}/date-from/2024-09-29/date-to/2024-09-30/ocr_status/10/count/50/miles"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
    }
    try:
        response = requests.get(ticket_list_url, headers=headers)
        api_response = response.json()
        
        tickets_data = {
            'location_id': location_id,
            'tickets': []
        }
        
        tickets = api_response.get('tickets', [])
        
        if tickets:
            for ticket in tickets:
                ticket_id = ticket.get('id')
                ticket_dict = {
                    'ticket_id': ticket_id
                }
                tickets_data['tickets'].append(ticket_dict)
                
            print("tickets successfully retrieved.")
        else:
            print("No tickets found for the company ID.")

        return tickets_data

    except Exception as e:
        print(f"Error fetching tickets data: {e}")
        return None

def get_ticket_list_by_location_v4(location_id,api_key,account_id):
    
    todays_date = datetime.datetime.now()
    todays_date = todays_date.date()

    ticket_list_url = ENV_CONFIG('GET_TICKET_DETAILS_V4')
    # ticket_list_url = f"{ticket_list_url}/{location_id}/date-from/{past_date}/date-to/{todays_date}/ocr_status/10/count/50/miles"
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json',
        'X-Requested-With' :'XMLHttpRequest'
    }

    body = {
            "dateFrom": f"{todays_date} 00:00:00",
            "dateTo": f"{todays_date} 23:59:00",
            "exportStatus": None,
            "status": 10,
            "accountId": account_id,
            "units": 1,
            "optional": True,
        }
    try:
        response = requests.post(ticket_list_url, headers=headers, json=body)
        api_response = response.json()
        
        tickets_data = {
            'location_id': location_id,
            'tickets': []
        }
        
        tickets = api_response.get('tickets', [])
        
        if tickets:
            for ticket in tickets:
                date_str = ticket.get('dateTimeLocal')
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                tickets_data['tickets'].append({
                    'ticket_id': ticket.get('id'),
                    'dateTimeLocal': date_obj
                })
            tickets_data['tickets'].sort(key=lambda x: x['dateTimeLocal'])   
            print("tickets successfully retrieved.")
        else:
            print("No tickets found for the company ID.")

        return tickets_data

    except Exception as e:
        print(f"Error fetching tickets data: {e}")
        return None

def get_location_details(location_id,api_key):
    location_obj = None
    try:
        entry_check = ImageLocation.objects.filter(location_id=location_id).exists()
        if not entry_check:
            location_url = ENV_CONFIG('GET_LOCATION_DETAILS')
            location_uri = f"{location_url}/{location_id}"
            headers = {
                'x-api-key': api_key,
                'Content-Type': 'application/json',
            }

            location_details = requests.get(location_uri, headers=headers)
            location_details.raise_for_status()

            api_response = location_details.json()
            location_details_to_insert = api_response.get('location')

            location_obj = ImageLocation.objects.create(
                location_id = location_details_to_insert.get('id'),
                company_id = location_details_to_insert.get('company_id'),
                radar_id = location_details_to_insert.get('radar_id'),
                name = location_details_to_insert.get('name'),
                address = location_details_to_insert.get('address'),
                city = location_details_to_insert.get('city'),
                state = location_details_to_insert.get('state'),
                country = location_details_to_insert.get('country'),
                zip = location_details_to_insert.get('zip'),
                contact_user_id = location_details_to_insert.get('contact_user_id'),
                timezone_id = location_details_to_insert.get('timezone_id'),
                direction = location_details_to_insert.get('direction'),
                group_id = location_details_to_insert.get('group_id'),
                latitude = location_details_to_insert.get('geocode').split(',')[0].replace('(', ''),
                longitude = location_details_to_insert.get('geocode').split(',')[1].replace(')', ''),
                tz = location_details_to_insert.get('tz'),
            )
            location_obj.save()
        return location_obj.id
    except Exception as e:
        print(e)
        return None

def set_export_status_ticket(ticket_id,api_key,status_code):
    base_url = ENV_CONFIG('GET_TICKET_DETAILS')
    print(f"Export Status update of the ticket number {ticket_id}")
    try:
        headers = {
                'x-api-key': api_key,
                'Content-Type': 'application/json',
            }
        set_export_status_url = f"{base_url}/{ticket_id}/export-status/{status_code}"
        response = requests.post(set_export_status_url, headers=headers)
        return f"Export status updated for ticket no. {ticket_id}"
    except Exception as e:
        return e