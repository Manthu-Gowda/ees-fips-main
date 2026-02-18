from . import views
from django.urls import path

urlpatterns = [
    path('Reject/GetRejectedMediaData',views.GetRejectedMediaDataView.as_view(),name="GetRejectedMediaData")
]