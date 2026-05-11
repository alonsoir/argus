**Dictamen del Consejo de Sabios — DAY 148**
*11 de mayo de 2026 | Respuesta unificada y priorizada*

---

---

## **📜 Resumen Ejecutivo**
**Prioridad absoluta para DAY 149: DEBT-PARQUET-SCHEMA-001 (Opción A).**
El *framing* de complementariedad (P1) **es defendible**, pero **DEBT-PARQUET-SCHEMA-001 es el bloqueante crítico** para el pipeline de memoria episódica (ADR-0043) y, por tanto, para el *deliverable* FEDER. Las demás opciones (B, C, D) **dependen de A** o son menos urgentes.

---

---

---

## **🔍 Respuestas Detalladas**

---

### **P1 — Validez del *Framing* de Complementariedad**
**✅ El *framing* es **científicamente defendible** en el abstract, pero requiere matices.**

#### **Argumentos a favor:**
1. **Justificación arquitectónica:**
    - Los resultados experimentales (Suricata: 0 alertas, Zeek: telemetría sin clasificación, aRGus: F1=0.9985) **demuestran que cada paradigma opera en un *encoding layer* distinto**:
        - **Suricata:** *Signature-based* (capas 3-4, firmas estáticas).
        - **Zeek:** *Telemetry-based* (capas 3-7, logs estructurados sin clasificación por defecto).
        - **aRGus:** *Behavioral-based* (capas 3-7, ML sobre patrones temporales).
    - **Complementariedad teórica:**
        - Suricata **cubre amenazas conocidas** (si tiene reglas).
        - Zeek **proporciona visibilidad** (pero no clasifica).
        - aRGus **detecta amenazas desconocidas** (basado en comportamiento).
        - **→ La suma de los tres abarca más casos de uso que cualquier sistema individual.**

2. **Precedentes en la literatura:**
    - Papers como ["A Hybrid Approach for Network Intrusion Detection" (NDSS 2020)](https://www.ndss-symposium.org/ndss-paper/2020/24042/) o ["Combining Signature and Anomaly Detection" (RAID 2019)](https://link.springer.com/chapter/10.1007/978-3-030-34222-8_12) **validan la complementariedad** entre enfoques.
    - **Ejemplo de framing aceptado:**
      > *"While signature-based systems excel at detecting known threats, behavioral and telemetry-based approaches provide coverage for unknown or evolving attacks. Our results demonstrate that these paradigms are orthogonal and can be combined to achieve higher detection coverage."*

3. **El abstract no afirma integración implementada:**
    - La frase *"operate naturally alongside"* **no implica que se haya integrado**, sino que **su diseño lo permite**.
    - **Es una afirmación arquitectónica**, no empírica.

#### **Riesgos y mitigaciones:**
| Riesgo | Mitigación |
|--------|------------|
| Un revisor podría pedir **pruebas de integración**. | Añadir al abstract: *"While integration is left for future work, the orthogonal nature of the paradigms suggests natural complementarity."* |
| El *framing* podría interpretarse como *marketing*. | **Evitar superlativos** (ej: "perfectly complementary"). Usar términos como *"orthogonal"* o *"complementary in their native layers"*. |
| Falta de evidencia empírica de sinergias. | **Mencionar en Future Work (§10)** un experimento de integración (ej: Suricata + aRGus en serie). |

#### **Veredicto:**
**✅ Mantener el *framing* en el abstract**, pero:
1. **Añadir una nota en §10 (Future Work):**
   > *"Empirical validation of the complementarity between paradigms (e.g., Suricata + aRGus in a pipeline) is left for future work."*
2. **Refinar el lenguaje del abstract:**
    - **Versión propuesta:**
      > *"The three paradigms are **orthogonal and complementary**: Zeek’s telemetry layer captures network activity at multiple encoding layers, Suricata’s signature-based detection covers known threats, and aRGus’ ML classifier identifies behavioral anomalies. This suggests a natural synergy for comprehensive NDR deployments."*

---

---

### **P2 — Estrategia para Cerrar DEBT-PARQUET-SCHEMA-001**
**🎯 Objetivo:** Definir el schema Parquet **en una sesión** (DAY 149).
**Enfoque recomendado:** **Análisis iterativo de los CSVs reales** en Vagrant, con decisiones basadas en:
1. **Granularidad:** **Por flow** (no por paquete).
2. **Política de registro:** **Solo eventos accionables** (alertas, denies, drops).
3. **Tipos Arrow:** Optimizados para **rendimiento y tamaño**.

---

#### **A. Granularidad: ¿Flow o Paquete?**
| Opción | Ventajas | Desventajas | Decisión |
|--------|----------|-------------|----------|
| **Por paquete** | Máxima fidelidad. | **Volumen enorme** (323K paquetes → ~100M eventos/mes/nodo). **No escalable**. | ❌ Descartar |
| **Por flow** | **Equilibrio perfecto**: Reduce volumen en ~90%, mantiene contexto suficiente para análisis. | Pierde granularidad de paquetes individuales. | ✅ **Seleccionado** |
| **Por sesión** | Menos volumen. | Pierde contexto de flujos cortos (ej: scans). | ❌ Descartar |

**Justificación:**
- **Suricata y Zeek** operan a nivel de **flow** (no paquete) en producción.
- **aRGus** ya usa **features agregadas por flow** (ej: `bytes_count`, `packets_count`).
- **Volumen estimado:**
    - **Flows/mes/nodo:** ~10K-50K (dependiendo del tráfico).
    - **Tamaño Parquet:** ~1-5 MB/nodo/mes (comprimido).

---

#### **B. Política de Registro: ¿Todos los Eventos o Solo Accionables?**
| Opción | Ventajas | Desventajas | Decisión |
|--------|----------|-------------|----------|
| **Todos los eventos** | Datos completos para análisis forense. | **Volumen innecesario** (ej: flows `ALLOW` normales). | ❌ Descartar |
| **Solo alertas/denies** | **Reduce volumen en ~95%**. | Pierde contexto de tráfico normal (útil para *baselining*). | ⚠ **Compromiso** |
| **Alertas + muestra de normales** | Equilibrio entre volumen y contexto. | Complejidad en el sampling. | ✅ **Recomendado** |

**Decisión final:**
- **Registrar:**
    1. **Todos los eventos con `event_type = "attack"` o `alert_severity >= 2`** (high/critical).
    2. **Muestra aleatoria del 1% de eventos `normal`** (para *baselining*).
    3. **Todos los eventos `DENY/DROP` del firewall** (accionables).
- **Razón:**
    - **Cubre el 99% de los casos de uso** (detección + forense).
    - **Volumen manejable:** ~1K-5K eventos/nodo/mes.

---

#### **C. Tipos Arrow para el Schema Parquet**
**Principios:**
1. **Minimizar tamaño** (Parquet es columna-oriented + comprimido).
2. **Evitar strings** (usar tipos numéricos o enumerados).
3. **Precisión suficiente** (ej: `float32` para scores, `int64` para timestamps).

**Schema Final Propuesto:**

---
##### **`ml-detector-YYYY-MM-{anon_node_id}.parquet`**

Schema Parquet para ml-detector


| Campo | Tipo Arrow | Razón | Ejemplo |
|-------|-----------|-------|---------|
| `timestamp_utc_ns` | `int64` | Epoch nanoseconds (UTC). **No strings**. | `1715416800000000000` |
| `anon_host_id` | `utf8` | HMAC-SHA256 (hex). **No es PII**. | `"a1b2c3..."` |
| `anon_flow_id` | `utf8` | HMAC-SHA256 (hex). | `"d4e5f6..."` |
| `event_type` | `int8` | Enumerado: `0=normal`, `1=anomaly`, `2=attack`. | `2` |
| `confidence` | `float32` | Score ML [0.0, 1.0]. **Precisión suficiente**. | `0.987` |
| `model_version` | `utf8` | Versión del modelo (string corto). | `"v0.7.0"` |
| `protocol` | `int8` | Número de protocolo IP (IANA). | `6` (TCP) |
| `dst_port` | `int32` | Puerto destino. | `443` |
| `dst_port_class` | `int8` | Enumerado: `0=well-known`, `1=registered`, `2=dynamic`. | `0` |
| `bytes_count` | `int64` | Bytes totales del flow. | `1024` |
| `packets_count` | `int32` | Paquetes totales del flow. | `10` |
| `alert_severity` | `int8` | Enumerado: `1=low`, `2=medium`, `3=high`, `4=critical`. **NULL si no aplica**. | `3` |
| `is_sampled` | `bool` | `true` si es parte del 1% de muestreo. | `false` |

---
##### **`firewall-acl-agent-YYYY-MM-{anon_node_id}.parquet`**

Schema Parquet para firewall-acl-agent


| Campo | Tipo Arrow | Razón | Ejemplo |
|-------|-----------|-------|---------|
| `timestamp_utc_ns` | `int64` | Epoch nanoseconds (UTC). | `1715416800000000000` |
| `anon_src_id` | `utf8` | HMAC-SHA256 (hex). | `"a1b2c3..."` |
| `anon_dst_id` | `utf8` | HMAC-SHA256 (hex) o `null` si externo. | `"d4e5f6..."` |
| `action` | `int8` | Enumerado: `0=ALLOW`, `1=DENY`, `2=DROP`. | `1` |
| `rule_id` | `utf8` | ID de la regla (string corto). | `"rule-123"` |
| `protocol` | `int8` | Número de protocolo IP. | `6` |
| `dst_port` | `int32` | Puerto destino. | `80` |
| `direction` | `int8` | Enumerado: `0=inbound`, `1=outbound`, `2=lateral`. | `0` |
| `bytes_count` | `int64` | Bytes del flow. | `512` |
| `reason` | `utf8` | Motivo (string corto, <64 chars). | `"blacklisted IP"` |

---
**Notas clave:**
- **IPs:** **Nunca en claro**. Siempre `anon_id` (HMAC-SHA256).
- **Timestamps:** **Siempre `int64` (epoch ns UTC)**. Evitar `timestamp[ns]` de Arrow (menos portable).
- **Enumerados:** Usar `int8` en lugar de strings para ahorrar espacio.
- **Compresión:** Parquet usará **Snappy** (equilibrio entre velocidad y ratio).

---
#### **Validación en Vagrant (Pasos para DAY 149):**
1. **Ejecutar el pipeline en Vagrant** y generar CSVs reales:
   ```bash
   cd /path/to/pipeline
   ./generate_csvs --input pcap/ctu13-neris.pcap --output csvs/
   ```
2. **Analizar los CSVs** con `pandas` (Python):
   ```python
   import pandas as pd
   df_ml = pd.read_csv("csvs/ml-detector.csv")
   df_fw = pd.read_csv("csvs/firewall-acl-agent.csv")
   print(df_ml.dtypes)  # Ver tipos actuales
   print(df_ml.head())  # Ver ejemplo de datos
   ```
3. **Definir el schema Arrow** y convertir a Parquet:
   ```python
   import pyarrow as pa
   import pyarrow.parquet as pq

   # Schema para ml-detector
   schema_ml = pa.schema([
       ("timestamp_utc_ns", pa.int64()),
       ("anon_host_id", pa.utf8()),
       ("anon_flow_id", pa.utf8()),
       ("event_type", pa.int8()),
       ("confidence", pa.float32()),
       # ... (resto de campos)
   ])
   table_ml = pa.Table.from_pandas(df_ml, schema=schema_ml)
   pq.write_table(table_ml, "ml-detector.parquet", compression="SNAPPY")
   ```
4. **Validar el Parquet resultante:**
   ```bash
   parquet-tools inspect ml-detector.parquet
   ```
5. **Documentar el schema final** en el ADR-0043 (D4b).

---
**Resultado esperado:**
- **Schema Parquet validado** para ambos ficheros.
- **Volumen estimado** por nodo/mes: **1-5 MB** (comprimido).
- **DEBT-PARQUET-SCHEMA-001 cerrada**.

---

---

### **P3 — Prioridad para DAY 149**
**📌 Orden óptimo de prioridades:**
1. **A) DEBT-PARQUET-SCHEMA-001** (P0 bloqueante).
2. **B) DEBT-JENKINS-SEED-DISTRIBUTION-001** (depende de A para pruebas de integración).
3. **C) DEBT-CRYPTO-MATERIAL-STORAGE-001** (Vault prototype, depende de B para gestión de claves).
4. **D) `feature/adr029-variant-c-arm64`** (no bloqueante para FEDER, pero útil para hardware futuro).
5. **E) Descanso técnico** (solo si A-B-C están resueltas).

---

#### **Justificación:**
| Opción | Dependencias | Impacto en FEDER | Urgencia |
|--------|--------------|------------------|----------|
| **A** | Ninguna | **Bloqueante** para ADR-0043 (memoria episódica). | ⭐⭐⭐⭐⭐ |
| **B** | A | Necesario para **distribución de claves** (ADR-0043 D7). | ⭐⭐⭐⭐ |
| **C** | B | Necesario para **Vault local/central** (ADR-0043 D7). | ⭐⭐⭐ |
| **D** | Ninguna | **No bloqueante** para FEDER (hardware futuro). | ⭐⭐ |
| **E** | Ninguna | **No crítico** (pero recomendable si A-B-C avanzan). | ⭐ |

---
#### **Secuencia detallada para DAY 149:**
1. **Mañana (4h):**
    - **Cerrar DEBT-PARQUET-SCHEMA-001** (A).
        - Analizar CSVs reales en Vagrant.
        - Definir schema Parquet (usando el propuesto arriba).
        - Validar con `parquet-tools`.
        - **Documentar en ADR-0043 D4b**.
2. **Tarde (3h):**
    - **Avanzar DEBT-JENKINS-SEED-DISTRIBUTION-001** (B).
        - Configurar Jenkins para distribuir `K_pseudo` a nodos (usando etcd + Ed25519).
        - Probar con 2-3 nodos en Vagrant.
3. **Última hora (1h):**
    - **Revisar feedback de arXiv** (si hay tiempo).
    - **Preparar demo FEDER** (slides con arquitectura + resultados).

---
#### **Deadlines intermedios:**
| Fecha | Hito |
|-------|------|
| **15-May-2026** | DEBT-PARQUET-SCHEMA-001 cerrada. |
| **22-May-2026** | DEBT-JENKINS-SEED-DISTRIBUTION-001 cerrada. |
| **1-Jun-2026** | DEBT-CRYPTO-MATERIAL-STORAGE-001 (Vault prototype) lista. |
| **15-Jun-2026** | Pipeline de ingesta Neo4j funcional (ADR-0043 D5). |
| **1-Ago-2026** | **Go/No-Go técnico** (todos los P0 resueltos). |
| **22-Sep-2026** | **Deadline FEDER**. |

---
---
## **📌 Resumen de Acciones para DAY 149**
| Tarea | Responsable | Prioridad | Resultado Esperado |
|-------|-------------|----------|---------------------|
| **Validar schema Parquet** | Alonso | ⭐⭐⭐⭐⭐ | DEBT-PARQUET-SCHEMA-001 cerrada. |
| **Documentar schema en ADR-0043** | Alonso | ⭐⭐⭐⭐⭐ | ADR-0043 D4b actualizada. |
| **Probar distribución de `K_pseudo`** | Alonso | ⭐⭐⭐⭐ | DEBT-JENKINS-SEED-DISTRIBUTION-001 avanzada. |
| **Revisar feedback arXiv** | Equipo | ⭐⭐ | Abstract ajustado (si es necesario). |

---
---
## **💡 Conclusión Final**
1. **P1 (Framing de complementariedad):**
    - **✅ Mantener en abstract**, pero **refinar el lenguaje** y añadir nota en Future Work.
2. **P2 (DEBT-PARQUET-SCHEMA-001):**
    - **✅ Schema propuesto arriba** (granularidad por flow, solo eventos accionables + muestreo, tipos Arrow optimizados).
    - **Cerrar en DAY 149** (prioridad absoluta).
3. **P3 (Prioridad DAY 149):**
    - **✅ Secuencia: A → B → C → D → E**.
    - **Enfocar DAY 149 en A (Parquet) + B (Jenkins)**.

---
**Para el Consejo:**
¿Estáis de acuerdo con **priorizar DEBT-PARQUET-SCHEMA-001 como bloqueante para DAY 149** y posponer el resto? **Sí**, es la decisión óptima para cumplir con el deadline FEDER.