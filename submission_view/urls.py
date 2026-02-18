from . import views
from django.urls import path

urlpatterns = [
    path('SubmissionView/GetSubmissionCount',views.GetSubmissionCountView.as_view(),name="GetSubmissionCount"),
    path('SubmissionView/DownloadTSVFile', views.DownloadTSVFileView.as_view(), name="DownloadTSVFile"),
    path('SubmissionView/FetchDuncanMasterRecord', views.FetchDuncanMasterRecordView.as_view(), name="FetchDuncanMasterRecord"),
    # path('SubmissionView/SubmitDuncanSubmissionData', views.SubmitDuncanSubmissionDataView.as_view(), name="SubmitDuncanSubmissionData"),
    path('SubmissionView/GetMediaData', views.GetMediaDataView.as_view(), name="GetMediaData"),
    path('SubmissionView/UploadCSV', views.UploadCSVView.as_view(), name="UploadCSV"),
    path('SubmissionView/SubmitDuncanSubmissionData', views.SubmitDuncanSubmissionDataView.as_view(), name="SubmitDuncanSubmissionData"),
    path("SubmissionView/VehicleClassification",views.VehicleClassificationView.as_view(),name="VehicleClassification"),
]