FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --network=host -r requirements.txt

COPY ./src /app/src

WORKDIR /app/src
CMD ["python", "aiogram_run.py"]