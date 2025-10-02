FROM python:3.10-slim
WORKDIR /app
COPY app.py .
RUN pip install flask boto3
CMD ["python", "app.py"]
