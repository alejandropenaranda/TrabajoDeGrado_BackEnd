import ollama
from langchain_community.llms import Ollama

def laguageModel(prompt):
  llm = Ollama(model="llama3", temperature=0)
  response = llm.invoke([prompt])
  return response