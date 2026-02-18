from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import localdate
from django.utils import timezone
from datetime import datetime
from accounts.models import Station, User

from django.db.models import Max
from django.db.models.functions import Coalesce

class Video(models.Model):
    VIDEO_NO = models.TextField(blank=True)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_videos"
    )
    caption = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    posted_speed = models.IntegerField(blank=True)
    speed = models.IntegerField(blank=True)
    speed_time = models.DecimalField(blank=True, decimal_places=20, max_digits=100)
    location = models.ForeignKey(
        "road_location", on_delete=models.CASCADE, related_name="location_videos"
    )
    reject = models.ForeignKey(
        "Rejects",
        on_delete=models.CASCADE,
        related_name="reject_videos",
        null=True,
        blank=True,
    )
    distance = models.IntegerField(blank=True)
    datetime = models.DateTimeField(default=timezone.now)
    isRejected = models.BooleanField(default=False)
    isAdjudicated = models.BooleanField(default=False)
    isRemoved = models.BooleanField(default=False)
    officer_badge = models.TextField(blank=True)
    isSent = models.BooleanField(default=False)
    citation = models.ForeignKey(
        'Citation', on_delete=models.CASCADE, related_name="citation_videos", null=True, blank=True,
    )
    custom_counter = models.IntegerField(null=True, blank=True)
    is_notfound = models.BooleanField(default=False,help_text="This boolean field will change when is not found triggered in submissions view and ticket sent to review bin")
    isSentToReviewBin = models.BooleanField(default=False,help_text="sent to review bin from adjudicator view")


    def __str__(self):
        return self.caption

    class Meta:
        db_table = "video"
        unique_together = ("station", "VIDEO_NO", "caption")



class Data(models.Model):
    PK = models.TextField(primary_key=True)
    VIDEO_NO = models.TextField()
    VIDEO_NAME = models.TextField()
    FRAMES = models.IntegerField()
    DATE = models.TextField()
    TIME = models.TextField()
    SPEED_LIMIT = models.IntegerField()
    SPEED = models.IntegerField()
    DISTANCE = models.IntegerField(null=True)
    BADGE_ID = models.TextField(blank=True)
    LOCATION_CODE = models.IntegerField(null=True)
    STATION = models.CharField(blank=True)

    class Meta:
        db_table = "video_data"


class Vehicle(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_vehicles"
    )
    vehicle_id = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=4, blank=True)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    color = models.CharField(max_length=100)
    plate = models.CharField(max_length=100)
    lic_state = models.ForeignKey(
        "State", on_delete=models.CASCADE, related_name="lic_state_vehicles"
    )
    vin = models.CharField(max_length=200)

    class Meta:
        db_table = "vehicle"
        unique_together = ("station", "vehicle_id")


class Person(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_persons", null=True
    )
    first_name = models.CharField(max_length=200)
    middle = models.CharField(max_length=50)
    last_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=50)

    class Meta:
        db_table = "person"


class Fine(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_fines"
    )
    speed_diff = models.IntegerField()
    fine = models.DecimalField(decimal_places=2, max_digits=5)
    rs_code = models.CharField(max_length=50)
    isSchoolZone = models.BooleanField(default=False)
    isConstructionZone = models.BooleanField(default=False)

    class Meta:
        db_table = "fine"
    
    def __str__(self):
        return f"{self.fine}"



class Rejects(models.Model):
    ADJUDICATOR = '1'
    DUNCAN = '2'
    
    REJECT_CHOICES = (
        (ADJUDICATOR, 'Adjudicator Rejects'),
        (DUNCAN, 'Duncan Rejects')
    )

    description = models.CharField(max_length=200)
    rejection_type = models.CharField(max_length=20,choices=REJECT_CHOICES, blank=True, null=True, default=None)
    class Meta:
        db_table = "rejects"


class City(models.Model):
    state = models.ForeignKey(
        "State", on_delete=models.CASCADE, related_name="state_cities"
    )
    name = models.CharField(max_length=200)

    class Meta:
        db_table = "city"
    
    def __str__(self):
        return self.name 


class QuickPD(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_quickpds"
    )
    offense_date = models.CharField(max_length=100)
    offense_time = models.CharField(max_length=100, blank=True)
    ticket_num = models.CharField(max_length=100)
    first_name = models.CharField(max_length=200)
    middle = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=200)
    generation = models.CharField(max_length=20, null=True)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=50, blank=True)
    dob = models.CharField(max_length=8, blank=True, default="01012001")
    race = models.CharField(max_length=20, blank=True, null=True)
    sex = models.CharField(max_length=20, blank=True, null=True)
    height = models.CharField(max_length=20, blank=True, null=True)
    weight = models.CharField(max_length=20, blank=True, null=True)
    ssn = models.CharField(max_length=20, blank=True, null=True)
    dl = models.CharField(max_length=20, blank=True, default="1")
    dl_state = models.CharField(max_length=2, blank=True, default="LA")
    accident = models.CharField(max_length=20, blank=True, null=True)
    comm = models.CharField(max_length=20, blank=True, null=True)
    vehder = models.CharField(max_length=20, blank=True, null=True)
    arraignment_date = models.CharField(max_length=100)
    actual_speed = models.IntegerField(null=True)
    posted_speed = models.IntegerField(null=True)
    officer_badge = models.TextField(blank=True)
    street1_id = models.CharField(max_length=20, blank=True, null=True)
    street2_id = models.CharField(max_length=20, blank=True, null=True)
    street1_name = models.CharField(max_length=200, blank=True, null=True)
    street2_name = models.CharField(max_length=200, blank=True, null=True)
    bac = models.CharField(max_length=20, blank=True, null=True)
    test_type = models.CharField(max_length=20, blank=True, null=True)
    plate_num = models.CharField(max_length=100, blank=True, null=True)
    plate_state = models.CharField(max_length=2, blank=True, null=True)
    vin = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=200, blank=True, null=True)
    radar = models.CharField(max_length=20, blank=True, default="0")
    state_rs1 = models.CharField(max_length=100, blank=True, null=True)
    state_rs2 = models.CharField(max_length=100, blank=True, null=True)
    state_rs3 = models.CharField(max_length=100, blank=True, null=True)
    state_rs4 = models.CharField(max_length=100, blank=True, null=True)
    state_rs5 = models.CharField(max_length=100, blank=True, null=True)

    warning = models.CharField(max_length=3, blank=True, null=True)
    notes = models.CharField(max_length=200, blank=True, null=True)
    dl_class = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "quickpd"


class State(models.Model):
    name = models.CharField(max_length=200)
    ab = models.CharField(max_length=2)

    class Meta:
        db_table = "state"


class CourtDates(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_court_dates"
    )
    date_string = models.CharField(max_length=20)
    c_date = models.DateField(null=True)
    phone = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        unique_together = ("station", "date_string")

    class Meta:
        db_table = "court_dates"


class road_location(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_road_locations"
    )
    LOCATION_CODE = models.IntegerField(null=True)
    location_name = models.CharField(max_length=200, blank=True)
    posted_speed = models.IntegerField()
    isSchoolZone = models.BooleanField(null=True)
    isTrafficLogix = models.BooleanField(null=True)
    trafficlogix_location_id= models.IntegerField(null =True)
    isConstructionZone = models.BooleanField(default=False,null=True)

    class Meta:
        db_table = "road_location"
        unique_together = ("station", "LOCATION_CODE")


class SMTP_Data(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_smtp_data"
    )
    csvFile = models.ForeignKey(
        "csv_metadata", on_delete=models.CASCADE, related_name="csv_smtp_data"
    )
    pdfFile = models.ForeignKey(
        "pdf_metadata", on_delete=models.CASCADE, related_name="pdf_smtp_data"
    )
    isPdfSent = models.BooleanField()
    dateTimePdfSent = models.DateTimeField(default=timezone.now)
    dateTimeCsvSent = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "smtp_data"



class Image(models.Model):
    id = models.BigAutoField(primary_key=True)
    ticket_id = models.BigIntegerField()
    location_id = models.BigIntegerField()
    time = models.DateTimeField(default=timezone.now)
    data = models.CharField(max_length=None)
    current_speed_limit = models.IntegerField()
    violating_speed = models.FloatField()
    plate_text = models.CharField(max_length=50)
    locked = models.DateTimeField(default=timezone.now)
    ocr_status = models.IntegerField()
    user_id = models.IntegerField()
    modelId = models.IntegerField()
    hash = models.CharField(max_length=None)
    password = models.CharField(max_length=None)
    validation_status_name = models.CharField(max_length=100)
    validation_name_color = models.CharField(max_length=100)
    camera_name = models.CharField(max_length=100)
    serial = models.CharField(max_length=1000,null=True, blank=True)
    plate_image_filename = models.CharField(max_length=1000)
    speed_unit = models.CharField(max_length=10)
    location_name = models.CharField(max_length=1000)
    static_url = models.CharField(max_length=1000)
    isRejected = models.BooleanField(default=False)
    isAdjudicated = models.BooleanField(default=False)
    isRemoved = models.BooleanField(default=False)
    isSent = models.BooleanField(default=False)
    reject = models.ForeignKey(
        "Rejects",
        on_delete=models.CASCADE,
        related_name="reject_images",
        null=True,
        blank=True,
    )
    citation = models.ForeignKey(
        'Citation', on_delete=models.CASCADE, related_name="citation_images", null=True, blank=True,
    )
    officer_badge = models.TextField(blank=True,default="")
    speed_image_url = models.CharField(max_length=1000,null=True, blank=True)
    lic_image_url = models.CharField(max_length=1000,null=True, blank=True)
    img_distance= models.IntegerField(null = True, blank = True)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_images", null=True, blank=True)
    custom_counter = models.IntegerField(null=True, blank=True)
    is_notfound = models.BooleanField(default=False,help_text="This boolean field will change when is not found triggered in submissions view and will move the ticket to review bin")
    isSentToReviewBin = models.BooleanField(default=False,help_text="sent to review bin from adjudicator view")

    class Meta:
        db_table = "image"

@receiver(post_save, sender=Image)
def reset_image_custom_counters(sender, instance, created, **kwargs):
    if created:
        if instance.custom_counter is None:
            station = instance.station
            ticket_id = instance.ticket_id
            date_time = str(instance.time)
            datetime_obj = datetime.fromisoformat(date_time)
            date_str = datetime_obj.date().isoformat()

            highest_counter = Image.objects.filter(
                station=station, 
                isRejected=False,
                isRemoved=False,
                time__date=date_str
            ).aggregate(max_counter=Coalesce(Max('custom_counter'), 0))['max_counter']

            new_counter_value = highest_counter + 1
            instance.custom_counter = new_counter_value

            instance.save(update_fields=['custom_counter'])


class ImageData(models.Model):
    id = models.BigAutoField(primary_key=True)
    ticket_id = models.BigIntegerField()
    image_name = models.CharField(max_length=None)
    image_url = models.CharField(max_length=None)

    class Meta:
        db_table = "image_data"

class ImageHash(models.Model):
    id = models.BigAutoField(primary_key=True)
    ticket_id = models.BigIntegerField()
    image_hash = models.CharField(max_length=None)
    image_url = models.CharField(max_length=None)

    class Meta:
        db_table = "image_hash"



class ImageLocation(models.Model):
    id = models.BigAutoField(primary_key=True)
    location_id = models.IntegerField()
    company_id = models.IntegerField()
    radar_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country= models.CharField(max_length=100)
    zip = models.CharField(max_length=50)
    contact_user_id = models.IntegerField()
    timezone_id = models.IntegerField()
    direction = models.CharField(max_length=100)
    group_id = models.IntegerField()
    latitude = models.CharField(max_length=100)
    longitude= models.CharField(max_length=100)
    tz= models.CharField(max_length=50)  

    class Meta:
        db_table="image_location"


class Tattile(models.Model):
    version = models.CharField(max_length=100, blank=True, null=True)
    camera_name = models.CharField(max_length=200, blank=True, null=True)
    serial_number = models.CharField(max_length=100)
    time_zone = models.CharField(max_length=100)
    ticket_id = models.CharField(max_length=100)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    image_time = models.DateTimeField()
    country = models.CharField(max_length=100)
    plate_text = models.CharField(max_length=50)
    score = models.IntegerField()
    measured_speed = models.IntegerField()
    speed_limit = models.IntegerField()
    speed_unit = models.CharField(max_length=20)
    officer_badge = models.TextField(blank=True,null=True)
    citation_id = models.CharField(max_length=100)
    location_id = models.IntegerField(null=True)
    location_name = models.CharField(max_length=200)
    license_image_url = models.CharField(max_length=500)
    speed_image_url = models.CharField(max_length=500)
    image_distance = models.FloatField(null=True)
    
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="tattile_records"
    )
    reject = models.ForeignKey(
        Rejects, on_delete=models.CASCADE, related_name="reject_tattile",
        null=True, blank=True,
    )
    
    is_adjudicated = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    is_sent_to_review_bin = models.BooleanField(default=False)
    is_not_found = models.BooleanField(default=False)
    is_violation = models.BooleanField(default=False)
    
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    custom_counter = models.IntegerField(null=True)

    class Meta:
        db_table = "tattile"


class TattileFile(models.Model):
    ticket_id = models.CharField(max_length=100)
    file_name = models.CharField(max_length=200, blank=True, null=True)
    file_url = models.CharField(max_length=200, blank=True, null=True)
    file_type = models.IntegerField()
    
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="tattile_files"
    )
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="tattile_files"
    )
    
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "tattile_file"
        
        
class Citation(models.Model):
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="person_citations", null=True
    )
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_citations"
    )
    vehicle = models.ForeignKey(
        "Vehicle", on_delete=models.CASCADE, related_name="vehicle_citations"
    )
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="video_citations", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="image_citations", null=True
    )
    location = models.ForeignKey(
        "road_location", on_delete=models.CASCADE, related_name="location_citations", null=True
    )
    court_date = models.ForeignKey(
        "CourtDates", on_delete=models.CASCADE, related_name="court_date_citations"
    )

    fine = models.ForeignKey(
        Fine, on_delete=models.CASCADE, related_name="fine_citations"
    )
    citationID = models.CharField(max_length=100, unique=True)
    datetime = models.DateTimeField(default=timezone.now)
    posted_speed = models.IntegerField(null=True)
    speed = models.IntegerField(null=True)
    speed_pic = models.CharField(max_length=500, blank=True)
    plate_pic = models.CharField(max_length=500, blank=True)
    note = models.CharField(max_length=1000, blank=True)
    isApproved = models.BooleanField(default=False)
    isRejected = models.BooleanField(default=False)
    isSendBack = models.BooleanField(default=False)
    isRemoved = models.BooleanField(default=False)
    dist = models.CharField(max_length=50, blank=True)
    is_warning = models.BooleanField(default=False)
    image_location = models.IntegerField(null=True,blank=True)
    captured_date = models.DateField(null=True)
    current_citation_status = models.CharField(
        max_length=10,
        choices=[
        ("OR", "Original"),
        ('PIH', 'Paid In House'),
        ('RTS', 'Return To Sender, Unknown address'),
        ('UA', 'Updated Address'),
        ('TL', 'Transfer of Liability'),
        ('EF', 'Edit Fine'),
        ('CE', 'Citation Error'),
        ("X", "Dismiss Citation"),
        ("WARN-A", "Agency Warning"),
    ],
        default="OR",
        help_text="Current edit status flag",
    )
    citation_error_type = models.CharField(
        max_length=10,
        choices=[
            ('DMV', 'DMV Error'),
            ('ADJ', 'ADJUDICATION ERROR')
        ],
        null=True,
        blank=True,
        help_text="Type of citation error if current_citation_status is CE",
    )
    citation_dissmissal_type = models.CharField(
        max_length=10,
        choices=[
            ('AD', 'AGENCY DECISION'),
            ('DUPC', 'DUPLICATE CITATION')
        ],
        null=True,
        blank=True,
        help_text="Type of citation dismissal if current_citation_status is DC",
    )
    citation_edited_at = models.DateTimeField(null=True)
    edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="citation_edited_by",
        null=True,
    )
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="tattile_citations", null=True
    )
    isRemainderSent = models.BooleanField(default=False)
    remainderSentDate = models.DateTimeField(null=True)
    remainderCombinedPdfPath = models.CharField(max_length=1024, blank=True, null=True)
    fine_amount = models.DecimalField(decimal_places=2, max_digits=10, null=True)
    class Meta:
        db_table = "citation"


class CitationEditLog(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_citation_edit_log"
    )
    citation = models.ForeignKey(
        Citation,
        on_delete=models.CASCADE,
        related_name="citation_citation_edit_log",
        null=True,
    )
    edited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="citation_edit_log_edited_by",
        null=True,
    )
    edited_at = models.DateTimeField(default=timezone.now)
    previous_citation_status = models.CharField(
        max_length=10,
        choices=[
        ("OR", "Original"),
        ('PID', 'Paid In House'),
        ('RTS', 'Return To Sender'),
        ('UA', 'Updated Address'),
        ('TL', 'Transfer of Liability'),
        ('EF', 'Edit Fine'),
        ('CE', 'Citation Error'),
        ("X", "Dismiss Citation"),
        ("WARN-A", "Agency Warning"),
        ],
        default="OR",
    )
    current_citation_status = models.CharField(
        max_length=10,
        choices=[
        ("OR", "Original"),
        ('PID', 'Paid In House'),
        ('RTS', 'Return To Sender'),
        ('UA', 'Updated Address'),
        ('TL', 'Transfer of Liability'),
        ('EF', 'Edit Fine'),
        ('CE', 'Citation Error'),
        ("X", "Dismiss Citation"),
        ("WARN-A", "Agency Warning"),
        ],
        default="OR"
    )
    citation_dissmissal_type = models.CharField(
        max_length=10,
        choices=[
            ('AD', 'AGENCY DECISION'),
            ('DUPC', 'DUPLICATE CITATION')
        ],
        null=True,
        blank=True,
        help_text="Type of citation dismissal if current_citation_status is X",
    )
    citation_error_type = models.CharField(
    max_length=10,
    choices=[
        ('DMV', 'DMV Error'),
        ('ADJ', 'ADJUDICATION ERROR')
    ],
    null=True,
    blank=True,
    help_text="Type of citation error if current_citation_status is CE",
    )
    class Meta:
        db_table = "citation_edit_log"


class adj_metadata(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_adj_metadata"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_adj_metadata"
    )
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="video_adj_metadata", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="image_adj_metadata", null=True
    )
    citation = models.ForeignKey(
        Citation,
        on_delete=models.CASCADE,
        related_name="citation_adj_metadata",
        null=True,
    )
    citationID = models.CharField(max_length=100, default="", blank=True)
    timeAdj = models.DateTimeField(default=timezone.now)
    isRemoved = models.BooleanField(default=False)
    timeRemoved = models.DateTimeField(default=timezone.now, null=True)
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="tattile_adj_metadata", null=True
    )
    class Meta:
        db_table = "adj_metadata"


class sup_metadata(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_sup_metadata"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_sup_metadata"
    )
    citation = models.ForeignKey(
        Citation, on_delete=models.CASCADE, related_name="citation_sup_metadata"
    )
    isApproved = models.BooleanField()
    timeApp = models.DateTimeField(default=timezone.now)
    isRemoved = models.BooleanField(default=False)
    timeRemoved = models.DateTimeField(default=timezone.now, null=True)
    isEdited = models.BooleanField(default=False)
    originalTimeApp = models.DateTimeField(default=None, null=True, blank=True)
    isMailCitationApproved = models.BooleanField(default=False)
    mailCitationApprovedTime = models.DateTimeField(default=None, null=True, blank=True)
    isMailCitationRejected = models.BooleanField(default=False)
    mailCitationRejectedTime = models.DateTimeField(default=None, null=True, blank=True)
    class Meta:
        db_table = "sup_metadata"


class csv_metadata(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_csv_metadata"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_csv_metadata"
    )
    quickPD = models.ForeignKey(
        QuickPD, on_delete=models.CASCADE, related_name="quickPD_csv_metadata"
    )
    date = models.DateTimeField(default=timezone.now)
    url = models.URLField(max_length=500, null=True)

    class Meta:
        db_table = "csv_metadata"


class pdf_metadata(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_pdf_metadata"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_pdf_metadata"
    )
    quickPD = models.ForeignKey(
        QuickPD, on_delete=models.CASCADE, related_name="quickPD_pdf_metadata"
    )
    date = models.DateTimeField(default=timezone.now)
    zipLocation = models.CharField(max_length=100, blank=True)
    url = models.URLField(max_length=500)

    class Meta:
        db_table = "pdf_metadata"


class dmv(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_dmv"
    )
    state_ab = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="state_dmv"
    )
    plate = models.TextField(blank=True)
    raw = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "dmv"


class Agency(models.Model):
    name = models.CharField(max_length=200)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_agencies"
    )
    onboarding_dt = models.DateTimeField(default=timezone.now)
    location = models.CharField(max_length=50)
    api_key = models.CharField(max_length=200)
    device_id = models.CharField(max_length=20)
    ORI = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    address_2 = models.TextField(blank=True)
    phone = models.TextField(blank=True)
    badge_url = models.URLField(max_length=500, blank=True, null=True)
    state_rs = models.CharField(blank=True, max_length=500)
    pay_portal = models.CharField(blank=True, max_length=500)
    court_comments = models.TextField(blank=True)
    emails = models.TextField(blank=True)
    traffic_logix_client_id = models.IntegerField(blank=True,null = True)
    traffic_logix_token = models.CharField(max_length=5000,blank=True,null = True)
    isXpressPay = models.BooleanField(default=False)
    isQuickPd = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    isPreOdr = models.BooleanField(default=False)
    isZill = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "agency"

class VideoFailedLog(models.Model):
    video_no = models.CharField(max_length=20)
    video_name = models.CharField(max_length=30)
    video_date = models.CharField(max_length=20)
    station = models.CharField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    status = models.BooleanField(default=False)
    location_code = models.CharField()
    class Meta:
        db_table = "video_failed_log"

class DuncanSubmission(models.Model):
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="video_duncan_submission", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="image_duncan_submission", null=True
    )
    station = models.CharField(max_length=100, null=True, blank=True)
    isSubmitted = models.BooleanField(default = False)
    isRejected = models.BooleanField(default = False)
    isSkipped = models.BooleanField(default = False)
    isReceived = models.BooleanField(default= False)
    isApproved = models.BooleanField(default= False)
    lic_plate = models.CharField(max_length=100,null=True, blank=True)
    submitted_date = models.DateTimeField(default=timezone.now)
    veh_state = models.CharField(max_length= 50, null= True, blank= True)
    isSent = models.BooleanField(default = False)
    is_notfound=models.BooleanField(default=False)
    is_unknown=models.BooleanField(default=False)
    is_sent_to_adjudication=models.BooleanField(default=False)
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="tattile_duncan_submission", null=True
    )
    class Meta:
        db_table = "duncan_submission"


class FtpUploadLog(models.Model):
    file_name = models.CharField(max_length=100,null=True, blank=True)
    s3_path = models.CharField(max_length=100,null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    record_count = models.IntegerField()
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_upload", null=True
    )
    class Meta:
        db_table = "ftp_upload_log"

class DuncanMasterData(models.Model):
    uploaded_date = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    lic_plate = models.CharField(max_length=100, null=True, blank=True)
    station = models.CharField(max_length=100, null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length= 100, null=True, blank=True)
    person_state = models.CharField(max_length=100, null=True, blank=True)
    zip = models.CharField(max_length=100, null=True, blank=True)
    vehicle_year = models.CharField(max_length=100, null=True, blank=True)
    vehicle_make = models.CharField(max_length=100, null=True, blank=True)
    vehicle_modle = models.CharField(max_length=100, null=True, blank=True)
    vehicle_model_2 = models.CharField(max_length=100, null=True, blank=True)
    vin_number = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    dunccan_data_status = models.CharField(max_length=100, null=True, blank=True)
    color = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_invalid_address = models.BooleanField(default=False,help_text = "Previously marked as invalid in approved table")
    is_address_updated = models.BooleanField(default=False,help_text = "Previously marked as updated address in approved table")
    class Meta:
        db_table = 'dunccan_master_data'

class UnpaidCitation(models.Model):
    ticket_number = models.CharField(max_length= 100, blank=True, null=True)
    off_date = models.DateField(null=True, blank=True)
    arr_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=5, decimal_places=2)
    payment = models.DecimalField(max_digits=5, decimal_places=2)
    balance = models.DecimalField(max_digits=5, decimal_places=2)
    full_name = models.CharField(max_length=100, blank= True, null= True)
    created_date = models.DateTimeField(default=timezone.now)
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="unpaid_video", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="unpaid_image", null=True
    )
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="unpaid_station",null=True, blank =True
    )
    isApproved = models.BooleanField(default=False)
    pre_odr_mail_count = models.IntegerField(blank=True,null = True)
    first_mail_due_date = models.CharField(max_length=100, blank= True, null =True)
    second_mail_due_date = models.CharField(max_length=100, blank= True, null =True)
    odr_due_date = models.DateField(blank= True, null =True)
    first_mail_fine = models.DecimalField(max_digits=5, decimal_places=2, blank= True, null =True)
    second_mail_fine =  models.DecimalField(max_digits=5, decimal_places=2, blank= True, null =True)
    is_deleted = models.BooleanField(default=False)
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="unpaid_tattile", null=True
    )

    class Meta:
        db_table = 'unpaid_citation'

class PaidCitationsData(models.Model):
    transaction_id = models.CharField(max_length=100)  # No longer the primary key
    transaction_date = models.DateField()
    citationID = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=100)
    paid_amount = models.DecimalField(decimal_places=2, max_digits=5)
    video = models.ForeignKey(
        Video, on_delete=models.SET_NULL, related_name="paid_video_citations", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.SET_NULL, related_name="paid_image_citations", null=True
    )
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="paid_tattile_citations", null=True 
    )

    class Meta:
        db_table = "paid_citations"

class PaidProcessedFiles(models.Model):
    """
    Model to store information about processed ZIP files to avoid reprocessing.
    """
    file_name = models.CharField(max_length=255)  # The ZIP file name
    station_name = models.CharField(max_length=100)  # The station that uploaded the ZIP file
    processed_at = models.DateTimeField(auto_now_add=True)  # The timestamp when the file was processed
    class Meta:
        db_table = "paid_citations_data_processed_files"
    def __str__(self):
        return f"{self.file_name} from {self.station_name} processed on {self.processed_at}" 
    

class PreOdrXpressBillPay(models.Model):

    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_xpresspd"
    )
    offense_date = models.CharField(max_length=100)
    offense_time = models.CharField(max_length=100, blank=True)
    ticket_num = models.CharField(max_length=100)
    first_name = models.CharField(max_length=200)
    middle = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=200)
    generation = models.CharField(max_length=20, null=True)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip = models.CharField(max_length=50, blank=True)
    dob = models.CharField(max_length=8, blank=True, default="01012001")
    race = models.CharField(max_length=20, blank=True, null=True)
    sex = models.CharField(max_length=20, blank=True, null=True)
    height = models.CharField(max_length=20, blank=True, null=True)
    weight = models.CharField(max_length=20, blank=True, null=True)
    ssn = models.CharField(max_length=20, blank=True, null=True)
    dl = models.CharField(max_length=20, blank=True, default="1")
    dl_state = models.CharField(max_length=2, blank=True, default="LA")
    accident = models.CharField(max_length=20, blank=True, null=True)
    comm = models.CharField(max_length=20, blank=True, null=True)
    vehder = models.CharField(max_length=20, blank=True, null=True)
    arraignment_date = models.CharField(max_length=100)
    actual_speed = models.IntegerField(null=True)
    posted_speed = models.IntegerField(null=True)
    officer_badge = models.TextField(blank=True)
    street1_id = models.CharField(max_length=20, blank=True, null=True)
    street2_id = models.CharField(max_length=20, blank=True, null=True)
    street1_name = models.CharField(max_length=200, blank=True, null=True)
    street2_name = models.CharField(max_length=200, blank=True, null=True)
    bac = models.CharField(max_length=20, blank=True, null=True)
    test_type = models.CharField(max_length=20, blank=True, null=True)
    plate_num = models.CharField(max_length=100, blank=True, null=True)
    plate_state = models.CharField(max_length=2, blank=True, null=True)
    vin = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=200, blank=True, null=True)
    radar = models.CharField(max_length=20, blank=True, default="0")
    state_rs1 = models.CharField(max_length=50, blank=True, null=True)
    state_rs2 = models.CharField(max_length=50, blank=True, null=True)
    state_rs3 = models.CharField(max_length=50, blank=True, null=True)
    state_rs4 = models.CharField(max_length=50, blank=True, null=True)
    state_rs5 = models.CharField(max_length=50, blank=True, null=True)
    warning = models.CharField(max_length=3, blank=True, null=True)
    notes = models.CharField(max_length=200, blank=True, null=True)
    dl_class = models.CharField(max_length=20, blank=True, null=True)


    class Meta:
        db_table = "pre_odr_xpress_bill_pay"

class PreOdrCSVMetadata(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_pre_csv_metadata"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_pre_csv_metadata"
    )
    xpress_bill_pay = models.ForeignKey(
        PreOdrXpressBillPay, on_delete=models.CASCADE, related_name="xpress_pay_pre_csv_metadata"
    )
    date = models.DateTimeField(default=timezone.now)
    url = models.URLField(max_length=500, null=True)

    class Meta:
        db_table = "pre_odr_csv_metadata"

class PreOdrFineScheduler(models.Model):
    first_mailer_fine_per = models.IntegerField(null=True,blank=True)
    second_mailer_fine_per = models.IntegerField(null=True,blank=True)
    first_mailer_day_gap = models.IntegerField(null=True,blank=True)
    second_mailer_day_gap = models.IntegerField(null=True,blank=True)
    agency = models.ForeignKey(Agency, on_delete= models.CASCADE,related_name= "pre_odr_fine_agency")

    class Meta:
        db_table = "pre_odr_fine_scheduler"


class QuickPdPaidCitations(models.Model):
    ticket_number = models.CharField(max_length=100, unique=True)
    paid_date = models.DateField(null=True)
    batch_date = models.DateField(null=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    total_paid = models.DecimalField(decimal_places=2,max_digits=5)
    court_id = models.IntegerField(null=True)
    court_name = models.CharField(max_length=100, null=True)
    ees_amount = models.DecimalField(decimal_places=2,max_digits=5)
    video = models.ForeignKey(
        Video, on_delete=models.SET_NULL, related_name="quick_pd_paid_citations_video", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.SET_NULL, related_name="quick_pd_paid_citations_image", null=True
    )
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="quick_pd_paid_citations_station",null=True, blank =True
    )
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="quick_pd_paid_citations_tattile", null=True
    )

    class Meta:
        db_table = "quick_pd_paid_citations"



class QuickPdPaidCitationFiles(models.Model):
    file_name = models.CharField(max_length=255)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="quick_pd_paid_citations_files_station",null=True, blank =True
    )
    processed_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="quick_pd_paid_citation_files_user", null=True, blank =True
    )
    rows_processed = models.IntegerField()

    class Meta:
        db_table = "quick_pd_paid_citation_files"
        
        
class OdrCitation(models.Model):
    citation = models.ForeignKey(
        Citation, on_delete=models.CASCADE, related_name="odr_citation"
    )
    initial_amount = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    fine_amount = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    fine_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    second_mail_fine_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="odr_video", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="odr_image", null=True
    )
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="odr_station",null=True, blank =True
    )
    isApproved = models.BooleanField(default=False)
    second_mail_due_date = models.CharField(max_length=100, blank= True, null =True)
    second_mail_fine =  models.DecimalField(max_digits=5, decimal_places=2, blank= True, null =True)
    created_date = models.DateTimeField(default=timezone.now)
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="odr_tattile", null=True
    )
    
    class Meta:
        db_table = "odr_citation"
    
class OdrCSVdata(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="odr_csv_metadata"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    agency_name = models.CharField(max_length=100 ,blank=True)
    state_program_code = models.IntegerField(null=True)
    state_funding_code = models.IntegerField(null=True)
    agency_id = models.CharField(max_length=100, blank=True)
    louisiana_taxpayer_number = models.CharField(max_length=50 , blank=True)
    latoga_agency_code = models.IntegerField(null=True)
    latoga_program_code = models.IntegerField(null=True)
    latoga_region_code = models.IntegerField(null=True)
    odr_debt_type = models.CharField(max_length=100, blank=True)
    agency_debt_id = models.CharField(max_length=100, blank=True)
    debtor_type = models.CharField(max_length=100 , blank=True)
    delinquency_date = models.DateField(null=True)
    finalized_date = models.DateField(null=True)
    interest_rate = models.IntegerField(null=True)
    interest_type = models.CharField(max_length=100 , blank=True)
    interest_to_date = models.DateField(null=True)
    prescription_expiration_date = models.DateField(null=True)
    prescription_amount = models.DecimalField(max_digits=5, decimal_places=2, blank=True)
    ssn = models.CharField(max_length=50 , blank=True)
    fein = models.CharField(max_length=50 , blank=True)
    drivers_license_number = models.CharField(max_length=20 , blank=True)
    drivers_license_state = models.CharField(max_length=20 , blank=True)
    business_name = models.CharField(max_length=100, blank=True)
    full_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100 , blank=True)
    first_name = models.CharField(max_length=100 , blank=True)
    middle_name = models.CharField(max_length=100 , blank=True)
    suffix = models.CharField(max_length=100 , blank=True)
    dba = models.CharField(max_length=100 , blank=True)
    address = models.CharField(max_length=100 , blank=True)
    address_2 = models.CharField(max_length=100)
    unit_type = models.CharField(max_length=100)
    unit = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)
    address_type = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True)
    phone1_type = models.CharField(max_length=50, blank=True)
    home_area_code = models.CharField(max_length=50, blank=True)
    home_phone_number = models.CharField(max_length=50, blank=True)
    phone2_type = models.CharField(max_length=50, blank=True)
    business_area_code = models.CharField(max_length=50, blank=True)
    business_phone_number = models.CharField(max_length=50, blank=True)
    phone3_type = models.CharField(max_length=50, blank=True)
    cell_area_code = models.CharField(max_length=50, blank=True)
    cell_phone_number = models.CharField(max_length=50, blank=True)
    phone4_type = models.CharField(max_length=50, blank=True)
    fax_area_code = models.CharField(max_length=50, blank=True)
    fax_number = models.CharField(max_length=50, blank=True)
    email_address = models.EmailField(blank=True)
    debt_short_description = models.CharField(max_length=100, blank=True)
    debt_long_description = models.CharField(max_length=150, blank=True)
    day_60_letter_mail_date = models.DateField(null=True)
    judgement_date = models.DateField(null=True)
    passback_information_1 = models.CharField(max_length=100, blank=True)
    passback_information_2 = models.CharField(max_length=100, blank=True)
    passback_information_3 = models.CharField(max_length=100, blank=True)
    passback_information_4 = models.CharField(max_length=100, blank=True)
    agency_last_payment_date = models.DateField(null=True)
    agency_last_payment_amt = models.DecimalField(max_digits=5, decimal_places=2, blank=True)
    fees_prior_to_plc = models.DecimalField(max_digits=5, decimal_places=2, blank=True)
    fees_by_OCA_ECA = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    line_item_code_1 = models.CharField(max_length=50, blank=True, null=True)
    line_item_incurred_date_1 = models.DateField(null=True)
    line_item_amount_1 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    line_item_code_2 = models.CharField(max_length=50, blank=True, null=True)
    line_item_incurred_date_2 = models.DateField(null=True, blank=True)
    line_item_amount_2 = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    class Meta:
        db_table = "odr_csv_data"
        
class Odr_csv_metadata(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_odr_csv_metadata"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_odr_csv_metadata"
    )
    odr_meta = models.ForeignKey(
        OdrCSVdata, on_delete=models.CASCADE, related_name="quickPD_odr_csv_metadata"
    )
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "odr_csv_metadata"


class ReviewBin(models.Model):
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="reviewbin_image", null=True
    )
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="reviewbin_video", null=True
    )
    license_plate = models.CharField(max_length=100, null=True, blank=True)
    vehicle_state = models.CharField(max_length=50, null=True, blank=True)
    submitted_date = models.DateTimeField(default=timezone.now)
    station = models.CharField(max_length=100, null=True, blank=True)
    is_notfound = models.BooleanField(default= False)
    is_adjudicated_in_review_bin =  models.BooleanField(default= False)
    is_send_adjbin = models.BooleanField(default= False)
    is_sent_back_subbin = models .BooleanField(default = False)
    is_rejected = models.BooleanField(default = False)
    note = models.CharField(max_length=1000, blank=True)
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="reviewbin_tattile", null=True
    )
    class Meta:
        db_table = "review_bin"

class AdjudicationBin(models.Model):
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="adjudicationbin_video", null=True
    )
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="adjudicationbin_image", null=True
    )
    license_plate = models.CharField(max_length=100,null=True, blank=True)
    vehicle_state = models.CharField(max_length=50, null=True, blank=True)
    is_submitted = models.BooleanField(default = False)
    is_adjudicated_in_adjudicationbin = models.BooleanField(default = False)
    is_skipped = models.BooleanField(default = False)
    is_sent = models.BooleanField(default = False)
    is_rejected = models.BooleanField(default = False)
    station = models.CharField(max_length=100, null=True, blank=True)
    note = models.CharField(max_length=1000, blank=True)
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="adjudicationbin_tattile", null=True
    )
    class Meta:
        db_table = "adjudicated_bin"


# class CitationsPaidInHouse(models.Model):
#     station = models.ForeignKey(
#         Station, on_delete=models.CASCADE, related_name="station_citationspaidinhouse"
#     )
#     is_citations_paid_in_house = models.BooleanField(default=False)
#     citation = models.ForeignKey(
#         Citation, on_delete=models.CASCADE, related_name="citation_citationspaidinhouse"
#     )
#     datetime = models.DateTimeField(default=timezone.now)

#     class Meta:
#         db_table = "citations_paid_in_house"

# class CitationsReturnToSender(models.Model):
#     station = models.ForeignKey(
#         Station, on_delete=models.CASCADE, related_name="station_citationsreturntosender"
#     )
#     is_citations_return_to_sender = models.BooleanField(default=False)
#     citation = models.ForeignKey(
#         Citation, on_delete=models.CASCADE, related_name="citation_citationsreturntosender"
#     )
#     datetime = models.DateTimeField(default=timezone.now)
#     lic_plate = models.CharField(max_length=100, null=True, blank=True)
#     state = models.CharField(max_length=100, null=True, blank=True)


#     class Meta:
#         db_table = "citations_return_to_sender"

class CitationsWithUpdatedAddress(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_citationupdateaddress"
    )
    is_citation_address_updated = models.BooleanField(default=False)
    citation = models.ForeignKey(
        Citation, on_delete=models.CASCADE, related_name="citation_citationupdateaddress"
    )
    datetime = models.DateTimeField(default=timezone.now)
    lic_plate = models.CharField(max_length=30, null=True, blank=True)
    old_address = models.CharField(max_length=100, null=True, blank=True)
    old_person_state = models.CharField(max_length=50, null=True, blank=True)
    old_city = models.CharField(max_length=50, null=True, blank=True)
    updated_address = models.CharField(max_length=100, null=True, blank=True)
    updated_person_state = models.CharField(max_length=50, null=True, blank=True)
    updated_zip = models.CharField(max_length=20, null=True, blank=True)
    old_zip = models.CharField(max_length=20, null=True, blank=True)
    updated_city = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "citations_updated_address"

class CitationsWithTransferOfLiabilty(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_citationtransferofliability"
    )
    is_citation_transfer_of_liabilty = models.BooleanField(default=False)
    citation = models.ForeignKey(
        Citation, on_delete=models.CASCADE, related_name="citation_citationtransferofliability"
    )
    datetime = models.DateTimeField(default=timezone.now)
    lic_plate = models.CharField(max_length=100, null=True, blank=True)
    old_person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="old_person_citations", null=True
    )
    new_person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="new_person_citations", null=True
    )

    class Meta:
        db_table = "citations_transfer_of_liability"

class CitationsWithEditFine(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_citationswitheditfine"
    )
    is_citation_fine_edited = models.BooleanField(default=False)
    citation = models.ForeignKey(
        Citation, on_delete=models.CASCADE, related_name="citation_citationswitheditfine"
    )
    datetime = models.DateTimeField(default=timezone.now)
    old_fine = models.ForeignKey(
        Fine, on_delete=models.CASCADE, related_name="old_fine_citations"
    )

    new_fine =  models.DecimalField(decimal_places=2, max_digits=5)
    class Meta:
        db_table = "citations_edit_fine"

# class CitationWithErrors(models.Model):
#     station = models.ForeignKey(
#         Station, on_delete=models.CASCADE, related_name="station_citationupdateaddress"
#     )
#     error_type = models.CharField(
#         max_length=10,
#         choices=[
#             ('DMV', 'DMV Error'),
#             ('ADJ', 'ADJUDICATION ERROR')
#         ],
#         null=True,
#         blank=True,
#         help_text="Type of citation error if current_citation_status is CE",
#     )
#     citation = models.ForeignKey(
#         Citation, on_delete=models.CASCADE, related_name="citation_citationsreturntosender"
#     )
#     datetime = models.DateTimeField(default=timezone.now)

#     class Meta:
#         db_table = "citation_errors"


class SuperAdminFolders(models.Model):
    folder_name = models.CharField(max_length=100)
    agency = models.ForeignKey(
        "Agency",
        on_delete=models.CASCADE,
        related_name="agency_folders",
        null=True,
        blank=True,
    )
    parent_folder_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of the parent folder, if this is a subfolder",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_folders",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "super_admin_folders"
        constraints = [
            models.UniqueConstraint(
                fields=["folder_name", "agency"], name="unique_folder_per_agency"
            )
        ]

    def __str__(self):
        return self.folder_name


# add filename and file type,size of the file to store file details
class AgencyFileDetails(models.Model):
    file_path = models.CharField(max_length=500)
    file_name = models.CharField(max_length=200)  
    file_type = models.CharField(max_length=10)  
    file_size = models.BigIntegerField()  

    folder = models.ForeignKey(
        SuperAdminFolders,
        on_delete=models.CASCADE,
        related_name="files",
    )
    agency = models.ForeignKey(
        "Agency",
        on_delete=models.CASCADE,
        related_name="file_details",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="uploaded_files",
        null=True,
        blank=True,
    )
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "agency_file_details"
        constraints = [
            models.UniqueConstraint(
                fields=["file_name", "folder", "agency"],
                name="unique_file_per_folder_agency",
            )
        ]

    def __str__(self):
        return self.file_name
    
class EvidenceCalibrationBin(models.Model):
    image = models.ForeignKey(
        Image, on_delete=models.CASCADE, related_name="evidence_calibration_bin_image", null=True
    )
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="evidence_calibration_bin_video", null=True
    )
    license_plate = models.CharField(max_length=100, null=True, blank=True)
    vehicle_state = models.CharField(max_length=50, null=True, blank=True)
    submitted_date = models.DateTimeField(default=timezone.now)
    station = models.CharField(max_length=100, null=True, blank=True)
    is_rejected = models.BooleanField(default = False)
    note = models.CharField(max_length=1000, blank=True)
    tattile = models.ForeignKey(
        Tattile, on_delete=models.CASCADE, related_name="evidence_calibration_bin_tattile", null=True
    )
    camera_date = models.DateTimeField(null=True, blank=True)
    camera_time = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = "evidence_calibration_bin"

class AddEvidenceCalibration(models.Model):
    license_plate = models.CharField(max_length=100, null=True, blank=True)
    evidence_date = models.DateTimeField(default=timezone.now)
    evidence_time = models.TimeField(default=timezone.now)
    evidence_speed = models.IntegerField(null=True, blank=True)
    tattile = models.ForeignKey(
        Tattile,
        on_delete=models.CASCADE,
        related_name="add_evidence_calibration_tattile",
        null=True,
    )
    image = models.ForeignKey(
        Image,
        on_delete=models.CASCADE,
        related_name="add_evidence_calibration_image",
        null=True,
    )
    evidence_ID = models.CharField(max_length=20, unique=True, null=True, blank=True)
    badge_id = models.CharField(max_length=100, null=True, blank=True)
    evidence_mapped_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.evidence_ID:
            last_id = AddEvidenceCalibration.objects.order_by("-id").first()
            next_number = 1 if not last_id else last_id.id + 1
            self.evidence_ID = f"ED-{next_number:08d}"  
        super().save(*args, **kwargs)

    class Meta:
        db_table = "add_evidence_calibration"

class CitationVersioning(models.Model):
    citation = models.OneToOneField(
        Citation,
        on_delete=models.CASCADE,
        related_name="citation_versioning",
    )
    current_version_number = models.IntegerField(default=1)
    versions = models.JSONField(default=list)
    latest_status = models.CharField(max_length=20, default="OR")
    latest_approved_date = models.DateTimeField(null=True, blank=True)
    isAllowEdit = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "citation_versioning"