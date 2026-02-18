from rest_framework import serializers


class GetEvidenceMediadataInputModel(serializers.Serializer):
    mediaType = serializers.IntegerField(required=True)
    mediaId = serializers.IntegerField(required=True)


class GetEvidenceMediaDataOutputModel(serializers.Serializer):
    mediaType = serializers.IntegerField(read_only=True)
    mediaId = serializers.IntegerField(read_only=True)
    mediaUrl = serializers.CharField(read_only=True, required=False, allow_blank=True)
    rejectId = serializers.IntegerField(read_only=True, required=False, allow_null=True)
    rejectReason = serializers.CharField(
        read_only=True, required=False, allow_blank=True
    )
    note = serializers.CharField(read_only=True, required=False, allow_blank=True)
    imageUrls = serializers.ListField()


class AddEvidenceCalibrationInputModel(serializers.Serializer):
    licensePlate = serializers.CharField(required=True, allow_blank=False)
    evidenceDate = serializers.DateField(required=True)
    evidenceTime = serializers.TimeField(
        input_formats=["%I:%M %p"],  # Accept: 02:30 PM
        format="%I:%M %p",  # Return: 02:30 PM
        required=False,
        allow_null=True,
    )
    evidenceSpeed = serializers.IntegerField(required=True)
    badgeID = serializers.CharField(required=True, allow_blank=False)


class GetEvidenceCalibrationDetailsInputModel(serializers.Serializer):
    # evidenceID = serializers.CharField(required=True)
    media_type = serializers.IntegerField(required=True)
    media_id = serializers.IntegerField(required=True)


class GetEvidenceCalibrationDetailsOutputModel(serializers.Serializer):
    evidenceId = serializers.IntegerField(read_only=True)
    evidenceID = serializers.CharField(read_only=True, allow_blank=True)
    licensePlate = serializers.CharField(
        read_only=True, required=False, allow_blank=True
    )
    state = serializers.CharField(read_only=True, required=False, allow_blank=True)
    speed = serializers.IntegerField(read_only=True, required=False, allow_null=True)
    locationName = serializers.CharField(
        read_only=True, required=False, allow_null=True
    )
    locationCode = serializers.IntegerField(
        read_only=True, required=False, allow_null=True
    )
    tattileId = serializers.IntegerField(
        read_only=True, required=False, allow_null=True
    )
    videoId = serializers.IntegerField(read_only=True, required=False, allow_null=True)


# add locatoionCode later
class SubmitEvidenceCalibrationDetailsInputModel(serializers.Serializer):
    evidenceID = serializers.CharField(required=True)
    tattileId = serializers.IntegerField(required=True)
    speedPic = serializers.CharField(required=True)
    licensePic = serializers.CharField(required=True)


class EvidenceTableInputSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    fromDate = serializers.DateField(required=False, allow_null=True)
    toDate = serializers.DateField(required=False, allow_null=True)
    page = serializers.IntegerField(required=False, default=1)
    size = serializers.IntegerField(required=False, default=10)

    def validate_from_date(self, value):
        if value in ["", None]:
            return None
        return value

    def validate_to_date(self, value):
        if value in ["", None]:
            return None
        return value


class CreatePDFInputModel(serializers.Serializer):
    evidenceID = serializers.CharField(required=True)


class GetEvidenceCalibrationViewInputSerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, default=1)
    size = serializers.IntegerField(required=False, default=10)
