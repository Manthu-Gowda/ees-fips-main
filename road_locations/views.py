from video.models import road_location
from rest_framework.permissions import IsAuthenticated
from .serializers import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from rest_framework.views import APIView
from drf_yasg import openapi
from .road_location_utils import *


class GetAllRoadLocationsDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses= {200 : GetAllRoadLocationsResponseModel(many=True)},
        tags=['RoadLocation'],
        security=[{'Bearer': []}]
    )
    def get(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get('stationId')
        road_locations_data = road_location.objects.filter(station_id=station_id).order_by("LOCATION_CODE")
        response_data = [{
            "locationId" : location.id,
            "locationCode" : location.LOCATION_CODE,
            "locationName" : location.location_name,
            "postedSpeed" : location.posted_speed,
            "isSchoolZone" : location.isSchoolZone,
            "isTrafficLogixLocation" : location.isTrafficLogix,
            "trafficLogixLocationId" : location.trafficlogix_location_id,
            "isConstructionZone" : location.isConstructionZone
        }
            for location in road_locations_data]
        
        if road_locations_data:
            return Response(ServiceResponse({
                "statusCode" : 200,
                "message" : "Success",
                "data" : GetAllRoadLocationsResponseModel(response_data,many=True).data
            }).data, status=200)
        else:
            return Response(ServiceResponse({
                "statusCode" : 204,
                "message" : "No content",
                "data" : []
            }).data, status=200)
        

class AddOrUpdateRoadLocationDetailsView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
            manual_parameters=[
            openapi.Parameter(
                'locationId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        request_body=AddOrUpdateRoadLocationInputModel,
        tags=['RoadLocation'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        locationId = request.query_params.get('locationId', None)

        try:
            locationId = int(locationId) if locationId is not None else None
        except ValueError:
            return Response(APIResponse({"statusCode": 400,"message": "Invalid locationId. Must be an integer."}).data, status=400)
        print(locationId)
        serializer = AddOrUpdateRoadLocationInputModel(data=request.data)

        if not serializer.is_valid():
            return Response({"statusCode": 400,"message": "Invalid input data","errors": serializer.errors}, status=400)
        
        station_id = readToken.get('stationId')
        
        extracted_fields = extracted_input_fields(serializer.validated_data)
        if not locationId:
            response = add_road_location(extracted_fields,station_id)
            return Response(APIResponse({"statusCode":201,"message":response}).data,status=200)
        else:
            response = update_road_location_details(extracted_fields,station_id,locationId)
            return Response(APIResponse({"statusCode":200,"message":response}).data,status=200)
        

class DeleteRoadLocationDetailsView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
            manual_parameters=[
            openapi.Parameter(
                'locationId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],
        tags=['RoadLocation'],
        security=[{'Bearer': []}]
    )
    def delete(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        locationId = request.query_params.get('locationId', None)

        try:
            locationId = int(locationId) if locationId is not None else None
        except ValueError:
            return Response(APIResponse({"statusCode": 400,"message": "Invalid locationId. Must be an integer."}).data, status=400)
        station_id = readToken.get('stationId')
        existing_road_location = road_location.objects.filter(id=locationId,station_id=station_id).first()
        if existing_road_location:
            existing_road_location.delete()
            return Response(APIResponse({"statusCode":200,"message":f"Road Location with Id : {locationId} deleted successfully"}).data, status=200)
        else:
            return Response(APIResponse({"statusCode":404,"message":f"Road Location with Id : {locationId} does not exists"}).data, status=200)




    

        
            