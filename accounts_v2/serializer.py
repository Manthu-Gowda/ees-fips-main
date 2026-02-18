from rest_framework import serializers

class APIResponse(serializers.Serializer):
    statusCode = serializers.IntegerField()
    message = serializers.CharField()


class ServiceResponse(APIResponse):
    data = serializers.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        data_serializer = kwargs.pop('data_serializer', None)
        super().__init__(*args, **kwargs)

        if data_serializer:
            self.fields['data'] = data_serializer()
        else:
            self.fields['data'] = serializers.JSONField(required=False)

class PagedResponseInput(serializers.Serializer):
    pageIndex = serializers.IntegerField(default=1)
    pageSize = serializers.IntegerField(default=10)
    searchString = serializers.CharField(default="", allow_blank=True)

    # def validate_searchString(self, value):
    #     return value.lower().replace(" ", "")



class PagedResponseOutput(serializers.Serializer):
    totalCount = serializers.IntegerField()
    data = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        data_serializer = kwargs.pop('data_serializer', None)
        super().__init__(*args, **kwargs)

        if data_serializer:
            self.fields['data'] = data_serializer(many=True)
        else:
            self.fields['data'] = serializers.ListField()

    def get_data(self, obj):
        return obj.get("data", [])
    


class PagedResponse(serializers.Serializer):
    pageIndex = serializers.IntegerField(default=1)
    pageSize = serializers.IntegerField(default=10)
    searchString = serializers.CharField(default="", allow_blank=True)
    hasNextPage = serializers.BooleanField()
    hasPreviousPage = serializers.BooleanField()
    totalRecords = serializers.IntegerField()
    statusCode = serializers.IntegerField()
    message = serializers.CharField()
    count = serializers.IntegerField()

    data = serializers.ListField()

    def __init__(self, *args, **kwargs):
        data_serializer = kwargs.pop('data_serializer', None)
        super().__init__(*args, **kwargs)

        if data_serializer:
            self.fields['data'] = data_serializer(many=True)
        else:
            self.fields['data'] = serializers.ListField()

    def get_data(self, obj):
        return obj.get("data", [])



class UserLoginRequestModel(serializers.Serializer):
    userName = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    loginType = serializers.IntegerField(required=True)


class AccessTokenResponseModel(serializers.Serializer):
    accessToken = serializers.CharField()
    refereshToken = serializers.CharField()
    expiryTime = serializers.IntegerField()


class UserPermissionLevelResponseModel(serializers.Serializer):
    isAdjudicator = serializers.BooleanField()
    isSupervisor = serializers.BooleanField()
    isCourt = serializers.BooleanField()
    isApprovedTableView = serializers.BooleanField()
    isRejectView = serializers.BooleanField()
    isCSVView = serializers.BooleanField()
    isAddUserView = serializers.BooleanField()
    isAddRoadLocationView = serializers.BooleanField()
    isEditFineView = serializers.BooleanField()
    isSubmissionView = serializers.BooleanField()
    isCourtPreview = serializers.BooleanField()
    isAddCourtDate = serializers.BooleanField()
    isAdmin = serializers.BooleanField()
    isODRView = serializers.BooleanField()
    isPreODRView = serializers.BooleanField()
    isViewReportView = serializers.BooleanField()
    isAgencyAdjudicationBinView = serializers.BooleanField()
    isReviewBinView = serializers.BooleanField()
    isReminderView = serializers.BooleanField()
    isTotalTicket = serializers.BooleanField()
    isDailyReport = serializers.BooleanField()


class LoginResponseModel(serializers.Serializer):
    userId = serializers.IntegerField()
    userName = serializers.CharField()
    station = serializers.CharField()
    agencyId = serializers.IntegerField()
    agencyName = serializers.CharField()
    isTrafficLogix = serializers.BooleanField()
    isVideoFlow = serializers.BooleanField()
    isTattileFlow = serializers.BooleanField()
    badgeUrl = serializers.CharField()
    accessTokenResponseModel = AccessTokenResponseModel()
    userPermissionLevelResponseModel = UserPermissionLevelResponseModel()


class UserRegisterInputModel(serializers.Serializer):
    firstName = serializers.CharField(required=False,allow_blank=True)
    lastName = serializers.CharField(required=False,allow_blank=True)
    userName = serializers.CharField(required=False,allow_blank=True)
    email = serializers.CharField(required=False,allow_blank=True)
    password = serializers.CharField(required=False,allow_blank=True)
    isAdjudicator = serializers.BooleanField(default=False)
    isSupervisor = serializers.BooleanField(default=False)
    isCourt = serializers.BooleanField(default=False)
    isApprovedTableView = serializers.BooleanField(default=False)
    isRejectView = serializers.BooleanField(default=False)
    isCSVView = serializers.BooleanField(default=False)
    isAddUserView = serializers.BooleanField(default=False)
    isAddRoadLocationView = serializers.BooleanField(default=False)
    isEditFineView = serializers.BooleanField(default=False)
    isSubmissionView = serializers.BooleanField(default=False)
    isCourtPreview = serializers.BooleanField(default=False)
    isAddCourtDate = serializers.BooleanField(default=False)
    isAgencyAdjudicationBinView = serializers.BooleanField(default=False)
    isReviewBinView = serializers.BooleanField(default=False)
    isPreODRView = serializers.BooleanField(default=False)
    isODRView = serializers.BooleanField(default=False)
    isViewReportView = serializers.BooleanField(default=False)
    isReminderView = serializers.BooleanField()
    # isTotalTicket = serializers.BooleanField()
    # isDailyReport = serializers.BooleanField()

