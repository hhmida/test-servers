FROM apache/airflow:2.10.5-python3.8
# Remplacez par la dernière version d'Airflow

# Passer à l’utilisateur root pour installer des dépendances
USER root
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         gcc \
         heimdal-dev \
         curl \
         vim \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*
# Revenir à l’utilisateur Airflow
USER airflow
# Copier et installer les packages Python
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir "apache-airflow==2.10.5" -r /requirements.txt