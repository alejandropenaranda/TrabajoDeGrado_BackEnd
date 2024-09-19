from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import AuthTokenSerializer, CualFortDebSerializer, SchoolFortDebSerializer, SchoolSerializer, UsuarioSerializer,AverageGradesSerizalizer, CuantFortDebSerializer, CalificacionesCualitativasSerializer

from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework. authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser

from django.contrib.auth.models import User
from django.db.models import Avg, Q
from .models import Escuela, FortalezasDebilidadesEscula, Usuario, PromedioCalificaciones,FortalezasDebilidadesCuantitativas, CalificacionesCualitativas, FortalezasDebilidadesCualitativas
from django.shortcuts import get_object_or_404

import base64
from io import BytesIO
from collections import Counter
from wordcloud import WordCloud
import pandas as pd

from .utils.fortalezas_debilidades.cual_fort_deb import laguageModel
from .utils.procesar_evaluaciones.cualitativas import procesar_evaluaciones_cualitativas
from .utils.procesar_evaluaciones.cuantitativas import procesar_evaluaciones_cuantitativas

# import openai
import tiktoken

# Este metodo se utiliza para autenticarse en la aplicación
@api_view(['POST'])
def user_login(request):
    serializer = AuthTokenSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = Usuario.objects.get(email=serializer.validated_data['email'])
        except Usuario.DoesNotExist:
            return Response({"error": "Credenciales incorrectas"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(serializer.validated_data['password']):
            return Response({"error": "Credenciales incorrectas"}, status=status.HTTP_400_BAD_REQUEST)
        
        token, created = Token.objects.get_or_create(user=user)

        user_serializer = UsuarioSerializer(instance=user)
        return Response({'token': token.key, 'user': user_serializer.data}, status=status.HTTP_200_OK)
    return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

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

# Este metodo permite modificar los datos del usuario con el id ingresado - requiere ser admin
@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  # Verifica que haya un token y que el usuario esté autenticado
def update_user_by_admin(request, user_id):
    # Obtenemos el token de la cabecera de autorización
    token_key = request.auth
    token = get_object_or_404(Token, key=token_key)

    # Obtenemos el usuario que está asociado con el token
    admin_user = token.user

    # Verificamos si el usuario autenticado es administrador
    if not admin_user.is_admin:
        return Response({'detail': 'Unauthorized. Admin access required.'}, status=status.HTTP_401_UNAUTHORIZED)

    # Buscamos el usuario que queremos modificar por su ID usando el modelo personalizado Usuario
    user = get_object_or_404(Usuario, id=user_id)
    serializer = UsuarioSerializer(user, data=request.data, partial=True)  # partial=True permite actualizaciones parciales

    if serializer.is_valid():
        # Si se proporciona una nueva contraseña
        if 'password' in request.data:
            # Encriptar la nueva contraseña
            user.set_password(request.data['password'])
            user.save()  # Guardamos solo el usuario con la nueva contraseña encriptada

        # Guardamos los demás campos del usuario sin incluir la contraseña
        serializer.save(password=user.password)  # Guardamos el serializer sin sobrescribir la contraseña

        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_self_change_password(request):
    token_key = request.auth
    token = get_object_or_404(Token, key=token_key)
    user = token.user

    if user.codigo != request.data.get('cedula'):
        return Response({'error': 'No puede modificar la contraseña de otro usuario'}, status=status.HTTP_400_BAD_REQUEST)

    # Validar y actualizar la contraseña
    new_password = request.data.get('password')
    if new_password:
        user.set_password(new_password)
        user.save()  # Guardamos solo el usuario con la nueva contraseña encriptada

    return Response({'message': 'Contraseña actualizada exitosamente'}, status=status.HTTP_200_OK)

# Este metodo permite listar a todos los usuarios del sistema - requiere ser admin

# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
# @api_view(['GET'])
# def list_users_except_self(request):

#     print("entre a la vista")
#     # Obtenemos el token de la cabecera de autorización
#     token_key = request.auth

#     print(token_key)
#     token = get_object_or_404(Token, key=token_key)

#     current_user = token.user

#     if not current_user.is_admin:
#         return Response({'detail': 'Unauthorized. Admin access required.'}, status=status.HTTP_401_UNAUTHORIZED)

#     users = Usuario.objects.exclude(id=current_user.id)

#     serializer = UsuarioSerializer(users, many=True)

#     # Retornar la lista de usuarios
#     return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated]) 
def list_users_except_self(request):
    print("entre a la vista")

    current_user = request.user

    # Verificar si el usuario no es administrador
    if not current_user.is_admin:
        return Response({'detail': 'Unauthorized. Admin access required.'}, status=status.HTTP_401_UNAUTHORIZED)

    users = Usuario.objects.exclude(id=current_user.id)

    serializer = UsuarioSerializer(users, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

# Este metodo retorna la información de ususario, requiere autenticación
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_profile(request):
    serializer = UsuarioSerializer(instance=request.user)
    return Response({'user':serializer.data},status=status.HTTP_200_OK)


# Este metodo retorna las calificaciones promedio de los docentes de la escuela ingresada o la información de un docente especifico
@api_view(['GET'])
def get_average_grades_registers(request):
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
            promedios = PromedioCalificaciones.objects.all()

        serializer = AverageGradesSerizalizer(promedios, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
# Este metodo retorna las fortalezas y debilidades cuantitaticas del docente con el id engresado   
@api_view(['GET'])
def get_cuant_fort_deb(request):
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


#Metodo que retorna el los promedios generales, cuantitativos y cualitativos del docente ingresado

@api_view(['GET'])
def get_average_grades(request):
    try:
        docente_id = request.query_params.get('docente_id')
        if not docente_id:
            return Response({'error': 'El parámetro docente_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrar las calificaciones por docente_id
        calificaciones = PromedioCalificaciones.objects.filter(docente_id=docente_id)
        
        # Obtener promedios
        
        promedio_cual = calificaciones.filter(promedio_cual__gt=0).aggregate(promedio_cual=Avg('promedio_cual'))['promedio_cual']
        promedio_cuant = calificaciones.filter(promedio_cuant__gt=0).aggregate(promedio_cuant=Avg('promedio_cuant'))['promedio_cuant']
        promedio = (promedio_cual + promedio_cuant)/2

        # Verificar si existen registros
        if promedio is None or promedio_cual is None or promedio_cuant is None:
            return Response({'error': 'No se encontraron calificaciones para el docente proporcionado.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Retornar los valores promedio
        return Response({
            'promedio': promedio,
            'promedio_cual': promedio_cual,
            'promedio_cuant': promedio_cuant
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Metodo que retorna el valor de calificación promedio de toda una escuela y el valor promedio de toda la facultad
# @api_view(['GET'])
# def get_average_grades_school_and_overall(request):
#     try:
#         escuela_id = request.query_params.get('escuela_id')
#         if not escuela_id:
#             return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
#         promedio_general = PromedioCalificaciones.objects.aggregate(promedio=Avg('promedio'))['promedio']
        
#         promedio_escuela = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id).aggregate(promedio=Avg('promedio'))['promedio']

#         if promedio_escuela is None:
#             promedio_escuela = 'No se encontraron calificaciones para la escuela proporcionada.'
        
#         return Response({
#             'promedio_facultad': promedio_general,
#             'promedio_escuela': promedio_escuela
#         }, status=status.HTTP_200_OK)
    
#     except Exception as e:
#         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_average_grades_school_and_overall(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calcular promedios generales de la facultad
        promedio_general = PromedioCalificaciones.objects.aggregate(
            promedio=Avg('promedio'),
            promedio_cuant=Avg('promedio_cuant'),
            promedio_cual=Avg('promedio_cual')
        )
        
        # Calcular promedios específicos de la escuela
        promedio_escuela = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id).aggregate(
            promedio=Avg('promedio'),
            promedio_cuant=Avg('promedio_cuant'),
            promedio_cual=Avg('promedio_cual')
        )

        # Manejo de caso donde no se encuentran registros para la escuela
        if not promedio_escuela['promedio']:
            return Response({'message': 'No se encontraron calificaciones para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
                'promedio_facultad': promedio_general['promedio'],
                'promedio_facultad_cuantitativo': promedio_general['promedio_cuant'],
                'promedio_facultad_cualitativo': promedio_general['promedio_cual'],
                'promedio_escuela': promedio_escuela['promedio'],
                'promedio_escuela_cuantitativo': promedio_escuela['promedio_cuant'],
                'promedio_escuela_cualitativo': promedio_escuela['promedio_cual'],
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# Metodo para obtener la información sobre promedios cualitativos de facultad, docente y escuela
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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

        # Promedio cuantitativo del docente específico
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
    
# Metodo para enviar wordcloud
def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    buffer = BytesIO()
    wordcloud.to_image().save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_wordcloud_and_frequent_words(request):
    try:
        docente_id = request.query_params.get('docente_id')
        if not docente_id:
            return Response({'error': 'El parámetro docente_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        docente = get_object_or_404(Usuario, pk=docente_id)
        comentarios = CalificacionesCualitativas.objects.filter(docente=docente).values_list('comentario_limpio', flat=True)
        
        if not comentarios:
            return Response({'error': 'No se encontraron comentarios para el docente proporcionado.'}, status=status.HTTP_404_NOT_FOUND)
        
        texto_completo = " ".join(comentarios)
        wordcloud_base64 = generate_wordcloud(texto_completo)
        
        palabras = texto_completo.split()
        conteo_palabras = Counter(palabras)
        palabras_mas_frecuentes = conteo_palabras.most_common(10)
        
        return Response({
            'wordcloud': wordcloud_base64,
            'palabras_mas_frecuentes': palabras_mas_frecuentes
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

# METODO PARA ESTRAER FORTALEZAS Y DEBILIDADES DE LOS COMENTARIOS USANDO MODELOS DE LENGUAJE.

import re
import json

def extraer_json(respuesta):
    json_match = re.search(r'\{.*\}', respuesta, re.DOTALL)
    print(json_match)
    if json_match:
        json_str = json_match.group()
        try:
            datos = json.loads(json_str)
            return datos
        except json.JSONDecodeError:
            return respuesta
    else:
        return respuesta 

# openai.api_key = 'tu_api_key'
enc = tiktoken.encoding_for_model("gpt-4")

def contar_tokens(texto):
    tokens = enc.encode(texto)
    return len(tokens)

def analizar_comentarios(comentarios):
    prompt_base = (
        "Analiza los siguientes comentarios sobre el desempeño de un docente. Identifica cuáles son las fortalezas y debilidades del docente y devuelve una estructura de datos que contenga las fortalezas y debilidades con un valor asignado de la siguiente escala: 1 es Muy Pobre, 2 es Pobre, 3 es Neutro, 4 es Bueno, y 5 es Muy Bueno.\n\n"
        "Comentarios:\n"
    )
    prompt_ejemplo = "\nEstructura de datos esperada:\n{\n    \"fortalezas\": {\"fortaleza 1\": 4, \"fortaleza 2\": 5, ...},\n    \"debilidades\": {\"debilidad 1\": 2, \"debilidad 2\": 1, ...}\n}"

    tokens_prompt = contar_tokens(prompt_base) + contar_tokens(prompt_ejemplo)
    max_tokens = 6144

    comentarios_incluidos = []
    tokens_comentarios = 0

    for comentario in comentarios:
        tokens_comentario = contar_tokens(comentario)
        if tokens_prompt + tokens_comentarios + tokens_comentario < max_tokens:
            comentarios_incluidos.append(comentario)
            tokens_comentarios += tokens_comentario
        else:
            break

    prompt = prompt_base
    for i, comentario in enumerate(comentarios_incluidos, 1):
        prompt += f" {i}. {comentario}\n"
    prompt += prompt_ejemplo

    response = extraer_json(laguageModel(prompt))
    return prompt, response

    # response = openai.Completion.create(
    #     engine="gpt-4",
    #     prompt=prompt,
    #     max_tokens=1500,
    #     n=1,
    #     stop=None,
    #     temperature=0.7,
    # )
    # return response.choices[0].text.strip()

#Metodo que analiza los 10 comentario mas relevantes de cada docente y determina sus fortalezas y debilidades
@api_view(['POST'])
def find_strengths_weaknesses(request):
    try:
        #docente_id = request.query_params.get('docente_id')
        docente_id = request.data.get('docente_id')
        if not docente_id:
            return Response({'error': 'El parámetro docente_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        docente = get_object_or_404(Usuario, pk=docente_id)
        comentarios = CalificacionesCualitativas.objects.filter(docente=docente).order_by('promedio')
        
        if not comentarios:
            return Response({'error': 'No se encontraron comentarios para el docente proporcionado.'}, status=status.HTTP_404_NOT_FOUND)
        
        mejores_comentarios = list(comentarios.order_by('-promedio')[:5].values_list('comentario', flat=True))
        peores_comentarios = list(comentarios.order_by('promedio')[:5].values_list('comentario', flat=True))
        
        todos_comentarios = mejores_comentarios + peores_comentarios
        if len(todos_comentarios) < 10:
            todos_comentarios = list(comentarios.values_list('comentario', flat=True))
        
        prompt, resultado = analizar_comentarios(todos_comentarios)

        registro, creado = FortalezasDebilidadesCualitativas.objects.get_or_create(
            docente=docente,
            defaults={'prompt': prompt, 'valoraciones': resultado}
        )

        if not creado:
            registro.prompt = prompt
            registro.valoraciones = resultado
            registro.save()
        
        return Response({
            'resultado': resultado
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def find_strengths_weaknesses_all_teachers(request):
    try:
        docentes = Usuario.objects.all()

        for docente in docentes:
            comentarios = CalificacionesCualitativas.objects.filter(docente=docente).order_by('promedio')
            
            if not comentarios.exists():
                continue 
            
            mejores_comentarios = list(comentarios.order_by('-promedio')[:5].values_list('comentario', flat=True))
            peores_comentarios = list(comentarios.order_by('promedio')[:5].values_list('comentario', flat=True))
            
            todos_comentarios = mejores_comentarios + peores_comentarios
            if len(todos_comentarios) < 10:
                todos_comentarios = list(comentarios.values_list('comentario', flat=True))
            
            prompt, resultado = analizar_comentarios(todos_comentarios)

            registro, creado = FortalezasDebilidadesCualitativas.objects.get_or_create(
                docente=docente,
                defaults={'prompt': prompt, 'valoraciones': resultado}
            )

            if not creado:
                registro.prompt = prompt
                registro.valoraciones = resultado
                registro.save()
            
        return Response({}, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    


@api_view(['GET'])
def get_cual_fort_deb(request):
    try:
        docente_id = request.query_params.get('docente_id')
        fortdeb = FortalezasDebilidadesCualitativas.objects.filter(docente_id=docente_id).first()

        if not fortdeb:
            return Response({'error': 'No se encontraron registros para el docente con el ID proporcionado'}, status=status.HTTP_404_NOT_FOUND)

        # Serializar el objeto
        serializer = CualFortDebSerializer(fortdeb)

        # Convertir valoraciones a JSON válido
        data = serializer.data
        if isinstance(data.get('valoraciones'), str):
            try:
                # Reemplazar comillas simples por comillas dobles en el string JSON
                data['valoraciones'] = json.loads(data['valoraciones'].replace("'", '"'))
            except json.JSONDecodeError:
                return Response({'error': 'El formato de valoraciones es inválido'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    # Metodo que retorna el top 10 mejores docentes por escuela

@api_view(['GET'])
def get_top_10_docentes_by_school(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrar docentes por escuela y asegurar que son profesores
        docentes = Usuario.objects.filter(escuela_id=escuela_id, is_profesor=True)
        
        # Obtener el promedio de la columna 'promedio' para cada docente
        top_docentes = (
            PromedioCalificaciones.objects.filter(docente__in=docentes)
            .values('docente__id', 'docente__nombre')  # Group by docente
            .annotate(promedio_total=Avg('promedio'))  # Promediar la columna 'promedio' para cada docente
            .order_by('-promedio_total')[:10]  # Ordenar de mayor a menor y obtener los primeros 10
        )

        if not top_docentes:
            return Response({'error': 'No se encontraron docentes para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(list(top_docentes), status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
# Metodo que retorna los promedios cualitativos y cuentitativos de todos los docentes de una escuela.

@api_view(['GET'])
def get_teacher_average_grades_by_school(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrar los docentes que pertenecen a la escuela especificada
        docentes_escuela = Usuario.objects.filter(escuela_id=escuela_id, is_profesor=True)
        
        if not docentes_escuela.exists():
            return Response({'error': 'No se encontraron docentes para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)

        # Obtener promedios individuales para cada docente
        promedios_docentes = []
        for docente in docentes_escuela:
            promedio_docente = PromedioCalificaciones.objects.filter(docente=docente).aggregate(
                promedio_cuant=Avg('promedio_cuant'),
                promedio_cual=Avg('promedio_cual')
            )
            promedios_docentes.append({
                'docente': docente.nombre,
                'promedio_cuantitativo': promedio_docente['promedio_cuant'],
                'promedio_cualitativo': promedio_docente['promedio_cual']
            })

        return Response(promedios_docentes, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

# Metodo que retorna los promedios cualitativos y cuantitativos de todos las escuelas de la facultad

@api_view(['GET'])
def get_school_average_grades(request):
    try:
        # Obtener todas las escuelas registradas
        escuelas = Escuela.objects.all()

        if not escuelas.exists():
            return Response({'error': 'No se encontraron escuelas registradas.'}, status=status.HTTP_404_NOT_FOUND)

        resultados_escuelas = []

        # Iterar sobre cada escuela
        for escuela in escuelas:
            # Filtrar los docentes de la escuela
            docentes_escuela = Usuario.objects.filter(escuela=escuela, is_profesor=True)

            if docentes_escuela.exists():
                # Calcular el promedio cuantitativo y cualitativo de todos los docentes de la escuela
                promedio_escuela = PromedioCalificaciones.objects.filter(docente__in=docentes_escuela).aggregate(
                    promedio_cuant=Avg('promedio_cuant'),
                    promedio_cual=Avg('promedio_cual')
                )

                resultados_escuelas.append({
                    'escuela': escuela.nombre,
                    'promedio_cuantitativo': promedio_escuela['promedio_cuant'],
                    'promedio_cualitativo': promedio_escuela['promedio_cual']
                })

        if not resultados_escuelas:
            return Response({'error': 'No se encontraron promedios para ninguna escuela.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(resultados_escuelas, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    
# Metodo que analiza todos los comentarios de una escuela con un modelo de lenguaje con el objetivo de identificar fortalezas y debilidades generales de los docentes


def analizar_comentarios_escuela(comentarios):
    # Prompt original
    # "Analiza los siguientes comentarios sobre el desempeño de los docentes de una escuela. Identifica cuáles son las fortalezas y oportunidades de mejora de los docentes de la escula en general y devuelve una estructura de datos que contenga las fortalezas y oportunidades de mejora, como maximo genera 5 fortalezas y 5 oporunidades de mejora.\n\n"
    # "\nEstructura de datos esperada:\n{\n {fortalezas: [fortaleza 1, fortaleza 2, fortaleza 3, fortaleza 4, fortaleza 5], oportunidades_mejora: [oportunidad 1, oportunidad 2, oportunidad 3, oportunidad 4, oportunidad 5]}"

    prompt_base = (
        "Analiza los siguientes comentarios sobre el desempeño de los docentes de una escuela. Identifica cuáles son las fortalezas y oportunidades de mejora de los docentes de la escula en general y devuelve una estructura de datos que contenga las fortalezas y oportunidades de mejora, como maximo genera 5 fortalezas y 5 oporunidades de mejora.\n\n"
        "Comentarios de los docentes:\n"
    )
    prompt_ejemplo = "\nEstructura de datos esperada: { fortalezas: [fortaleza 1, fortaleza 2, fortaleza 3, fortaleza 4, fortaleza 5], oportunidades_mejora: [oportunidad 1, oportunidad 2, oportunidad 3, oportunidad 4, oportunidad 5] }"

    comentarios_incluidos = []
    prompt = prompt_base
    for comentario in comentarios:
        prompt += f" {comentario}\n"
    prompt += prompt_ejemplo

    response = extraer_json(laguageModel(prompt))
    return prompt, response


# @api_view(['POST'])
# def find_strengths_weaknesses_school(request):
#     try:
#         escuela_id = request.data.get('escuela_id')
#         if not escuela_id:
#             return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
#         escuela = get_object_or_404(Escuela, pk=escuela_id)
#         comentarios = CalificacionesCualitativas.objects.filter(docente__escuela_id=escuela_id).order_by('promedio')
        
#         if not comentarios:
#             return Response({'error': 'No se encontraron comentarios para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)
        
#         prompt, resultado = analizar_comentarios_escuela(comentarios)

#         registro, creado = FortalezasDebilidadesEscula.objects.get_or_create(
#             escuela=escuela,
#             defaults={'prompt': prompt, 'valoraciones': resultado}
#         )

#         if not creado:
#             registro.prompt = prompt
#             registro.valoraciones = resultado
#             registro.save()
        
#         return Response({
#             'resultado': resultado
#         }, status=status.HTTP_200_OK)
    
#     except Exception as e:
#         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def find_strengths_weaknesses_school(request):
    try:
        escuela_id = request.data.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        escuela = get_object_or_404(Escuela, pk=escuela_id)
        
        # Obtener los 20 comentarios con peor promedio (orden ascendente)
        peores_comentarios = CalificacionesCualitativas.objects.filter(
            docente__escuela_id=escuela_id
        ).order_by('promedio')[:20]
        
        # Obtener los 20 comentarios con mejor promedio (orden descendente)
        mejores_comentarios = CalificacionesCualitativas.objects.filter(
            docente__escuela_id=escuela_id
        ).order_by('-promedio')[:20]
        
        # Combinar ambos conjuntos de comentarios
        comentarios = list(peores_comentarios) + list(mejores_comentarios)
        
        if not comentarios:
            return Response({'error': 'No se encontraron comentarios para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Pasar los comentarios combinados al método de análisis
        prompt, resultado = analizar_comentarios_escuela(comentarios)

        registro, creado = FortalezasDebilidadesEscula.objects.get_or_create(
            escuela=escuela,
            defaults={'prompt': prompt, 'valoraciones': resultado}
        )

        if not creado:
            registro.prompt = prompt
            registro.valoraciones = resultado
            registro.save()
        
        return Response({
            'resultado': resultado
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# @api_view(['POST'])
# def find_strengths_weaknesses_all_schools(request):
#     try:
#         escuelas = Escuela.objects.all()

#         if not escuelas:
#             return Response({'error': 'No se encontraron escuelas.'}, status=status.HTTP_404_NOT_FOUND)
        
#         resultado_general = []

#         for escuela in escuelas:
#             comentarios = CalificacionesCualitativas.objects.filter(docente__escuela=escuela).order_by('promedio')

#             if comentarios:
#                 prompt, resultado = analizar_comentarios_escuela(comentarios)

#                 registro, creado = FortalezasDebilidadesEscula.objects.get_or_create(
#                     escuela=escuela,
#                     defaults={'prompt': prompt, 'valoraciones': resultado}
#                 )

#                 if not creado:
#                     registro.prompt = prompt
#                     registro.valoraciones = resultado
#                     registro.save()

#                 resultado_general.append({
#                     'escuela': escuela.nombre,
#                     'resultado': resultado
#                 })

#         if not resultado_general:
#             return Response({'error': 'No se encontraron comentarios para ninguna escuela.'}, status=status.HTTP_404_NOT_FOUND)

#         return Response({
#             'resultados': resultado_general
#         }, status=status.HTTP_200_OK)

#     except Exception as e:
#         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def find_strengths_weaknesses_all_schools(request):
    try:
        escuelas = Escuela.objects.all()

        if not escuelas:
            return Response({'error': 'No se encontraron escuelas.'}, status=status.HTTP_404_NOT_FOUND)
        
        resultado_general = []

        for escuela in escuelas:
            # Obtener los 20 comentarios con peor promedio (orden ascendente)
            peores_comentarios = CalificacionesCualitativas.objects.filter(
                docente__escuela=escuela
            ).order_by('promedio')[:15]

            # Obtener los 20 comentarios con mejor promedio (orden descendente)
            mejores_comentarios = CalificacionesCualitativas.objects.filter(
                docente__escuela=escuela
            ).order_by('-promedio')[:15]

            # Combinar ambos conjuntos de comentarios
            comentarios = list(peores_comentarios) + list(mejores_comentarios)

            if comentarios:
                # Pasar los comentarios combinados al método de análisis
                prompt, resultado = analizar_comentarios_escuela(comentarios)

                # Crear o actualizar el registro de fortalezas y debilidades
                registro, creado = FortalezasDebilidadesEscula.objects.get_or_create(
                    escuela=escuela,
                    defaults={'prompt': prompt, 'valoraciones': resultado}
                )

                if not creado:
                    registro.prompt = prompt
                    registro.valoraciones = resultado
                    registro.save()

                # Añadir el resultado para esta escuela a la lista general
                resultado_general.append({
                    'escuela': escuela.nombre,
                    'resultado': resultado
                })

        if not resultado_general:
            return Response({'error': 'No se encontraron comentarios para ninguna escuela.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'resultados': resultado_general
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_school_fort_deb(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        fortdeb = FortalezasDebilidadesEscula.objects.filter(escuela_id=escuela_id).first()

        if not fortdeb:
            return Response({'error': 'No se encontraron registros para la escuela con el ID proporcionado'}, status=status.HTTP_404_NOT_FOUND)

        # Serializar el objeto
        serializer = SchoolFortDebSerializer(fortdeb)

        # Convertir valoraciones a JSON válido
        data = serializer.data
        if isinstance(data.get('valoraciones'), str):
            try:
                # Reemplazar comillas simples por comillas dobles en el string JSON
                data['valoraciones'] = json.loads(data['valoraciones'].replace("'", '"'))
            except json.JSONDecodeError:
                return Response({'error': 'El formato de valoraciones es inválido'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Metodo que recibe, almacena y procesa los archivos de las valoraciones cualitativas

@api_view(['POST'])
def upload_qualitative_evaluations(request):
    parser_classes = (MultiPartParser, FormParser)
    
    file = request.FILES.get('file')

    if not file:
        return Response({"error": "No se ha proporcionado un archivo"}, status=status.HTTP_400_BAD_REQUEST)

    # Verificar si el archivo es un archivo Excel
    if not file.name.endswith('.xlsx'):
        return Response({"error": "El archivo debe tener formato .xlsx"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        df = pd.read_excel(file)

        # Validar estructura del archivo
        required_columns = ['SEMESTRE', 'DOCENTE', 'CEDULA', 'ESCUELA', 'COMENTARIO', 'MATERIA', 'CODIGO_MATERIA']
        if not all(column in df.columns for column in required_columns):
            return Response({"error": "El archivo no contiene la estructura esperada"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verificar si el archivo tiene registros
        if df.empty:
            return Response({"error": "El archivo no contiene ningún registro"}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar si alguna columna tiene valores faltantes en los registros
        if df[required_columns].isnull().any().any():
            return Response({"error": "Algunas columnas tienen valores faltantes"}, status=status.HTTP_400_BAD_REQUEST)

        # Proceso de análisis de datos
        procesar_evaluaciones_cualitativas(df)

        return Response({"message": "Archivo procesado correctamente"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Metodo que recibe, almacena y procesa los archivos de las valoraciones cuantitativas

@api_view(['POST'])
def upload_quantitative_evaluations(request):
    parser_classes = (MultiPartParser, FormParser)
    
    file = request.FILES.get('file')

    if not file:
        return Response({"error": "No se ha proporcionado un archivo"}, status=status.HTTP_400_BAD_REQUEST)

    # Verificar si el archivo es un archivo Excel
    if not file.name.endswith('.xlsx'):
        return Response({"error": "El archivo debe tener formato .xlsx"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        df = pd.read_excel(file)

        # Validar estructura del archivo
        required_columns = ['SEMESTRE', 'DOCENTE', 'CEDULA', 'ESCUELA', 'PROM_PREGUNTA9', 'PROM_PREGUNTA10',
                            'PROM_PREGUNTA11', 'PROM_PREGUNTA12', 'PROM_PREGUNTA13', 'PROM_PREGUNTA14', 
                            'PROM_PREGUNTA15', 'PROM_PREGUNTA16', 'PROM_PREGUNTA17', 'PROM_PREGUNTA18',    
                            'PROM_PREGUNTA19', 'PROM_PREGUNTA20', 'PROM_DOCENTE', 'MATERIA', 'CODIGO_MATERIA']
        if not all(column in df.columns for column in required_columns):
            return Response({"error": "El archivo no contiene la estructura esperada"}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar si el archivo tiene registros
        if df.empty:
            return Response({"error": "El archivo no contiene ningún registro"}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar si alguna columna tiene valores faltantes en los registros
        if df[required_columns].isnull().any().any():
            return Response({"error": "Algunas columnas tienen valores faltantes"}, status=status.HTTP_400_BAD_REQUEST)

        # Proceso de análisis de datos
        procesar_evaluaciones_cuantitativas(df)

        return Response({"message": "Archivo procesado correctamente"}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_Schools(request):
    try:
        # Obtener todas las escuelas
        escuelas = Escuela.objects.all()

        if not escuelas:
            return Response({'error': 'No se encontraron registros de escuelas'}, status=status.HTTP_404_NOT_FOUND)

        # Serializar los objetos de escuelas
        serializer = SchoolSerializer(escuelas, many=True)

        # Retornar los datos serializados
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
