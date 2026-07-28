FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/scripts

WORKDIR /app

COPY scripts /app/scripts
COPY database /app/database

EXPOSE 8080

CMD ["python", "-m", "recruiting_ai.server"]

