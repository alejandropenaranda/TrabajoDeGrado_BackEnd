# Script para leer un archivo Excel con nombres y guardarlos en el modelo Escuela de Django

import pandas as pd
import os
import django

# Configurar la configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TrabajoDeGrado_BackEnd.settings')
django.setup()

from core.models import Materia  # Importar el modelo Escuela de tu aplicación Django

def insertar_nombres_desde_excel(archivo):
    # Cargar el archivo Excel en un DataFrame de Pandas
    df = pd.read_excel(archivo)  # Para Excel

    # Iterar sobre cada nombre en el DataFrame y guardarlos como instancias de Escuela
    for index, row in df.iterrows():
        nombre_materia = row['nombre']
        codigo_materia = row['codigo']
        escuela = Materia(codigo=codigo_materia, nombre=nombre_materia)
        escuela.save()  # Guardar la escuela en la base de datos

    print(f'Se han insertado {len(df)} materias desde el archivo {archivo}')

if __name__ == '__main__':
    archivo = './Datasets/Materias2.xlsx'  # Ruta al archivo Excel
    insertar_nombres_desde_excel(archivo)