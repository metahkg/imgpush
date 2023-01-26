FROM python:3.10-slim

COPY ./pyproject.toml ./poetry.lock ./

RUN apt-get update && \
    apt-get install -y libmagickwand-dev && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

RUN pip install poetry

RUN poetry config virtualenvs.create false

RUN poetry install --no-dev --no-interaction

COPY ./ImageMagick-6/policy.xml /etc/ImageMagick-6/policy.xml

RUN mkdir /images
RUN mkdir /cache
RUN mkdir /certs

COPY ./app /app

WORKDIR /app

RUN useradd -M python

RUN chown python:python /images /cache /certs /app

USER python

CMD FLASK_APP=app/app.py flask run --port "${PORT:-5000}" --host 0.0.0.0
