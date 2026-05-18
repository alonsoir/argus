# ADR-046 — Multi-Source Enriched Pipeline: aRGus++ (NDR/EDR Híbrido Distribuido)

**Estado:** BORRADOR — Pendiente revisión Consejo de Sabios DAY 146
**Fecha:** 2026-05-19
**Autor:** Alonso Isidoro Román + Consejo de Sabios
**Rama:** feature/adr046-multi-source-pipeline
**ADR relacionado:** ADR-045 (VaultClient Decomposition by Composition)

---

## 1. Contexto

aRGus NDR en su estado actual (v0.7.0-variant-b) produce dos fuentes de datos
en runtime:

- **CSV ml-detector** — features de flujo + ML score por flujo
- **CSV firewall-acl-agent** — decisiones de bloqueo + reglas ACL aplicadas

Ambos CSVs se envían al servidor via `rag-security` (ZeroMQ + ChaCha20-Poly1305),
se convierten a Parquet, y alimentan el pipeline de entrenamiento de plugins ML
(XGBoost, F1=0.9985 sobre CTU-13 Neris).

El pipeline es funcionalmente correcto pero **incompleto en señal**:

- Solo ve el tráfico desde la perspectiva de flujo de red (Layer 3/4)
- No tiene contexto de protocolo (Layer 7: TLS, DNS, HTTP)
- No tiene firmas de amenazas conocidas como feature ni como ground truth automático
- No tiene visibilidad del host (procesos, ficheros, autenticación)
- Los datasets de entrenamiento carecen de etiquetado automático de alta confianza

Esta limitación impide construir modelos ensemble de calidad superior y un grafo
de amenazas completo en Neo4j.

**Nota crítica sobre datasets históricos:**
El pcap relay con CTU-13 Neris (2011) y CIC-IDS-2017 valida aRGus solo. No es
suficiente para validar aRGus++ porque:

- Suricata moderno no genera alertas sobre tráfico de 2011 — las reglas ET Open
  para amenazas de esa época están retiradas del feed actual (confirmado DAY 146,
  §8.13 del paper v23)
- Zeek ve el tráfico pero genera señal limitada — contexto de protocolo presente,
  pero dominios C2 de 2011 no están en feeds actuales de threat intelligence
- Wazuh no ve nada — no hay procesos reales, no hay actividad en el host

Para validar aRGus++ se requiere **ataques reales ejecutándose en tiempo real**
mediante scripts MITRE ATT&CK (ver §7 de este ADR).

---

## 2. Decisión

Extender el pipeline edge para incorporar **tres fuentes adicionales** corriendo
en los mismos nodos que aRGus:

| Componente | Rol | Datos producidos |
|---|---|---|
| **Suricata** | Detección por firma | `eve.json` — alertas, flows, DNS, TLS |
| **Zeek** | Análisis de protocolo | `conn.log`, `dns.log`, `ssl.log`, `files.log` |
| **Wazuh agent** | Visibilidad host | FIM, procesos, auth, syscalls |

Las cuatro fuentes corren en paralelo en el edge. **El join no ocurre en el
edge** — los recursos del edge (RPi5, N100) están reservados para captura,
detección y bloqueo.

El join y el enriquecimiento ocurren en el **servidor central**, en un nuevo
componente `correlation-engine` implementado en C++20.

**Sin Python en el pipeline de producción.** Consistencia arquitectural con
el resto del stack C++20.

---

## 3. Arquitectura

### 3.1 Edge (cada nodo protegido)

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
    └── Wazuh agent
            └── FIM + procesos + auth → Wazuh manager → servidor
```

**Principio:** cada componente es pasivo y no interfiere con los demás.
aRGus mantiene autoridad exclusiva sobre decisiones de bloqueo (ACL).

### 3.2 Transporte edge → servidor

Las fuentes Suricata y Zeek se envían al servidor usando el mismo mecanismo
que ya existe para los CSVs de aRGus:

- ZeroMQ PUSH/PULL
- Cifrado ChaCha20-Poly1305 (libsodium)
- Formato: JSON lines (eve.json, Zeek logs) → conversión a Parquet en servidor

No se añade nueva infraestructura de transporte — se reutiliza el canal existente.

### 3.3 Servidor central — `correlation-engine` (C++20)

```
Entradas:
  ├── CSV aRGus (flow features + ML score)
  ├── eve.json Suricata (alerts + metadata)
  ├── Zeek logs (conn + dns + ssl + files)
  └── Wazuh events (host telemetry)

Correlación:
  └── join temporal por 5-tupla (src_ip, dst_ip, src_port, dst_port, proto)
      ventana ±500ms configurable via JSON

Salidas:
  ├── Parquet enriquecido → entrenamiento plugins ensemble
  └── Neo4j → grafo de amenazas multi-dimensión
```

**Implementación C++20:**
- `arrow::parquet` (Arrow C++) para producción de Parquet
- `nlohmann/json` para parseo de eve.json y Zeek logs (ya en el stack)
- `std::unordered_map` + `std::chrono` para join temporal por 5-tupla

### 3.4 Neo4j — grafo enriquecido

Con las cuatro fuentes el grafo incorpora nodos de nuevo tipo:

| Nodo | Fuente | Ejemplo |
|---|---|---|
| `Flow` | aRGus | 5-tupla + ML score + decisión ACL |
| `Signature` | Suricata | ET rule ID + CVE + severidad |
| `Domain` | Zeek dns.log | FQDN resuelto antes de la conexión |
| `Certificate` | Zeek ssl.log | JA3/JA4 fingerprint + CN + issuer |
| `File` | Zeek files.log | hash SHA256 de fichero transferido |
| `Process` | Wazuh | PID + nombre + parent + usuario |
| `AuthEvent` | Wazuh | login + origen + resultado |

Relaciones de ejemplo:
```
(IP)-[:RESOLVED]->(Domain)
(Flow)-[:TRIGGERED]->(Signature)
(Flow)-[:USED_CERT]->(Certificate)
(IP)-[:SPAWNED]->(Process)
(Process)-[:MODIFIED]->(File)
(AuthEvent)-[:FROM]->(IP)
```

Un nodo IP que resuelve dominios DGA + establece TLS con JA3 conocido de
Cobalt Strike + dispara regla ET de C2 + lanza proceso anómalo post-conexión:
el grafo cuenta la cadena de ataque completa. aRGus solo ve la anomalía de flujo.
El grafo enriquecido permite hacer preguntas cualitativamente superiores.

---

## 4. Plugins ensemble — especialistas por fuente

La señal enriquecida permite entrenar un ensemble de especialistas:

```
XGBoost-flow      → features aRGus únicamente (baseline, como hoy)
XGBoost-enriched  → features aRGus + Zeek + Suricata correlacionadas
XGBoost-graph     → features extraídas del grafo Neo4j
                    (centralidad, clustering, distancia a nodos maliciosos)

Meta-learner      → combina predicciones de los tres especialistas
                    firmado Ed25519, desplegado como plugin enterprise
```

**Hipótesis científica verificable:**
```
F1(ensemble enriquecido) > F1(aRGus solo) > F1(Suricata solo) > F1(Zeek solo)
```

Demostrable empíricamente con pentesting estructurado MITRE ATT&CK — cada
técnica ATT&CK deja huella en las cuatro fuentes simultáneamente, produciendo
ground truth de alta calidad sin intervención humana.

---

## 5. Etiquetado automático y flywheel de aprendizaje

**El problema histórico** de los datasets de ciberseguridad es ground truth
caro y ruidoso. Suricata resuelve esto parcialmente para amenazas conocidas:

- Si Suricata dispara alerta sobre un flujo → flujo etiquetado como malicioso
  con alta confianza (reglas ET Open, validadas por la comunidad global)
- El conjunto de entrenamiento crece con etiquetas fiables sin intervención humana
- Menos ruido en etiquetas → modelos más precisos → mejor generalización

**Flywheel de aprendizaje distribuido:**
```
Más instalaciones → más tráfico real capturado
                 → datasets más ricos con etiquetado automático
                 → pentesting MITRE ATT&CK → ground truth de alta calidad
                 → plugins ensemble mejores (firmados Ed25519)
                 → mejor detección en todas las instalaciones
                 → más instalaciones confían en el sistema
```

Es el mecanismo inmunológico federado descrito en el paper — cada nodo que
aprende protege a todos los demás.

---

## 6. Por qué los datasets históricos no son suficientes para aRGus++

Esta distinción es crítica y debe quedar documentada:

**pcap replay histórico (CTU-13, CIC-IDS-2017):**
- Válido para: validar aRGus solo (ML sobre flujos comportamentales)
- Inválido para: validar aRGus++ con las cuatro fuentes activas

La razón técnica:
- Suricata no genera alertas (reglas para amenazas de 2011 están retiradas)
- Zeek genera señal limitada (dominios C2 de 2011 no en threat intel actual)
- Wazuh no ve nada (no hay procesos reales, solo paquetes en el wire)

**MITRE ATT&CK ejecutado en tiempo real:**
- Válido para: validar aRGus++ completo (las cuatro fuentes)
- Produce ground truth perfecto con manifiesto de experimento
- Datasets modernos, reproducibles, cualitativamente superiores

**Esto es una contribución científica por sí misma** — documentada en §8
de este ADR y pendiente de sección en el paper v24.

---

## 7. Scripts MITRE ATT&CK — `mitre-generator`

Componente nuevo que no es un atacante sino un **orquestador de experimentos**:

1. Selecciona técnicas ATT&CK a ejecutar (configurable via JSON)
2. Lanza Atomic Red Team en la máquina víctima
3. Registra timestamps de inicio y fin de cada técnica
4. Produce manifiesto JSON: `{tecnica, t_inicio, t_fin, nodo, fuente}`
5. El manifiesto se cruza con logs del servidor para etiquetar el dataset

El manifiesto es la clave — sin él el dataset no tiene ground truth verificable.
Con él cada fila del Parquet enriquecido queda etiquetada con la técnica ATT&CK
exacta que la generó.

**Herramientas candidatas:**
- **Atomic Red Team** (Red Canary) — tests atómicos por técnica MITRE, open-source
- **Caldera** (MITRE) — adversary emulation automatizado, campañas completas
- **Metasploit** — para técnicas de explotación real

**Implementación:** C++20 para el orquestador. Atomic Red Team como dependencia
externa (bash/PowerShell por técnica). El manifiesto JSON es el contrato entre
el orquestador y el `correlation-engine`.

---

## 8. Contribución científica no documentada — datasets sintéticos vs académicos

**Esta sección documenta un descubrimiento empírico que no aparece en el paper
actual (v23) y que merece sección propia en v24.**

### 8.1 El experimento

Durante el desarrollo temprano del proyecto, se evaluaron tres estrategias de
entrenamiento para los clasificadores de aRGus:

1. **100% datos académicos** (CIC-IDS-2017, CTU-13): métricas excelentes en
   validación cruzada. Al pasar el mismo dataset via pcap relay, el detector
   era prácticamente ciego. El modelo había memorizado peculiaridades del
   dataset, no el comportamiento subyacente.

2. **Mezcla en proporciones** (académico + sintético, varios ratios): evaluados
   sistemáticamente. Resultado empírico sorprendente: añadir datos académicos
   a los sintéticos **degradaba** el modelo. El punto óptimo no era un ratio
   intermedio — era el extremo puro.

3. **100% datos sintéticos basados en distribuciones estadísticas de
   comportamiento**: el único que funcionó. El modelo aprendió invariantes
   comportamentales en lugar de correlaciones específicas del dataset.

### 8.2 Por qué ocurre

Los datasets académicos tienen sesgo de construcción: están diseñados para que
los ataques sean detectables por métodos conocidos. Un modelo que los memoriza
tiene métricas perfectas en validación y falla en producción.

Los datos sintéticos basados en distribuciones estadísticas capturan algo más
profundo: **cómo se comporta el tráfico malicioso en términos de flujo,
independientemente de la técnica específica**. Esto explica por qué aRGus
detecta tráfico de 2011 con modelos entrenados en 2026 — los invariantes
estadísticos del comportamiento botnet no han cambiado tanto como las firmas.

### 8.3 Evidencia empírica en el paper actual

El paper v23 menciona el resultado (sintético puro) pero **no documenta el
proceso de descubrimiento ni el experimento de mezcla**. Lo que aparece:

- Abstract: *"All classifiers trained exclusively on synthetic data"*
- §8.5: *"Synthetic training data. All classifiers trained exclusively on
  synthetic data; CTU-13 Neris held out entirely for evaluation."*
- §8.13: *"trained on synthetic data informed by CTU-13 flow statistics"*

Lo que **no aparece**:
- El experimento de mezcla con curva F1 vs ratio académico/sintético
- La degradación al añadir datos académicos
- La justificación teórica del por qué
- La conexión con la incapacidad de Suricata para detectar tráfico histórico
  (ambos son síntomas del mismo problema: dependencia del conocimiento previo)

### 8.4 Tarea para el paper v24

Añadir sección: *"On the inadequacy of academic datasets for behavioral anomaly
detection: an empirical study"* con:

- Curva F1 vs ratio académico/sintético (si los datos del experimento existen)
- Justificación teórica: sesgo de construcción vs invariantes comportamentales
- Conexión con el resultado Suricata DAY 146: ambos dependen de conocimiento
  previo de la amenaza; aRGus no
- Conexión con Sommer & Paxson [2010]: evidencia empírica adicional de la tesis

---

## 9. Consumo de recursos del pipeline conjunto

**Tarea relacionada con ADR-045 (VaultClient Decomposition by Composition).**

El consumo de recursos de aRGus solo está documentado en el paper (DAY 87,
Tabla de recursos). El consumo del pipeline aRGus++ completo es **desconocido**.

### 9.1 Hipótesis de trabajo

Se anticipa que el pipeline completo no cabrá en una RPi5 con todos los
componentes activos simultáneamente. La decisión de qué sacrificar o distribuir
requiere medición empírica.

### 9.2 Experimento requerido

En cada configuración de hardware (BM-A, BM-B, BM-C, BM-D de
BACKLOG-BENCHMARK-CAPACITY-001), medir con las cuatro fuentes activas:

```
aRGus sniffer + detector + ACL  → CPU, RAM, disco conocidos (DAY 87)
+ Suricata                       → delta CPU, delta RAM
+ Zeek                           → delta CPU, delta RAM
+ Wazuh agent                    → delta CPU, delta RAM
──────────────────────────────────────────────────────
Total → ¿queda margen para rag-security en el mismo nodo?
```

### 9.3 Combinaciones de despliegue posibles

El pipeline distribuido permite múltiples configuraciones según los recursos
disponibles:

```
Mínima (RPi5 solo, 90€)
  └── aRGus únicamente → detección básica, bloqueo

Media (RPi5 + N100, ~310€)
  └── RPi5: aRGus + Suricata
      N100: Zeek + Wazuh agent + rag-security local

Completa (múltiples nodos)
  └── Nodo 1: aRGus + Suricata
      Nodo 2: Zeek + Wazuh agent
      Servidor: correlation-engine + Neo4j + ensemble
```

Cada combinación tiene su perfil de coste/protección documentable — útil
para que un hospital rural sepa qué puede desplegar con su presupuesto.

### 9.4 Decisión sobre rag-security

Si rag-security no cabe en el edge junto a las demás fuentes, se migra al
servidor. El edge tiene prioridad absoluta: capturar, detectar, bloquear.
Todo lo demás es secundario.

**Deuda técnica derivada:** DEBT-ARGUSPP-RESOURCE-001 — medir consumo de
CPU/RAM/disco de Suricata + Zeek + Wazuh agent en RPi5 y N100. Prerequisito
para definir configuraciones de despliegue recomendadas. Vinculada a
BACKLOG-BENCHMARK-CAPACITY-001 (re-ejecutar con las cuatro fuentes activas).

---

## 10. Frontera community / enterprise

| Capa | Community | Enterprise |
|---|---|---|
| aRGus core (sniffer, detector, ACL) | ✅ open-source | ✅ |
| Suricata + Zeek en edge | ✅ open-source | ✅ |
| Wazuh agent | ✅ open-source | ✅ |
| `correlation-engine` C++20 | ✅ open-source | ✅ |
| Neo4j grafo local | ✅ | ✅ |
| **Plugins ensemble especializados** | ❌ | ✅ plugin enterprise firmado Ed25519 |
| **Meta-learner distribuido** | ❌ | ✅ |
| **Inteligencia federada entre instalaciones** | ❌ | ✅ |
| **Dashboard de flota** | ❌ | ✅ |

---

## 11. Consecuencias

### Positivas

- El pipeline edge no cambia estructuralmente — se añaden procesos pasivos
- No hay nueva infraestructura de transporte — se reutiliza ZeroMQ existente
- `correlation-engine` es un componente nuevo aislado, testeable independientemente
- Los datasets generados serán cualitativamente superiores a cualquier dataset
  público disponible para infraestructura crítica
- La hipótesis científica es verificable y publicable (USENIX Security / NDSS)
- aRGus evoluciona de NDR a solución híbrida **NDR/EDR distribuida auto-aprendiente**
- El modelo de sostenibilidad económica queda justificado: community gratuito,
  enterprise de pago por el ensemble y la inteligencia federada

### Negativas / Riesgos

- Suricata y Zeek añaden carga de CPU en el edge — requiere cuantificación
  (DEBT-ARGUSPP-RESOURCE-001)
- El join temporal requiere sincronización de relojes NTP en todos los nodos —
  sin esto la ventana ±500ms produce joins incorrectos
- `correlation-engine` requiere su propio ADR de implementación detallado antes
  de escribir código
- Los scripts MITRE ATT&CK son prerequisito para validación — no hay pcap
  histórico que sirva para las cuatro fuentes simultáneamente

### Deuda técnica generada

| ID | Descripción | Prioridad |
|---|---|---|
| DEBT-ARGUSPP-NTP-001 | NTP sincronizado y verificado en todos los nodos edge | P0 pre-deploy |
| DEBT-ARGUSPP-RESOURCE-001 | Medir CPU/RAM/disco de las 4 fuentes en RPi5 y N100 | P1 con hardware |
| DEBT-ARGUSPP-SURICATA-001 | Integrar Suricata en Vagrantfile + EMECAS | P1 |
| DEBT-ARGUSPP-ZEEK-001 | Integrar Zeek en Vagrantfile + EMECAS | P1 |
| DEBT-ARGUSPP-WAZUH-001 | Wazuh agent en edge + manager en servidor | P1 |
| DEBT-ARGUSPP-CORRELATION-001 | ADR detallado + implementación C++20 correlation-engine | P1 post-hardware |
| DEBT-ARGUSPP-MITRE-001 | Diseño e implementación mitre-generator + Atomic Red Team | P1 post-hardware |
| DEBT-ARGUSPP-BENCHMARK-001 | Re-ejecutar BACKLOG-BENCHMARK-CAPACITY-001 con 4 fuentes | P1 post-hardware |
| DEBT-PAPER-SYNTHETIC-001 | Sección paper v24: datasets sintéticos vs académicos | P2 |

---

## 12. Alternativas consideradas

**Join en el edge** — Descartado. Recursos del edge reservados para captura,
detección y bloqueo. El join añadiría latencia y consumo inaceptables en RPi5.

**Python para `correlation-engine`** — Descartado. Consistencia arquitectural
con el resto del pipeline C++20. Arrow C++ y nlohmann/json cubren todos los
requisitos sin Python.

**Sustituir aRGus por Suricata + Zeek** — Descartado. Suricata no detecta
anomalías desconocidas. Zeek no toma decisiones. Ninguno bloquea. Ninguno
corre con el perfil de recursos de aRGus. Son complementarios, no sustitutos.

**Usar CIC-IDS-2017 / CTU-13 para validar aRGus++** — Descartado. Wazuh
ciego sobre pcap histórico. Suricata sin alertas sobre tráfico de 2011.
Zeek con señal limitada. Solo MITRE ATT&CK en tiempo real produce
ground truth válido para las cuatro fuentes simultáneamente.

---

## 13. Preguntas abiertas para el Consejo de Sabios

1. **Ventana de correlación** — ±500ms como valor inicial. ¿El Consejo
   identifica escenarios donde esta ventana produce joins incorrectos? ¿Debería
   ser configurable por tipo de protocolo (DNS más corto, SMTP más largo)?

2. **Orden de integración** — ¿Suricata primero o Zeek primero? Suricata aporta
   etiquetado automático (valor inmediato para datasets). Zeek aporta contexto
   de protocolo (valor para el grafo). ¿Recomendación del Consejo?

3. **Wazuh en el edge** — footprint mayor que Suricata/Zeek. ¿P1 junto a los
   otros o P2 post-validación de que Suricata + Zeek caben en el edge?

4. **`correlation-engine` scope mínimo v1** — ¿Mínimo viable científicamente
   útil? ¿Solo aRGus + Suricata (etiquetado automático) como v1, o los tres
   desde el principio?

5. **`mitre-generator`** — ¿Componente independiente con su propio ADR o
   sección dentro de ADR-046? ¿Atomic Red Team como dependencia externa o
   implementación propia de los scripts atómicos?

6. **Experimento de mezcla datasets** — ¿Los datos del experimento académico
   vs sintético existen en forma recuperable? ¿Es prioritario reconstruirlos
   para el paper v24 o se documenta el resultado sin la curva?

---

## 14. Referencias

- ADR-026 — XGBoost Plugin Track 1 (baseline actual F1=0.9985)
- ADR-029 — Variant A/B (eBPF/XDP vs libpcap)
- ADR-040 — ML Plugin Retraining Contract
- ADR-045 — VaultClient Decomposition by Composition
- BACKLOG-BENCHMARK-CAPACITY-001 — Plan de benchmarks de capacidad
- BACKLOG-ZMQ-TUNING-001 — Prerequisito optimización ZeroMQ
- arXiv:2604.04952 v23 — Paper DAY 148
- Sommer & Paxson [2010] — Outside the Closed World
- Asad et al. [2023] — Signature aging en Snort/Suricata

---

*"Un escudo, nunca una espada."*
*Via Appia Quality — construido para permanecer.*