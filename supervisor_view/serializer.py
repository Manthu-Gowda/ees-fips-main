from rest_framework import serializers


class GetCitationByIdInputModel(serializers.Serializer):
    mediaType = serializers.IntegerField(required=True)
    citationId = serializers.IntegerField(required=True)

class GetCitationByIdOuputModel(serializers.Serializer):
    citationId = serializers.IntegerField(read_only=True)
    videoUrl = serializers.CharField(read_only=True)
    imageUrls = serializers.ListField(child=serializers.CharField(),allow_empty=True)
    speedPic = serializers.CharField(read_only=True)
    platePic = serializers.CharField(read_only=True)
    licensePlateState = serializers.CharField(read_only=True)
    licensePlateNumber = serializers.CharField(read_only=True)
    postedSpeed = serializers.IntegerField(read_only=True)
    violatingSpeed = serializers.IntegerField(read_only=True)
    locationCode = serializers.IntegerField(read_only=True)
    locationName = serializers.CharField(read_only=True)
    stateRS = serializers.CharField(read_only=True)
    distance = serializers.IntegerField(read_only=True,allow_null = True)
    fine = serializers.IntegerField(read_only=True)
    citationID = serializers.CharField(read_only=True)
    firstName = serializers.CharField(read_only=True)
    middleName = serializers.CharField(read_only=True)
    lastName = serializers.CharField(read_only=True)
    phoneNumber = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    city = serializers.CharField(read_only=True)
    personStateAB = serializers.CharField(read_only=True)
    zip = serializers.CharField(read_only=True)
    vehicleYear = serializers.CharField(allow_blank=True)
    vehicleMake = serializers.CharField(allow_blank=True)
    vehicleModel = serializers.CharField(allow_blank=True)
    vehicleColor = serializers.CharField(allow_blank=True)
    vinNumber = serializers.CharField(allow_blank=True)
    note = serializers.CharField(allow_blank=True)
    isWarning = serializers.BooleanField(default=True)

class CitationStatusUpdateInputModel(serializers.Serializer):
    citationIds = serializers.ListField(child=serializers.IntegerField(),allow_empty=False)
    isApproved = serializers.BooleanField(default=True)
    isSendBack = serializers.BooleanField(default=False)
    isRejected = serializers.BooleanField(default=False)
    note = serializers.CharField(required=False,allow_blank=True)    

    def validate_citationIds(self, value):
        for citation_id in value:
            if not isinstance(citation_id, int):
                raise serializers.ValidationError("Invalid citation ID format.")
        return value
    
class ApprovedCitationIDsOutputModel(serializers.Serializer):
    citationID = serializers.ListField(child=serializers.CharField(),allow_empty=True)