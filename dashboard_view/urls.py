from . import views
from django.urls import path

urlpatterns = [
    path('DashBoard/GetDashBoardData',views.GetDashBoardDataView.as_view(),name="GetDashBoardData"),
    path('DashBoard/GetAllMediaCountView',views.GetAllMediaCountView.as_view(),name="GetAllMediaCountView"),
]