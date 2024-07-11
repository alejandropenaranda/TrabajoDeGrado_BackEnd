import pandas as pd
import os
import django

# Configurar la configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TrabajoDeGrado_BackEnd.settings')
django.setup()

from core.models import CalificacionesCuantitativas, Usuario, Materia

def insertar_calif_cualitativas_desde_excel(archivo):
    # Cargar el archivo Excel en un DataFrame de Pandas
    df = pd.read_excel(archivo)  # Para Excel

    for index, row in df.iterrows():
        periodo = row['periodo']
        promedio = row['promedio']
        codigo_docente = row['docente_id']
        codigo_materia = row['materia_id']
 
        # Encontrar el ID del docente usando el código único
        try:
            docente = Usuario.objects.get(codigo=codigo_docente)
        except Usuario.DoesNotExist:
            print(f'No se encontró el docente con código: {codigo_docente}')
            continue

        # Encontrar el ID de la materia usando el código único
        try:
            materia = Materia.objects.get(codigo=codigo_materia)
        except Materia.DoesNotExist:
            print(f'No se encontró la materia con código: {codigo_materia}')
            continue

        # Crear la instancia de CalificacionesCualitativas
        califCual = CalificacionesCuantitativas(
            periodo=periodo,
            promedio=promedio,
            docente_id=docente.id,
            materia_id=materia.id
        )

        califCual.save()  # Guardar la escuela en la base de datos

        # Falta revisar bien el tema de is_docente y eso
    print(f'Se han insertado {len(df)} registros de calificaciones cuantitativas desde el archivo {archivo}')

if __name__ == '__main__':
    archivo = './Datasets/calificaciones_cuantitativas.xlsx'  # Ruta al archivo Excel
    insertar_calif_cualitativas_desde_excel(archivo)

