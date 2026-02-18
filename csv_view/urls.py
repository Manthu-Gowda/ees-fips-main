from . import views
from django.urls import path

urlpatterns = [
    path('CSVView/GetQuickPDData',views.GetQuickPDDataView.as_view(),name="GetQuickPDData")
]