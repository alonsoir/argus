El **ADR-052 v3.1** es una versión **madura, técnica y alineada con la misión primaria del proyecto**, que resuelve todas las ambigüedades y problemas identificados en versiones anteriores. Además, incorpora **correcciones críticas** (C1–C4) que refuerzan la **reproducibilidad del corpus**, la **estabilidad de la identidad de flujo**, y la **integridad del etiquetado**. A continuación, presento un análisis detallado, **respuestas a las preguntas implícitas**, y una **recomendación final de ratificación** con acciones concretas.

---

---

## **🔍 Análisis por Sección Clave (v3.1)**
---

---

### **🎯 §0. Misión Primaria y §0.1 Métricas de Calidad del Corpus**
**✅ Fortalezas:**
- **Principio ordenador claro y accionable**:
  La distinción entre **corpus de entrenamiento** (producto principal) y **correlación en vivo** (beneficio secundario) está **perfectamente justificada**. Esto alinea todas las decisiones técnicas bajo el principio de que **la integridad del corpus es prioritaria**.
    - **Ejemplo de impacto**: La decisión de usar un **WAL externo con hash-chain** (§3.7) para el etiquetado garantiza **auditabilidad científica** del corpus, algo crítico para el entrenamiento de modelos de ML.

- **Métricas de calidad del corpus (§0.1)**:
  Los KPIs propuestos son **medibles, relevantes y alineados con la misión**. Destacan:
    - **% flujos con `provenance_ground_truth` validado**: >90% en escenarios MITRE.
    - **% flujos con `witness_count ≥ 2`**: >70% en segmentos de cobertura solapada.
    - **Tiempo de reconstrucción de `flow_uid` desde pcap**: <1s.
    - **Cobertura de técnicas MITRE ATT&CK**: Crecimiento por sesión.
    - **Balance de clases benigno/malicioso**: Documentado por dataset.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de umbrales para el balance de clases**:
    - **Problema**: El balance de clases es crítico para evitar *covariate shift*, pero no hay un objetivo concreto (ej: "60% benigno / 40% malicioso").
    - **Recomendación**:
        - Definir un **rango aceptable** (ej: 50–70% benigno) y alertar si el corpus se desvía.
        - Incluir un **test automático** en EMECAS++ que valide el balance de clases.

- **Almacenamiento por niveles (N12)**:
    - **Problema**: La retención de todos los flujos puede llevar a un **crecimiento inmanejable** del grafo en producción.
    - **Recomendación**:
        - Implementar un **mecanismo de archivado automático** (ej: flujos >90 días se mueven a un grafo histórico o a un data lake como Parquet).
        - Usar **compresión de aristas** para flujos correlacionados (ej: agrupar flujos de la misma sesión en un meta-nodo).

---

---

### **🔐 §3.1. Identidad de Flujo: `flow_uid`**
**✅ Fortalezas:**
- **`node_id` como identidad de corpus estable (C1)**:
    - **Solución definitiva**: Eliminar `deployment_epoch` y usar un **identificador declarado y legible** (ej: `argus-sensor-gw-lan-01`) resuelve el problema de **reproducibilidad en EMECAS++** (`vagrant destroy+up`).
    - **Ventaja**: El `node_id` es **estable, auditable y legible**, lo que facilita el forense del corpus.
    - **Ejemplo**:
      ```python
      node_id = "argus-sensor-gw-lan-01"  # String canónico declarado en el inventario
      ```

- **Codificación canónica con BLAKE2b (libsodium)**:
    - **Correcto**: Usar `crypto_generichash` (BLAKE2b) de libsodium **garantiza consistencia cross-implementación** (C++/Python) y evita dependencias externas.
    - **Test de paridad**: Validar que C++ y Python producen el mismo `flow_uid` **y enlazan la misma versión de libsodium** es **crítico** para la reproducibilidad.

- **`seq_in_window` transportado en el evento (N2)**:
    - **Correcto**: Evita recomputar el contador en el correlation-engine, lo que **garantiza reproducibilidad** incluso con reordenamiento de paquetes o drops en el ring buffer.

- **`sensor_native_flow_id` como propiedad de trazabilidad (N3)**:
    - **Correcto**: No incluirlo en el `flow_uid` evita problemas de **colisión con históricos** (Suricata reinicia `flow_id`) y **normalización entre herramientas** (Zeek usa `string`, Suricata `uint64`).

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de validación de `node_id`**:
    - **Problema**: ¿Cómo se valida que un `node_id` es válido (ej: está en el inventario firmado)?
    - **Recomendación**:
        - Implementar un **test en EMECAS++** que verifique que todos los `node_id` en el grafo están registrados en el inventario de endpoints (ADR-046 §3.9).
        - Ejemplo:
          ```cypher
          MATCH (f:NetworkFlow)
          WHERE NOT EXISTS {
            MATCH (s:Sensor {node_id: f.node_id})
          }
          RETURN f.node_id AS invalid_node_id
          ```

- **Calibración de `N` por protocolo**:
    - **Problema**: El default de **60s para TCP/UDP** puede no ser óptimo para todos los entornos.
    - **Recomendación**:
        - **Calibrar `N` empíricamente** sobre un *golden pcap* de producción:
            1. Extraer todos los flujos y calcular el **tiempo medio entre reutilizaciones de 5-tuplas** por protocolo.
            2. Elegir `N` como el **percentil 1** de esta distribución (ej: TCP = 120s, UDP = 30s).
        - **Test en EMECAS++**:
          ```python
          def test_flow_start_window_calibration():
              pcap = load_golden_pcap()
              reuse_intervals_tcp = calculate_reuse_intervals(pcap, protocol="TCP")
              reuse_intervals_udp = calculate_reuse_intervals(pcap, protocol="UDP")
              assert np.percentile(reuse_intervals_tcp, 1) > 60  # Ajustar N si falla
              assert np.percentile(reuse_intervals_udp, 1) > 30
          ```

---

---

### **🔗 §3.2. Correlación Host↔Red**
**✅ Fortalezas:**
- **Definición de `agent_id` (N11)**:
    - **Correcto**: Usar `hostname + domain + os_uuid` garantiza **estabilidad bajo DHCP/contenedores**.
    - **Ejemplo**:
      ```python
      agent_id = base64(H("host1.example.com" + "\x00" + "example.com" + "\x00" + "a1b2c3d4..."))
      ```

- **Coincidencia temporal asimétrica en *event time* (N7)**:
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

---

---
### **📊 §3.6. Marca de Confianza**
**✅ Fortalezas:**
- **Separación de `trust_tier` y peso IPW (C3)**:
    - **Correcto**: Distinguir entre:
        - **`trust_tier`** (enum para queries/UI).
        - **Confianza por corroboración** (feature para el modelo, sube con testigos).
        - **Peso de de-duplicación** (para el sampler, baja con testigos).
    - **Ejemplo**:
      ```python
      # Confianza por corroboración (feature)
      corroboration_confidence = min(1.0, corroboration_count / expected_witnesses)
  
      # Peso de de-duplicación (sampler)
      dedup_weight = 1.0 / witness_count  # Baja con más testigos
      ```

- **Dependencia del mapa de cobertura (§3.8)**:
    - **Correcto**: `expected_witnesses` se calcula a partir del mapa de cobertura, lo que evita **sesgo por cobertura no solapada**.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de cálculo de `expected_witnesses`**:
    - **Problema**: ¿Cómo se calcula `expected_witnesses` para un flujo?
    - **Recomendación**:
        - Usar el **mapa de cobertura** para determinar qué sensores **deberían** haber visto el flujo.
        - Ejemplo:
          ```python
          expected_witnesses = len([s for s in sensors if flow.src_ip in s.segments])
          ```

---

---
### **🏷️ §3.7. Etiquetado de Procedencia**
**✅ Fortalezas:**
- **Dos campos ortogonales**:
    - **`provenance_suspected`**: Heurística de runtime (ej: `orphan_rate` alto).
    - **`provenance_ground_truth`**: Verdad de escenario (manifiesto MITRE).
    - **Correcto**: Evita **sesgo de confirmación** (no se usa la salida del detector para validar al detector).

- **WAL externo con hash-chain (C4)**:
    - **Correcto**: Usar un **WAL append-only** (soportado por etcd HA, ADR-048) garantiza **no-repudio** y **auditabilidad**.
    - **Estructura de la cadena**:
      ```json
      {
        "offset": 12345,
        "timestamp": 1717200000,
        "flow_uid": "abc123",
        "tag": "INJECTED",
        "method": "MITRE_GROUND_TRUTH",
        "source": "ADR-050-SESSION-1",
        "prev_hash": "a1b2c3...",  # Hash de la entrada anterior
        "hash_current": "d4e5f6..."  # Hash de esta entrada
      }
      ```
    - **Verificación periódica**: Un job programado recorre el WAL y valida la continuidad de `prev_hash`.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo de consulta para validar el WAL vs. grafo**:
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
    - **Separación de señales (C2)**:
        - **Anomalías TCP (RST/seq_num)**: **Ligeras**, entran sin reservas.
        - **Mismatch TLS**: **Requiere *cert-expectation store***, acotado a destinos gestionados con expectativa declarada.
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
- **Cardinalidad exacta para la etiqueta (N6)**:
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

---
---
---
## **📌 Respuestas a las Preguntas Implícitas y Recomendaciones Finales**
---

### **1. ¿Está listo el ADR-052 v3.1 para ratificación?**
**✅ Sí, con las siguientes salvedades:**
- **El diseño es técnicamente sólido** y aborda todos los problemas identificados en v1/v2/v3.
- **Las correcciones C1–C4 son críticas** y refuerzan la **reproducibilidad del corpus** y la **integridad del etiquetado**.
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
El ADR-052 v3.1 **resuelve todas las preguntas de la v2 y v3**, pero hay **dos temas nuevos** que podrían requerir aclaración:

#### **🔹 Pregunta 1: ¿Cómo se garantiza la sincronización del `node_id` en el inventario firmado?**
- **Contexto**: El `node_id` debe estar **registrado en el inventario de endpoints** (ADR-046 §3.9) y ser **consistente en todos los sensores** de un despliegue.
- **Recomendación**:
    - Usar un **servicio centralizado** (ej: etcd) para almacenar el inventario firmado.
    - Ejemplo:
      ```bash
      # Al desplegar un sensor
      etcdctl put /argus/inventory/sensors/argus-sensor-gw-lan-01 '{"node_id": "argus-sensor-gw-lan-01", "role": "gateway", "public_key": "..."}'
      ```
    - Los sensores leen el inventario al iniciar y validan su `node_id`.

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
---
### **3. Recomendaciones para la Implementación**
| **Tarea** | **Descripción** | **Responsable** | **Plazo** | **Prioridad** |
|-----------|-----------------|-----------------|-----------|---------------|
| Implementar `node_id` estable | Usar `declared_sensor_id` legible en inventario firmado | Equipo de Sensores | 1 semana | **P0** |
| Implementar `flow_uid` con BLAKE2b | Usar `crypto_generichash` de libsodium | Equipo de Sensores | 1 semana | **P0** |
| Implementar WAL externo | Usar etcd HA (ADR-048) para etiquetado | Equipo de Correlación | 2 semanas | **P0** |
| Implementar mapa de cobertura | Tabla declarativa + validación por beacons | Equipo de Red | 2 semanas | **P0** |
| Calibrar `N` por protocolo | Usar *golden pcap* de producción | Equipo de QA | 1 semana | **P1** |
| Implementar señales TCP/TLS | Integración con Wazuh/osquery | Equipo de Host Plane | 3 semanas | **P1** |
| Validar paridad `flow_uid` | Test C++/Python con misma libsodium | Equipo de Testing | 1 semana | **P0** |
| Implementar rate-limit exacto | Contadores exactos en correlation-engine | Equipo de Correlación | 2 semanas | **P1** |
| Implementar DEBT-LABEL-WAL-001 | WAL con hash-chain + verificación periódica | Equipo de Correlación | 2 semanas | **P1** |
| Implementar DEBT-CERT-EXPECTATION-STORE-001 | *Cert-expectation store* para TLS | Equipo de Seguridad | 4 semanas | **P2** |

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
| **Resolución de Preguntas Abiertas** | ✅ **Completa** | Todas las preguntas de v2/v3 están resueltas. |
| **Implementabilidad** | ✅ **Alta** | Las tareas están bien definidas y son realistas. |
| **Documentación** | ✅ **Detallada** | El ADR es claro, con ejemplos y justificaciones. |
| **Riesgos Residuales** | ⚠️ **Bajos** | Solo temas menores (calibración de `N`, manejo de DHCP). |

---

### **🗳️ Voto de Ratificación**
**✅ Recomendación: RATIFICAR ADR-052 v3.1**
con las siguientes **acciones post-ratificación**:
1. **Calibrar `N` por protocolo** (TCP/UDP) usando *golden pcap* de producción.
2. **Definir `nat_confidence_floor`** usando escenarios MITRE etiquetados.
3. **Implementar el WAL externo** (etcd HA) como **P0 bloqueante** antes de poblar el grafo.
4. **Validar la paridad de `flow_uid`** entre C++ y Python con la misma versión de libsodium.
5. **Abrir DEBT para señales L3 (BGP)** en ADR-053.
6. **Implementar DEBT-CERT-EXPECTATION-STORE-001** para habilitar el mismatch TLS en destinos gestionados.

---
---
### **🔥 Conclusión Final**
El **ADR-052 v3.1 es un documento maduro, técnicamente riguroso y alineado con la misión del proyecto**. Resuelve todos los problemas identificados en versiones anteriores, incorpora las **correcciones críticas C1–C4**, y añade mejoras clave como el **WAL externo con hash-chain** y la **separación de señales TCP/TLS**. **Está listo para ratificación**, con acciones claras para su implementación.

---
---
### **📝 Pregunta Final para el Consejo**
**¿Están de acuerdo con:**
1. **Ratificar el ADR-052 v3.1** con las acciones post-ratificación propuestas?
2. **Priorizar la implementación del WAL externo (etcd HA) y la calibración de `N` por protocolo** como P0?
3. **Abrir DEBT-CERT-EXPECTATION-STORE-001** para habilitar el mismatch TLS en destinos gestionados?

FDO

MISTRAL