from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import APIResponse, ServiceResponse
from rest_framework.views import APIView
from pre_odr_view.pre_odr_view_utils import *
from pre_odr_view.serializer import *
from drf_yasg import openapi


class UploadUnpaidCitationDataView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=UploadUnpaidCitationDataInputModel,
        tags=['PreODR'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = UploadUnpaidCitationDataInputModel(data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=400)    
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken    
        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')

        base64StringDocxFile = serializer.validated_data.get('base64StringDocxFile')
        base64StringTxtFile = serializer.validated_data.get('base64StringTxtFile')

        response_data = upload_unpaid_citation_data(base64StringDocxFile,base64StringTxtFile)

        return Response(response_data.data)
    

class SubmitPreOdrCitationView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=SubmitPreOdrCitationInputModel,
        tags=['PreODR'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = SubmitPreOdrCitationInputModel(data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=400)    
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken    
        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')
        user_id = readToken.get('user_id')
        agency_id = readToken.get('agencyId')

        citationIDs = serializer.validated_data.get("citationIDs")
        response = process_pre_odr_citation(citationIDs,station_id,user_id,station_name,agency_id)
        return response


class GetDataForPreOdrTableView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=GetDataForPreOdrTableInputModel,
        responses={200:GetDataForPreOdrResponseModel},
        tags=['PreODR'],
        security=[{'Bearer': []}]
    ) 
    def post(self,request):
        serializer = GetDataForPreOdrTableInputModel(data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=400)    
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        stationId = readToken.get('stationId')
        stationName = readToken.get('stationName')

        pageIndex = serializer.validated_data.get('pageIndex')
        pageSize = serializer.validated_data.get('pageSize')
        searchString = serializer.validated_data.get('searchString')
        fromDate = serializer.validated_data.get('fromDate')
        toDate = serializer.validated_data.get('toDate')

        query_result = get_data_for_pre_odr_table(fromDate,toDate,searchString,pageIndex,pageSize,stationId)
        citations = query_result['data']
        total_records = query_result['total_records']
        
        serialized_data = GetDataForPreOdrResponseModel(citations, many=True).data

        paged_response = PagedResponse(
            page_index=pageIndex,
            page_size=pageSize,
            total_records=total_records,
            data=serialized_data
        )
        
        response_data = {
            "data": paged_response.data,
            "pageIndex": paged_response.pageIndex,
            "pageSize": paged_response.pageSize,
            "totalRecords": paged_response.totalRecords,
            "hasNextPage": paged_response.hasNextPage,
            "hasPreviousPage": paged_response.hasPreviousPage,
            "statusCode": 200,
            "message": "Success"
        }
        if paged_response.data is None:
            return Response(ServiceResponse({
                "statusCode" : 204,
                "message" : "No content",
                "data" : None
            }).data,status=200)
        
        return Response(response_data)
    

class GetCSVDataForPreOdrView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        responses={200: GetPreOdrCSVViewResponseModel(many=True)},
        tags=['PreODR'],
        security=[{'Bearer': []}]
    )
    def get(self,request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        stationId = readToken.get('stationId')

        response_data = get_pre_odr_data_for_csv(stationId)
        if response_data:
            return Response(ServiceResponse({"statusCode":200, "message":"Success", "data": GetPreOdrCSVViewResponseModel(response_data,many=True).data}).data, status=200)
        else:
            return Response(ServiceResponse({"statusCode":204, "message":"No content", "data": []}).data, status=200)
        
        
class ViewMailerPDFView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=GetMailerPDFBase64StringInputModel,
        responses={200 : GetMailerPDFBase64StringOutputModel},
        tags=['PreODR'],
        security=[{'Bearer': []}]
    )
    def post(self,request):
        serializer = GetMailerPDFBase64StringInputModel(data=request.data,partial=True)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=400)    
        readToken = user_information(request)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        stationId = readToken.get('stationId')
        agencyId = readToken.get('agencyId')
        mailerType = serializer.validated_data.get('mailerType')
        citationID = serializer.validated_data.get('citationID')
        
        if mailerType == 1:
            return get_first_mailer_pdf(stationId,citationID,agencyId) 
        elif mailerType == 2:
            return get_second_mailer_pdf(stationId,citationID,agencyId) 
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid mailer type"
            }).data, status=200)
        
        
class DelectUnpaidCitationDataView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'unpaidCitationId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],  
        responses={200 : APIResponse,
                   400 : APIResponse},
        tags=['PreODR'],
        security=[{'Bearer': []}]
    )
    def delete(self,request):
        unpaidCitationId = request.query_params.get('unpaidCitationId', None)

        try:
            unpaidCitationId = int(unpaidCitationId) if unpaidCitationId is not None else 1
        except ValueError:
            return Response({
                "statusCode": 400,
                "message": "Invalid requestType. Must be an integer."
            }, status=400)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        return delete_unpaid_citation_data(unpaidCitationId)
        