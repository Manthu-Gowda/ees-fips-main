from . import views
from django.urls import path

urlpatterns = [
    path('Fine/GetAllFineDetails',views.GetAllFineDetailsView.as_view(),name="GetAllFineDetails"),
    path('Fine/UpdateFineDetails',views.UpdateFineDetailsView.as_view(),name="UpdateFineDetails")
]