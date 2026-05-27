# ADR-005 — Unificación de logs del ml-detector

**Estado:** ACCEPTED — pendiente implementación (post-paper, bloqueado por ENT-4 hot-reload)
**Fecha:** 2026-03-10 (DAY 81)
**Autor:** Alonso + Consejo de Sabios
**Componente:** ml-detector

---

## Contexto

El ml-detector genera actualmente **dos ficheros de log distintos** con orígenes
y formatos diferentes:

### `detector.log`
- **Origen:** spdlog interno del proceso C++
- **Configurado en:** `ml-detector/config/ml_detector_config.json` → `logging.file`
- **Valor actual:** `/vagrant/logs/lab/detector.log`
- **Formato:** `[timestamp] [ml-detector] [level] [pid] mensaje`
- **Contenido:** Toda la actividad estructurada — DUAL-SCORE, Stats, HTTP
  heartbeats, alertas de features, errores de inferencia

### `ml-detector.log`
- **Origen:** stdout/stderr del proceso redirigido por el Makefile
- **Configurado en:** `Makefile` → `>> /vagrant/logs/lab/ml-detector.log 2>&1`
- **Formato:** Banner ASCII + texto plano no estructurado
- **Contenido:** Arranque del proceso, carga de configuración, mensajes de
  inicialización que van a stdout antes de que spdlog esté activo

### CSV de eventos
- **Origen:** `csv_writer` interno
- **Configurado en:** `ml_detector_config.json` → `csv_writer.base_dir`
- **Valor actual:** `/vagrant/logs/ml-detector/events/`
- **Función:** Input para rag-ingester (pipeline de datos, no log operacional)
- **No afectado por este ADR**

---

## Problema

1. **Dos ficheros para un componente** — confusión sobre cuál consultar para
   diagnosticar problemas. En DAY 81 se comprobó que `grep 'Stats:'` debe ir
   a `ml-detector.log` (stdout Makefile) pero `grep 'DUAL-SCORE'` va a
   `detector.log` (spdlog).

2. **Idioma mixto** — algunos mensajes en español (`sniffer.log`), inglés
   (`detector.log`), y texto decorativo (banners ASCII). No grep-friendly.

3. **`log_file` hardcodeado parcialmente** — la ruta `/vagrant/logs/lab/detector.log`
   está en el JSON (correcto), pero el nombre `ml-detector.log` está hardcodeado
   en el Makefile (violación menor de "JSON is the LAW").

---

## Decisión

### Inmediata (ya implementada)
- Documentar el estado actual como deuda técnica conocida
- Usar `detector.log` como fuente de verdad para análisis operacional
  (DUAL-SCORE, Stats, alertas)
- Usar `ml-detector.log` solo para diagnóstico de arranque

### Futura (post-paper, junto con ENT-4 hot-reload)

**Opción elegida: Unificación en un único fichero vía spdlog**

Redirigir stdout al mismo destino que spdlog desde el inicio del proceso,
eliminando la dependencia del Makefile para el routing de logs:

```cpp
// En main.cpp, antes de cualquier output a stdout:
// 1. Inicializar spdlog con la ruta del JSON
// 2. Redirigir stdout/stderr al mismo sink
// 3. Eliminar el banner ASCII (o moverlo a spdlog level=debug)
```

Configuración resultante en JSON:
```json
"logging": {
  "level": "INFO",
  "file": "/vagrant/logs/lab/ml-detector.log",
  "stdout_redirect": true,
  "banner": false
}
```

El Makefile quedaría sin redirección explícita:
```makefile
./ml-detector  # sin >> fichero.log 2>&1
```

**Estándar de formato unificado para todos los componentes:**
```
[YYYY-MM-DD HH:MM:SS.mmm] [component-name] [level] message
```
- Idioma: **inglés** en todos los componentes
- Sin banners ASCII en producción
- Sin emojis en log estructurado (permitidos solo en nivel DEBUG)

---

## Consecuencias

### Positivas
- Un solo `grep` para diagnosticar cualquier problema del ml-detector
- Logs parseables por herramientas estándar (ELK, Grafana Loki)
- Consistencia con el formato ya usado en `etcd-server.log`
- Eliminación de dependencia Makefile → routing de logs

### Negativas / Riesgos
- Requiere modificación de `main.cpp` del ml-detector
- El banner de arranque tiene valor diagnóstico para confirmar versión —
  mover a nivel INFO estructurado, no eliminar

### No afectado
- CSV de eventos (`csv_writer`) — es pipeline de datos, no log operacional
- Configuración de `rag-ingester` que consume el CSV

---

## Deuda técnica relacionada

| Item | ADR | Estado |
|---|---|---|
| Hot-reload de configuración | ENT-4 | Pendiente post-paper |
| Estandarización idioma logs (ES→EN) | Este ADR | Pendiente post-paper |
| `log_file` en Makefile → JSON | Este ADR | Pendiente post-paper |
| `shard_count`/`flow_timeout_ns` en JSON | DEBT-P2 | Pendiente post-paper |

---

## Referencias

- `ml-detector/config/ml_detector_config.json` → sección `logging`
- `Makefile` → target `pipeline-start`, línea ml-detector
- DAY 81 — diagnóstico durante TAREA 3 (comparativa F1 limpia)
- ADR-004 — HMAC key rotation (patrón de configuración vía JSON)