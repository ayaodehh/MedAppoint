from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.tokens import RefreshToken

from patients.models import Patient

from .models import User

try:
    from axes.handlers.proxy import AxesProxyHandler
except ImportError:
    AxesProxyHandler = None


def _run_password_validators(password, user=None):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with this email already exists.")],
    )
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with this username already exists.")],
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "otp_required",
            "is_active",
            "password",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_password(self, value):
        _run_password_validators(value, user=self.instance)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "Password is required to create a user."})
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with this email already exists.")],
    )
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="A user with this username already exists.")],
    )
    medical_record_number = serializers.CharField(
        write_only=True,
        validators=[UniqueValidator(queryset=Patient.objects.all(), message="This medical record number is already registered.")],
    )
    date_of_birth = serializers.DateField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "phone_number", "password", "medical_record_number", "date_of_birth")
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            "phone_number": {"required": True, "allow_blank": False},
        }

    def validate_password(self, value):
        _run_password_validators(value)
        return value

    def validate_date_of_birth(self, value):
        today = timezone.localdate()
        if value > today:
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        if (today.year - value.year) > 130:
            raise serializers.ValidationError("Date of birth is not valid.")
        return value


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    otp_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        request = self.context["request"]
        user = authenticate(request=request, username=attrs["username"], password=attrs["password"])
        if not user:
            if AxesProxyHandler is not None:
                try:
                    locked = AxesProxyHandler.is_locked(request, credentials={"username": attrs["username"]})
                except Exception:
                    locked = False
                if locked:
                    raise serializers.ValidationError(
                        "Account temporarily locked after repeated failed attempts. Please try again later."
                    )
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive. Contact your clinic administrator.")
        if user.otp_required or TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            otp_token = attrs.get("otp_token")
            device = TOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").first()
            if not otp_token:
                raise serializers.ValidationError("OTP token is required for this account.")
            if not device or not device.verify_token(otp_token):
                raise serializers.ValidationError("Invalid OTP token.")
        attrs["user"] = user
        return attrs


class OTPSetupSerializer(serializers.Serializer):
    name = serializers.CharField(default="default")

    def create(self, validated_data):
        user = self.context["request"].user
        return TOTPDevice.objects.create(user=user, name=validated_data["name"], confirmed=False)


class OTPVerifySerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = self.context["request"].user
        try:
            device = TOTPDevice.objects.get(pk=attrs["device_id"], user=user)
        except TOTPDevice.DoesNotExist as exc:
            raise serializers.ValidationError("Device not found.") from exc
        if not device.verify_token(attrs["token"]):
            raise serializers.ValidationError("Invalid OTP token.")
        attrs["device"] = device
        return attrs


def issue_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    return {"refresh": str(refresh), "access": str(refresh.access_token)}
