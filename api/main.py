import os
import psycopg2
import io
import csv
from datetime import datetime
from fastapi import FastAPI, Query, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Weather-Logs API")

# Métricas Prometheus
REQUESTS_TOTAL = Counter("api_requests_total", "Total de requests a la API", ["endpoint", "method"])
REQUEST_DURATION = Histogram("api_request_duration_seconds", "Duración de requests", ["endpoint"])

PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
PG_DB   = os.getenv("POSTGRES_DB", "weather")
PG_USER = os.getenv("POSTGRES_USER", "weather")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "weather")

def pg_conn():
    return psycopg2.connect(host=PG_HOST, dbname=PG_DB, user=PG_USER, password=PG_PASS)

@app.get("/logs")
def read_logs(
    station: str = Query(None, description="Filtrar por estación"),
    start: datetime = Query(None, description="Inicio (ISO 8601)"),
    end: datetime = Query(None, description="Fin (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=10000)
):
    where, args = [], []
    if station:
        where.append("station = %s"); args.append(station)
    if start:
        where.append("ts >= %s"); args.append(start)
    if end:
        where.append("ts <= %s"); args.append(end)
    sql = "SELECT * FROM weather_logs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY ts DESC LIMIT %s"
    args.append(limit)
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return {"columns": cols, "rows": rows}

@app.get("/logs.csv")
def csv_report(
    station: str = Query(None),
    start: datetime = Query(None),
    end: datetime = Query(None)
):
    data = read_logs(station=station, start=start, end=end, limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(data["columns"])
    writer.writerows(data["rows"])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=weather.csv"}
    )

@app.get("/health")
def health():
    with pg_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM weather_logs")
        count = cur.fetchone()[0]
    return {"status": "ok", "rows": count}


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )