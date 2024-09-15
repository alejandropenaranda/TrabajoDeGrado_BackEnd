from core.models import CalificacionesCualitativas, Usuario, Materia, Escuela
from core.utils.analisis_sentimiento.sa_models import sentimiento1_marianna13, sentimiento2_nlptown, sentimiento3_lxyuan, sentimiento4_pysentimiento, sentimiento5_citizenlab
from core.utils.limpiar_texto.limpiador_texto import cleaner

#Metodo mediante el cual se filtran y eliminan registros donde los comentarios no estan dirigidos al desempeño del docente
def filtro_comentarios(df):
    key_words = [
        "profe", "profesor", "profesora", "docente", "maestro", "maestra", "bueno", "buena", "buen", "mal",
        "malo", "excelente", "terrible", "genial", "mejor", "mejorar", "peor", "increíble", "metodología", "teacher",
        "metodologia", "didáctica", "pedagogía", "pedagogia", "explicación", "explicacion", "clase", "clases", "curso",
        "cursos", "enseñanza", "enseñanza", "aprendizaje", "facilitador", "guía", "guia", "competente", "competencia",
        "preparado", "preparada", "organizado", "organizada", "interesante", "aburrido", "puntual", "responsable",
        "comprometido", "comprometida", "empático", "empática", "empatico", "empatica", "paciente", "amable",
        "estricto", "estricta", "riguroso", "rigorosa", "exigente", "apoyo", "soporte", "evaluación", "evaluacion",
        "retroalimentación", "retroalimentacion", "disponible", "accesible", "interacción", "interaccion", "feedback",
        "motivador", "motivadora", "inspirador", "inspiradora", "entusiasta", "dedicado", "dedicada", "experto",
        "experta", "atento", "atenta", "pasión", "pasion", "habilidad", "claridad", "dinámico", "dinamico",
        "dinámica", "dinamica", "expresivo", "expresiva", "puntualidad", "conocimiento", "compañerismo", "companerismo",
        "paciencia", "dedicación", "dedicacion", "compasivo", "compasiva", "proactivo", "proactiva", "confiable",
        "imaginativo", "imaginativa", "constructivo", "constructiva", "crítico", "critico", "crítica", "critica",
        "dialogante", "motivación", "motivacion", "apasionado", "apasionada", "creativo", "creativa", "empoderador",
        "empoderadora", "innovador", "innovadora", "liderazgo", "mentor", "mentora", "apoyo", "mentoría", "mentoria"
    ]

    del_words = [
        "salon", "aula", "salas", "proyector", "videobeam", "computadores", "computador", "equipos", "reproductor",
        "instalaciones", "infraestructura", "sillas", "mesas", "pupitres", "bancos", "ventilador", "aire acondicionado",
        "iluminación", "iluminacion", "sonido", "acústica", "acustica", "paredes", "techo", "ventanas", "puertas",
        "baños", "servicios", "ascensor", "escaleras", "cafetería", "cafeteria", "biblioteca", "laboratorio", "parqueadero",
        "zona de estudio", "zona de descanso", "horario", "calendario", "administración", "administracion", "secretaría",
        "secretaria", "recepción", "recepcion", "seguridad", "limpieza", "mantenimiento", "wifi", "internet",
        "electrónica", "electronica", "tiza", "pizarra", "marcador", "proyectores", "sala de reuniones", "auditorio",
        "cafeterias", "laboratorios", "gimnasio", "estacionamiento", "pasillos", "jardines", "canchas", "servicios sanitarios"
    ]
    patron1 = '|'.join(key_words)
    filtro1= df['COMENTARIO'].str.contains(patron1, case=False, na=False)
    datos_filtrados = df[filtro1]

    patron2 = '|'.join(del_words)
    filtro2 = datos_filtrados['COMENTARIO'].str.contains(patron2, case=False, regex=True)
    datos_filtrados_2 = datos_filtrados[~filtro2]

    return datos_filtrados_2

def insertar_calif_cualitativas(df):
    for index, row in df.iterrows():
        periodo = row['SEMESTRE']
        comentario = row['COMENTARIO']
        codigo_docente = row['CEDULA']
        nombre_docente = row['DOCENTE']
        nombre_escuela = row['ESCUELA'] 
        codigo_materia = row['CODIGO_MATERIA']
        nombre_materia = row['MATERIA']

        if len(comentario) > 2050:
            continue

        try:
            escuela = Escuela.objects.get(nombre=nombre_escuela)
        except Escuela.DoesNotExist:
            print(f'No se encontró la escuela: {nombre_escuela}')
            escuela = None

        docente, created_docente = Usuario.objects.get_or_create(
            codigo=codigo_docente,
            defaults={
                'nombre': nombre_docente,
                'email': f'{codigo_docente}@temporal.com',
                'is_profesor': True,
                'escuela': escuela
            }
        )

        materia, created_materia = Materia.objects.get_or_create(
            codigo=codigo_materia,
            defaults={'nombre': nombre_materia}
        )

        califCual = CalificacionesCualitativas(
            periodo=periodo,
            comentario=comentario,
            docente_id=docente.id,
            materia_id=materia.id
        )

        califCual.save()

def aplicar_analisis_de_sentimientos():
    registros_sin_promedio = CalificacionesCualitativas.objects.filter(promedio__isnull=True)

    if not registros_sin_promedio.exists():
        print("No hay registros sin promedio, no se realizó ningún análisis.")
        return

    for registro in registros_sin_promedio:
        comentario = registro.comentario

        resultado1 = sentimiento1_marianna13(comentario)
        resultado2 = sentimiento2_nlptown(comentario)
        resultado3 = sentimiento3_lxyuan(comentario)
        resultado4 = sentimiento4_pysentimiento(comentario)
        resultado5 = sentimiento5_citizenlab(comentario)

        promedio = (resultado1 + resultado2 + resultado3 + resultado4 + resultado5) / 5
        registro.promedio = promedio
        registro.save()

def limpiar_comentarios():
    calificaciones = CalificacionesCualitativas.objects.filter(comentario_limpio__isnull=True)
    for calificacion in calificaciones:
        calificacion.comentario_limpio = cleaner(calificacion.comentario)
        calificacion.save()
    print(f'Se han actualizado {calificaciones.count()} registros de calificaciones cualitativas.')

def filtrar_y_almacenar_datos(df):
    df_filtrado = filtro_comentarios(df)
    insertar_calif_cualitativas(df_filtrado)

def procesar_evaluaciones_cualitativas(df):
    filtrar_y_almacenar_datos(df)
    aplicar_analisis_de_sentimientos()
    limpiar_comentarios()
