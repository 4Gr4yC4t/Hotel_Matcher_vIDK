FROM python:3.14-slim
WORKDIR /app
COPY client/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY client/test.py ./
COPY client/datainput/ ./datainput/
RUN mkdir -p /app/output
CMD ["python", "test.py"]
