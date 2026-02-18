from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class Station(models.Model):
    state = models.ForeignKey(
        "video.State", on_delete=models.CASCADE, related_name="state_stations", null=True
    )
    name = models.CharField(
        max_length=50,
        unique=True,
    )
    city = models.ForeignKey(
        "video.City", on_delete=models.CASCADE, related_name="city_stations", null=True, blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = "station"


class User(AbstractUser):
    agency = models.ForeignKey(
        "video.Agency", on_delete=models.CASCADE, related_name="agency_users", null=True
    )
    middle_name = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=500, blank=True)
    zip = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = "user"


class PermissionLevel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    isAdjudicator = models.BooleanField(default=False)
    isSupervisor = models.BooleanField(default=False)
    isAdmin = models.BooleanField(default=False)
    isSuperAdmin = models.BooleanField(default=False)
    isCourt = models.BooleanField(default=False)
    isApprovedTableView = models.BooleanField(default=False)
    isRejectView = models.BooleanField(default=False)
    isCSVView = models.BooleanField(default=False)
    isAddUserView = models.BooleanField(default=False)
    isAddRoadLocationView = models.BooleanField(default=False)
    isEditFineView = models.BooleanField(default=False)
    isSubmissionView = models.BooleanField(default=False)
    isCourtPreview = models.BooleanField(default=False)
    isAddCourtDate = models.BooleanField(default=False)
    isODRView = models.BooleanField(default=False)
    isPreODRView = models.BooleanField(default=False)
    isViewReportView = models.BooleanField(default=False)
    isAgencyAdjudicationBinView = models.BooleanField(default=False)
    isReviewBinView = models.BooleanField(default=False)
    isTotalTicket = models.BooleanField(default=False)
    isDailyReport = models.BooleanField(default=False)

    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_permissions", null=True
    )
    isReminderView = models.BooleanField(default=False)

    class Meta:
        db_table = "permission_level"
