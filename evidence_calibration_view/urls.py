from . import views
from django.urls import path

urlpatterns = [
    path(
        "EvidenceCalibration/GetEvidenceCalibrationdMediaDataView",
        views.GetEvidenceCalibrationdMediaDataView.as_view(),
        name="GetEvidenceCalibrationdMediaDataView",
    ),
    path(
        "EvidenceCalibration/AddEvidenceCalibrationView",
        views.AddEvidenceCalibrationView.as_view(),
        name="AddEvidenceCalibrationView",
    ),
    path(
        "EvidenceCalibration/GetEvidenceCalibrationView",
        views.GetEvidenceCalibrationView.as_view(),
        name="GetEvidenceCalibrationView",
    ),
    path(
        "EvidenceCalibration/GetEvidenceCalibrationDetails",
        views.GetEvidenceCalibrationDetails.as_view(),
        name="GetEvidenceCalibrationDetails",
    ),
    path(
        "EvidenceCalibration/SubmitEvidenceDetailsView",
        views.SubmitEvidenceDetailsView.as_view(),
        name="SubmitEvidenceDetailsView",
    ),
    path(
        "EvidenceCalibration/EvidenceCalibrationTableView",
        views.GetEvidenceTableDataView.as_view(),
        name="EvidenceCalibrationTableView",
    ),
    path(
        "EvidenceCalibration/GetEvidenceTableGraphDataView",
        views.GetEvidenceTableGraphDataView.as_view(),
        name="GetEvidenceTableGraphDataView",
    ),
    path(
        "EvidenceCalibration/CreatePDFView",
        views.CreatePDFView.as_view(),
        name="CreatePDFView",
    ),
]