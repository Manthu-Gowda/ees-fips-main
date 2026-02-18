from rest_framework import serializers

from accounts_v2.serializer import PagedResponseInput


class StateDropDownModel(serializers.Serializer):
    id = serializers.IntegerField()
    stateName = serializers.CharField(source='name')
    stateAB = serializers.CharField(source='ab')


class GetSubmissionDateDropDownModel(serializers.Serializer):
    date = serializers.CharField()
    isSent = serializers.BooleanField()


class GetRejectReasonsDropDownModel(serializers.Serializer):
    id = serializers.IntegerField()
    description = serializers.CharField()
    rejectionType = serializers.CharField(source="rejection_type")


class GetMediaDropDownInputModel(serializers.Serializer):
    date = serializers.CharField(allow_blank=True, required=False)
    type = serializers.IntegerField()


class GetAllVideoDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isSkipped = serializers.BooleanField()
    isRejected = serializers.BooleanField()
    isSubmitted = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isUnknown = serializers.BooleanField(default=False)
    isSentBackSubbin = serializers.BooleanField(default=False) 


class GetAllImageDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isSkipped = serializers.BooleanField()
    isRejected = serializers.BooleanField()
    isSubmitted = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isUnknown = serializers.BooleanField(default=False)
    isSentBackSubbin = serializers.BooleanField(default=False) 


class GetAllTattileDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isSkipped = serializers.BooleanField()
    isRejected = serializers.BooleanField()
    isSubmitted = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isUnknown = serializers.BooleanField(default=False)
    isSentBackSubbin = serializers.BooleanField(default=False) 


class GetAllAdjudicationDatesDropDown(serializers.Serializer):
    date = serializers.CharField()


class GetAdjudicationDatesInputModel(serializers.Serializer):
    mediaType = serializers.IntegerField(required=True)
    dateType = serializers.IntegerField(required=True)


class GetAllCitationIdsOutputModel(serializers.Serializer):
    citationId = serializers.IntegerField(read_only=True)
    citationID = serializers.CharField(read_only=True)
    isApproved = serializers.BooleanField(read_only=True)
    isRejected = serializers.BooleanField(read_only=True)
    isSendBack = serializers.BooleanField(read_only=True)


class GetAllCitationIdsInputModel(serializers.Serializer):
    mediaType = serializers.IntegerField(required=True)
    date = serializers.CharField(required=False,allow_blank=True)
    isApproved = serializers.BooleanField(allow_null=True)
    isRejected = serializers.BooleanField(allow_null=True)
    dateType = serializers.IntegerField(required=True)

class GetAllRejectsOutputModel(serializers.Serializer):
    mediaId = serializers.IntegerField(read_only=True)
    label = serializers.CharField(read_only=True)


class GetTrafficLogixLocationResponseModel(serializers.Serializer):
    trafficLogixClientId = serializers.IntegerField()
    locationName = serializers.CharField()


class GetAllAdjudicatorVideoDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isRejected = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isSent = serializers.BooleanField()
    isSentToReviewBin = serializers.BooleanField(required=False, allow_null=True)


class GetAllAdjudicatorImageDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isRejected = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isSent = serializers.BooleanField()
    isSentToReviewBin = serializers.BooleanField(required=False, allow_null=True)
    

class GetAllAdjudicatorTattileDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isRejected = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isSent = serializers.BooleanField()
    isSentToReviewBin = serializers.BooleanField(required=False, allow_null=True)

class GetAllReviewBinVideoDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isRejected = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isSent = serializers.BooleanField()
    isSentToReviewBin = serializers.BooleanField()
    isNotFound = serializers.BooleanField()
    citationID = serializers.CharField(required=False,allow_blank=True)


class GetAllReviewBinImageDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isRejected = serializers.BooleanField()
    isAdjudicated = serializers.BooleanField()
    isSent = serializers.BooleanField()
    isSentToReviewBin = serializers.BooleanField()
    isNotFound = serializers.BooleanField()
    citationID = serializers.CharField(required=False,allow_blank=True)

class GetAllAgencyAdjudicationVideoDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isRejectedInAgnecyAdjudicationBin = serializers.BooleanField()
    isAdjudicatedInAgencyAdjudicationBin = serializers.BooleanField()
    citationID = serializers.CharField(required=False,allow_blank=True)
    isSent = serializers.BooleanField(default=False)


class GetAllAgencyAdjudicationImageDataModel(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    isRejectedInAgnecyAdjudicationBin = serializers.BooleanField()
    isAdjudicatedInAgencyAdjudicationBin = serializers.BooleanField()
    citationID = serializers.CharField(required=False,allow_blank=True)
    isSent = serializers.BooleanField(default=False)


class GetOdrDropDownInputModel(serializers.Serializer):
    fromDate = serializers.DateField(required=False, allow_null=True)
    toDate = serializers.DateField(required=False, allow_null=True)
    isApproved = serializers.BooleanField(allow_null = True)
 
    def to_internal_value(self, data):
        if data.get('fromDate') == '':
            data['fromDate'] = None
        if data.get('toDate') == '':
            data['toDate'] = None
        return super().to_internal_value(data)
   
class GetOdrAllCitationResponseModel(serializers.Serializer):
    citationId = serializers.IntegerField(read_only=True)
    citationID = serializers.CharField(read_only=True)
    isApproved = serializers.BooleanField(allow_null=True)


class GetAllYearsForPreOdrResponseModel(serializers.Serializer):
    year = serializers.IntegerField(read_only=True)


class GetAllMonthsForPreOdrInputModel(serializers.Serializer):
    year = serializers.IntegerField(required=False,allow_null=True)


class GetAllMonthsForPreOdrResponseModel(serializers.Serializer):
    month = serializers.IntegerField(read_only=True)
    monthName = serializers.CharField(read_only=True)


class GetAllDaysForPreOdrInputModel(serializers.Serializer):
    year = serializers.IntegerField(required=False,allow_null=True)
    month = serializers.IntegerField(required=False,allow_null=True)


class GetAllDaysForPreOdrResponseModel(serializers.Serializer):
    day = serializers.IntegerField(read_only=True)


class GetAllPreOdrCitationIdsInputModel(PagedResponseInput,serializers.Serializer):
    mailerType = serializers.IntegerField(required=False,allow_null=True)
    isApproved = serializers.BooleanField(required=False,allow_null=True)
    year = serializers.IntegerField(required=False,allow_null=True)
    month = serializers.IntegerField(required=False,allow_null=True)
    day = serializers.IntegerField(required=False,allow_null=True)
    

class PagedResponse:
    def __init__(self, page_index, page_size, total_records, data):
        self.pageIndex = page_index
        self.pageSize = page_size
        self.totalRecords = total_records
        self.hasNextPage = (page_index * page_size) < total_records
        self.hasPreviousPage = page_index > 1
        self.data = data
        

class GetAllPermissionLevelResponseModel(serializers.Serializer):
    permissions = serializers.DictField(child=serializers.CharField())

class FineDropDownModel(serializers.Serializer):
    fine_amount = serializers.DecimalField(max_digits=10, decimal_places=2)