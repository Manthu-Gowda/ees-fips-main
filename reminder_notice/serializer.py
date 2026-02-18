from rest_framework import serializers
from accounts_v2.serializer import *


class GetDataForReminderNoticeYearAndMonthModel(serializers.Serializer):
    year = serializers.IntegerField(required=True)
    month = serializers.IntegerField(required=True)


class GetReminderNoticeCitationsInputModel(PagedResponseInput, serializers.Serializer):
    dateType = serializers.IntegerField(required=True, allow_null=False)
    fromDate = serializers.DateTimeField(allow_null=True, required=False)
    toDate = serializers.DateTimeField(allow_null=True, required=False)


class GetReminderCitationData(serializers.Serializer):
    citationId = serializers.IntegerField()
    citationID = serializers.CharField(allow_blank=True, required=False)
    mediaId = serializers.CharField(allow_null=True, required=False)
    fine = serializers.IntegerField(allow_null=True, required=False)
    speed = serializers.IntegerField(allow_null=True, required=False)
    locationCode = serializers.IntegerField(allow_null=True, required=False)
    locationName = serializers.CharField(allow_blank=True, required=False)
    firstName = serializers.CharField(allow_blank=True, required=False)
    lastName = serializers.CharField(allow_blank=True, required=False)
    state = serializers.CharField(allow_blank=True, required=False)
    plate = serializers.CharField(allow_blank=True, required=False)
    capturedDate = serializers.CharField(allow_blank=True, required=False)
    approvedDate = serializers.CharField(allow_blank=True, required=False)
    citationStatus = serializers.CharField(allow_blank=True,required=False)
    paidStatus = serializers.CharField(allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    combinedPdfPath = serializers.CharField(allow_blank=True, required=False)


class PagedResponse:
    def __init__(self, page_index, page_size, total_records, data):
        self.pageIndex = page_index
        self.pageSize = page_size
        self.totalRecords = total_records
        self.hasNextPage = (page_index * page_size) < total_records
        self.hasPreviousPage = page_index > 1
        self.data = data