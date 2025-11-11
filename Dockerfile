FROM python:3.11-slim

WORKDIR /app

# Avoid cache problems and install packages
COPY custom_exporter.py /app/custom_exporter.py

# Install required packages
RUN pip install --no-cache-dir prometheus_client requests

EXPOSE 8000

ENV UPDATE_INTERVAL=20
ENV EXPORTER_PORT=8000

CMD ["python", "custom_exporter.py"]