# Manual de Usuario

Este manual proporciona una guía detallada para configurar, ejecutar y probar el sistema de monitoreo meteorológico.

## Tabla de Contenidos

- [Manual de Usuario](#manual-de-usuario)
  - [Tabla de Contenidos](#tabla-de-contenidos)
  - [Configuración del Entorno](#configuración-del-entorno)
    - [Requisitos Previos](#requisitos-previos)
    - [Variables de Entorno](#variables-de-entorno)
    - [Clave de RapidAPI](#clave-de-rapidapi)
  - [Ejecución del Sistema](#ejecución-del-sistema)
  - [Verificación y Pruebas](#verificación-y-pruebas)
    - [Verificar que los Contenedores esten en Funcionamiento](#verificar-que-los-contenedores-esten-en-funcionamiento)
    - [Pruebas de Endpoints](#pruebas-de-endpoints)
    - [Monitoreo](#monitoreo)
  - [Solución de Problemas](#solución-de-problemas)

## Configuración del Entorno

### Requisitos Previos

- Docker
- Docker Compose

### Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto a partir del archivo `.env.example`. A continuación, se describen las variables de entorno que puedes configurar:

| Variable            | Descripción                                                           | Valor por Defecto |
| ------------------- | --------------------------------------------------------------------- | ----------------- |
| `RABBITMQ_HOST`     | Host de RabbitMQ.                                                     | `rabbitmq`        |
| `RABBITMQ_USER`     | Usuario de RabbitMQ.                                                  | `guest`           |
| `RABBITMQ_PASS`     | Contraseña de RabbitMQ.                                               | `guest`           |
| `POSTGRES_HOST`     | Host de PostgreSQL.                                                   | `postgres`        |
| `POSTGRES_DB`       | Nombre de la base de datos de PostgreSQL.                             | `weather`         |
| `POSTGRES_USER`     | Usuario de PostgreSQL.                                                | `weather`         |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL.                                             | `weather`         |
| `STATION`           | Estación meteorológica de la que se obtendrán los datos.              | `LEMD`            |
| `INTERVAL`          | Intervalo en segundos para obtener los datos.                         | `60`              |
| `PROMETHEUS_PORT`   | Puerto en el que el consumidor expone las métricas de Prometheus.     | `8001`            |
| `RAPIDAPI_KEY`      | **(Requerido)** Clave de RapidAPI para acceder a la API de Meteostat. |                   |

### Clave de RapidAPI

Para obtener una clave de RapidAPI, sigue estos pasos:

1.  Ve a [RapidAPI](https://rapidapi.com/) y crea una cuenta.
2.  Busca la API de "Meteostat" y suscríbete a ella.
3.  Copia tu clave de RapidAPI y pégala en el archivo `.env` como valor de la variable `RAPIDAPI_KEY`.

## Ejecución del Sistema

Para ejecutar el sistema, utiliza el siguiente comando:

```bash
docker-compose up -d
```

Este comando levantará todos los servicios en segundo plano. Para detener el sistema, utiliza:

```bash
docker-compose down
```

## Verificación y Pruebas

### Verificar que los Contenedores esten en Funcionamiento

Para verificar que todos los contenedores se están ejecutando correctamente, utiliza el siguiente comando:

```bash
docker-compose ps
```

Deberías ver todos los servicios en estado `Up`.

### Pruebas de Endpoints

Puedes probar los endpoints de la API utilizando herramientas como `curl` o Postman.

- **Verificar que la API está en funcionamiento:**

  ```bash
  curl http://localhost:8000/health
  ```

- **Obtener los últimos 10 registros de la estación `LEMD`:**

  ```bash
  curl "http://localhost:8000/logs?station=LEMD&limit=10"
  ```

- **Descargar los datos en formato CSV:**

  ```bash
  curl "http://localhost:8000/logs.csv?station=LEMD" -o weather_data.csv
  ```

### Monitoreo

- **Prometheus:** `http://localhost:9090`
- **Grafana:** `http://localhost:3000` (inicia sesión con `admin`/`admin`)

## Solución de Problemas

Para obtener ayuda con problemas comunes, consulta el archivo [troubleshooting.md](troubleshooting.md).
