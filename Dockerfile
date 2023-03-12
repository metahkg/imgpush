FROM python:3.10.9-slim

COPY ./pyproject.toml ./poetry.lock ./

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libmagickwand-dev && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

RUN pip install --no-cache-dir poetry==1.4.0 && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction && \
    rm -rf ~/.cache/pypoetry/{cache,artifacts}

COPY ./ImageMagick-6/policy.xml /etc/ImageMagick-6/policy.xml

RUN mkdir /images /cache /certs

COPY ./app /app

WORKDIR /app

RUN useradd -M python && \
    chown python:python /images /cache /certs /app

USER python

ENV FLASK_APP=app.py

CMD ["sh", "-c", "flask run --port ${PORT:-5000} --host 0.0.0.0"]
