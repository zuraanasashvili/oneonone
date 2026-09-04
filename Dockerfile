FROM python:3.12-slim

WORKDIR /srv/oneonone

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

ENV FLASK_APP=app \
    DATABASE_URL=sqlite:////data/oneonone.db

VOLUME /data
EXPOSE 8000

# Create the schema (idempotent) then serve.
CMD ["sh", "-c", "flask db upgrade 2>/dev/null || flask shell -c 'from app.extensions import db; db.create_all()'; gunicorn -b 0.0.0.0:8000 'app:create_app()'"]
