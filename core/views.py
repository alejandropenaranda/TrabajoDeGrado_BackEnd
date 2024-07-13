from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import AuthTokenSerializer, UsuarioSerializer

from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework. authentication import TokenAuthentication

from django.contrib.auth.models import User
from .models import Usuario
from django.shortcuts import get_object_or_404


@api_view(['POST'])
def login_ex(request):
    serializer = AuthTokenSerializer(data=request.data)
    if serializer.is_valid():
        user = get_object_or_404(Usuario, email=serializer.validated_data['email'])

        if not user.check_password(serializer.validated_data['password']):
            return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)
        
        token, created = Token.objects.get_or_create(user=user)

        user_serializer = UsuarioSerializer(instance=user)
        return Response({'token': token.key, 'user': user_serializer.data}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
def register_ex(request):
    serializer = UsuarioSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        user.set_password(serializer.validated_data['password'])
        user.save()

        token = Token.objects.create(user=user)
        return Response({'token': token.key, 'user': serializer.data}, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def profile_ex(request):
    serializer = UsuarioSerializer(instance=request.user)
    return Response({"user": serializer.data}, status=status.HTTP_200_OK)