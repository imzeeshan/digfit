from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class EmailAuthTokenSerializer(serializers.Serializer):
    """Credentials for `CustomUser` (`USERNAME_FIELD` is `email`)."""

    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request,
            email=attrs['email'],
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError(
                {'non_field_errors': ['Unable to log in with provided credentials.']},
                code='authorization',
            )
        attrs['user'] = user
        return attrs


class LoginView(APIView):
    """Return or create a DRF API token for the given email and password."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = EmailAuthTokenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


class LogoutView(APIView):
    """Delete the caller's API token (send the same `Authorization: Token …` header)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
