from datetime import timedelta
from rest_framework import serializers
from accounts_v2.serializer import PagedResponseInput, PagedResponseOutput, PagedResponse
import calendar
class GetQuickPdPaidFileInputModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True,required=False)

class GetQuickPdPaidFileOutputModel(serializers.Serializer):
    rowsProcessed = serializers.IntegerField(default=0,required=False)
    errors = serializers.ListField(child=serializers.CharField(),allow_empty=True)
    duplicateTicketNumbers = serializers.ListField(child=serializers.CharField(),allow_empty=True)

class CitationReportItemSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.CharField()
    approvedDate = serializers.DateField()
    citationId = serializers.CharField()
    state = serializers.CharField()
    licencePlate = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    dueAmount = serializers.DecimalField(max_digits=10, decimal_places=2)
    dueDate = serializers.DateField(allow_null=True)
    paymentStatus = serializers.CharField()

    def to_representation(self, instance):
        # Build the output using the annotated fields and related objects.
        rep = {
            'year': instance.year,
            'month': calendar.month_name[instance.month] if instance.month and 1 <= instance.month <= 12 else "",
            'approvedDate': instance.timeApp.strftime("%B %d %Y") if instance.timeApp else "",
            'citationId': instance.citation.citationID,
            'state': instance.citation.person.state if hasattr(instance.citation.person, 'state') else "",
            'licencePlate': instance.citation.vehicle.plate if hasattr(instance.citation.vehicle, 'plate') else "",
            'firstName': instance.citation.person.first_name,
            'lastName': instance.citation.person.last_name,
            'dueAmount': instance.due_amount,
            'dueDate': instance.timeApp.date()  + timedelta(days=30) if instance.timeApp else None,
            'paymentStatus': instance.payment_status,
        }
        return rep

class SummaryLevelInputModel(PagedResponseInput,serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    filterType = serializers.IntegerField(required=False, default=1)
    mailerType = serializers.IntegerField(required=False, default=0)


class QuickPdReportSummaryDownloadInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    searchString = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    filterType = serializers.IntegerField(required=False, default=1)
    mailerType = serializers.IntegerField(required=False, default=0)
    pageIndex = serializers.IntegerField(required=False, default=1)
    pageSize = serializers.IntegerField(required=False, default=10)

class CitationLevelReportInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    searchString = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    pageIndex = serializers.IntegerField(required=False, default=1)
    pageSize = serializers.IntegerField(required=False, default=10)
    mailerType = serializers.IntegerField(required=False, default=0)
    paymentStatusType = serializers.IntegerField(required=False, default=0)

class CitationLevelReportDownloadInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    searchString = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    mailerType = serializers.IntegerField(required=False, default=0)
    pageIndex = serializers.IntegerField(required=False, default=1)
    pageSize = serializers.IntegerField(required=False, default=10)
    paymentStatusType = serializers.IntegerField(required=False, default=0)

class GetCSVBase64StringOutputModel(serializers.Serializer):
    base64String = serializers.CharField(allow_blank=True,required=False)


class GetSummaryLevelReportDataResponseModel(serializers.Serializer):
    approvedDate = serializers.CharField(allow_blank=True,required=False)
    totalApproved = serializers.IntegerField(required=False,allow_null=False)
    paid = serializers.IntegerField(required=False,allow_null=False)
    unPaid = serializers.IntegerField(required=False,allow_null=False)
    paidPercentage = serializers.CharField(required=False,allow_blank=True)
    unPaidPercentage = serializers.IntegerField(required=False,allow_null=False)
    amountreceived = serializers.IntegerField(required=False,allow_null=False)
    amountDues = serializers.IntegerField(required=False,allow_null=False)
    month = serializers.CharField(allow_blank=True,required=False)
    year = serializers.CharField(allow_blank=True,required=False)

class XpressBillPayCitationLevelReportInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    searchString = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    pageIndex = serializers.IntegerField(required=False, default=1)
    pageSize = serializers.IntegerField(required=False, default=10)
    paymentStatusType = serializers.IntegerField(required=False, default=0)

class  XpressBillPaySummaryLevelInputModel(PagedResponseInput,serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    filterType = serializers.IntegerField(required=False, default=1)

# class PagedResponse:
#     def __init__(self, page_index, page_size, total_records, data):
#         self.pageIndex = page_index
#         self.pageSize = page_size
#         self.totalRecords = total_records
#         self.hasNextPage = (page_index * page_size) < total_records
#         self.hasPreviousPage = page_index > 1
#         self.data = data


class CitationlevelReportItemSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.CharField()
    approved_date = serializers.DateField()
    citation_id = serializers.CharField()
    state = serializers.CharField()
    lic_plate = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    due_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_date = serializers.DateField(allow_null=True)
    payment_status = serializers.CharField()

    def to_representation(self, instance):
        return {
            'year': instance.get('year'),
            'month': instance.get('month'),
            'approvedDate': instance.get('approved_date'),
            'citationId': instance.get('citation_id'),
            'state': instance.get('state'),
            'licencePlate': instance.get('lic_plate'),
            'firstName': instance.get('first_name'),
            'lastName': instance.get('last_name'),
            'dueAmount': instance.get('due_amount'),
            'dueDate': instance.get('due_date'),
            'paymentStatus': instance.get('payment_status'),
        }
    
class GetAdjudicatedCitationCountViewInputModel(serializers.Serializer):
    adjFromDate = serializers.CharField(required=False,allow_null=True, allow_blank=True)
    adjToDate = serializers.CharField(required=False,allow_null=True, allow_blank=True)

class GetSplitCSVBase64OutputModel(serializers.Serializer):
    approvedCSV = serializers.CharField(allow_blank=True, required=False)
    # editedApprovedCSV = serializers.CharField(allow_blank=True, required=False)

class MonthWiseCitationPaymentStatusInputSerializer(serializers.Serializer):
    monthFilter = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    viewType = serializers.IntegerField(required=False, default=0)

class MonthWiseCitationPaymentStatusOutputSerializer(serializers.Serializer):
    approvedDate = serializers.CharField(allow_blank=True,required=False)
    totalApproved = serializers.IntegerField(required=False,allow_null=False)
    paid = serializers.IntegerField(required=False,allow_null=False)
    unPaid = serializers.IntegerField(required=False,allow_null=False)
    paidPercentage = serializers.CharField(required=False,allow_blank=True)
    unPaidPercentage = serializers.CharField(required=False,allow_null=False)
    amountreceived = serializers.IntegerField(required=False,allow_null=False)
    amountDues = serializers.IntegerField(required=False,allow_null=False)
    month = serializers.CharField(allow_blank=True,required=False)
    year = serializers.CharField(allow_blank=True,required=False)

class ApprovedDateAnalysisInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    viewType = serializers.IntegerField(required=False, default=0)
class ApprovedDateAnalysisOutputSerializer(serializers.Serializer):
    approvedDate = serializers.CharField(allow_blank=True,required=False)
    totalApproved = serializers.IntegerField(required=False,allow_null=False)
    paid = serializers.IntegerField(required=False,allow_null=False)
    unPaid = serializers.IntegerField(required=False,allow_null=False)
    paidPercentage = serializers.CharField(required=False,allow_blank=True)
    unPaidPercentage = serializers.CharField(required=False,allow_null=False)
    amountreceived = serializers.IntegerField(required=False,allow_null=False)
    amountDues = serializers.IntegerField(required=False,allow_null=False)
    month = serializers.CharField(allow_blank=True,required=False)
    year = serializers.CharField(allow_blank=True,required=False)

class TicketSummaryInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    dataType = serializers.IntegerField(required=False, default=0)
    
class TicketSummaryOutputSerializer(serializers.Serializer):
    approvedDate = serializers.CharField(allow_blank=True, required=False)
    tattileImageUploadCount = serializers.IntegerField(required=False, allow_null=False)
    dockerUploadedVideos = serializers.IntegerField(required=False, allow_null=False)

class DuncanActivitySummaryInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)

class DuncanActivitySummaryOutputSerializer(serializers.Serializer):
    approvedDate = serializers.CharField(allow_blank=True,required=False)
    ticketsAdjudicatedInAgencyAdjudicationBin = serializers.IntegerField(required=False,allow_null=False)
    ticketsAdjudicatedInAdjudicatorViewBin = serializers.IntegerField(required=False,allow_null=False)
    ticketsAdjudicatedInReviewBin = serializers.IntegerField(required=False,allow_null=True)

class PaidSummaryInputSerializer(serializers.Serializer):
    startDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    endDate = serializers.CharField(required=False, allow_blank=True,allow_null=True)
    viewType = serializers.IntegerField(required=False, default=0)

class PaidSummaryOutputSerializer(serializers.Serializer):
    approvedDate = serializers.CharField(allow_blank=True, required=False)
    totalApprovedCitations = serializers.IntegerField(required=False, allow_null=False)
    paidBetweenZeroToSevenDays = serializers.IntegerField(required=False, allow_null=False)
    paidBetweenEightToFifteenDays = serializers.IntegerField(required=False, allow_null=False)
    paidBetweenSixteenToThirtyDays = serializers.IntegerField(required=False, allow_null=False)
    paidBetweenThirtyToSixtyDays = serializers.IntegerField(required=False, allow_null=False)
    paidAfterSixtyDays = serializers.IntegerField(required=False, allow_null=False)
    totalPaid = serializers.IntegerField(required=False, allow_null=False)
    totalPaidPercentage = serializers.CharField(required=False, allow_null=False)