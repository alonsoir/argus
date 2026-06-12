Aironman DirtDiver, tu consulta al Consejo de Sabios está impecablemente estructurada: **evidencia clara, decisiones explicitadas, hallazgos reencuadrados y preguntas concretas**. Aquí tienes mi análisis y respuestas, organizadas para facilitar la convergencia 8/8. Usaré el formato de **respuesta directa + justificación técnica + impacto** para cada pregunta, y finalizaré con una síntesis de gobernanza.

---

---

## **Respuestas al Consejo**

---

### **Q1: Dirección del fix de ROWGAP-001**
**Respuesta:** **(a) + (d)** — **Comprobar `send()` + reintento acotado** (a) **y aceptar dedup por `flow_uid`** (d).
**Justificación:**
- **(a)** es el mínimo indispensable para una herramienta de prueba: **determinismo en CI** exige que el injector no pierda eventos *silenciosamente*. Un `send()` fallido con `dontwait` debe al menos loguear un error y reintentar (ej. 3 veces con backoff exponencial). Esto no añade complejidad a Kuzu/bronce, solo al injector.
- **(d)** es válido *adicionalmente* porque el diseño actual ya es robusto a reenvíos: `flow_uid` (hash de 5-tupla + community_id) es único incluso si `event_id` se repite. **El riesgo de (d) solo es el ruido en logs**, no corrupción de datos.
- **(b)** (bloqueante) añade latencia y puede enmascarar problemas de rendimiento en el pipe. **(c)** (reconsiderar PUSH/PULL) es overkill para una herramienta de test.

**Impacto:** Coste bajo (código en injector solo), ganancia alta (CI determinista + logs honestos).

---

### **Q2: Realismo del benigno vs cobertura del discard path**
**Respuesta:** **Dos perillas: modo determinista (100% TCP/UDP) + modo realista (5% ICMP/otros)**.
**Justificación:**
- **Determinismo CI:** El modo por defecto (usado en pipelines de integración) debe ser 100% TCP/UDP para evitar falsos negativos en tests de bronce.
- **Cobertura:** Un flag `--realistic-benign` (o variable de entorno) puede inyectar un 5% de protocolos sin puertos (ICMP, etc.) para ejercitar el camino de descarte. **Ejemplo:**
  ```cpp
  if (realistic_mode && rand() % 20 == 0) { // 5%
      proto = ICMP; // community_id == nullopt
  }
  ```
- **Alternativa:** Si el Consejo prefiere simplicidad, **1% ICMP** es suficiente para cubrir el path sin afectar significativamente el conteo de bronce.

**Impacto:** Mínimo cambio en código, máxima flexibilidad para CI vs. testing de edge cases.

---

### **Q3: ¿Alimenta ADR-055?**
**Respuesta:** **Sí, absorbe ADR-055** (como subsección "Decisiones de Injector").
**Justificación:**
- ADR-055 ya cubre "decisiones de injectors/golden/lib". El reencuadre de ROWGAP-001 y el fix de `node_id`/`proto` son **decisiones de diseño del injector**, no del engine de correlación.
- **Estructura propuesta para ADR-055:**
  - **Sección 3.1:** `node_id` sintético (isomorfo, `synth-node-00`).
  - **Sección 3.2:** `proto` benigno (TCP/UDP forzado + opción realista).
  - **Sección 3.3:** Garantías de entrega en injector (ROWGAP-001: (a)+(d)).

**Excepción:** Si el Consejo quiere destacar el **reencuadre conceptual** (de "pérdida" a "no garantía once-only"), puede añadirse un **ADR-055-A1** (Addendum) para documentar el cambio de mentalidad.

**Impacto:** Centraliza la documentación, evita fragmentación.

---

### **Q4: DEBT id para el fix de proto**
**Respuesta:** **No merece ID propio** — **cierra el objetivo de poblar `community_id` (DAY 176, A)**.
**Justificación:**
- El bug de `proto` benigno era un **síntoma de un injector irrealista**, no una deuda arquitectónica. El fix es **completar el objetivo A** (poblar `community_id`).
- **Regla de oro:** Una deuda (DEBT) debe ser un **problema sistémico con impacto en producción o mantenimiento**. Aquí, el impacto era solo en tests (bronce vacío).
- **Acción:** Añadir al changelog del injector: *"Fix: proto benigno forzado a TCP/UDP (DAY 177) para garantizar community_id poblado"*.

**Impacto:** Evita inflación de IDs de deuda.

---

### **Q5: Oracle Divergence en bronce**
**Respuesta:** **Registrar como aviso, pero no actuar ahora**.
**Justificación:**
- El bronce **preserva la procedencia real** (`DETECTOR_SOURCE_DIVERGENCE`), lo cual es correcto según ADR-051.
- La propagación a Kuzu/gold es **fuera de alcance** del día 177 (cableado E2E). **Recomendación:**
  - Añadir un **TODO** en el código de Kuzu: *"Verificar que `DETECTOR_SOURCE_DIVERGENCE` se propaga correctamente a gold (relacionado con ADR-051)"*.
  - **No bloquear el merge** por esto: el riesgo es bajo (solo 9/159 filas afectadas).

**Impacto:** Decisión aplazada al equipo de Kuzu, sin bloqueo en el actual PR.

---

---
---
## **Síntesis de Gobernanza**

| Pregunta | Respuesta | Tipo          | Prioridad | Dueño       |
|----------|-----------|---------------|-----------|-------------|
| Q1       | (a)+(d)   | Decisión      | Alta      | Injector    |
| Q2       | Dos perillas | Decisión   | Media     | Injector    |
| Q3       | Sí (ADR-055) | Documentación | Media     | Arquitectura|
| Q4       | No (cierra A) | Gobernanza  | Baja      | Injector    |
| Q5       | Aviso     | Observación   | Baja      | Kuzu        |

---
**Conclusión:**
- **Q1 y Q2** requieren **cambio en el injector** (mínimo, local).
- **Q3** es **documentación** (ADR-055).
- **Q4 y Q5** son **gobernanza** (no bloqueantes).

**Próximos pasos sugeridos:**
1. Implementar **(a)+(d)** en el injector y añadir logs de `send()` fallidos.
2. Abrir un PR con:
  - Fix de `proto` benigno (Q4).
  - Actualización de ADR-055 (Q3).
  - TODO para Kuzu (Q5).
3. **Votación rápida:** ¿Acepta el Consejo esta dirección para Q1–Q4?

---
**Observación final:**
El reencuadre de ROWGAP-001 es **brillante**: pasa de un problema de "pérdida" (que generaba paranoia) a uno de **garantías de entrega** (que tiene solución clara). Esto merece un **`// NOTE: DAY 177 - ROWGAP reencuadrado como falta de garantía once-only`** en el código del injector.

---
¿Qué aspectos de este análisis te gustaría profundizar, o hay alguna objeción a estas propuestas?

FDO
MISTRAL