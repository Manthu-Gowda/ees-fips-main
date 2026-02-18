from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import ServiceResponse
from rest_framework.views import APIView
from .odr_utils import get_pdf_base64, create_pdf, get_odr_data_for_csv, save_odr_csv_data, save_odr_csv_meta_data, \
    citation_data_for_odr_approved_table, citation_data_for_odr_approved_table_download
data_agencies = Data.objects.all()
from drf_yasg import openapi
from video.views import get_cit_refactor
from io import StringIO
import csv
import base64
from datetime import date, timedelta
class ViewODRPDF(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'citationId',
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER
            )
        ],  
        responses={200 : GetOdrPDFBase64StringOutputModel},
        tags=['OdrView'],
        security=[{'Bearer': []}]
    )
    def get(self, request):
        citation_id = request.query_params.get('citationId', None)

        try:
            citation_id = int(citation_id) if citation_id is not None else 1
        except ValueError:
            return Response({
                "statusCode": 400,
                "message": "Invalid requestType. Must be an integer."
            }, status=400)
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        
        station_id = readToken.get('stationId')
        station_name = readToken.get('stationName')

        citation_data = Citation.objects.filter(id=citation_id,station_id=station_id).first()
        citation_ID = str(citation_data.citationID)
        base64String = ""
        if citation_data.video_id:
            data = get_cit_refactor(citation_ID,station_id,image_flow=False)
            filename = f"{citation_ID}.pdf"
            create_pdf(filename, data, station_name)
            base64String = get_pdf_base64(filename)    
        elif citation_data.image_id:
            data = get_cit_refactor(citation_ID,station_id,image_flow=True)
            filename = f"{citation_ID}.pdf"
            create_pdf(filename, data, station_name)
            get_pdf_base64(filename)
            base64String = get_pdf_base64(filename)

        return Response(ServiceResponse({
                "statusCode" : 200,
                "message" : "Success",
                "data" : base64String
        }).data, status=200)
        
class GetOdrCsvDataView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: GetOdrCSVViewOutputModel(many=True)},
        tags=['OdrView'],
    )
    def get(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        station_id = readToken.get('stationId')
        response_data = get_odr_data_for_csv(station_id)
        if response_data:
            return Response(ServiceResponse({"statusCode":200, "message":"Success", "data": GetOdrCSVViewOutputModel(response_data,many=True).data}).data, status=200)
        else:
            return Response(ServiceResponse({"statusCode":204, "message":"No content", "data": []}).data, status=200)
        
        
class OdrCitationSubmitView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body = OdrCitationStatusUpdateInputModel,
        responses={200: OdrApprovedCitationIDsOutputModel},
        tags=['OdrView'],
        security=[{'Bearer' : []}]
    )
    
    def post(self, request):
        serializer = OdrCitationStatusUpdateInputModel(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data" : serializer.errors
            }).data, status=200)
        
        serializer_data = serializer.validated_data
        citation_ids = serializer_data.get('citationIds')
        is_approved = serializer_data.get('isApproved')
        user_id = readToken.get('user_id')
        user_station_id = readToken.get('stationId')
        
        print(citation_ids, 'citation_ids')
        
        citation_data = UnpaidCitation.objects.filter(id__in=citation_ids)
        already_approved_citations = citation_data.filter(isApproved=True)
        print(citation_data, 'citation_data')
        if already_approved_citations.exists():
            approved_ids = already_approved_citations.values_list('citation__citationID', flat=True)
            return Response(ServiceResponse({
                "statusCode": 409,
                "message": f"These Citations are already approved and cannot be updated. Please choose valid CitationIDs",
                "data" : OdrApprovedCitationIDsOutputModel({"citationID" : approved_ids}).data
            }).data, status=200)
        
        for citation in citation_data:
            quick_pd_id = save_odr_csv_data(citation.ticket_number, user_station_id)
            citation.isApproved = is_approved
            odr_due_date = date.today() + timedelta(days=60)
            citation.odr_due_date = odr_due_date
            citation.save()
            
            save_odr_csv_meta_data(quick_pd_id,citation.id,user_id,citation.station_id)
            stationName = Station.objects.filter(id=citation.station_id).values_list('name',flat=True).first()
            # try:
            #     create_odr_csv_and_pdf_data(citation.citationID,citation.station_id,stationName,image_flow = False)
            # except:
            #     return Response(APIResponse({
            #         "statusCode" : 400,
            #         "message" : "Citation id did not process successfully.",
            #         "data" : []
            #     }).data,status=200)

        status_messages = []
        if is_approved:
            status_messages.append("approved")
            
        update_message = "Citations have been "+ "".join(status_messages) + " successfully."   
        return Response(ServiceResponse({
            "statusCode" : 200,
            "message" : update_message,
            "data" : []
        }).data,status=200)
        
class GetOdrApprovedTableView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=GetOdrCitationDataInputModel,
        responses={200: GetOdrCitationData(many=True)},
        tags=['OdrView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetOdrCitationDataInputModel(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)
        station_id = readToken.get('stationId')
        serializer_data = serializer.validated_data

        from_date = serializer_data.get('fromDate')
        to_date = serializer_data.get('toDate')
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)
        
        query_result = citation_data_for_odr_approved_table(from_date, to_date, search_string, page_index, page_size,station_id)

        citations = query_result['data']
        total_records = query_result['total_records']
        
        serialized_data = GetOdrCitationData(citations, many=True).data

        paged_response = PagedResponse(
            page_index=page_index,
            page_size=page_size,
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
    
class DownloadOdrApprovedTableDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=GetOdrCitationDataInputModel,
        responses={200: GetOdrCSVBase64StringOutputModel},
        tags=['OdrView'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetOdrCitationDataInputModel(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)
        station_id = readToken.get('stationId')
        serializer_data = serializer.validated_data

        from_date = serializer_data.get('fromDate')
        to_date = serializer_data.get('toDate')
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)

        query_result = citation_data_for_odr_approved_table_download(from_date, to_date, search_string, page_index, page_size,station_id)
        if query_result["total_records"]:
            csv_output = StringIO()
            csv_writer = csv.DictWriter(csv_output, fieldnames=["Citation ID", "Video/Image ID", "Fine", "Full Name","Captured Date", "Initial Due Date", "ODR Fine", "ODR Mail Count", "ODR Due Date"])
            csv_writer.writeheader()
            for row in query_result["data"]:
                csv_writer.writerow(row)
            csv_output.seek(0)
            csv_content = csv_output.getvalue()
            csv_base64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            return Response(ServiceResponse({"statusCode":200, "message": "Sucess", "data": GetOdrCSVBase64StringOutputModel({ "base64String" : csv_base64}).data}).data, status=200)
        else:
           return Response(ServiceResponse({"statusCode":204, "message": "No content", "data": []}).data, status=200)