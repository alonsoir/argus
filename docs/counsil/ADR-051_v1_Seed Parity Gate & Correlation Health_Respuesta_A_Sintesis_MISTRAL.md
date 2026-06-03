Aquí tienes una **síntesis accionable y estructurada** del ADR-051 v1 tras la deliberación del Consejo, enfocada en **tareas concretas, decisiones tomadas y dependencias claras** para su implementación. El objetivo es que cualquier miembro del Consejo o equipo de desarrollo pueda extraer **qué hay que hacer, en qué orden y con qué prioridad**.

---

---

---

## **📌 Resumen Ejecutivo (TL;DR para el Consejo)**
✅ **ADR-051 v1 APROBADO con condiciones** (8/8 sabios).
🔹 **Principios innegociables**:
- **Data-plane > control-plane**: Validar lo que los sensores *emiten*, no lo que *configuran*.
- **Fail-closed en arranque**: Si no hay paridad de `community_id`, el correlation-engine **no arranca**.
- **Degradación gracefully en runtime**: Si un sensor drifta, se excluye de la correlación pero **se anota en el grafo** (nunca fallo silencioso).
- **`orphan_rate` per-sensor**: Métrica accionable para identificar el sensor problemático.

🔹 **Decisiones clave**:
1. **Flujo-diana**: Inyección sintética determinista (flujo Neris + batería de vectores).
2. **Gate periódico**: **NO bloqueante**. Solo en arranque. La sonda activa periódica se difiere a una DEBT opcional (`DEBT-SEED-ACTIVE-PROBE-001`, P3).
3. **Degradación en runtime**: Excluir sensor con `orphan_rate` alto, pero anotarlo en Neo4j.

🔹 **Tareas inmediatas**:
- Redactar **ADR-051 v2** incorporando las enmiendas convergentes (§3).
- Extraer el **backlog de DEBTs** (§5) y priorizarlas.

---

---

---

## **📋 Decisiones Finales (Consenso 8/8)**

### **1. Flujo-diana de referencia**
- **Decisión**: **Inyección sintética determinista** del flujo Neris (`147.32.84.165:1027 → 74.125.232.195:80`).
- **Ampliación**: Incluir una **batería mínima de vectores** para cubrir casos de borde:
    - TCP IPv4 (flujo Neris).
    - UDP IPv4 (ej. mDNS).
    - TCP IPv6.
    - Dirección invertida (verificar canonicidad).
- **Requisitos**:
    - Inyectar en el segmento observado por **todos los sensores** (ej. `eth1/intnet`).
    - Marcar el flujo con un **SNI/User-Agent identificable** (ej. `ARGUS-SEED-PROBE`) para descartarlo tras la validación.
    - **No contaminar el grafo de producción**: El flujo de prueba debe ser descartado antes de aceptar tráfico real.

---

### **2. Gate de paridad de `community_id` (antes "Seed Parity Gate")**
- **Nuevo nombre**: **"Community ID Parity Gate"** (propuesto por ChatGPT).
    - *Razón*: El gate valida la paridad del `community_id` emitido, no solo el seed. Un drift puede deberse a bugs en plugins, versiones de sensores, o normalización de direcciones.
- **Mecánica**:
    - **Bloqueante en arranque**: Si no hay paridad entre sensores **y con el oráculo**, el correlation-engine **no arranca**.
    - **Diagnóstico en fallo**:
        - Plantilla verbose: `sensor / cid_esperado(oráculo) / cid_emitido / acción sugerida`.
        - Incluir **hash SHA-256 del config cargado** (para verificar si el binario ignora la configuración).
        - Incluir **seed del oráculo** (para comparar con el declarado en cada sensor).
- **Oráculo en dos niveles**:
    - **Nivel 1**: Paridad entre sensores (¿todos coinciden entre sí?).
    - **Nivel 2**: Paridad con `pycommunityid` (¿coinciden con el oráculo?).
    - Si todos los sensores coinciden entre sí pero **no con el oráculo** → Alertar: *"Posible error en oráculo"* (no bloqueante).

---

### **3. Health-check continuo (`orphan_rate`)**
- **Métrica**: `orphan_rate` **per-sensor** (no global).
    - Definición: Fracción de flujos emitidos por un sensor que **ningún otro sensor corrobora** dentro de la ventana de correlación.
- **Umbrales provisionales** (hasta calibración de B):
    - `>5%` sostenido 5 min → **Warning**.
    - `>15%` → **Critical**.
- **Acciones en runtime**:
    - Si un sensor supera el umbral → **Degradarlo**: Excluirlo de la correlación pero **anotarlo en el grafo** con:
      ```cypher
      (flow)-[:DETECTED_BY {method: "suricata", confidence: "low", reason: "high_orphan_rate"}]->(sensor)
      ```
    - Generar alerta: *"Sensor X degradado por orphan_rate=Y%. Revisar seed o cobertura."*

---
### **4. Sonda activa periódica**
- **Decisión**: **No incluir en el núcleo de ADR-051 v2**.
    - El `orphan_rate` continuo ya cubre el drift post-arranque.
    - **Opcional**: Registrar como **DEBT diferida** (`DEBT-SEED-ACTIVE-PROBE-001`, P3), activable por configuración en entornos de alta criticidad.
    - **Reintegración automática**: Si se implementa la sonda, el sensor se reintegra cuando recupere paridad (verificado por la sonda o el gate manual).

---

---
---
## **🛠️ Enmiendas Convergentes para ADR-051 v2**
*(Todas aditivas, sin contradicciones)*

| **Área**               | **Cambio**                                                                 | **Prioridad** | **Responsable**       |
|------------------------|----------------------------------------------------------------------------|---------------|------------------------|
| **Título**             | Renombrar a **"Community ID Parity Gate"**                                | Alta          | Redactor ADR           |
| **Flujo-diana**        | Batería de vectores (TCP/UDP/IPv4/IPv6/invertido)                         | Alta          | Equipo de pruebas      |
| **Oráculo**            | Dos niveles (paridad entre sensores + paridad con oráculo) + quórum      | Alta          | Equipo de correlación   |
| **Diagnóstico**        | Plantilla verbose + hash config + seed oráculo                           | Alta          | Equipo de operaciones   |
| **Health-check**       | `orphan_rate` per-sensor + umbrales provisionales (5%/15%)                 | Alta          | Equipo de métricas      |
| **Despliegue**         | **Fase 1**: Gate + health-check (Suricata/Zeek). **Fase 2**: +aRGus       | Alta          | Equipo de despliegue    |
| **Pruebas**            | `make crosscheck-up/run` obligatorio en CI (`DEBT-CID-CROSSCHECK-CI-001`) | Alta          | Equipo de CI/CD         |
| **Pruebas de caos**    | Forzar drift de seed y verificar degradación (`DEBT-SEED-CHAOS-TEST-001`) | Media         | Equipo de QA            |
| **Métricas**           | Añadir `match_rate = 1 - orphan_rate` (para dashboards)                     | Baja          | Equipo de monitorización|

---

---
---
## **📦 Backlog de DEBTs (Priorizadas)**
*(Extraídas de §5 + nuevas propuestas)*

### **🔴 P1 (Críticas para ADR-051 v2)**
| **ID**                          | **Descripción**                                                                 | **Dependencias**               | **Equipo**          |
|---------------------------------|---------------------------------------------------------------------------------|--------------------------------|---------------------|
| `DEBT-CORRELATION-SEED-GATE-001` | Especificación del gate (ADR-051 v2).                                          | Ninguna                       | Todos               |
| `DEBT-SEED-GATE-DIAGNOSTIC-001` | Diagnóstico verbose + hash config + seed oráculo.                              | ADR-051 v2                    | Operaciones         |
| `DEBT-ARGUSPP-COUNTER-DUMP-001` | Volcado de contadores de aRGus (bloquea health-check de aRGus).                | Fase 2                         | Equipo aRGus        |
| `DEBT-CID-PARITY-VECTORS-001`   | Batería de vectores de referencia (TCP/UDP/IPv6/invertido).                    | ADR-051 v2                    | Pruebas             |
| `DEBT-CID-CROSSCHECK-CI-001`    | `make crosscheck-up/run` como gate de CI.                                       | ADR-051 v2                    | CI/CD               |

### **🟡 P2 (Importantes, pero no bloqueantes)**
| **ID**                          | **Descripción**                                                                 | **Dependencias**               | **Equipo**          |
|---------------------------------|---------------------------------------------------------------------------------|--------------------------------|---------------------|
| `DEBT-CORRELATION-TIMEOUT-CALIB-001` | Calibración de `source_wait_timeout` (inputs de §3.4).                     | ADR-051 v2                    | Equipo B            |
| `DEBT-SENSOR-COVERAGE-MAP-001`  | Mapa declarativo sensor↔segmento (prerequisito para `orphan_rate`).             | ADR-051 v2                    | Equipo de red        |
| `DEBT-CID-ORACLE-QUORUM-001`    | Oráculo en dos niveles + quórum.                                               | ADR-051 v2                    | Correlación         |
| `DEBT-SEED-CHAOS-TEST-001`      | Pruebas de caos (forzar drift de seed).                                         | ADR-051 v2                    | QA                  |

### **🟢 P3 (Opcionales/Diferidas)**
| **ID**                          | **Descripción**                                                                 | **Dependencias**               | **Equipo**          |
|---------------------------------|---------------------------------------------------------------------------------|--------------------------------|---------------------|
| `DEBT-SEED-ACTIVE-PROBE-001`    | Sonda activa periódica no bloqueante (configurable).                          | ADR-051 v2                    | Operaciones         |

---

---
---
## **📅 Ruta de Implementación Propuesta**
1. **Día 0 (Inmediato)**:
    - Redactar **ADR-051 v2** incorporando las enmiendas de §3.
    - Circular v2 para **confirmación de fidelidad** (no re-deliberación).
    - Extraer y priorizar el **backlog de DEBTs** (§5).

2. **Fase 1 (1-2 sprints)**:
    - Implementar el **Community ID Parity Gate** (bloqueante en arranque).
    - Desplegar **health-check en modo degradado** (Suricata + Zeek).
    - Implementar **DEBT-SEED-GATE-DIAGNOSTIC-001** (diagnóstico verbose).
    - Añadir **`crosscheck-up/run` a CI** (`DEBT-CID-CROSSCHECK-CI-001`).

3. **Fase 2 (3-4 sprints)**:
    - Cerrar **DEBT-ARGUSPP-COUNTER-DUMP-001** (volcado de contadores de aRGus).
    - Incorporar aRGus al **health-check** (`orphan_rate`).
    - Calibrar **`source_wait_timeout`** (`DEBT-CORRELATION-TIMEOUT-CALIB-001`).

4. **Fase 3 (Opcional)**:
    - Implementar **DEBT-SEED-ACTIVE-PROBE-001** (sonda activa periódica).
    - Ejecutar **pruebas de caos** (`DEBT-SEED-CHAOS-TEST-001`).

---

---
---
## **⚠️ Riesgos y Mitigaciones**

| **Riesgo**                              | **Impacto**                          | **Mitigación**                                                                 |
|-----------------------------------------|--------------------------------------|--------------------------------------------------------------------------------|
| **Falsos positivos en `orphan_rate`**   | Degradación innecesaria de sensores. | Usar umbrales dinámicos (percentiles) + mapa de cobertura para distinguir asimetría legítima. |
| **Contaminación del grafo**             | Flujos de prueba en producción.      | Marcar flujos sintéticos con SNI/User-Agent y descartarlos tras validación.   |
| **Dependencia de `pycommunityid`**      | Error en oráculo bloquea el gate.    | Oráculo en dos niveles + quórum. Alertar si N-1 sensores coinciden entre sí.   |
| **Latencia en arranque**                | Retraso en despliegue.               | Inyección sintética determinista (rápida) + timeout máximo para el gate.      |

---

---
---
## **🔍 Preguntas para el Consejo (Acción Inmediata)**
1. **¿El backlog de DEBTs propuesto cubre todas las dependencias críticas para implementar ADR-051 v2?**
    - *Ejemplo*: ¿Falta alguna DEBT para el versionado del oráculo o la inyección sintética?

2. **¿Priorización de DEBTs correcta?**
    - *Ejemplo*: ¿`DEBT-CID-PARITY-VECTORS-001` debería ser P0 en lugar de P1?

3. **¿Falta algún escenario de prueba crítico?**
    - *Ejemplo*: ¿Pruebas con flujos IPv6 o direcciones invertidas?

4. **¿Aceptable la degradación gracefully en runtime?**
    - *Alternativa*: ¿Alguien prefiere un **fail-closed total** en runtime (apagar el sistema si un sensor drifta)?

---
---
## **📌 Próximos Pasos (Accionables)**
1. **Redactar ADR-051 v2** con las enmiendas acordadas.
2. **Confirmar backlog de DEBTs** y asignar responsables.
3. **Iniciar Fase 1**:
    - Implementar el **Community ID Parity Gate**.
    - Desplegar health-check en modo degradado (Suricata/Zeek).
4. **Revisar en 1 sprint**:
    - Avance en DEBTs P1.
    - Resultados de las pruebas de caos.

---
**Aironman DirtDiver**, ¿te parece que esta síntesis captura todas las decisiones y tareas accionables? ¿O hay algún punto que requiera más detalle o ajuste?

FDO MISTRAL