from django.urls import path

from . import views

from .images import views as image_views
handler404 = "your_app.views.custom_404"

urlpatterns = [
    path("", views.custom_404, name="index"),
    path("upload_file_to_s3", views.upload_file_to_s3, name="upload_file_to_s3"),
    path("genrate_required_pdf/<str:date>", views.genrate_required_pdf, name="genrate_required_pdf"), # based on dates
    # path("genrate_required_pdf", views.genrate_required_pdf, name="genrate_required_pdf"), # based on list of citations
    path("genrate_required_csv/<str:date>", views.genrate_required_csv, name="genrate_required_csv"),
    path("upload/uploads/Non_Violation", views.FileUploadViewNonViolation.as_view(), name="non_violation_upload_file"),
    path("upload/uploads/Violation", views.FileUploadViewViolation.as_view(), name="violation_upload_file"),
    path("upload/uploads/Diagnostic", views.FileUploadViewDiagonistic.as_view(), name="diagonistic_upload_file"),
]
