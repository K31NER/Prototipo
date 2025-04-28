# Usar una imagen oficial de Python como base
FROM python:3.11.8-slim

# Crear un directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar los requerimientos
COPY requirements.txt .


# Instalar los paquetes
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright y los navegadores
RUN pip install playwright
RUN playwright install chromium
RUN playwright install-deps

# Copiar el resto del proyecto al contenedor
COPY . .

# Exponer el puerto donde FastAPI corre (por defecto 8000)
EXPOSE 8000

# Comando para correr la app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
