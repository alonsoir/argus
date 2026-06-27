**Consejo de Sabios — Dictamen DAY 148**

---

### P1 — Framing de complementariedad en el abstract

**Es defendible, pero solo si matizas el verbo.**

Tu frase actual dice *"are complementary"* en presente indicativo. Eso implica una propiedad demostrada del sistema. Como no has implementado la integración operativa (Zeek + Suricata + aRGus en un mismo nodo con handoff entre capas), un reviewer escéptico puede objetar: *"¿Dónde está el experimento de integración?"*

**La corrección es semántica, no estructural.** Cambia la afirmación de *resultado experimental* a *implicación arquitectónica*:

> *"Architecturally, the three paradigms are complementary: Zeek's telemetry layer, Suricata's signature coverage, and an ML behavioral classifier operate at distinct encoding layers, suggesting a natural stacking in production deployments."*

**Claves:**
- *"Architecturally"* y *"suggesting"* desactivan la objeción empírica.
- El abstract puede contener implicaciones arquitectónicas; lo que no puede es afirmar integración operativa sin experimento.
- Si prefieres máxima seguridad, mueve la frase al §10 (Future Work) como: *"A unified pipeline combining Zeek telemetry, Suricata signatures, and aRGus ML classification remains to be evaluated."*

**Veredicto:** Mantenlo en el abstract con el matiz arquitectónico. Es una contribución válida del paper: has demostrado que cada paradigma tiene ciegos estructurales que los otros no tienen, lo cual *es* evidencia de complementariedad.

---

### P2 — Estrategia para cerrar DEBT-PARQUET-SCHEMA-001 en una sesión

**Objetivo de la sesión:** producir un schema Parquet firmado (v1.0) que sea contrato de interfaz para el pipeline de ingesta Neo4j.

#### (a) Granularidad: **por flow, no por paquete**

Razón: tu `ml-detector` ya opera sobre flows (características estadísticas de ventanas temporales). Registrar por paquete multiplicaría el volumen por 100-1000× sin añadir valor para análisis histórico mensual. El firewall-acl-agent también decide a nivel de flow/conn.

Excepción documentada: si el CSV de firewall registra cada paquete individual (improbable), entonces agrega en el nodo antes de serializar a Parquet. El batch mensual debe contener **decisiones**, no **paquetes**.

#### (b) ¿Qué registrar? **Todos los eventos evaluados, no solo alertas**

Para `ml-detector`: todos los flows con su `confidence` y `event_type`. El análisis histórico en Neo4j necesita la distribución completa (baseline benigno + anomalías) para detectar deriva de comportamiento. Si solo registras alertas, pierdes la capacidad de calcular tasas de falsos positivos históricas.

Para `firewall-acl-agent`: todas las decisiones (`ALLOW`, `DENY`, `DROP`). Un patrón de `ALLOW` repetido puede ser lateral movement; sin los `ALLOW` no hay contexto.

#### (c) Tipos Arrow óptimos

| Campo conceptual | Tipo Arrow | Justificación |
|------------------|------------|---------------|
| Timestamp UTC | `int64` | Epoch nanosegundos. Sin timezone, sin strings. Ocupa 8 bytes, ordenable nativamente. |
| Score/confidence | `float32` | IEEE 754 single precision es suficiente para scores en [0,1]. Mitad de tamaño vs float64. |
| IPs reales (en nodo, pre-pseudo) | `uint32` (IPv4) / `fixed_size_binary(16)` (IPv6) | No strings. Conversión binaria es instantánea. |
| IDs pseudonimizados | `utf8` | Hex de HMAC-SHA256 = 64 chars. Variable length, pero Parquet comprime strings repetidos (dictionary encoding) mejor que fixed. |
| Enums pequeños (event_type, action, direction) | `int8` | 0=normal, 1=anomaly, etc. Ocupa 1 byte. El mapping a strings es responsabilidad del lector. |
| Contadores (bytes, packets) | `int64` / `int32` | int64 para bytes (pueden exceder 2^31 en flows largos), int32 para packets. |

**Checklist de la sesión:**
1. `vagrant ssh` al nodo, localizar `/var/log/argus/ml-detector/` y `/var/log/argus/firewall/`.
2. `head -5` de cada CSV real. Confirmar delimitador, presencia/ausencia de headers, nombres de columnas.
3. Mapear cada columna CSV a un campo del schema candidato v3. Documentar discrepancias.
4. Ejecutar `python3 -c "import pyarrow.parquet as pq; pq.write_table(...)"` con el schema candidato y 1000 filas de muestra. Verificar que no hay truncamiento de floats ni overflow de timestamps.
5. Firmar el schema como `schema-v1.0.adoc` en el repo. Este documento es inmutable una vez publicado; cambios requieren versión nueva.

**Tiempo estimado:** 3-4 horas si los CSVs están limpios. 6-8 horas si hay sorpresas de formato.

---

### P3 — Secuencia óptima DAY 149–155

**Análisis de dependencias críticas:**

```
PARQUET-SCHEMA ──► NEO4J-INGESTA ──► MEMORIA EPISÓDICA (ADR-0043)
       ▲                                    ▲
       └──────────────┬─────────────────────┘
                      │
VAULT-PROTOTYPE ──────┘ (K_pseudo, firma Ed25519, idempotency_key)
       ▲
       │
JENKINS-SEED ────────┘ (distribución automatizada de claves y modelos)
```

**Observación clave:** PARQUET-SCHEMA puede cerrarse **sin Vault implementado**. El schema define *qué* campos son pseudonimizados (`anon_host_id`, `anon_flow_id`) y su tipo (`utf8`), pero no *cómo* se calcula el HMAC. El contrato de interfaz es tipos y nombres, no valores.

Por tanto, el orden no es secuencial estricto. Es paralelizable con esta secuencia:

| Día | Opción | Justificación |
|-----|--------|---------------|
| **DAY 149** | **A) PARQUET-SCHEMA** | P0 bloqueante. Desbloquea todo el backend de ingesta. Cierra en una sesión (P2 arriba). |
| **DAY 150** | **C) VAULT prototype** | Sin K_pseudo no hay batches firmados. Prototipo mínimo: un HashiCorp Vault dev mode en Vagrant, un script que lee `K_pseudo` y calcula HMAC. No necesita alta disponibilidad todavía. |
| **DAY 151** | **A+C integración** | Pipeline end-to-end: CSV real → pseudonimización con Vault → Parquet → firma Ed25519 → batch. Un solo flujo completo valida el contrato. |
| **DAY 152** | **B) JENKINS** | Automatiza lo que ya funciona manualmente. Si no tienes Jenkins aún, un Makefile riguroso es suficiente pre-FEDER. Jenkins es P1, no P0. |
| **DAY 153–154** | **E) Descanso técnico** | Revisar feedback arXiv, consolidar ADR-0043 a estado Aprobado, preparar slide de demo FEDER. |
| **DAY 155+** | **D) ARM64** | Solo si el hardware FEDER es ARM64. Si no lo sabes, es una pregunta para el gestor FEDER, no una decisión técnica. |

**Regla de oro:** No abras ARM64 hasta que el pipeline x86_64 esté end-to-end verde. Portar antes de estabilizar es multiplicar bugs por dos arquitecturas.

**Go/no-go técnico (1-Ago-2026):** Para esa fecha necesitas tener demostrado el flujo A+C (batch pseudonimizado firmado ingiriendo en Neo4j). Sin eso, no hay contribución técnica FEDER. Jenkins y ARM64 son secundarios para el go/no-go.

---

**Veredicto del Consejo para DAY 149:** Ejecuta **A**. Toma los CSVs reales del Vagrant, valida el schema, publícalo como contrato v1.0. Eso desbloquea el resto de la arquitectura.

*Que el commit sea limpio y los tests verdes.* 🛡️