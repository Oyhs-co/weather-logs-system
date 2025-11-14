import os
import json
import time
import logging
import pika
import requests
import random
from datetime import datetime, timezone, timedelta

STATION      = os.getenv("STATION", "LEMD")
RABBITMQ_HOST= os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER= os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS= os.getenv("RABBITMQ_PASS", "guest")
INTERVAL     = int(os.getenv("INTERVAL", "60"))
SIMULATE     = os.getenv("SIMULATE", "false").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def fetch_simulated():
    """
    Genera datos simulados con variaciones mínimas.
    """
    base_temp = 20 + random.uniform(-1, 1)
    base_rh = 60 + random.uniform(-5, 5)
    base_pres = 1013 + random.uniform(-1, 1)
    
    return {
        "station": STATION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "temp": round(base_temp, 1),
        "rh": max(0, min(100, int(base_rh))),
        "pres": round(base_pres, 1),
        "wind": round(random.uniform(2, 4), 1),
        "rain": round(random.uniform(0, 0.1), 2)
    }

def fetch_real():
    """
    Obtiene el último dato horario de Meteostat v2 vía RapidAPI.
    """
    # Construcción de URL y parámetros según especificación V1
    url = "https://meteostat.p.rapidapi.com/stations/hourly"
    # Parámetros requeridos: station, start, end. Usamos hoy como valor por defecto
    today = datetime.now(timezone.utc).date().isoformat()
    params = {
        "station": STATION,
        "start": os.getenv("METEOSTAT_START", today),
        "end": os.getenv("METEOSTAT_END", today),
        "tz": os.getenv("METEOSTAT_TZ", "UTC"),
        "model": os.getenv("METEOSTAT_MODEL", "true"),
        "units": os.getenv("METEOSTAT_UNITS", "metric")
    }
    # Opcional: freq si está definida
    freq = os.getenv("METEOSTAT_FREQ")
    if freq:
        params["freq"] = freq

    headers = {
        "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", ""),
        "x-rapidapi-host": "meteostat.p.rapidapi.com"
    }

    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()["data"][0]
    return {
        "station": STATION, #estacion
        "ts":      data["time"], #timestamp
        "temp":    float(data["temp"] or 0.0), # temperatura
        "rh":      int(data["rhum"] or 0), # humedad relativa
        "pres":    float(data["pres"] or 1013.25), # presion al nivel del mar
        "wind":    int(data["wspd"] or 0), # velocidad del viento
        "rain":    float(data["prcp"] or 0.0) # precipitacion
    }

def publish(msg):
    creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    conn  = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST, credentials=creds))
    ch    = conn.channel()
    ch.exchange_declare(exchange='weather.topic', exchange_type='topic', durable=True)
    ch.basic_publish(
        exchange='weather.topic',
        routing_key=STATION,
        body=json.dumps(msg),
        properties=pika.BasicProperties(delivery_mode=2)  # persistent
    )
    conn.close()

def main():
    if SIMULATE:
        logging.info("SIMULATE mode ON: generating synthetic weather data")
    while True:
        try:
            if SIMULATE:
                data = fetch_simulated()
            else:
                data = fetch_real()
            publish(data)
            logging.info("published %s", data)
        except Exception:
            logging.exception("producer error")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()