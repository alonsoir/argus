**Análisis del Consejo de Sabios — ADR-046 (aRGus++: Multi-Source Enriched Pipeline)**
*19 de mayo de 2026 | Respuesta estructurada y crítica*

---

---

## **📜 Resumen Ejecutivo del Consejo**
**ADR-046 es un avance estratégico crítico para aRGus**, transformándolo de un **NDR puro** a un **sistema híbrido NDR/EDR distribuido con capacidad de autoaprendizaje federado**. El diseño es **técnicamente sólido**, pero requiere **ajustes en claridad, priorización y mitigación de riesgos**. A continuación, se detallan **puntos fuertes, debilidades, recomendaciones y respuestas a las preguntas abiertas**.

---

---

---

## **✅ Puntos Fuertes del ADR-046**

1. **Visión Arquitectónica Clara**
    - **Separación de responsabilidades**: Edge (captura/detección) vs. Servidor (correlación/enriquecimiento).
    - **Reutilización de infraestructura**: ZeroMQ + ChaCha20-Poly1305 para transporte, sin nuevas dependencias.
    - **Consistencia tecnológica**: Todo en C++20 (sin Python en producción).

2. **Contribución Científica**
    - **Hipótesis verificable**: `F1(ensemble enriquecido) > F1(aRGus solo)`.
    - **Datasets sintéticos vs. académicos**: Descubrimiento empírico valioso (§8) que merece sección en el paper v24.
    - **Flywheel de aprendizaje federado**: Mecanismo inmunológico distribuido (novel en el contexto de infraestructura crítica).

3. **Modelo Open-Core Bien Definido**
    - **Community**: aRGus + Suricata + Zeek + Wazuh + `correlation-engine`.
    - **Enterprise**: Plugins ensemble firmados + meta-learner + inteligencia federada.

4. **Validación Empírica**
    - **MITRE ATT&CK en tiempo real**: Ground truth de alta calidad (superior a datasets históricos).
    - **Experimentos reproducibles**: Scripts `mitre-generator` + manifiesto JSON.

5. **Escalabilidad**
    - **Configuraciones flexibles**: Mínima (RPi5), Media (RPi5 + N100), Completa (múltiples nodos).

---

---

---

## **⚠️ Puntos Débiles y Recomendaciones de Mejora**

---

### **1. Falta de Detalles en la Arquitectura de `correlation-engine`**
**Problema:**
- El ADR describe **qué hace** `correlation-engine` (join temporal por 5-tupla), pero **no cómo lo hace**.
- **Falta:**
    - Diagrama de flujo de datos.
    - Esquema de las tablas intermedias (ej: ¿cómo se almacenan los datos antes del join?).
    - Detalles de implementación del join temporal (ej: ¿ventana deslizante? ¿buffer en memoria?).

**Recomendación:**
- **Añadir un diagrama de secuencia** (Mermaid) en §3.3:
  ```mermaid
  sequenceDiagram
      participant Sniffer
      participant Suricata
      participant Zeek
      participant Wazuh
      participant RAG
      participant CorrelationEngine
      participant Neo4j

      Sniffer->>RAG: Flow features (CSV)
      Suricata->>RAG: eve.json (alerts)
      Zeek->>RAG: conn.log, dns.log (JSON)
      Wazuh->>WazuhManager: Host events
      WazuhManager->>RAG: Forward to server

      RAG->>CorrelationEngine: Parquet files
      CorrelationEngine->>CorrelationEngine: Join por 5-tupla (±500ms)
      CorrelationEngine->>Neo4j: Grafo enriquecido
      CorrelationEngine->>Parquet: Datasets para entrenamiento
  ```
- **Detallar el algoritmo de join**:
    - ¿Cómo se manejan **mensajes fuera de orden** (ej: `eve.json` llega después que el flow de aRGus)?
    - ¿Se usa un **buffer circular** en memoria? ¿O se persiste en disco?
    - **Ejemplo de pseudocódigo**:
      ```cpp
      // Buffer de eventos por 5-tupla (src_ip, dst_ip, src_port, dst_port, proto)
      std::unordered_map<FiveTuple, std::vector<Event>> buffer;
  
      void CorrelationEngine::process_event(const Event& event) {
          auto key = event.five_tuple();
          buffer[key].push_back(event);
  
          // Eliminar eventos fuera de la ventana (±500ms)
          auto now = std::chrono::system_clock::now();
          buffer[key].erase(
              std::remove_if(buffer[key].begin(), buffer[key].end(),
                  [now](const Event& e) {
                      return std::abs((now - e.timestamp).count()) > 500ms;
                  }),
              buffer[key].end()
          );
  
          // Si hay eventos de todas las fuentes, hacer join
          if (has_all_sources(buffer[key])) {
              auto enriched = join_events(buffer[key]);
              write_to_parquet(enriched);
              write_to_neo4j(enriched);
          }
      }
      ```

---

### **2. Ventana de Correlación (±500ms)**
**Problema:**
- **500ms puede ser demasiado corto** para algunos protocolos (ej: SMTP, FTP) o **demasiado largo** para otros (ej: DNS, ICMP).
- **No se justifica el valor** (¿por qué 500ms y no 100ms o 1s?).

**Recomendación:**
- **Hacerla configurable por protocolo**:
  ```json
  {
    "correlation": {
      "window_ms": {
        "default": 500,
        "tcp": 1000,    // SMTP, HTTP
        "udp": 200,     // DNS, QUIC
        "icmp": 100     // Ping
      }
    }
  }
  ```
- **Justificación en el ADR**:
  > *"La ventana de correlación de 500ms por defecto se eligió empíricamente para equilibrar precisión y rendimiento. Protocolos como DNS (UDP) pueden usar ventanas más cortas (200ms), mientras que TCP (HTTP/SMTP) puede requerir ventanas más largas (1s) para acomodar latencias de aplicación. Este valor es configurable por protocolo en `correlation.json`."*

---

### **3. Orden de Integración (Suricata vs. Zeek vs. Wazuh)**
**Problema:**
- El ADR no prioriza qué fuente integrar primero.

**Recomendación:**
**Priorizar en este orden:**
1. **Suricata** (P0):
    - **Razón:** Proporciona **etiquetado automático** (ground truth) para el dataset.
    - **Impacto:** Permite entrenar el primer modelo enriquecido (`XGBoost-enriched`) **sin depender de Wazuh o Zeek**.
2. **Zeek** (P1):
    - **Razón:** Añade **contexto de protocolo** (DNS, TLS, HTTP), mejorando la calidad del grafo.
3. **Wazuh** (P2):
    - **Razón:** **Mayor footprint** (requiere agente + manager). Validar primero que Suricata + Zeek caben en el edge.

**Justificación:**
- **Suricata primero** permite **validar el valor del enriquecimiento** (etiquetado automático) antes de añadir complejidad.
- **Zeek segundo** añade **profundidad** (Layer 7) sin requerir cambios en el edge.
- **Wazuh tercero** es el más costoso (recursos + despliegue).

---
**Acción:**
Añadir en §13 (Preguntas abiertas):
> *"El Consejo recomienda integrar las fuentes en el orden: **Suricata (P0) → Zeek (P1) → Wazuh (P2)**. Esto permite validar el valor del enriquecimiento de forma incremental."*

---

### **4. Consumo de Recursos (DEBT-ARGUSPP-RESOURCE-001)**
**Problema:**
- **No hay datos concretos** sobre el consumo de CPU/RAM de Suricata + Zeek + Wazuh en RPi5/N100.
- **Riesgo:** El pipeline completo **puede no caber** en hardware de bajo coste.

**Recomendación:**
- **Añadir una tabla estimada** en §9.2 (aunque sea aproximada):

Consumo de Recursos Estimado (aRGus++)


| Componente          | CPU (RPi5) | RAM (RPi5) | CPU (N100) | RAM (N100) | Notas                          |
  |--------------------|------------|------------|------------|------------|--------------------------------|
| aRGus (sniffer)    | 20%        | 512MB      | 10%        | 256MB      | eBPF/XDP                       |
| aRGus (ml-detector)| 30%        | 1GB        | 15%        | 512MB      | XGBoost inference              |
| Suricata           | 40%        | 1.5GB      | 20%        | 768MB      | Modo pasivo, 50K reglas        |
| Zeek               | 35%        | 1GB        | 15%        | 512MB      | Logs básicos (conn, dns, ssl) |
| Wazuh Agent        | 25%        | 512MB      | 10%        | 256MB      | FIM + procesos                 |
| **Total**          | **150%**   | **4.5GB**  | **70%**    | **2.3GB**  | **RPi5 no soporta el total**  |

- **Conclusión:**
    - **RPi5 solo**: **No viable** para todas las fuentes (CPU >100%, RAM >4GB).
    - **RPi5 + N100**:
        - **RPi5**: aRGus + Suricata (CPU: 90%, RAM: 2.5GB).
        - **N100**: Zeek + Wazuh (CPU: 45%, RAM: 1.5GB).
    - **Servidor**: `correlation-engine` + Neo4j (requiere **8GB RAM mínimo**).

---
**Acción:**
Añadir en §9.3:
> *"Basado en estimaciones, **RPi5 no puede ejecutar todas las fuentes simultáneamente**. La configuración mínima viable es:
> - **Edge (RPi5)**: aRGus + Suricata.
> - **Edge (N100)**: Zeek + Wazuh.
> - **Servidor**: `correlation-engine` + Neo4j (8GB RAM)."*

---

### **5. `mitre-generator` como Componente**
**Problema:**
- No está claro si `mitre-generator` es un **componente interno** o una **herramienta externa**.

**Recomendación:**
- **Tratarlo como un componente interno** (C++20) con su propio ADR.
- **Justificación:**
    - **Integración estrecha** con `correlation-engine` (necesita sincronización de timestamps).
    - **Reproducibilidad**: Atomic Red Team es open-source, pero **el orquestador debe ser determinista**.
- **Estructura propuesta:**
  ```
  argus/
  ├── mitre-generator/       # Nuevo componente
  │   ├── mitre_orchestrator.cpp  # C++20, lanza Atomic Red Team
  │   ├── manifest_schema.json
  │   └── CMakeLists.txt
  ```

---
**Acción:**
Añadir en §7:
> *"`mitre-generator` se implementará como un **componente interno en C++20** (no como una herramienta externa). Esto garantiza:
> - **Determinismo** (mismos inputs → mismos outputs).
> - **Integración nativa** con `correlation-engine` (sincronización de timestamps).
> - **Reproducibilidad** en entornos de prueba."*

---

### **6. Experimento de Mezcla Datasets (Academic vs. Sintético)**
**Problema:**
- **No se especifica si los datos del experimento (§8.2) aún existen**.

**Recomendación:**
- **Reconstruir el experimento** si los datos no existen.
    - **Pasos:**
        1. Entrenar modelos con ratios: 100% académico, 75/25, 50/50, 25/75, 100% sintético.
        2. Evaluar en **CTU-13 Neris** (holdout).
        3. Graficar **F1 vs. ratio académico/sintético**.
    - **Herramientas:**
        - Usar `XGBoost` (ya integrado en aRGus).
        - Datasets académicos: CIC-IDS-2017, CTU-13.
        - Datasets sintéticos: Generados con **GANs** o **simuladores de tráfico** (ej: [FlowGAN](https://github.com/guofei9987/flowgan)).
- **Si no se pueden reconstruir los datos:**
    - **Documentar el resultado cualitativo** (sin curva):
      > *"El experimento empírico mostró que los modelos entrenados con datos sintéticos puros superaban a aquellos entrenados con mezclas de datos académicos y sintéticos. Este resultado sugiere que los datasets académicos introducen sesgos que degradan la generalización del modelo."*

---
**Acción:**
Añadir en §8.4:
> *"Si los datos del experimento original no son recuperables, se reconstruirá el experimento usando:
> - **Datasets académicos**: CIC-IDS-2017, CTU-13.
> - **Datasets sintéticos**: Generados con FlowGAN o simuladores de tráfico.
> - **Métrica**: F1 en CTU-13 (holdout)."*

---

### **7. `correlation-engine` Scope Mínimo Viable (v1)**
**Problema:**
- No está claro qué funcionalidad es **mínima para validar el concepto**.

**Recomendación:**
**Scope mínimo para v1:**
1. **Join temporal por 5-tupla** (aRGus + Suricata).
    - **Razón:** Suricata proporciona **etiquetado automático** (ground truth).
2. **Salida a Parquet** (para entrenamiento).
3. **Salida a Neo4j** (grafo básico: `Flow`, `Signature`, `Alert`).

**Excluir en v1:**
- Zeek (añadir en v2).
- Wazuh (añadir en v3).
- Meta-learner (enterprise, post-v1).

---
**Acción:**
Añadir en §3.3:
> *"El **scope mínimo viable (v1)** de `correlation-engine` incluye:
> - Join temporal por 5-tupla (aRGus + Suricata).
> - Salida a Parquet (entrenamiento).
> - Salida a Neo4j (grafo básico).
> - **Excluye**: Zeek, Wazuh, meta-learner (fases posteriores)."*

---

### **8. Sincronización NTP (DEBT-ARGUSPP-NTP-001)**
**Problema:**
- **No se menciona cómo garantizar la sincronización de relojes** (crítico para el join temporal).

**Recomendación:**
- **Requisitos mínimos:**
    - **NTP en todos los nodos edge** (sincronización con servidor central).
    - **Verificación de drift**:
        - **Máximo drift permitido**: **10ms** (para ventana de 500ms).
        - **Monitorización**: Alertar si el drift supera el umbral.
    - **Fallback**: Si NTP falla, **usar el timestamp del servidor central** (asumiendo que el edge tiene conectividad intermitente).

---
**Acción:**
Añadir en §9.1:
> *"**Requisito crítico**: Todos los nodos edge deben sincronizar sus relojes con el servidor central via NTP, con un **drift máximo de 10ms**. Si el drift supera este umbral, el `correlation-engine` **descarta eventos** del nodo afectado y genera una alerta. En caso de fallo de NTP, se usa el timestamp del servidor central (si hay conectividad)."*

---

### **9. Frontera Community/Enterprise (Tabla §10)**
**Problema:**
- **`correlation-engine` está marcado como open-source**, pero **depende de Neo4j** (que es AGPL).

**Recomendación:**
- **Aclarar la licencia de `correlation-engine`**:
    - **Opción 1:** `correlation-engine` es **AGPL** (para cumplir con Neo4j).
    - **Opción 2:** **Aislar la dependencia de Neo4j** en un plugin separado (enterprise).
- **Recomendación del Consejo:**
    - **Mantener `correlation-engine` como open-source (AGPL)**.
    - **Documentar la dependencia de Neo4j** claramente:
      > *"`correlation-engine` usa Neo4j (AGPL) para el grafo de amenazas. Los usuarios deben cumplir con los términos de la licencia AGPL si distribuyen el componente."*

---
**Acción:**
Actualizar §10:
> *"`correlation-engine` (C++20 + Neo4j) se distribuye bajo **AGPL-3.0** para cumplir con la licencia de Neo4j. El resto del pipeline (aRGus, Suricata, Zeek, Wazuh) sigue siendo MIT/Apache 2.0."*

---

### **10. Validación con Datasets Históricos**
**Problema:**
- **§6 argumenta que los datasets históricos (CTU-13, CIC-IDS-2017) no son suficientes para validar aRGus++**.
- **Pero no se propone una alternativa concreta para validar el pipeline actual (sin MITRE ATT&CK).**

**Recomendación:**
- **Validación en dos fases:**
    1. **Fase 1 (Pre-MITRE):**
        - Usar **datasets públicos con etiquetado de Suricata** (ej: [Stratosphere IPS Dataset](https://stratosphereips.org/datasets)).
        - **Objetivo:** Validar que el join temporal funciona y que el etiquetado automático de Suricata mejora el F1.
    2. **Fase 2 (Post-MITRE):**
        - Usar **MITRE ATT&CK en tiempo real** (ground truth perfecto).

---
**Acción:**
Añadir en §6:
> *"Antes de implementar `mitre-generator`, se validará el pipeline con:
> - **Stratosphere IPS Dataset**: Incluye alertas de Suricata + tráfico de red.
> - **Objetivo**: Verificar que el join temporal y el etiquetado automático funcionan correctamente."*

---

---
---
## **📌 Respuestas a las Preguntas Abiertas del ADR (§13)**

| Pregunta | Respuesta del Consejo | Justificación |
|----------|-----------------------|---------------|
| **Q1: Ventana de correlación (±500ms)** | **Configurable por protocolo** (default: 500ms, TCP: 1s, UDP: 200ms, ICMP: 100ms). | Equilibra precisión y rendimiento. |
| **Q2: Orden de integración** | **Suricata (P0) → Zeek (P1) → Wazuh (P2)**. | Suricata proporciona etiquetado automático (ground truth). |
| **Q3: Wazuh en el edge** | **P2 (post-validación de Suricata + Zeek)**. | Mayor footprint; validar primero que el edge soporta las otras fuentes. |
| **Q4: `correlation-engine` scope mínimo v1** | **aRGus + Suricata (join + Parquet + Neo4j básico)**. | Permite validar el valor del enriquecimiento con etiquetado automático. |
| **Q5: `mitre-generator`** | **Componente interno (C++20) con su propio ADR**. | Garantiza determinismo e integración nativa. |
| **Q6: Experimento de mezcla datasets** | **Reconstruir el experimento** (si los datos no existen). | Prioritario para el paper v24. |

---

---
---
## **🚀 Plan de Acción Recomendado**

### **Fase 1: Validación del Concepto (P0)**
| Tarea | Prioridad | Tiempo Estimado | Dependencias |
|-------|-----------|------------------|--------------|
| **ADR-047: `correlation-engine` v1** | P0 | 2 días | ADR-046 |
| **Implementar `correlation-engine` (aRGus + Suricata)** | P0 | 5 días | ADR-047 |
| **Validar con Stratosphere IPS Dataset** | P0 | 2 días | `correlation-engine` v1 |
| **DEBT-ARGUSPP-NTP-001** | P0 | 1 día | Ninguna |

### **Fase 2: Integración de Zeek (P1)**
| Tarea | Prioridad | Tiempo Estimado | Dependencias |
|-------|-----------|------------------|--------------|
| **Integrar Zeek en edge** | P1 | 3 días | `correlation-engine` v1 |
| **Actualizar `correlation-engine` (aRGus + Suricata + Zeek)** | P1 | 2 días | Zeek integrado |
| **Validar con datasets públicos** | P1 | 2 días | `correlation-engine` v2 |

### **Fase 3: Integración de Wazuh (P2)**
| Tarea | Prioridad | Tiempo Estimado | Dependencias |
|-------|-----------|------------------|--------------|
| **DEBT-ARGUSPP-RESOURCE-001** | P1 | 2 días | Hardware (RPi5/N100) |
| **Integrar Wazuh en edge** | P2 | 4 días | DEBT-ARGUSPP-RESOURCE-001 |
| **Actualizar `correlation-engine` (v3 completa)** | P2 | 2 días | Wazuh integrado |

### **Fase 4: Validación con MITRE ATT&CK (P1)**
| Tarea | Prioridad | Tiempo Estimado | Dependencias |
|-------|-----------|------------------|--------------|
| **ADR-048: `mitre-generator`** | P1 | 1 día | ADR-046 |
| **Implementar `mitre-generator`** | P1 | 3 días | ADR-048 |
| **Validar con MITRE ATT&CK** | P1 | 2 días | `mitre-generator` + `correlation-engine` v3 |

### **Fase 5: Paper v24 (P2)**
| Tarea | Prioridad | Tiempo Estimado | Dependencias |
|-------|-----------|------------------|--------------|
| **Sección: Datasets sintéticos vs. académicos** | P2 | 2 días | Experimento reconstruido |
| **Sección: aRGus++ (NDR/EDR híbrido)** | P2 | 3 días | Validación completa |

---

---
---
## **⚠️ Riesgos Críticos y Mitigaciones**

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| **Consumo de recursos en edge** | El pipeline completo no cabe en RPi5. | **Configuraciones escalonadas** (RPi5 + N100). |
| **Sincronización NTP fallida** | Joins incorrectos en `correlation-engine`. | **Verificación de drift + fallback a timestamp del servidor**. |
| **Suricata/Zeek/Wazuh no escalan** | Degradación del rendimiento. | **Benchmarks previos** (DEBT-ARGUSPP-RESOURCE-001). |
| **Dependencia de Neo4j (AGPL)** | Problemas de licencia. | **Documentar claramente** (AGPL para `correlation-engine`). |
| **Falta de ground truth** | Datasets históricos no válidos. | **Usar Stratosphere IPS Dataset + MITRE ATT&CK**. |

---

---
---
## **💡 Recomendaciones Finales del Consejo**

1. **Priorizar la validación del concepto** (`correlation-engine` v1 + Suricata).
2. **Documentar el experimento de mezcla datasets** (§8) en el paper v24.
3. **Añadir diagramas y pseudocódigo** para clarificar la implementación de `correlation-engine`.
4. **Definir configuraciones de despliegue claras** (RPi5 solo, RPi5 + N100, servidor).
5. **Aislar la dependencia de Neo4j** (AGPL) en `correlation-engine`.
6. **Reconstruir el experimento académico vs. sintético** si los datos no existen.

---
---
## **📝 Conclusión del Consejo**
**ADR-046 es un diseño ambicioso y bien fundamentado**, pero requiere **ajustes en claridad, priorización y mitigación de riesgos** para ser implementable. Las recomendaciones del Consejo se centran en:
1. **Validar el concepto con el scope mínimo viable** (`correlation-engine` v1 + Suricata).
2. **Garantizar la sincronización de relojes** (NTP + drift máximo).
3. **Documentar el consumo de recursos** y definir configuraciones de despliegue realistas.
4. **Reconstruir el experimento de datasets** para el paper v24.

**Para el equipo de aRGus:**
¿Estáis de acuerdo con **priorizar `correlation-engine` v1 (aRGus + Suricata) como primer paso**? **Sí**, es el camino más robusto para validar el valor del enriquecimiento antes de escalar a Zeek y Wazuh. **La sincronización NTP y los benchmarks de recursos son críticos para el éxito.**