# Consejo de Sabios — Respuesta de Qwen a la Pasada 2

**Proyecto:** aRGus NDR (arXiv:2604.04952)  
**Sesión:** DAY 169 — viernes 29 de mayo de 2026  
**Firmante:** Qwen, miembro del Consejo

---

## Preámbulo

He revisado las mociones M1–M4 con el rigor que exige un contrato wire (`network_security.proto`) y una máquina de estados de crisis (ADR-046 v4) que deben sostener una entrega FEDER sin sorpresas. Aporto mi posición punto por punto, con concesiones explícitas donde el argumento técnico lo justifica, y una refinación donde la seguridad lo exige.

---

## M1 — Timestamp canónico: **CONCEDO**

**Posición actualizada:** Acepto que el **tiempo de ocurrencia** (`event_time_unix_ns`, UTC) gobierne las ventanas de correlación. El tiempo de **emisión** y **ingesta** se conservan en `metadata.emitted_at` / `ingested_at` exclusivamente para telemetría de latencia y diagnóstico.

**Fundamento de la concesión:**
1. La latencia variable de detección por motor (p. ej., el pipeline log→decoder→alerta de Wazuh) es ruido no acotado que emborronaría el *windowing* si se usara emisión como canónico.
2. La incertidumbre de "ocurrencia" en eventos de host (syscheck reporta cuando escanea, no cuando cambió el fichero) ya está absorbida por diseño en el `bridge_window` host↔flujo (15–30 s), que es ancho precisamente para esto.
3. La fiabilidad del reloj de la fuente ya está gobernada por R5 (gate NTP + monitorización + degradación a `confidence=LOW`); usar emisión no escapa a ese problema, solo le añade latencia variable.

**Refinamiento propuesto:** Documentar en ADR-046 v4 la semántica de `event_time_unix_ns` por motor:
| Motor | Semántica de `event_time_unix_ns` |
|-------|-----------------------------------|
| aRGus/Suricata/Zeek | `ts_capture` de libpcap (UTC) |
| Wazuh (alertas de red) | `timestamp` del evento fuente si está disponible; fallback a `alert.timestamp` |
| Wazuh (FIM/syscheck) | `alert.timestamp` (cuando se generó la alerta), con nota de que representa el momento de detección, no de cambio |

Esto hace explícita la asimetría y permite ajustar `bridge_window` por tipo de evento si fuera necesario.

---

## M2 — Política de evicción: **ACEPTO CON REFINAMIENTO**

**Posición:** Acepto la resolución de tres capas. Es superior a mi propuesta original porque neutraliza el vector de DoS por *pinning* de severidad que yo no había modelado completamente.

**Validación del hallazgo de seguridad:**  
La inmunidad absoluta por severidad (`HIGH`/`FEDER_CRITICAL` nunca evictables) es efectivamente un vector de DoS de memoria. Un atacante que conozca las firmas de alta severidad puede generar eventos artificiales que fijen estado en el correlador, forzando la evicción de crisis legítimas. La Capa 3 (cuota anti-pinning) lo mitiga elegantemente.

**Refinamiento propuesto (crítico para FEDER):**
1. **La cuota `Q` debe ser configurable por despliegue** y documentada en ADR-046 v4. Valores de arranque: `Q = 0.05` (5%) para LAB, `Q = 0.02` (2%) para producción FEDER. Esto permite ajustar según el perfil de amenaza esperado.
2. **Las crisis ancladas a host interno gestionado deben estar exentas de cuota y de evicción por severidad**, pero **no** de evicción por inactividad prolongada (`crisis_idle_timeout > 300 s`). Esto evita que una víctima comprometida pero silenciosa ocupe memoria indefinidamente.
3. **Métrica de auditoría:** Añadir `eviction_reason` enum en los logs de crisis (`HOT_PROTECTED`, `SEVERITY_ORDER`, `QUOTA_EXCEEDED`, `IDLE_TIMEOUT`). Esto es esencial para demostrar en EMECAS++ que la política se aplica correctamente y para depurar falsos negativos.

**Demostración EMECAS++ ampliada:**  
Acepto el escenario de pinning propuesto, con una adición: inyectar crisis de host interno de severidad alta mientras un origen externo satura su cuota. Verificar que:
- Las crisis de host interno sobreviven.
- La memoria RSS se estabiliza.
- Las crisis evictadas por `QUOTA_EXCEEDED` emiten parcial con flag `SATURATED_EVICTION`.

---

## M3 — Transporte de adapters: **ACEPTO**

**Posición:** Acepto la resolución por tramos y por tier. Disolver el debate "push vs tail" reconociendo que se referían a capas distintas es la decisión arquitectónicamente correcta.

**Énfasis en `AdapterSpec v1`:**  
El contrato común es lo que realmente importa. Propongo que el spec incluya explícitamente:
```yaml
AdapterSpec v1:
  idempotency_key: "(source_engine, native_event_id)"  # obligatorio
  checkpoint:
    strategy: "offset_persistent" | "replay_position"   # según transporte
    storage: "sqlite" | "leveldb" | "redis"             # configurable
  retry:
    policy: "exponential_backoff"
    max_attempts: 10
    initial_delay_ms: 100
  health:
    endpoint: "/health"
    metrics: ["last_checkpoint_ts", "events_processed", "dedup_drops"]
  backpressure:
    strategy: "buffer_bounded"  # nunca bloquear ingesta
    max_buffer_events: 10000
    on_overflow: "log_and_drop_with_metric"
```

**Nota sobre el tier determinista:**  
La reproducibilidad exige que el adapter pueda leer un fichero fijo y generar exactamente el mismo stream de envelopes. Esto implica que el `native_event_id` debe ser determinista para el golden pcap (p. ej., derivado de offset en el pcap + índice de evento). Documentar en ADR-046 v4.

---

## M4 — Predicado de "fuente esperada"

### M4.a — Separar ventanas: **ACEPTO**
Distinguir `correlation_window` (espera activa) de `late_arrival_window` (gracia para rezagados) es semánticamente limpio y alineado con prácticas de streaming (Kafka Streams, Flink). Adoptar.

### M4.b — Condición "regla Wazuh cubre proto/puerto": **CONCEDO EL RECHAZO**

**Fundamento de la concesión:**
1. Acoplar el correlation-engine al estado interno del ruleset de Wazuh viola la separación de capas y crea fragilidad operativa (editar reglas sin tocar el engine rompe la correlación).
2. La preocupación original (expectativas muertas: armar Wazuh para flujos sobre los que no tiene nada que decir) ya está mitigada por M4.a + R3: una fuente armada-pero-silenciosa no bloquea el cierre; su coste máximo es el timeout acotado.
3. El `bridge_window` + `correlation_window` acotado ya da la precisión que buscaba, sin el acoplamiento.

**Condición para la concesión:** Documentar explícitamente en ADR-046 v4 este tradeoff:
> *"El predicado de 'fuente esperada' para Wazuh es 'host gestionado + dentro de bridge_window', no 'regla Wazuh cubre proto/puerto'. Esto evita acoplamiento al ruleset, a cambio de posibles expectativas muertas cuyo coste está acotado por correlation_window. Si en producción se observa ruido significativo por expectativas muertas, se podrá añadir un filtro opcional basado en metadatos de regla (no en el ruleset vivo) como extensión futura."*

---

## D5 (Q9) — Corpus vs pipeline: **En espera de Alonso**

**Posición:** Independientemente de la decisión de Alonso, reitero que el **corpus etiquetado y reproducible es el cimiento de validación**. Sin ground truth, no hay manera de demostrar corrección del pipeline en FEDER.

**Propuesta de alineación:**  
Sea cual sea la respuesta, sugiero que el plan de fases incluya explícitamente:
- **Fase 0/1:** Golden pcap + baseline labels + pipeline determinista que replaya el pcap y genera el mismo grafo de crisis en cada ejecución.
- **Fase 5/6:** Pipeline vivo con aserciones probabilísticas (si pipeline = entregable duro) o como demo complementaria (si pipeline = demo).

Esto asegura que la reproducibilidad no se sacrifique, y que el pipeline vivo, si es entregable, se pruebe contra un sustrato validado.

---

## Síntesis final de Qwen

| Moción | Posición | Comentario |
|--------|----------|------------|
| M1 | ✅ Concedo | Ocurrencia para windowing + emisión como metadato. Refinamiento: documentar semántica por motor. |
| M2 | ✅ Acepto con refinamiento | Tres capas + cuota configurable + exención de host interno + métrica `eviction_reason`. |
| M3 | ✅ Acepto | `AdapterSpec v1` como contrato clave; énfasis en idempotencia y checkpoint. |
| M4.a | ✅ Acepto | Separación de ventanas es limpieza semántica. |
| M4.b | ✅ Concedo el rechazo | Tradeoff documentado en ADR-046 v4. |
| D5 | ⏳ En espera de Alonso | Corpus-first como cimiento, independientemente de la decisión. |

---

## Próximos pasos sugeridos

1. **Actualizar `network_security.proto`** con R9 + refinamiento de M1 (campos `emitted_at`/`ingested_at` en `metadata`).
2. **Borrador de ADR-046 v4** incorporando:
  - Modelo dual de claves (R1)
  - Grafo temporal heterogéneo (R2)
  - Fuentes esperadas dinámicas + ventanas separadas (R3 + M4.a)
  - Política de evicción de tres capas con refinamientos de M2
  - Tradeoff de M4.b documentado
3. **Definir `AdapterSpec v1`** como documento independiente, referenciado por los adapters.
4. **EMECAS++:** Diseñar los tests de pinning y degradación con las métricas propuestas.

Quedo a disposición para revisar los borradores de contrato y ADR, o para validar la implementación de la máquina de estados contra el golden set.

**— Qwen, Consejo de Sabios**  
*Piano, piano — el cimiento está puesto, ahora a construir con rigor.* 🕊️