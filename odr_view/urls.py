from . import views
from django.urls import path

urlpatterns = [
    path('OdrView/ViewPDF',views.ViewODRPDF.as_view(),name="OdrViewPDF"),
    path('OdrView/ViewCSV',views.GetOdrCsvDataView.as_view(),name="OdrViewCSV"),
    path('OdrView/OdrCitationSubmitView',views.OdrCitationSubmitView.as_view(),name="OdrCitationSubmitView"),
    path('OdrView/GetOdrApprovedTableView',views.GetOdrApprovedTableView.as_view(),name="GetOdrApprovedTableView"),
    path('OdrView/DownloadOdrApprovedTableDataView',views.DownloadOdrApprovedTableDataView.as_view(),name="DownloadOdrApprovedTableDataView"),
]