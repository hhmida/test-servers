FROM apache/airflow:2.10.5  # Remplacez par la dernière version d'Airflow

# Passer à l’utilisateur root pour installer des dépendances
USER root
RUN apt-get update && apt-get install -y curl vim

# Copier et installer les packages Python
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Revenir à l’utilisateur Airflow
USER airflow