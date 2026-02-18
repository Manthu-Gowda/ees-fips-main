import logging
import os
import base64
import boto3
from regex import E
import requests
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from decouple import config as ENV_CONFIG
from video.models import Agency, Fine, Station
from django.db.models import Max
from concurrent.futures import ThreadPoolExecutor, as_completed
from accounts.models import PermissionLevel,Station, User
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

s3_signature = {"v4": "s3v4", "v2": "s3"}
BASE_DIR = ENV_CONFIG("BASE_DIR")

AWS_S3_BUCKET_NAME_DOCK = ENV_CONFIG("AWS_S3_BUCKET_NAME_DOCK")
AWS_S3_BUCKET_NAME = ENV_CONFIG("AWS_S3_BUCKET_NAME")
AWS_REGION = ENV_CONFIG("AWS_REGION")
# AWS_ACCESS_KEY = ENV_CONFIG("AWS_ACCESS_KEY")
# AWS_SECRET_KEY = ENV_CONFIG("AWS_SECRET_KEY")
AWS_S3_EXPECTED_OWNER = ENV_CONFIG("AWS_ACCOUNT_OWNER_ID")


class S3Client:
    def __init__(self):
        config = Config(
            region_name=AWS_REGION,
            signature_version=s3_signature["v4"],

        )

        self.client = boto3.client(
            "s3",
            # aws_access_key_id=AWS_ACCESS_KEY,
            # aws_secret_access_key=AWS_SECRET_KEY,
            config=config,
        )

        print(f"S3 Client has been intitalized and connected over {self.client.meta.endpoint_url}")




s3 = S3Client()
s3_client = s3.client


# s3_client = boto3.client(
#     "s3",
#     aws_access_key_id=AWS_ACCESS_KEY,
#     aws_secret_access_key=AWS_SECRET_KEY,
#     config=Config(signature_version=s3_signature["v4"]),
#     region_name=AWS_REGION,
# )


def s3_download_file(
    file_name, folder_name, local_path, bucket_name=AWS_S3_BUCKET_NAME
):
    file_path = f"{folder_name}/{file_name}"
    local_file_path = f"{local_path}/{file_name}"

    try:
        s3_client.head_object(
            Bucket=bucket_name, Key=file_path, ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER
        )
    except s3_client.exceptions.ClientError:
        return False

    s3_client.download_file(
        Bucket=bucket_name,
        Key=file_path,
        Filename=local_file_path,
        ExtraArgs={"ExpectedBucketOwner": AWS_S3_EXPECTED_OWNER},
    )
    return True


def s3_upload_file(local_file_path, file_name, folder_name, bucket_name):
    file_path = f"{folder_name}/{file_name}"
    local_file_path = os.path.join(BASE_DIR, local_file_path)

    with open(local_file_path, "rb") as f:
        s3_client.upload_fileobj(
            f,
            bucket_name,
            file_path,
            ExtraArgs={"ExpectedBucketOwner": AWS_S3_EXPECTED_OWNER},
        )
        os.remove(local_file_path)

    file_url = f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{file_path}"
    # file_url = create_presigned_url(file_path, bucket_name)

    return file_url


def s3_check_folder_exists(folder_name):
    try:
        s3_client.head_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=folder_name,
            ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER,
        )
        return True
    except ClientError:
        return False


def s3_delete_files_in_folder(folder_name, bucket_name=AWS_S3_BUCKET_NAME):
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=folder_name,
        ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER,
    )
    if "Contents" in response:
        for item in response["Contents"]:
            s3_client.delete_object(Bucket=bucket_name, Key=item["Key"], ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER)

def create_presigned_url(bucket_key, bucket_name=AWS_S3_BUCKET_NAME, expiration=3600):
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": bucket_key},
            ExpiresIn=expiration,
        )

    except ClientError as e:
        logging.error(e)
        return None
    return response




from urllib.parse import urlparse

def extract_s3_key_from_url(url):
    if not url:
        raise ValueError("URL cannot be None")

    parsed = urlparse(url)
    host = parsed.netloc
    path = parsed.path.lstrip("/")

    # Case: Virtual-hosted–style (bucket.s3-region.amazonaws.com)
    if ".s3." in host or ".s3-" in host:
        bucket = host.split(".")[0]
        key = path
        return bucket, key
    
    # Case: FIPS or path-style (s3-fips.region.amazonaws.com/bucket/key)
    if host.startswith("s3") or host.startswith("s3-fips"):
        parts = path.split("/", 1)
        if len(parts) != 2:
            raise ValueError("Invalid path-style S3 URL")
        bucket, key = parts
        return bucket, key

    raise ValueError(f"Unrecognized S3 URL: {url}")


def s3_get_file(path):
    try:
        response = s3_client.get_object(
            Bucket=AWS_S3_BUCKET_NAME,
            Key=path,
            ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER,
        )

        return response["Body"].read()

    except NoCredentialsError:
        print("Credentials not available")
        return ""


def upload_to_s3(file, file_name, folder_name):
    try:
        file_path = f"{folder_name}/{file_name}"
        s3_client.upload_fileobj(
            Fileobj=file,
            Bucket=AWS_S3_BUCKET_NAME,
            Key=file_path,
            ExtraArgs={"ExpectedBucketOwner": AWS_S3_EXPECTED_OWNER},
        )

        file_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_path}"
        return file_url

    except NoCredentialsError:
        print("Credentials not available")
        return ""


# def s3_dock_create_folder(agency_name, dock_name="LE2669"):
#     try:
#         folder_path = f"{agency_name}/{dock_name}/"
#         s3_client.put_object(
#             Bucket=AWS_S3_BUCKET_NAME_DOCK,
#             Key=folder_path,
#             ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER,
#         )

#     except NoCredentialsError:
#         print("Credentials not available")

#     return ""


def s3_create_folder(folder_name):

    s3_client.put_object(Bucket=AWS_S3_BUCKET_NAME, Key=folder_name, Body="", ExpectedBucketOwner=AWS_S3_EXPECTED_OWNER)

    print(f"Folder {folder_name} created in AWS S3 bucket.")


# def s3_seed_agency_folders(agency_name, dock_name="LE2669"):
#     s3_dock_create_folder(agency_name, dock_name)

#     for folder in ["Videos", "Images", "PDFs", "CSVs"]:
#         if folder == "Videos":
#             for name in ["speed_pictures", "license_plate_pictures"]:
#                 s3_create_folder(f"{agency_name}/{folder}/{name}/")

#         elif folder == "Images":
#             s3_create_folder(f"{agency_name}/{folder}/badge_picture/")

#         s3_create_folder(f"{agency_name}/{folder}/")


def get_presigned_url(s3_url):
    if not s3_url:
        return None
    bucket_name, key = extract_s3_key_from_url(s3_url)
    url = create_presigned_url(key, bucket_name)

    return url


def get_presigned_url_base64string(s3_url):
    if not s3_url:
        return None
    bucket_name, key = extract_s3_key_from_url(s3_url)
    url = create_presigned_url(key, bucket_name)
    response = requests.get(url)
    if not url:
        return None
    base64_encoded_url = base64.b64encode(response.content).decode("utf-8")
    return base64_encoded_url


def get_base64_from_presigned_url(s3_url):
    if not s3_url:
        return None
    response = requests.get(s3_url)
    base64_encoded_url = base64.b64encode(response.content).decode("utf-8")
    return base64_encoded_url


def add_station_default_fines(station_name, rs_code):
    station_id = Station.objects.get(name=station_name).id

    fine_max_id = Fine.objects.aggregate(Max("id"))["id__max"] or 0  # handle None case
    est_fines = Fine.objects.filter(station__name="EST").values()

    default_fines = []
    for i, est_fine in enumerate(est_fines):
        est_fine.pop("id")
        est_fine.pop("station_id")

        if rs_code not in [None, "", "n/a", "N/A"]:
            est_fine["rs_code"] = est_fine["rs_code"].replace("2022-168", rs_code)

        est_fine["id"] = fine_max_id + i + 1
        default_fines.append(est_fine)

    for fine in default_fines:
        print(fine)
        Fine.objects.create(
            id=fine["id"],
            station_id=station_id,
            **{k: v for k, v in fine.items() if k != "id"},
        )


# This code is for the Rest Api
import jwt
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

# Load the public key from file (used for verifying RS256 tokens)
with open(settings.BASE_DIR / "keys" / "public_key_4096.pem", "r") as f:
    PUBLIC_KEY = f.read()


class TokenService:
    @staticmethod
    def extract_claims_from_token(request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            try:
                decoded_data = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
                return {
                    "user_id": decoded_data.get("user_id", None),
                    "username": decoded_data.get("username", None),
                    "email": decoded_data.get("email", None),
                    "isSuperuser": decoded_data.get("isSuperuser", None),
                    "agencyId": decoded_data.get("agencyId", None),
                    "isStaff": decoded_data.get("isStaff", None),
                    "isAdjudicator": decoded_data.get("isAdjudicator", None),
                    "isSupervisor": decoded_data.get("isSupervisor", None),
                    "isSuperAdmin": decoded_data.get("isSuperAdmin", None),
                    "isCourt": decoded_data.get("isCourt", None),
                    "isAdmin": decoded_data.get("isAdmin", None),
                    "agencyName": decoded_data.get("agencyName", None),
                    "stationId": decoded_data.get("stationId", None),
                    "stationName": decoded_data.get("stationName", None),
                    "stateId": decoded_data.get("stateId", None),
                    "stateName": decoded_data.get("stateName", None),
                    "stationModifiedName": decoded_data.get(
                        "stationModifiedName", None
                    ),
                }

            except ExpiredSignatureError:
                return Response(
                    {"error": "Token has expired"}, status=status.HTTP_401_UNAUTHORIZED
                )
            except InvalidTokenError:
                return Response(
                    {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
                )

        else:
            return Response(
                {"error": "Authorization header is missing or not valid"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


# class RedisClient:
#     def __init__(self):
#         self.client = redis.Redis.from_url(settings.CACHES['default']['LOCATION'], decode_responses=True)

#     def set(self, key, value, expiry=None):
#         self.client.set(key, value, ex=expiry)

#     def get(self, key):
#         return self.client.get(key)

#     def delete(self, key):
#         self.client.delete(key)

# redis_client = RedisClient()


def get_base64_image_from_url(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode("utf-8")
    except:
        return None


def create_presigned_url_PDF(
    bucket_key, bucket_name=AWS_S3_BUCKET_NAME, expiration=3600, download=False
):
    try:
        params = {"Bucket": bucket_name, "Key": bucket_key}

        # Special handling for PDFs
        if bucket_key.lower().endswith(".pdf"):
            if download:
                params["ResponseContentDisposition"] = "attachment"
            else:
                params["ResponseContentDisposition"] = "inline"
                params["ResponseContentType"] = "application/pdf"

        response = s3_client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiration,
        )
        return response

    except ClientError as e:
        logging.error(e)
        return None


def get_presigned_url_PDF(s3_url, download=True):
    if not s3_url:
        return None
    bucket_name, key = extract_s3_key_from_url(s3_url)
    print(bucket_name, key, "inside get_presigned")

    url = create_presigned_url_PDF(key, bucket_name, download=download)
    return url


# def upload_non_violation_folder_to_s3(folder_path, bucket_name, s3_prefix=""):

#     try:
#         for root, dirs, files in os.walk(folder_path):
#             for file_name in files:
#                 local_path = os.path.join(root, file_name)

#                 # Relative path inside the folder, used for S3 key
#                 relative_path = os.path.relpath(local_path, folder_path)
#                 s3_key = os.path.join(s3_prefix, relative_path).replace("\\", "/")

#                 print(f"Uploading {local_path} to s3://{bucket_name}/{s3_key}")
#                 s3_client.upload_file(local_path, bucket_name, s3_key)

#                 # Delete the file locally after successful upload
#                 os.remove(local_path)
#                 print(f"Deleted local file: {local_path}")

#         # Optionally remove empty dirs
#         for root, dirs, _ in os.walk(folder_path, topdown=False):
#             for d in dirs:
#                 dir_path = os.path.join(root, d)
#                 if not os.listdir(dir_path):  # delete only if empty
#                     os.rmdir(dir_path)
#                     print(f"Deleted empty directory: {dir_path}")

#         print("Move completed successfully!")

#     except ClientError as e:
#         print(f"Error uploading files: {e}")


def upload_single_file(local_path, bucket_name, s3_key):
    """Helper for parallel upload."""
    try:
        s3_client.upload_file(
            local_path,
            bucket_name,
            s3_key,
            ExtraArgs={"ExpectedBucketOwner": AWS_S3_EXPECTED_OWNER},
        )
        os.remove(local_path)
        return (local_path, True)
    except Exception as e:
        return (local_path, False, str(e))


def upload_non_violation_folder_to_s3(
    folder_path, bucket_name, s3_prefix="", max_workers=10
):
    """Highly optimized parallel uploader."""
    all_files = []
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            local_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(local_path, folder_path)
            s3_key = os.path.join(s3_prefix, relative_path).replace("\\", "/")
            all_files.append((local_path, s3_key))

    total_files = len(all_files)
    print(f"Found {total_files:,} files to upload.")

    if not all_files:
        print("No files found.")
        return

    success, fail = 0, 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(upload_single_file, f, bucket_name, k): (f, k)
            for f, k in all_files
        }

        for i, future in enumerate(as_completed(future_to_file), 1):
            local_path, result = None, None
            try:
                result = future.result()
                if result[1]:
                    success += 1
                else:
                    fail += 1
                    print(f"Failed: {result[0]} - {result[2]}")
            except Exception as e:
                fail += 1
                print(f"Exception while uploading: {e}")

            if i % 500 == 0:
                print(f"Progress: {i}/{total_files} ({(i/total_files)*100:.2f}%)")

    # Clean up empty folders
    for root, dirs, _ in os.walk(folder_path, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)

    print(f"Completed. Success: {success}, Failed: {fail}, Total: {total_files}")


# your_project/api/utils.py
from django.http import HttpRequest


def identify_consumer(request: HttpRequest):
    # 1️⃣ Check if Django already knows the user (e.g. login session)
    if hasattr(request, "user") and request.user.is_authenticated:
        return f"{request.user.id}-{request.user.username}"

    # 2️⃣ If not authenticated via session, try to decode JWT manually
    try:
        readToken = TokenService.extract_claims_from_token(request)
        if isinstance(readToken, dict):
            user_id = readToken.get("user_id")
            username = readToken.get("userName") or readToken.get("username")
            if user_id and username:
                return f"{user_id}-{username}"
    except Exception:
        pass

    return None


import re
import csv
from collections import defaultdict


def count_all_file_dates():
    date_regex = re.compile(r"(\d{4}-\d{2}-\d{2})")
    date_counts = defaultdict(int)

    continuation_token = None

    while True:
        kwargs = {
            "Bucket": AWS_S3_BUCKET_NAME,
            "Prefix": "tattile/non-violation",
            "ExpectedBucketOwner": AWS_S3_EXPECTED_OWNER,
        }

        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3_client.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]

            match = date_regex.search(key)
            if match:
                file_date = match.group(1)
                date_counts[file_date] += 1

        if response.get("IsTruncated"):
            continuation_token = response["NextContinuationToken"]
        else:
            break
    csv_output_path = r"C:\Users\EM\Downloads\count.csv"
    # ---- Write CSV ----
    with open(csv_output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "count"])

        for date_str, count in sorted(date_counts.items()):
            writer.writerow([date_str, count])

    return date_counts

def search_zip_files_json():

    matched_files = []
    continuation_token = None

    while True:
        kwargs = {
            "Bucket": AWS_S3_BUCKET_NAME,
            "Prefix": "tattile/non-violation",
            "ExpectedBucketOwner": AWS_S3_EXPECTED_OWNER,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3_client.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.lower().endswith(".zip"):
                matched_files.append(key)

        if response.get("IsTruncated"):
            continuation_token = response["NextContinuationToken"]
        else:
            break

    json_response = {
        "status": "success",
        "count": len(matched_files),
        "files": matched_files,
    }

    return json_response


def user_information(request):
    token_data = TokenService.extract_claims_from_token(request)

    if isinstance(token_data, Response):
        return token_data

    user = get_object_or_404(User, id=token_data["user_id"])

    permission = (
        PermissionLevel.objects
        .filter(user=user)
        .select_related("station", "station__state")
        .first()
    )
    agency = Agency.objects.get(id=user.agency_id)
    station_id = getattr(agency, 'station_id', None)
    station = Station.objects.filter(id = station_id).first()
    # station = permission.station if permission else None

    state = station.state if station and station.state else None

    is_super_admin = permission.isSuperAdmin if permission else False

    data = {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "agencyId": user.agency.id if user.agency else None,
        "agencyName": None if is_super_admin else (user.agency.name if user.agency else None),

        "stationId": None if is_super_admin else (station.id if station else None),
        "stationName": None if is_super_admin else (station.name if station else None),

        "stateId": None if is_super_admin else (state.id if state else None),
        "stateName": None if is_super_admin else (state.name if state else None),

        # permissions
        "isAdjudicator": permission.isAdjudicator if permission else False,
        "isSupervisor": permission.isSupervisor if permission else False,
        "isAdmin": permission.isAdmin if permission else False,
        "isSuperAdmin": is_super_admin,
        "isCourt": permission.isCourt if permission else False,
        "isApprovedTableView": permission.isApprovedTableView if permission else False,
        "isRejectView": permission.isRejectView if permission else False,
        "isCSVView": permission.isCSVView if permission else False,
        "isAddUserView": permission.isAddUserView if permission else False,
        "isAddRoadLocationView": permission.isAddRoadLocationView if permission else False,
        "isEditFineView": permission.isEditFineView if permission else False,
        "isSubmissionView": permission.isSubmissionView if permission else False,
        "isCourtPreview": permission.isCourtPreview if permission else False,
        "isAddCourtDate": permission.isAddCourtDate if permission else False,
    }

    return data