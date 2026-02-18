from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import login as auth_login,logout
from .serializer import *
from drf_yasg.utils import swagger_auto_schema
from accounts.models import PermissionLevel , User, Station
from video.models import *
from ees.utils import *
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from accounts_v2.account_v2_utils import extract_fields_for_register_view
from django.contrib.auth.hashers import check_password

class LoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=UserLoginRequestModel,
        responses={200 : LoginResponseModel},
        tags=['Account']
    )
    def post(self, request):
        serializer = UserLoginRequestModel(data=request.data)

        if not serializer.is_valid():       
            return Response(ServiceResponse({"statusCode": 400,"message": "Invalid input data","data" : serializer.errors}).data, status=200)
        username = serializer.validated_data['userName']
        password = serializer.validated_data['password']
        logintype = serializer.validated_data['loginType']

        user = User.objects.filter(username=username).first()
        if user:
            hashedPassword = user.password
            decryptedPassword = check_password(password,hashedPassword)
        if user and decryptedPassword:
            auth_login(request, user)
            request.session["userID"] = request.user.id
            permissions = get_object_or_404(PermissionLevel, user=request.user)
            if permissions.isSuperAdmin and logintype == 1:
                refresh = AccessToken.get_token(user)
                refresh_token = str(refresh)
                access_token = str(refresh.access_token)
                access_token_lifetime = str(refresh.access_token.lifetime)
                expiry_time = int(refresh.access_token['exp'])
                request.session["station"] = "All"
                response_data = {
                    "userId": request.user.id,
                    "userName" : request.user.username,
                    "station": "All",
                    "agencyId": 0,
                    "agencyName" : "All",
                    
                    "isTrafficLogix" : False,
                    "isVideoFlow" : False,
                    "isTattileFlow" : False,
                    "badgeUrl":None,
                    "accessTokenResponseModel":{
                        "refereshToken" : refresh_token,
                        "accessToken" : access_token,
                        "expiryTime" : expiry_time
                    },
                    "userPermissionLevelResponseModel" : {
                        "isAdjudicator" : permissions.isAdjudicator,
                        "isSupervisor" : permissions.isSupervisor,
                        "isCourt" : permissions.isCourt,
                        "isApprovedTableView" : permissions.isApprovedTableView,
                        "isRejectView" : permissions.isRejectView,
                        "isCSVView" : permissions.isCSVView,
                        "isAddUserView" : permissions.isAddUserView,
                        "isAddRoadLocationView" : permissions.isAddRoadLocationView,
                        "isEditFineView" : permissions.isEditFineView,
                        "isSubmissionView" : permissions.isSubmissionView,
                        "isCourtPreview" : permissions.isCourtPreview,
                        "isAddCourtDate" : permissions.isAddCourtDate,
                        "isAdmin" : permissions.isAdmin,
                        "isODRView" : permissions.isODRView,
                        "isPreODRView" : permissions.isPreODRView,
                        "isViewReportView" : permissions.isViewReportView,
                        "isAgencyAdjudicationBinView": permissions.isAgencyAdjudicationBinView,
                        "isReviewBinView": permissions.isReviewBinView,
                        "isReminderView" : permissions.isReminderView,
                        "isTotalTicket" : permissions.isTotalTicket,
                        "isDailyReport" : permissions.isDailyReport
                    }
                }
                login_response = LoginResponseModel(response_data)
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "Login successful",
                    "data": login_response.data
                }).data, status=200)
            elif permissions.isSuperAdmin and logintype == 2:
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "You are not supposed to login here.",
                    "data": None
                }).data, status=200)
            elif (permissions.isAdmin and logintype == 2) or (permissions.isAdmin == False and logintype == 2):
                if user.is_active == False:
                    return Response(ServiceResponse({
                        "statusCode": 400,
                        "message": "Your account has been de-activated please contact administrator.",
                        "data": []
                    }).data, status=200)
                refresh = AccessToken.get_token(user)
                refresh_token = str(refresh)
                access_token = str(refresh.access_token)
                access_token_lifetime = str(refresh.access_token.lifetime)
                expiry_time = int(refresh.access_token['exp'])
                request.session["station"] = permissions.user.agency.station.name
                response_data = {
                    "userId": request.user.id,
                    "userName" : request.user.username,
                    "station": permissions.user.agency.station.name,
                    "agencyId": permissions.user.agency.id,
                    "agencyName" : permissions.user.agency.name,
                    "isTrafficLogix" : True if permissions.user.agency.traffic_logix_client_id else False,
                    "isVideoFlow": True if Video.objects.filter(station_id=permissions.user.agency.station.id).exists() else False,
                    "isTattileFlow" : True if Tattile.objects.filter(station_id=permissions.user.agency.station.id).exists() else False,
                    "badgeUrl" : get_presigned_url(permissions.user.agency.badge_url),
                    "accessTokenResponseModel":{
                        "refereshToken" : refresh_token,
                        "accessToken" : access_token,
                        "expiryTime" : expiry_time
                    },
                    "userPermissionLevelResponseModel" : {
                        "isAdjudicator" : permissions.isAdjudicator,
                        "isSupervisor" : permissions.isSupervisor,
                        "isCourt" : permissions.isCourt,
                        "isApprovedTableView" : permissions.isApprovedTableView,
                        "isRejectView" : permissions.isRejectView,
                        "isCSVView" : permissions.isCSVView,
                        "isAddUserView" : permissions.isAddUserView,
                        "isAddRoadLocationView" : permissions.isAddRoadLocationView,
                        "isEditFineView" : permissions.isEditFineView,
                        "isSubmissionView" : permissions.isSubmissionView,
                        "isCourtPreview" : permissions.isCourtPreview,
                        "isAddCourtDate" : permissions.isAddCourtDate,
                        "isAdmin" : permissions.isAdmin,
                        "isODRView" : permissions.isODRView,
                        "isPreODRView" : permissions.isPreODRView,
                        "isViewReportView" : permissions.isViewReportView,
                        "isAgencyAdjudicationBinView":permissions.isAgencyAdjudicationBinView,
                        "isReviewBinView":permissions.isReviewBinView,
                        "isReminderView" : permissions.isReminderView,
                        "isTotalTicket" : permissions.isTotalTicket,
                        "isDailyReport" : permissions.isDailyReport
                    }
                }
                login_response = LoginResponseModel(response_data)
                return Response(ServiceResponse({
                    "statusCode": 200,
                    "message": "Login successful",
                    "data": login_response.data
                }).data, status=200)
            elif (permissions.isAdmin and logintype == 1) or (permissions.isAdmin == False and logintype == 1):
                return Response(ServiceResponse({
                    "statusCode": 400,
                    "message": "You are not supposed to login here.",
                    "data": None
                }).data, status=200)
        else:
            return Response(ServiceResponse({
                "statusCode": 400,
                "message": "Invalid credentials",
            }).data, status=200)
        return Response(ServiceResponse({
            "statusCode": 400,
            "message": "Invalid login attempt.",
            "data": None
        }).data, status=200)


@swagger_auto_schema(
    method='post',
    tags=['Account']
)

@api_view(['POST'])
@require_http_methods(["POST"])
@permission_classes([IsAuthenticated])
def LogoutView(request):
    logout(request)
    return Response({"statusCode": 200, "message": "Logout successful"}, status=200)


class RegisterView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=UserRegisterInputModel,
        tags=['Account'],
        security=[{'Bearer': []}],
    )
    def post(self, request):
        serializer = UserRegisterInputModel(data=request.data)
        if not serializer.is_valid():
            return Response(APIResponse({"statusCode": 400,"message": "Invalid input data","data": serializer.errors}).data,status=200)

        readToken = user_information(request)
        if isinstance(readToken, Response):
            return readToken
        agency_id = readToken.get('agencyId')
        station_id = readToken.get('stationId')
        extracted_input_fields = extract_fields_for_register_view(serializer.validated_data)

        if User.objects.filter(username=extracted_input_fields["user_name"]).exists():
            return Response(APIResponse({"statusCode": 409, "message": "Username already exists."}).data, status=200)
        
        if User.objects.filter(email=extracted_input_fields["email"], agency=agency_id).exists():
            return Response(APIResponse({"statusCode": 409, "message": "Email already exists."}).data,status=200)

        newuser = User.objects.create(
            username=extracted_input_fields["user_name"],
            email=extracted_input_fields["email"],
            first_name=extracted_input_fields["first_name"],
            last_name=extracted_input_fields["last_name"],
            agency_id=agency_id
        )
        newuser.set_password(extracted_input_fields["password"])
        newuser.save()
        PermissionLevel.objects.create(
            user_id=newuser.id,
            isAdjudicator=extracted_input_fields["is_adjudicator"],
            isSupervisor=extracted_input_fields["is_supervisor"],
            isCourt=extracted_input_fields["is_court"],
            isAdmin=False,
            isSuperAdmin=False,
            isApprovedTableView=extracted_input_fields["is_approved_table_view"],
            isRejectView=extracted_input_fields["is_reject_view"],
            isCSVView=extracted_input_fields["is_csv_view"],
            isAddUserView=extracted_input_fields["is_add_user_view"],
            isAddRoadLocationView=extracted_input_fields["is_add_road_location_view"],
            isEditFineView=extracted_input_fields["is_edit_fine_view"],
            isSubmissionView=extracted_input_fields["is_submission_view"],
            isCourtPreview=extracted_input_fields["is_court_preview"],
            isAddCourtDate=extracted_input_fields["is_add_court_date"],
            isAgencyAdjudicationBinView=extracted_input_fields["is_agency_adjudication_bin_view"],
            isReviewBinView=extracted_input_fields["is_review_bin_view"],
            isPreODRView=extracted_input_fields["is_pre_odr_view"],
            isODRView=extracted_input_fields["is_odr_view"],
            isViewReportView=extracted_input_fields["is_view_report_view"],
            isReminderView=extracted_input_fields["is_reminder_view"],
            station_id=station_id
            # isTotalTicket = extracted_input_fields["is_total_ticket"],
            # isDailyReport = extracted_input_fields["is_daily_report"]
        )
        return Response(
            APIResponse({"statusCode": 201, "message": "User has been registered successfully"}).data, status=200)


        
#To Generate Access Token

class AccessToken(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['userName'] = user.username
        # token['email'] = user.email
        token['isSuperuser'] = user.is_superuser
        token['roles'] = 'user_role'
        # token['agencyId'] = user.agency_id
        token['isStaff'] = user.is_staff

        # try:
        #     # Get permission level
        #     permission_level = PermissionLevel.objects.get(user=user)
        #     token['isAdjudicator'] = permission_level.isAdjudicator
        #     token['isSupervisor'] = permission_level.isSupervisor
        #     token['isSuperAdmin'] = permission_level.isSuperAdmin
        #     token['isCourt'] = permission_level.isCourt
        #     token['isAdmin'] = permission_level.isAdmin
        #     token['isApprovedTableView'] = permission_level.isApprovedTableView
        #     token['isRejectView'] = permission_level.isRejectView
        #     token['isCSVView'] = permission_level.isCSVView
        #     token['isAddUserView'] = permission_level.isAddUserView
        #     token['isAddRoadLocationView'] = permission_level.isAddRoadLocationView
        #     token['isEditFineView'] = permission_level.isEditFineView
        #     token['isSubmissionView'] = permission_level.isSubmissionView
        #     token['isCourtPreview'] = permission_level.isCourtPreview
        #     token['isAddCourtDate'] = permission_level.isAddCourtDate
        #     # Get agency details
        #     agency = Agency.objects.get(id=user.agency_id)
        #     token['agencyName'] = agency.name
        #     station_id = getattr(agency, 'station_id', None)
        #     token['stationId'] = station_id
        #     station_name_mappings = {
        #         'MOR-C': 'MORR',
        #         'FED-M': 'FEDB',
        #         'OIL': 'OILC',
        #         'OBR': 'OBER',
        #         'ELZ': 'ELIZ',
        #         'HUD-C': 'HUDS'
        #     }
        #     # Get station details
        #     if station_id:
        #         station = Station.objects.get(id=station_id)
        #         station_name = station.name
        #         station_modified_name = station.name
        #         station_modified_name = station_name_mappings.get(station_modified_name, station_modified_name)
        #         token['stationModifiedName'] = station_modified_name
        #         token['stationName'] = station_name
        #         state_id = station.state_id
        #         token['stateId'] = state_id

        #         # Get state name
        #         state = State.objects.get(id=state_id) if state_id else None
        #         token['stateName'] = state.name if state else None
        #     else:
        #         token['stationName'] = None
        #         token['stationModifiedName'] = None
        #         token['stateId'] = None
        #         token['stateName'] = None

        # except PermissionLevel.DoesNotExist:
        #     token['isAdjudicator'] = False
        #     token['isSupervisor'] = False
        #     token['isSuperAdmin'] = False
        #     token['isCourt'] = False
        #     token['isAdmin'] = False
        #     token['agencyName'] = None
        #     token['stationId'] = None
        #     token['stationName'] = None
        #     token['stateId'] = None
        #     token['stateName'] = None
        #     token['isApprovedTableView'] = None
        #     token['isRejectView'] = None
        #     token['isCSVView'] = None
        #     token['isAddUserView'] = None
        #     token['isAddRoadLocationView'] = None
        #     token['isEditFineView'] = None
        #     token['isSubmissionView'] = None
        #     token['isCourtPreview'] = None
        #     token['isAddCourtDate'] = None
        # except Agency.DoesNotExist:
        #     token['agencyName'] = None
        #     token['stationId'] = None
        #     token['stationName'] = None
        #     token['stateId'] = None
        #     token['stateName'] = None
        # except Station.DoesNotExist:
        #     token['stationName'] = None
        #     token['stateId'] = None
        #     token['stateName'] = None
        # except State.DoesNotExist:
        #     token['stateName'] = None

        return token
    
@swagger_auto_schema(
    method='get',
    tags=['Account']
)
 
@api_view(['GET'])
@require_http_methods(["GET"])
@permission_classes([AllowAny])
def ServerStatusCheck(request):
    status_check = True
    return Response({"statusCode": 200, "message": status_check}, status=200)