from rest_framework import serializers
from accounts_v2.serializer import *

class GetCitationData(serializers.Serializer):
    citationId = serializers.IntegerField()
    citationID = serializers.CharField(allow_blank=True,required=False)
    mediaId = serializers.CharField(allow_null=True,required=False)
    fine = serializers.IntegerField(allow_null=True,required=False)
    speed = serializers.IntegerField(allow_null=True,required=False)
    locationCode = serializers.IntegerField(allow_null=True,required=False)
    locationName = serializers.CharField(allow_blank=True,required=False)
    firstName = serializers.CharField(allow_blank=True,required=False)
    lastName = serializers.CharField(allow_blank=True,required=False)
    state = serializers.CharField(allow_blank=True,required=False)
    plate = serializers.CharField(allow_blank=True,required=False)
    capturedDate = serializers.CharField(allow_blank=True,required=False)
    approvedDate = serializers.CharField(allow_blank=True,required=False)
    citationStatus = serializers.CharField(allow_blank=True,required=False)
    paidStatus = serializers.CharField(allow_blank=True,required=False)
    address = serializers.CharField(allow_blank=True,required=False)
    citationVersion = serializers.IntegerField(allow_null=True,required=False)

class PagedResponse:
    def __init__(self, page_index, page_size, total_records, data):
        self.pageIndex = page_index
        self.pageSize = page_size
        self.totalRecords = total_records
        self.hasNextPage = (page_index * page_size) < total_records
        self.hasPreviousPage = page_index > 1
        self.data = data

class GetCitationDataInputModel(PagedResponseInput,serializers.Serializer):
    dateType = serializers.IntegerField(required=True,allow_null=False)
    fromDate = serializers.DateTimeField(allow_null=True,required=False)
    toDate = serializers.DateTimeField(allow_null=True,required=False)
    paidFilterType = serializers.ChoiceField(required=True,allow_null=False,choices=[
        (1,"All"),
        (2,"Paid"),
        (3,"Unpaid")
    ])
    editFilterType = serializers.ChoiceField(required=True,allow_null=False,choices=[
        (1, "All"),
        (2, "OR"),
        (3, "Paid In House"),
        (4, "Return To Sender, Unknown address"),
        (5, "Update Address"),
        (6, "Transfer of Liability"),
        (7, "Edit Fine"),
        (8, "Citation Error"),
        (9, "Dismiss Citation"),
        (10,"Citation Error - DMV"),
        (11,"Citation Error - Adjudication"),
        (12,"Dismiss Citation - Agency Decision"),
        (13,"Dismiss Citation - Duplicate Citation"),
        (14,"Warning Admin"),
    ])
    fine_amount = serializers.IntegerField(allow_null=True,required=False)

class GetPDFBase64StringOutputModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True,required=False)


class GetCSVBase64StringOutputModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True,required=False)

class UpdateCitationDataInputModel(serializers.Serializer):
    citationId = serializers.CharField(allow_blank=False,required=True)
    editType = serializers.ChoiceField(required=True,allow_null=False,choices=[
        (1,"Update Address"),
        (2,"Transfer of Liability"),
        (3,"Edit Fine"),
        (4,"Citation Error"),
        (5,"Dismiss Citation"),
        (6, "Warning Admin"),
    ])
    # Update Address or Transfer of Liability
    address = serializers.CharField(allow_blank=False,required=False)
    state = serializers.CharField(allow_blank=False,required=False)
    zip = serializers.CharField(allow_blank=False,required=False)
    city = serializers.CharField(allow_blank=False,required=False)

    # # Transfer of Liability
    firstName = serializers.CharField(allow_blank=False,required=False)
    lastName = serializers.CharField(allow_blank=False,required=False)
    phoneNumber = serializers.CharField(allow_blank=False,required=False)

    # # Edit Fine
    fine = serializers.IntegerField(allow_null=False,required=False)

    # # Citation Error
    citationErrorType = serializers.ChoiceField(allow_null=False,required=False,choices=[
        (1,"DMV Error"),
        (2,"Adjudication Error"),
    ])

    # # Dismiss Citation
    citationDismissalType = serializers.ChoiceField(allow_null=False,required=False,choices=[
        (1,"Agency Decision"),
        (2, "Duplicate Citation"),
    ])

    sendMail = serializers.BooleanField(default=True)


class GetApprovedTableEditViewDataInputModel(serializers.Serializer):
    fromDate = serializers.CharField(required=False,allow_null=True, allow_blank=True)
    toDate = serializers.CharField(required=False,allow_null=True, allow_blank=True)
    filterType = serializers.ChoiceField(required=True,allow_null=False,choices=[
        (1,"All"),
        (2,"Paid"),
        (3,"Unpaid")
    ])

class EditCitationDataInputModel(serializers.Serializer):
  citationId = serializers.CharField(allow_blank=False,required=True)
  editType = serializers.ChoiceField(required=True,allow_null=False,choices=[
      (1,"Paid In House"),
      (2,"Return To Sender, Unknown address"),
  ])

class GetCitationVersionsInputSerializer(serializers.Serializer):
    citationId = serializers.IntegerField()
