"""ees URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views import defaults as default_views
from rest_framework import permissions
from rest_framework.schemas import get_schema_view
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
   openapi.Info(
      title="EES API's",
      default_version='v2',
      description="EES API LIST",
      terms_of_service="https://www.emergentapp.com/",
      contact=openapi.Contact(email="gdn@emergentenforcement.com"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("video.urls")),
    # path("accounts/", include("django.contrib.auth.urls")),
    # path("ees/", include("video.urls")),
    # path("", include("image.urls")),

    #This is for Swagger
    path("api/", include("accounts_v2.urls")),
    path("api/",include("dropdown.urls")),
    path("api/",include("submission_view.urls")),
    path("api/",include("adjudicator_view.urls")),
    path("api/",include("supervisor_view.urls")),
    path("api/",include("approved_tables.urls")),
    path("api/", include("reject_view.urls")),
    path("api/", include("court_preview_view.urls")),
    path("api/", include("csv_view.urls")),
    path("api/", include("road_locations.urls")),
    path("api/", include("fine_view.urls")),
    path("api/", include("court_view.urls")),
    path("api/", include("dashboard_view.urls")),
    path("api/", include("super_admin.urls")),
    path("api/", include("quickpd_reports_view.urls")),
    path("api/", include("pre_odr_view.urls")),
    path("api/", include("agency_adjudicationbin_view.urls")),
    path("api/", include("reviewbin_view.urls")),
    path("api/", include("odr_view.urls")),
    path("api/", include("reminder_notice.urls")),
    path("api/", include("evidence_calibration_view.urls")),
    path("api/", include("mail_center_review.urls")),
    path('ees-api-docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]


if settings.DEBUG:
    # Error pages for development
    urlpatterns += [
        re_path(
            r"^400/$",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        re_path(
            r"^403/$",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        re_path(
            r"^404/$",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        re_path(r"^500/$", default_views.server_error),
    ]

# if settings.DEBUG:
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
