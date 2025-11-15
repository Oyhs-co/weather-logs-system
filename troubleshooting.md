# Solución de Problemas Frecuentes

A continuación se presentan soluciones y pasos de diagnóstico para problemas habituales tras los cambios recientes del proyecto (productor/consumer/API/Prometheus/Grafana/DB). Mantén este documento como referencia rápida para debugging.

## 1. Error en el Productor: `401 Unauthorized` / `429 Too Many Requests`

Problema: El productor falla con `401` o `429` al consumir Meteostat vía RapidAPI.

Causas comunes:
- `RAPIDAPI_KEY` ausente o inválida.
- Límite de peticiones excedido (rate-limit).
- Parámetros `station`, `start`/`end` inválidos.

Solución:
```bash
# Ver logs del productor
docker-compose logs producer

# Si no quieres usar RapidAPI mientras debuggeas:
# 1) Habilita modo simulado en .env
#    SIMULATE=true
# 2) Reinicia el servicio
docker-compose up -d --no-deps --build producer
```
Recomendaciones:
- Reduce `INTERVAL` para evitar rate limits o usa `SIMULATE=true`.
- Verifica `RAPIDAPI_KEY` en `.env`.
- Revisa la respuesta completa de la API en los logs para detectar mensajes de error (quota, parámetro).

## 2. Contenedores no se Inician o quedan en Restart Loop

Problema: Algunos servicios quedan en estado `Exit` o `Restarting`.

Diagnóstico y comandos:
```bash
docker-compose ps
docker-compose logs <service>
docker inspect --format '{{json .State.Health}}' $(docker-compose ps -q <service>)
```
Causas y soluciones:
- Puertos ocupados: libera o cambia puertos en `.env` / `docker-compose.yml`.
- Variables de entorno faltantes o mal escritas: revisa `.env` y `docker-compose.yml`.
- Healthchecks fallando: comprueba que el comando del healthcheck funciona dentro del contenedor.
- Recursos insuficientes: aumenta memoria/CPU en la configuración de Docker Desktop.

## 3. No hay datos en Grafana / Prometheus Targets DOWN

Problema: Dashboards vacíos o targets en Prometheus muestran DOWN.

Pasos de verificación:
```bash
# Comprobar endpoints de métricas desde host
curl http://localhost:8001/metrics   # consumer
curl http://localhost:8000/metrics   # api

# Revisar targets en Prometheus UI: http://localhost:9090 → Status → Targets
```
Causas y soluciones:
- Prometheus usa nombres de servicio en la red Docker: asegúrate que `prometheus.yml` apunta a `consumer:8001` y `api:8000` (no a `localhost`).
- Servicios no exponen métricas (ver logs del servicio).
- Firewalls/puertos no mapeados en la máquina host.
- Grafana datasource mal configurado: comprueba `grafana/provisioning/datasources/datasource.yml` y logs de Grafana.

Comandos útiles:
```bash
docker-compose exec prometheus cat /etc/prometheus/prometheus.yml
docker-compose logs prometheus
docker-compose logs grafana
```

## 4. RabbitMQ: Mensajes en cola / Unacked / No llegan al consumidor

Problema: Mensajes se acumulan en la cola o aparecen como "unacked".

Verificación:
- Accede a UI: http://localhost:15672 (guest/guest)
- Revisa `Queues`, `Exchanges`, `Connections`, `Channels`.

Comandos:
```bash
# Desde el host, ejecuta en el contenedor rabbitmq:
docker-compose exec rabbitmq rabbitmqctl list_queues name messages consumers
docker-compose exec rabbitmq rabbitmqctl list_connections
```

Causas y soluciones:
- Consumer lanza excepción y hace basic_nack(requeue=True) → mensaje vuelve a la cola y puede quedar en loop.
  - Revisa logs del consumidor: `docker-compose logs consumer`.
  - Si un mensaje es inválido, consumer debe nack y no requeue; revisar comportamiento en `consumer/main.py`.
- Queue no ligada al exchange correctamente: revisa bindings y routing key.
- Prioridad/arguments de la queue (`x-max-priority`) y durable settings: confirma configuración en `docker-compose` y en consumidor (exchange/queue_declare).

## 5. Consumer: errores de insert / bucle de reintentos / métricas no actualizan

Problema: Inserciones no ocurren, métricas no reflejan actividad o consumer se reinicia por excepción.

Diagnóstico:
```bash
docker-compose logs -f consumer
docker-compose exec consumer tail -n 200 /root/.cache/* || true
```
Causas y soluciones:
- Formato JSON incorrecto o campos faltantes → JSONDecodeError o KeyError. Revisa logs para traza.
- Si ocurre excepción en insert(), consumer hace basic_nack(requeue=True) → mensajes reencolados. Corregir datos fuente o ajustar manejo en código.
- Verifica que PostgreSQL está accesible desde el container del consumer (`POSTGRES_HOST` correcto).
  ```bash
  docker-compose exec consumer python -c "import psycopg2; print('ok')"
  ```
- Métricas Prometheus: verifica puerto `PROMETHEUS_PORT` y que `start_http_server` se esté ejecutando (consumer expondrá métricas en :8001).

## 6. PostgreSQL: inicialización de scripts / errores de migración / tablas faltantes

Problema: DB no contiene tabla `weather_logs` o scripts no se ejecutaron.

Causas:
- Los scripts en `./sql` sólo se ejecutan la primera vez que se crea el volumen de postgres.
- Si el volumen existe, los scripts no se re-aplican.

Soluciones:
```bash
# Ver estructura de la tabla desde host
psql "host=localhost port=5432 dbname=weather user=weather password=weather" -c "\d weather_logs"

# Para re-ejecutar scripts (ADVERTENCIA: borrará datos)
docker-compose down -v
docker-compose up -d postgres
# Esperar a que el contenedor inicialice, luego levantar el resto
docker-compose up -d
```
Comprobar logs de Postgres:
```bash
docker-compose logs postgres
```

## 7. Exportación CSV pesada (/logs.csv consume memoria)

Problema: Descarga CSV para rangos grandes genera uso elevado de memoria o timeouts.

Explicación: `/logs.csv` usa el endpoint `/logs` con límite 10000. Para datasets mayores, es preferible exportar desde Postgres con COPY.

Recomendación:
```sql
-- Exportar desde postgres (en host con psql):
COPY (SELECT * FROM weather_logs WHERE station='LEMD' ORDER BY ts DESC) TO STDOUT WITH CSV HEADER;
```
O usando docker:
```bash
docker-compose exec postgres psql -U weather -d weather -c "\copy (SELECT * FROM weather_logs) TO '/tmp/weather.csv' CSV HEADER"
docker cp $(docker-compose ps -q postgres):/tmp/weather.csv ./weather.csv
```

## 8. Errores de dependencias / ImportError / NameError en contenedores Python

Problema: ImportError, NameError (ej. falta `random` o `requests`) o versiones de paquetes incompatibles.

Diagnóstico:
```bash
docker-compose exec producer python -c "import requests, random; print('ok')"
docker-compose exec producer pip freeze
```
Solución:
- Revisa `requirements.txt` en cada servicio.
- Reconstruye la imagen tras actualizar dependencias:
```bash
docker-compose build --no-cache producer
docker-compose up -d producer
```

## 9. Healthchecks en docker-compose: dependencias y orden de arranque

Nota importante: `depends_on: condition: service_healthy` espera healthcheck del servicio. Si los healthchecks están mal configurados, dependientes pueden quedar esperando.

Diagnóstico:
```bash
docker inspect --format '{{json .State.Health}}' $(docker-compose ps -q rabbitmq)
```
Solución:
- Ajusta o simplifica healthchecks durante debugging.
- Evita usar `condition: service_healthy` si prefieres manejar dependencias dentro de la app.

## 10. Grafana: dashboards no provisionados al iniciar

Problema: Dashboards faltantes o sin datos.

Verifica:
- Volumen y rutas en `docker-compose.yml` (`./grafana/provisioning` montado correctamente).
- Logs de Grafana para errores de provisioning:
```bash
docker-compose logs grafana
```
Si los dashboards no aparecen, ingresa al contenedor y revisa `/etc/grafana/provisioning` y `/var/lib/grafana/dashboards`.

## 11. Permisos y Volúmenes (datos persistentes)

Problema: Postgres no escribe en volumen, permisos deny.

Solución:
- Revisa ownership/perm de los volúmenes en el host (en Windows con Docker Desktop los permisos difieren).
- Si quieres resetear volúmenes:
```bash
docker-compose down -v
```
(Esto elimina datos persistentes).

## 12. Comandos rápidos de diagnóstico

```bash
# Estado general
docker-compose ps

# Logs en tiempo real
docker-compose logs -f consumer producer api prometheus grafana rabbitmq postgres

# Entrar a un contenedor
docker-compose exec consumer bash

# Comprobar métricas desde host
curl http://localhost:8001/metrics
curl http://localhost:8000/metrics
```

## 13. Qué revisar en los logs (qué buscar para poder orientarse)

- Tracebacks completos (stack trace) para identificar la línea exacta del error.
- Mensajes HTTP de RapidAPI (códigos 401, 429, 400).
- Excepciones de conexión a Postgres (timeout, auth failed).
- JSON malformado en consumer (KeyError, TypeError).
- Mensajes de RabbitMQ sobre colas y bindings.
