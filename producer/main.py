import os
import json
import time
import logging
import pika
import requests
from datetime import datetime, timezone

STATION      = os.getenv("STATION", "LEMD")
RABBITMQ_HOST= os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER= os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS= os.getenv("RABBITMQ_PASS", "guest")
INTERVAL     = int(os.getenv("INTERVAL", "60"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def fetch_real():
    """
    Obtiene el último dato horario de Meteostat v2 vía RapidAPI.
    """
    url = f"https://meteostat.p.rapidapi.com/stations/{STATION}/hourly"
    params = {"limit": 1, "offset": 0}
    headers = {
        "X-RapidAPI-Key":  os.getenv("RAPIDAPI_KEY", ""),
        "X-RapidAPI-Host": "meteostat.p.rapidapi.com"
    }
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()["data"][0]
    return {
        "station": STATION,
        "ts":      data["time"],
        "temp":    float(data["temperature"]),
        "rh":      int(data["rhum"] or 0),
        "pres":    float(data["sealevel"] or 1013.25),
        "wind":    int(data["wspd"] or 0),
        "rain":    float(data["prcp"] or 0.0)
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
    while True:
        try:
            data = fetch_real()
            publish(data)
            logging.info("published %s", data)
        except Exception as e:
            logging.exception("producer error")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()