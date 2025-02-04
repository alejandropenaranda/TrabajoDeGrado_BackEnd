from core.models import CalificacionesCuantitativas, Usuario, Materia, Escuela
from core.utils.calificaciones_promedio.generar_promedios import calcular_promedios
from core.utils.fortalezas_debilidades.cuant_fort_deb import identificar_fortalezas_debilidades_cuant

def insertar_calif_cuantitativas(df):
    for index, row in df.iterrows():
        periodo = row['SEMESTRE']
        codigo_docente = row['CEDULA']
        nombre_docente = row['DOCENTE']
        nombre_escuela = row['ESCUELA'] 
        codigo_materia = row['CODIGO_MATERIA']
        nombre_materia = row['MATERIA']
        promedio = row['PROM_DOCENTE']
        pregunta_9 = row['PREGUNTA9']
        pregunta_10 = row['PREGUNTA10']
        pregunta_11 = row['PREGUNTA11']
        pregunta_12 = row['PREGUNTA12']
        pregunta_13 = row['PREGUNTA13']
        pregunta_14 = row['PREGUNTA14']
        pregunta_15 = row['PREGUNTA15']
        pregunta_16 = row['PREGUNTA16']
        pregunta_17 = row['PREGUNTA17']
        pregunta_18 = row['PREGUNTA18']
        pregunta_19 = row['PREGUNTA19']
        pregunta_20 = row['PREGUNTA20']

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

        califCual = CalificacionesCuantitativas(
            periodo=periodo,
            promedio=promedio,
            pregunta_9 = pregunta_9,
            pregunta_10 = pregunta_10,
            pregunta_11 = pregunta_11,
            pregunta_12 = pregunta_12,
            pregunta_13 = pregunta_13,
            pregunta_14 = pregunta_14,
            pregunta_15 = pregunta_15,
            pregunta_16 = pregunta_16,
            pregunta_17 = pregunta_17,
            pregunta_18 = pregunta_18,
            pregunta_19 = pregunta_19,
            pregunta_20 = pregunta_20,
            docente_id=docente.id,
            materia_id=materia.id
        )

        califCual.save()

def procesar_evaluaciones_cuantitativas(df):
    insertar_calif_cuantitativas(df)
    calcular_promedios()
    identificar_fortalezas_debilidades_cuant()