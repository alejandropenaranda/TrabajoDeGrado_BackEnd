from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import AuthTokenSerializer, UsuarioSerializer,AverageGradesSerizalizer

from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework. authentication import TokenAuthentication

from django.contrib.auth.models import User
from .models import Usuario, PromedioCalificaciones
from django.shortcuts import get_object_or_404

@api_view(['POST'])
def user_login(request):
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
def user_register(request):
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
def user_profile(request):
    serializer = UsuarioSerializer(instance=request.user)
    return Response({'user':serializer.data},status=status.HTTP_200_OK)


@api_view(['GET'])
def get_average_grades(request):
    try:
        docente_id = request.query_params.get('docente_id')
        periodo = request.query_params.get('periodo')
        escuela_id = request.query_params.get('escuela_id')

        if docente_id and periodo:
            promedios = PromedioCalificaciones.objects.filter(docente_id=docente_id, periodo=periodo)
        elif escuela_id and periodo:
            promedios = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id, periodo=periodo)
        elif docente_id:
            promedios = PromedioCalificaciones.objects.filter(docente_id=docente_id)
        elif periodo:
            promedios = PromedioCalificaciones.objects.filter(periodo=periodo)
        elif escuela_id:
            promedios = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id)
        else:
            promedios = PromedioCalificaciones.objects.all()

        serializer = AverageGradesSerizalizer(promedios, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)