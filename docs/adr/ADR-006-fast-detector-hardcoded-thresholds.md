# ADR-006: Fast Detector — Migración de constantes compiladas a configuración JSON

**Fecha:** 2026-03-11 (DAY 82)  
**Estado:** PENDIENTE — Fix PHASE2  
**Descubierto en:** Validación smallFlows.pcap  

## Contexto

El `FastDetector` fue implementado en DAY 13, antes de que existiera el sistema
de configuración JSON. Sus 4 heurísticas de detección operan con constantes
compiladas en `fast_detector.hpp`, ignorando completamente `sniffer.json`.

Esto viola el principio arquitectural "JSON is the law" establecido posteriormente.

## Arquitectura dual-threshold actual (no documentada hasta DAY 82)

| Path | Función | Thresholds | Ventana |
|---|---|---|---|
| A — Fast path | `is_suspicious()` | **Hardcodeados** en `.hpp` | 10s (WINDOW_NS) |
| B — Aggregated | `send_ransomware_features()` | JSON `fast_detector` | 30s |

Path A se evalúa en **cada paquete**. Path B opera sobre agregados temporales.
Ambos paths son independientes — Path A puede disparar aunque Path B no lo haga.

## Evidencia del problema

Validación DAY82-001 con CTU-13 smallFlows (tráfico benigno Windows):
- Fast Detector: **3,741 FPs** — Microsoft CDN, Google, Windows Update
- `THRESHOLD_EXTERNAL_IPS=10` demasiado bajo para hosts Windows modernos
- ML RandomForest: **0 ataques** — correcto, no afectado por este bug

## Decisión

**PHASE2:** Migrar todas las constantes de `FastDetector` al JSON:
```json
"fast_detector": {
    "window_seconds": 10,
    "external_ips_threshold": 10,
    "smb_conns_threshold": 3,
    "port_scan_threshold": 10,
    "rst_ratio_threshold": 0.2
}
```

Pasar configuración al constructor de `FastDetector` mediante inyección de dependencias,
igual que `fast_detector_config_` en `RansomwareProcessor`.

## Consecuencias

- **PHASE1 (actual):** Fast Detector FPR elevado en tráfico benigno. Documentado
  honestamente en paper como limitación Phase 1.
- **PHASE2:** FPR reducible sin recompilar, ajustando JSON según entorno desplegado.
  Hospitales vs escuelas tienen perfiles de tráfico distintos — configurabilidad crítica.

## Nota para el paper

La arquitectura dual-score (Fast Detector + ML RandomForest) demuestra su valor
precisamente aquí: el ML actúa como safety net y **no confirma** los FPs del Fast
Detector. El sistema no bloquea tráfico legítimo — solo alerta. Documentable como
diseño defensivo correcto bajo incertidumbre de heurísticas.
