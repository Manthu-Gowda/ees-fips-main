from . import views
from django.urls import path

urlpatterns = [
    path("AgencyAdjudicationBinView/SubmitAgencyAdjudicationBin", views.SubmitAgencyAdjudicationBin.as_view(), name="SubmitAgencyAdjudicationBin"),
    path("AgencyAdjudicationBinView/GetAgencyAdjudicationBinMediaData", views.GetAgencyAdjudicationBinMediaData.as_view(), name="GetAgencyAdjudicationBinMediaData"),
]
