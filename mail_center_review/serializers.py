from rest_framework import serializers


class GetMailCenterTableDataInputModel(serializers.Serializer):
    pageIndex = serializers.IntegerField(required=True, allow_null=False)
    dateType = serializers.IntegerField(required=True, allow_null=False)
    pageSize = serializers.IntegerField(required=True, allow_null=False)
    searchString = serializers.CharField(allow_blank=True, required=False)
    approvedDate = serializers.DateTimeField(
        allow_null=True,
        required=False,
        input_formats=[
            "%B %d, %Y",
        ],
    )

class GetApprovedDatesDropdownInputModel(serializers.Serializer):
    dateType = serializers.IntegerField(required=True, allow_null=False)
    
class GetMailCenterTableDataModel(serializers.Serializer):
    citationId = serializers.IntegerField(required=True)
    citationID = serializers.CharField(allow_blank=True, required=False)
    licensePlate = serializers.CharField(allow_blank=True, required=False)
    licenseState = serializers.CharField(allow_blank=True, required=False)
    firstName = serializers.CharField(allow_blank=True, required=False)
    lastName = serializers.CharField(allow_blank=True, required=False)
    capturedDate = serializers.CharField(allow_blank=True, required=False)


class GetMailCenterPDFInputModel(serializers.Serializer):
    citationID = serializers.CharField(required=True)


class GetMailCenterPDFModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True, required=False)


class DeleteMailCenterReviewInputModel(serializers.Serializer):
    citationIds = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        required=True,
        help_text="Array of citation IDs to mark as mail rejected",
    )


class ApproveMailCenterReviewInputModel(serializers.Serializer):
    citationIds = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        required=True,
        help_text="Array of citation_ids to mark as mail approved",
    )
    dateType = serializers.IntegerField(required=True, allow_null=False)