from . import views
from django.urls import path

urlpatterns = [
    path('AdjudicatorView/GetPreSignedUrls',views.GetPreSignedUrls.as_view(),name="GetPreSignedUrls"),
    path('AdjudicatorView/SubmitAdjudicatorData',views.SubmitAdjudicatorDataView.as_view(),name="SubmitAdjudicatorData"),
    path('AdjudicatorView/GetAdjudicationMediaData',views.GetAdjudicationMediaDataView.as_view(),name="GetAdjudicationMediaData"),
    path('AdjudicatorView/GenerateNewCitationID',views.GenerateNewCitationIDView.as_view(),name="GenerateNewCitationID"),
    path('AdjudicatorView/GetBase64StringForPresignedUrls',views.GetBase64StringForPresignedUrlsView.as_view(),name="GetBase64StringForPresignedUrls"),
    path('AdjudicatorView/GetFineView',views.GetFineView.as_view(),name="GetFineView")
]