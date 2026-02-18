from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from .serializers import *
from accounts_v2.serializer import ServiceResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from ees.utils import user_information
from .csv_view_utils import get_data_for_csv


class GetQuickPDDataView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: GetCSVViewOutputModel(many=True)},
        tags=['CSVView'],
    )
    def get(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_id = readToken.get('stationId')
        response_data = get_data_for_csv(station_id)
        if response_data:
            return Response(ServiceResponse({"statusCode":200, "message":"Success", "data": GetCSVViewOutputModel(response_data,many=True).data}).data, status=200)
        else:
            return Response(ServiceResponse({"statusCode":204, "message":"No content", "data": []}).data, status=200)

