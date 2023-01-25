FROM python:3.10-slim

COPY ./pyproject.toml ./poetry.lock ./

RUN apt-get update && \
    apt-get install -y libmagickwand-dev && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

COPY ./ImageMagick-6/policy.xml /etc/ImageMagick-6/policy.xml

RUN mkdir /images
RUN mkdir /cache
RUN mkdir /certs

COPY ./app /app

WORKDIR /app

RUN useradd -M python

RUN chown python:python /images /cache /certs /app

USER python

CMD flask run --port "${PORT:-5000}" --host 0.0.0.0
