from . import views
from django.urls import path

urlpatterns = [
    path('CourtPreview/GetCitationDataForCourtPreview',views.GetCitationDataForCourtPreviewView.as_view(),name="GetCitationDataForCourtPreviewView")
]