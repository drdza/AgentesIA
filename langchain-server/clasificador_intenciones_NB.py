import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report, confusion_matrix
from dataset import questions


# ----------------------------------------
# 1. Dataset (226 preguntas equilibradas)
# ----------------------------------------

preguntas = questions
etiquetas = [1]*113 + [0]*113
print(len(preguntas), len(etiquetas))  # 200 200