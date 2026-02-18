# import cv2
# import easyocr
# import datetime


# import cv2
# import numpy as np

# from ees.utils import create_presigned_url, url_to_image, extract_s3_key_from_url, read_image_from_s3_url
# reader = easyocr.Reader(["en"])





# def OCRImage(image_path):
#     """
#     OCRs a Image to return time, speed, and the distance

#     Parameters:
#     image_path (str): The image with the path that it is coming from

#     Returns:
#     dict: A list with time, speed, and distance that are all strings
#     """

#     global reader
#     img = read_image_from_s3_url(image_path)

#     # Crop time
#     crop_time = img[0:22, 0:108]

#     # Crop speed
#     crop_speed = img[58:105, 520:640]

#     # Crop distance
#     crop_distance = img[555:573, 380:462]

#     # Crop being OCR-ed - crop_image to text
#     time = reader.readtext(crop_time, detail=0)
#     speed = reader.readtext(crop_speed, detail=0)
#     distance = reader.readtext(crop_distance, detail=0)

#     time1 = None

#     # Fix the time...
#     for fmt in ("%H:%M.%S", "%H.%M:%S", "%H.%M.%S", "%H:%M:%S"):
#         try:
#             time1 = datetime.datetime.strptime(str(time[0]), fmt)
#         except ValueError:
#             pass

#     # Returning values
#     speed.append("0")
#     distance.append("0")
#     if time1 is None:
#         time1 = datetime.time(0, 0, 0)

#     query = {
#         "time": time1.strftime("%H%M%S"),
#         "speed": speed[0],
#         "distance": distance[0],
#     }
#     return query
