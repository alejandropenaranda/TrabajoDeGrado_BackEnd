# Funcion que se encarga de normalizar el resultado obtenido del modelo "marianna13/bert-multilingual-sentiment" y
# "nlptown/bert-base-multilingual-uncased-sentiment" a formato numerico

def convertir_a_calificacion_5_estrellas(calificacion):
  calificacion_final = sum((int(item['label'][0]) * item['score']) for item in calificacion)

  calificacion_normalizada = calificacion_final / 5  # Normalizamos al rango de 0 a 1

  calificacion_escalada = calificacion_normalizada * 4 + 1  # Escalamos al rango de 1 a 5
  return calificacion_escalada

def conversor_calificacion_lxyuan(input):
  scores = input
  weights = {'negative': 1, 'neutral': 3, 'positive': 5}

  # Inicializamos la variable para la suma ponderada
  weighted_sum = 0

  # Calculamos la suma ponderada de las puntuaciones
  for score in scores:
      weighted_sum += score['score'] * weights[score['label']]

  # Normalizamos la suma ponderada al rango de 1 a 5
  total_weight = 5

  # Normalización de la suma ponderada
  normalized_weighted_sum = (weighted_sum / total_weight) * 4 + 1

  return normalized_weighted_sum

def conversor_calificacion_citizenlab(input):
  scores = input
  weights = {'Negative': 1, 'Neutral': 3, 'Positive': 5}

  weighted_sum = 0

  for score in scores:
      weighted_sum += score['score'] * weights[score['label']]

  total_weight = 5

  normalized_weighted_sum = (weighted_sum / total_weight) * 4 + 1

  return normalized_weighted_sum

def formatear(puntuacion):

    def transformar_etiqueta(etiqueta):
        if etiqueta == 'NEG':
            return 'negative'
        elif etiqueta == 'NEU':
            return 'neutral'
        elif etiqueta == 'POS':
            return 'positive'
    # Transformar el diccionario original a la lista de diccionarios
    puntuaciones_transformadas = [{'label': transformar_etiqueta(etiqueta), 'score': puntuacion[etiqueta]} for etiqueta in puntuacion]

    return puntuaciones_transformadas