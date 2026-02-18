from video.citations.versioning_utils import get_snapshot_by_version, get_latest_version_number
from rest_framework.response import Response
import csv
import re

from video.models import Citation, PreOdrXpressBillPay, QuickPD, UnpaidCitation, CitationsWithEditFine

def format_csv(input_file,):
    try:
        col = ['offense_date', 'offense_time', 'ticket_num', 'first_name', 'middle', 'last_name', 'generation', 'address',
            'city', 'state', 'zip', 'dob', 'race', 'sex', 'height', 'weight', 'ssn', 'dl', 'dl_state', 'accident',
            'comm', 'vehder', 'arraignment_date', 'actual_speed', 'posted_speed', 'officer_badge', 'street1_id',
            'street2_id', 'street1_name', 'street2_name', 'bac', 'test_type', 'plate_num', 'plate_state', 'vin',
            'phone_number', 'radar', 'state_rs1', 'state_rs2', 'state_rs3', 'state_rs4', 'state_rs5', 'warning',
            'notes', 'dl_class', 'station_id']

        data_1 = [
            {'C':'C', 'Traffic':'Traffic', 'MPD':'MPD', 'offense_date':'offense_date', 'offense_time':'offense_time', 'station_id':'station_id', 'plate_num':'plate_num', 'plate_state':'plate_state', 'vin':'vin', 'arraignment_date':'arraignment_date', 'officer_badge':'officer_badge', 'dl':'dl', 'dl_state':'dl_state', 'ticket_num':'ticket_num'},
            {'D':'D', 'first_name':'first_name', 'middle':'middle', 'last_name':'last_name', 'address':'address', 'city':'city', 'state':'state', 'zip':'zip', 'dob':'dob'},
            {'O':'O', 'state_rs1':'state_rs1', 'actual_speed':'actual_speed', 'posted_speed':'posted_speed'}
        ]

        with open(input_file, 'r') as initial_csv:
            data = [row + [''] * (len(col) - len(row)) for row in csv.reader(initial_csv)]

        with open(input_file, 'w', newline='') as csvfile:
            columns = [key for item in data_1 for key in item.keys()]
            writer = csv.DictWriter(csvfile, fieldnames=columns)

            for row in data:
                for item in data_1:
                    for key, value in item.items():
                        if key in col:
                            item[key] = row[col.index(key)]
                        if key == 'station_id':
                            item[key] = 14
                        if key == 'state_rs1':
                            item[key] = row[col.index(key)][:3] + '-' + row[col.index(key)][4:8]
                for item in data_1:
                    writer.writerow(item)

        with open(input_file, 'r') as initial_csv:
            final_data = [row for row in csv.reader(initial_csv)]

        for inner_list in final_data:
            i = 0
            while i < len(inner_list):
                if inner_list[i] == '' and i > 0 and inner_list[i - 1] == '':
                    del inner_list[i]
                    del inner_list[i - 1]
                else:
                    i += 1

            while inner_list and inner_list[0] == '':
                del inner_list[0]
            
            if inner_list[0] == 'D':
                inner_list.extend([''] * 3)
            elif inner_list[0] == 'O':
                inner_list.extend([''] * 7)

        with open(input_file, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(final_data)
        
        print("Successfully modified MOR-C csv file")

    except Exception as e:
        print(e)

def xpress_csv(input_file, fine, issuing_agency):
    try:
        col = ['id', 'offense_date', 'offense_time', 'ticket_num', 'first_name', 'middle', 'last_name', 'generation', 'address',
               'city', 'state', 'zip', 'dob', 'race', 'sex', 'height', 'weight', 'ssn', 'dl', 'dl_state', 'accident',
               'comm', 'vehder', 'arraignment_date', 'actual_speed', 'posted_speed', 'officer_badge', 'street1_id',
               'street2_id', 'street1_name', 'street2_name', 'bac', 'test_type', 'plate_num', 'plate_state', 'vin',
               'phone_number', 'radar', 'state_rs1', 'state_rs2', 'state_rs3', 'state_rs4', 'state_rs5', 'warning',
               'notes', 'dl_class', 'station_id', 'fine', 'issuing_agency']

        print(len(col))

        with open(input_file, 'r') as initial_csv:
            reader = csv.reader(initial_csv)
            data = [row for row in reader]
            for row in data:
                if len(row) < len(col) - 3:
                    row.extend([''] * (len(col) - 3 - len(row)))
                id_num = QuickPD.objects.filter(ticket_num =row[2]).last()
                citation_data = Citation.objects.filter(citationID =id_num.ticket_num).first()
                if citation_data:
                    citation_version = get_latest_version_number(citation_data)
                    version_data = get_snapshot_by_version(citation_data, citation_version)
                    if not version_data:
                        return Response({
                            "statusCode": 404,
                            "message": "Version not found"
                        }, status=404)

                    snapshot = version_data["snapshot"]
                    fine = snapshot.get("fine", {})
                    citation_fine = str(fine.get("amount", {}))
                    # if citation_data and citation_data.current_citation_status == "EF":
                    #     cef_object = CitationsWithEditFine.objects.filter(citation=citation_data).first()
                    #     if cef_object:
                    #         citation_fine = cef_object.new_fine
                    # else:
                    #     citation_fine  = citation_data.fine.fine
                else:
                    citation_fine = fine
                row.insert(0,id_num.id)
                row.append(str(citation_fine))
                row.append(issuing_agency)
        with open(input_file, 'w', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(col)
            csv_writer.writerows(data)
        print("Successfully generated for Xpress Bill Pay")

    except Exception as e:
        print(e)

# class Sftp:
#     def __init__(self, hostname, username, password, cnopts , port=22):
#         self.connection = None
#         self.hostname = hostname
#         self.username = username
#         self.password = password
#         self.port = port
#         self.cnopts = cnopts

#     def connect(self):
#         """Connects to the sftp server and returns the sftp connection object"""
#         try:
#             self.connection = pysftp.Connection(
#                 host=self.hostname,
#                 username=self.username,
#                 password=self.password,
#                 port=self.port,
#                 cnopts = self.cnopts
#             )

#         except Exception as err:
#             raise Exception(err)
#         finally:
#             print(f"Connected to {self.hostname} as {self.username}.")


#     def disconnect(self):
#         """Closes the sftp connection"""
#         self.connection.close()
#         print(f"Disconnected from host {self.hostname}")

#     def listdir(self, remote_path):
#         """lists all the files and directories in the specified path and returns them"""
#         for obj in self.connection.listdir(remote_path):
#             yield obj

#     def listdir_attr(self, remote_path):
#         """lists all the files and directories (with their attributes) in the specified path and returns them"""
#         for attr in self.connection.listdir_attr(remote_path):
#             yield attr

#     def download(self, remote_path, target_local_path):
#         """
#         Downloads the file from remote sftp server to local.
#         Also, by default extracts the file to the specified target_local_path
#         """

#         try:
#             print(
#                 f"downloading from {self.hostname} as {self.username} [(remote path : {remote_path});(local path: {target_local_path})]"
#             )

#             # Create the target directory if it does not exist
#             path, _ = os.path.split(target_local_path)
#             if not os.path.isdir(path):
#                 try:
#                     os.makedirs(path)
#                 except Exception as err:
#                     raise Exception(err)

#             # Download from remote sftp server to local
#             self.connection.get(remote_path, target_local_path)
#             print("download completed")

#         except Exception as err:
#             raise Exception(err)

#     def upload(self, source_local_path, remote_path):
#         """
#         Uploads the source files from local to the sftp server.
#         """

#         try:
#             print(
#                 f"uploading to {self.hostname} as {self.username} [(remote path: {remote_path});(source local path: {source_local_path})]"
#             )

#             # Download file from SFTP
#             self.connection.put(source_local_path, remote_path)
#             print("upload completed")

#         except Exception as err:
#             raise Exception(err)
    
def sanitize_text(value):
    """
    Sanitize a string to remove unwanted characters.
    Keeps only alphanumerics, spaces, dots, commas, and hyphens.
    Converts None or non-string values to strings safely.
    """
    if value is None:
        return ''
    value = str(value).strip()
    return re.sub(r'[^\w\s.,-]', '', value)

def xpress_csv_pre_odr(input_file, issuing_agency):
    try:
        col = ['id', 'offense_date', 'offense_time', 'ticket_num', 'first_name', 'middle', 'last_name', 'generation', 'address',
               'city', 'state', 'zip', 'dob', 'race', 'sex', 'height', 'weight', 'ssn', 'dl', 'dl_state', 'accident',
               'comm', 'vehder', 'arraignment_date', 'actual_speed', 'posted_speed', 'officer_badge', 'street1_id',
               'street2_id', 'street1_name', 'street2_name', 'bac', 'test_type', 'plate_num', 'plate_state', 'vin',
               'phone_number', 'radar', 'state_rs1', 'state_rs2', 'state_rs3', 'state_rs4', 'state_rs5', 'warning',
               'notes', 'dl_class', 'station_id', 'fine', 'issuing_agency']

        print(f"Expecting {len(col)} columns")

        with open(input_file, 'r') as csv_input:
            reader = csv.reader(csv_input)
            data = []
            ticket_nums = []
            for row in reader:
                # Pad row if it's short
                while len(row) < len(col) - 3:
                    row.append('')

                ticket_number = row[2]
                if ticket_number in ticket_nums:
                    continue
                else:
                    ticket_nums.append(ticket_number)
                print(f"Processing ticket: {ticket_number}")

                pre_odr_obj = PreOdrXpressBillPay.objects.filter(ticket_num=ticket_number).first()
                if not pre_odr_obj:
                    print(f"Warning: Ticket {ticket_number} not found in DB.")
                    continue

                id_num = pre_odr_obj.id
                unpaid_citation_object = UnpaidCitation.objects.filter(ticket_number=ticket_number, is_deleted=False).first()
                if not unpaid_citation_object:
                    continue
                fine = unpaid_citation_object.first_mail_fine

                # Sanitize
                row = [sanitize_text(value) for value in row]

                # Insert new data
                row.insert(0, id_num)
                row.append(str(fine))
                row.append(issuing_agency)

                data.append(row)

        with open(input_file, 'w', newline='') as csv_out:
            writer = csv.writer(csv_out)
            writer.writerow(col)
            writer.writerows(data)

        print("Successfully generated for Xpress Bill Pay")

    except Exception as e:
        print(f"Error occurred: {e}")


# import cv2
# import math
# import numpy as np
# import requests
# import boto3
# from urllib.parse import urlparse

# # Setup AWS S3 client
# s3 = boto3.client("s3")

# def read_image_from_url(url):
#     response = requests.get(url)
#     if response.status_code == 200:
#         img_array = np.frombuffer(response.content, np.uint8)
#         return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
#     else:
#         raise Exception(f"Failed to fetch image: {url}")

# def get_aspect_ratio_cv2(image):
#     height, width = image.shape[:2]
#     ratio = width / height
#     gcd = math.gcd(width, height)
#     return ratio, (width, height), (width // gcd, height // gcd)

# def convert_to_custom_ratio(image, target_width=2048, target_height=1713, method='crop'):
#     target_aspect = target_width / target_height
#     h, w = image.shape[:2]
#     current_aspect = w / h

#     if method == 'crop':
#         if current_aspect > target_aspect:
#             # Crop width
#             new_width = int(h * target_aspect)
#             offset = (w - new_width) // 2
#             image = image[:, offset:offset + new_width]
#         else:
#             # Crop height
#             new_height = int(w / target_aspect)
#             offset = (h - new_height) // 2
#             image = image[offset:offset + new_height, :]
#     else:  # pad
#         new_w = max(w, int(h * target_aspect))
#         new_h = max(h, int(w / target_aspect))
#         pad_top = (new_h - h) // 2
#         pad_bottom = new_h - h - pad_top
#         pad_left = (new_w - w) // 2
#         pad_right = new_w - w - pad_left
#         image = cv2.copyMakeBorder(
#             image,
#             pad_top, pad_bottom,
#             pad_left, pad_right,
#             borderType=cv2.BORDER_CONSTANT,
#             value=[255, 255, 255]  # white padding
#         )

#     return cv2.resize(image, (target_width, target_height))

# def parse_s3_url(presigned_url):
#     parsed = urlparse(presigned_url)
#     bucket = parsed.netloc.split('.')[0]
#     key = parsed.path.lstrip('/')
#     return bucket, key

# def upload_to_s3(image, bucket, key):
#     _, img_encoded = cv2.imencode('.jpg', image)
#     s3.put_object(Bucket=bucket, Key=key, Body=img_encoded.tobytes(), ContentType='image/jpeg')
#     print(f"✅ Re-uploaded to S3 at s3://{bucket}/{key}")

# def process_image_from_url_and_reupload(presigned_url, method='pad'):
#     bucket, key = parse_s3_url(presigned_url)
#     image = read_image_from_url(presigned_url)
#     ratio, (w, h), (sw, sh) = get_aspect_ratio_cv2(image)

#     print(f"[INFO] Image: {key} — Size: {w}x{h} — Ratio: {sw}:{sh}")
#     if ratio < (16 / 9):
#         print("       ➤ Converting to 16:9 with white padding...")
#         image = convert_to_custom_ratio(image, method=method)
#     else:
#         print("       ✓ Already 16:9 or wider, resizing only...")
#         image = cv2.resize(image, (1280, 720))

#     upload_to_s3(image, bucket, key)

import winreg

def is_windows_fips_enabled():
    try:
        reg_path = r"SYSTEM\CurrentControlSet\Control\Lsa\FipsAlgorithmPolicy"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as reg_key:
            value, _ = winreg.QueryValueEx(reg_key, "Enabled")
            print(f"Registry value read: {value}")  # Debug
            return value == 1
    except FileNotFoundError:
        print("FIPS policy registry key not found.")
        return False
    except PermissionError:
        print("Permission denied: Run Python as Administrator.")
        return False
    except Exception as e:
        print(f"Unexpected error reading FIPS registry: {e}")
        return False
