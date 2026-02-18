from rest_framework import serializers

class GetDashBoardDataResponseModel(serializers.Serializer):
    dockerUploadedVideos = serializers.IntegerField(required=False, allow_null=True)
    trafficLogixUploadedImage = serializers.IntegerField(required=False, allow_null=True)
    adjudicatedVideoCount = serializers.IntegerField(required=False, allow_null=True)
    adjudicatedImageCount = serializers.IntegerField(required=False, allow_null=True)
    approvedVideoCount = serializers.IntegerField(required=False, allow_null=True)
    approvedImageCount = serializers.IntegerField(required=False, allow_null=True)
    tattileImageUploadCount = serializers.IntegerField(required=False, allow_null=True)
    tattileImageAdjudicatedCount = serializers.IntegerField(required=False, allow_null=True)
    tattileImageApprovedCount = serializers.IntegerField(required=False, allow_null=True)


class GetDashBoardDataInputModel(serializers.Serializer):
    fromDate = serializers.DateTimeField(allow_null=True,required=False)
    toDate = serializers.DateTimeField(allow_null=True,required=False)