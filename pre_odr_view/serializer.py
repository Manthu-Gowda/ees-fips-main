from rest_framework import serializers
from accounts_v2.serializer import PagedResponseInput, PagedResponse, PagedResponseOutput

class UploadUnpaidCitationDataInputModel(serializers.Serializer):
    base64StringDocxFile = serializers.CharField(required=False,allow_blank=True,allow_null=True)
    base64StringTxtFile = serializers.CharField(required=False,allow_blank=True,allow_null=True)


class UploadUnpiadCitationDataResponseModel(serializers.Serializer):
    processedCitationCount = serializers.IntegerField()
    unprocessedCitationCount = serializers.IntegerField()


class SubmitPreOdrCitationInputModel(serializers.Serializer):
    citationIDs = serializers.ListField(child=serializers.CharField(),allow_empty=True)


class PagedResponse:
    def __init__(self, page_index, page_size, total_records, data):
        self.pageIndex = page_index
        self.pageSize = page_size
        self.totalRecords = total_records
        self.hasNextPage = (page_index * page_size) < total_records
        self.hasPreviousPage = page_index > 1
        self.data = data


class GetDataForPreOdrTableInputModel(PagedResponseInput,serializers.Serializer):
    fromDate = serializers.DateTimeField(allow_null=True,required=False)
    toDate = serializers.DateTimeField(allow_null=True,required=False)


class GetDataForPreOdrResponseModel(serializers.Serializer):
    id = serializers.IntegerField(read_only=True,required=False,allow_null=True)
    citationId = serializers.CharField(read_only=True,required=False,allow_blank=True)
    citationID = serializers.CharField(read_only=True,required=False,allow_blank=True)
    mediaId = serializers.CharField(read_only=True,required=False,allow_blank=True)
    fine = serializers.DecimalField(max_digits=10,decimal_places=2,read_only=True,required=False,allow_null=True)
    fullName = serializers.CharField(read_only=True,required=False,allow_blank=True)
    capturedDate = serializers.CharField(read_only=True,required=False,allow_blank=True)
    intialDueDate = serializers.CharField(read_only=True,required=False,allow_blank=True)
    preODRMailCount = serializers.IntegerField(read_only=True,required=False,allow_null=True)
    firstMailDueDate = serializers.CharField(read_only=True,required=False,allow_blank=True)
    secondMailDueDate = serializers.CharField(read_only=True,required=False,allow_blank=True)
    firstMailerFine = serializers.DecimalField(max_digits=10,decimal_places=2,read_only=True,required=False,allow_null=True)
    secondMailerFine = serializers.DecimalField(max_digits=10,decimal_places=2,read_only=True,required=False,allow_null=True)
    isFirstMailerPDF = serializers.BooleanField(read_only=True,default=True)
    isSecondMailerPDF = serializers.BooleanField(read_only=True,default=False)


class GetPreOdrCSVViewResponseModel(serializers.Serializer):
    preODRXpressBillPayId = serializers.IntegerField(required=True)
    offenseDate = serializers.CharField(required=False,allow_blank=True)
    offenseTime = serializers.CharField(required=False,allow_blank=True)
    ticketNumber = serializers.CharField(required=False,allow_blank=True)
    firstName = serializers.CharField(required=False,allow_blank=True)
    middleName = serializers.CharField(required=False,allow_blank=True)
    lastName = serializers.CharField(required=False,allow_blank=True)
    generation = serializers.CharField(required=False,allow_blank=True)
    address = serializers.CharField(required=False,allow_blank=True)
    city = serializers.CharField(required=False,allow_blank=True)
    state = serializers.CharField(required=False,allow_blank=True)
    zip = serializers.CharField(required=False,allow_blank=True)
    dob = serializers.CharField(required=False,allow_blank=True)
    race = serializers.CharField(required=False,allow_blank=True)
    sex = serializers.CharField(required=False,allow_blank=True)
    height = serializers.CharField(required=False,allow_blank=True)
    weight = serializers.CharField(required=False,allow_blank=True)
    ssn = serializers.CharField(required=False,allow_blank=True)
    dl = serializers.CharField(required=False,allow_blank=True)
    dlState = serializers.CharField(required=False,allow_blank=True)
    accident = serializers.CharField(required=False,allow_blank=True)
    comm = serializers.CharField(required=False,allow_blank=True)
    vehder = serializers.CharField(required=False,allow_blank=True)
    arraignmentDate = serializers.CharField(required=False,allow_blank=True)
    actualSpeed = serializers.IntegerField(required=False,allow_null=True)
    postedSpeed = serializers.IntegerField(required=False,allow_null=True)
    officerBadge = serializers.CharField(required=False,allow_blank=True)
    street1Id = serializers.CharField(required=False,allow_blank=True)
    street2Id = serializers.CharField(required=False,allow_blank=True)
    street1Name = serializers.CharField(required=False,allow_blank=True)
    street2Name = serializers.CharField(required=False,allow_blank=True)
    bac = serializers.CharField(required=False,allow_blank=True)
    testType = serializers.CharField(required=False,allow_blank=True)
    plateNum = serializers.CharField(required=False,allow_blank=True)
    plateState = serializers.CharField(required=False,allow_blank=True)
    vin = serializers.CharField(required=False,allow_blank=True)
    phoneNumber = serializers.CharField(required=False,allow_blank=True)
    radar = serializers.CharField(required=False,allow_blank=True)
    stateRS1 = serializers.CharField(required=False,allow_blank=True)
    stateRS2 = serializers.CharField(required=False,allow_blank=True)
    stateRS3 = serializers.CharField(required=False,allow_blank=True)
    stateRS4 = serializers.CharField(required=False,allow_blank=True)
    stateRS5 = serializers.CharField(required=False,allow_blank=True)
    warning = serializers.CharField(required=False,allow_blank=True)
    notes = serializers.CharField(required=False,allow_blank=True)
    dlClass = serializers.CharField(required=False,allow_blank=True)
    stationId = serializers.IntegerField(required=False,allow_null=True)
    

class GetMailerPDFBase64StringInputModel(serializers.Serializer):
    mailerType = serializers.IntegerField(required=True,allow_null=False)
    citationID = serializers.CharField(required=True,allow_blank=False)


class GetMailerPDFBase64StringOutputModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True,required=False)