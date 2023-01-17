FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y libmagickwand-dev curl ninja-build && \
    apt-get clean autoclean && \
    apt-get autoremove -y && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

COPY ./requirements.txt ./

RUN pip install -r requirements.txt

COPY ./ImageMagick-6/policy.xml /etc/ImageMagick-6/policy.xml


RUN mkdir /images
RUN mkdir /cache
RUN mkdir /certs

COPY ./app /app

WORKDIR /app

CMD flask run --port "${PORT:-5000}" --host 0.0.0.0
