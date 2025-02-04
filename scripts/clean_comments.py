import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TrabajoDeGrado_BackEnd.settings')
django.setup()

from core.models import CalificacionesCualitativas
from core.utils.limpiar_texto.limpiador_texto import cleaner

def actualizar_comentarios():
    calificaciones = CalificacionesCualitativas.objects.all()
    for calificacion in calificaciones:
        calificacion.comentario_limpio = cleaner(calificacion.comentario)
        calificacion.save()
    print(f'Se han actualizado {calificaciones.count()} registros de calificaciones cualitativas.')

if __name__ == '__main__':
    actualizar_comentarios()