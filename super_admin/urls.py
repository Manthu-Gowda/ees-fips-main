from . import views
from django.urls import path

urlpatterns = [
    path('SuperAdmin/AddCustomer',views.AddCustomerView.as_view(),name="AddCustomer"),
    path('SuperAdmin/GetAllAgencyDetails',views.GetAllAgencyDetailsView.as_view(),name="GetAllAgencyDetails"),
    path('SuperAdmin/GetAgencyDetailsById',views.GetAgencyDetailsByIdView.as_view(),name="GetAgencyDetailsById"),
    path('SuperAdmin/UpdateAgencyDetailsById',views.UpdateAgencyDetailsByIdView.as_view(),name="UpdateAgencyDetailsById"),
    path('SuperAdmin/GetAllUserDetails',views.GetAllUserDetailsView.as_view(),name="GetAllUserDetails"),
    path('SuperAdmin/GetUserDetailsById',views.GetUserDetailsByIdView.as_view(),name="GetUserDetailsById"),
    path('SuperAdmin/UpdateUserDetailsById',views.UpdateUserDetailsByIdView.as_view(),name="UpdateUserDetailsById"),
    path('SuperAdmin/UpdateAgencyStatusView',views.UpdateAgencyStatusView.as_view(),name="UpdateAgencyStatusView"),
    path("superadmin/CreateFolder", views.CreateFolder.as_view(),name="CreateFolder"),
    path("superadmin/UploadFiles", views.UploadFiles.as_view(),name="UploadFiles"),
    path("superadmin/GetFolderHierarchy", views.GetFolderHierarchy.as_view(),name="GetFolderHierarchy"),
    path("superadmin/GetFileData", views.GetFileData.as_view(),name="GetFileData"),
    path("superadmin/DeleteFolder", views.DeleteFolder.as_view(),name="DeleteFolder"),
    path("superadmin/DeleteFiles", views.DeleteFiles.as_view(),name="DeleteFiles"),
]