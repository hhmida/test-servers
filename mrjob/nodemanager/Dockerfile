FROM bde2020/hadoop-nodemanager:2.0.0-hadoop3.2.1-java8

ENV PATH="/opt/miniconda/bin:$PATH"


# Miniconda3-py38 = dernière version compatible avec GLIBC 2.24
RUN curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-py38_4.12.0-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/miniconda && \
    rm /tmp/miniconda.sh && \
    pip install mrjob && \
    ln -s /opt/miniconda/bin/python3 /usr/bin/python3 && \
    ln -s /opt/miniconda/bin/python3 /usr/bin/python