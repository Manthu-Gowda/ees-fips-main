from video.citations.versioning_utils import append_new_version, format_us_date, get_snapshot_by_version
from video.models import *
from rest_framework.permissions import IsAuthenticated
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from ees.utils import user_information
from rest_framework.response import Response
from accounts_v2.serializer import ServiceResponse
from rest_framework.views import APIView
from drf_yasg import openapi
from .approved_table_utils import *
from video.views import get_cit_refactor,get_original_cit_refactor_approved_table
from .approved_table_utils import create_pdf
import csv
import base64
from io import StringIO
from supervisor_view.supervisor_utils import create_refactor_csv,save_csv_meta_data,create_csv_and_pdf_data,update_quick_pd_data

class GetCitationDataForApprovedTableView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=GetCitationDataInputModel,
        responses={200: GetCitationData(many=True)},
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetCitationDataInputModel(data=request.data)
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
        station_name = readToken.get('stationName')

        date_type = serializer_data.get('dateType')
        from_date = serializer_data.get('fromDate')
        to_date = serializer_data.get('toDate')
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)
        paid_filter = serializer_data.get('paidFilterType',1)
        edit_filter = serializer_data.get('editFilterType',1)
        fine_amount = serializer_data.get('fine_amount', None)

        # query_result = citation_data_for_approved_table(date_type,from_date, to_date, search_string, page_index, page_size,station_id,isDownload=False)
        query_result = citation_data_for_approved_table(date_type,from_date, to_date, search_string, page_index, 
                                                        page_size,station_id,isDownload=False,paid_filter=paid_filter,edit_filter=edit_filter,fine_amount=fine_amount)
        citations = query_result['data']
        total_records = query_result['total_records']
        
        serialized_data = GetCitationData(citations, many=True).data

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
    

class ViewPDF(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('citationId', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter('citationVersion', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={200: GetPDFBase64StringOutputModel},
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def get(self, request):

        citation_id = request.query_params.get("citationId")
        citation_version = request.query_params.get("citationVersion")

        if not citation_id or not citation_version:
            return Response({
                "statusCode": 400,
                "message": "citationId and citationVersion are required"
            }, status=400)

        citation_id = int(citation_id)
        citation_version = int(citation_version)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        station_id = readToken.get("stationId")
        station_name = readToken.get("stationName")

        citation = Citation.objects.filter(
            id=citation_id,
            station_id=station_id
        ).first()

        if not citation:
            return Response({
                "statusCode": 404,
                "message": "Citation not found"
            }, status=404)

        # 🔹 Fetch snapshot
        version_data = get_snapshot_by_version(citation, citation_version)
        if not version_data:
            return Response({
                "statusCode": 404,
                "message": "Version not found"
            }, status=404)

        snapshot = version_data["snapshot"]
        status = version_data["status"]
        citation_ID = citation.citationID
        if citation.video_id:
            pdf_data = get_cit_refactor(citation_ID, station_id, status, image_flow=False)
        elif citation.image_id:
            pdf_data = get_cit_refactor(citation_ID, station_id, status, image_flow=True)
        elif citation.tattile_id:
            pdf_data = get_cit_refactor(citation_ID, station_id, status, image_flow=False, is_tattile=True)
        else:
            return Response({
                "statusCode": 400,
                "message": "No media found for citation"
            }, status=400)
        
        pdf_data = patch_pdf_data_from_snapshot(pdf_data, snapshot)
        if status == 'OR':
            pdf_data["cit"]["fine"] = pdf_data['cit']['fine_amount']
        filename = f"{citation_ID}_v{citation_version}.pdf"
        create_pdf(filename, pdf_data, station_name)
        base64String = get_pdf_base64(filename)

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": base64String
        }).data, status=200)
    

class DownloadApprovedTableDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=GetCitationDataInputModel,
        responses={200: GetCSVBase64StringOutputModel},
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetCitationDataInputModel(data=request.data)
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

        date_type = serializer_data.get('dateType')
        from_date = serializer_data.get('fromDate')
        to_date = serializer_data.get('toDate')
        search_string = serializer_data.get('searchString', None)
        page_index = serializer_data.get('pageIndex', 1)
        page_size = serializer_data.get('pageSize', 10)
        paid_filter = serializer_data.get('paidFilterType',1)
        edit_filter = serializer_data.get('editFilterType',1)
        fine_amount = serializer_data.get('fine_amount',None)
        
        query_result = citation_data_for_approved_table(date_type,from_date, to_date, search_string, page_index, page_size,station_id,isDownload=True,paid_filter=paid_filter,edit_filter=edit_filter, fine_amount= fine_amount)
        # query_result = citation_data_for_approved_table(date_type,from_date, to_date, search_string, page_index, page_size,station_id,isDownload=True)
        print(query_result)
        if query_result["total_records"]:
            csv_output = StringIO()
            csv_writer = csv.DictWriter(csv_output, fieldnames=["citationId", "citationID", "mediaId", "fine", "speed", "locationCode","locationName", "firstName", "lastName", "state", "plate","capturedDate", "approvedDate", "citationStatus","paidStatus","address"])
            csv_writer.writeheader()
            for row in query_result["data"]:
                csv_writer.writerow(row)
            csv_output.seek(0)
            csv_content = csv_output.getvalue()
            csv_base64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            return Response(ServiceResponse({"statusCode":200, "message": "Sucess", "data": GetCSVBase64StringOutputModel({ "base64String" : csv_base64}).data}).data, status=200)
        else:
           return Response(ServiceResponse({"statusCode":204, "message": "No content", "data": []}).data, status=200) 

class EditApprovedTableDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=EditCitationDataInputModel,
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        serializer = EditCitationDataInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)
        serializer_data = serializer.validated_data
        citation_id = serializer_data.get('citationId')
        editType = serializer_data.get('editType')
        user_id = readToken.get('user_id')
        
        QUICKPD_STATIONS = ['MAR',"CLA","OIL","ROB","EST","RNG"]
        XPRESS_BILL_PAY_STATIONS = ['FED-M',"HUD-C","WBR2","FPLY-C","KRSY-C"]
        citation_object = Citation.objects.filter(id=citation_id).first()
        citation_id = citation_object.citationID
        user = User.objects.filter(id=user_id).first()
        station_name = citation_object.station.name
        payment_status_check = PaidCitationsData.objects.filter(citationID = citation_id).exists()
        if payment_status_check:
            return Response(ServiceResponse({"statusCode":400, "message": f"Editing is not allowed for Citation {citation_id} as it has been marked as paid.."}).data, status=200)
        if editType == 1:
            # Paid In House Flow

            # if station uses QUICKPD save paid data to quickpd paid citations table else save to paid citations table
            if station_name in QUICKPD_STATIONS:
                quickpd_paid_citations = QuickPdPaidCitations.objects.filter(ticket_number=citation_id).first()
                if quickpd_paid_citations:
                    return Response(ServiceResponse({"statusCode":200, "message": "Sucess", "data": "Citation is already paid"}).data, status=200)
                else:
                    quickpd_paid_citations = QuickPdPaidCitations.objects.create(
                        ticket_number=citation_id,
                        paid_date=timezone.now(),
                        batch_date=timezone.now(),
                        first_name=citation_object.person.first_name,
                        last_name=citation_object.person.last_name,
                        total_paid = citation_object.fine.fine,
                        video = citation_object.video,
                        image = citation_object.image,
                        tattile = citation_object.tattile,
                        station = citation_object.station,
                        ees_amount = 0
                        )
                    quickpd_paid_citations.save()

            if station_name in XPRESS_BILL_PAY_STATIONS:
                paid_citations = PaidCitationsData.objects.filter(citationID=citation_id).first()
                if paid_citations:
                    return Response(ServiceResponse({"statusCode":200, "message": "Citation is already paid" }).data, status=200)
                else:
                    now = timezone.now()

                    # Format the current time as YYYYMMDDHHMM
                    timestamp_str = now.strftime('%Y%m%d%H%M')

                    # Create the transaction ID
                    transaction_id = f"PIH-{timestamp_str}-{citation_id}"
                    paid_citations = PaidCitationsData.objects.create(
                        transaction_id = transaction_id,
                        citationID=citation_id,
                        transaction_date=timezone.now(),
                        full_name=citation_object.person.first_name + citation_object.person.last_name,
                        paid_amount = citation_object.fine.fine,
                        video = citation_object.video,
                        image = citation_object.image,
                        tattile = citation_object.tattile
                        )
                    paid_citations.save()

            save_citation_edit_log(citation_object, user, "PIH")
            
            citation_object.current_citation_status = "PIH"
            citation_object.edited_by = user
            citation_object.citation_edited_at = timezone.now()
            citation_object.save()

            append_new_version(
                citation=citation_object,
                new_status="PIH",
            )

            # notify express bill pay as paid - code to be written
            return Response(ServiceResponse({"statusCode":200, "message": "Citation marked as paid in house successfully"}).data, status=200)
        
        if editType == 2:
            # Return To Sender, Unknown address
            duncan_master_object = DuncanMasterData.objects.filter(
                lic_plate=citation_object.vehicle.plate,
                state=citation_object.vehicle.lic_state.ab).last()
            
            if duncan_master_object:
                duncan_master_object.is_invalid_address = True

                citation_object.current_citation_status = "RTS"
                citation_object.edited_by = user
                citation_object.citation_edited_at = timezone.now()

                duncan_master_object.save()
                citation_object.save()
                save_citation_edit_log(citation_object, user, "RTS")

                append_new_version(
                    citation=citation_object,
                    new_status="RTS",
                )

                return Response(ServiceResponse({"statusCode":200, "message": "Citation marked as return to sender successfully"}).data, status=200)
            else:
                return Response(ServiceResponse({"statusCode": 404, "message": "Plate not found in duncan master table."}).data,status= 200)

class UpdateApprovedTableData(APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=UpdateCitationDataInputModel,
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = UpdateCitationDataInputModel(data=request.data)
        readToken = user_information(request)
        
        if isinstance(readToken, Response):
            return readToken
        
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)
        serializer_data = serializer.validated_data

        citation_id = serializer_data.get('citationId')
        editType = serializer_data.get('editType')
        user_id = readToken.get('user_id')
        new_fine_amount = serializer_data.get('fine')
        
        citation_object = Citation.objects.filter(id=citation_id).first()
        citation_id = citation_object.citationID
        user = User.objects.filter(id=user_id).first()
        station_name = citation_object.station.name
        payment_status_check = PaidCitationsData.objects.filter(citationID = citation_id).exists()
        if payment_status_check:
            return Response(ServiceResponse({"statusCode":400, "message": f"Editing is not allowed for Citation {citation_id} as it has been marked as paid.."}).data, status=200)
        if editType == 1:
            # update address
            duncan_master_object = DuncanMasterData.objects.filter(
                lic_plate=citation_object.vehicle.plate,
                state=citation_object.vehicle.lic_state.ab).last()
            
            if duncan_master_object:
                # cwua = CitationsWithUpdatedAddress(
                #     citation=citation_object,
                #     updated_address = serializer_data.get('address',""),
                #     updated_person_state = serializer_data.get('state',""),
                #     updated_zip = serializer_data.get('zip',""),
                #     updated_city = serializer_data.get('city',""),
                #     old_address = citation_object.person.address,
                #     old_person_state = citation_object.person.state,
                #     old_zip = citation_object.person.zip,
                #     old_city = citation_object.person.city,
                #     station = citation_object.station,
                #     is_citation_address_updated = True
                # )

                duncan_master_object.is_invalid_address = False
                duncan_master_object.is_address_updated = True
                duncan_master_object.address  = serializer_data.get('address',"")
                duncan_master_object.person_state  = serializer_data.get('state',"")
                duncan_master_object.zip  = serializer_data.get('zip',"")
                duncan_master_object.city  = serializer_data.get('city',"")

                person = Person.objects.filter(id=citation_object.person.id).first()
                person.address = serializer_data.get('address',"")
                person.state = serializer_data.get('state',"")
                person.zip = serializer_data.get('zip',"")
                person.city = serializer_data.get('city',"")

            
                citation_object.current_citation_status = "UA"
                citation_object.edited_by = user
                citation_object.citation_edited_at = timezone.now()

                # cwua.save()
                person.save()
                duncan_master_object.save()
                citation_object.save()
                save_citation_edit_log(citation_object, user, "UA")

                append_new_version(
                citation=citation_object,
                new_status="UA",
                snapshot_overrides={
                    "person": {
                        "first_name": person.first_name,
                        "last_name": person.last_name,
                        "address": person.address,
                        "city": person.city,
                        "state": person.state,
                        "zip": person.zip,
                        "phone_number": person.phone_number,
                    }
                }
            )
                # update supervisor metadata with new approved date
                
                # SAVE DATA TO QUiCK PD And get quick pd id
                try:
                    note = ""
                    update_supervisor_metadata(citation_object, user)
                    quick_pd_id = update_quick_pd_data(citation_object.id, note)
                    save_csv_meta_data(quick_pd_id, citation_object.id,user_id, citation_object.station_id)
                    if citation_object.video_id:
                        create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = False)
                    elif citation_object.image_id:
                        create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = True)
                    elif citation_object.tattile_id:
                        create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = False,is_tattile=True)
                except Exception as e:
                    print(e)
                # notify express bill pay or quick pd
                return Response(ServiceResponse({"statusCode":200, "message": "Citation marked as updated address successfully."}).data, status=200)
            
            else:
                return Response(ServiceResponse({"statusCode": 404, "message": "Plate not found in duncan master table."}).data,status= 200)
    
        elif editType == 2:
            # Transfer of Liability
            duncan_master_object = DuncanMasterData.objects.filter(
                lic_plate=citation_object.vehicle.plate,
                state=citation_object.vehicle.lic_state.ab).last()

            
            duncan_master_object.is_invalid_address = False
            duncan_master_object.is_address_updated = True
            duncan_master_object.save()
            # create a new person

            new_person = Person(
                first_name = serializer_data.get('firstName',""),
                middle = serializer_data.get('middleName',""),
                last_name = serializer_data.get('lastName',""),
                phone_number = serializer_data.get('phoneNumber',""),
                address = serializer_data.get('address',""),
                city = serializer_data.get('city',""),
                state = serializer_data.get('state',""),
                zip = serializer_data.get('zip',""),
                station = citation_object.station
                )
            
            new_person.save()

            # cwtol = CitationsWithTransferOfLiabilty(
            #     station = citation_object.station,
            #     is_citation_transfer_of_liabilty = True,
            #     citation = citation_object,
            #     old_person = citation_object.person,
            #     new_person = new_person
                
            # )
            # cwtol.save()
            citation_object.person = new_person
            citation_object.person = new_person
            citation_object.current_citation_status = "TL"
            citation_object.edited_by = user
            citation_object.citation_edited_at = timezone.now()
            citation_object.save()
            save_citation_edit_log(citation_object, user, "TL")

            append_new_version(
                citation=citation_object,
                new_status="TL",
                snapshot_overrides={
                    "person": {
                        "first_name": new_person.first_name,
                        "last_name": new_person.last_name,
                        "address": new_person.address,
                        "city": new_person.city,
                        "state": new_person.state,
                        "zip": new_person.zip,
                        "phone_number": new_person.phone_number,
                    }
                }
            )

            # SAVE DATA TO QUiCK PD And get quick pd id
            note = ""
            update_supervisor_metadata(citation_object, user)
            quick_pd_id = update_quick_pd_data(citation_object.id, note)
            save_csv_meta_data(quick_pd_id, citation_object.id,user_id, citation_object.station_id)
            if citation_object.video_id:
                create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = False)
            elif citation_object.image_id:
                create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = True)
            elif citation_object.tattile_id:
                create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = False,is_tattile=True)


            # generate new pdf/csv and notify xpress bill pay or quick pd based on station
            return Response(ServiceResponse({"statusCode":200, "message": "Citation marked as transfer of liability successfully"}).data, status=200)
    
        elif editType == 3:
            # Edit fine

            citation_object.current_citation_status = "EF"
            citation_object.edited_by = user
            citation_object.citation_edited_at = timezone.now()

            # CitationsWithEditFine(
            #     station = citation_object.station,
            #     is_citation_fine_edited = True,
            #     citation = citation_object,
            #     old_fine = citation_object.fine,
            #     new_fine = serializer_data.get('fine')
            # ).save()

            citation_object.save()

            save_citation_edit_log(citation_object, user, "EF")

            append_new_version(
            citation=citation_object,
            new_status="EF",
            snapshot_overrides={
                "fine": {
                    "id": citation_object.fine.id,
                    "amount": float(new_fine_amount), 
                }
            }
        )

            # SAVE DATA TO QUiCK PD And get quick pd id
            note = ""
            update_supervisor_metadata(citation_object, user)
            quick_pd_id = update_quick_pd_data(citation_object.id, note)
            send_mail = serializer_data.get('sendMail',True)
            save_csv_meta_data(quick_pd_id, citation_object.id,user_id, citation_object.station_id)
            if send_mail:
                if citation_object.video_id:
                    create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = False)
                elif citation_object.image_id:
                    create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = True)
                elif citation_object.tattile_id:
                    create_csv_and_pdf_data(citation_object.citationID,citation_object.station_id,station_name,image_flow = False,is_tattile=True)
            else:
                create_refactor_csv(citation_object.station_id)


            # generate new pdf/csv and notify xpress bill pay or quick pd based on station
            return Response(ServiceResponse({"statusCode":200, "message": "Citation marked as edit fine successfully."}).data, status=200)
        
        elif editType == 4:
            # Citation Error
            citationErrorType = serializer_data.get('citationErrorType')
            sub_status = "DMV" if serializer_data["citationErrorType"] == 1 else "ADJ"

            citation_object.current_citation_status = "CE"
            citation_object.citation_error_type = sub_status
            citation_object.edited_by = user
            citation_object.citation_edited_at = timezone.now()

            citation_object.save()
            save_citation_edit_log(citation_object, user, "CE",sub_status)

            append_new_version(
                citation=citation_object,
                new_status="CE",
                sub_status=sub_status
            )

            return Response(ServiceResponse({"statusCode":200, "message": "Citation marked as citation error successfully."}).data, status=200)
        
        elif editType == 5:
            # Dismiss Citation
            citationDismissType = serializer_data.get('citationDismissalType')

            sub_status = "AD" if serializer_data["citationDismissalType"] == 1 else "DUPC"

            citation_object.current_citation_status = "X"
            citation_object.edited_by = user
            citation_object.citation_dissmissal_type = sub_status
            citation_object.citation_edited_at = timezone.now()

            citation_object.save()

            save_citation_edit_log(citation_object, user, "X",sub_status)

            append_new_version(
                citation=citation_object,
                new_status="X",
                sub_status=sub_status
            )
            # generate new pdf/csv and notify xpress bill pay or quick pd based on station
            return Response(ServiceResponse({"statusCode":200, "message": "Citation marked as dismiss citation successfully."}).data, status=200)
        elif editType == 6:
    # Agency Warning

            citation_object.is_warning = True
            citation_object.current_citation_status = "WARN-A"
            citation_object.edited_by = user
            citation_object.citation_edited_at = datetime.now()
            citation_object.save()

            save_citation_edit_log(citation_object, user, "WARN-A")

            append_new_version(
                citation=citation_object,
                new_status="WARN-A",
                snapshot_overrides={
                    "status": "WARN-A",  
                    "fine": {
                        "id": citation_object.fine.id,
                        "amount": 0.0      
                    }
                }
            )

            update_supervisor_metadata(citation_object, user)

            quick_pd_id = update_quick_pd_data(
                citation_object.id,
                note="Agency Warning Issued"
            )

            save_csv_meta_data(
                quick_pd_id,
                citation_object.id,
                user_id,
                citation_object.station_id
            )

            return Response(ServiceResponse({
                "statusCode": 200,
                "message": "Citation marked as Warning Admin successfully."
            }).data, status=200)

        else:
            return Response(ServiceResponse({"statusCode":400, "message": "Invalid edit type"}).data, status=200)
               

class GetApprovedTableEditCountView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetApprovedTableEditViewDataInputModel,
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken

        serializer = GetApprovedTableEditViewDataInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid input data",
                "data": serializer.errors
            }).data, status=200)

        data = serializer.validated_data
        from_date = data.get('fromDate')
        to_date = data.get('toDate')
        filter_type = data.get('filterType')
        station_name = readToken.get('stationName')

        station = Station.objects.filter(name=station_name).first()
        if not station:
            return Response(ServiceResponse({
                "statusCode": 404,
                "message": "Station not found",
                "data": {}
            }).data, status=200)

        # Normalize dates
        if isinstance(from_date, str) and from_date:
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
        if isinstance(to_date, str) and to_date:
            to_date = (
                datetime.strptime(to_date, "%Y-%m-%d")
                + timedelta(days=1)
                - timedelta(seconds=1)
            )

        edit_log_qs = CitationEditLog.objects.filter(
            station=station
        )

        if from_date:
            edit_log_qs = edit_log_qs.filter(edited_at__gte=from_date)
        if to_date:
            edit_log_qs = edit_log_qs.filter(edited_at__lte=to_date)

        warning_citation_ids = edit_log_qs.filter(
            current_citation_status="WARN-A"
        ).values_list("citation_id", flat=True).distinct()

        totalWarningAdminCitation = warning_citation_ids.count()

        totalReturnToSender = edit_log_qs.filter(
            current_citation_status="RTS"
        ).exclude(
            citation_id__in=warning_citation_ids
        ).values("citation_id").distinct().count()

        # STANDARD EDIT COUNTS
        totalPaidInHouse = edit_log_qs.filter(
            current_citation_status="PIH"
        ).values("citation_id").distinct().count()

        totalUpdatedAddress = edit_log_qs.filter(
            current_citation_status="UA"
        ).values("citation_id").distinct().count()

        totalTransferOfLiability = edit_log_qs.filter(
            current_citation_status="TL"
        ).values("citation_id").distinct().count()

        totalEditFine = edit_log_qs.filter(
            current_citation_status="EF"
        ).values("citation_id").distinct().count()


        totalCitationError = edit_log_qs.filter(
            current_citation_status="CE"
        ).values("citation_id").distinct().count()

        totalDmvError = edit_log_qs.filter(
            current_citation_status="CE",
            citation_error_type="DMV"
        ).values("citation_id").distinct().count()

        totalAdjError = edit_log_qs.filter(
            current_citation_status="CE",
            citation_error_type="ADJ"
        ).values("citation_id").distinct().count()

        totalDismissedCitation = edit_log_qs.filter(
            current_citation_status="X"
        ).values("citation_id").distinct().count()

        totalAgencyDecisionDismissal = edit_log_qs.filter(
            current_citation_status="X",
            citation_dissmissal_type="AD"
        ).values("citation_id").distinct().count()

        totalDuplicateCitationDismissal = edit_log_qs.filter(
            current_citation_status="X",
            citation_dissmissal_type="DUPC"
        ).values("citation_id").distinct().count()

        result = {
            "totalPaidInHouse": totalPaidInHouse,
            "totalReturnToSender": totalReturnToSender,
            "totalEditFine": totalEditFine,
            "totalCitationError": totalCitationError,
            "totalUpdatedAddress": totalUpdatedAddress,
            "totalTransferOfLiability": totalTransferOfLiability,
            "totalDismissedCitation": totalDismissedCitation,
            "totalDmvError": totalDmvError,
            "totalAdjError": totalAdjError,
            "totalAgencyDecisionDismissal": totalAgencyDecisionDismissal,
            "totalDuplicateCitationDismissal": totalDuplicateCitationDismissal,
            "totalWarningAdminCitation": totalWarningAdminCitation
        }

        return Response(ServiceResponse({
            "statusCode": 200,
            "message": "Success",
            "data": result
        }).data, status=200)
    
class GetCitationVersions(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=GetCitationVersionsInputSerializer,
        tags=['ApprovedTable'],
        security=[{'Bearer': []}]
    )
    def post(self, request):
        serializer = GetCitationVersionsInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        citation_id = serializer.validated_data["citationId"]

        # Fetch citation
        try:
            citation = Citation.objects.get(id=citation_id)
        except Citation.DoesNotExist:
            return Response({
                "statusCode": 404,
                "message": "Citation not found",
                "data": []
            }, status=200)

        # Fetch versioning
        try:
            cv = citation.citation_versioning
        except CitationVersioning.DoesNotExist:
            return Response({
                "statusCode": 400,
                "message": "No version history exists for this citation",
                "data": []
            }, status=200)

        versions = cv.versions or []

        # Sort by version_number DESC (latest first)
        versions_sorted = sorted(
            versions,
            key=lambda v: v.get("version_number", 0),
            reverse=True
        )

        for v in versions_sorted:
            # Approved Date
            v["approvedDate"] = format_us_date(v.get("approvedDate"))
            if v["status"] == 'OR':
                v['snapshot']['fine']['amount'] = citation.fine_amount
            # Captured Date (inside snapshot)
            snapshot = v.get("snapshot", {})
            snapshot["captured_date"] = format_us_date(
                snapshot.get("captured_date")
            )

        return Response({
            "statusCode": 200,
            "message": "Success",
            "data": versions_sorted
        }, status=200)