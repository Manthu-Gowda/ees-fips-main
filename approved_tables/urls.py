from . import views
from django.urls import path

urlpatterns = [
    path('ApprovedTable/GetCitationDataForApprovedTable',views.GetCitationDataForApprovedTableView.as_view(),name="GetCitationDataForApprovedTable"),
    path('ApprovedTable/ViewPDF',views.ViewPDF.as_view(),name="ViewPDF"),
    path('ApprovedTable/DownloadApprovedTableData',views.DownloadApprovedTableDataView.as_view(),name="DownloadApprovedTableData"),
    path('ApprovedTable/EditApprovedTableData',views.EditApprovedTableDataView.as_view(),name="EditApprovedTableData"),
    path("ApprovedTable/UpdateApprovedTableData", views.UpdateApprovedTableData.as_view(), name="UpdateApprovedTableData"),
    path("ApprovedTable/GetApprovedTableEditCountView", views.GetApprovedTableEditCountView.as_view(), name="GetApprovedTableEditCountView"),
    path("ApprovedTable/GetCitationVersions", views.GetCitationVersions.as_view(), name="GetCitationVersions"),
]