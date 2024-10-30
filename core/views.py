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
import re
import json
import time

from .utils.fortalezas_debilidades.cual_fort_deb import laguageModel
from .utils.procesar_evaluaciones.cualitativas import procesar_evaluaciones_cualitativas
from .utils.procesar_evaluaciones.cuantitativas import procesar_evaluaciones_cuantitativas

#-------------------------------------------------------------------
#   Metodo que permite a los usuarios autenticarse en la aplicación
#-------------------------------------------------------------------

@api_view(['POST'])
def user_login(request):
    serializer = AuthTokenSerializer(data=request.data)
    if serializer.is_valid():
        try:
            user = Usuario.objects.get(email=serializer.validated_data['email'])
        except Usuario.DoesNotExist:
            return Response({"error": "Credenciales incorrectas"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.is_active:
            return Response({"error": "Este usuario ha sido desactivado, comuníquese con el administrador del sistema para gestionar su ingreso"}, status=status.HTTP_403_FORBIDDEN)

        if not user.check_password(serializer.validated_data['password']):
            return Response({"error": "Credenciales incorrectas"}, status=status.HTTP_400_BAD_REQUEST)
        
        token, created = Token.objects.get_or_create(user=user)

        user_serializer = UsuarioSerializer(instance=user)
        return Response({'token': token.key, 'user': user_serializer.data}, status=status.HTTP_200_OK)
    
    return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

#-------------------------------------------------------------------
# Metodo que permite a los administradores registrar nuevos usuarios
#-------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
def user_register(request):
    serializer = UsuarioSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        user.set_password(serializer.validated_data['password'])
        user.save()

        token = Token.objects.create(user=user)
        return Response({'user': serializer.data}, status=status.HTTP_201_CREATED)
    
    return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

#-------------------------------------------------------------------------
# Metodo que permite modificar los datos del usuario con el id ingresado 
#-------------------------------------------------------------------------

@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def update_user_by_admin(request, user_id):
    token_key = request.auth
    token = get_object_or_404(Token, key=token_key)

    admin_user = token.user

    if not admin_user.is_admin:
        return Response({'detail': 'Unauthorized. Admin access required.'}, status=status.HTTP_401_UNAUTHORIZED)

    user = get_object_or_404(Usuario, id=user_id)
    serializer = UsuarioSerializer(user, data=request.data, partial=True)  # partial=True permite actualizaciones parciales

    if serializer.is_valid():
        if 'password' in request.data:
            user.set_password(request.data['password'])
            user.save() 

        serializer.save(password=user.password)
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#-----------------------------------------------------------------
# Metodo que permite al usuario modificar su contraseña de ingreso
#-----------------------------------------------------------------

@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_self_change_password(request):
    token_key = request.auth
    token = get_object_or_404(Token, key=token_key)
    user = token.user

    if user.codigo != request.data.get('cedula'):
        return Response({'error': 'No puede modificar la contraseña de otro usuario'}, status=status.HTTP_400_BAD_REQUEST)

    new_password = request.data.get('password')
    if new_password:
        user.set_password(new_password)
        user.save()

    return Response({'message': 'Contraseña actualizada exitosamente'}, status=status.HTTP_200_OK)

#------------------------------------------------------------------------------
# Metodo permite a los administradores obtener la lista de usuarios del sistema
#------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated]) 
def list_users_except_self(request):
    print("entre a la vista")

    current_user = request.user
    if not current_user.is_admin:
        return Response({'detail': 'Unauthorized. Admin access required.'}, status=status.HTTP_401_UNAUTHORIZED)

    users = Usuario.objects.exclude(id=current_user.id)
    serializer = UsuarioSerializer(users, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)

#------------------------------------------------
# Este metodo retorna la información del ususario
#------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_profile(request):
    serializer = UsuarioSerializer(instance=request.user)
    return Response({'user':serializer.data},status=status.HTTP_200_OK)

#---------------------------------------------------------------------------------------------------------------------------------------------------
#   Metodo que retorna los registros de calificaciones promedio de todos los docentes, de la escuela con id ingresado o del docente con id ingresado
#---------------------------------------------------------------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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
    
#----------------------------------------------------------------------------------------------
# Metodo que retorna las fortalezas y debilidades cuantitaticas del docente con el id engresado  
#----------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
def get_cuant_fort_deb(request):
    try:
        docente_id = request.query_params.get('docente_id')
        fortdeb = FortalezasDebilidadesCuantitativas.objects.filter(docente_id=docente_id).first()

        if not fortdeb:
            return Response({'error': 'No existen fortalezas y debilidades cuantitativas para el docente con el ID proporcionado'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CuantFortDebSerializer(fortdeb)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#------------------------------------------------------------------------------------------------
# Metodo que retorna los comentarios con mayor y menor valoración del docente con el id ingresado
#------------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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
    
#-------------------------------------------------------------------------------------------------------------
#Metodo que retorna el los promedios generales, cuantitativos y cualitativos del docente ingresado
#-------------------------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
def get_average_grades(request):
    try:
        docente_id = request.query_params.get('docente_id')
        if not docente_id:
            return Response({'error': 'El parámetro docente_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        calificaciones = PromedioCalificaciones.objects.filter(docente_id=docente_id)
        
        promedio_cual = calificaciones.filter(promedio_cual__gt=0).aggregate(promedio_cual=Avg('promedio_cual'))['promedio_cual']
        promedio_cuant = calificaciones.filter(promedio_cuant__gt=0).aggregate(promedio_cuant=Avg('promedio_cuant'))['promedio_cuant']
        
        if promedio_cual is None and promedio_cuant is None:
            return Response({'error': 'No se encontraron calificaciones para el docente proporcionado.'}, status=status.HTTP_404_NOT_FOUND)

        if promedio_cual is not None and promedio_cuant is not None:
            promedio = (promedio_cual + promedio_cuant) / 2
        elif promedio_cual is not None:
            promedio = promedio_cual
        else:
            promedio = promedio_cuant

        return Response({
            'promedio': promedio,
            'promedio_cual': promedio_cual,
            'promedio_cuant': promedio_cuant
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

#-------------------------------------------------------------------------------------------------------------
#   Metodo que calcula y retornalas calificaciones promedio de la escuela con el id ingresado
#-------------------------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_average_grades_school_and_overall(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        promedio_general_cual = PromedioCalificaciones.objects.filter(promedio_cual__gt=0).aggregate(promedio_cual=Avg('promedio_cual'))['promedio_cual']
        promedio_general_cuant = PromedioCalificaciones.objects.filter(promedio_cuant__gt=0).aggregate(promedio_cuant=Avg('promedio_cuant'))['promedio_cuant']
        
        if promedio_general_cual is not None and promedio_general_cuant is not None:
            promedio_general = (promedio_general_cual + promedio_general_cuant) / 2
        elif promedio_general_cual is not None:
            promedio_general = promedio_general_cual
        else:
            promedio_general = promedio_general_cuant

        promedio_escuela_cual = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id, promedio_cual__gt=0).aggregate(promedio_cual=Avg('promedio_cual'))['promedio_cual']
        promedio_escuela_cuant = PromedioCalificaciones.objects.filter(docente__escuela_id=escuela_id, promedio_cuant__gt=0).aggregate(promedio_cuant=Avg('promedio_cuant'))['promedio_cuant']
        
        if promedio_escuela_cual is not None and promedio_escuela_cuant is not None:
            promedio_escuela = (promedio_escuela_cual + promedio_escuela_cuant) / 2
        elif promedio_escuela_cual is not None:
            promedio_escuela = promedio_escuela_cual
        else:
            promedio_escuela = promedio_escuela_cuant

        if promedio_escuela is None:
            return Response({'error': 'No se encontraron calificaciones para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
                'promedio_facultad': promedio_general,
                'promedio_facultad_cuantitativo': promedio_general_cuant,
                'promedio_facultad_cualitativo': promedio_general_cual,
                'promedio_escuela': promedio_escuela,
                'promedio_escuela_cuantitativo': promedio_escuela_cuant,
                'promedio_escuela_cualitativo': promedio_escuela_cual,
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)  
    
#-------------------------------------------------------------------------------------------------------------
# Metodo para obtener la información sobre promedios cualitativos de facultad, docente y escuela
#-------------------------------------------------------------------------------------------------------------

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
        
        promedio_facultad = PromedioCalificaciones.objects.filter(promedio_cual__gt=0).aggregate(promedio=Avg('promedio_cual'))['promedio']

        promedio_escuela = None
        promedio_docente = None

        if escuela_id:
            promedio_escuela = PromedioCalificaciones.objects.filter(
                promedio_cual__gt=0,
                docente__escuela_id=escuela_id
            ).aggregate(promedio=Avg('promedio_cual'))['promedio']

        promedio_docente = PromedioCalificaciones.objects.filter( 
            promedio_cual__gt=0,
            docente_id=docente_id
        ).aggregate(promedio=Avg('promedio_cual'))['promedio']

        response_data = {
            'promedio_facultad': promedio_facultad if promedio_facultad is not None else 'No se encontraron calificaciones para la facultad.',
            'promedio_escuela': promedio_escuela if promedio_escuela is not None else 'No se encontraron calificaciones para la escuela proporcionada.',
            'promedio_docente': promedio_docente if promedio_docente is not None else 'No se encontraron calificaciones para el docente proporcionado.'
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

#-------------------------------------------------------------------------------------------------------------
# Metodo para obtener la información sobre promedios cuantitativos de facultad, docente y escuela
#-------------------------------------------------------------------------------------------------------------

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
        
        promedio_facultad = PromedioCalificaciones.objects.filter(promedio_cuant__gt=0).aggregate(promedio=Avg('promedio_cuant'))['promedio']

        promedio_escuela = None
        promedio_docente = None

        if escuela_id:
            promedio_escuela = PromedioCalificaciones.objects.filter(
                promedio_cuant__gt=0,
                docente__escuela_id=escuela_id,
            ).aggregate(promedio=Avg('promedio_cuant'))['promedio']

        promedio_docente = PromedioCalificaciones.objects.filter( 
            promedio_cuant__gt=0,
            docente_id=docente_id,
        ).aggregate(promedio=Avg('promedio_cuant'))['promedio']

        response_data = {
            'promedio_facultad': promedio_facultad if promedio_facultad is not None else 'No se encontraron calificaciones cuantitativas para la facultad.',
            'promedio_escuela': promedio_escuela if promedio_escuela is not None else 'No se encontraron calificaciones cuantitativas para la escuela proporcionada.',
            'promedio_docente': promedio_docente if promedio_docente is not None else 'No se encontraron calificaciones cuantitativas para el docente proporcionado.'
        }
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

#-------------------------------------------------------------------------------------------------------------    
# Metodo que genera y envia un wordcloud en base 64 generado con las palabras mas repetidas en un texto
#-------------------------------------------------------------------------------------------------------------

def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    buffer = BytesIO()
    wordcloud.to_image().save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()

#-------------------------------------------------------------------------------------------------------------
#  Metodo que se encarga de generar y retornar el wordcloud de los comentarios del docente con el id ingresado
#-------------------------------------------------------------------------------------------------------------

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
    
#---------------------------------------------------------------------------------------------------------
#  Metodo que se encarga de extraer la estructura JSON de la respuesta generada por el modelo de lenguaje
#---------------------------------------------------------------------------------------------------------

def extraer_json(respuesta):
    # Intentar buscar el bloque JSON dentro de la respuesta
    json_match = re.search(r'\{.*\}', respuesta, re.DOTALL)
    
    if json_match:
        json_str = json_match.group()  # Obtener el string que coincide con la expresión regular
        try:
            # Intentar decodificar el string como JSON
            datos = json.loads(json_str)
            return datos
        except json.JSONDecodeError as e:
            # Si falla la decodificación, devolver el error y la respuesta original para mayor claridad
            print(f"Error al decodificar el JSON: {e}")
            return {"error": "Error al decodificar el JSON", "respuesta_original": respuesta}
    else:
        # Si no encuentra JSON en la respuesta, retornar la respuesta original como error
        return {"error": "No se encontró un bloque JSON en la respuesta", "respuesta_original": respuesta}

#---------------------------------------------------------------------------------------------------------------------------------------------------
#   Metodo que se encarga de analizar los comentarios ingresados con el modelo de lenguaje para identificar fortalezas y debilidades de los docentes
#---------------------------------------------------------------------------------------------------------------------------------------------------

def analizar_comentarios(comentarios, max_reintentos=3, delay_reintento=2):
    prompt_base = (
        """
        Analiza los siguientes comentarios sobre el desempeño de un docente. 
        Identifica cuáles son las fortalezas y oportunidades de mejora (debilidades) del docente y 
        genera una estructura de datos en formato JSON similar a la que se indica a continuación.
        Cada una de las fortalezas y oportunidades de mejora (debilidades) debe tener un valor asignado 
        dentro de la siguiente escala: 1 siendo Muy Pobre, 2 siendo Pobre, 3 siendo Neutro, 4 siendo Bueno, y 5 siendo Muy Bueno".
        Asegúrate de que el JSON tenga exactamente 5 fortalezas y 5 oportunidades de mejora, o menos si no es posible identificar todas. 
        No agregues explicaciones adicionales fuera del formato JSON.

        Comentarios del docente:
        """
    )

    prompt_ejemplo = """ 
        Formato de la respuesta esperada (en JSON):
        {
            "fortalezas": { "fortaleza 1": puntuación, "fortaleza 2": puntuación, "fortaleza 3": puntuación, "fortaleza 4": puntuación, "fortaleza 5": puntuación},
            "debilidades": {"debilidad 1": puntuación, "debilidad 2": puntuación, "debilidad 3": puntuación, "debilidad 4": puntuación, "debilidad 5": puntuación}
        }
    """ 

    comentarios_incluidos = "\n".join([f"{comentario}" for comentario in comentarios])
    prompt = f"{prompt_base}\n{comentarios_incluidos}\n{prompt_ejemplo}"

    reintento = 0
    while reintento < max_reintentos:
        try:
            respuesta_modelo = laguageModel(prompt)
             # Extraer el JSON de la respuesta

            # Verificar si la respuesta es un simple eco del ejemplo proporcionado
            if "fortaleza 1" in respuesta_modelo.lower() or "debilidad 1" in respuesta_modelo.lower():
                raise ValueError("La respuesta parece ser un eco del ejemplo.")

            respuesta_json = extraer_json(respuesta_modelo)

            if "error" in respuesta_json:
                raise ValueError(f"Error en la extracción del JSON: {respuesta_json['error']}")
            
            if "fortalezas" not in respuesta_json or "debilidades" not in respuesta_json:
                raise ValueError("La estructura JSON no contiene las claves 'fortalezas' o 'debilidades'.")
            
            return prompt, respuesta_json
        
        except (json.JSONDecodeError, ValueError) as e:
            reintento += 1
            if reintento >= max_reintentos:
                return prompt, {"error": f"Error al procesar los comentarios después de {max_reintentos} intentos: {str(e)}"}
            else:
                time.sleep(delay_reintento)

    return prompt, {"error": "No se pudo obtener una respuesta válida después de varios intentos."}

#---------------------------------------------------------------------------------------------------------------------------
#Metodo que analiza los 10 comentario mas relevantes del docente con el id ingresado y determina sus fortalezas y debilidades
#--------------------------------------------------------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
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

#---------------------------------------------------------------------------------------------------------------------------
#   Metodo que ejecuta el analisis de los comentarios de cada docente para encontrar su fortalezas y oportunidades de mejora
#---------------------------------------------------------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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

#----------------------------------------------------------------------------------------------------   
#   Metodo que retorna las fortalezas y oportunidades de mejora para el docente con el id ingresado
#----------------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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
    
#-------------------------------------------------------------------------
# Metodo que retorna el top 10 de docentes con mejor promedio por escuela
#-------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
def get_top_10_docentes_by_school(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        docentes = Usuario.objects.filter(escuela_id=escuela_id, is_profesor=True)
        
        top_docentes = (
            PromedioCalificaciones.objects.filter(docente__in=docentes)
            .values('docente__id', 'docente__nombre')
            .annotate(promedio_total=Avg('promedio'))
            .order_by('-promedio_total')[:10]
        )
        if not top_docentes:
            return Response({'error': 'No se encontraron docentes para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(list(top_docentes), status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

#----------------------------------------------------------------------------------------------------
# Metodo que retorna los promedios cualitativos y cuentitativos de todos los docentes de una escuela.
#----------------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  

def get_teacher_average_grades_by_school(request):
    try:
        escuela_id = request.query_params.get('escuela_id')
        if not escuela_id:
            return Response({'error': 'El parámetro escuela_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)
        
        docentes_escuela = Usuario.objects.filter(escuela_id=escuela_id, is_profesor=True)
        
        if not docentes_escuela.exists():
            return Response({'error': 'No se encontraron docentes para la escuela proporcionada.'}, status=status.HTTP_404_NOT_FOUND)

        promedios_docentes = []
        for docente in docentes_escuela:

            promedio_cuantitativo = PromedioCalificaciones.objects.filter(docente=docente, promedio_cuant__gt=0).aggregate(promedio=Avg('promedio_cuant'))['promedio']
            promedio_cualitativo = PromedioCalificaciones.objects.filter(docente=docente, promedio_cual__gt=0).aggregate(promedio=Avg('promedio_cual'))['promedio']

            promedios_docentes.append({
                'docente': docente.nombre,
                'promedio_cuantitativo': promedio_cuantitativo if promedio_cuantitativo is not None else 'No se encontraron calificaciones cuantitativas.',
                'promedio_cualitativo': promedio_cualitativo if promedio_cualitativo is not None else 'No se encontraron calificaciones cualitativas.'
            })

        return Response(promedios_docentes, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
#----------------------------------------------------------------------------------------------------
# Metodo que retorna los promedios cualitativos y cuantitativos de todos las escuelas de la facultad
#----------------------------------------------------------------------------------------------------

@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
def get_school_average_grades(request):
    try:
        escuelas = Escuela.objects.all()

        if not escuelas.exists():
            return Response({'error': 'No se encontraron escuelas registradas.'}, status=status.HTTP_404_NOT_FOUND)

        resultados_escuelas = []
        for escuela in escuelas:
            docentes_escuela = Usuario.objects.filter(escuela=escuela, is_profesor=True)

            if docentes_escuela.exists():

                promedio_cuantitativo = PromedioCalificaciones.objects.filter(
                    docente__in=docentes_escuela,
                    promedio_cuant__gt=0
                ).aggregate(promedio=Avg('promedio_cuant'))['promedio']

                promedio_cualitativo = PromedioCalificaciones.objects.filter(
                    docente__in=docentes_escuela,
                    promedio_cual__gt=0
                ).aggregate(promedio=Avg('promedio_cual'))['promedio']

                resultados_escuelas.append({
                    'escuela': escuela.nombre,
                    'promedio_cuantitativo': promedio_cuantitativo if promedio_cuantitativo is not None else 'No se encontraron calificaciones cuantitativas.',
                    'promedio_cualitativo': promedio_cualitativo if promedio_cualitativo is not None else 'No se encontraron calificaciones cualitativas.'
                })

        if not resultados_escuelas:
            return Response({'error': 'No se encontraron promedios para ninguna escuela.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(resultados_escuelas, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Metodo que analiza todos los comentarios de una escuela con un modelo de lenguaje con el objetivo de identificar fortalezas y debilidades generales de los docentes

# def analizar_comentarios_escuela(comentarios):
#     # Prompt original
#     # "Analiza los siguientes comentarios sobre el desempeño de los docentes de una escuela. Identifica cuáles son las fortalezas y oportunidades de mejora de los docentes de la escula en general y devuelve una estructura de datos que contenga las fortalezas y oportunidades de mejora, como maximo genera 5 fortalezas y 5 oporunidades de mejora.\n\n"
#     # "\nEstructura de datos esperada:\n{\n {fortalezas: [fortaleza 1, fortaleza 2, fortaleza 3, fortaleza 4, fortaleza 5], oportunidades_mejora: [oportunidad 1, oportunidad 2, oportunidad 3, oportunidad 4, oportunidad 5]}"

#     prompt_base = (
#         """Analiza los siguientes comentarios sobre el desempeño de los docentes de una escuela. Identifica las fortalezas y oportunidades de mejora generales que tienen estos docentes y genera una estructura de datos en formato JSON estrictamente como se indica a continuación. Asegúrate de que el JSON tenga exactamente 5 fortalezas y 5 oportunidades de mejora, o menos si no es posible identificar todas. No agregues explicaciones adicionales fuera del formato JSON.

#         Comentarios de los docentes:"""
    
#     )
#     prompt_ejemplo = """ Formato de la respuesta esperada (en JSON):
#                     {
#                     "fortalezas": ["fortaleza 1", "fortaleza 2", "fortaleza 3", "fortaleza 4", "fortaleza 5"],
#                     "oportunidades_mejora": ["oportunidad 1", "oportunidad 2", "oportunidad 3", "oportunidad 4", "oportunidad 5"]
#                     }"""

#     comentarios_incluidos = []
#     prompt = prompt_base
#     for comentario in comentarios:
#         prompt += f" {comentario}\n"
#     prompt += prompt_ejemplo

#     response = extraer_json(laguageModel(prompt))
#     return prompt, response

# def analizar_comentarios_escuela(comentarios):
#     # Prompt base
#     prompt_base = (
#         """Analiza los siguientes comentarios sobre el desempeño de los docentes de una escuela. 
#         Identifica las fortalezas y oportunidades de mejora generales que tienen estos docentes y 
#         genera una estructura de datos en formato JSON estrictamente como se indica a continuación. 
#         Asegúrate de que el JSON tenga exactamente 5 fortalezas y 5 oportunidades de mejora, o menos si no es posible identificar todas. 
#         No agregues explicaciones adicionales fuera del formato JSON.

#         Comentarios de los docentes:
#         """
#     )
    
#     # Ejemplo de formato esperado
#     prompt_ejemplo = """
#         Formato de la respuesta esperada (en JSON):
#         {
#             "fortalezas": ["fortaleza 1", "fortaleza 2", "fortaleza 3", "fortaleza 4", "fortaleza 5"],
#             "oportunidades_mejora": ["oportunidad 1", "oportunidad 2", "oportunidad 3", "oportunidad 4", "oportunidad 5"]
#         }
#     """
    
#     # Unimos todos los comentarios al prompt
#     comentarios_incluidos = "\n".join([f"{comentario}" for comentario in comentarios])
#     prompt = f"{prompt_base}\n{comentarios_incluidos}\n{prompt_ejemplo}"
    
#     try:
#         # Llamada al modelo de lenguaje
#         respuesta_modelo = laguageModel(prompt)
        
#         # Extraer solo el JSON de la respuesta del modelo
#         respuesta_json = extraer_json(respuesta_modelo)
        
#         # Validar que la respuesta sea un JSON válido
#         datos = json.loads(respuesta_json)
        
#         # Verificar que la estructura contenga las claves esperadas
#         if "fortalezas" not in datos or "oportunidades_mejora" not in datos:
#             raise ValueError("La estructura JSON no contiene las claves 'fortalezas' o 'oportunidades_mejora'.")
        
#         # Asegurarse de que la longitud de las listas no sea mayor a 5
#         datos["fortalezas"] = datos["fortalezas"][:5]
#         datos["oportunidades_mejora"] = datos["oportunidades_mejora"][:5]

#         return prompt, datos
    
#     except (json.JSONDecodeError, ValueError) as e:
#         # Si ocurre algún error, devolver una respuesta con un formato de error
#         return prompt, {"error": f"Error al procesar los comentarios: {str(e)}"}


#---------------------------------------------------------------------------------------------------------------------------------------------------
#   Metodo que se encarga de analizar los comentarios ingresados con el modelo de lenguaje para identificar fortalezas y debilidades de las escuelas
#---------------------------------------------------------------------------------------------------------------------------------------------------

def analizar_comentarios_escuela(comentarios, max_reintentos=3, delay_reintento=1):
    print("numero de comentarios: ", len(comentarios))
    prompt_base = (
        """Analiza los siguientes comentarios sobre el desempeño de los docentes de una escuela. 
        Identifica las fortalezas y oportunidades de mejora generales que tienen estos docentes y 
        genera una estructura de datos en formato JSON estrictamente como se indica a continuación. 
        Asegúrate de que el JSON tenga exactamente 5 fortalezas y 5 oportunidades de mejora, o menos si no es posible identificar todas. 
        No agregues explicaciones adicionales fuera del formato JSON.

        Comentarios de los docentes:
        """
    )
    
    prompt_ejemplo = """
        Formato de la respuesta esperada (en JSON):
        {
            "fortalezas": ["fortaleza 1", "fortaleza 2", "fortaleza 3", "fortaleza 4", "fortaleza 5"],
            "oportunidades_mejora": ["oportunidad 1", "oportunidad 2", "oportunidad 3", "oportunidad 4", "oportunidad 5"]
        }
    """
    
    comentarios_incluidos = "\n".join([f"{comentario}" for comentario in comentarios])
    prompt = f"{prompt_base}\n{comentarios_incluidos}\n{prompt_ejemplo}"
    
    reintento = 0
    while reintento < max_reintentos:
        try:
            # Llamada al modelo de lenguaje
            respuesta_modelo = laguageModel(prompt)
            
            # Extraer el JSON de la respuesta
            respuesta_json = extraer_json(respuesta_modelo)
            
            # Verificar si extraer_json devolvió un error
            if "error" in respuesta_json:
                raise ValueError(f"Error en la extracción del JSON: {respuesta_json['error']}")

            # Asegurarse de que la estructura JSON tenga las claves esperadas
            if "fortalezas" not in respuesta_json or "oportunidades_mejora" not in respuesta_json:
                raise ValueError("La estructura JSON no contiene las claves 'fortalezas' o 'oportunidades_mejora'.")
            
            # Limitar a 5 fortalezas y 5 oportunidades
            respuesta_json["fortalezas"] = respuesta_json["fortalezas"][:5]
            respuesta_json["oportunidades_mejora"] = respuesta_json["oportunidades_mejora"][:5]

            return prompt, respuesta_json
        
        except (json.JSONDecodeError, ValueError) as e:
            reintento += 1
            if reintento >= max_reintentos:
                return prompt, {"error": f"Error al procesar los comentarios después de {max_reintentos} intentos: {str(e)}"}
            else:
                time.sleep(delay_reintento)

    return prompt, {"error": "No se pudo obtener una respuesta válida después de varios intentos."}

#-----------------------------------------------------------------------------------------------------------------------------
#   Metodo que se encarga de pedirle al modelo de lenguae buscar las fortalezas y debilidades de la ecuela con el id ingresado
#-----------------------------------------------------------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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
#             # Obtener los 20 comentarios con peor promedio (orden ascendente)
#             peores_comentarios = CalificacionesCualitativas.objects.filter(
#                 docente__escuela=escuela
#             ).order_by('promedio')[:15]

#             # Obtener los 20 comentarios con mejor promedio (orden descendente)
#             mejores_comentarios = CalificacionesCualitativas.objects.filter(
#                 docente__escuela=escuela
#             ).order_by('-promedio')[:15]

#             # Combinar ambos conjuntos de comentarios
#             comentarios = list(peores_comentarios) + list(mejores_comentarios)

#             if comentarios:
#                 # Pasar los comentarios combinados al método de análisis
#                 prompt, resultado = analizar_comentarios_escuela(comentarios)

#                 # Crear o actualizar el registro de fortalezas y debilidades
#                 registro, creado = FortalezasDebilidadesEscula.objects.get_or_create(
#                     escuela=escuela,
#                     defaults={'prompt': prompt, 'valoraciones': resultado}
#                 )

#                 if not creado:
#                     registro.prompt = prompt
#                     registro.valoraciones = resultado
#                     registro.save()

#                 # Añadir el resultado para esta escuela a la lista general
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

# @api_view(['POST'])
# def find_strengths_weaknesses_all_schools(request):
#     try:
#         escuelas = Escuela.objects.all()

#         if not escuelas:
#             return Response({'error': 'No se encontraron escuelas.'}, status=status.HTTP_404_NOT_FOUND)
        
#         resultado_general = []

#         for escuela in escuelas:
#             docentes = Usuario.objects.filter(escuela=escuela, is_profesor=True)

#             if not docentes:
#                 continue  # Si no hay docentes en la escuela, pasar a la siguiente

#             comentarios_por_escuela = []

#             for docente in docentes:
#                 # Obtener los 2 peores comentarios del docente (orden ascendente)
#                 peores_comentarios = CalificacionesCualitativas.objects.filter(
#                     docente=docente
#                 ).order_by('promedio')[:1]

#                 # Obtener los 2 mejores comentarios del docente (orden descendente)
#                 mejores_comentarios = CalificacionesCualitativas.objects.filter(
#                     docente=docente
#                 ).order_by('-promedio')[:1]

#                 # Combinar ambos conjuntos de comentarios
#                 comentarios = list(peores_comentarios) + list(mejores_comentarios)

#                 # Añadir los comentarios del docente a la lista de comentarios por escuela
#                 comentarios_por_escuela.extend(comentarios)

#             if comentarios_por_escuela:
#                 # Pasar todos los comentarios de la escuela al método de análisis
#                 prompt, resultado = analizar_comentarios_escuela(comentarios_por_escuela)

#                 # Crear o actualizar el registro de fortalezas y debilidades
#                 registro, creado = FortalezasDebilidadesEscula.objects.get_or_create(
#                     escuela=escuela,
#                     defaults={'prompt': prompt, 'valoraciones': resultado}
#                 )

#                 if not creado:
#                     registro.prompt = prompt
#                     registro.valoraciones = resultado
#                     registro.save()

#                 # Añadir el resultado para esta escuela a la lista general
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


#Version buena
# @api_view(['POST'])
# def find_strengths_weaknesses_all_schools(request):
#     try:
#         escuelas = Escuela.objects.all()
#         if not escuelas:
#             return Response({'error': 'No se encontraron escuelas.'}, status=status.HTTP_404_NOT_FOUND)
        
#         resultado_general = []
#         for escuela in escuelas:
#             docentes = Usuario.objects.filter(escuela=escuela, is_profesor=True)
#             if not docentes:
#                 continue 

#             # Filtrar los docentes que tienen registros en la tabla PromedioCalificaciones
#             promedios = PromedioCalificaciones.objects.filter(docente__in=docentes).values('docente').annotate(promedio_cual=Avg('promedio_cual')).order_by('-promedio_cual')

#             # Obtener los 10 docentes con mayor promedio cualitativo
#             top_10_docentes = promedios[:10]
#             # Obtener los 10 docentes con menor promedio cualitativo
#             bottom_10_docentes = promedios.reverse()[:10]

#             # Unir los docentes seleccionados
#             docentes_seleccionados = list(top_10_docentes) + list(bottom_10_docentes)

#             comentarios_por_escuela = []

#             for docente in docentes_seleccionados:
#                 # Obtener el objeto Usuario del docente
#                 docente_obj = Usuario.objects.get(id=docente['docente'])

#                 # Obtener los peores comentarios del docente (orden ascendente)
#                 peores_comentarios = CalificacionesCualitativas.objects.filter(
#                     docente=docente_obj
#                 ).order_by('promedio')[:1]

#                 # Obtener los mejores comentarios del docente (orden descendente)
#                 mejores_comentarios = CalificacionesCualitativas.objects.filter(
#                     docente=docente_obj
#                 ).order_by('-promedio')[:1]

#                 # Combinar ambos conjuntos de comentarios
#                 comentarios = list(peores_comentarios) + list(mejores_comentarios)

#                 # Añadir los comentarios del docente a la lista de comentarios por escuela
#                 comentarios_por_escuela.extend(comentarios)

#             if comentarios_por_escuela:
#                 # Pasar todos los comentarios de la escuela al método de análisis
#                 prompt, resultado = analizar_comentarios_escuela(comentarios_por_escuela)

#                 # Crear o actualizar el registro de fortalezas y debilidades
#                 registro, creado = FortalezasDebilidadesEscula.objects.get_or_create(
#                     escuela=escuela,
#                     defaults={'prompt': prompt, 'valoraciones': resultado}
#                 )

#                 if not creado:
#                     registro.prompt = prompt
#                     registro.valoraciones = resultado
#                     registro.save()

#                 # Añadir el resultado para esta escuela a la lista general
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

#------------------------------------------------------------------------------------------------------------------
#   Metodo que se encarga de pedirle al modelo de lenguae buscar las fortalezas y debilidades de todas las ecuelas
#------------------------------------------------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
def find_strengths_weaknesses_all_schools(request):
    try:
        escuelas = Escuela.objects.all()

        if not escuelas:
            return Response({'error': 'No se encontraron escuelas.'}, status=status.HTTP_404_NOT_FOUND)
        
        resultado_general = []

        for escuela in escuelas:
            docentes = Usuario.objects.filter(escuela=escuela, is_profesor=True)

            if not docentes:
                continue  

            promedios = PromedioCalificaciones.objects.filter(docente__in=docentes).values('docente').annotate(promedio_cual=Avg('promedio_cual')).order_by('-promedio_cual')

            # Obtener los 10 docentes con mayor promedio cualitativo
            top_10_docentes = promedios[:10]
            # Obtener los 10 docentes con menor promedio cualitativo
            bottom_10_docentes = promedios.reverse()[:10]

            # Unir los docentes seleccionados
            seleccionados = list(top_10_docentes) + list(bottom_10_docentes)
            total_docentes = len(seleccionados)

            # Si hay menos de 20 docentes, ajustamos la cantidad de comentarios a tomar
            comentarios_por_docente = 1  # Por defecto 1 comentario (mejor y peor) por docente
            if total_docentes < 20:
                print('menos de 20 docentes')
                comentarios_por_docente = (40 // total_docentes)  # Dividir para obtener más comentarios por docente

            comentarios_por_escuela = []

            for docente in seleccionados:
                # Obtener el objeto Usuario del docente
                docente_obj = Usuario.objects.get(id=docente['docente'])

                # Obtener los peores comentarios del docente (orden ascendente)
                peores_comentarios = CalificacionesCualitativas.objects.filter(
                    docente=docente_obj
                ).order_by('promedio')[:comentarios_por_docente]

                # Obtener los mejores comentarios del docente (orden descendente)
                mejores_comentarios = CalificacionesCualitativas.objects.filter(
                    docente=docente_obj
                ).order_by('-promedio')[:comentarios_por_docente]

                # Combinar ambos conjuntos de comentarios
                comentarios = list(peores_comentarios) + list(mejores_comentarios)

                # Añadir los comentarios del docente a la lista de comentarios por escuela
                comentarios_por_escuela.extend(comentarios)

            # Ajustar la cantidad de comentarios si excede los 40
            comentarios_por_escuela = comentarios_por_escuela[:40]

            if comentarios_por_escuela:
                # Pasar todos los comentarios de la escuela al método de análisis
                prompt, resultado = analizar_comentarios_escuela(comentarios_por_escuela)

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

#---------------------------------------------------------------------------------------------------
#   Metodo que retorna las fortlezas y debilidades de la escuela con el id ingresado
#---------------------------------------------------------------------------------------------------
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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

#---------------------------------------------------------------------------------------------------
# Metodo que recibe, almacena y procesa los archivos de las valoraciones cualitativas
#---------------------------------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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
    
#---------------------------------------------------------------------------------------------------
# Metodo que recibe, almacena y procesa los archivos de las valoraciones cuantitativas
#---------------------------------------------------------------------------------------------------

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])  
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
