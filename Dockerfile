FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y libmagickwand-dev curl && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

COPY requirements.txt ./

RUN apt-get update && \
    apt-get install -y ninja-build && \
    pip install -r requirements.txt && \
    apt-get remove -y ninja-build && \
    apt-get clean autoclean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

COPY ImageMagick-6/policy.xml /etc/ImageMagick-6/policy.xml


RUN mkdir /images
RUN mkdir /cache

COPY app /app

WORKDIR /app

CMD python app.py
