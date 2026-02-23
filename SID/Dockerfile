cat <<EOF > Dockerfile
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Instala dependências para o PostgreSQL
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Instala as dependências do projeto
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . /app/

# Coleta arquivos estáticos (CSS/JS)
RUN python manage.py collectstatic --noinput

# Inicia o servidor (ajustado para o seu projeto)
CMD exec gunicorn projeto.wsgi:application --bind 0.0.0.0:\$PORT --workers 1 --threads 8 --timeout 0
EOF