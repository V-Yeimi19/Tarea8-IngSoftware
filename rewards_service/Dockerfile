FROM python:3.11-slim
WORKDIR /app
RUN mkdir -p /app/data
COPY rewards_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY rewards_service/ ./rewards_service/
CMD ["python", "-m", "rewards_service.main"]
