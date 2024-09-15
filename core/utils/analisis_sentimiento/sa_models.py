import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from pysentimiento import create_analyzer

from core.utils.analisis_sentimiento.conversor import conversor_calificacion_citizenlab,conversor_calificacion_lxyuan,convertir_a_calificacion_5_estrellas,formatear

#Funcion que se encarga de aplicar el analisis de sentimientos del modelo "marianna13/bert-multilingual-sentiment" a un comentario

def sentimiento1_marianna13(comentario):

# Si un comentario es muy largo es posible que el model no pueda procesarlo
  if len(comentario) > 2200:
    return 'cadena muy larga'

  tokenizer = AutoTokenizer.from_pretrained("marianna13/bert-multilingual-sentiment")
  model = AutoModelForSequenceClassification.from_pretrained("marianna13/bert-multilingual-sentiment")

  input_ids = torch.tensor(tokenizer.encode(comentario)).unsqueeze(0)
  outputs = model(input_ids)
  output = outputs.logits.argmax(1)

  predicted_probs = torch.softmax(outputs.logits, dim=1).tolist()[0]

  # Obtener las etiquetas de sentimiento
  sentiment_labels = ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"]

  # Construir la salida en el formato deseado
  output_dict = [
      {"label": sentiment_labels[i], "score": score}
      for i, score in enumerate(predicted_probs)
  ]

  procesado = convertir_a_calificacion_5_estrellas(output_dict)

  return procesado


def sentimiento2_nlptown(comentario):

  # Si un comentario es muy largo es posible que el model no pueda procesarlo
  if len(comentario) > 2200:
    return 'cadena muy larga'

  tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
  model = AutoModelForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")

  input_ids = torch.tensor(tokenizer.encode(comentario)).unsqueeze(0)
  outputs = model(input_ids)
  output = outputs.logits.argmax(1)


  predicted_probs = torch.softmax(outputs.logits, dim=1).tolist()[0]

  # Obtener las etiquetas de sentimiento
  sentiment_labels = ["1 star", "2 stars", "3 stars", "4 stars", "5 stars"]

  # Construir la salida en el formato deseado
  output_dict = [
      {"label": sentiment_labels[i], "score": score}
      for i, score in enumerate(predicted_probs)
  ]

  procesado = convertir_a_calificacion_5_estrellas(output_dict)

  return procesado


def sentimiento3_lxyuan(comentario):

  # Si un comentario es muy largo es posible que el model no pueda procesarlo
  if len(comentario) > 2050:
    return 'cadena muy larga'

  distilled_student_sentiment_classifier = pipeline(
      model="lxyuan/distilbert-base-multilingual-cased-sentiments-student",
      top_k=None)

  result = distilled_student_sentiment_classifier(comentario)

  output = conversor_calificacion_lxyuan(result[0])

  return output

def sentimiento4_pysentimiento(comentario):

  # Si un comentario es muy largo es posible que el model no pueda procesarlo
  if len(comentario) > 2200:
    return 'cadena muy larga'

  # analyzer = SentimentAnalyzer(lang="es")

  analyzer = create_analyzer(task="sentiment", lang="es")
  result = analyzer.predict(comentario)
  resultado = formatear(result.probas)
  output = conversor_calificacion_lxyuan(resultado)
  return output



def sentimiento5_citizenlab(comentario):

  # Si un comentario es muy largo es posible que el model no pueda procesarlo
  if len(comentario) > 2200:
    return "cadena muy larga"

  tokenizer = AutoTokenizer.from_pretrained("citizenlab/twitter-xlm-roberta-base-sentiment-finetunned")
  model = AutoModelForSequenceClassification.from_pretrained("citizenlab/twitter-xlm-roberta-base-sentiment-finetunned")

  input_ids = torch.tensor(tokenizer.encode(comentario)).unsqueeze(0)
  outputs = model(input_ids)
  output = outputs.logits.argmax(1)
  predicted_probs = torch.softmax(outputs.logits, dim=1).tolist()[0]

  # Obtener las etiquetas de sentimiento
  sentiment_labels = ["Negative","Neutral","Positive"]

  # Construir la salida en el formato deseado
  output_dict = [
      {"label": sentiment_labels[i], "score": score}
      for i, score in enumerate(predicted_probs)
  ]

  output = conversor_calificacion_citizenlab(output_dict)

  return output
