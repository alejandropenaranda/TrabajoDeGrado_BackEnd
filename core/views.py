from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import AuthTokenSerializer, CualFortDebSerializer, UsuarioSerializer,AverageGradesSerizalizer, CuantFortDebSerializer, CalificacionesCualitativasSerializer

from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework. authentication import TokenAuthentication

from django.contrib.auth.models import User
from django.db.models import Avg, Q
from .models import Usuario, PromedioCalificaciones,FortalezasDebilidadesCuantitativas, CalificacionesCualitativas, FortalezasDebilidadesCualitativas
from django.shortcuts import get_object_or_404

import base64
from io import BytesIO
from collections import Counter
from wordcloud import WordCloud

from .utils.fortalezas_debilidades.cual_fort_deb import laguageModel

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