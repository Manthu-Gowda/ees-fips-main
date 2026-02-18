from rest_framework import serializers

class GetRejectedMediadataInputModel(serializers.Serializer):
    mediaType = serializers.IntegerField(required=True)
    mediaId = serializers.IntegerField(required=True)
    

class GetRejectedMediaDataOutputModel(serializers.Serializer):
    mediaUrl = serializers.CharField(read_only=True,required=False,allow_blank=True)
    rejectId = serializers.IntegerField(read_only=True,required=False,allow_null=True)
    rejectReason = serializers.CharField(read_only=True,required=False,allow_blank=True)
    note = serializers.CharField(read_only=True,required=False,allow_blank=True)