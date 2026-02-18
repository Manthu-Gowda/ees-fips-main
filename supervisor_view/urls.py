from . import views
from django.urls import path

urlpatterns = [
    path('SupervisorView/GetCitationDataById',views.GetCitationDataByIdView.as_view(),name="GetCitationDataById"),
    path('SupervisorView/CitationStatusUpdate',views.CitationStatusUpdateView.as_view(),name="CitationStatusUpdate")
]