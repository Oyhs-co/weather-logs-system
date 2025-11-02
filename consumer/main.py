import os
import json
import logging
import psycopg2
import pika
from prometheus_client import start_http_server, Counter

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB   = os.getenv("POSTGRES_DB", "weather")
POSTGRES_USER = os.getenv("POSTGRES_USER", "weather")
POSTGRES_PASS = os.getenv("POSTGRES_PASSWORD", "weather")
PROM_PORT     = int(os.getenv("PROMETHEUS_PORT", "8001"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# métricas
INSERT_COUNTER = Counter("weather_inserted_rows", "Total rows inserted")
INVALID_COUNTER = Counter("weather_invalid_msg", "Total invalid messages")

def pg_conn():
    return psycopg2.connect(host=POSTGRES_HOST, dbname=POSTGRES_DB,
                          user=POSTGRES_USER, password=POSTGRES_PASS)

def valid(msg):
    return (-40 <= msg["temp"] <= 60 and
            0 <= msg["rh"] <= 100 and
            870 <= msg["pres"] <= 1100)

def insert(msg):
    sql = """INSERT INTO weather_logs(station,ts,temp,rh,pres,wind,rain)
             VALUES (%(station)s,%(ts)s,%(temp)s,%(rh)s,%(pres)s,%(wind)s,%(rain)s)
             ON CONFLICT DO NOTHING"""
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, msg)
        conn.commit()
        INSERT_COUNTER.inc(cur.rowcount)

def on_message(ch, method, properties, body):
    try:
        msg = json.loads(body)
        if valid(msg):
            insert(msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            INVALID_COUNTER.inc()
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception:
        logging.exception("consumer error")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    start_http_server(PROM_PORT)
    creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    conn  = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST, credentials=creds))
    ch    = conn.channel()
    ch.exchange_declare(exchange='weather.topic', exchange_type='topic', durable=True)
    ch.queue_declare(queue='weather.queue', durable=True, arguments={"x-max-priority":10})
    ch.queue_bind(queue='weather.queue', exchange='weather.topic', routing_key='#')
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue='weather.queue', on_message_callback=on_message)
    logging.info("consumer ready")
    ch.start_consuming()

if __name__ == "__main__":
    main()