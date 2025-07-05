# ===========================================================
#     Clasificador de intenciones con Scikit-learn
# ===========================================================
# Paso 1. Instalar / actualizar dependencias
# (En Colab normalmente ya está scikit-learn, pero por si acaso)
#pip install --quiet -U scikit-learn pandas numpy

# Paso 2. Importaciones
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.metrics import classification_report, confusion_matrix
from dataset import questions

# Paso 3. Ejemplos de entrenamiento  -------------------------
# 1 = pregunta sobre tickets / dominio SQL
# 0 = pregunta fuera de dominio

preguntas = questions
etiquetas = [1]*113 + [0]*113
print(len(preguntas), len(etiquetas))  # 200 200


# Paso 4. Separar en train/test  -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    preguntas, etiquetas, test_size=0.2, random_state=42, stratify=etiquetas
)

# Paso 5. Pipeline (TF-IDF + Regresión Logística) ------------
modelo = make_pipeline(
    TfidfVectorizer(ngram_range=(1,2), stop_words=None),
    LogisticRegression(max_iter=200)
)

modelo.fit(X_train, y_train)

# Paso 6. Evaluación rápida  --------------------------------
y_pred = modelo.predict(X_test)
print("== Reporte de clasificación ==")
print(classification_report(y_test, y_pred, target_names=["FueraDom", "Tickets"]))
print("Matriz de confusión:\n", confusion_matrix(y_test, y_pred))

# Paso 7. Probar nuevas preguntas ----------------------------
pruebas = [
    "¿Cómo puedo cerrar un ticket?",
    "¿Qué tickets abiertos tengo?",
    "¿Cuál es la temperatura en París?",
    "Explícame la teoría de cuerdas",
    "Dime, ¿cuál es la diferencia entre la atención de Soporte y Redes?",
    "¿Puedes decirme cuantos tickets hay en el mundo?"
]
pred = modelo.predict(pruebas)

for p, etiqueta in zip(pruebas, pred):
    dominio = "TICKETS/SQL" if etiqueta == 1 else "FUERA_DOMINIO"
    print(f"► '{p}'  ->  {dominio}")
