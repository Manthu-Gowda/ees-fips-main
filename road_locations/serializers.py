from rest_framework import serializers

class GetAllRoadLocationsResponseModel(serializers.Serializer):
    locationId = serializers.IntegerField(read_only=True)
    locationCode = serializers.IntegerField(read_only=True)
    locationName = serializers.CharField(read_only=True)
    postedSpeed = serializers.IntegerField(read_only=True)
    isSchoolZone = serializers.BooleanField(read_only=True)
    isTrafficLogixLocation = serializers.BooleanField(read_only=True)
    trafficLogixLocationId = serializers.IntegerField(read_only=True)
    isConstructionZone = serializers.BooleanField(read_only=True)


class AddOrUpdateRoadLocationInputModel(serializers.Serializer):
    locationName = serializers.CharField(required=True,allow_blank=False)
    postedSpeed = serializers.IntegerField(required=True,allow_null=False)
    isSchoolZone = serializers.BooleanField(default=False)
    isTrafficLogix = serializers.BooleanField(default=False)
    trafficLogixClientId = serializers.IntegerField(required=False,allow_null=True)
    isConstructionZone = serializers.BooleanField(default=False)