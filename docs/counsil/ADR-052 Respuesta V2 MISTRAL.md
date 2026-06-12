El **ADR-052 v2** es un avance significativo respecto a la v1, con una **misión primaria clara** (§0) que alinea todas las decisiones técnicas bajo el principio de que **el grafo es un corpus de entrenamiento, no solo un sistema de correlación en vivo**. Esto resuelve muchas ambigüedades y refuerza la coherencia del diseño. A continuación, mi análisis estructurado, **puntos fuertes, débiles, respuestas a las preguntas abiertas (v2)**, y recomendaciones accionables para el Consejo.

---

---

## **🔍 Análisis por Sección Clave**

---

### **🎯 §0. Misión Primaria: El Corpus como Producto**
**✅ Fortalezas:**
- **Principio ordenador claro**: El grafo existe para **producir un corpus de entrenamiento enriquecido y trazable**, no solo para correlación en vivo. Esto es **revolucionario** en el contexto de sistemas de detección, ya que prioriza la **integridad científica** sobre la operatividad inmediata.
    - **Ejemplo de alineación**: La decisión de **etiquetar (no borrar) flujos inyectados** (§3.7) es coherente con la necesidad de retener *ground truth* para entrenar modelos robustos (similar a cómo [MITRE ATT&CK](https://attack.mitre.org/) incluye técnicas adversarias en sus datasets).
    - **Conexión con ADR-040**: El uso de **Inverse Probability Weighting (IPW)** para ajustar sesgos en el corpus (ej: flujos observados por un solo sensor) es una práctica estándar en *causal inference* (ej: [Hernán & Robins, 2020](https://www.hsph.harvard.edu/miguel-hernan/causal-inference-book/)).

- **Invariante de proyecto**:
  > *"El grafo de aRGus es, antes que nada, un corpus de entrenamiento que además hace correlación en vivo. Cuando ambos fines chocan, ganan la retención y la integridad de la etiqueta."*
    - Esto resuelve el **dilema clásico en SIEMs**: ¿filtrar ruido (operatividad) o retenerlo (entrenamiento)? La respuesta aquí es **retener y etiquetar**, lo que es **correcto para ML adversarial** (ej: [Goodfellow et al., 2015](https://arxiv.org/abs/1412.6572)).

**⚠️ Puntos débiles / Riesgos:**
- **Falta de métricas de calidad del corpus**:
    - ¿Cómo se medirá la **calidad del corpus**? Por ejemplo:
        - **Cobertura de técnicas MITRE**: ¿Qué % de técnicas ATT&CK están representadas en el corpus?
        - **Balance de clases**: ¿Hay suficiente representación de flujos benignos vs. maliciosos?
        - **Trazabilidad**: ¿Se puede reconstruir el 100% de los flujos desde los pcaps originales?
    - **Recomendación**:
        - Añadir un **§0.1: Métricas de Calidad del Corpus** con KPIs como:
            - `% de flujos con `provenance_ground_truth` validado (objetivo: >90%).`
            - `% de flujos con `witness_count >= 2` (objetivo: >70%).`
            - `Tiempo medio de reconstrucción de un flujo desde pcap (objetivo: <1s).`

- **Tensión entre correlación en vivo y corpus**:
    - En la práctica, **el grafo puede crecer demasiado** si se retiene todo. Por ejemplo, en un entorno con 10K flujos/segundo, el grafo podría alcanzar **millones de nodos/día**.
    - **Recomendación**:
        - Implementar un **mecanismo de archivado automático** (ej: flujos >30 días se mueven a un grafo histórico en Neo4j o a un data lake como Parquet).
        - Usar **compresión de aristas** para flujos correlacionados (ej: agrupar flujos de la misma sesión en un meta-nodo).

---

---

### **🔐 §3.1. Identidad de Flujo: `flow_uid`**
**✅ Fortalezas:**
- **Codificación canónica (§3.1.1)**:
    - La fórmula `flow_uid = base64(SHA3-256(utf8(node_id) ‖ 0x00 ‖ utf8(community_id) ‖ 0x00 ‖ uint64_be(flow_start_window)))` es **determinista, reproducible y resistente a colisiones**.
    - **SHA3-256** es una elección sólida (resistente a *length-extension attacks*, a diferencia de SHA-1/2).
    - **Test de paridad cross-implementación** (C++/Python) es **crítico** para evitar inconsistencias en el corpus.

- **Definición de `node_id` (§3.1.2)**:
    - `node_id = base64(SHA256(sensor_public_key))` es **inmutable, único y verificable**, alineado con **ADR-027** (identidad criptográfica).
    - **Ventaja**: Permite **firmar flujos** en el futuro (ej: el sensor podría firmar el `flow_uid` para probar su origen).

- **Aclaración de `node_id` ≠ correlación cross-nodo (§3.1.3)**:
    - **Consenso correcto**: Dos sensores que ven el mismo flujo **deben tener `flow_uid` distintos** (por diseño). La correlación se hace vía `community_id` (arista `FLOW_IDENTITY`).
    - Esto resuelve el **"Box-Car Problem"** (Gemini/Qwen): el *skew* de reloj solo afecta a la correlación, no a la identidad.

- **`flow_start_window` (§3.1.4)**:
    - **Decisión de usar buckets fijos** (no `CrisisWindow`) es **correcta** porque:
        - Es **reproducible offline** (requisito §0).
        - Evita depender de estado dinámico (ej: `CrisisWindow` podría cambiar entre sensores).
    - **`seq_in_window`** para evitar colisiones UDP es **elegante y minimalista**.
    - **Default de 60s** es razonable (cubre el `TIME-WAIT` de TCP).

**⚠️ Puntos débiles / Mejoras:**
- **`flow_start_window` y flujos de larga duración**:
    - **Problema**: Flujos persistentes (ej: SSH, VPN) podrían generar **múltiples `flow_uid`** si se extienden más de un bucket.
    - **Recomendación**:
        - Usar **`flow_start_window` solo para el primer paquete del flujo** (evento de inicio). Los paquetes posteriores **referencian el `flow_uid` inicial** (no generan nuevos).
        - Ejemplo:
          ```cypher
          (:NetworkFlow {flow_uid: "abc123", flow_start_window: 1717200000})
          -[:CONTINUES]->(:NetworkFlow {flow_uid: "abc123", flow_start_window: 1717200060})
          ```
        - Esto evita fragmentar flujos legítimos.

- **`sensor_native_flow_id` (§3.1.4.4)**:
    - **Problema**: Suricata y Zeek ya tienen sus propios `flow_id`/`uid`. ¿Cómo se integran?
    - **Recomendación**:
        - **Priorizar `sensor_native_flow_id` sobre `(flow_start_window ‖ seq_in_window)`** cuando esté disponible.
        - Para el sniffer propio de aRGus, usar el mecanismo de buckets + `seq_in_window`.

- **Validación de `N` (60s)**:
    - **Riesgo**: 60s podría ser **demasiado corto** para entornos con alta reutilización de puertos (ej: contenedores efímeros).
    - **Recomendación**:
        - **Calibrar `N` empíricamente** sobre un *golden pcap* de producción:
            1. Extraer todos los flujos y calcular el **tiempo medio entre reutilizaciones de 5-tuplas** en el mismo nodo.
            2. Elegir `N` como el **percentil 1** de esta distribución (ej: si el 99% de los reciclajes ocurren después de 120s, usar `N=120s`).

---

---

### **🔗 §3.2. Correlación Host↔Red**
**✅ Fortalezas:**
- **Doble arista (flujo↔flujo y host↔flujo)**:
    - **Flujo↔flujo**: Por `community_id` (determinista, cross-sensor).
    - **Host↔flujo**: Por `agent_id` + **coincidencia temporal asimétrica** (5s red→host, 30s host→red).
    - Esto es **coherente con modelos de grafos en ciberseguridad** (ej: [Microsoft’s Cyber Battle Simulation](https://www.microsoft.com/en-us/research/publication/cyberbattle-simulation/)).

- **Manejo de NAT (§3.2.1)**:
    - **Menú de mecanismos** con anotación de confianza es **práctico y realista**.
    - **Resolución de conflictos**: Usar **mayoría ponderada por confianza** es una solución robusta.
    - **`CONFLICT_NAT`**: Etiquetar (no fallar silenciosamente) es **correcto para el corpus**.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de ejemplo concreto de `agent_id`**:
    - ¿Cómo se construye el `agent_id` canónico? ¿Es un UUID generado por Wazuh? ¿O un hash de `hostname + domain`?
    - **Recomendación**:
        - Definir `agent_id` como:
          ```python
          agent_id = SHA256(hostname + "|" + domain + "|" + os_uuid)
          ```
          donde `os_uuid` es un identificador único del sistema (ej: `/etc/machine-id` en Linux).

- **Ventanas temporales asimétricas**:
    - **Problema**: 5s (red→host) podría ser **demasiado corto** si hay latencia en la red.
    - **Recomendación**:
        - Usar **ventanas dinámicas** basadas en la latencia medida entre sensores y hosts.
        - Ejemplo:
            - Medir el **RTT medio** entre el sensor de red y el host (ej: 10ms).
            - Ajustar la ventana como `RTT * 10` (ej: 100ms para red→host).

- **Falta de manejo de DHCP**:
    - **Problema**: En redes con DHCP, la IP de un host puede cambiar, rompiendo la correlación.
    - **Recomendación**:
        - Usar **`agent_id` + `mac_address`** como clave principal para la correlación host↔flujo.
        - Ejemplo:
          ```cypher
          (:Host {agent_id: "abc", mac: "00:11:22:33:44:55"})
          -[:OBSERVED]->(:NetworkFlow {flow_uid: "xyz", src_ip: "192.168.1.10"})
          ```

---

---

### **🛡️ §3.3–§3.5. Modelo de Amenaza y Defensas**
**✅ Fortalezas:**
- **Vectores A y B claramente diferenciados**:
    - **Vector A (MITM)**: Ciego al `community_id` (MAC no está en el hash).
    - **Vector B (Inyección)**: Manipulable (5-tupla falsa → `community_id` falso).
    - Esto alinea con el **principio de defensa en profundidad** (ej: [NIST SP 800-53](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)).

- **Tres líneas de defensa**:
    1. **`flow_uid` + `node_id`**: Anti-inyección (vector B).
    2. **Correlación host↔red**: Anti-MITM (vector A).
    3. **`community_id.orphan_rate`**: Detección de sensores comprometidos.
    - **Cobertura completa**: Cada vector tiene su propia defensa.

- **Límite fundamental del vector A (§3.4.1)**:
    - **Correcto**: Si el host está comprometido, el vector A es **indetectable sin una fuente out-of-band** (ej: switch con port-security).
    - **Honestidad intelectual**: Documentar este límite es **clave para la validez científica del corpus**.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de detección de MITM en L3/L4**:
    - **Problema**: El modelo actual solo detecta MITM en L2 (ARP/NDP). Pero MITM también puede ocurrir en L3 (ej: BGP hijacking) o L4 (ej: TCP session hijacking).
    - **Recomendación**:
        - Añadir **señales adicionales** para detectar MITM en otras capas:
            - **L3**: Cambios en la ruta (ej: `traceroute` anómalo).
            - **L4**: Anomalías en el estado TCP (ej: RST inesperados, saltos en `seq_num`).
            - **L7**: Mismatches en certificados TLS (ej: certificado no esperado).

- **`orphan_rate` y cobertura de sensores**:
    - **Problema**: `orphan_rate` es **ruidoso** si no se tiene en cuenta el **mapa de cobertura** (§3.8).
    - **Recomendación**:
        - Definir `orphan_rate` como:
          ```
          orphan_rate = (número de community_id únicos emitidos por el sensor NO vistos por otros sensores en su área de cobertura)
                        / (número total de community_id únicos emitidos por el sensor)
          ```
        - **Umbral**: Marcar como sospechoso si `orphan_rate > 0.95` (ajustable).

---

---
### **📊 §3.6. Marca de Confianza: *Features* del Corpus**
**✅ Fortalezas:**
- **Enfoque correcto**: La confianza no es un veredicto opaco, sino **features para el modelo** (alineado con ADR-040 y IPW).
- **Propiedades primitivas**:
    - `witness_count` / `corroboration_count`.
    - `is_host_plane_anchored`.
    - `nat_resolution_method` + `nat_confidence`.
    - `orphan_rate` del sensor.
    - Esto permite **recomputar `trust_tier`** si la semántica evoluciona.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de definición de `trust_tier`**:
    - ¿Cómo se deriva `trust_tier` a partir de las primitivas?
    - **Recomendación**:
        - Definir una **tabla de decisión** clara. Ejemplo:

          | `witness_count` | `is_host_plane_anchored` | `nat_confidence` | `orphan_rate` | `trust_tier`       |
                |------------------|---------------------------|------------------|----------------|--------------------|
          | >= 2             | true                      | >= 80            | < 0.1          | `CORROBORATED`     |
          | 1                | true                      | >= 60            | < 0.5          | `SINGLE_SENSOR`    |
          | 1                | false                     | >= 60            | >= 0.5         | `ORPHAN`           |
          | Any              | Any                       | Any              | Any            | `CONFLICT_NAT`     |

- **Falta de peso IPW**:
    - **Problema**: ¿Cómo se usan estas features para calcular los **pesos IPW** (ADR-040)?
    - **Recomendación**:
        - Usar un modelo de **regresión logística** para predecir la probabilidad de que un flujo sea *ground truth* (basado en las primitivas).
        - El peso IPW para un flujo sería:
          ```
          weight = 1 / predicted_probability
          ```

---

---
### **🏷️ §3.7. Etiquetado de Procedencia**
**✅ Fortalezas:**
- **Dos campos ortogonales**:
    - `provenance_suspected`: Heurística de runtime (ej: `orphan_rate` alto).
    - `provenance_ground_truth`: Verdad de escenario (ej: manifiesto MITRE).
    - Esto evita **sesgo de confirmación** (no se usa la salida del detector para validar al detector).

- **Etiquetado como arista append-only**:
    - **Correcto**: Evita que un motor comprometido **des-etiquete** flujos maliciosos.
    - Ejemplo:
      ```cypher
      (:NetworkFlow)-[:TAGGED_AS {
        method: "MITRE_GROUND_TRUTH",
        source: "ADR-050-SESSION-1",
        timestamp: 1717200000,
        analyst: "auto"
      }]->(:Tag {label: "INJECTED"})
      ```

**⚠️ Puntos débiles / Mejoras:**
- **Falta de jerarquía de etiquetas**:
    - **Problema**: ¿Qué pasa si un flujo tiene **múltiples etiquetas conflictivas** (ej: `provenance_suspected: true` pero `provenance_ground_truth: false`)?
    - **Recomendación**:
        - Definir una **jerarquía de prioridad**:
            1. `provenance_ground_truth` (fuente: manifiesto MITRE).
            2. `provenance_suspected` (fuente: heurísticas).
            3. `trust_tier` (fuente: features).
        - En caso de conflicto, **la etiqueta de mayor prioridad prevalece**.

- **Falta de etiquetas para flujos benignos**:
    - **Problema**: El enfoque actual se centra en etiquetar flujos maliciosos (`INJECTED`, `MITM`), pero **no hay etiquetas para flujos benignos**.
    - **Recomendación**:
        - Añadir etiquetas como:
            - `BENIGN` (flujo normal).
            - `FALSE_POSITIVE` (flujo benigno marcado como malicioso por error).
            - `UNKNOWN` (flujo no clasificado).

---

---
### **🗺️ §3.8. Mapa de Cobertura de Sensores**
**✅ Fortalezas:**
- **Prerrequisito para la honestidad del corpus**:
    - Sin este mapa, **`orphan_rate` y los pesos IPW son ruido**.
    - Ejemplo: Un flujo visto por un solo sensor en una subred **no monitorizada por otros** no debe contar como `ORPHAN`.

**⚠️ Puntos débiles / Mejoras:**
- **Falta de diseño concreto**:
    - ¿Cómo se representa el mapa de cobertura? ¿Como un **grafo de topología** o una **tabla de adyacencia**?
    - **Recomendación**:
        - Usar un **grafo de topología** en Neo4j:
          ```cypher
          (:Sensor {node_id: "sensor1"})-[:MONITORS]->(:Subnet {cidr: "192.168.1.0/24"})
          (:Sensor {node_id: "sensor2"})-[:MONITORS]->(:Subnet {cidr: "192.168.2.0/24"})
          ```
        - **Ventaja**: Permite consultas como:
          ```cypher
          MATCH (s:Sensor {node_id: "sensor1"})-[:MONITORS]->(sub:Subnet)
          MATCH (f:NetworkFlow {src_ip: "192.168.1.10"})
          WHERE sub.cidr CONTAINS f.src_ip
          RETURN s, f
          ```
          para validar si un sensor **debería** haber visto un flujo.

- **Falta de actualización dinámica**:
    - **Problema**: La topología de red puede cambiar (ej: nuevos sensores, subredes).
    - **Recomendación**:
        - Implementar un **mecanismo de sincronización** con el inventario de endpoints (ADR-046 §3.9).
        - Usar **etcd** (ADR-048) para almacenar el mapa de cobertura y notificar cambios.

---

---
### **🔍 §3.9. Señal ARP/NDP**
**✅ Fortalezas:**
- **Nodo de primera clase**: Correcto, ya que permite consultas temporales y detección de cambios de estado.
- **Modelado como `:IpMacBinding`**:
    - Propiedades: `ip`, `mac`, `valid_from`, `valid_to`, `previous_mac`.
    - **Ventaja**: Permite detectar **re-bindings** (cambios de MAC para una IP), que son señal de MITM (vector A).

**⚠️ Puntos débiles / Mejoras:**
- **Falta de integración con Wazuh**:
    - **Problema**: ¿Cómo se recoge la señal ARP/NDP? ¿Wazuh emite eventos de cambio de MAC?
    - **Recomendación**:
        - Usar el **agente de Wazuh** para monitorizar la tabla ARP del host:
          ```bash
          arp -a | grep "192.168.1.1"
          ```
        - Emitir un evento cuando la MAC para una IP cambie.

- **Falta de detección de ARP spoofing pasivo**:
    - **Problema**: Un atacante puede **envenenar la caché ARP** sin generar tráfico (ej: enviando paquetes ARP gratuitos).
    - **Recomendación**:
        - Monitorizar **paquetes ARP gratuitos** (gratis ARP) en el sensor de red.
        - Ejemplo:
          ```python
          # Pseudocódigo para Suricata
          if packet.arp.op == "reply" and packet.arp.sender_ip == packet.arp.target_ip:
              emit_arp_spoofing_alert()
          ```

---

---
### **⚖️ §3.10. Rate-Limit de Cardinalidad**
**✅ Fortalezas:**
- **Enforcement en el correlation-engine**: Correcto, ya que Neo4j no debe ser el rate-limiter primario.
- **Umbral adaptativo**: Basado en **Count-Min Sketch / HyperLogLog** para estimar cardinalidad.
- **No se descarta evidencia**: Los flujos que superan el umbral se **etiquetan** (`rate_limited: true`) o se agrupan en un meta-nodo (`:HighCardinalityFlowCluster`).

**⚠️ Puntos débiles / Mejoras:**
- **Falta de definición de `baseline`**:
    - ¿Cómo se calcula la **baseline por nodo/rol**?
    - **Recomendación**:
        - Usar el **percentil 95** de la cardinalidad histórica por nodo.
        - Ejemplo:
          ```python
          baseline = np.percentile(historical_cardinalities, 95)
          ```
- **Falta de acción para flujos rate-limitados**:
    - **Problema**: ¿Qué se hace con los flujos etiquetados como `rate_limited`?
    - **Recomendación**:
        - **Agrupar en un meta-nodo** con propiedades:
          ```cypher
          (:HighCardinalityFlowCluster {
            start_time: 1717200000,
            end_time: 1717200060,
            node_id: "sensor1",
            cardinality: 10000,
            sample_flow_uids: ["abc123", "def456", ...]  # Muestra de flujos
          })
          ```
        - Esto permite **analizar el clustering** sin perder información.

---

---
---
## **📌 Respuestas a las Preguntas Abiertas (v2, §6)**

| **Pregunta** | **Respuesta** | **Justificación** |
|--------------|---------------|-------------------|
| **Q1: Ratificación de §3.1.3** | **Sí, ratificar.** Dos sensores NO deben compartir `flow_uid`. El skew solo amenaza el *match* de correlación, no la identidad. | **Consenso técnico**: El diseño actual es coherente con el principio de que cada observación es una muestra independiente para el corpus. |
| **Q2: Diseño del mapa de cobertura** | **Grafo de topología en Neo4j** (nodos `:Sensor` y `:Subnet`, aristas `:MONITORS`). | **Ventajas**: Permite consultas flexibles (ej: "¿qué sensores deberían haber visto este flujo?"). **Integración**: Usar el inventario de endpoints (ADR-046 §3.9) como fuente de verdad. |
| **Q3: Calibración de `N` y `nat_confidence_floor`** | **Metodología**: Usar *golden pcap* de producción para: (1) Calcular el percentil 1 del intervalo de reúso de 5-tuplas → `N`. (2) Medir la precisión de cada método NAT → `nat_confidence_floor`. | **Ejemplo**: Si el 99% de los reciclajes ocurren después de 120s, usar `N=120s`. Para NAT, si el método `LOG` tiene 95% de precisión, usar `nat_confidence_floor=95`. |
| **Q4: Forma final de `trust_tier`** | **Enum derivado + score continuo para IPW**. Guardar las primitivas (`witness_count`, `nat_confidence`, etc.) y derivar `trust_tier` como vista. El score continuo se usa para IPW. | **Flexibilidad**: Permite ajustar la semántica sin cambiar el esquema. **IPW**: Usar regresión logística para predecir la probabilidad de *ground truth*. |
| **Q5: `provenance` y `acceptance_criteria.md`** | **Confirmar**: Añadir el eje `provenance` **sin modificar** el enum congelado de presencia (`DROP/CONFIG/POLICY/BUG/UNKNOWN`). | **Razón**: Evita descongelar artefactos y mantiene la separación de preocupaciones. |
| **Q6: Fuente out-of-band para vector A con host comprometido** | **Documentar el límite y abrir DEBT**. Asumir que el vector A con host comprometido es **indetectable sin fuente externa** (ej: switch con port-security). | **Honestidad científica**: No prometemos lo que no podemos detectar. **DEBT**: `DEBT-ARGUSPP-PORT-SECURITY-001` para integrar señales de switches. |
| **Q7: Señal de host más allá de L2** | **Incluir en v2**: Añadir detección de anomalías TCP/TLS (ej: RST inesperados, mismatches de certificados) como parte de la señal del host plane. | **Razón**: El vector A no se limita a L2 (ej: BGP hijacking, TCP session hijacking). **Prioridad**: Alta, ya que mejora la cobertura de detección. |

---

---
---
## **🎯 Recomendaciones Accionables para el Consejo**

---
### **1. Decisiones Inmediatas (Bloqueantes)**
| **Decisión** | **Acción** | **Responsable** | **Plazo** |
|--------------|------------|-----------------|-----------|
| **Ratificar §3.1.3** | Confirmar que `flow_uid` es único por sensor y que el skew no afecta a la identidad. | Consejo | **Inmediato** |
| **Aprobar diseño del mapa de cobertura** | Grafo de topología en Neo4j (`:Sensor`-[:MONITORS]->`:Subnet`). | Consejo | **Inmediato** |
| **Aprobar `N=60s` como default** | Usar 60s para `flow_start_window`, calibrable con *golden pcap*. | Consejo | **Inmediato** |
| **Aprobar `trust_tier` como vista derivada** | Guardar primitivas y derivar `trust_tier` como vista. | Consejo | **Inmediato** |
| **Aprobar `provenance` como eje separado** | Añadir `provenance_suspected` y `provenance_ground_truth` sin tocar `acceptance_criteria.md`. | Consejo | **Inmediato** |

---
### **2. Tareas para el Equipo (P0/P1)**
| **Tarea** | **Descripción** | **Responsable** | **Plazo** | **Dependencias** |
|-----------|-----------------|-----------------|-----------|------------------|
| **Implementar `DEBT-SENSOR-COVERAGE-MAP-001`** | Crear grafo de topología en Neo4j y sincronizar con inventario de endpoints. | Equipo de Grafo | 2 semanas | ADR-046 §3.9 |
| **Implementar `DEBT-FLOWUID-CANONICAL-ENCODING-001`** | Codificar `flow_uid` en C++/Python y validar paridad. | Equipo de Sensores | 1 semana | - |
| **Implementar `DEBT-NODEID-CRYPTO-IDENTITY-001`** | Generar `node_id` como `SHA256(sensor_public_key)` y ligarlo a ADR-027. | Equipo de Seguridad | 1 semana | ADR-027 |
| **Implementar vigilancia ARP/NDP** | Emitir eventos `:IpMacBinding` desde Wazuh y sensores de red. | Equipo de Host Plane | 2 semanas | Wazuh integrado |
| **Calibrar `N` y `nat_confidence_floor`** | Usar *golden pcap* para ajustar parámetros. | Equipo de QA | 1 semana | - |
| **Añadir métricas de calidad del corpus** | Implementar KPIs como `% flujos con `provenance_ground_truth``. | Equipo de ML | 2 semanas | ADR-040 |
| **Implementar rate-limit adaptativo** | Usar Count-Min Sketch en el correlation-engine. | Equipo de Correlación | 2 semanas | - |

---
### **3. Deudas a Abrir (P2)**
| **DEBT** | **Descripción** | **Prioridad** | **Responsable** |
|----------|-----------------|---------------|-----------------|
| **DEBT-ARGUSPP-PORT-SECURITY-001** | Integrar señales de switches (port-security) para detectar vector A con host comprometido. | Alta | Equipo de Red |
| **DEBT-ARGUSPP-TCP-TLS-ANOMALIES-001** | Añadir detección de anomalías TCP/TLS (RST, seq_num, certificados). | Alta | Equipo de Sensores |
| **DEBT-CORPUS-QUALITY-METRICS-001** | Definir e implementar métricas de calidad del corpus (cobertura MITRE, balance de clases). | Media | Equipo de ML |

---
---
## **📊 Resumen Ejecutivo**
| **Aspecto** | **Estado en v2** | **Evaluación** | **Acciones Recomendadas** |
|-------------|------------------|----------------|---------------------------|
| **Misión primaria (§0)** | Claramente definida | ✅ **Excelente** | Añadir métricas de calidad del corpus. |
| **`flow_uid` (§3.1)** | Codificación canónica, `node_id` criptográfico | ✅ **Sólido** | Validar `N=60s` con *golden pcap*; manejar flujos de larga duración. |
| **Correlación host↔red (§3.2)** | Doble arista, manejo de NAT | ✅ **Robusto** | Definir `agent_id` como `SHA256(hostname + domain + os_uuid)`. |
| **Modelo de amenaza (§3.3–3.5)** | Vectores A/B claros, 3 líneas de defensa | ✅ **Completo** | Añadir detección de MITM en L3/L4. |
| **Marca de confianza (§3.6)** | Features para IPW | ✅ **Correcto** | Definir tabla de decisión para `trust_tier`. |
| **Etiquetado (§3.7)** | Dos campos ortogonales | ✅ **Innovador** | Añadir jerarquía de etiquetas y etiquetas para flujos benignos. |
| **Mapa de cobertura (§3.8)** | Prerrequisito identificado | ✅ **Crítico** | Implementar como grafo de topología en Neo4j. |
| **Señal ARP/NDP (§3.9)** | Nodo de primera clase | ✅ **Adecuado** | Integrar con Wazuh y detectar ARP spoofing pasivo. |
| **Rate-limit (§3.10)** | Adaptativo en correlation-engine | ✅ **Práctico** | Definir baseline por nodo/rol. |

---
---
## **🔥 Conclusión y Próximos Pasos**
El **ADR-052 v2 es un documento maduro y técnicamente sólido**, con una **misión primaria clara** que guía todas las decisiones. Las **mejoras clave** respecto a v1 son:
1. **Enfoque en el corpus** (§0), que alinea el diseño con la producción de modelos de ML.
2. **Definiciones concretas** (`flow_uid`, `node_id`, `flow_start_window`).
3. **Resolución de preguntas abiertas** (Q1–Q7) con consenso técnico.

**Próximos pasos para el Consejo**:
1. **Ratificar las decisiones inmediatas** (§3.1.3, mapa de cobertura, `N=60s`, `trust_tier`, `provenance`).
2. **Asignar tareas al equipo** (implementación de DEBTs P0/P1).
3. **Abrir DEBTs P2** para señales adicionales (port-security, TCP/TLS).

**Pregunta final para el Consejo**:
---
**¿Están de acuerdo con las recomendaciones para:**
1. **Ratificar §3.1.3** (identidad ≠ correlación cross-nodo)?
2. **Aprobar el diseño del mapa de cobertura como grafo de topología en Neo4j**?
3. **Priorizar la implementación de `DEBT-SENSOR-COVERAGE-MAP-001` y `DEBT-FLOWUID-CANONICAL-ENCODING-001` como P0**?
MISTRAL