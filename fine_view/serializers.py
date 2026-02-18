from rest_framework import serializers

class GetAllFineDetailsResponseModel(serializers.Serializer):
    fineId = serializers.IntegerField(read_only=True)
    speedDifference = serializers.IntegerField(read_only=True)
    fineAmount = serializers.IntegerField(read_only=True)
    stateRS = serializers.CharField(read_only=True)
    isSchoolZone = serializers.BooleanField(read_only=True)
    isConstructionZone = serializers.BooleanField(read_only=True)

class UpdateFineDetailsInputModel(serializers.Serializer):
    fineId = serializers.IntegerField(required=True,allow_null=False)
    fineAmount = serializers.IntegerField(required=False,allow_null=True)
    stateRS = serializers.CharField(required=False,allow_blank=True)

class MissingFineIdsResponseModel(serializers.Serializer):
    fineId = serializers.ListField(child=serializers.IntegerField())