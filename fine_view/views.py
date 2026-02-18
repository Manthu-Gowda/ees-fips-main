from video.models import Fine
from rest_framework.permissions import IsAuthenticated
from .serializers import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import ServiceResponse
from rest_framework.views import APIView

class GetAllFineDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses= {200 : GetAllFineDetailsResponseModel(many=True)},
        tags=['Fine'],
        security=[{'Bearer': []}]
    )
    def get(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_id = readToken.get('stationId')
        fine_data = Fine.objects.filter(station_id=station_id).all()
        response_data = [{
            "fineId" : fine.id,
            "speedDifference" : fine.speed_diff,
            "fineAmount" : fine.fine,
            "stateRS" : fine.rs_code,
            "isSchoolZone" : fine.isSchoolZone,
            "isConstructionZone" : fine.isConstructionZone
        }
        for fine in fine_data]

        if response_data:
            return Response(ServiceResponse({"statusCode":200, "message":"Sucess", "data":GetAllFineDetailsResponseModel(response_data,many=True).data}).data, status=200)
        
        return Response(ServiceResponse({"statusCode":204, "message":"No content", "data":[]}).data, status=200)
    

class UpdateFineDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body= serializers.ListSerializer(child=UpdateFineDetailsInputModel()),
        responses={200: MissingFineIdsResponseModel(many=True)},
        tags=['Fine'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        serializer = UpdateFineDetailsInputModel(data=request.data)
        serializer = serializers.ListSerializer(
            child=UpdateFineDetailsInputModel(),
            data=request.data,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        fine_details_list = serializer.validated_data
        fine_ids = [fine['fineId'] for fine in fine_details_list]
        stationId = readToken.get('stationId')
        existing_fines = Fine.objects.filter(id__in=fine_ids,station_id=stationId).values_list('id', flat=True)

        missing_fine_ids = set(fine_ids) - set(existing_fines)
        if missing_fine_ids:
            missing_ids_response = MissingFineIdsResponseModel(data={"fineId": list(missing_fine_ids)}, many=False)
            if not missing_ids_response.is_valid():
                return Response(missing_ids_response.errors, status=400)
            return Response(ServiceResponse({"statusCode":400, "message": "The following fine IDs do not exist", "data":missing_ids_response.validated_data}).data, status=200)
        
        for fine in fine_details_list:
            fine_obj = Fine.objects.get(id=fine['fineId'])
            fine_obj.fine = fine.get('fineAmount', fine_obj.fine)
            fine_obj.rs_code = fine.get('stateRS', fine_obj.rs_code)
            fine_obj.save()

        return Response(ServiceResponse({"statusCode":200, "message":"Fine details updated successfully", "data":[]}).data, status=200)