from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import AuthTokenSerializer, UsuarioSerializer,AverageGradesSerizalizer, CuantFortDebSerializer, CalificacionesCualitativasSerializer

from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework. authentication import TokenAuthentication

from django.contrib.auth.models import User
from django.db.models import Avg, Q
from .models import Usuario, PromedioCalificaciones,FortalezasDebilidadesCuantitativas, CalificacionesCualitativas
from django.shortcuts import get_object_or_404


# Este metodo se utiliza para autenticarse en la aplicación
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

# Este metodo se utiliza para registrar nuevos usuarios. Requiere autenticación
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

# Este metodo retorna la información de ususario, requiere autenticación
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_profile(request):
    serializer = UsuarioSerializer(instance=request.user)
    return Response({'user':serializer.data},status=status.HTTP_200_OK)


# Este metodo retorna las calificaciones promedio de los docentees de la escuela ingresada o la información de un docente especifico
@api_view(['GET'])
def get_average_grades(request):
    try:
        docente_id = request.query_params.get('docente_id')
        escuela_id = request.query_params.get('escuela_id')

        if docente_id:
            promedios = PromedioCalificaciones.objects.filter(docente_id=docente_id)
        elif docente_id and escuela_id:
            promedios = PromedioCalificaciones.objects.filter(docente_id=docente_id, escuela_id = escuela_id)
        elif escuela_id:
            promedios = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id)
        else:
            return Response({'error': 'debe ingresar una parametro valido para llevar a cabo la consulta'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AverageGradesSerizalizer(promedios, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
# Este metodo retorna las fortalezas y debilidades cuantitaticas del docente con el id engresado   
@api_view(['GET'])
def get_cuant_fort_dev(request):
    try:
        docente_id = request.query_params.get('docente_id')
        fortdeb = FortalezasDebilidadesCuantitativas.objects.filter(docente_id=docente_id).first()

        if not fortdeb:
            return Response({'error': 'No existen fortalezas y debilidades cuantitativas para el docente con el ID proporcionado'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CuantFortDebSerializer(fortdeb)  # Serializa el objeto individual
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Metodo que retorna el mejor y peor comentario del docente con el id ingresado:
@api_view(['GET'])
def get_best_and_worst_comment(request):
    try:
        docente_id = request.query_params.get('docente_id')
        if not docente_id:
            return Response({'error': 'El parámetro docente_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        calificaciones = CalificacionesCualitativas.objects.filter(docente_id=docente_id)
        if not calificaciones.exists():
            return Response({'error': 'No se encontraron calificaciones para el docente proporcionado.'}, status=status.HTTP_404_NOT_FOUND)
        
        mejor_comentario = calificaciones.order_by('-promedio').first()
        peor_comentario = calificaciones.order_by('promedio').first()

        mejor_calificacion_serializer = CalificacionesCualitativasSerializer(mejor_comentario)
        peor_calificacion_serializer = CalificacionesCualitativasSerializer(peor_comentario)
        
        return Response({
            'mejor': mejor_calificacion_serializer.data,
            'peor': peor_calificacion_serializer.data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

# Hay que evaluar que es mejor. que las fortalezas y desventajas cualitativas se generen dinamicamente o generarlas y tenerlas almacenadas en la base de datos y que cambien
# cada vez que se de una actualización de datos?


# Metodo que retorna el valor de calificación promedio de toda una escuela y el valor promedio de toda la facultad
@api_view(['GET'])
def get_average_grades_school_and_overall(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        promedio_general = PromedioCalificaciones.objects.aggregate(promedio=Avg('promedio'))['promedio']
        
        promedio_escuela = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id).aggregate(promedio=Avg('promedio'))['promedio']

        if promedio_escuela is None:
            promedio_escuela = 'No se encontraron calificaciones para la escuela proporcionada.'
        
        return Response({
            'promedio_facultad': promedio_general,
            'promedio_escuela': promedio_escuela
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Metodo para obtener la información sobre promedios cualitativos de facultad, docente y escuela
@api_view(['GET'])
def get_qualitative_average_grades(request):
    try:
        docente_id = request.query_params.get('docente_id')
        if not docente_id:
            return Response({'error': 'El parámetro docente_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            docente = Usuario.objects.get(id=docente_id)
            escuela_id = docente.escuela_id
        except Usuario.DoesNotExist:
            return Response({'error': 'Docente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Promedio cualitativo de todos los docentes de la facultad
        promedio_facultad = PromedioCalificaciones.objects.filter(~Q(promedio_cual=None), ~Q(promedio_cual=0)).aggregate(promedio=Avg('promedio_cual'))['promedio']

        promedio_escuela = None
        promedio_docente = None

        # Promedio cualitativo de todos los docentes de la escuela
        if escuela_id:
            promedio_escuela = PromedioCalificaciones.objects.filter(
                ~Q(promedio_cual=None), 
                ~Q(promedio_cual=0),
                docente__escuela_id=escuela_id,
            ).aggregate(promedio=Avg('promedio_cual'))['promedio']

        # Promedio cualitativo del docente específico
        promedio_docente = PromedioCalificaciones.objects.filter( 
            ~Q(promedio_cual=None), 
            ~Q(promedio_cual=0),
            docente_id=docente_id,
        ).aggregate(promedio=Avg('promedio_cual'))['promedio']

        response_data = {
            'promedio_facultad': promedio_facultad,
            'promedio_escuela': promedio_escuela if promedio_escuela is not None else 'No se encontraron calificaciones para la escuela proporcionada.',
            'promedio_docente': promedio_docente if promedio_docente is not None else 'No se encontraron calificaciones para el docente proporcionado.'
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
# Metodo para obtener la información sobre promedios cuantitativos de facultad, docente y escuela
@api_view(['GET'])
def get_cuantitative_average_grades(request):
    try:
        docente_id = request.query_params.get('docente_id')
        if not docente_id:
            return Response({'error': 'El parámetro docente_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            docente = Usuario.objects.get(id=docente_id)
            escuela_id = docente.escuela_id
        except Usuario.DoesNotExist:
            return Response({'error': 'Docente no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Promedio cualitativo de todos los docentes de la facultad
        promedio_facultad = PromedioCalificaciones.objects.filter(~Q(promedio_cual=None), ~Q(promedio_cual=0)).aggregate(promedio=Avg('promedio_cuant'))['promedio']

        promedio_escuela = None
        promedio_docente = None

        # Promedio cualitativo de todos los docentes de la escuela
        if escuela_id:
            promedio_escuela = PromedioCalificaciones.objects.filter(
                ~Q(promedio_cual=None), 
                ~Q(promedio_cual=0),
                docente__escuela_id=escuela_id,
            ).aggregate(promedio=Avg('promedio_cuant'))['promedio']

        # Promedio cualitativo del docente específico
        promedio_docente = PromedioCalificaciones.objects.filter( 
            ~Q(promedio_cual=None), 
            ~Q(promedio_cual=0),
            docente_id=docente_id,
        ).aggregate(promedio=Avg('promedio_cuant'))['promedio']

        response_data = {
            'promedio_facultad': promedio_facultad,
            'promedio_escuela': promedio_escuela if promedio_escuela is not None else 'No se encontraron calificaciones para la escuela proporcionada.',
            'promedio_docente': promedio_docente if promedio_docente is not None else 'No se encontraron calificaciones para el docente proporcionado.'
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)