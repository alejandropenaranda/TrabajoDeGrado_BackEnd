import os
import django

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TrabajoDeGrado_BackEnd.settings')
# django.setup()

from django.db.models import Avg
from core.models import Usuario, CalificacionesCualitativas, CalificacionesCuantitativas, PromedioCalificaciones, Materia

def calcular_promedios():
    # Obtener todos los docentes
    docentes = Usuario.objects.filter(is_profesor=True)

    for docente in docentes:
        # Obtener todas las materias
        materias = Materia.objects.all()
        
        for materia in materias:
            # Obtener promedios cualitativos por periodo y materia
            promedios_cualitativos = CalificacionesCualitativas.objects.filter(docente=docente, materia=materia).values('periodo').annotate(promedio=Avg('promedio'))
            
            # Obtener promedios cuantitativos por periodo y materia
            promedios_cuantitativos = CalificacionesCuantitativas.objects.filter(docente=docente, materia=materia).values('periodo').annotate(
                promedio=Avg('promedio'),
                prom_pregunta_9=Avg('pregunta_9'),
                prom_pregunta_10=Avg('pregunta_10'),
                prom_pregunta_11=Avg('pregunta_11'),
                prom_pregunta_12=Avg('pregunta_12'),
                prom_pregunta_13=Avg('pregunta_13'),
                prom_pregunta_14=Avg('pregunta_14'),
                prom_pregunta_15=Avg('pregunta_15'),
                prom_pregunta_16=Avg('pregunta_16'),
                prom_pregunta_17=Avg('pregunta_17'),
                prom_pregunta_18=Avg('pregunta_18'),
                prom_pregunta_19=Avg('pregunta_19'),
                prom_pregunta_20=Avg('pregunta_20')
            )

            # Crear un diccionario para almacenar los promedios por periodo
            promedios_por_periodo = {}

            for promedio in promedios_cualitativos:
                periodo = promedio['periodo']
                if periodo not in promedios_por_periodo:
                    promedios_por_periodo[periodo] = {}
                promedios_por_periodo[periodo]['promedio_cual'] = promedio['promedio']

            for promedio in promedios_cuantitativos:
                periodo = promedio['periodo']
                if periodo not in promedios_por_periodo:
                    promedios_por_periodo[periodo] = {}
                promedios_por_periodo[periodo]['promedio_cuant'] = promedio['promedio']
                promedios_por_periodo[periodo]['prom_pregunta_9'] = promedio['prom_pregunta_9']
                promedios_por_periodo[periodo]['prom_pregunta_10'] = promedio['prom_pregunta_10']
                promedios_por_periodo[periodo]['prom_pregunta_11'] = promedio['prom_pregunta_11']
                promedios_por_periodo[periodo]['prom_pregunta_12'] = promedio['prom_pregunta_12']
                promedios_por_periodo[periodo]['prom_pregunta_13'] = promedio['prom_pregunta_13']
                promedios_por_periodo[periodo]['prom_pregunta_14'] = promedio['prom_pregunta_14']
                promedios_por_periodo[periodo]['prom_pregunta_15'] = promedio['prom_pregunta_15']
                promedios_por_periodo[periodo]['prom_pregunta_16'] = promedio['prom_pregunta_16']
                promedios_por_periodo[periodo]['prom_pregunta_17'] = promedio['prom_pregunta_17']
                promedios_por_periodo[periodo]['prom_pregunta_18'] = promedio['prom_pregunta_18']
                promedios_por_periodo[periodo]['prom_pregunta_19'] = promedio['prom_pregunta_19']
                promedios_por_periodo[periodo]['prom_pregunta_20'] = promedio['prom_pregunta_20']

            # Guardar o actualizar los promedios en la tabla PromedioCalificaciones
            for periodo, promedios in promedios_por_periodo.items():
                promedio_cual = promedios.get('promedio_cual', 0)
                promedio_cuant = promedios.get('promedio_cuant', 0)
                promedio_general = (promedio_cual + promedio_cuant) / 2 if promedio_cual and promedio_cuant else promedio_cual or promedio_cuant

                PromedioCalificaciones.objects.update_or_create(
                    docente=docente,
                    materia=materia,
                    periodo=periodo,
                    defaults={
                        'promedio': promedio_general,
                        'promedio_cual': promedio_cual,
                        'promedio_cuant': promedio_cuant,
                        'prom_pregunta_9': promedios.get('prom_pregunta_9', 0),
                        'prom_pregunta_10': promedios.get('prom_pregunta_10', 0),
                        'prom_pregunta_11': promedios.get('prom_pregunta_11', 0),
                        'prom_pregunta_12': promedios.get('prom_pregunta_12', 0),
                        'prom_pregunta_13': promedios.get('prom_pregunta_13', 0),
                        'prom_pregunta_14': promedios.get('prom_pregunta_14', 0),
                        'prom_pregunta_15': promedios.get('prom_pregunta_15', 0),
                        'prom_pregunta_16': promedios.get('prom_pregunta_16', 0),
                        'prom_pregunta_17': promedios.get('prom_pregunta_17', 0),
                        'prom_pregunta_18': promedios.get('prom_pregunta_18', 0),
                        'prom_pregunta_19': promedios.get('prom_pregunta_19', 0),
                        'prom_pregunta_20': promedios.get('prom_pregunta_20', 0)
                    }
                )