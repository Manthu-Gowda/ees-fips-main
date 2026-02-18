from . import views
from django.urls import path

urlpatterns = [
    path('Court/AddCourtDate',views.AddCourtDateView.as_view(),name="AddCourtDate")
]