from rest_framework import serializers
from accounts_v2.serializer import PagedResponseInput 
from video.models import SuperAdminFolders 

class CreateUserModel(serializers.Serializer):
    name = serializers.CharField(required=False,allow_blank=True)
    code = serializers.CharField(required=False,allow_blank=True)
    cityName = serializers.CharField(required=False,allow_blank=True)
    stateAB = serializers.CharField(required=False,allow_blank=True)
    location = serializers.CharField(required=False,allow_blank=True)
    deviceId = serializers.CharField(required=False,allow_blank=True)
    stateRS = serializers.CharField(required=False,allow_blank=True)
    apiKey = serializers.CharField(required=False,allow_blank=True)
    oRI = serializers.CharField(required=False,allow_blank=True)
    address = serializers.CharField(required=False,allow_blank=True)
    address2 = serializers.CharField(required=False,allow_blank=True)
    phone = serializers.CharField(required=False,allow_blank=True)
    payPortal = serializers.CharField(required=False,allow_blank=True)
    emails = serializers.CharField(required=False,allow_blank=True)
    courtComments = serializers.CharField(required=False,allow_blank=True)
    badgePicture = serializers.CharField(required=False,allow_blank=True)
    userName = serializers.CharField(required=False,allow_blank=True)
    email = serializers.CharField(required=False,allow_blank=True)
    password = serializers.CharField(required=False,allow_blank=True)
    isXpressPay = serializers.BooleanField(required=False,default=False)
    isQuickPd = serializers.BooleanField(required=False,default=True)
    trafficLogixClientId = serializers.IntegerField(required=False,allow_null=True)
    trafficLogixToken = serializers.CharField(required=False,allow_blank=True)
    isPreOdr = serializers.BooleanField(required=False,default=False,allow_null=True)
    firstMailerFinePercentage = serializers.IntegerField(required=False,allow_null=True)
    secondMailerFinePercentage = serializers.IntegerField(required=False,allow_null=True)
    firstMailDaysGap = serializers.IntegerField(required=False,allow_null=True)
    secondMailerDaysGap = serializers.IntegerField(required=False,allow_null=True)
    isZill = serializers.BooleanField(required=False,default=False)


class GetAllAgenciesDataResponseModel(serializers.Serializer):
    agencyId = serializers.IntegerField()
    agencyName = serializers.CharField(read_only=True,allow_blank=True)
    location = serializers.CharField(read_only=True,allow_blank=True)
    station = serializers.CharField(read_only=True,allow_blank=True)
    isActive = serializers.CharField(read_only=True)


class PagedResponse:
    def __init__(self, page_index, page_size, total_records, data):
        self.pageIndex = page_index
        self.pageSize = page_size
        self.totalRecords = total_records
        self.hasNextPage = (page_index * page_size) < total_records
        self.hasPreviousPage = page_index > 1
        self.data = data


class GetAgencyDetailsByIdResponseModel(serializers.Serializer):
    agencyId = serializers.IntegerField(read_only=True)
    agencyName = serializers.CharField(required=False,allow_blank=True)
    location = serializers.CharField(required=False,allow_blank=True)
    deviceId = serializers.CharField(required=False,allow_blank=True)
    stateRS = serializers.CharField(required=False,allow_blank=True)
    apiKey = serializers.CharField(required=False,allow_blank=True)
    oRI = serializers.CharField(required=False,allow_blank=True)
    address = serializers.CharField(required=False,allow_blank=True)
    address2 = serializers.CharField(required=False,allow_blank=True)
    phone = serializers.CharField(required=False,allow_blank=True)
    payPortal = serializers.CharField(required=False,allow_blank=True)
    emails = serializers.CharField(required=False,allow_blank=True)
    courtComments = serializers.CharField(required=False,allow_blank=True)
    userName = serializers.CharField(required=False,allow_blank=True)
    email = serializers.CharField(required=False,allow_blank=True)
    isXpressPay = serializers.BooleanField(required=False)
    isQuickPd = serializers.BooleanField(required=False)
    stateId = serializers.IntegerField(required=False,allow_null=True)
    stateName = serializers.CharField(required=False,allow_blank=True)
    stateAB = serializers.CharField(required=False,allow_blank=True)
    cityId = serializers.IntegerField(allow_null=True)
    cityName = serializers.CharField(required=False,allow_blank=True)
    isActive = serializers.BooleanField()
    stationId = serializers.IntegerField(allow_null=True)
    stationName = serializers.CharField(required=False,allow_blank=True)
    badgePicture = serializers.CharField(required=False,allow_blank=True)
    trafficLogixClientId = serializers.IntegerField(required=False,allow_null=True)
    trafficLogixToken = serializers.CharField(required=False,allow_blank=True),
    isPreOdr = serializers.BooleanField()
    firstMailerFinePercentage = serializers.IntegerField(required=False,allow_null=True)
    secondMailerFinePercentage = serializers.IntegerField(required=False,allow_null=True)
    firstMailDaysGap = serializers.IntegerField(required=False,allow_null=True)
    secondMailerDaysGap = serializers.IntegerField(required=False,allow_null=True)
    isZill = serializers.BooleanField(required=False,default=False)


class UpdateAgencyDetailsByIdInputModel(serializers.Serializer):
    agencyId = serializers.IntegerField(required=True,allow_null=False)
    agencyName = serializers.CharField(required=False,allow_blank=True)
    location = serializers.CharField(required=False,allow_blank=True)
    deviceId = serializers.CharField(required=False,allow_blank=True)
    stateRS = serializers.CharField(required=False,allow_blank=True)
    apiKey = serializers.CharField(required=False,allow_blank=True)
    oRI = serializers.CharField(required=False,allow_blank=True)
    address = serializers.CharField(required=False,allow_blank=True)
    address2 = serializers.CharField(required=False,allow_blank=True)
    phone = serializers.CharField(required=False,allow_blank=True)
    payPortal = serializers.CharField(required=False,allow_blank=True)
    emails = serializers.CharField(required=False,allow_blank=True)
    courtComments = serializers.CharField(required=False,allow_blank=True)
    isXpressPay = serializers.BooleanField(required=False)
    isQuickPd = serializers.BooleanField(required=False)
    stateAB = serializers.CharField(required=False,allow_blank=False)
    cityName = serializers.CharField(required=False,allow_blank=True)
    badgePicture = serializers.CharField(required=False,allow_blank=True)
    trafficLogixClientId = serializers.IntegerField(required=False,allow_null=True)
    trafficLogixToken = serializers.CharField(required=False,allow_blank=True)
    isPreOdr = serializers.BooleanField()
    firstMailerFinePercentage = serializers.IntegerField(required=False,allow_null=True)
    secondMailerFinePercentage = serializers.IntegerField(required=False,allow_null=True)
    firstMailDaysGap = serializers.IntegerField(required=False,allow_null=True)
    secondMailerDaysGap = serializers.IntegerField(required=False,allow_null=True)
    isZill = serializers.BooleanField(required=False,default=False)


class GetAllUserDetailsInputModel(PagedResponseInput,serializers.Serializer):
    agencyId = serializers.IntegerField(required=True,allow_null=False)


class GetAllUserDetailsResponseModel(serializers.Serializer):
    userId = serializers.IntegerField()
    userName = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    email = serializers.CharField()
    agencyId = serializers.IntegerField()
    agencyName = serializers.CharField()


class GetUserDetailsByIdResponseModel(serializers.Serializer):
    userId = serializers.IntegerField()
    userName = serializers.CharField()
    password=serializers.CharField()
    email = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    agencyName = serializers.CharField()
    isActive = serializers.BooleanField()
    isSubmissionView = serializers.BooleanField()
    isAdjudicator = serializers.BooleanField()
    isCourt = serializers.BooleanField()
    isAdmin = serializers.BooleanField()
    isSuperAdmin = serializers.BooleanField()
    isApprovedTableView = serializers.BooleanField()
    isRejectView = serializers.BooleanField()
    isCSVView = serializers.BooleanField()
    isAddUserView = serializers.BooleanField()
    isAddRoadLocationView = serializers.BooleanField()
    isEditFineView = serializers.BooleanField()
    isCourtPreview = serializers.BooleanField()
    isAddCourtDate = serializers.BooleanField()
    isActive = serializers.BooleanField()
    isSupervisor = serializers.BooleanField()
    isAgencyAdjudicationBinView = serializers.BooleanField()
    isReviewBinView = serializers.BooleanField()
    isPreODRView = serializers.BooleanField()
    isODRView = serializers.BooleanField()
    isViewReportView = serializers.BooleanField()


class UpdateUserDetailsByIdInputModel(serializers.Serializer):
    userId = serializers.IntegerField()
    agencyId = serializers.IntegerField()
    userName = serializers.CharField(required=False,allow_blank=True)
    password=serializers.CharField(required=False,allow_blank=True)
    email = serializers.CharField(required=False,allow_blank=True)
    firstName = serializers.CharField(required=False,allow_blank=True)
    lastName = serializers.CharField(required=False,allow_blank=True)
    isActive = serializers.BooleanField()
    isSubmissionView = serializers.BooleanField(default=False)
    isAdjudicator = serializers.BooleanField()
    isCourt = serializers.BooleanField()
    isAdmin = serializers.BooleanField()
    isSuperAdmin = serializers.BooleanField(default=False)
    isApprovedTableView = serializers.BooleanField(default=False)
    isRejectView = serializers.BooleanField(default=False)
    isCSVView = serializers.BooleanField(default=False)
    isAddUserView = serializers.BooleanField(default=False)
    isAddRoadLocationView = serializers.BooleanField(default=False)
    isEditFineView = serializers.BooleanField(default=False)
    isCourtPreview = serializers.BooleanField(default=False)
    isAddCourtDate = serializers.BooleanField(default=False)
    isSupervisor = serializers.BooleanField(default=False)
    isAgencyAdjudicationBinView = serializers.BooleanField(default=False)
    isReviewBinView = serializers.BooleanField(default=False)
    isPreODRView = serializers.BooleanField(default=False)
    isODRView = serializers.BooleanField(default=False)
    isViewReportView = serializers.BooleanField(default=False)


class SuperAdminFolderSerializer(serializers.ModelSerializer):
    folderName = serializers.CharField(source="folder_name")
    agencyId = serializers.IntegerField(source="agency_id")
    userId = serializers.IntegerField(source="user_id")
    parentFolderId = serializers.IntegerField(
        source="parent_folder_id", required=False, allow_null=True
    )

    class Meta:
        model = SuperAdminFolders
        fields = ["folderName", "agencyId", "userId", "parentFolderId"]

class GetFolderHierarchyInputModel(serializers.Serializer):
    parent_id = serializers.IntegerField(
        required=False,
        help_text="ID of the parent folder. If not provided, returns top-level folders.",
    )


# Recursive Folder serializer
class FolderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    childFolders = serializers.ListField(
        child=serializers.DictField(), help_text="List of subfolders"
    )
    files = serializers.ListField(
        child=serializers.CharField(), help_text="List of file names in this folder"
    )


# Response model (wraps folder hierarchy)
class GetFolderHierarchyResponseModel(FolderSerializer):
    pass