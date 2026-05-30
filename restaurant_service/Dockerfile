FROM python:3.11-slim
WORKDIR /app
COPY restaurant_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY restaurant_service/ ./restaurant_service/
CMD ["uvicorn", "restaurant_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
