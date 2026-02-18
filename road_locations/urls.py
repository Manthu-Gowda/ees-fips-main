from . import views
from django.urls import path

urlpatterns = [
    path('RoadLocation/GetAllRoadLocationsDetails',views.GetAllRoadLocationsDetailsView.as_view(),name="GetAllRoadLocationsDetails"),
    path('RoadLocation/AddOrUpdateRoadLocationDetails',views.AddOrUpdateRoadLocationDetailsView.as_view(),name="AddOrUpdateRoadLocationDetails"),
    path('RoadLocation/DeleteRoadLocationDetails',views.DeleteRoadLocationDetailsView.as_view(),name="DeleteRoadLocationDetails"),
]