# Utiliser une image Python officielle légère
FROM python:3.12-slim

# Empêcher Python de générer des fichiers .pyc et d'utiliser un buffer pour les logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Installer les dépendances Python directement
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary

# Copier le fichier principal de l'API
COPY . .

# Exposer le port sur lequel l'application tourne
EXPOSE 8000

# Lancer l'application avec Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]