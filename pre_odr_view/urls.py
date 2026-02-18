from . import views
from django.urls import path

urlpatterns = [
    path('PreODR/UploadUnpaidCitationData',views.UploadUnpaidCitationDataView.as_view(),name="UploadUnpaidCitationData"),
    path('PreODR/SubmitPreOdrCitation',views.SubmitPreOdrCitationView.as_view(),name="SubmitPreOdrCitation"),
    path('PreODR/GetDataForPreOdrTable',views.GetDataForPreOdrTableView.as_view(),name="GetDataForPreOdrTable"),
    path('PreODR/GetCSVDataForPreOdr',views.GetCSVDataForPreOdrView.as_view(),name="GetCSVDataForPreOdr"),
    path('PreODR/ViewMailerPDF',views.ViewMailerPDFView.as_view(),name="ViewMailerPDF"),
    path('PreODR/DelectUnpaidCitationData',views.DelectUnpaidCitationDataView.as_view(),name="DelectUnpaidCitationData")
]