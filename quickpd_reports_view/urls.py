from . import views
from django.urls import path


urlpatterns = [
    path("QuickPDReports/UploadQuickPdPaidCitations", views.UploadQuickPdPaidCitationsView.as_view(), name="UploadQuickPdPaidCitations"),
    path("QuickPDReports/QuickPdReportSummaryView", views.QuickPdReportSummaryView.as_view(), name="QuickPdReportSummaryView"),
    path("QuickPDReports/QuickPdCitationLevelReportView", views.QuickPdCitationLevelReportView.as_view(), name="QuickPdCitationLevelReportView"),
    path("QuickPDReports/QuickPdReportSummaryDownloadView", views.QuickPdReportSummaryDownloadView.as_view(), name="QuickPdReportSummaryDownloadView"),
    path("QuickPDReports/QuickPdCitationLevelReportDownloadView", views.QuickPdCitationLevelReportDownloadView.as_view(), name="QuickPdCitationLevelReportDownloadView"),
    # path("QuickPDReports/GetSummaryLevelReport", views.GetSummaryLevelReportView.as_view(), name="GetSummaryLevelReport"),
    path("QuickPDReports/GetXpressBillPaySummaryLevelReport", views.GetXpressBillPaySummaryLevelReportView.as_view(), name="GetXpressBillPaySummaryLevelReportView"),
    path("QuickPDReports/GetXpressBillPayReportDownload", views.GetXpressBillPayReportDownloadView.as_view(), name="GetXpressBillPayReportDownload"),
    path("QuickPDReports/GetXpressBillPayCitationLevelReport", views.GetXpressBillPayCitationlevelReportView.as_view(), name="GetXpressBillPayCitationLevelReport"),
    path("QuickPDReports/GetXpressBillPayCitationLevelReportDownload", views.GetXpressBillPayCitationlevelReportDownloadView.as_view(), name="GetXpressBillPayCitationlevelReportDownload"),
    path("QuickPDReports/GetAdjudicatedCitationCountView", views.GetAdjudicatedCitationCountView.as_view(), name="GetAdjudicatedCitationCountView"),
    path("QuickPDReports/QuickPdReportSplitSummaryDownloadView",views.GetXpressBillPaySplitCSVReportDownloadView.as_view(), name="GetXpressBillPaySplitCSVReportDownloadView"),
    ## GRAPH URLS.
    path("QuickPDReports/MonthWiseCitationPaymentStatusGraph",views.MonthWiseCitationPaymentStatusGraph.as_view(),name="MonthWiseCitationPaymentStatusGraph"),
    path("QuickPDReports/ApprovedDateAnalysisGraph",views.ApprovedDateAnalysisGraph.as_view(),name="ApprovedDateAnalysisGraph"),
    path("QuickPDReports/TicketSummaryGraph",views.TicketSummaryGraph.as_view(),name="TicketSummaryGraph"),
    path("QuickPDReports/DuncanActivitySummaryGraph",views.DuncanActivitySummaryGraph.as_view(),name="DuncanActivitySummaryGraph"),
    path("QuickPDReports/PaidSummaryInDaysTableView",views.PaidSummaryInDaysTableView.as_view(),name="PaidSummaryInDaysTableView"),
    path("QuickPDReports/SeventyPlusTicketSummaryGraph",views.SeventyPlusTicketSummaryGraph.as_view(),name="SeventyPlusTicketSummaryGraph"),
]