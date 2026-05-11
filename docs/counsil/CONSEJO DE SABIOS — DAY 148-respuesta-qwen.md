**CONSEJO DE SABIOS — RESPUESTAS TÉCNICAS — DAY 148**
*Respuestas concisas, fundamentadas en metodología de investigación, ingeniería de datos y gestión de proyectos FEDER.*

---

### **P1 — Validez del framing de complementariedad en abstract v23**

**Veredicto**: ✅ **Defendible y estratégico**, con una precisión léxica menor.

**Argumentación**:
| Aspecto | Evaluación |
|---------|-----------|
| **Nivel de afirmación** | El abstract describe *arquitectura conceptual*, no integración implementada. Es válido afirmar complementariedad teórica si los resultados experimentales muestran que cada paradigma opera en una capa distinta del espacio de detección. |
| **Evidencia de soporte** | Los resultados de §8.13 (Suricata 0 alertas, Zeek 14 TP, aRGus 646 TP) demuestran empíricamente que los tres sistemas *no se solapan* en cobertura. Eso es evidencia indirecta de complementariedad. |
| **Riesgo de revisión** | Un revisor podría objetar "complementariedad no demostrada". Mitigación: añadir *"in principle"* o *"architecturally"* para calibrar la afirmación. |

**Recomendación de redacción** (mínimo cambio, máximo blindaje):
```latex
% Abstract v23.1:
"The three paradigms are \emph{architecturally complementary}: Zeek's telemetry layer and Suricata's signature coverage operate at distinct encoding layers from behavioral ML classification, suggesting natural integration pathways for hybrid NDR systems."
```

**Conclusión**: Mantener en abstract. Mover la *demostración de integración* a Future Work (§10). El framing actual es una contribución conceptual válida.

---

### **P2 — Estrategia óptima para cerrar DEBT-PARQUET-SCHEMA-001**

**Objetivo**: Validar schema Parquet en una sesión (<4h). Priorizar *contract-first*: el schema es la interfaz edge→central; todo lo demás depende de él.

#### **(a) Granularidad: por FLOW, no por paquete**
```yaml
# Justificación técnica:
- ml-detector y firewall-acl-agent operan a nivel de flow (5-tuple + ventana temporal)
- CTU-13 está etiquetado a nivel de flow bidireccional
- Neo4j modela entidades y relaciones, no paquetes individuales
- Volumen: ~12K flujos/mes/nodo vs ~300K paquetes → Parquet 25× más compacto
```

#### **(b) Política de registro: TODOS los eventos, con flag de relevancia**
```yaml
# Schema incluye campo "relevance_flag":
relevance_flag: utf8  # "all", "alert_only", "deny_only", "anomaly_only"

# Por defecto en producción: registrar todo, filtrar en ingesta Neo4j
# Beneficio: flexibilidad analítica futura sin re-ingesta
```

#### **(c) Tipos Arrow recomendados**
| Campo | Tipo Arrow | Justificación |
|-------|-----------|--------------|
| `timestamp_utc_ns` | `int64` | Epoch nanoseconds: ordenable, sin ambigüedad TZ, eficiente en columnar |
| `confidence` / `threat_score` | `float32` | IEEE 754 single-precision suficiente para scores [0,1]; 2× más compacto que float64 |
| `anon_host_id`, `anon_flow_id` | `utf8` (dictionary-encoded) | HMAC hex strings; dictionary encoding reduce 70-90% espacio en columnas de baja cardinalidad |
| `protocol` | `uint8` | Rango 0-255 suficiente para IP protocol numbers |
| `dst_port_class` | `utf8` (dictionary) | 3-4 valores únicos → dictionary ideal |
| `alert_severity`, `action` | `int8` o `dictionary(utf8)` | Cardinalidad baja; int8 si se prioriza velocidad de comparación numérica |

**Script de validación en una sesión**:
```bash
# 1. Extraer muestra representativa de CSVs en Vagrant
vagrant ssh suricata -c "head -1000 /var/log/aRGus/ml-detector.csv > /tmp/sample_ml.csv"

# 2. Generar schema candidato con pyarrow
python3 << 'EOF'
import pyarrow as pa, pyarrow.parquet as pq, csv, sys

# Definir schema candidato (ver arriba)
schema = pa.schema([
    ('timestamp_utc_ns', pa.int64()),
    ('anon_host_id', pa.string()),  # + dictionary encoding en writer
    ('anon_flow_id', pa.string()),
    ('event_type', pa.dictionary(pa.int8(), pa.string())),
    ('confidence', pa.float32()),
    # ... resto de campos
])

# Validar que CSV sampleado mapea sin pérdida
# (implementar conversor CSV→Arrow con casting seguro)
EOF

# 3. Escribir Parquet de prueba y verificar tamaño/compresión
# 4. Commit schema final en repo: schemas/parquet/ml-detector-v1.arrow
```

**Criterio de cierre**: El schema permite serializar/deserializar 1000 filas de CSV real sin pérdida de precisión, sin errores de casting, y con tamaño Parquet <30% del CSV original.

---

### **P3 — Priorización DAY 149: secuencia óptima pre-FEDER**

**Contexto temporal**:
- **Go/No-Go técnico**: 1-Ago-2026 (~7 semanas)
- **Deadline FEDER**: 22-Sep-2026 (~19 semanas)
- **Estado actual**: Paper en arXiv ✅, código en verde ✅, ADR-0043 aprobado ✅

#### **Matriz de dependencia crítica**:
```
DEBT-PARQUET-SCHEMA-001 (A)
       ↓
Pipeline ingesta Neo4j (ADR-0043 paso 5)
       ↓
Demostración federación funcional (requisito FEDER)
       ↓
Go/No-Go 1-Ago-2026
```

#### **Secuencia recomendada**:
| Día | Opción | Justificación |
|-----|--------|--------------|
| **DAY 149** | **A) DEBT-PARQUET-SCHEMA-001** | 🔴 **Bloqueante crítico**. Sin schema no hay interfaz, no hay ingesta, no hay demo FEDER. Cerrar hoy libera el camino para todo lo demás. |
| **DAY 150-152** | **C) DEBT-CRYPTO-MATERIAL-STORAGE-001** | 🟡 **Pre-requisito de seguridad**. Vault prototype es necesario antes de distribuir `K_pseudo` en entorno federado. Paralelizable con ingesta Neo4j una vez cerrado A. |
| **DAY 153-155** | **B) DEBT-JENKINS-SEED-DISTRIBUTION-001** | 🟢 **Habilitador de CI/CD**. Necesario para automatizar despliegues FEDER, pero puede esperar a tener schema y crypto definidos. |
| **DAY 156+** | **D) feature/adr029-variant-c-arm64** | 🔵 **Scope expansion**. Solo si A+B+C están verdes y hay margen temporal. ARM64 es valor añadido, no requisito FEDER base. |
| **Buffer** | **E) Descanso técnico** | Insertar ½ día cada 10 días de desarrollo intenso para evitar burnout y consolidar feedback arXiv. |

#### **Dependencia oculta que cambia el orden**:
Si **DEBT-LEGAL-DATA-RETENTION-001** (dictamen GDPR) se retrasa, podría bloquear la ingesta de datos pseudonimizados en Neo4j. **Recomendación**: Contactar al Dr. Andrés Caro Lindo (UEx/INCIBE) **esta semana** para iniciar el dictamen en paralelo con el trabajo técnico. No es bloqueante para schema Parquet, pero sí para despliegue productivo.

---

## 🎯 RESUMEN EJECUTIVO

```yaml
P1_abstract: 
  status: "APROBADO con precisión léxica menor"
  action: "Añadir 'architecturally' o 'in principle' para blindaje"

P2_parquet_schema:
  status: "ESTRATEGIA DEFINIDA"
  granularity: "flow (5-tuple + ventana)"
  policy: "todos los eventos + relevance_flag"
  arrow_types: "int64 timestamp, float32 scores, dictionary(utf8) para low-cardinality"
  closure_criterion: "1000 filas CSV→Parquet sin pérdida, <30% tamaño original"

P3_prioritization:
  sequence: "A → C → B → (D opcional) + E buffer"
  critical_path: "Schema Parquet → Ingesta Neo4j → Demo federación → Go/No-Go 1-Ago"
  parallel_track: "Iniciar dictamen GDPR esta semana (no bloquea schema, sí despliegue)"
```

---

> *"La complementariedad no requiere integración para ser válida; requiere evidencia de no-solapamiento. El schema Parquet no es un detalle de implementación; es el contrato de soberanía entre edge y centro. La prioridad no es lo urgente, es lo que desbloquea lo importante."*

**¿Procedemos a ejecutar el script de validación de schema Parquet en Vagrant hoy mismo?** 🛡️🧠