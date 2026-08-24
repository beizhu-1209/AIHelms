FROM python:3.11-slim

WORKDIR /app
COPY dsh/manager/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY dsh/manager/ ./

EXPOSE 8080
CMD ["uvicorn", "manager:app", "--host", "0.0.0.0", "--port", "8080"]
