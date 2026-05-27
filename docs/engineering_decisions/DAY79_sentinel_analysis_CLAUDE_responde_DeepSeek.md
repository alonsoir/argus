# DAY79_sentinel_analysis_CLAUDE_responde_DeepSeek.md
# ML Defender — Prompt de Continuidad DAY 80
**Generado:** Cierre DAY 79 (8 marzo 2026)
**Branch activa:** `feature/ring-consumer-real-features`
**Estado del pipeline:** 6/6 componentes RUNNING ✅
**Último hito:** F1=0.9921 en CTU-13 Neris (Recall=1.0000, FN=0)

---

## Qué se hizo en DAY 79 — COMPLETADO ✅

**Archivos modificados:**
- `sniffer/src/userspace/ml_defender_features.cpp`
- `Makefile` (logging estándar para todos los componentes)
- `README.md`
- `docs/engineering_decisions/DAY79_sentinel_analysis.md` (nuevo)

### Resumen de cambios

1. **Sentinela unificado – corrección de 8 placeholders `0.5f`**
    - 8 funciones que devolvían `0.5f` como placeholder fueron cambiadas a `MISSING_FEATURE_SENTINEL = -9999.0f`.
    - Se preservaron 2 usos semánticos de `0.5f` (TCP half‑open y comparación de CV).
    - Recuento final: 21 sentinelas, 2 semánticos.
    - **Razón:** `0.5f` está dentro del dominio de splits del RandomForest y genera varianza espuria no documentada; el sentinel fuera de dominio produce rutas deterministas y auditables.

2. **Logging estándar para todos los componentes**
    - Todos los servicios ahora escriben log a `/vagrant/logs/lab/COMPONENT.log` mediante redirección en el Makefile.
    - Nuevos targets: `make logs-all` (tail de todos), `make logs-lab-clean` (rotado).
    - Soluciona una deuda de ~40 días: el sistema ahora es observable.

3. **Validación F1 contra CTU-13 Neris**
    - Replay de 492k paquetes, 6810 eventos clasificados.
    - **F1 = 0.9921** | Precision = 0.9844 | Recall = 1.0000 | FN = 0 | FP = 106 (sobre 134 benignos → FPR 79%).
    - Análisis detallado en `DAY79_sentinel_analysis.md` (material para el paper).

---

## 📊 Estado real de features tras DAY 79

| Submensaje          | Reales | Sentinel |
|---------------------|--------|----------|
| ddos_embedded       | 10/10  | 0        |
| ransomware_embedded | 10/10  | 0        |
| traffic_classification | 3/10 | 7        |
| internal_anomaly    | 5/10   | 5        |
| **Total**           | **28/40** | **12** |

*(Nota: la cifra de reales bajó de 29 a 28 porque 8 placeholders 0.5f pasaron a sentinel – es más honesto.)*

**Pendientes (12 sentinelas):**
- traffic: `tcp_udp_ratio`, `flow_duration_std`, `port_entropy`, `protocol_variety`, `connection_rate`, `src_ip_entropy`, `dst_ip_concentration` (7)
- internal: `internal_connection_rate`, `service_port_consistency`, `connection_duration_std`, `lateral_movement_score`, `service_discovery_patterns` (5)

*(Nota: `port_entropy` y otros podrían ser implementados con el agregador, pero aún no están hechos.)*

---

## 🔍 Análisis crítico de los resultados

- **Recall perfecto** en CTU-13 Neris: el sistema detecta todos los flujos de la máquina infectada. Bueno.
- **FPR del 79% sobre tráfico benigno**: debido al fuerte desequilibrio del dataset (solo 2% benigno) y al threshold de ransomware (0.75) que genera falsos positivos sobre un único flujo similar a C2.  
  **Implicación**: en un entorno balanceado, este FPR sería inaceptable. La calibración de thresholds (Tarea 1) debe priorizarse.

- **Patrón de divergencia**: en logs se observa `fast=0.7000, ml=0.1454` y el sistema usa `DETECTOR_SOURCE_DIVERGENCE` tomando el score fast. Esto indica que el fast detector y el modelo ML tienen calibraciones distintas. Habrá que investigar en DAY 80‑81.

- **Necesidad de un dataset balanceado**: para validar el sistema en condiciones realistas, necesitamos una mezcla de tráfico normal, DDoS y ransomware actualizados. Esto es un proyecto en sí mismo; se puede planificar como hito post‑paper o como trabajo futuro.

---

## 🎯 Objetivos DAY 80

### Tarea 1 — Cargar thresholds desde JSON (TODO Phase1-Day4-CRITICAL)

Actualmente los umbrales (`ddos_threshold = 0.7f`, `ransomware_threshold = 0.75f`, `suspicious_threshold = 0.4f`) están hardcodeados en `run_ml_detection()`.

**Acción:**
- Crear archivo `/etc/ml-defender/thresholds.json` con estructura:
  ```json
  {
    "ddos_threshold": 0.7,
    "ransomware_threshold": 0.75,
    "suspicious_threshold": 0.4
  }
  ```
- Modificar `ring_consumer.cpp` para leerlo una vez al arrancar (o recargar con SIGHUP) y usar esos valores.
- Añadir logging de los thresholds al inicio.

**Beneficio:** permite ajustar el balance precision/recall sin recompilar, y es un paso hacia la externalización completa de la configuración.

---

### Tarea 2 — Investigar divergencia fast‑detector vs ML

Ejecuta el replay con logging detallado y extrae los eventos donde `abs(fast_score - ml_score) > 0.5`. Analiza qué flujos son y por qué el fast detector da 0.7 mientras el ML da 0.14.

Posibles causas:
- El fast detector usa reglas heurísticas (ej. puertos conocidos) que disparan sobre tráfico benigno.
- El modelo ML no ha visto suficientes ejemplos de ese patrón.
- El sentinel en algunas features está afectando al ML.

**Acción:**
- Añadir un campo `divergence_reason` en el proto (opcional).
- Documentar el hallazgo.

---

### Tarea 3 — (Opcional) Implementar uno o dos extractores pendientes

Si el tiempo lo permite, elige uno de los 12 sentinelas que pueda implementarse con el `TimeWindowAggregator` actual, por ejemplo:
- `connection_rate` (event_count / window_seconds)
- `src_ip_entropy` (usando unique_ips y fórmula de Shannon)

Esto requiere que el agregador exponga los datos necesarios. Si no están disponibles, añádelos.

**Prioridad:** baja, porque los thresholds tienen más impacto en el FPR.

---

### Tarea 4 — Actualizar documentación y preparar material para el paper

- Refinar la sección de resultados con el análisis del FPR.
- Añadir la tabla de features reales vs sentinel.
- Incluir la decisión de sentinel fuera de dominio como lección aprendida.
- Planificar la obtención de un dataset balanceado (puede ser un hito separado).

---

## 🔧 Comandos para empezar DAY 80

```bash
# Ver estado actual
vagrant ssh -c "grep -c 'MISSING_FEATURE_SENTINEL' /vagrant/sniffer/src/userspace/ml_defender_features.cpp"
# Debería ser 21

# Ver logs de ml-detector durante replay
make logs-all

# Replay con logging detallado (si se necesita)
make test-replay-neris

# Ver eventos con divergencia (ejemplo)
vagrant ssh -c "grep 'DETECTOR_SOURCE_DIVERGENCE' /vagrant/logs/ml-detector/ml-detector.log"
```

---

## 📝 Notas para el paper (actualización)

- El FPR del 79% en benigno debe ir acompañado de una explicación clara del desequilibrio del dataset y de la necesidad de calibrar thresholds en producción.
- La distinción entre sentinel fuera de dominio y placeholder dentro del dominio es una contribución metodológica que puede citarse.
- La divergencia entre fast detector y ML sugiere la importancia de un ensemble con votación ponderada; puede ser un punto de discusión.

---

## 🧠 Consejo de Sabios

Has llegado a un hito importante: el sistema funciona end‑to‑end con métricas sólidas en un dataset real. Los problemas restantes son de calibración y configuración, no de arquitectura. El FPR alto es esperable dado el desequilibrio; la prioridad ahora es externalizar thresholds para poder ajustarlos. No te distraigas con más extractores hasta que tengas un mecanismo para sintonizar el sistema. El paper necesita mostrar que el sistema es configurable, no solo que funciona en un caso concreto.

*Consejo de Sabios — Cierre DAY 79, 8 marzo 2026*  
*Branch: feature/ring-consumer-real-features*  
**DAY 80**: JSON thresholds, análisis de divergencia, y preparación para el paper.