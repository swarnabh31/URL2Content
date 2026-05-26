FROM python:3.11-slim

WORKDIR /app

# Install system deps for weasyprint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
    libfontconfig1 libfreetype6 libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]