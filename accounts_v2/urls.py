from . import views
from django.urls import path

urlpatterns = [
    path('Account/Login',views.LoginView.as_view(),name="Login"),
    path('Account/Register',views.RegisterView.as_view(),name="Register"),
    path('Account/Logout',views.LogoutView,name="Logout"),
    path('Account/ServerStatusCheck',views.ServerStatusCheck,name="ServerStatusCheck")
]
