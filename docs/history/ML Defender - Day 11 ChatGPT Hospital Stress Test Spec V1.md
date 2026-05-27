# Hospital Network Stress Test Specification (v1)

## 1. Objective

Definir un procedimiento reproducible para evaluar rendimiento, estabilidad y resiliencia de la red hospitalaria simulada bajo condiciones de carga realista, incluyendo EHR/HL7/FHIR, PACS, dispositivos médicos IoT, estaciones administrativas y tráfico no clínico.

## 2. Scope

* IDS en modo gateway y host.
* Multi‑VM Lab con rutas diferenciadas.
* Carga mixta con patrones diurnos y ráfagas.
* Validación automática de latencia, jitter, p99/p999 y preservación de calidad clínica.

## 3. Traffic Classes

### 3.1 Electronic Health Records (EHR)

* Protocolos: HL7, FHIR/REST.
* Frecuencia: 20–50 msg/min.
* Distribución: Poisson.
* Payload: 2–20 KB.

### 3.2 PACS Imaging

* Modalidades: CT, MRI, XR.
* Ráfagas: 50–200 MB en bloques.
* Distribución: Lognormal.
* Intervalos: 10–40 min.

### 3.3 Medical IoT Devices

* Telemetría rítmica.
* Frecuencia: 1–5 Hz.
* Distribución: Weibull.
* Eventos: Alarma aleatoria.

### 3.4 Administrative Workstations

* Navegación interna.
* Requests: 2–5 por segundo.
* Tiempos de uso por turno.

### 3.5 Guest WiFi Noise

* Tráfico mixto HTTP/HTTPS.
* Patrones no deterministas.

## 4. Load Model

### 4.1 Diurnal Pattern

* Factor sinusoidal con tres picos:

    * Mañana: +30% carga.
    * Tarde: +20%.
    * Noche: -40%.

### 4.2 Burst Injection Model

* PACS bursts.
* Reinyección de colas.

## 5. Metrics Collected

* Latencia media / p50 / p90 / p99 / p999.
* Jitter.
* Throughput.
* Retransmisiones y drops.
* Carga CPU/memoria en IDS.
* Sensibilidad y falsos positivos del IDS.

## 6. Validation Criteria

* p99 < 200 ms para mensajes EHR.
* PACS bursts sin superar cola de 5 s.
* Zero‑loss en telemetría IoT.
* <0.5% false positives EHR.

## 7. Automation Rules

* Scripts de generación de tráfico.
* Extractores de métricas basados en logs.
* Comparación automática con criterios.

## 8. Test Procedure

1. Inicializar topología multi‑VM.
2. Activar perfiles de carga.
3. Ejecutar ráfagas PACS.
4. Registrar métricas durante 45–60 min.
5. Evaluar criterios automáticamente.

## 9. Output Artifacts

* `stress_results.json`.
* `latency_dashboard.html`.
* `pacs_burst_profile.csv`.
* Informe comparativo con criterios.

## 10. Next Steps

* Validación cruzada con perfiles alternativos.
* Afinar modelos ML con datos reales.
* Preparación para documentación Day 12.
