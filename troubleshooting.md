# Solución de Problemas Frecuentes

A continuación, se presentan soluciones a problemas comunes que pueden surgir al configurar o ejecutar el sistema.

## 1. Error en el Productor: `401 Unauthorized`

**Problema:** El servicio del productor falla al iniciarse y muestra un error `401 Unauthorized` en los registros.

**Causa:** La clave de RapidAPI no se ha configurado correctamente o es inválida.

**Solución:**

1.  Asegúrate de haber creado un archivo `.env` en la raíz del proyecto.
2.  Verifica que la variable `RAPIDAPI_KEY` esté definida en el archivo `.env`.
3.  Asegúrate de que el valor de `RAPIDAPI_KEY` sea una clave válida de RapidAPI con una suscripción activa a la API de Meteostat.

**Ejemplo de `.env`:**

```
RAPIDAPI_KEY=tu_clave_de_rapidapi
```

## 2. Los Contenedores no se Inician

**Problema:** Al ejecutar `docker-compose up`, algunos contenedores no se inician correctamente.

**Causa:** Puede haber varias causas, como puertos ocupados, falta de recursos o problemas de red.

**Solución:**

- **Verifica los puertos:** Asegúrate de que los puertos utilizados por los servicios (ej. 8000, 5432, 15672) no estén en uso por otras aplicaciones.
- **Revisa los registros:** Utiliza el comando `docker-compose logs <nombre_del_servicio>` para ver los registros del contenedor que falla y obtener más información sobre el error.
- **Aumenta los recursos de Docker:** Si estás en un entorno con recursos limitados, considera aumentar la memoria o la CPU asignada a Docker.

## 3. No se Muestran Datos en Grafana

**Problema:** El panel de control de Grafana no muestra ningún dato.

**Causa:** Puede haber un problema en la cadena de recolección de datos (Productor → RabbitMQ → Consumidor → Prometheus → Grafana).

**Solución:**

1.  **Verifica el Productor:** Asegúrate de que el productor esté funcionando y publicando mensajes. Revisa los registros del productor con `docker-compose logs producer`.
2.  **Verifica RabbitMQ:** Accede a la interfaz de administración de RabbitMQ en `http://localhost:15672` y comprueba que los mensajes se están publicando en la cola `weather.queue`.
3.  **Verifica el Consumidor:** Asegúrate de que el consumidor esté en funcionamiento y procesando los mensajes. Revisa los registros del consumidor con `docker-compose logs consumer`.
4.  **Verifica Prometheus:** Accede a la interfaz de Prometheus en `http://localhost:9090` y comprueba que el consumidor se esté scrapeando correctamente. Ve a `Status > Targets` para verificar el estado del endpoint del consumidor.
5.  **Verifica la Fuente de Datos en Grafana:** Asegúrate de que la fuente de datos de Prometheus esté configurada correctamente en Grafana.
