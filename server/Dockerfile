FROM python:3.14-slim
WORKDIR /app
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY server/main_api.py server/matcher.py server/database.py server/01_hotels_base.csv ./
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8000"]
