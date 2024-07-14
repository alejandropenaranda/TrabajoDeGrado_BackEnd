import pandas as pd
from sa_models import sentimiento1_marianna13,sentimiento2_nlptown,sentimiento3_lxyuan,sentimiento4_pysentimiento,sentimiento5_citizenlab

dataframe = pd.read_excel("./Datasets/OG_MD_Cualitativo_Asignatura_Periodo_Comentarios_Filtrados.xlsx")

print(dataframe.shape)

col_comentario = "COMENTARIO"

def eliminar_registros_con_cadena_larga(df, columnas):

    for col in columnas:
        df = df[df[col] != "cadena muy larga"]
    return df


def agregar_promedio(dataframe, columnnas):
    # Calcular el promedio de las calificaciones
    df = eliminar_registros_con_cadena_larga(dataframe, columnnas)

    df['SCORE'] = df[columnnas].mean(axis=1)

    # Guardar el DataFrame con la nueva columna en un archivo Excel
    df.to_excel('./Datasets/pruebaFinal.xlsx', index=False)


def analizar_sentimiento(dataframe):
  df = pd.DataFrame()

  for i in range(0,dataframe.shape[0], 100): #se modifica el tamaño del paso #dataframe.shape[0]

      dataframe['SCORE1'] = dataframe[i:i+100][col_comentario].apply(sentimiento1_marianna13)#se modifica el tamaño del paso
      dataframe['SCORE2'] = dataframe[i:i+100][col_comentario].apply(sentimiento2_nlptown)
      dataframe['SCORE3'] = dataframe[i:i+100][col_comentario].apply(sentimiento3_lxyuan)
      dataframe['SCORE4'] = dataframe[i:i+100][col_comentario].apply(sentimiento4_pysentimiento)
      dataframe['SCORE5'] = dataframe[i:i+100][col_comentario].apply(sentimiento5_citizenlab)

      datos_subset = dataframe[i:i+100]#se modifica el tamaño del paso

      # Convierte los datos en un DataFrame temporal
      df_temporal = pd.DataFrame(datos_subset)

      # Agrega el DataFrame temporal al DataFrame principal
      df = pd.concat([df, df_temporal], ignore_index=True)

      # Guarda el DataFrame en un archivo Excel después de cada iteración
      df.to_excel('./Datasets/prueba.xlsx', index=False)

  columnas_score = ['SCORE1', 'SCORE2', 'SCORE3', 'SCORE4', 'SCORE5']

  agregar_promedio(df, columnas_score)

analizar_sentimiento(dataframe)