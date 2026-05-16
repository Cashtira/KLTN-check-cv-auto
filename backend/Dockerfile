FROM python:3.10-slim

# Cài đặt poppler-utils trực tiếp vào hệ điều hành Linux của Render
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Xóa biến môi trường poppler trên Windows để chạy theo cấu hình Linux
ENV POPPLER_PATH=""

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]