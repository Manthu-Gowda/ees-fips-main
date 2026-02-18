from video.models import ReviewBin
from django.utils import timezone
from video.models import Person, Vehicle, Citation, Video, Image, CourtDates, adj_metadata, Data, Tattile
data_agencies = Data.objects.all()
from ees.utils import upload_to_s3
import base64
import io
from datetime import datetime

class ReviewBinUtils:
   
    @staticmethod
    def save_reviewbin_data(**kwargs):
        # Check the record exists or not
        if kwargs["video_object"]:
            print("In Not found, video")
            review_bin = ReviewBin.objects.filter(video=kwargs.get("video_object")).first()
            if review_bin:
                print("In Not found, overide the existing record ++++++++++++++++++++++++ ---------------")
                # overide the existing record
                review_bin.image = kwargs.get("image_object")
                review_bin.video = kwargs.get("video_object")
                review_bin.license_plate = kwargs.get("license_plate", "")
                review_bin.vehicle_state = kwargs.get("vehicle_state", "")
                review_bin.submitted_date = kwargs.get("submitted_date", timezone.now())
                review_bin.is_notfound = kwargs.get("is_notfound", False)
                review_bin.is_adjudicated_in_review_bin = kwargs.get("is_adjudicated_in_review_bin", False)
                review_bin.is_send_adjbin = kwargs.get("is_send_adjbin", False)
                review_bin.is_sent_back_subbin = kwargs.get("is_sent_back_subbin", False)
                review_bin.station = kwargs["station_name"]
                review_bin.note = kwargs.get("note", "")
                review_bin.tattile = kwargs.get("tattile_object", None)
                review_bin.save()
                return review_bin
            else:
                print("In Not found, else ++++++++++++++++++++++++ ---------------")
                review_bin = ReviewBin(
                    image=kwargs.get("image_object"),
                    video=kwargs.get("video_object"),
                    license_plate=kwargs.get("license_plate", ""),
                    station=kwargs["station_name"],  # Required field, should always be provided
                    vehicle_state=kwargs.get("vehicle_state", ""),
                    submitted_date=kwargs.get("submitted_date", timezone.now()),
                    is_notfound=kwargs.get("is_notfound", False),
                    is_adjudicated_in_review_bin=kwargs.get("is_adjudicated_in_review_bin", False),
                    is_send_adjbin=kwargs.get("is_send_adjbin", False),
                    is_sent_back_subbin=kwargs.get("is_sent_back_subbin", False),
                    note=kwargs.get("note", ""),
                    tattile=kwargs.get("tattile_object", None)
                )
                review_bin.save()
        if kwargs["image_object"]:
            print("In Not found, image")
            review_bin = ReviewBin.objects.filter(image=kwargs.get("image_object")).first()
            
            if review_bin:
                # overide the existing record
                review_bin.image = kwargs.get("image_object")
                review_bin.video = kwargs.get("video_object")
                review_bin.license_plate = kwargs.get("license_plate", "")
                review_bin.vehicle_state = kwargs.get("vehicle_state", "")
                review_bin.submitted_date = kwargs.get("submitted_date", timezone.now())
                review_bin.is_notfound = kwargs.get("is_notfound", False)
                review_bin.is_adjudicated_in_review_bin = kwargs.get("is_adjudicated_in_review_bin", False)
                review_bin.is_send_adjbin = kwargs.get("is_send_adjbin", False)
                review_bin.is_sent_back_subbin = kwargs.get("is_sent_back_subbin", False)
                review_bin.station = kwargs["station_name"]
                review_bin.note = kwargs.get("note", "")
                review_bin.tattile = kwargs.get("tattile_object", None)
                review_bin.save()
                return review_bin
            else:
                review_bin = ReviewBin(
                    image=kwargs.get("image_object"),
                    video=kwargs.get("video_object"),
                    license_plate=kwargs.get("license_plate", ""),
                    station=kwargs["station_name"],  # Required field, should always be provided
                    vehicle_state=kwargs.get("vehicle_state", ""),
                    submitted_date=kwargs.get("submitted_date", timezone.now()),
                    is_notfound=kwargs.get("is_notfound", False),
                    is_adjudicated_in_review_bin=kwargs.get("is_adjudicated_in_review_bin", False),
                    is_send_adjbin=kwargs.get("is_send_adjbin", False),
                    is_sent_back_subbin=kwargs.get("is_sent_back_subbin", False),
                    note=kwargs.get("note", ""),
                    tattile=kwargs.get("tattile_object", None)
                )
                review_bin.save()
        
        if kwargs["tattile_object"]:
            print("In Not found, tattile")
            review_bin = ReviewBin.objects.filter(tattile=kwargs.get("tattile_object")).first()
            
            if review_bin:
                # overide the existing record
                review_bin.image = kwargs.get("image_object")
                review_bin.video = kwargs.get("video_object")
                review_bin.license_plate = kwargs.get("license_plate", "")
                review_bin.vehicle_state = kwargs.get("vehicle_state", "")
                review_bin.submitted_date = kwargs.get("submitted_date", timezone.now())
                review_bin.is_notfound = kwargs.get("is_notfound", False)
                review_bin.is_adjudicated_in_review_bin = kwargs.get("is_adjudicated_in_review_bin", False)
                review_bin.is_send_adjbin = kwargs.get("is_send_adjbin", False)
                review_bin.is_sent_back_subbin = kwargs.get("is_sent_back_subbin", False)
                review_bin.station = kwargs["station_name"]
                review_bin.note = kwargs.get("note", "")
                review_bin.tattile = kwargs.get("tattile_object", None)
                review_bin.save()
                return review_bin
            
            else:
                review_bin = ReviewBin(
                    image=kwargs.get("image_object"),
                    video=kwargs.get("video_object"),
                    license_plate=kwargs.get("license_plate", ""),
                    station=kwargs["station_name"],  # Required field, should always be provided
                    vehicle_state=kwargs.get("vehicle_state", ""),
                    submitted_date=kwargs.get("submitted_date", timezone.now()),
                    is_notfound=kwargs.get("is_notfound", False),
                    is_adjudicated_in_review_bin=kwargs.get("is_adjudicated_in_review_bin", False),
                    is_send_adjbin=kwargs.get("is_send_adjbin", False),
                    is_sent_back_subbin=kwargs.get("is_sent_back_subbin", False),
                    note=kwargs.get("note", ""),
                    tattile=kwargs.get("tattile_object", None)
                )
                review_bin.save()
        return review_bin
    @staticmethod
    def extract_fields(validated_data):
        """
        Extract and return input fields from serializer data.
        """
        return {
            "video_id": validated_data.get('videoId', None),
            "image_id": validated_data.get('imageId', None),
            ## this is for tattile
            "tattile_id" : validated_data.get('tattileId',None),
            "is_adjudicated": validated_data.get('isAdjudicatedInReviewBin', False),
            "is_rejected": validated_data.get('isRejected', False),
            "first_name": validated_data.get('firstName', ""),
            "middle_name": validated_data.get('middleName', ""),
            "last_name": validated_data.get('lastName', ""),
            "phone_number": validated_data.get('phoneNumber', ""),
            "address": validated_data.get('address', ""),
            "city": validated_data.get('city', ""),
            "state_ab": validated_data.get('stateAB', ""),
            "zip_code": validated_data.get('zip', ""),
            "vehicle_year": validated_data.get('vehicleYear', ""),
            "make": validated_data.get('make', ""),
            "model": validated_data.get('model', ""),
            "color": validated_data.get('color', ""),
            "vin_number": validated_data.get('vinNumber', ""),
            "note": validated_data.get('note', ""),
            "is_warning": validated_data.get('isWarning', True),
            "reject_id": validated_data.get('rejectId', None),
            "license_plate": validated_data.get('licensePlate', None),
            "speedPic": validated_data.get('speedPic', None),
            "platePic": validated_data.get('platePic', None),
            "license_state_id": validated_data.get('licenseStateId', None),
            "location_id": validated_data.get('locationId', None),
            "violate_speed": validated_data.get('violatedSpeed', None),
            "posted_speed": validated_data.get('postedSpeed', None),
            "distance": validated_data.get('distance', ""),
            "fine_id": validated_data.get('fineId', None),
            "mediaType" : validated_data.get('mediaType'),
            "citationID" : validated_data.get('citationID'),
            "isSent" : validated_data.get('isSent'),
            "isSentToReviewBin" : validated_data.get('isSentToReviewBin',False),
        }

    @staticmethod
    def save_person_data(station_id, fields):
        person = Person(
            first_name=fields.get('first_name', "") or "",
            middle=fields.get('middle_name', "") or "",
            last_name=fields.get('last_name', "") or "",
            phone_number=fields.get('phone_number', "") or "",
            address=fields.get('address', "") or "",
            city=fields.get('city', "") or "",
            state=fields.get('state_ab', "") or "",
            zip=fields.get('zip_code', "") or "",
            station_id=station_id
        )
        person.save()
        return person
    

    @staticmethod
    def save_vehicle_data(station_id, fields):
        vehicle = Vehicle(
            station_id=station_id,
            vehicle_id=Vehicle.objects.filter(station=station_id).count() + 1,
            year=fields.get('vehicle_year', "") or "",
            make=fields.get('make', "") or "",
            model=fields.get('model', "") or "",
            color=fields.get('color', "") or "",
            plate=fields.get('license_plate', "") or "",
            lic_state_id=fields.get('license_state_id'),
            vin=fields.get('vin_number', "") or "",
        )
        vehicle.save()
        return vehicle

    @staticmethod
    def get_date_object(fields):
        """
        Fetch and process the date object for a video.
        """
        if fields['mediaType'] == 1:
            VIDEO_NO = Video.objects.get(id=fields['video_id'])
           
            date = data_agencies.filter(
                VIDEO_NO=VIDEO_NO.VIDEO_NO,
                VIDEO_NAME = VIDEO_NO.caption[:20]
            ).values_list('DATE', flat=True).first()
            return datetime.strptime(date, "%y%m%d").strftime("%Y-%m-%d")
        elif fields['mediaType'] == 2:
            image_data = Image.objects.filter(id=fields['image_id']).values_list('time',flat=True).first()
            return image_data.date().strftime("%Y-%m-%d")
        
        ## this is for tattile
        elif fields['mediaType'] == 3:
            tattile_data = Tattile.objects.filter(id=fields['tattile_id']).values_list('image_time',flat=True).first()
            return tattile_data.date().strftime("%Y-%m-%d")
        
        else:
            return datetime.now().strftime("%Y-%m-%d")
        
    @staticmethod
    def get_court_date(station_id):
        """
        Fetch and return court date.
        """
        court_date = CourtDates.objects.filter(station=station_id).values_list('id',flat=True).first()
        return court_date

    
    @staticmethod
    def save_citation_data(station_name,station_id, citation_id, person, vehicle, court_date, date_object, fields, speed_pic, plate_pic, fine_amount):
        """
        Save and return Citation data.
        """
        video_id = None
        image_id = None
        tattile_id=None
        station_citations = Citation.objects.filter(station__id=station_id)
        if station_citations.exists():
            latest_citation = station_citations.order_by("-citationID").values_list("citationID", flat=True).first()
            next_num = int(latest_citation.split("-")[-1]) + 1
        else:
            next_num = 1

        new_citation_number = f"{station_name}-{next_num:08d}"
        
        if fields['mediaType'] == 1:

            if fields['video_id'] != 0:
                video_id = fields['video_id']
            
            citation = Citation(
            id=Citation.objects.order_by("-id").first().id + 1 if Citation.objects.exists() else 1,
            person=person,
            station_id=station_id,
            vehicle=vehicle,
            video_id=video_id,
            image_id=image_id,
            location_id=fields['location_id'],
            court_date_id=court_date,
            fine_id=fields['fine_id'],
            citationID=new_citation_number,
            datetime=datetime.now(),
            posted_speed=fields['posted_speed'],
            speed=fields['violate_speed'],
            speed_pic=speed_pic,
            plate_pic=plate_pic,
            note=fields['note'],
            dist=fields['distance'],
            is_warning=fields['is_warning'],
            captured_date=date_object,
            isRejected=fields['is_rejected'],
            isSendBack=False,
            isRemoved=False,
            image_location = None,
            tattile_id=None,
            fine_amount=fine_amount
            )
            citation.save()
            return citation
        elif fields['mediaType'] == 2:
            if fields['image_id'] != 0:
                image_id = fields['image_id']
            citation = Citation(
                id=Citation.objects.order_by("-id").first().id + 1 if Citation.objects.exists() else 1,
                person=person,
                station_id=station_id,
                vehicle=vehicle,
                video_id=video_id,
                image_id=image_id,
                location_id=None,
                court_date_id=court_date,
                fine_id=fields['fine_id'],
                citationID=new_citation_number,
                datetime=datetime.now(),
                posted_speed=fields['posted_speed'],
                speed=fields['violate_speed'],
                speed_pic=speed_pic,
                plate_pic=plate_pic,
                note=fields['note'],
                dist=fields['distance'],
                is_warning=fields['is_warning'],
                captured_date=date_object,
                isRejected=fields['is_rejected'],
                isSendBack=False,
                isRemoved=False,
                image_location=fields['location_id'],
                tattile_id=None
            )
            citation.save()
            return citation

        ## this is for tattile
        elif fields['mediaType'] == 3:
            print(fields['distance'],"================================")
            if fields['tattile_id'] != 0:
                tattile_id = fields['tattile_id']
            citation = Citation(
                id=Citation.objects.order_by("-id").first().id + 1 if Citation.objects.exists() else 1,
                person=person,
                station_id=station_id,
                vehicle=vehicle,
                video_id=video_id,
                image_id=image_id,
                location_id=fields['location_id'],
                court_date_id=court_date,
                fine_id=fields['fine_id'],
                citationID=new_citation_number,
                datetime=datetime.now(),
                posted_speed=fields['posted_speed'],
                speed=fields['violate_speed'],
                speed_pic=speed_pic,
                plate_pic=plate_pic,
                note=fields['note'],
                dist=fields['distance'] if fields['distance'] else "",
                is_warning=fields['is_warning'],
                captured_date=date_object,
                isRejected=fields['is_rejected'],
                isSendBack=False,
                isRemoved=False,
                image_location=None,
                tattile_id=tattile_id,
                fine_amount=fine_amount
            )
            citation.save()
            return citation 
        

    @staticmethod
    def update_media_data(media_id, citation, fields,speed_pic,plate_pic):
        reject_id = fields['reject_id']
        if reject_id == 0:
            reject_id = None
        if fields['mediaType'] == 1:
            media = Video.objects.get(id=media_id)
            media.citation_id = citation.id
            media.isAdjudicated = fields['is_adjudicated']
            media.isRejected = fields['is_rejected']
            media.isSent = False
            media.isRemoved=False
            media.reject_id = reject_id if reject_id else None
            media.save()
        elif fields['mediaType'] == 2:
            media = Image.objects.get(id=media_id)
            media.speed_image_url = speed_pic
            media.lic_image_url = plate_pic
            media.citation_id = citation.id
            media.isAdjudicated = fields['is_adjudicated']
            media.isSent = False
            media.isRemoved=False
            media.isRejected = fields['is_rejected']
            media.reject_id = reject_id if reject_id else None
            media.save()
            
        ## this is for tattiles
        elif fields['mediaType'] == 3:
            media = Tattile.objects.get(id=media_id)
            media.speed_image_url = speed_pic
            media.license_image_url = plate_pic
            media.citation_id = citation.id
            media.is_adjudicated = fields['is_adjudicated']
            media.is_sent = False
            media.is_removed=False
            media.is_rejected = fields['is_rejected']
            media.reject_id = reject_id if reject_id else None
            media.save()

    @staticmethod
    def save_metadata(station_id, user, media_id ,fields ,citation):
        if fields['mediaType'] == 1:
            metadata = adj_metadata(
                station_id=station_id,
                user=user,
                video=Video.objects.get(id=media_id),
                image=None,
                citationID=citation.citationID,
                citation_id=citation.id,
                timeAdj=datetime.now(),
                isRemoved=False
            )
            metadata.save()
        elif fields['mediaType'] == 2:
            metadata = adj_metadata(
                station_id=station_id,
                user=user,
                video=None,
                image=Image.objects.get(id=media_id),
                citationID=citation.citationID,
                citation_id=citation.id,
                timeAdj=datetime.now(),
                isRemoved=False
            )
            metadata.save()
            
        ## this is for tattile
        elif fields['mediaType'] == 3:
            metadata = adj_metadata(
                station_id=station_id,
                user=user,
                video=None,
                image=None,
                citationID=citation.citationID,
                citation_id=citation.id,
                timeAdj=datetime.now(),
                isRemoved=False,
                tattile=Tattile.objects.get(id=media_id)
            )
            metadata.save()


    @staticmethod
    def get_video_id_for_adjudication(station_id, initial_video_id):

        video_data = Video.objects.filter(
            id=initial_video_id,
            station=station_id,
            isRejected=False,
            isRemoved=False
        ).first()
        print(video_data.id)

        return video_data.id if video_data.id else None
    
    @staticmethod

    def get_image_id_for_adjudication(station_id, initial_image_id):
        image_data = Image.objects.filter(
            station=station_id,
            id=initial_image_id,
            isRejected=False,
            isRemoved=False
        ).first()

        return image_data.id if image_data.id else None
    
    
    @staticmethod
    ## this is for tattile
    def get_tattile_id_for_adjudication(station_id, initial_image_id):
        tattile_data = Tattile.objects.filter(
            station=station_id,
            id=initial_image_id,
            isRejected=False,
            isRemoved=False
        ).first()

        return tattile_data.id if tattile_data.id else None


def update_existing_citation_data(fields, citationID, mediaType, videoId=None, imageId=None, 
                                  isAdjudicated=False, isSent=False, personId=None, vehicleId=None, station_id=None, tattileId=None,fine_amount=None):
    citation = Citation.objects.filter(citationID=citationID).first()
    if not citation:
        raise ValueError(f"No citation found with ID {citationID}")

    if mediaType == 1:
        video_data = Video.objects.filter(id=citation.video_id).first()
        video_data.isSent = False
        video_data.isAdjudicated = True
        video_data.save()
        citation.video_id = videoId
        citation.location_id = fields.get('locationId', citation.location_id)
        citation.plate_pic = generate_s3_file_name(mediaType, videoId, station_id, None, fields.get('platePic')) or citation.plate_pic
        citation.speed_pic = generate_s3_file_name(mediaType, videoId, station_id, fields.get('speedPic'), None) or citation.speed_pic
        meta_data = adj_metadata.objects.filter(citationID=citation.citationID).update(
            timeAdj = datetime.now(),
            isRemoved=False
        )
    elif mediaType == 2:
        image_data = Image.objects.filter(id=citation.image_id).first()
        image_data.isSent = False
        image_data.isAdjudicated = True
        image_data.save()
        citation.image_id = imageId
        citation.image_location = fields.get('location_id', citation.image_location)
        citation.plate_pic = generate_s3_file_name(mediaType, imageId, station_id, None, fields.get('platePic')) or citation.plate_pic
        citation.speed_pic = generate_s3_file_name(mediaType, imageId, station_id, fields.get('speedPic'), None) or citation.speed_pic
        meta_data = adj_metadata.objects.filter(citationID=citation.citationID).update(
            timeAdj = datetime.now(),
            isRemoved=False
        )
        
    ## this is for tattile
    elif mediaType == 3:
        tattile_data = Tattile.objects.filter(id=citation.tattile_id).first()
        tattile_data.is_sent = False
        tattile_data.is_adjudicated = True
        tattile_data.save()
        citation.tattile_id = tattileId
        citation.location_id = fields.get('location_id', citation.location_id)
        citation.plate_pic = generate_s3_file_name(mediaType, tattileId, station_id, None, fields.get('platePic')) or citation.plate_pic
        citation.speed_pic = generate_s3_file_name(mediaType, tattileId, station_id, fields.get('speedPic'), None) or citation.speed_pic
        meta_data = adj_metadata.objects.filter(citationID=citation.citationID).update(
            timeAdj = datetime.now(),
            isRemoved=False
        )
    

    if personId and citation.person_id == personId:
        Person.objects.filter(id=personId).update(
            first_name=fields.get('first_name', ''),
            middle=fields.get('middle_name', ''),
            last_name=fields.get('last_name', ''),
            phone_number=fields.get('phone_number', ''),
            address=fields.get('address', ''),
            city=fields.get('city', ''),
            state=fields.get('state_ab', ''),
            zip=fields.get('zip_code', '')
        )

    if vehicleId and citation.vehicle_id == vehicleId:
        Vehicle.objects.filter(id=vehicleId).update(
            year=fields.get('vehicle_year', ''),
            make=fields.get('make', ''),
            model=fields.get('model', ''),
            color=fields.get('color', ''),
            plate=fields.get('license_plate', ''),
            lic_state_id=fields.get('license_state_id', ''),
            vin=fields.get('vin_number', '')
        )

    video_id = fields.get('video_id') if fields['mediaType'] == 1 and fields.get('video_id', 0) != 0 else None
    image_id = fields.get('image_id') if fields['mediaType'] == 2 and fields.get('image_id', 0) != 0 else None
    tattile_id = fields.get('tattile_id') if fields['mediaType'] == 3 and fields.get('tattile_id', 0) != 0 else None
    citation.person_id = personId if personId else citation.person_id
    citation.station_id = station_id
    citation.vehicle_id = vehicleId if vehicleId else citation.vehicle_id
    citation.court_date_id = fields.get('court_date', citation.court_date_id)
    citation.fine_id = fields.get('fine_id', citation.fine_id)
    citation.datetime = datetime.now()
    citation.posted_speed = fields.get('posted_speed', citation.posted_speed)
    citation.speed = fields.get('violate_speed', citation.speed)
    citation.note = fields.get('note', citation.note)
    citation.dist = fields.get('distance') if fields.get('distance') is not None else " "
    citation.is_warning = fields.get('is_warning', citation.is_warning)
    citation.captured_date = fields.get('date_object', citation.captured_date)
    citation.isRejected = fields.get('is_rejected', citation.isRejected)
    citation.isSendBack = False
    citation.isRemoved=False
    citation.fine_amount = fine_amount if fine_amount is not None else citation.fine_amount
    citation.save()




def generate_s3_file_name(media_type, media_id, station_id, speed_pic=None, plate_pic=None):
    s3_bucket_prefix = "https://ee-prod-s3-bucket.s3.amazonaws.com/"
    if speed_pic and speed_pic.startswith(s3_bucket_prefix):
        return speed_pic.split("?")[0]
    if plate_pic and plate_pic.startswith(s3_bucket_prefix):
        return plate_pic.split("?")[0] 
    if media_type == 1:
        video_data = Video.objects.filter(id=media_id, station_id=station_id).first()
        print(video_data)
        if not video_data:
            raise ValueError("Video data not found for the given mediaId and stationId")
        date_now = datetime.now()
        formatted_date = date_now.strftime("%m%d%Y%H%M%S.%f")
        if speed_pic:
            file_data = base64.b64decode(speed_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{video_data.caption}_speed_{formatted_date}.png"
            speed_pic_url = upload_to_s3(file_obj, file_name, "images")
            return speed_pic_url
        
        elif plate_pic:
            file_data = base64.b64decode(plate_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{video_data.caption}_plate_{formatted_date}.png"
            plate_pic_url = upload_to_s3(file_obj, file_name, "images")
            return plate_pic_url
    elif media_type == 2:
        image_data = Image.objects.filter(id=media_id, station_id=station_id).first()
        print(image_data)
        if not image_data:
            raise ValueError("Image data not found for the given mediaId and stationId")
        date_now = datetime.now()
        formatted_date = date_now.strftime("%m%d%Y%H%M%S.%f")
        if speed_pic:
            file_data = base64.b64decode(speed_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{image_data.plate_image_filename}.png"
            speed_pic_url = upload_to_s3(file_obj, file_name, "PGM2/speed")
            return speed_pic_url
        
        elif plate_pic:
            file_data = base64.b64decode(plate_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{image_data.plate_image_filename}.jpg"
            plate_pic_url = upload_to_s3(file_obj, file_name, "PGM2/plates")
            return plate_pic_url
        
    ## this is for tattile
    elif media_type == 3:
        tattile_data = Tattile.objects.filter(id=media_id, station_id=station_id).first()
        if not tattile_data:
            raise ValueError("Image data not found for the given mediaId and stationId")
        date_now = datetime.now()
        formatted_date = date_now.strftime("%m%d%Y%H%M%S.%f")
        if speed_pic:
            file_data = base64.b64decode(speed_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{tattile_data.ticket_id}.png"
            speed_pic_url = upload_to_s3(file_obj, file_name, "PGM2/speed")
            return speed_pic_url
        
        elif plate_pic:
            file_data = base64.b64decode(plate_pic)
            file_obj = io.BytesIO(file_data)
            file_name = f"{tattile_data.ticket_id}.jpg"
            plate_pic_url = upload_to_s3(file_obj, file_name, "PGM2/plates")
            return plate_pic_url

    else:
        raise ValueError("Invalid media type")