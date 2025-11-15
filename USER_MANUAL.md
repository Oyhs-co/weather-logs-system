# Manual de Usuario

Este manual proporciona una guía práctica y actualizada para configurar, ejecutar y verificar el sistema de monitoreo meteorológico.

## Tabla de Contenidos

- [Configuración del Entorno](#configuración-del-entorno)  
  - [Requisitos Previos](#requisitos-previos)  
  - [Variables de Entorno](#variables-de-entorno)  
  - [Clave de RapidAPI](#clave-de-rapidapi)  
- [Ejecución del Sistema](#ejecución-del-sistema)  
- [Verificación y Pruebas](#verificación-y-pruebas)  
  - [Verificar que los Contenedores estén en Funcionamiento](#verificar-que-los-contenedores-esten-en-funcionamiento)  
  - [Pruebas de Endpoints](#pruebas-de-endpoints)  
  - [Monitoreo](#monitoreo)  
- [Operación y Depuración de Servicios Individuales](#operación-y-depuración-de-servicios-individuales)  
  - [Productor (producer)](#productor-producer)  
  - [Consumidor (consumer)](#consumidor-consumer)  
  - [API (api)](#api-api)  
  - [Postgres, RabbitMQ, Prometheus, Grafana](#postgres-rabbitmq-prometheus-grafana)  
- [Tareas Administrativas](#tareas-administrativas)  
  - [Re-ejecutar scripts SQL / recrear esquema](#re-ejecutar-scripts-sql--recrear-esquema)  
  - [Exportar datos (CSV / COPY)](#exportar-datos-csv--copy)  
- [Notas para Windows / Docker Desktop](#notas-para-windows--docker-desktop)  
- [Buenas prácticas y seguridad](#buenas-prácticas-y-seguridad)  
- [Dónde buscar ayuda](#dónde-buscar-ayuda)

---

## Configuración del Entorno

### Requisitos Previos

- Docker (Desktop) v20.10+  
- Docker Compose v2+  
- Git  
- (Opcional) RapidAPI Key para Meteostat si no se usa modo simulado

### Variables de Entorno

Crea `.env` basado en `.env.example`. Las variables principales a revisar:

- `RABBITMQ_HOST, RABBITMQ_USER, RABBITMQ_PASS`  
- `POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD`  
- `STATION, INTERVAL, SIMULATE`  
- `RAPIDAPI_KEY` (si SIMULATE=false)  
- `PROMETHEUS_PORT`

No dupliques aquí detalles largos; la lista completa está en el [README](README.md). Mantén el archivo `.env` fuera de repositorios públicos.

### Clave de RapidAPI

Si usas datos reales (SIMULATE=false) necesitas una clave RapidAPI:

1. Regístrate en https://rapidapi.com/  
2. Busca "Meteostat" → suscríbete  
3. Copia `x-rapidapi-key` en `.env` como `RAPIDAPI_KEY`

---

## Ejecución del Sistema

Levantar todos los servicios en segundo plano:

```bash
git clone https://github.com/Oyhs-co/weather-logs-system.git
cd weather-logs-system
cp .env.example .env
# editar .env según sea necesario
docker-compose up -d
```

Detener y eliminar contenedores (sin borrar volúmenes):

```bash
docker-compose down
```

---

## Verificación y Pruebas

### Verificar que los Contenedores estén en Funcionamiento

```bash
docker-compose ps
```

Esperar que los servicios aparezcan `Up`. Para ver healthchecks:

```bash
docker inspect --format '{{json .State.Health}}' $(docker-compose ps -q postgres)
```

### Pruebas de Endpoints

- Health API:

```bash
curl http://localhost:8000/health
```

- Logs (JSON):

```bash
curl "http://localhost:8000/logs?station=LEMD&limit=10"
```

- Descargar CSV:

```bash
curl "http://localhost:8000/logs.csv?station=LEMD" -o weather_data.csv
```

- Métricas API:

```bash
curl http://localhost:8000/metrics
```

### Monitoreo

- Prometheus UI: http://localhost:9090  
- Grafana UI: http://localhost:3000 (usuario por defecto: admin/admin)

---

## Operación y Depuración de Servicios Individuales

A continuación comandos y notas prácticas para operar y depurar cada componente.

### Productor (producer)

- Modo simulado (no requiere RAPIDAPI_KEY): setear `SIMULATE=true` en `.env`.  
- Para reconstruir y levantar solo el productor:

```bash
docker-compose build --no-cache producer
docker-compose up -d --no-deps producer
docker-compose logs -f producer
```

- Ejecutar en primer plano para debugging:

```bash
docker-compose up producer
```

- Problemas comunes: 401/429 → revisar `RAPIDAPI_KEY`, rate limits y `INTERVAL`. Cuando debugees, usa `SIMULATE=true`.

### Consumidor (consumer)

- Exposición de métricas en `PROMETHEUS_PORT` (por defecto 8001). Ver métrica:

```bash
curl http://localhost:8001/metrics
```

- Reconstruir y reiniciar:

```bash
docker-compose build consumer
docker-compose up -d --no-deps consumer
docker-compose logs -f consumer
```

- Validaciones aplicadas por el consumidor:
  - temp: -40..60  
  - rh: 0..100  
  - pres: 870..1100

Si el consumidor cae con excepciones, revisa logs; si un mensaje inválido genera requeue en loop, ajustar manejo (ack/nack) o corregir origen.

### API (api)

- Reconstruir y ver logs:

```bash
docker-compose build api
docker-compose up -d --no-deps api
docker-compose logs -f api
```

- Swagger UI:

```
http://localhost:8000/docs
```

- CSV grande: el endpoint `/logs.csv` limita a 10000 filas; para dumps grandes usar COPY desde Postgres (ver sección "Exportar datos").

### Postgres, RabbitMQ, Prometheus, Grafana

- Reiniciar solo Postgres:

```bash
docker-compose up -d --no-deps postgres
```

- Acceder RabbitMQ Management: http://localhost:15672 (guest/guest por defecto)  
- Ver cola y conexiones en rabbit:

```bash
docker-compose exec rabbitmq rabbitmqctl list_queues name messages consumers
docker-compose exec rabbitmq rabbitmqctl list_connections
```

---

## Tareas Administrativas

### Re-ejecutar scripts SQL / recrear esquema

Los scripts en `sql/` se ejecutan solo al inicializar el volumen. Opciones:

- Ejecutar script dentro del contenedor postgres (sin borrar volúmenes):

```bash
docker-compose exec postgres psql -U ${POSTGRES_USER:-weather} -d ${POSTGRES_DB:-weather} -f /docker-entrypoint-initdb.d/01-schema.sql
```

- Recrear volumen (ELIMINA datos):

```bash
docker-compose down -v
docker-compose up -d
```

- Ejecutar desde host con psql:

```bash
psql "host=localhost port=5432 dbname=weather user=weather password=weather" -f sql/01-schema.sql
```

### Exportar datos (CSV / COPY)

El endpoint `/logs.csv` construye el CSV en memoria y tiene límite. Para volúmenes grandes usar COPY:

- Exportar con psql COPY (desde host):

```sql
COPY (SELECT * FROM weather_logs WHERE station='LEMD' ORDER BY ts DESC) TO STDOUT WITH CSV HEADER;
```

- Usando Docker para crear archivo dentro del contenedor postgres y copiarlo al host:

```bash
docker-compose exec postgres psql -U weather -d weather -c "\copy (SELECT * FROM weather_logs) TO '/tmp/weather.csv' CSV HEADER"
docker cp $(docker-compose ps -q postgres):/tmp/weather.csv ./weather.csv
```

---

## Notas para Windows / Docker Desktop

- Volúmenes y permisos: en Windows pueden aparecer problemas de permisos. Si Postgres no escribe, reinicia Docker Desktop o recrea volúmenes:

```bash
docker-compose down -v
docker-compose up -d
```

- Recursos: si hay reinicios o OOM, aumenta memoria/CPU en la configuración de Docker Desktop.

- Rutas y comandos psql: en Windows, `psql` desde host requiere instalación previa; usa los comandos dentro del contenedor postgres cuando sea posible.

---

## Buenas prácticas y seguridad

- No subir `.env` ni claves a repositorios públicos.  
- Cambiar credenciales por defecto (`guest/guest`, `weather/weather`) en entornos no de desarrollo.  
- Limitar puertos expuestos en producción.  
- Monitorizar rate limits de RapidAPI para evitar bloqueos.

---

## Dónde buscar ayuda

- Para problemas operativos y pasos de diagnóstico detallados revisa [`troubleshooting.md`](troubleshooting.md).  
- Para cambios en la arquitectura y configuración general revisa [`README.md`](README.md)  
- Para asistencia muy específica, necesitarás valerte de:
  - Logs relevantes (últimas ~200 líneas) de servicios implicados:

```bash
docker-compose logs --tail=200 consumer producer api postgres rabbitmq
```

  - Contenido de `.env` (sin claves).  
  - Capturas de pantalla de Prometheus/Grafana (si aplica) o traza de error.

Última actualización: Noviembre 2025