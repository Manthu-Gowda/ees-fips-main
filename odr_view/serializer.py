from rest_framework import serializers
from accounts_v2.serializer import PagedResponseInput

class GetOdrPDFBase64StringOutputModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True,required=False)


class GetOdrCSVViewOutputModel(serializers.Serializer):
    agency_name = serializers.CharField(allow_blank=True, required=False)
    state_program_code = serializers.IntegerField(required=False, allow_null=True)
    state_funding_code = serializers.IntegerField(required=False, allow_null=True)
    agency_id = serializers.CharField(allow_blank=True, required=False)
    louisiana_taxpayer_number = serializers.CharField(allow_blank=True, required=False)
    latoga_agency_code = serializers.IntegerField(required=False, allow_null=True)
    latoga_program_code = serializers.IntegerField(required=False, allow_null=True)
    latoga_region_code = serializers.IntegerField(required=False, allow_null=True)
    odr_debt_type = serializers.CharField(allow_blank=True, required=False)
    agency_debt_id = serializers.CharField(allow_blank=True, required=False)
    debtor_type = serializers.CharField(allow_blank=True, required=False)
    delinquency_date = serializers.DateField(required=False, allow_null=True)
    finalized_date = serializers.DateField(required=False, allow_null=True)
    interest_rate = serializers.IntegerField(required=False, allow_null=True)
    interest_type = serializers.CharField(allow_blank=True, required=False)
    interest_to_date = serializers.DateField(required=False, allow_null=True)
    prescription_expiration_date = serializers.DateField(required=False, allow_null=True)
    prescription_amount = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    ssn = serializers.CharField(allow_blank=True, required=False)
    fein = serializers.CharField(allow_blank=True, required=False)
    drivers_license_number = serializers.CharField(allow_blank=True, required=False)
    drivers_license_state = serializers.CharField(allow_blank=True, required=False)
    business_name = serializers.CharField(allow_blank=True, required=False)
    full_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    first_name = serializers.CharField(allow_blank=True, required=False)
    middle_name = serializers.CharField(allow_blank=True, required=False)
    suffix = serializers.CharField(allow_blank=True, required=False)
    dba = serializers.CharField(allow_blank=True, required=False)
    address = serializers.CharField(allow_blank=True, required=False)
    unit_type = serializers.CharField(required=True)
    unit = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    state = serializers.CharField(required=True)
    zip_code = serializers.CharField(allow_blank=True, required=False)
    country = serializers.CharField(allow_blank=True, required=False)
    address_type = serializers.CharField(allow_blank=True, required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    phone1_type = serializers.CharField(allow_blank=True, required=False)
    home_area_code = serializers.CharField(allow_blank=True, required=False)
    home_phone_number = serializers.CharField(allow_blank=True, required=False)
    phone2_type = serializers.CharField(allow_blank=True, required=False)
    business_area_code = serializers.CharField(allow_blank=True, required=False)
    business_phone_number = serializers.CharField(allow_blank=True, required=False)
    phone3_type = serializers.CharField(allow_blank=True, required=False)
    cell_area_code = serializers.CharField(allow_blank=True, required=False)
    cell_phone_number = serializers.CharField(allow_blank=True, required=False)
    phone4_type = serializers.CharField(allow_blank=True, required=False)
    fax_area_code = serializers.CharField(allow_blank=True, required=False)
    fax_number = serializers.CharField(allow_blank=True, required=False)
    email_address = serializers.EmailField(allow_blank=True, required=False)
    debt_short_description = serializers.CharField(allow_blank=True, required=False)
    debt_long_description = serializers.CharField(allow_blank=True, required=False)
    day_60_letter_mail_date = serializers.DateField(required=False, allow_null=True)
    judgement_date = serializers.DateField(required=False, allow_null=True)
    passback_information_1 = serializers.CharField(allow_blank=True, required=False)
    passback_information_2 = serializers.CharField(allow_blank=True, required=False)
    passback_information_3 = serializers.CharField(allow_blank=True, required=False)
    passback_information_4 = serializers.CharField(allow_blank=True, required=False)
    agency_last_payment_date = serializers.DateField(required=False, allow_null=True)
    agency_last_payment_amt = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    fees_prior_to_plc = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    previous_fees_by_oca = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    line_item_code = serializers.CharField(allow_blank=True, required=False)
    line_item = serializers.CharField(allow_blank=True, required=False)
    incurred_date = serializers.DateField(required=False, allow_null=True)
    line_item_amount = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    
    
class OdrCitationStatusUpdateInputModel(serializers.Serializer):
    citationIds = serializers.ListField(child=serializers.IntegerField(),allow_empty=False)
    isApproved = serializers.BooleanField(default=True)
    
class OdrApprovedCitationIDsOutputModel(serializers.Serializer):
    citationID = serializers.ListField(child=serializers.CharField(),allow_empty=True)
    
class GetOdrCitationDataInputModel(PagedResponseInput,serializers.Serializer):
    dateType = serializers.IntegerField(required=True,allow_null=False)
    fromDate = serializers.DateTimeField(allow_null=True,required=False)
    toDate = serializers.DateTimeField(allow_null=True,required=False)
    
class GetOdrCitationData(serializers.Serializer):
    citationId = serializers.IntegerField()
    citationID = serializers.CharField(allow_blank=True,required=False)
    mediaId = serializers.CharField(allow_null=True,required=False)
    fine = serializers.IntegerField(allow_null=True,required=False)
    fullName = serializers.CharField(allow_blank=True,required=False)
    capturedDate = serializers.CharField(allow_blank=True,required=False)
    initialDueDate = serializers.CharField(allow_blank=True,required=False)
    odrDueDate = serializers.CharField(allow_blank=True,required=False)
    odrFine = serializers.IntegerField(allow_null=True,required=False)
    odrMailCount = serializers.IntegerField(allow_null=True,required=False)

class PagedResponse:
    def __init__(self, page_index, page_size, total_records, data):
        self.pageIndex = page_index
        self.pageSize = page_size
        self.totalRecords = total_records
        self.hasNextPage = (page_index * page_size) < total_records
        self.hasPreviousPage = page_index > 1
        self.data = data
        

class GetOdrCSVBase64StringOutputModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True,required=False)