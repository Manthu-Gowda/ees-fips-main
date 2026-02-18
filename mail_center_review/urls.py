from . import views
from django.urls import path

urlpatterns = [
    path(
        "MailCenter/GetAllApprovedCitationDates",
        views.GetApprovedDatesDropdown.as_view(),
        name="GetAllApprovedDates",
    ),
    path(
        "MailCenter/GetMailCenterCitationTableData",
        views.MailCenterReviewTableView.as_view(),
        name="GetMailCenterTableData",
    ),
    path(
        "MailCenter/GetMailCenterCitationPDF",
        views.MailCenterPDFView.as_view(),
        name="GetMailCenterCitationPDF",
    ),
    path(
        "MailCenter/ApproveMailCenterCitation",
        views.ApproveMailCenterReview.as_view(),
        name="ApproveMailCenterCitation",
    ),
    path(
        "MailCenter/DeleteMailCenterCitation",
        views.DeleteMailCenterReview.as_view(),
        name="DeleteMailCenterCitation",
    ),
    path(
        "MailCenter/GeneratePDFAndCSVForMailCenterCitations",
        views.GeneratePDFAndCSVForMailCenterCitations.as_view(),
        name="GeneratePDFAndCSVForMailCenterCitations",
    ),
    path(
        "MailCenter/JobStatus/<str:task_id>",
        views.JobStatus.as_view(),
        name="MailCenterJobStatus",
    ),
]
