FROM python:3.11-slim
WORKDIR /app
COPY notification_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY notification_service/ ./notification_service/
CMD ["python", "-m", "notification_service.main"]
