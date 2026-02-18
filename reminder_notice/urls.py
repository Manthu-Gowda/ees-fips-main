from . import views
from django.urls import path

urlpatterns = [
    path(
        "ReminderNotice/GetReminderNoticeYears",
        views.GetReminderNoticeYearsView.as_view(),
        name="GetReminderNoticeYears",
    ),
    path(
        "ReminderNotice/GetReminderNoticeMonthsByYear",
        views.GetReminderNoticeMonthsByYearView.as_view(),
        name="GetReminderNoticeMonthsByYear",
    ),
    path(
        "ReminderNotice/GetReminderNoticeCitationIDs",
        views.ReminderNoticeCitationIDView.as_view(),
        name="GetReminderNoticeCitationIDs",
    ),
    path(
        "ReminderNotice/SubmitReminderNoticeAndPDF",
        views.SubmitReminderNoticeAndPDFView.as_view(),
        name="SubmitReminderNoticeAndPDF",
    ),
    path(
        "ReminderNotice/GetReminderNoticeCitationsData",
        views.GetCitationDataForReminderApprovedTableView.as_view(),
        name="GetReminderNoticeCitations",
    ),
    path("ReminderNotice/ViewReminderPDF", views.ViewReminderPDFView.as_view(), name="GetReminderCitationData"),
]
