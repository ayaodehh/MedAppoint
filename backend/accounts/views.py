from django.conf import settings
from django.db import transaction
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from audit.services import audit_auth_event, audit_state_change
from patients.models import Patient

from .models import User
from .permissions import DenyAll
from .permissions import UserPermission
from .serializers import (
    LoginSerializer,
    OTPSetupSerializer,
    OTPVerifySerializer,
    RegisterSerializer,
    UserSerializer,
    issue_tokens_for_user,
)


def set_auth_cookies(response, access_token, refresh_token):
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE_NAME,
        access_token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


def clear_auth_cookies(response):
    response.delete_cookie(settings.JWT_ACCESS_COOKIE_NAME)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE_NAME)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [UserPermission]

    @action(detail=False, methods=["get"], permission_classes=[UserPermission])
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = serializer.save()
            audit_state_change(self.request, actor=self.request.user, action="user.create", instance=user)

    def perform_update(self, serializer):
        with transaction.atomic():
            user = serializer.save()
            audit_state_change(self.request, actor=self.request.user, action="user.update", instance=user)

    def perform_destroy(self, instance):
        resource_id = str(instance.pk)
        with transaction.atomic():
            instance.delete()
            audit_state_change(
                self.request,
                actor=self.request.user,
                action="user.delete",
                resource_type=instance.__class__.__name__,
                resource_id=resource_id,
            )


class AuthSessionViewSet(viewsets.GenericViewSet):
    queryset = User.objects.none()
    serializer_class = drf_serializers.Serializer
    permission_classes = [DenyAll]

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = User.objects.create_user(
                username=serializer.validated_data["username"],
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
                first_name=serializer.validated_data["first_name"],
                last_name=serializer.validated_data["last_name"],
                phone_number=serializer.validated_data["phone_number"],
                role=User.Role.PATIENT,
            )
            patient = Patient.objects.create(
                user=user,
                full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
                medical_record_number=serializer.validated_data["medical_record_number"],
                date_of_birth=serializer.validated_data["date_of_birth"],
                phone_number=user.phone_number,
            )
            audit_state_change(request, actor=user, action="auth.register", instance=user, metadata={"patient_id": str(patient.pk)})
            tokens = issue_tokens_for_user(user)
        response = Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)
        set_auth_cookies(response, tokens["access"], tokens["refresh"])
        return response

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def login(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            audit_auth_event(request, actor=None, action="auth.login.failure", status_value="failure", metadata={"username": request.data.get("username")})
            raise

        user = serializer.validated_data["user"]
        tokens = issue_tokens_for_user(user)
        response = Response({"user": UserSerializer(user).data})
        set_auth_cookies(response, tokens["access"], tokens["refresh"])
        audit_auth_event(request, actor=user, action="auth.login.success")
        return response

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def refresh(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not raw_refresh:
            audit_auth_event(request, actor=request.user if request.user.is_authenticated else None, action="auth.refresh.failure", status_value="failure")
            return Response({"detail": "Refresh token cookie is missing."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(raw_refresh)
            access_token = str(refresh.access_token)
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                refresh.set_jti()
                refresh.set_exp()
                refresh.set_iat()
            response = Response({"detail": "Token refreshed."})
            set_auth_cookies(response, access_token, str(refresh))
            audit_auth_event(request, actor=request.user if request.user.is_authenticated else None, action="auth.refresh.success")
            return response
        except TokenError:
            audit_auth_event(request, actor=request.user if request.user.is_authenticated else None, action="auth.refresh.failure", status_value="failure")
            return Response({"detail": "Refresh token is invalid."}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def logout(self, request):
        raw_refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass
        response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        audit_auth_event(request, actor=request.user if request.user.is_authenticated else None, action="auth.logout")
        return response

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def otp_setup(self, request):
        serializer = OTPSetupSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        audit_state_change(request, actor=request.user, action="auth.otp_setup", instance=device, metadata={"config_url": device.config_url})
        return Response({"device_id": device.pk, "config_url": device.config_url, "confirmed": device.confirmed}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def otp_verify(self, request):
        serializer = OTPVerifySerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            audit_auth_event(request, actor=request.user, action="auth.otp_verify.failure", status_value="failure")
            raise
        device = serializer.validated_data["device"]
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        audit_auth_event(request, actor=request.user, action="auth.otp_verify.success")
        return Response({"detail": "OTP device verified.", "device_id": device.pk})
