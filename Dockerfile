# Stage 1: Build environment
FROM python:3.10-alpine as builder

WORKDIR /app

# Install build dependencies
RUN apk update && apk add --no-cache build-base libffi-dev

# Copy poetry configuration files
COPY ./pyproject.toml ./poetry.lock ./

# Install poetry and project dependencies
RUN pip install --no-cache-dir poetry==1.4.0 && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction && \
    rm -rf ~/.cache/pypoetry/{cache,artifacts}

# Stage 2: Runtime environment
FROM python:3.10-alpine

WORKDIR /app

# Copy application code and dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

COPY ./imgpush ./imgpush

# Create directories and set permissions
RUN mkdir /images /cache /certs && \
    adduser -D python && \
    chown -R python:python /images /cache /certs

# Switch to non-root user
USER python

# Start application
CMD FLASK_APP=imgpush/app.py flask run --port ${PORT:-5000} --with-threads --host 0.0.0.0 $(if [ "$DEBUG" = "True" ]; then echo "--debug"; fi;)
