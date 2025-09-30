FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install mysql-connector-python pulp

COPY school_schedule.py .

CMD ["python", "school_schedule.py"]