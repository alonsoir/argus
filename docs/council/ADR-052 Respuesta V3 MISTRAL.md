El **ADR-052 v3** es una versión **madura, técnica y alineada con la misión primaria** del proyecto (el corpus como producto). Incorpora **soluciones concretas a los problemas identificados en v2**, resuelve las preguntas abiertas del Consejo, y añade **mejoras críticas** como el **WAL externo para no-repudio**, la **separación entre `node_id` estable y keypair efímero**, y la **inclusión de señales TCP/TLS para el vector A ampliado**. A continuación, mi análisis detallado, **respuestas a las preguntas implícitas**, y recomendaciones finales para la ratificación.

---

---

---

## **🔍 Análisis por Sección Clave (v3)**
---

### **🎯 §0. Misión Primaria y §0.1 Métricas de Calidad del Corpus**
**✅ Fortalezas:**
- **Principio ordenador claro y accionable**:
    - El grafo es **un corpus de entrenamiento enriquecido**, no solo un sistema de correlación en vivo. Esto justifica decisiones como **etiquetar (no borrar) flujos inyectados** o priorizar la **trazabilidad offline**.
    - **Ejemplo de impacto**: La decisión de usar un **WAL externo append-only** (§3.7) para el etiquetado es coherente con la necesidad de **auditabilidad científica** del corpus.

- **Métricas de calidad del corpus (§0.1)**:
    - Los KPIs propuestos (**% flujos con `provenance_ground_truth`**, **% con `witness_count ≥ 2`**, **tiempo de reconstrucción desde pcap**, **cobertura MITRE**, **balance de clases**) son **medibles, relevantes y alineadas con la misión**.
    - **Recomendación**:
        - Añadir una métrica de **"% de flujos con `CONFLICT_NAT` resueltos"** para medir la calidad de la correlación host↔red.
        - Incluir **"% de flujos con `rate_limited: true`"** para monitorizar el rate-limit de cardinalidad.

**⚠️ Puntos débiles / Riesgos:**
- **Falta de umbrales para el balance de clases**:
    - **Problema**: El balance de clases es crítico para evitar *covariate shift* en el modelo, pero no hay un objetivo concreto (ej: "60% benigno / 40% malicioso").
    - **Recomendación**:
        - Definir un **rango aceptable** (ej: 50–70% benigno) y alertar si el corpus se desvía.

- **Tensión entre retención y escalabilidad**:
    - **Problema**: Retener **todo** el grafo (incluyendo flujos inyectados) puede llevar a un **crecimiento inmanejable** en producción.
    - **Recomendación**:
        - Implementar un **mecanismo de archivado automático** (ej: flujos >90 días se mueven a un grafo histórico o a un data lake como Parquet).
        - Usar **compresión de aristas** para flujos correlacionados (ej: agrupar flujos de la misma sesión en un meta-nodo).

---

---

### **🔐 §3.1. Identidad de Flujo: `flow_uid`**
**✅ Fortalezas:**
- **Codificación canónica con BLAKE2b (libsodium)**:
    - **Correcto**: Usar `crypto_generichash` (BLAKE2b) de libsodium **garantiza consistencia cross-implementación** (C++/Python) y evita dependencias externas.
    - **Ventaja**: BLAKE2b es **rápido, seguro y resistente a colisiones** (mejor que SHA-1/2 para este uso).

- **`node_id` como identidad de corpus estable (§3.1.2)**:
    - **Solución elegante**: Separar `node_id` (estable, basado en `declared_sensor_id + deployment_epoch`) de la **keypair efímera** (para firmar eventos) resuelve el problema de **reproducibilidad en EMECAS++** (`vagrant destroy+up`).
    - **Ejemplo**:
      ```python
      node_id = base64(H("argus-sensor-gw-lan-01" + "\x00" + str(deployment_epoch)))
      ```
        - `deployment_epoch` solo cambia en **despliegues deliberados** (no en rebuilds de desarrollo).

- **`seq_in_window` transportado en el evento (§3.1.4)**:
    - **Correcto**: Evita recomputar el contador en el correlation-engine, lo que **garantiza reproducibilidad** incluso con reordenamiento de paquetes o drops en el ring buffer.

- **`sensor_native_flow_id` como propiedad de trazabilidad (§3.1.4)**:
    - **Correcto**: No incluirlo en el `flow_uid` evita problemas de **colisión con históricos** (Suricata reinicia `flow_id`) y **normalización entre herramientas** (Zeek usa `string`, Suricata `uint64`).

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de `deployment_epoch`**:
    - **Problema**: ¿Cómo se gestiona `deployment_epoch`? ¿Es un contador global? ¿Se incrementa manualmente?
    - **Recomendación**:
        - Definir `deployment_epoch` como un **timestamp Unix** (ej: `1717200000` para el despliegue del DAY 173).
        - Almacenarlo en un **archivo de configuración persistente** (ej: `/etc/argus/deployment_epoch`).

- **Validación de `N` por protocolo**:
    - **Problema**: El default de **60s para TCP/UDP** puede no ser óptimo para todos los entornos.
    - **Recomendación**:
        - **Calibrar `N` empíricamente** sobre un *golden pcap* de producción:
            1. Extraer todos los flujos y calcular el **tiempo medio entre reutilizaciones de 5-tuplas** por protocolo.
            2. Elegir `N` como el **percentil 1** de esta distribución (ej: TCP = 120s, UDP = 30s).

---

---

### **🔗 §3.2. Correlación Host↔Red**
**✅ Fortalezas:**
- **Definición de `agent_id` (§3.2.3)**:
    - **Correcto**: Usar `hostname + domain + os_uuid` garantiza **estabilidad bajo DHCP/contenedores**.
    - **Ejemplo**:
      ```python
      agent_id = base64(H("host1.example.com" + "\x00" + "linux" + "\x00" + "a1b2c3d4..."))
      ```

- **Coincidencia temporal asimétrica en *event time* (§3.2.2)**:
    - **Correcto**: Usar **watermark** (estándar en stream processing) para manejar eventos de host atrasados (ej: logs de Wazuh bufferizados).
    - **Ventaja**: Evita problemas con *processing time* (latencia variable en el pipeline).

- **Resolución de conflictos NAT (§3.2.1)**:
    - **Correcto**: Usar **mayoría ponderada por confianza** y etiquetar `CONFLICT_NAT` cuando hay discrepancia.
    - **Impacto en IPW**: Asignar **peso nulo o penalizado** a flujos con `CONFLICT_NAT` evita contaminar el modelo.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de `nat_confidence_floor`**:
    - **Problema**: ¿Cómo se calibra `nat_confidence_floor`?
    - **Recomendación**:
        - Usar **escenarios MITRE etiquetados** para medir la precisión de cada método NAT.
        - Ejemplo:
          | Método               | Precisión en MITRE | `nat_confidence_floor` |
          |----------------------|--------------------|------------------------|
          | Translation node     | 99%                | 95                     |
          | `agent_id`/hostname   | 95%                | 90                     |
          | (proceso, puerto)    | 80%                | 70                     |
          | Fallback temporal    | 50%                | 40                     |

- **Falta de manejo de DHCP en `agent_id`**:
    - **Problema**: Si un host cambia de `hostname` (ej: en DHCP), el `agent_id` cambiará.
    - **Recomendación**:
        - Usar **`os_uuid` como clave principal** (ej: `/etc/machine-id` en Linux, que es estable incluso con DHCP).
        - Ejemplo:
          ```python
          agent_id = base64(H(os_uuid + "\x00" + hostname + "\x00" + domain))
          ```

---

---

### **🛡️ §3.3–§3.5. Modelo de Amenaza y Defensas**
**✅ Fortalezas:**
- **Vectores A y B ampliados (§3.3)**:
    - **Correcto**: Incluir **rogue gateway, DNS poisoning, BGP hijack, TCP hijack, y mismatches TLS** en el vector A cubre **todos los niveles de la pila OSI**.
    - **Ejemplo de ataque**: Un atacante que usa **BGP hijacking** para redirigir tráfico no cambiará la MAC, pero sí la ruta (L3).

- **Tres líneas de defensa (§3.4)**:
    - **`flow_uid` + mapa de cobertura**: Anti-inyección (vector B).
    - **Correlación host↔red + señales TCP/TLS**: Anti-MITM (vector A).
    - **`community_id.orphan_rate`**: Detección de sensores comprometidos.
    - **Cobertura completa**: Cada vector tiene su propia defensa.

- **Límite fundamental del vector A (§3.4.1)**:
    - **Correcto**: Documentar que **el vector A con host comprometido es indetectable sin fuente out-of-band** (ej: switch con port-security) es **honesto y necesario** para la validez científica del corpus.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de detección de MITM en L3 (BGP hijacking)**:
    - **Problema**: El modelo actual no incluye **señales de ruta** (ej: cambios en BGP).
    - **Recomendación**:
        - Añadir un **nodo `:BgpRoute`** en el grafo para rastrear cambios en la tabla de rutas.
        - Ejemplo:
          ```cypher
          (:BgpRoute {prefix: "192.168.1.0/24", as_path: "65001 65002", timestamp: t})
          -[:ANNOUNCED_BY]->(:Sensor {node_id: "sensor1"})
          ```

- **Falta de ejemplo de fuente out-of-band**:
    - **Problema**: ¿Qué fuentes out-of-band se usarán para detectar el vector A con host comprometido?
    - **Recomendación**:
        - **Switch con port-security**: Detecta cambios de MAC en puertos específicos.
        - **SPAN/TAP**: Captura tráfico pasivamente sin depender del host.
        - **Canary Host**: Host dedicado para detectar ataques (ej: honeypot).

---

---
### **📊 §3.6. Marca de Confianza y §3.8. Mapa de Cobertura**
**✅ Fortalezas:**
- **`trust_tier` como vista derivada**:
    - **Correcto**: Guardar **señales primitivas** (`witness_count`, `nat_confidence`, etc.) y derivar `trust_tier` como vista permite **flexibilidad futura**.
    - **Ejemplo de consulta**:
      ```cypher
      MATCH (f:NetworkFlow)
      WHERE f.witness_count >= 2 AND f.nat_confidence >= 80
      SET f.trust_tier = "CORROBORATED"
      ```

- **Score IPW continuo (§3.6)**:
    - **Correcto**: Usar `corroboration_count / expected_witnesses` (normalizado por el mapa de cobertura) evita **sesgo por cobertura no solapada**.
    - **Ejemplo**:
        - Si un segmento tiene **2 sensores** y un flujo es visto por **1 sensor**, `score = 1/2 = 0.5`.
        - Si el segmento tiene **1 sensor**, `score = 1/1 = 1.0` (no se penaliza).

- **Mapa de cobertura (§3.8)**:
    - **Correcto**: Usar una **tabla declarativa** (`node_id → {segmentos}`) con **validación por beacons** garantiza que la cobertura sea **predecible y auditables**.
    - **Ejemplo de estructura**:
      ```json
      {
        "sensor1": ["192.168.1.0/24", "10.0.0.0/16"],
        "sensor2": ["192.168.2.0/24"]
      }
      ```

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de `expected_witnesses`**:
    - **Problema**: ¿Cómo se calcula `expected_witnesses` para un flujo?
    - **Recomendación**:
        - Usar el **mapa de cobertura** para determinar qué sensores **deberían** haber visto el flujo.
        - Ejemplo:
          ```python
          expected_witnesses = len([s for s in sensors if flow.src_ip in s.segments])
          ```

- **Falta de actualización dinámica del mapa de cobertura**:
    - **Problema**: La topología de red puede cambiar (ej: nuevos sensores, fallos de NIC).
    - **Recomendación**:
        - Usar **beacons/heartbeats** para validar la cobertura en tiempo real.
        - Ejemplo:
          ```bash
          # Beacon desde el correlation-engine
          ping -c 1 192.168.1.1  # Verificar que sensor1 ve este segmento
          ```

---

---
### **🏷️ §3.7. Etiquetado de Procedencia**
**✅ Fortalezas:**
- **Dos campos ortogonales**:
    - **`provenance_suspected`**: Heurística de runtime (ej: `orphan_rate` alto).
    - **`provenance_ground_truth`**: Verdad de escenario (manifiesto MITRE).
    - **Correcto**: Evita **sesgo de confirmación** (no se usa la salida del detector para validar al detector).

- **WAL externo con hash-chain (§3.7)**:
    - **Correcto**: Usar un **WAL append-only** (soportado por etcd HA, ADR-048) garantiza **no-repudio** y **auditabilidad**.
    - **Ejemplo de estructura del WAL**:
      ```json
      {
        "offset": 12345,
        "timestamp": 1717200000,
        "flow_uid": "abc123",
        "tag": "INJECTED",
        "method": "MITRE_GROUND_TRUTH",
        "source": "ADR-050-SESSION-1",
        "hash_prev": "a1b2c3...",  # Hash del bloque anterior
        "hash_current": "d4e5f6..."  # Hash de este bloque
      }
      ```

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de consulta para validar el WAL**:
    - **Problema**: ¿Cómo se valida que el grafo contiene todas las entradas del WAL?
    - **Recomendación**:
        - Implementar un **test de integridad** que compare el WAL con el grafo:
          ```cypher
          // Contar flujos etiquetados como INJECTED en el grafo
          MATCH (f:NetworkFlow)-[:TAGGED_AS]->(t:Tag {label: "INJECTED"})
          RETURN count(f) AS injected_in_graph
    
          // Contar entradas INJECTED en el WAL (ej: consulta a etcd)
          // Deberían ser iguales
          ```

- **Falta de manejo de conflictos en el WAL**:
    - **Problema**: ¿Qué pasa si dos procesos intentan etiquetar el mismo flujo simultáneamente?
    - **Recomendación**:
        - Usar **transacciones atómicas** en el WAL (etcd soporta esto nativamente con Raft).

---

---
### **📡 §3.9. Señal ARP/NDP y §3.11. Señales TCP/TLS**
**✅ Fortalezas:**
- **Nodo `:IpMacBinding` (§3.9)**:
    - **Correcto**: Modelar el **estado de binding IP↔MAC** (no paquetes individuales) evita inundar el grafo.
    - **Ejemplo de detección de MITM**:
      ```cypher
      MATCH (b1:IpMacBinding {ip: "192.168.1.10", mac: "00:11:22:33:44:55", valid_to: t1})
      MATCH (b2:IpMacBinding {ip: "192.168.1.10", mac: "aa:bb:cc:dd:ee:ff", valid_from: t2})
      WHERE t2 > t1
      RETURN b1, b2 AS ReBindingDetected
      ```

- **Señales TCP/TLS (§3.11)**:
    - **Correcto**: Incluir **RST inesperados, saltos de `seq_num`, y mismatches TLS** cubre el **vector A ampliado** (L4/L7).
    - **Ejemplo de nodo `:HostAnomaly`**:
      ```cypher
      (:HostAnomaly {
        agent_id: "host1.example.com",
        type: "TLS_MISMATCH",
        expected_cert: "CN=example.com",
        presented_cert: "CN=attacker.com",
        timestamp: 1717200000
      })
      -[:DETECTED_IN]->(:NetworkFlow {flow_uid: "abc123"})
      ```

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de integración con Wazuh/osquery**:
    - **Problema**: ¿Cómo se recogen las señales TCP/TLS?
    - **Recomendación**:
        - Usar **osquery** para monitorizar:
            - **RST TCP**: `SELECT * FROM kernel_events WHERE event_type = 'TCP_RST';`
            - **Mismatches TLS**: `SELECT * FROM tls_connections WHERE certificate_subject != expected_subject;`

- **Falta de manejo de falsos positivos en señales TCP/TLS**:
    - **Problema**: Algunas aplicaciones legítimas pueden generar RST o mismatches TLS (ej: balanceadores de carga).
    - **Recomendación**:
        - Usar una **lista blanca** de IPs/puertos conocidos (ej: balanceadores de carga).
        - Ejemplo:
          ```cypher
          MATCH (f:NetworkFlow {dst_ip: "192.168.1.100", dst_port: 443})
          WHERE NOT (f.dst_ip IN ["192.168.1.100", "10.0.0.1"])  # IPs de balanceadores
          RETURN f
          ```

---

---
### **⚖️ §3.10. Rate-Limit de Cardinalidad**
**✅ Fortalezas:**
- **Cardinalidad exacta para la etiqueta (§3.10)**:
    - **Correcto**: Usar **contadores exactos** (no estructuras probabilísticas como HyperLogLog) para decidir si etiquetar un flujo como `rate_limited`.
    - **Ejemplo**:
      ```python
      # Pseudocódigo en el correlation-engine
      if new_cid_count[node_id][window] > max_new_cid_per_window_per_node[node_id]:
          flow.rate_limited = True
      ```

- **Meta-nodo para flujos rate-limitados**:
    - **Correcto**: Agrupar flujos en un `:HighCardinalityFlowCluster` permite **analizar el ataque** sin perder información.
    - **Ejemplo**:
      ```cypher
      (:HighCardinalityFlowCluster {
        start_time: 1717200000,
        end_time: 1717200060,
        node_id: "sensor1",
        cardinality: 10000,
        sample_flow_uids: ["abc123", "def456", ...]
      })
      ```

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de `max_new_cid_per_window_per_node`**:
    - **Problema**: ¿Cómo se calcula el umbral adaptativo?
    - **Recomendación**:
        - Usar el **percentil 99** de la cardinalidad histórica por nodo.
        - Ejemplo:
          ```python
          baseline = np.percentile(historical_cardinalities[node_id], 99)
          max_new_cid_per_window_per_node[node_id] = baseline * 1.5  # Margen de seguridad
          ```

- **Falta de acción para flujos `rate_limited`**:
    - **Problema**: ¿Qué se hace con los flujos etiquetados como `rate_limited`?
    - **Recomendación**:
        - **Alertar en tiempo real** (ej: enviar a un SIEM como Splunk).
        - **Incluirlos en el corpus** (para entrenar modelos contra ataques de flooding).

---

---
---
## **📌 Respuestas a las Preguntas Implícitas y Recomendaciones Finales**
---

### **1. ¿Está listo el ADR-052 v3 para ratificación?**
**✅ Sí, con las siguientes salvedades:**
- **El diseño es técnicamente sólido** y aborda todos los problemas identificados en v1/v2.
- **Las decisiones de arbitraje (N1–N12) son correctas** y están bien justificadas.
- **Las métricas de calidad del corpus (§0.1) son un gran avance** para garantizar la validez científica del dataset.

**⚠️ Salvedades menores (no bloqueantes):**
| **Tema** | **Recomendación** | **Prioridad** |
|----------|-------------------|---------------|
| Calibración de `N` por protocolo | Validar con *golden pcap* de producción | Alta |
| Definición de `nat_confidence_floor` | Usar escenarios MITRE para calibrar | Media |
| Manejo de DHCP en `agent_id` | Priorizar `os_uuid` sobre `hostname` | Media |
| Validación del WAL vs. grafo | Implementar test de integridad | Alta |
| Señales L3 (BGP) | Añadir como DEBT para v4 | Baja |

---

### **2. ¿Qué preguntas quedan abiertas?**
El ADR-052 v3 **resuelve todas las preguntas de la v2**, pero hay **dos temas nuevos** que podrían requerir aclaración:

#### **🔹 Pregunta 1: ¿Cómo se garantiza la sincronización del `deployment_epoch`?**
- **Contexto**: El `node_id` depende de `deployment_epoch`, que debe ser **consistente en todos los sensores** de un despliegue.
- **Recomendación**:
    - Usar un **servicio centralizado** (ej: etcd) para almacenar `deployment_epoch`.
    - Ejemplo:
      ```bash
      # Al desplegar
      deployment_epoch=$(date +%s)
      etcdctl put /argus/deployment_epoch $deployment_epoch
      ```
    - Los sensores leen `deployment_epoch` al iniciar.

#### **🔹 Pregunta 2: ¿Cómo se maneja el *drift* de reloj en el *event time*?**
- **Contexto**: El `flow_start_window` y las ventanas de correlación dependen de **timestamps precisos**.
- **Recomendación**:
    - Usar **NTP con alta precisión** (ej: `chrony` con fuentes estratum 1).
    - **Tolerancia de skew**: Ajustar las ventanas de correlación (±5s) para manejar *drift* residual.
    - Ejemplo:
      ```python
      # En el correlation-engine
      if abs(sensor_clock - engine_clock) > 5s:
          log_warning("Clock skew detected, adjusting windows")
      ```

---

### **3. Recomendaciones para la Implementación**
| **Tarea** | **Descripción** | **Responsable** | **Plazo** | **Prioridad** |
|-----------|-----------------|-----------------|-----------|---------------|
| Implementar `node_id` estable | Usar `declared_sensor_id + deployment_epoch` | Equipo de Sensores | 1 semana | **P0** |
| Implementar `flow_uid` con BLAKE2b | Usar `crypto_generichash` de libsodium | Equipo de Sensores | 1 semana | **P0** |
| Implementar WAL externo | Usar etcd HA (ADR-048) para etiquetado | Equipo de Correlación | 2 semanas | **P0** |
| Implementar mapa de cobertura | Tabla declarativa + validación por beacons | Equipo de Red | 2 semanas | **P0** |
| Calibrar `N` por protocolo | Usar *golden pcap* de producción | Equipo de QA | 1 semana | **P1** |
| Implementar señales TCP/TLS | Integración con Wazuh/osquery | Equipo de Host Plane | 3 semanas | **P1** |
| Validar paridad `flow_uid` | Test C++/Python con misma libsodium | Equipo de Testing | 1 semana | **P0** |
| Implementar rate-limit exacto | Contadores exactos en correlation-engine | Equipo de Correlación | 2 semanas | **P1** |

---

---
---
## **🎯 Resumen Ejecutivo y Voto de Ratificación**
---

### **📊 Evaluación General**
| **Criterio** | **Evaluación** | **Notas** |
|--------------|----------------|-----------|
| **Alineación con §0 (Misión Primaria)** | ✅ **Excelente** | Todas las decisiones priorizan el corpus sobre la correlación en vivo. |
| **Diseño Técnico** | ✅ **Sólido** | `flow_uid`, `node_id`, WAL, mapa de cobertura, señales TCP/TLS están bien diseñados. |
| **Resolución de Preguntas Abiertas** | ✅ **Completa** | Todas las preguntas de v2 están resueltas. |
| **Implementabilidad** | ✅ **Alta** | Las tareas están bien definidas y son realistas. |
| **Documentación** | ✅ **Detallada** | El ADR es claro, con ejemplos y justificaciones. |
| **Riesgos Residuales** | ⚠️ **Bajos** | Solo temas menores (calibración de `N`, manejo de DHCP). |

---

### **🗳️ Voto de Ratificación**
**✅ Recomendación: RATIFICAR ADR-052 v3**
con las siguientes **acciones post-ratificación**:
1. **Calibrar `N` por protocolo** (TCP/UDP) usando *golden pcap* de producción.
2. **Definir `nat_confidence_floor`** usando escenarios MITRE etiquetados.
3. **Implementar el WAL externo** (etcd HA) como **P0 bloqueante** antes de poblar el grafo.
4. **Validar la paridad de `flow_uid`** entre C++ y Python con la misma versión de libsodium.
5. **Abrir DEBT para señales L3 (BGP)** en ADR-053.

---
---
### **🔥 Conclusión Final**
El **ADR-052 v3 es un documento maduro, técnicamente riguroso y alineado con la misión del proyecto**. Resuelve todos los problemas identificados en versiones anteriores, incorpora las decisiones de arbitraje de manera coherente, y añade mejoras críticas como el **WAL externo** y las **señales TCP/TLS**. **Está listo para ratificación**, con acciones claras para su implementación.

**Pregunta final para el Consejo:**
---
**¿Están de acuerdo con:**
1. **Ratificar el ADR-052 v3** con las acciones post-ratificación propuestas?
2. **Priorizar la implementación del WAL externo (etcd HA) y la calibración de `N` por protocolo** como P0?
3. **Abrir un DEBT para señales L3 (BGP) en ADR-053**?

FDO
MISTRAL