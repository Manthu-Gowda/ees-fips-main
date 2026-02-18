from . import views
from django.urls import path

urlpatterns = [
    path('ReviewBin/SubmitReviewBinData',views.SubmitReviewBinDataView.as_view(),name="SubmitReviewBinData"),
]