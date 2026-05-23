# DEBT-CONFIG-JINJA2-PIPELINE-001

## Estado
Abierta — DAY 161

## Descripción
Sistema de plantillas Jinja2 para generación de configuraciones por perfil hardware.

## Motivación
Los ficheros JSON en `*/config/` son sagrados — nunca se modifican directamente.
En producción (RPi5, N100, servidor FEDER) no existirán los JSON originales.
El script generará el fichero correcto calculando valores óptimos para el hardware destino.

## Diseño acordado DAY 161
- `json-templates/` — plantillas Jinja2 con {{variables}} extraídas de los JSON originales
- `json-values/naive.json` — valores dev actuales (extraídos de los originales)
- `json-values/edge-low.json` — ≤4GB RAM (RPi5 4GB)
- `json-values/edge-medium.json` — 8GB RAM (RPi5 8GB / N100)
- `json-values/edge-high.json` — ≥16GB RAM (servidor FEDER)
- `json-generated/` — salida (.gitignore), nombrada `component-DDMMYYYY.json`
- `tools/generate_config.py` — orquesta Jinja2: template + values → generated

## Ficheros a templatear (en orden de prioridad)
1. firewall-acl-agent/config/firewall.json         (parámetros ZMQ + batch + threads)
2. etcd-server/config/etcd-server.json             (worker_threads)
3. ml-detector/config/ml_detector_config.json      (threads + queues + memory)
4. sniffer/config/sniffer.json                     (pendiente)
5. sniffer/config/sniffer-libpcap.json             (pendiente)
6. rag-ingester/config/rag-ingester.json           (pendiente)
7. etcd-client/config/etcd_client_config.json      (pendiente)
8. rag/config/rag-config.json                      (pendiente)
9. ml-detector/config/rag_logger_config.json       (pendiente)

## Prerequisitos
- BACKLOG-ZMQ-TUNING-001: benchmarks físicos en hardware UEx antes de valores reales
- Hardware físico disponible (RPi5x2 + N100x2) — pendiente adquisición FEDER

## Notas
- En dev: el binario usa los JSON originales (comportamiento actual, sin cambios)
- En prod: SOLO existen los JSON generados — los originales no se distribuyen
- El script debe calcular valores óptimos en función del hardware detectado
- Jinja2 3.1.6 disponible en el entorno Mac del fundador

## Prioridad
P2 — después de DEBT-WIRE-PROTOCOL-TEST-001 y Jenkinsfile

## Deadline
Antes de primera demo FEDER con hardware físico UEx
