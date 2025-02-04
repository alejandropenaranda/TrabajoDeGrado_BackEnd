import os
import django

from django.db.models import Avg
from core.models import Usuario, PromedioCalificaciones, FortalezasDebilidadesCuantitativas

def identificar_fortalezas_debilidades_cuant():
    docentes = Usuario.objects.filter(is_profesor=True)

    for docente in docentes:
        # Obtener promedios cuantitativos generales
        promedios_cuantitativos = PromedioCalificaciones.objects.filter(docente=docente).aggregate(
            prom_pregunta_9=Avg('prom_pregunta_9'),
            prom_pregunta_10=Avg('prom_pregunta_10'),
            prom_pregunta_11=Avg('prom_pregunta_11'),
            prom_pregunta_12=Avg('prom_pregunta_12'),
            prom_pregunta_13=Avg('prom_pregunta_13'),
            prom_pregunta_14=Avg('prom_pregunta_14'),
            prom_pregunta_15=Avg('prom_pregunta_15'),
            prom_pregunta_16=Avg('prom_pregunta_16'),
            prom_pregunta_17=Avg('prom_pregunta_17'),
            prom_pregunta_18=Avg('prom_pregunta_18'),
            prom_pregunta_19=Avg('prom_pregunta_19'),
            prom_pregunta_20=Avg('prom_pregunta_20')
        )

        # Determinar fortalezas y debilidades basadas en las medias
        valoraciones = {}
        for i in range(9, 21):
            pregunta = f'prom_pregunta_{i}'
            media = promedios_cuantitativos[pregunta]
            valoraciones[pregunta] = calificar_fortaleza_debilidad(media)

        # Guardar o actualizar las medias y valoraciones en la tabla FortalezasDebilidadesCuantitativas
        FortalezasDebilidadesCuantitativas.objects.update_or_create(
            docente=docente,
            defaults={
                'prom_pregunta_9': promedios_cuantitativos['prom_pregunta_9'],
                'prom_pregunta_10': promedios_cuantitativos['prom_pregunta_10'],
                'prom_pregunta_11': promedios_cuantitativos['prom_pregunta_11'],
                'prom_pregunta_12': promedios_cuantitativos['prom_pregunta_12'],
                'prom_pregunta_13': promedios_cuantitativos['prom_pregunta_13'],
                'prom_pregunta_14': promedios_cuantitativos['prom_pregunta_14'],
                'prom_pregunta_15': promedios_cuantitativos['prom_pregunta_15'],
                'prom_pregunta_16': promedios_cuantitativos['prom_pregunta_16'],
                'prom_pregunta_17': promedios_cuantitativos['prom_pregunta_17'],
                'prom_pregunta_18': promedios_cuantitativos['prom_pregunta_18'],
                'prom_pregunta_19': promedios_cuantitativos['prom_pregunta_19'],
                'prom_pregunta_20': promedios_cuantitativos['prom_pregunta_20'],
                'valoraciones': valoraciones
            }
        )

def calificar_fortaleza_debilidad(calificacion):
    if calificacion >= 0 and calificacion <= 1.9:
        return 'deb_MP'
    elif calificacion >= 2 and calificacion <= 2.9:
        return 'deb_P'
    elif calificacion >= 3.8 and calificacion <= 4.5:
        return 'fort_B'
    elif calificacion >= 4.6 and calificacion <= 5:
        return 'fort_MB'
    else:
        return 'neu'
    

if __name__ == "__main__":
    identificar_fortalezas_debilidades_cuant()
