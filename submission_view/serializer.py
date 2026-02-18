from rest_framework import serializers


class SubmitSubmissionViewDataInputModel(serializers.Serializer):
    date = serializers.CharField(required=False,allow_null=True, allow_blank=True)


class GetSubmissionViewDataModel(serializers.Serializer):
    totalSubmission = serializers.IntegerField()
    totalRejection = serializers.IntegerField()
    totalSkipped = serializers.IntegerField()
    totalReviewBin = serializers.IntegerField()
    totalUnknown = serializers.IntegerField()
    totalSentToAdjucation = serializers.IntegerField()


class GetDuncanMasterDataModel(serializers.Serializer):
    licensePlate = serializers.CharField(required=False,allow_blank=True,allow_null=True)
    stateAB = serializers.CharField(required=False,allow_blank=True,allow_null=True)
    viewType = serializers.IntegerField(required=True)


class SubmitSubmissionViewInputModel(serializers.Serializer):
    licensePlate = serializers.CharField(required=False,allow_blank=True)
    isSkipped = serializers.BooleanField(default=False)
    isRejected = serializers.BooleanField(default=False)
    isSubmitted = serializers.BooleanField(default=False)
    isSent = serializers.BooleanField(default=False)
    submittedDate = serializers.DateTimeField()
    isReceived = serializers.BooleanField(default=False)
    isApproved = serializers.BooleanField(default=False)
    imageId = serializers.IntegerField(required=False,allow_null=True)
    videoId = serializers.IntegerField(required=False,allow_null=True)
    rejectId = serializers.IntegerField(required=False,allow_null=False)
    stateAB = serializers.CharField(required=True,allow_blank=False)
    isNotFound = serializers.BooleanField(default=False)
    isSendToAdjudicatorView = serializers.BooleanField(default=False)
    isUnknown = serializers.BooleanField(default=False)
    tattileId = serializers.IntegerField(required=False,allow_null=True)
    cameraDate = serializers.DateTimeField(required=False, allow_null=True)
    cameraTime = serializers.TimeField(required=False, allow_null=True)

class DuncanMasterDataOutputModel(serializers.Serializer):
    fullName = serializers.CharField(read_only=True,allow_null=True)
    address = serializers.CharField(read_only=True,allow_null=True)
    city = serializers.CharField(read_only=True,allow_null=True)
    stateName = serializers.CharField(read_only=True,allow_null=True)
    stateAB = serializers.CharField(read_only=True,allow_null=True)
    zip = serializers.CharField(read_only=True,allow_null=True)
    make = serializers.CharField(read_only=True,allow_null=True)
    model = serializers.CharField(read_only=True,allow_null=True)
    vehicleModel2 = serializers.CharField(read_only=True,allow_null=True)
    color = serializers.CharField(read_only=True,allow_null=True)
    vehicleYear = serializers.CharField(read_only=True,allow_null=True)
    vinNumber = serializers.CharField(read_only=True,allow_null=True)
    firstName = serializers.CharField(read_only=True,allow_null=True)
    middleName = serializers.CharField(read_only=True,allow_null=True)
    lastName = serializers.CharField(read_only=True,allow_null=True)
    phoneNumber = serializers.CharField(read_only=True,allow_null=True)
    personStateAB = serializers.CharField(read_only=True,allow_null=True)
    personStateName = serializers.CharField(read_only=True,allow_null=True)
    zip = serializers.CharField(read_only=True,allow_null=True)
    

class GetMediaDataInputModel(serializers.Serializer):
    mediaId = serializers.IntegerField(required=True)
    mediaType = serializers.IntegerField(required=True)


class GetVideoDataByIdModel(serializers.Serializer):
    id = serializers.IntegerField()
    url = serializers.CharField()
    speed = serializers.IntegerField()
    datetime = serializers.DateTimeField()
    stationId = serializers.IntegerField()
    locationId = serializers.IntegerField()
    locationName = serializers.CharField()
    locationCode = serializers.IntegerField()
    postedSpeed = serializers.IntegerField()
    isSchoolZone = serializers.BooleanField()
    stateRS = serializers.CharField()
    stateId = serializers.IntegerField()
    stateName = serializers.CharField()
    stateAB = serializers.CharField()
    fineId = serializers.IntegerField()
    fineAmount = serializers.IntegerField()
    distance = serializers.IntegerField()
    licensePlate = serializers.CharField(allow_blank=True)



class GetImageDataByIdModel(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    ticketId = serializers.IntegerField(allow_null=True)
    time = serializers.DateTimeField()
    data = serializers.CharField(allow_blank=True)
    speed = serializers.IntegerField(allow_null=True)
    violatingSpeed = serializers.IntegerField(allow_null=True)
    plateText = serializers.CharField(allow_blank=True)
    citationId = serializers.IntegerField(allow_null=True)
    licenseImageUrl = serializers.CharField(allow_blank=True)
    speedImageUrl = serializers.CharField(allow_blank=True)
    stationId = serializers.IntegerField(allow_null=True)
    locationId = serializers.IntegerField(allow_null=True)
    locationName = serializers.CharField(allow_blank=True)
    locationCode = serializers.IntegerField(allow_null=True)
    postedSpeed = serializers.IntegerField(allow_null=True)
    isSchoolZone = serializers.BooleanField()
    stateRS = serializers.CharField(allow_blank=True)
    stateId = serializers.IntegerField(allow_null=True)
    stateName = serializers.CharField(allow_blank=True)
    stateAB = serializers.CharField(allow_blank=True)
    imageUrls = serializers.ListField(child=serializers.CharField(),allow_empty=True)
    fineId = serializers.IntegerField(allow_null=True)
    fineAmount = serializers.IntegerField(allow_null=True)
    distance = serializers.IntegerField(allow_null=True)
    licensePlate = serializers.CharField(allow_blank=True)


class UploadCSVFileModel(serializers.Serializer):
    base64String = serializers.CharField()


class UploadCSVFileResponseModel(serializers.Serializer):
    fileProcessedCount = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField(),allow_empty=True)
    duplicatePlates = serializers.ListField(child=serializers.CharField(),allow_empty=True)


class DownloadTsvFileReturnModel(serializers.Serializer):
    base64String = serializers.CharField()

class VehicleClassificationInputModel(serializers.Serializer):
    firstName = serializers.CharField(required=False, allow_blank=True)
    lastName = serializers.CharField(required=False, allow_blank=True)