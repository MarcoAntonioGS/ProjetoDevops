FROM python:3.13-slim

# Instalar dependências do Tkinter (necessário para GUI no container)
RUN apt-get update && apt-get install -y python3-tk && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install mysql-connector-python pulp

# Copiar o código
COPY school_schedule.py .

# Comando para rodar a app
CMD ["python", "school_schedule.py"]