# ==========================
#  STAGE 1 — Build frontend
# ==========================
FROM node:20-bullseye AS frontend-build

WORKDIR /app/frontend

# Copiar dependencias e instalarlas
COPY frontend/package*.json ./
RUN npm install

# Copiar resto del frontend
COPY frontend/ .

# 🧩 Hotfix para bug de Astro/Vite (tsconfig fantasma)
RUN mkdir -p /app/frontend/src/components && touch /app/frontend/src/components/tsconfig.json

# Build sin analizar tsconfig
RUN npx astro build --no-tsconfig

# Limpiar el fix temporal
RUN rm -f /app/frontend/src/components/tsconfig.json


# ==========================
#  STAGE 2 — Backend
# ==========================
FROM python:3.11-slim AS backend

# Instalar dependencias del sistema (Chromium + fonts + utilities)
RUN apt-get update && apt-get install -y \
    chromium chromium-driver fonts-liberation \
    libatk-bridge2.0-0 libnss3 libxss1 libasound2 libatk1.0-0 libgbm1 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libxshmfence1 \
    libgtk-3-0 libpango-1.0-0 libcairo2 libxext6 wget unzip \
    && rm -rf /var/lib/apt/lists/*

# Variables de entorno
ENV CHROME_PATH=/usr/bin/chromium
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=8080

WORKDIR /app

# Copiar backend y dependencias
COPY backend/ ./backend
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copiar build del frontend al backend (para servirlo)
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8080
WORKDIR /app/backend
CMD ["python", "main.py"]
