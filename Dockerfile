FROM python:3.10-alpine

COPY ./pyproject.toml ./poetry.lock ./

RUN pip install --no-cache-dir poetry==1.4.0 && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction && \
    rm -rf ~/.cache/pypoetry/{cache,artifacts}

RUN mkdir /images /cache /certs

WORKDIR /app

COPY ./imgpush ./imgpush

RUN adduser -D python && \
    chown -R python:python /images /cache /certs /app

USER python

CMD FLASK_APP=imgpush/app.py flask run --port ${PORT:-5000} --with-threads --host 0.0.0.0 $(if [ "$DEBUG" = "True" ]; then echo "--debug"; fi;)
