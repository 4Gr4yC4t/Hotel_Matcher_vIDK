FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY test.py 01_hotels_external_10.csv ./
COPY datainput/ ./datainput/
RUN mkdir -p /app/output
CMD ["python", "test.py"]