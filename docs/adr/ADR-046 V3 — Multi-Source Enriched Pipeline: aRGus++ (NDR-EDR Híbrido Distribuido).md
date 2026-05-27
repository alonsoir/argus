# ADR-046 — Multi-Source Enriched Pipeline: aRGus++
# (NDR/EDR Híbrido Distribuido con Correlación Event-Driven)

**Estado:** BORRADOR v3 — Pendiente aprobación final Consejo de Sabios DAY 158
**Fecha:** 2026-05-19
**Autor:** Alonso Isidoro Román + Consejo de Sabios (8/8)
**Supersede:** ADR-046 v1 (PENDING-REVISION DAY 156), ADR-046 v2 (DAY 158)
**ADR relacionado:** ADR-045, ADR-040, ADR-026, ADR-029, ADR-043

---

## 1. Contexto

aRGus NDR en su estado actual (v0.9.2-day157) produce dos fuentes de datos
en runtime:

- **CSV ml-detector** — features de flujo + ML score por flujo
- **CSV firewall-acl-agent** — decisiones de bloqueo + reglas ACL aplicadas

El pipeline es funcionalmente correcto pero **incompleto en señal**:

- Solo ve el tráfico desde la perspectiva de flujo de red (Layer 3/4)
- No tiene contexto de protocolo (Layer 7: TLS, DNS, HTTP)
- No tiene firmas de amenazas conocidas como feature ni como ground truth
- No tiene visibilidad del host (procesos, ficheros, autenticación, syscalls)
- Los datasets de entrenamiento carecen de etiquetado automático de alta
  confianza

**Decisión de diseño que guía este ADR:**
El contrato protobuf actual no se modifica. El firewall sigue siendo accionado
exclusivamente por aRGus. Si los experimentos MITRE ATT&CK demuestran
empíricamente que la señal combinada mejora la decisión de bloqueo, se
abrirá un ADR específico para enriquecer el protobuf. No antes — esta
decisión requiere evidencia empírica, no especulación.

---

## 2. Decisión

Extender el pipeline edge para incorporar tres fuentes adicionales corriendo
en los mismos nodos que aRGus, con correlación event-driven en el servidor
central disparada por cualquiera de las cuatro fuentes.

**Principio rector: la crisis es la ventana de correlación.**

Cuando hay un ataque en curso, las cuatro fuentes generan señal sobre el
mismo período temporal por construcción — todas observan el mismo evento
físico desde ángulos distintos. La correlación temporal emerge del mundo
real. El servidor no impone una ventana artificial: reconoce el período
de crisis y agrupa lo que llega naturalmente agrupado.

---

## 3. Arquitectura

### 3.1 Edge — cuatro fuentes pasivas en paralelo

```
Tráfico de red
    │
    ├── aRGus sniffer (eBPF/XDP o libpcap)
    │       └── flow features + ML score → CSV → rag-security → servidor
    │
    ├── Suricata (modo pasivo, misma interfaz)
    │       └── eve.json (alerts + flows + DNS + TLS) → rag-security → servidor
    │
    ├── Zeek (modo pasivo, misma interfaz)
    │       └── conn.log + dns.log + ssl.log + files.log → rag-security → servidor
    │
    └── Wazuh agent (P2 — post-medición de recursos)
            └── FIM + procesos + auth + syscalls
                → Wazuh manager (canal propio, asíncrono) → servidor
```

**Principios:**
- Cada componente es pasivo y no interfiere con los demás
- aRGus mantiene autoridad exclusiva sobre decisiones de bloqueo (ACL)
- El contrato protobuf actual no se modifica
- Suricata y Zeek usan el canal ZeroMQ existente (rag-security)
- Wazuh usa su propio canal (OSSEC protocol TCP/1514) al manager central
- No hay nueva infraestructura de transporte — reutilización total

### 3.2 Cobertura de detección — cuatro planos ortogonales

| Fuente | Plano | Lo que ve | Lo que no ve |
|---|---|---|---|
| aRGus | Flujo behavioral | Anomalías estadísticas L3/L4 | Contenido, protocolo, host |
| Suricata | Firma | Amenazas conocidas con CVE | Anomalías sin firma |
| Zeek | Protocolo semántico | TLS, DNS, HTTP, ficheros | Decisiones, host |
| Wazuh | Host integrity | FIM, procesos, syscalls, auth | Tráfico de red |

Un atacante debe evadir los cuatro planos simultáneamente. Cualquiera de
los cuatro puede ser el primero en detectar — los otros tres responden
enviando su acumulado del mismo período.

### 3.3 Servidor central — `correlation-engine` (C++20)

El correlation-engine implementa **correlación event-driven con disparadores
múltiples y dos tipos de timeout distintos** (amendment Consejo DAY 158,
ChatGPT).

#### 3.3.1 Separación conceptual de timeouts

| Timeout | Tipo | Descripción | Default |
|---|---|---|---|
| `source_wait_timeout` | Técnico | Cuánto esperamos a cada fuente individual | por fuente |
| `crisis_idle_timeout` | Semántico | Cuánto tiempo sin nueva señal antes de cerrar la crisis | 120s |

Mezclar estos dos conceptos produce bugs en escenarios de beaconing:
un C2 que hace beacon cada 90 segundos con un timeout único de 60s
cerraría la primera aparición como crisis resuelta y abriría una nueva
para el siguiente beacon — partiendo en dos lo que es un único ataque.

#### 3.3.2 Valores de `source_wait_timeout`

Configurables vía JSON en el servidor. Valores por defecto documentados:

```json
{
  "correlation": {
    "source_wait_timeout_sec": {
      "argus":    5,
      "suricata": 10,
      "zeek":     20,
      "wazuh":    90
    },
    "crisis_idle_timeout_sec": 120,
    "late_arrival_window_sec": 180
  }
}
```

Si una fuente no está declarada en el despliegue, su timeout no penaliza
la ventana — el timeout efectivo es `max(fuentes_activas) + 5s`
(DeepSeek, DAY 158).

#### 3.3.3 Late arrivals

Si Wazuh llega después de `source_wait_timeout` pero dentro de
`late_arrival_window_sec`, se registra con `late_arrival: true` en el
Parquet en lugar de descartarse. La latencia de Wazuh es en sí misma
un dato de dataset (Grok, DAY 158).

#### 3.3.4 Modelo de operación

```
Estado normal (sin crisis):
  └── cada fuente acumula en buffer circular por nodo

Disparador de crisis — cualquiera de los cuatro:
  ├── aRGus:    ML score supera umbral configurable
  ├── Suricata: alerta de severidad alta/crítica en eve.json
  ├── Zeek:     anomalía de protocolo (DGA, JA3 conocido de C2, etc.)
  └── Wazuh:    evento FIM crítico, proceso anómalo, auth fallida repetida

Al dispararse:
  1. correlation-engine marca T1 para el nodo X, crisis_generation++
  2. Solicita flush de buffers de las otras fuentes para ese nodo
  3. Espera con source_wait_timeout individual por fuente
     — fuentes que no responden → registradas como null o late_arrival
  4. crisis_idle_timeout reinicia con cada nueva señal del mismo ataque
  5. Cuando crisis_idle_timeout expira sin nueva señal → marca T2
  6. Construye registro enriquecido compuesto → Neo4j + Parquet
```

#### 3.3.5 Implementación C++20

```cpp
// Estructura conceptual — no código de producción
struct CrisisWindow {
    std::string  node_id;
    uint64_t     crisis_generation;   // permite crisis simultáneas
    std::chrono::system_clock::time_point t1;
    std::optional<std::chrono::system_clock::time_point> t2;
    std::optional<ArgusSignal>    argus;
    std::optional<SuricataSignal> suricata;
    std::optional<ZeekSignal>     zeek;
    std::optional<WazuhSignal>    wazuh;
    CrisisSource  trigger_source;
    bool          wazuh_late_arrival = false;
};
```

- `nlohmann/json` para parseo de eve.json y Zeek logs (ya en el stack)
- `arrow::parquet` (Arrow C++) para producción de Parquet enriquecido
- `std::unordered_map<node_id, CrisisWindow>` para crisis activas
- `crisis_generation` resuelve crisis simultáneas y solapadas en el
  mismo nodo (ChatGPT, DAY 158)

#### 3.3.6 community_id como primary key de correlación

Suricata y Zeek soportan nativamente `community_id` (IETF draft,
implementación estándar). Es mucho más robusto para el join que
timestamps y 5-tupla heurística:

- Inmune a asimetrías de clock entre fuentes
- Funciona en presencia de NAT
- Estándar ya soportado — no hay que implementarlo

**`community_id` debe ser la columna vertebral del join cross-tool.**
Cuando esté disponible, tiene prioridad sobre la correlación temporal.
La correlación temporal es el fallback cuando `community_id` no está
presente (ChatGPT, DAY 158 — elevado a decisión de diseño P0).

### 3.4 Neo4j — grafo enriquecido

Con las cuatro fuentes el grafo incorpora nuevos tipos de nodo:

| Nodo | Fuente | Ejemplo |
|---|---|---|
| `Flow` | aRGus | 5-tupla + ML score + decisión ACL |
| `Signature` | Suricata | ET rule ID + CVE + severidad |
| `Domain` | Zeek dns.log | FQDN resuelto antes de la conexión |
| `Certificate` | Zeek ssl.log | JA3/JA4 fingerprint + CN + issuer |
| `File` | Zeek files.log | SHA256 de fichero transferido |
| `Process` | Wazuh | PID + nombre + parent + usuario |
| `AuthEvent` | Wazuh | login + origen + resultado |
| `Crisis` | correlation-engine | T1-T2 + trigger_source + nodo + generation |

Relaciones (refinadas por Gemini, DAY 158):

```cypher
(Crisis)-[:TRIGGERED_BY]->(Signature)
(Flow)-[:PART_OF]->(Crisis)
(Domain)-[:RESOLVED_IN]->(Crisis)
(Process)-[:EXECUTED_DURING]->(Crisis)
(AuthEvent)-[:PRECEDED]->(Crisis)
(Flow)-[:USED_CERT]->(Certificate)
```

Usando `[:PART_OF]` desde `Flow` hacia `Crisis`, las queries de
centralidad mapean la IP atacada como sumidero de aristas — el blast
radius queda visualmente inmediato.

**Advertencia — explosión cardinal (ChatGPT, DAY 158):**
El grafo puede crecer explosivamente en producción real. Antes de
despliegue se requieren: TTL por tipo de nodo, compactación periódica,
agregación de nodos redundantes, snapshots, y política de cold storage.
Registrado como DEBT-ARGUSPP-NEO4J-TTL-001.

---

## 4. Secuencia de implementación — v1.0 → v2.0

Secuencia incremental acordada por el Consejo 8/8 (síntesis Kimi + ChatGPT):

### v1.0 — Crisis lifecycle engine (solo aRGus)
- Disparador: aRGus ML score > umbral
- Buffer circular por nodo con timestamp
- Flush a Parquet con esquema Arrow completo (columnas opcionales para
  las cuatro fuentes desde el día 1 — evitar migración en v1.1)
- `crisis_generation`, `source_wait_timeout`, `crisis_idle_timeout`
- Sin join multi-fuente, sin Neo4j aún
- Valida la infraestructura de ventanas temporales

### v1.1 — Join aRGus + Suricata (MVP real)
- Suricata integrado en Vagrantfile + EMECAS
- Join temporal aRGus ↔ Suricata via `community_id` (primario) +
  5-tupla + ventana temporal (fallback)
- Etiquetado automático: Suricata alerta → flujo aRGus etiquetado
- Este es el mínimo viable para el flywheel de reentrenamiento (ADR-040)
- Valida el core del correlation-engine (join multi-fuente real)

### v1.2 — Join tri-fuente
- Zeek integrado en Vagrantfile + EMECAS
- Nodos `Domain`, `Certificate`, `File` en Neo4j
- Join completo aRGus + Suricata + Zeek

### v2.0 — Join cuatro fuentes + Neo4j completo
- Wazuh agent en edge (post-medición de recursos)
- Wazuh manager en servidor central
- Nodos `Process`, `AuthEvent` en Neo4j
- Meta-learner ensemble entrenado sobre datos enriquecidos

---

## 5. Dataset enriquecido y flywheel de reentrenamiento asíncrono

La señal compuesta que llega al servidor sirve directamente como dataset
para reentrenamiento asíncrono de plugins ML (ADR-040).

**Flujo completo:**
```
Crisis detectada
    → correlation-engine construye registro enriquecido
    → Parquet enriquecido (Arrow v1.0 schema, ADR-043)
    → pipeline de entrenamiento asíncrono (ADR-040)
    → nuevo plugin ensemble (XGBoost/CatBoost/LightGBM)
    → guardrails (Recall -0.5pp, F1 -2pp — ADR-040)
    → firma Ed25519 (ADR-025)
    → despliegue como plugin enterprise
    → mejor detección en todos los nodos
    → más instalaciones → datasets más ricos → loop
```

**Plugins ensemble especializados:**
```
XGBoost-flow      → features aRGus únicamente (baseline, como hoy)
XGBoost-enriched  → features aRGus + Zeek + Suricata correlacionadas
XGBoost-graph     → features extraídas del grafo Neo4j
Meta-learner      → combina predicciones de los tres especialistas
                    firmado Ed25519, plugin enterprise
```

**Hipótesis científica verificable:**
```
F1(ensemble enriquecido) > F1(aRGus solo) > F1(Suricata solo) > F1(Zeek solo)
```

**Sobre el protobuf y el firewall:**
El firewall sigue siendo accionado exclusivamente por aRGus. Si los
pentestings MITRE demuestran empíricamente que la señal combinada mejora
la decisión de bloqueo, se abrirá ADR específico. No antes.

---

## 6. Etiquetado automático — Suricata como ground truth

Suricata resuelve parcialmente el problema del ground truth costoso:

- Suricata alerta sobre un flujo → flujo etiquetado como malicioso con
  alta confianza (reglas ET Open, validadas por la comunidad global)
- El dataset crece con etiquetas fiables sin intervención humana

**Nota crítica sobre datasets históricos — confirmada empíricamente:**
Los pcap relay con CTU-13 Neris y CIC-IDS-2017 validan aRGus solo.
Para validar aRGus++ se requieren ataques reales en tiempo real. La
razón está documentada en §8 de este ADR.

---

## 7. Scripts MITRE ATT&CK — `mitre-generator` (→ ADR-047)

El `mitre-generator` merece ADR-047 independiente (consenso 8/8 DAY 158).
Este ADR lo referencia como dependencia para la validación empírica.

**Función:** orquestador de experimentos reproducibles. No es un atacante.

1. Selecciona técnicas ATT&CK (configurable via JSON)
2. Lanza Atomic Red Team en la máquina víctima
3. Registra timestamps exactos T1/T2 por técnica
4. Produce manifiesto: `{tecnica, t1, t2, nodo, fuente}`

El manifiesto es el contrato entre `mitre-generator` y
`correlation-engine`. Con él, cada fila del Parquet enriquecido queda
etiquetada con la técnica ATT&CK exacta que la generó.

---

## 8. Contribución científica — el experimento de los datasets

*(Sección para paper v24 — DEBT-PAPER-SYNTHETIC-001)*

### 8.1 El experimento — narración cronológica

Este hallazgo se descubrió de forma empírica y fue documentado en el
historial del proyecto. Se narra en detalle porque el proceso de
descubrimiento es parte de la contribución científica.

**Experimento 1 — baseline académico:**
Entrenamiento con CIC-IDS-2017 y CTU-13. Validación con pcap relay de
los mismos datasets académicos. F1 ≈ 0.3. El modelo había memorizado
artefactos de captura del dataset — peculiaridades del entorno de
laboratorio donde se generaron los datos — y no el comportamiento
subyacente del ataque. Resultado: catastrófico sobre tráfico real.

**Experimento 2 — mezcla proporcional:**
Introducción incremental de datos sintéticos en proporciones 5%, 10%,
15%... Mejora marginal en cada paso pero insuficiente en todos los
casos. El descubrimiento contraintuitivo: añadir datos académicos a
los sintéticos *degradaba* el modelo. El punto óptimo no era un ratio
intermedio — era el extremo puro. La mezcla seguía introduciendo el
sesgo del dataset académico.

**Experimento 3 — sintético estadístico puro:**
DeepSeek generó un dataset que no captura firmas ni ejemplos concretos
de ataques, sino las *distribuciones estadísticas del comportamiento* —
probabilidades, pesos de features, invariantes de flujo que definen
cómo se comporta el tráfico malicioso, no qué paquetes concretos envió.
Resultado: F1=0.9985, Recall=1.000. El modelo detecta Neris 2011 sin
haber visto nunca ese dataset ni tráfico similar.

### 8.2 El descubrimiento

El modelo aprendió *invariantes comportamentales* en lugar de
correlaciones específicas del dataset. Esto explica por qué aRGus
detecta tráfico de 2011 con modelos entrenados en 2026 — los invariantes
estadísticos del comportamiento botnet no han cambiado tanto como las
firmas.

### 8.3 Implicación para la comunidad científica

Los datasets académicos de ciberseguridad tienen sesgo de construcción:
están diseñados para que los ataques sean detectables por métodos
conocidos. Un modelo que los memoriza tiene métricas perfectas en
validación cruzada y falla en producción. **Son herramientas de
benchmark, no de entrenamiento.** Esta distinción no está documentada
en la literatura con evidencia empírica de esta claridad.

La misma razón por la que Suricata no genera alertas sobre tráfico de
2011 (reglas retiradas del feed actual) es la razón por la que el
modelo académico falla: ambos dependen de conocimiento previo de la
amenaza. aRGus no.

### 8.4 Reproducibilidad

El experimento es reproducible por construcción: los mismos datasets
académicos están disponibles, el generador sintético estadístico puede
re-ejecutarse, el proceso está documentado en el historial del proyecto.
Si los artefactos originales (curvas F1 vs ratio) se han perdido en VMs
destruidas, el experimento se re-ejecuta con una nueva ejecución
controlada usando el pipeline actual. La reproducibilidad es el punto,
no la conservación de artefactos específicos.

### 8.5 Tarea para paper v24

Sección: *"On the inadequacy of academic datasets for behavioral anomaly
detection: an empirical study"*

Contenido:
- Curva F1 vs ratio académico/sintético (0%, 5%...100%)
- Justificación teórica: sesgo de construcción vs invariantes
  comportamentales
- Conexión con resultado Suricata DAY 146 (mismo mecanismo subyacente)
- Referencias: Sommer & Paxson [2010], Arp et al. [2022] "Dos and
  Don'ts of Machine Learning in Computer Security" (USENIX Security),
  Wagner et al. [2022] "SoK: The Problem of Dataset Shift in
  Machine-Learning-Based Network Intrusion Detection"

---

## 9. Consumo de recursos — tiers de despliegue

El consumo del pipeline aRGus++ completo es desconocido y requiere
medición empírica en hardware físico (DEBT-ARGUSPP-RESOURCE-001).

```
Tier 1 — Mínima (RPi5)
  └── aRGus únicamente — detección básica, bloqueo

Tier 2 — Media (RPi5 + N100)
  └── RPi5: aRGus + Suricata
      N100: Zeek + Wazuh agent + rag-security local

Tier 3 — Completa (múltiples nodos)
  └── Nodo 1: aRGus + Suricata
      Nodo 2: Zeek + Wazuh agent
      Servidor: correlation-engine + Neo4j + Wazuh manager + ensemble
```

La decisión de qué componente va en qué tier requiere mediciones reales.
Las configuraciones anteriores son hipótesis de trabajo, no garantías.

---

## 10. NTP — gate de arranque (P0)

La correlación temporal del correlation-engine es inútil sin relojes
sincronizados. Sin NTP, el join produce registros incorrectos.

**NTP es P0 pre-deploy, no una deuda técnica menor** (DeepSeek + Grok,
DAY 158). Implementación:

- `chrony` instalado en todos los nodos edge via Vagrantfile
- Health-check del sistema rechaza arranque del correlation-engine si
  offset NTP > 1 segundo
- `community_id` como fallback cuando el offset sea inaceptable

Registrado como DEBT-ARGUSPP-NTP-001 con nivel P0.

---

## 11. Frontera community / enterprise

| Capa | Community | Enterprise |
|---|---|---|
| aRGus core (sniffer, detector, ACL) | ✅ | ✅ |
| Suricata + Zeek en edge | ✅ | ✅ |
| Wazuh agent | ✅ | ✅ |
| `correlation-engine` C++20 | ✅ | ✅ |
| Neo4j grafo local | ✅ | ✅ |
| `mitre-generator` (ADR-047) | ✅ | ✅ |
| **Plugins ensemble especializados** | ❌ | ✅ firmado Ed25519 |
| **Meta-learner distribuido** | ❌ | ✅ |
| **Inteligencia federada entre instalaciones** | ❌ | ✅ |
| **Dashboard de flota** | ❌ | ✅ |

---

## 12. Consecuencias

### Positivas

- El pipeline edge no cambia estructuralmente — se añaden procesos pasivos
- No hay nueva infraestructura de transporte — reutilización total
- El contrato protobuf no se modifica — backlog actual intacto
- `correlation-engine` es un componente nuevo aislado y testeable
- Secuencia v1.0→v1.1→v1.2→v2.0 permite validación incremental
- Los datasets generados serán cualitativamente superiores a cualquier
  dataset público disponible para infraestructura crítica
- La hipótesis científica es verificable y publicable
- aRGus evoluciona de NDR a **plataforma NDR/EDR híbrida distribuida
  auto-aprendiente**

### Negativas / Riesgos

- Suricata y Zeek añaden carga de CPU en el edge — requiere cuantificación
- Sin NTP sincronizado el join produce registros incorrectos — P0
- Sin `community_id` el join es heurístico — presente en Suricata y Zeek
  desde la configuración inicial
- El grafo Neo4j puede crecer explosivamente — TTL y compactación
  necesarios antes de producción (DEBT-ARGUSPP-NEO4J-TTL-001)
- Si los pentestings MITRE demuestran que el firewall necesita señal
  combinada, habrá que enriquecer el protobuf — coste conocido y aceptado

### Deuda técnica generada

| ID | Descripción | Prioridad |
|---|---|---|
| DEBT-ARGUSPP-NTP-001 | NTP + health-check offset >1s bloquea arranque | P0 pre-deploy |
| DEBT-ARGUSPP-RESOURCE-001 | Medir CPU/RAM de las 4 fuentes en RPi5 y N100 | P1 con hardware |
| DEBT-ARGUSPP-SURICATA-001 | Integrar Suricata en Vagrantfile + EMECAS | P1 |
| DEBT-ARGUSPP-ZEEK-001 | Integrar Zeek en Vagrantfile + EMECAS | P1 |
| DEBT-ARGUSPP-WAZUH-001 | Wazuh agent en edge + manager en servidor | P2 post-recursos |
| DEBT-ARGUSPP-COMMUNITY-ID-001 | Habilitar community_id en Suricata y Zeek | P0 en v1.1 |
| DEBT-ARGUSPP-CORRELATION-001 | Implementación C++20 correlation-engine v1.0 | P1 |
| DEBT-ARGUSPP-TIMEOUT-CONFIG-001 | Mapa source_wait_timeout configurable por JSON | P1 en v1.0 |
| DEBT-ARGUSPP-NEO4J-TTL-001 | TTL + compactación + cold storage Neo4j | P1 pre-producción |
| DEBT-ARGUSPP-MITRE-001 | mitre-generator + Atomic Red Team (→ ADR-047) | P1 post-hardware |
| DEBT-ARGUSPP-BENCHMARK-001 | BENCHMARK-CAPACITY-001 con 4 fuentes activas | P1 post-hardware |
| DEBT-PAPER-SYNTHETIC-001 | Sección paper v24: curva F1 vs ratio + referencias | P2 |

---

## 13. Alternativas consideradas y descartadas

**Join en el edge** — Descartado. Recursos del edge reservados para
captura, detección y bloqueo.

**Ventana fija ±500ms (v1)** — Descartado. La crisis es la ventana.
Un join basado en ventana temporal fija produce ruido en períodos de
calma y puede partir ataques multi-step en registros distintos.

**Timeout único para todas las fuentes (v2)** — Descartado. Mezcla
latencia técnica (source_wait_timeout) con duración de crisis
(crisis_idle_timeout). ChatGPT DAY 158 identificó el bug resultante en
escenarios de beaconing periódico.

**Wazuh como único disparador** — Descartado. Wazuh no ve ataques
puramente de red. El modelo de cuatro disparadores es necesario.

**Enriquecer el protobuf ahora** — Descartado hasta evidencia MITRE.

**Python para correlation-engine** — Descartado. Consistencia C++20.

**community_id como opcional** — Descartado. Es la columna vertebral
del join. Debe habilitarse desde la configuración inicial de Suricata
y Zeek, no como mejora posterior.

---

## 14. Orden de integración aprobado (Consejo 8/8 unánime)

```
1. Crisis lifecycle engine (correlation-engine v1.0) — aRGus only
2. Suricata en Vagrantfile + EMECAS (v1.1)
3. Parquet enriquecido con etiquetado automático
4. MITRE reproducibilidad (ADR-047)
5. Zeek enriquecimiento semántico (v1.2)
6. Wazuh — post-medición de recursos (v2.0)
7. Graph intelligence Neo4j completo
8. Ensemble federation + meta-learner
```

---

## 15. Referencias

- ADR-026 — XGBoost Plugin Track 1 (baseline F1=0.9985)
- ADR-029 — Variant A/B (eBPF/XDP vs libpcap)
- ADR-040 — ML Plugin Retraining Contract
- ADR-043 — Memoria Episódica Distribuida
- ADR-045 — VaultClient Decomposition by Composition
- ADR-047 — mitre-generator (pendiente redacción)
- BACKLOG-BENCHMARK-CAPACITY-001
- BACKLOG-ZMQ-TUNING-001 ✅ cerrado DAY 155
- arXiv:2604.04952 v3 — Paper DAY 148
- Sommer & Paxson [2010] — Outside the Closed World
- Asad et al. [2023] — Signature aging en Snort/Suricata
- Arp et al. [2022] — Dos and Don'ts of ML in Computer Security
  (USENIX Security) — sesgo en datasets académicos
- Wagner et al. [2022] — SoK: The Problem of Dataset Shift in
  ML-Based Network Intrusion Detection

---

## Notas del Consejo de Sabios — DAY 158 (8/8)

> "ADR-046 v3 — APROBADO.
>
> Los amendments principales respecto a v2:
>
> **community_id como primary key** (ChatGPT): elevado de nota a decisión
> de diseño P0. Es la columna vertebral del join cross-tool. La correlación
> temporal es el fallback, no el mecanismo principal.
>
> **Separación source_wait_timeout / crisis_idle_timeout** (ChatGPT): la
> v2 mezclaba dos conceptos distintos. crisis_idle_timeout de 120s permite
> que beaconing, movimiento lateral y campañas multi-step queden capturados
> como una única crisis coherente.
>
> **crisis_generation** (ChatGPT): permite múltiples crisis simultáneas
> o parcialmente solapadas en el mismo nodo. Crítico para microsegmentación
> y múltiples interfaces.
>
> **late_arrival: true** (Grok): la latencia de Wazuh es información,
> no ruido. Registrar en lugar de descartar.
>
> **Secuencia v1.0→v1.1→v1.2→v2.0** (Kimi): el MVP real es v1.1 con
> join aRGus+Suricata, no v1.0. v1.0 valida la infraestructura;
> v1.1 valida el core.
>
> **NTP como gate de arranque** (DeepSeek + Grok): elevado de deuda
> técnica P2 a P0 bloqueante. Chrony en Vagrantfile. Health-check
> rechaza arranque si offset >1s.
>
> **§8 del paper** (Kimi): añadir Arp et al. [2022] y Wagner et al. [2022]
> para el marco teórico del experimento académico/sintético. El resultado
> de F1≈0.3 con entrenamiento académico es evidencia empírica de lo que
> estos papers teorizan.
>
> **Explosión cardinal Neo4j** (ChatGPT): TTL y compactación son
> prerequisitos de producción real, no mejoras opcionales.
> DEBT-ARGUSPP-NEO4J-TTL-001 registrada.
>
> 'Primero demostrar que la sombra existe. Después enseñarle a aprender.'
> — ChatGPT · DAY 158"
> — Consejo de Sabios (8/8) · ADR-046 v3 · DAY 158

---

*"Un escudo que aprende de su propia sombra."*
*Via Appia Quality — construido para permanecer.*