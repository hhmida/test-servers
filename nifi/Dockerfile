# Utiliser l'image officielle Apache NiFi 2.4.0 comme base
ARG IMAGE_NAME=apache/nifi
ARG IMAGE_TAG=2.4.0
FROM ${IMAGE_NAME}:${IMAGE_TAG}

# Définir les métadonnées
LABEL maintainer="H. Hmida <hhmida@gmail.com>"

# Copier les fichiers de configuration HDFS (core-site.xml et hdfs-site.xml)
# Remplacez les chemins par ceux correspondant à votre configuration HDFS
COPY --chown=nifi:nifi start.sh /opt/nifi/scripts/start.sh

# Définir les permissions appropriées pour start.sh
RUN chmod a+x /opt/nifi/scripts/start.sh
