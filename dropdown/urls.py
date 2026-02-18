from . import views
from django.urls import path

urlpatterns = [
    path('DropDown/GetStateDropDown',views.GetStateDropDownView.as_view(),name="GetStateDropDown"),
    path('DropDown/GetSubmissionDatesDropDown',views.GetSubmissionDatesDropDownView.as_view(),name="GetSubmissionDatesDropDown"),
    path('DropDown/GetRejectReasonsDropDown',views.GetRejectReasonsDropDownView.as_view(),name="GetRejectReasonsDropDown"),
    path('DropDown/GetSubmissionViewMediaDropDownView',views.GetSubmissionViewMediaDropDownView.as_view(),name="GetSubmissionViewMediaDropDownView"),
    path('DropDown/GetAdjudicatorViewMediaDropDownView',views.GetAdjudicatorViewMediaDropDownView.as_view(),name="GetAdjudicatorViewMediaDropDownView"),
    path('DropDown/GetAdjudicationDatesDropDown',views.GetAdjudicationDatesDropDownView.as_view(),name="GetAdjudicationDatesDropDown"),
    path('DropDown/GetAllCitationsIDs',views.GetAllCitationsIDsView.as_view(),name="GetAllCitationsIDs"),
    path('DropDown/GetAllRejectedMediaDropDown',views.GetAllRejectedMediaDropDownView.as_view(),name="GetAllRejectedMediaDropDown"),
    path('DropDown/GetTrafficLogixDropDown',views.GetTrafficLogixDropDownView.as_view(),name="GetTrafficLogixDropDown"),
    path('DropDown/GetReviewBinViewMediaDropDown',views.GetReviewBinViewMediaDropDownView.as_view(),name="GetReviewBinViewMediaDropDown"),
    path('DropDown/GetAgencyAdjudicationMediaDropDown',views.GetAgencyAdjudicationMediaDropDownView.as_view(),name="GetAgencyAdjudicationMediaDropDown"),
    path('DropDown/GetAllYearsDropDownForPreOdr',views.GetAllYearsDropDownForPreOdrView.as_view(),name="GetAllYearsDropDownForPreOdr"),
    path('DropDown/GetAllMonthsDropDownForPreOdr',views.GetAllMonthsDropDownForPreOdrView.as_view(),name="GetAllMonthsDropDownForPreOdr"),
    path('DropDown/GetAllDaysDropDownForPreOdr',views.GetAllDaysDropDownForPreOdrView.as_view(),name="GetAllDaysDropDownForPreOdr"),
    path('DropDown/GetAllCitationsForPreOdr',views.GetAllCitationsForPreOdrView.as_view(),name="GetAllCitationsForPreOdr"),
    path('DropDown/GetOdrDropDownView',views.GetOdrDropDownView.as_view(), name = 'GetOdrDropDownView'),
    path('DropDown/GetAllPermissionLevel',views.GetAllPermissionLevelView.as_view(), name = 'GetAllPermissionLevel'),
    path('DropDown/GetFineAmountDropDownView',views.GetFineAmountDropDownView.as_view(), name = 'GetFineAmountDropDownView'),
    path('DropDown/GetEvidenceCalibrationMediaDropDownView',views.GetEvidenceCalibrationMediaDropDownView.as_view(), name = 'GetEvidenceCalibrationMediaDropDownView'),
    path('DropDown/GetSeventyPlusTicketsDropdownView',views.GetSeventyPlusTicketsDropdownView.as_view(),name="GetSeventyPlusTicketsDropdownView"),
]