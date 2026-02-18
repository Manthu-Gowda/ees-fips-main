from video.models import CourtDates, Agency
from rest_framework.permissions import IsAuthenticated
from .serializers import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from rest_framework.views import APIView


class AddCourtDateView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=AdCourtDateInputModel,
        tags=['Court'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        serializer = AdCourtDateInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","errors": serializer.errors}).data, status=400)
        
        serializer_data = serializer.validated_data
        court_date_title = serializer_data.get("courtDateTitle")
        date = serializer_data.get("date")
        stationId = readToken.get('stationId')
        agency_location = Agency.objects.filter(station_id=stationId).values("location").first() 
        if CourtDates.objects.filter(date_string=court_date_title,c_date=date,station_id=stationId).first():
            return Response(APIResponse({"statusCode":409, "message": f"Court date {date} with speed difference {court_date_title} already exists"}).data, status=200)
        
        new_court_data = CourtDates.objects.create(
            date_string = court_date_title,
            c_date = date,
            station_id = stationId,
            location = agency_location
        )
        return Response(APIResponse({"statusCode":201,"message": f"Court Date {court_date_title} added successfully."}).data, status=200)