# 🏛️ Consejo de Sabios — Revisión ADR-046 v2 (DAY 158)

El ADR ha madurado muchísimo respecto a la v1. Ya no parece “cuatro herramientas conectadas”, sino una arquitectura coherente con una tesis operativa clara:

> **La crisis como unidad de correlación.**

Ese cambio conceptual es importante. El ADR deja de pensar en “joins de logs” y empieza a pensar en “eventos físicos observados desde múltiples planos”. Eso acerca el diseño a sistemas reales de DFIR/NDR maduros.

La separación entre:

* detección,
* correlación,
* entrenamiento,
* y enforcement,

está bastante bien resuelta.

El consejo cree que este ADR ya tiene entidad de paper serio y de arquitectura desplegable real.

---

# 1. Timeout de espera (60s)

## Evaluación

El timeout de 60s es razonable como:

* valor inicial conservador,
* compatible con Wazuh,
* tolerante a congestión,
* y seguro para entornos edge lentos.

El problema es que ahora mismo el timeout mezcla dos conceptos distintos:

| Concepto              | Naturaleza |
| --------------------- | ---------- |
| Latencia de ingestión | técnica    |
| Duración de la crisis | semántica  |

Y no son lo mismo.

---

## Riesgo arquitectónico

Imaginemos:

```text
t=0    Suricata alerta C2
t=2    Zeek observa JA3
t=4    aRGus sube score
t=45   Wazuh detecta proceso raro
t=90   segundo beacon del mismo C2
```

Con timeout fijo:

* o cierras demasiado pronto,
* o fusionas múltiples ataques distintos.

---

## Recomendación del Consejo

### Separar:

## A) `correlation_wait_timeout`

Tiempo máximo esperado para convergencia de señales.

Ejemplo:

```yaml
wait_timeout:
  argus: 5s
  suricata: 10s
  zeek: 15s
  wazuh: 60s
```

---

## B) `crisis_idle_timeout`

Tiempo sin nueva señal antes de cerrar la crisis.

Ejemplo:

```yaml
crisis_idle_timeout: 120s
```

Esto convierte la crisis en:

> “ventana viva mientras siga llegando actividad correlacionada”.

Mucho más robusto para:

* beaconing,
* movimiento lateral,
* campañas multi-step,
* ransomware lento,
* hands-on-keyboard.

---

## Recomendación adicional

Añadir:

```cpp
uint64_t crisis_generation;
```

Porque un nodo puede tener:

* múltiples crisis simultáneas,
* o crisis consecutivas parcialmente solapadas.

Especialmente importante cuando existan:

* múltiples interfaces,
* múltiples tenants,
* o microsegmentación.

---

# 2. Orden de integración — Suricata vs Zeek

## Recomendación clara del Consejo

## Primero Suricata.

No por calidad arquitectónica.

Por retorno inmediato.

---

## Motivos

### A) Ground truth instantáneo

Suricata permite:

* etiquetas automáticas,
* benchmarking,
* datasets enriquecidos,
* validación de correlación.

Eso desbloquea medio ADR.

---

### B) Eve.json es extremadamente cómodo

La integración operativa es simple:

* JSON,
* eventos estructurados,
* severidad,
* flow_id,
* community_id.

Zeek requiere más normalización.

---

### C) Suricata valida el pipeline entero

Con Suricata podéis validar:

```text
detección
→ crisis
→ flush
→ parquet
→ Neo4j
→ retraining
```

sin esperar a:

* parsers complejos,
* semántica TLS,
* grafos ricos.

---

## Después Zeek

Zeek aporta:

* el valor científico,
* el grafo semántico,
* el contexto profundo,
* la trazabilidad ATT&CK sofisticada.

Pero no es el mejor “primer ladrillo”.

---

## Recomendación operativa exacta

```text
Fase 1:
aRGus + Suricata + correlation-engine mínimo

Fase 2:
añadir Zeek

Fase 3:
añadir Wazuh
```

---

# 3. Wazuh en edge — prioridad

## Recomendación: P2.

Y esto es importante.

---

## Razón principal

Wazuh no es “una fuente más”.

Es:

* agente,
* manager,
* indexing,
* reglas,
* decoders,
* colas,
* sincronización,
* persistencia.

Operacionalmente es un sistema entero.

---

## Riesgo real

Ahora mismo el mayor peligro del ADR no es precisión.

Es:

> colapsar el edge antes de medir nada.

Suricata + Zeek ya pueden consumir muchísimo.

Añadir Wazuh demasiado pronto puede ocultar:

* cuellos reales,
* problemas de captura,
* pérdidas de paquetes,
* degradación del sniffer.

---

## Recomendación fuerte

### Validar primero:

```text
aRGus + Suricata + Zeek
```

en:

* RPi5,
* N100,
* tráfico real,
* MITRE real,
* stress prolongado.

Después medir cuánto margen queda.

---

## Observación importante

Wazuh tiene muchísimo valor…

pero principalmente para:

* EDR,
* persistencia,
* post-exploitation,
* compliance,
* DFIR.

No es el núcleo de vuestro diferencial científico actual.

El núcleo sigue siendo:

> comportamiento + correlación distribuida.

---

# 4. Scope mínimo del `correlation-engine`

## Total acuerdo con el enfoque incremental.

La propuesta del ADR es correcta.

---

## Recomendación exacta de v1

### correlation-engine v1

Implementar SOLO:

```text
- trigger aRGus
- lifecycle crisis
- buffers circulares
- flush parquet
- timestamps
- IDs correlación
- persistencia
```

SIN:

* joins complejos,
* Neo4j sofisticado,
* multi-trigger real,
* lógica ATT&CK,
* graph features.

---

## ¿Por qué?

Porque el riesgo principal ahora mismo es:

> complejidad accidental.

No falta visión.

Falta validación empírica.

---

## El peligro actual

El ADR ya está entrando en:

* NDR,
* EDR,
* SIEM,
* graph intelligence,
* federated learning,
* ATT&CK orchestration.

Eso puede explotar cognitivamente el proyecto.

---

## Recomendación del Consejo

Construir primero:

```text
CrisisWindow lifecycle engine
```

como núcleo puro.

Si eso funciona:

* todo lo demás es extensión natural.

Si eso falla:

* el resto del ADR colapsa.

---

# 5. ¿ADR propio para `mitre-generator`?

## Sí. Absolutamente sí.

Debe ser ADR-047.

---

## Motivo

No es una utilidad auxiliar.

Es:

# infraestructura experimental.

Y además:

* define reproducibilidad científica,
* define ground truth,
* define metodología de evaluación,
* define comparabilidad futura.

---

## Más importante todavía

Ese componente puede acabar siendo:

> uno de los activos científicos más valiosos de aRGus.

Porque la mayoría de papers:

* no automatizan ATT&CK correctamente,
* no generan datasets reproducibles,
* no sincronizan telemetría multi-fuente.

Vosotros sí vais hacia eso.

Eso tiene muchísimo valor académico.

---

# 6. Experimento académico vs sintético

## La hipótesis es extremadamente interesante.

Y coherente con lo observado en sistemas reales.

El consejo cree que probablemente habéis descubierto algo importante:

> el modelo aprendía “artefactos del dataset”, no invariantes del ataque.

Eso encaja perfectamente con Machine Learning moderno y con las críticas clásicas de Robin Sommer y Vern Paxson.

---

## PERO

Necesitáis muchísimo rigor aquí.

Porque esta afirmación es fuerte.

Muy fuerte.

---

## El Consejo recomienda:

### NO afirmar todavía:

```text
“los datasets académicos son malos”
```

---

## Sí afirmar:

```text
“en nuestras condiciones experimentales,
los datasets sintéticos generalizaron mejor”
```

Mucho más defendible.

---

## Recomendación crítica

Guardar inmediatamente:

* seeds,
* hiperparámetros,
* ratios mezcla,
* métricas,
* datasets exactos,
* commits,
* notebooks,
* curvas.

Porque esa sección puede acabar siendo:

> uno de los resultados más citables del paper.

Y sería terrible perder reproducibilidad.

---

# Observaciones arquitectónicas adicionales

## 1. Community ID

El ADR no lo menciona explícitamente y debería.

Suricata y Zeek soportan:

```text
community_id
```

Eso puede convertirse en:

> la columna vertebral de correlación cross-tool.

Muchísimo más robusto que:

* timestamps,
* 5-tuplas,
* heurísticas temporales.

El consejo recomienda elevarlo a:

```text
Correlation Primary Key
```

si está disponible.

---

## 2. Riesgo de duplicación masiva

Las cuatro fuentes observarán:

* el mismo flujo,
* múltiples veces,
* con granularidades distintas.

Necesitáis definir:

```text
canonical event identity
```

o Neo4j acabará lleno de duplicados semánticos.

---

## 3. Grafo — cuidado con explosión cardinal

El modelo de grafo es potente.

Pero:

```text
Flow
→ Domain
→ Cert
→ Process
→ File
→ AuthEvent
```

puede crecer explosivamente.

Necesitaréis:

* TTL,
* compactación,
* agregación,
* snapshots,
* cold storage.

Antes de producción real.

---

# Veredicto del Consejo

## El ADR ya tiene coherencia arquitectónica seria.

La idea central:

> correlación dirigida por crisis y no por polling pasivo

es buena.

Muy buena.

Y además diferenciadora.

---

## Recomendación estratégica final

No intentéis construir “la plataforma definitiva” en una sola iteración.

El ADR ya contiene:

* NDR,
* EDR,
* SIEM,
* graph analytics,
* ML retraining,
* federated intelligence,
* ATT&CK orchestration.

Eso son años de producto.

---

## Prioridad recomendada

```text
1. Crisis lifecycle engine
2. Suricata integration
3. Parquet enrichment
4. MITRE reproducibility
5. Zeek semantic enrichment
6. Wazuh
7. Graph intelligence
8. Ensemble federation
```

Ese orden minimiza riesgo y maximiza validación científica temprana.

---

*"Primero demostrar que la sombra existe. Después enseñarle a aprender."*
