from rest_framework import serializers

class GetCitationDataForCourtPrviewInputModel(serializers.Serializer):
    mediaType = serializers.IntegerField(required=True)
    citationID = serializers.CharField(required=True)

class GetCitationDataForCourtPrviewOutputModel(serializers.Serializer):
    citationID = serializers.CharField(read_only=True,allow_blank=False)
    mediaUrl = serializers.ListField(child=serializers.CharField(),allow_empty=True)