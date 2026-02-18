from video.models import Agency, City, State, User, dmv, AgencyFileDetails, SuperAdminFolders
from rest_framework.permissions import IsAuthenticated,AllowAny
from .serializers import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information, get_presigned_url_PDF
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from rest_framework.views import APIView
from accounts_v2.serializer import PagedResponseInput
from .super_admin_utils import *
from drf_yasg import openapi
import base64
import io
import os


class AddCustomerView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=CreateUserModel,
        tags=['SuperAdmin']
    )
    def post(self, request):
        serializer = CreateUserModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data": serializer.errors}).data,status=200)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        extracted_input_fields = extracted_fields_for_add_customer(serializer.validated_data)

        try:
            print(extracted_input_fields['stateAB'])
            state = State.objects.get(ab=extracted_input_fields['stateAB'])
            print(state)
        except State.DoesNotExist:
            return Response(APIResponse({"statusCode":404, "message":"Invalid state abbreviation."}).data, status=200)


        if User.objects.filter(username=extracted_input_fields['userName']).exists():
            return Response(APIResponse({"statusCode":409, "message":"Username is already taken."}).data, status=200)
        if Agency.objects.filter(name=extracted_input_fields['name']).exists():
            return Response(APIResponse({"statusCode":409, "message":"Agency name is already taken."}).data, status=200)
        if Station.objects.filter(name=extracted_input_fields['name']).exists():
            return Response(APIResponse({"statusCode":409, "message":"Agency code is already taken."}).data, status=200)
        badge_url = ""
        if extracted_input_fields['badgePicture']:
            file_data = base64.b64decode(extracted_input_fields['badgePicture'])
            file_obj = io.BytesIO(file_data)
            badge_url = upload_to_s3(file_obj, f"{extracted_input_fields['code']}-badge.png", "images")
        
        city, _ = City.objects.get_or_create(name=extracted_input_fields['cityName'], state=state)
        station = Station.objects.create(name=extracted_input_fields['code'], state=state, city=city)
        new_dmv = dmv.objects.create(plate='', state_ab=state, station=station)

        AddCustomerDetails(extracted_input_fields,badge_url,station)
        return Response(APIResponse({"statusCode":201, "message":"User Created Successfully"}).data ,status=200)
    

class GetAllAgencyDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=PagedResponseInput,
        responses={200: GetAllAgenciesDataResponseModel(many=True)},
        tags=['SuperAdmin'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = PagedResponseInput(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data": serializer.errors}).data, status=200)
        read_token = user_information(request)
        if isinstance(read_token, Response):
            return read_token
        serializer_data = serializer.validated_data
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)
        query_result = get_all_agency_data(search_string, page_index, page_size)
        agencies = query_result['data']
        total_records = query_result['total_records']
        if not agencies:
            return Response(ServiceResponse({"statusCode": 204,"message": "No content","data": []}).data, status=200)
        serialized_data = GetAllAgenciesDataResponseModel(agencies, many=True).data
        paged_response = {
            "data": serialized_data,
            "pageIndex": page_index,
            "pageSize": page_size,
            "totalRecords": total_records,
            "hasNextPage": page_index * page_size < total_records,
            "hasPreviousPage": page_index > 1,
            "statusCode": 200,
            "message": "Success"
        }
        return Response(paged_response)
 

class GetAgencyDetailsByIdView(APIView):
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'agencyId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={200:GetAgencyDetailsByIdResponseModel},
        tags=['SuperAdmin'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        agency_id = request.query_params.get('agencyId', None)

        try:
            agency_id = int(agency_id) if agency_id is not None else 1
        except ValueError:
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid agency id."}).data, status=200)
        
        agency_data = Agency.objects.filter(id=agency_id).first()
        if not agency_data:
            return Response(ServiceResponse({"statusCode":204,"message":f"Agency with this id {agency_id} does not exists","data":None}).data, status=200)

        return Response(ServiceResponse({"statusCode":200,"message":"Success","data":GetAgencyDetailsByIdResponseModel(get_agency_data_by_id(agency_id)).data}).data, status=200)
    

class UpdateAgencyDetailsByIdView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=UpdateAgencyDetailsByIdInputModel,
        tags=['SuperAdmin'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        serializer = UpdateAgencyDetailsByIdInputModel(data=request.data)
        if not serializer.is_valid():       
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data" : serializer.errors}).data, status=200)

        serializer_data = serializer.validated_data
        extracted_input_fields = extract_fields_to_update_agency_details(serializer.validated_data)
        try:
            state = State.objects.get(ab=extracted_input_fields['stateAB'])
        except State.DoesNotExist:
            return Response(APIResponse({"statusCode":404, "message":"Invalid state abbreviation."}).data, status=200)

        agency_data = Agency.objects.filter(id=extracted_input_fields['agencyId']).first()
        if not agency_data:
            return Response(APIResponse({"statusCode":204,"message":f"Agency with this id {extracted_input_fields['agencyId']} does not exists"}).data, status=200)

        city, _ = City.objects.get_or_create(name=extracted_input_fields['cityName'], state=state)
        update_agency_details(extracted_input_fields)
        return Response(APIResponse({"statusCode":200,"message":"Agency details has been updated successfully"}).data, status=200)


class GetAllUserDetailsView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=GetAllUserDetailsInputModel,
        responses={200:GetAllUserDetailsResponseModel(many=True)},
        tags=['SuperAdmin'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        serializer = GetAllUserDetailsInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data": serializer.errors}).data, status=200)
        serializer_data = serializer.validated_data
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)
        agency_id = serializer_data.get('agencyId')
        agency_data = Agency.objects.filter(id=agency_id).values("id").first()
        if not agency_data:
            return Response(ServiceResponse({"statusCode":204,"message":f"Agency with this id {agency_id} does not exists","data":[]}).data, status=200)
        
        query_result = get_all_user_details(agency_data["id"],search_string, page_index, page_size)
        user_data = query_result['data']
        total_records = query_result['total_records']

        if not user_data:
            return Response(ServiceResponse({"statusCode": 204,"message": "No content","data": []}).data, status=200)
        
        serialized_data = GetAllUserDetailsResponseModel(user_data, many=True).data
        paged_response = {
            "data": serialized_data,
            "pageIndex": page_index,
            "pageSize": page_size,
            "totalRecords": total_records,
            "hasNextPage": page_index * page_size < total_records,
            "hasPreviousPage": page_index > 1,
            "statusCode": 200,
            "message": "Success"
        }
        return Response(paged_response)
    

class GetUserDetailsByIdView(APIView):
    permission_classes=[IsAuthenticated]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'userId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'agencyId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={200:GetUserDetailsByIdResponseModel},
        tags=['SuperAdmin'],
        security=[{'Bearer': []}]
    )
    def get(self,request):
        user_id = request.query_params.get('userId', None)
        agency_id = request.query_params.get('agencyId', None)

        try:
            user_id = int(user_id) if user_id is not None else 1
            agency_id = int(agency_id) if agency_id is not None else 1
        except ValueError:
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid user or agency id."}).data, status=200)
        
        user_data = User.objects.filter(id=user_id,agency_id=agency_id).first()
        if not user_data:
            return Response(ServiceResponse({"statusCode":204,"message":"Invalid user or agency id","data":[]}).data,status=200)
        
        return Response(ServiceResponse({"statusCode":200,"message":"Success","data":GetUserDetailsByIdResponseModel(get_user_details_by_id(user_id,agency_id)).data}).data, status=200)
        

class UpdateUserDetailsByIdView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=UpdateUserDetailsByIdInputModel,
        tags=['SuperAdmin'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        serializer = UpdateUserDetailsByIdInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data" : serializer.errors}).data, status=200)

        serializer_data = serializer.validated_data
        extracted_input_fields = extract_fields_to_update_user_details(serializer_data)

        update_user_details(extracted_input_fields)
        return Response(APIResponse({"statusCode":200,"message":"User details has been updated successfully"}).data, status=200)
    

class UpdateAgencyStatusView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
            manual_parameters=[
            openapi.Parameter(
                'isActive',
                openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'agencyId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        tags=['SuperAdmin'],
        security=[{'Bearer': []}]
    )
    def get(self,request):
        read_token = user_information(request)
        if isinstance(read_token, Response):
            return read_token
        isActive = request.query_params.get('isActive', None)
        agencyId = request.query_params.get('agencyId', None)
        try:
            agencyId = int(agencyId)
        except (TypeError, ValueError):
            return Response(APIResponse({"statusCode": 400,"message": "Invalid agency ID"}).data, status=200)
        if isActive is not None:
            isActive = isActive.lower() in ['true', '1']
        else:
            return Response(APIResponse({"statusCode": 400,"message": "Missing isActive parameter"}).data, status=200)
        
        isSuperAdmin = read_token.get('isSuperAdmin')
        if not isSuperAdmin:
            return Response(APIResponse({"statusCode":400,"message":"You don't have the required permission to perform this action"}).data, status=200)


        agencyData = Agency.objects.filter(id=agencyId).first()
        
        if not agencyData:
            return Response(APIResponse({"statusCode":400,"message":"Invalid agency id"}).data, status=200)
        
        agencyData.is_active = isActive
        agencyData.save()
        User.objects.filter(agency_id=agencyId).update(is_active=isActive)
        
        return Response(APIResponse({"statusCode":200,"message":f"Agency status updated to {'Active' if isActive else 'InActive'} successfully"}).data, status=200)

class CreateFolder(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["folderName", "agencyId", "userId"],
            properties={
                "folderName": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Folder name",
                    example="AgencyDocs",
                ),
                "agencyId": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Agency ID"
                ),
                "userId": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="User ID"
                ),
                "parentFolderId": openapi.Schema(
                    type=openapi.TYPE_INTEGER, description="Parent Folder ID", example=1
                ),
            },
        ),
        responses={201: "Folder created successfully", 400: "Bad Request"},
        tags=["SuperAdmin"],
        operation_description="Create a folder only if user is Super Admin",
        security=[{"Bearer": []}],
    )
    def post(self, request):
        serializer = SuperAdminFolderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                APIResponse(
                    {
                        "statusCode": 400,
                        "message": "Validation failed",
                        "data": serializer.errors,
                    }
                ).data,
                status=400,
            )

        validated_data = serializer.validated_data
        user_id = validated_data["user_id"]
        folder_name = validated_data["folder_name"]
        agency_id = validated_data["agency_id"]
        parent_folder_id = validated_data.get("parent_folder_id")
        print(user_id, folder_name, agency_id, parent_folder_id)
        # 1. Check Super Admin permission
        perm = PermissionLevel.objects.filter(user_id=user_id).first()
        if not perm or not perm.isSuperAdmin:
            return Response(
                APIResponse(
                    {
                        "statusCode": 403,
                        "message": "Only Super Admins can create a folder",
                    }
                ).data,
                status=403,
            )

        # 2. Check for duplicate folder name for the given agency
        if SuperAdminFolders.objects.filter(
            folder_name__iexact=folder_name, agency_id=agency_id
        ).exists():
            return Response(
                APIResponse(
                    {
                        "statusCode": 400,
                        "message": f"Folder '{folder_name}' already exists for the selected agency.",
                    }
                ).data,
            )
        # 3 Check if parent folder exists
        if parent_folder_id:
            try:
                parent_folder = SuperAdminFolders.objects.get(
                    id=parent_folder_id, agency_id=agency_id
                )
            except SuperAdminFolders.DoesNotExist:
                return Response(
                    APIResponse(
                        {
                            "statusCode": 404,
                            "message": "Parent folder not found for the given agency.",
                        }
                    ).data,
                    status=404,
                )

        # 4. Save manually
        try:
            new_folder = SuperAdminFolders.objects.create(
                folder_name=folder_name,
                agency_id=agency_id,
                created_by_id=user_id,
                parent_folder_id=parent_folder_id if parent_folder_id else None,
            )
            response_data = {
                "id": new_folder.id,
                "folderName": new_folder.folder_name,
                "agencyId": new_folder.agency_id,
                "createdBy": new_folder.created_by_id,
                "parentFolderId": new_folder.parent_folder_id,
                "statusCode": 201,
                "message": "Folder created successfully",
            }
            return Response(response_data)

        except Exception as e:
            return Response(
                APIResponse(
                    {
                        "statusCode": 500,
                        "message": f"Error creating folder: {str(e)}",
                    }
                ).data,
                status=500,
            )




class UploadFiles(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "folderId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True
            ),
            openapi.Parameter(
                "userId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True
            ),
            openapi.Parameter(
                "agencyId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["folderId", "userId", "agencyId", "files"],
            properties={
                "files": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_FILE),
                    description="Upload multiple files",
                )
            },
        ),
        responses={200: "Files uploaded successfully", 400: "Bad Request"},
        tags=["SuperAdmin"],
        operation_description="Upload files (images, videos, or documents) to a specific folder",
        security=[{"Bearer": []}],
    )
    def post(self, request):
        folder_id = request.query_params.get("folderId")
        user_id = request.query_params.get("userId")
        agency_id = request.query_params.get("agencyId")
        files = request.FILES.getlist("files")

        if not folder_id or not user_id or not agency_id or not files:
            return Response(
                APIResponse(
                    {
                        "statusCode": 400,
                        "message": "folder_id, user_id,agency_id and files are required",
                    }
                ).data,
                status=400,
            )

        # Check if folder exists
        try:
            folder = SuperAdminFolders.objects.get(id=folder_id)
        except SuperAdminFolders.DoesNotExist:
            return Response(
                APIResponse({"statusCode": 404, "message": "Folder not found"}).data,
                status=404,
            )

        # Fetch  permission level data based on user_id
        try:
            permission = PermissionLevel.objects.get(user_id=user_id)
        except PermissionLevel.DoesNotExist:
            return Response(
                APIResponse(
                    {
                        "statusCode": 404,
                        "message": "user_id not found in permission_level",
                    }
                ).data,
                status=404,
            )

        # Block if not admin or superadmin
        if not (permission.isSuperAdmin or permission.isAdmin):
            return Response(
                APIResponse(
                    {
                        "statusCode": 403,
                        "message": "User is neither superadmin nor admin to upload files",
                    }
                ).data,
                status=403,
            )

        # Upload each file and create a FileDetails record
        uploaded_file_paths = []
        failed_files = []
        duplicate_files = []
        for file in files:
            # Check duplicate
            if AgencyFileDetails.objects.filter(
                file_name=file.name, folder_id=folder_id, agency_id=agency_id
            ).exists():
                duplicate_files.append(file.name)
                continue

            print(
                f"Uploading file: agency_files/{folder.agency_id}/{file.name} to folder: {folder.folder_name}"
            )

            file_path = upload_to_s3(
                file, f"agency_files/{folder.agency_id}/{file.name}", folder.folder_name
            )
            file_type = os.path.splitext(file.name)[1].lstrip(".")
            file_size = file.size

            print("File type:", file_type)
            print("File size:", file_size, "bytes")
            print("File path after upload:", file_path)

            if not file_path:
                failed_files.append(file.name)
                continue  # this one is okay here — skips saving for failed uploads
            try:
                #  Save file record in DB
                AgencyFileDetails.objects.create(
                    file_name=file.name,
                    file_path=file_path,
                    folder=folder,
                    agency=folder.agency,
                    uploaded_by=folder.created_by,
                    file_type=file_type,
                    file_size=file_size,
                )
                uploaded_file_paths.append(file_path)
            except Exception as e:
                failed_files.append(file.name)
                print(f"Error uploading {file.name}: {str(e)}")

        print("uploaded_file_paths:", uploaded_file_paths)
        print("failed_files:", failed_files)
        print("duplicate_files:", duplicate_files)
        response_data = {
            "uploadedFilePaths": uploaded_file_paths,
            "failedFiles": failed_files,
            "duplicateFiles": duplicate_files,
            "statusCode": 200,
            "message": "Files uploaded successfully",
        }
        return Response(response_data)

class GetFolderHierarchy(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "parentId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False
            ),
            openapi.Parameter(
                "agencyId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True
            ),
        ],
        responses={200: GetFolderHierarchyResponseModel(many=True)},
        tags=["SuperAdmin"],
        security=[{"Bearer": []}],
    )
    def get(self, request):
        parent_id = request.query_params.get("parentId", None)
        agency_id = request.query_params.get(
            "agencyId",
        )

        if not agency_id:
            return Response(
                APIResponse(
                    {"statusCode": 400, "message": "agency_id is required"}
                ).data,
                status=400,
            )

        if parent_id:
            try:
                root_folder = SuperAdminFolders.objects.get(
                    id=parent_id, agency_id=agency_id, is_deleted=False
                )
            except SuperAdminFolders.DoesNotExist:
                return Response(
                    APIResponse(
                        {"statusCode": 404, "message": "Folder not found"}
                    ).data,
                    status=404,
                )
            data = self.get_folder_structure(root_folder, agency_id)
        else:
            top_level_folders = SuperAdminFolders.objects.filter(
                parent_folder_id__isnull=True, agency_id=agency_id, is_deleted=False
            )
            data = [
                self.get_folder_structure(folder, agency_id)
                for folder in top_level_folders
            ]
        print(f"Fetched folder hierarchy for agency_id {agency_id}: {data}")
        if not data:
            return Response(
                APIResponse(
                    {"statusCode": 204, "message": "No content", "data": []}
                ).data,
                status=200,
            )
        response_data = {
            "statusCode": 200,
            "message": "Folder hierarchy fetched successfully",
            "data": data,
        }
        return Response(
            response_data,
        )

    def get_folder_structure(self, folder, agency_id):
        """Recursive function to get folder + files for a specific agency."""
        subfolders = SuperAdminFolders.objects.filter(
            parent_folder_id=folder.id, agency_id=agency_id, is_deleted=False
        )
        files = AgencyFileDetails.objects.filter(
            folder=folder, agency_id=agency_id, is_deleted=False
        ).values(
            "id",
            "file_path",
            "file_name",
            "file_type",
            "file_size",
            "uploaded_at",
        )
        # Convert QuerySet to list of dicts and update file_path with presigned URL
        files_list = []
        for file in files:
            file_dict = dict(file) 
            if file_dict["file_type"] == 'pdf':
                file_dict["file_path"] = get_presigned_url_PDF(file_dict["file_path"],download=False)
            else:
                file_dict["file_path"] = get_presigned_url(file_dict["file_path"])
            files_list.append(file_dict)
        return {
            "id": folder.id,
            "name": folder.folder_name,
            "childFolders": [
                self.get_folder_structure(subfolder, agency_id)
                for subfolder in subfolders
            ],
            "files": files_list,
        }


class DeleteFolder(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["agencyId", "folderIds", "userId"],
            properties={
                "agencyId": openapi.Schema(type=openapi.TYPE_INTEGER),
                "userId": openapi.Schema(type=openapi.TYPE_INTEGER),
                "folderIds": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                ),
            },
        ),
        tags=["SuperAdmin"],
        security=[{"Bearer": []}],
    )
    def delete(self, request):
        agency_id = request.data.get("agencyId")
        folder_ids = request.data.get("folderIds")
        user_id = request.data.get("userId")
        print(
            f"Deleting folders: {folder_ids} for agency_id: {agency_id} by user_id: {user_id}"
        )
        #  Check required params
        if not agency_id or not folder_ids or not user_id:
            return Response(
                APIResponse(
                    {
                        "statusCode": 400,
                        "message": "agency_id, folder_ids, and user_id are required",
                    }
                ).data,
                status=400,
            )

        #  Check permission level
        try:
            permission = PermissionLevel.objects.get(user_id=user_id)
        except PermissionLevel.DoesNotExist:
            return Response(
                APIResponse(
                    {"statusCode": 403, "message": "User does not have permission"}
                ).data,
                status=403,
            )

        if not permission.isSuperAdmin:
            return Response(
                APIResponse(
                    {
                        "statusCode": 403,
                        "message": "Only SuperAdmins can delete folders",
                    }
                ).data,
                status=403,
            )

        deleted_folders = []
        not_found = []

        #  Loop through folder_ids
        for folder_id in folder_ids:
            try:
                folder_obj = SuperAdminFolders.objects.get(
                    id=folder_id, agency_id=agency_id
                )
                self.delete_folder_and_contents(folder_obj, agency_id)
                deleted_folders.append(folder_id)
            except SuperAdminFolders.DoesNotExist:
                not_found.append(folder_id)
        print(f"Deleted folders: {deleted_folders}, Not found: {not_found}")
        response_data = {
            "statusCode": 200,
            "message": "Folder deletion completed",
            "deletedFolders": deleted_folders,
            "foldersNotFound": not_found,
        }
        return Response(response_data)

    def delete_folder_and_contents(self, folder, agency_id):
        """Recursively delete folder, its subfolders, and files."""

        # Fetch files first
        files_qs = AgencyFileDetails.objects.filter(folder=folder, agency_id=agency_id)

        # Delete from S3
        # for file_obj in files_qs:
        #     if file_obj.file_path:
        #         key = file_obj.file_path.split(".amazonaws.com/")[1]
        #         print(key)
        #         delete_from_s3(key)

        # Now delete from DB
        files_qs.update(is_deleted=True)

        # Find subfolders and delete them recursively
        subfolders = SuperAdminFolders.objects.filter(
            parent_folder_id=folder.id, agency_id=agency_id
        )
        for subfolder in subfolders:
            self.delete_folder_and_contents(subfolder, agency_id)

        # Delete the folder itself
        folder.is_deleted = True
        folder.save()

class GetFileData(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "fileId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True
            ),
            openapi.Parameter(
                "folderId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=False
            ),
            openapi.Parameter(
                "agencyId", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, required=True
            ),
        ],
        responses={200: "File binary data from S3"},
        tags=["SuperAdmin"],
        security=[{"Bearer": []}],
    )
    def get(self, request):
        file_id = request.query_params.get("fileId")
        folder_id = request.query_params.get("folderId")
        agency_id = request.query_params.get("agencyId")

        if not file_id or not agency_id:
            return Response(
                APIResponse(
                    {
                        "statusCode": 400,
                        "message": "file_id and agency_id are required",
                    }
                ).data,
                status=400,
            )
        # Fetch file_path from DB
        try:
            file_record = AgencyFileDetails.objects.get(
                id=file_id,
                agency_id=agency_id,
                **({"folder_id": folder_id} if folder_id else {}),
            )
        except AgencyFileDetails.DoesNotExist:
            return Response({"error": "File not found"}, status=404)

        file_path = file_record.file_path
        if not file_path:
            return Response(
                APIResponse({"statusCode": 404, "message": "File path not found"}).data,
                status=404,
            )
        presigned_url = get_presigned_url(file_path)
        print("presigned_url:", presigned_url)
        response_data = {
            "statusCode": 200,
            "message": "File fetched successfully",
            "filePath": presigned_url,
        }
        return Response(response_data)


class DeleteFiles(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["agencyId", "folderId", "fileIds", "userId"],
            properties={
                "agencyId": openapi.Schema(type=openapi.TYPE_INTEGER),
                "folderId": openapi.Schema(type=openapi.TYPE_INTEGER),
                "fileIds": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_INTEGER),
                ),
                "userId": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        tags=["SuperAdmin"],
        security=[{"Bearer": []}],
    )
    def delete(self, request):
        try:
            agency_id = request.data.get("agencyId")
            folder_id = request.data.get("folderId")
            file_ids = request.data.get("fileIds")
            user_id = request.data.get("userId")
            print(
                f"Deleting files: {file_ids} for agency_id: {agency_id}, folder_id: {folder_id} by user_id: {user_id}"
            )
            # Validate required fields
            if not file_ids or not agency_id:
                return Response(
                    APIResponse(
                        {
                            "statusCode": 400,
                            "message": "file_ids and agency_id are required",
                            "data": None,
                        }
                    ).data,
                    status=400,
                )

            # Check permissions from permission table
            user_permission = PermissionLevel.objects.filter(user_id=user_id).first()

            if not user_permission:
                return Response(
                    APIResponse(
                        {
                            "statusCode": 403,
                            "message": "Permission not found for this user in the agency",
                            "data": None,
                        }
                    ).data,
                    status=403,
                )

            files = AgencyFileDetails.objects.filter(
                id__in=file_ids, agency_id=agency_id, folder_id=folder_id
            )

            blocked_files = []

            for f in files:
                if f.uploaded_by == user_id:
                    # Admin or uploader can delete their own files
                    continue
                elif user_permission.isAdmin:
                    # Admin can delete other Admin's files, but not SuperAdmin's
                    uploader_perm = PermissionLevel.objects.filter(
                        user_id=f.uploaded_by, agency_id=agency_id
                    ).first()
                    if uploader_perm and uploader_perm.isSuperAdmin:
                        blocked_files.append(f.id)  # Can't delete SuperAdmin files
                    else:
                        continue  # Allow deleting other Admin  files

            if blocked_files:
                return Response(
                    APIResponse(
                        {
                            "statusCode": 403,
                            "message": f"Cannot delete files uploaded by Super Admin: {blocked_files}",
                            "data": None,
                        }
                    ).data,
                    status=403,
                )

            files_to_delete = files.exclude(id__in=blocked_files)
            if not files_to_delete:
                return Response(
                    APIResponse(
                        {
                            "statusCode": 404,
                            "message": "No files found to delete",
                            "data": None,
                        }
                    ).data,
                    status=404,
                )
            print(f"Files to delete: {files_to_delete}")
            # Delete from S3
            # for file_obj in files_to_delete:
            #     if file_obj.file_path:
            #         key = file_obj.file_path.split(".amazonaws.com/")[1]
            #         print(key)
            #         delete_from_s3(key)
            # Delete from DB
            files_to_delete.update(is_deleted=True)

            response_data = {
                "statusCode": 200,
                "message": "Files deleted successfully",
                "blockedFiles": blocked_files,
            }
            return Response(
                response_data,
            )

        except Exception as e:
            return Response(
                APIResponse(
                    {
                        "statusCode": 500,
                        "message": f"An error occurred: {str(e)}",
                        "data": None,
                    }
                ).data,
                status=500,
            )