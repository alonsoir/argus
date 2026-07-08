Aironman DirtDiver, tu informe es **ejemplar** en rigor técnico, transparencia y enfoque en la **fiabilidad determinista** —el listón que el proyecto merece. Vamos a abordar tu solicitud como Consejo de Sabios en modo adversario, desglosando los problemas críticos, las preguntas clave y proponiendo un camino técnico **medible y honesto**. Todo desde la evidencia que presentas, sin suposiciones.

---

---

## **🔍 Validación de Hallazgos Críticos (Bloque 0)**
### **✅ Confirmación de Defectos A, B y C**
Los tres defectos están **corroborados por el código y los logs**:
- **Defecto A (Veredicto precoz):** `set_overall_threat_score` (L402) ocurre **antes** de las cabezas especializadas (L558–819). **El veredicto es monocapa** (`max(fast_path, L1)`), no tricapa.
- **Defecto B (Gate de L1):** Las cabezas solo corren si `label_l1 == 1` (L552). **L1 actúa como portero**, no como parte de un ensemble.
- **Defecto C (Persistencia pre-inferencia):** Las escrituras a bronce/RAG/CSV (L525–542) ocurren **antes** del gate y las cabezas. **El grafo se alimenta de datos incompletos**.

**Consecuencia:** El `ml-detector` **no cumple con la arquitectura tricapa** del paper (arXiv:2604.04952). Las cabezas existen, pero **no influyen en el veredicto ni en el grafo**.

---

---
## **🧠 Respuestas a las Preguntas del Consejo (Bloque 1-3)**

---

### **🔴 Bloque 1: Las Cabezas Rotas (P1–P3)**
#### **P1: ¿Son recuperables Ransomware y Traffic?**
**Respuesta técnica:**
- **Ransomware (1/10 features reales):**
   - El feature `entropy` está **mal implementado** (varianza de longitud de paquete ÷ 100,000, no entropía de Shannon).
   - **Problema de diseño:** La entropía de Shannon es una métrica estándar para detectar patrones anómalos en tráfico (ej: cifrado, exfiltración). Usar varianza de longitud **no captura la esencia del ransomware** (que suele cifrar archivos, generando tráfico con alta entropía).
   - **¿Recuperable?** **Sí, pero requiere:**
      1. Reimplementar el extractor de `entropy` para calcular **entropía de Shannon real** sobre los bytes de payload (o, si no hay payload, sobre las longitudes de paquete con un modelo probabilístico correcto).
      2. **Reentrenar el modelo** con datos etiquetados de ransomware real (ej: muestras de MITRE ATT&CK T1486).
      3. **Validar** que el nuevo feature discrimina mejor que el actual (medir AUC/F1).

- **Traffic (5/10 features constantes):**
   - Features como `source IP entropy`, `dst IP concentration`, y `protocol variety` están **hardcodeados a 1.0f**.
   - **Problema de diseño:** Estos features son **críticos** para detectar tráfico anómalo (ej: escaneo de puertos, exfiltración a IPs externas). Si son constantes, el modelo **no puede aprender patrones**.
   - **¿Recuperable?** **Depende:**
      - Si los datos de `NetworkFeatures` **no contienen la información necesaria** (ej: no hay acceso a los bytes de payload o a metadatos de IP), **no es recuperable**.
      - Si los datos **sí están disponibles** pero no se extraen, **sí es recuperable** reimplementando el extractor para leer:
         - `source_ip_entropy`: Calcular entropía de Shannon sobre la distribución de IPs fuente en el flujo.
         - `dst_ip_concentration`: Calcular el índice de Gini o entropía sobre IPs destino.
         - `protocol variety`: Contar protocolos únicos en el flujo.

  **Conclusión:**
   - **Ransomware:** Recuperable con cambios en el extractor + reentrenamiento.
   - **Traffic:** **No recuperable en su forma actual** si no se tienen datos de IP/protocolo en `NetworkFeatures`. **Recomendación:** Si no hay datos, **eliminar la cabeza** y documentar por qué (falta de features discriminativos).

---

#### **P2: ¿Cabeza con peso 0 vs. cabeza ausente?**
**Postura científica:**
- **Cabeza con peso 0 en noisy-OR:**
   - **Ventaja:** Mantiene la arquitectura tricapa **explícita** (transparencia).
   - **Riesgo:** Si el peso es 0, **no contribuye al veredicto**, pero puede generar confusión ("¿por qué está ahí si no hace nada?").
- **Cabeza ausente:**
   - **Ventaja:** **Honestidad radical**: si una cabeza no es fiable, no debe estar en el sistema.
   - **Riesgo:** **Rompe el contrato del paper** (tricapa) y puede requerir cambios en el grafo (ej: el firewall espera 4 cabezas).

**Decisión propuesta:**
- **Para Ransomware:** **Mantenerla con peso 0 temporalmente** (hasta que se reentrene), pero **documentar claramente** que su peso es 0 y por qué.
- **Para Traffic:** **Eliminarla** si no es recuperable (P1). Si se elimina, actualizar el paper y el grafo para reflejar que el sistema es **bicapa** (L1 + Internal + DDoS).

---

#### **P3: ¿Debe sobrevivir la cascada L748 (Traffic → Internal)?**
**Análisis:**
- La cascada actual:
  ```cpp
  if (traffic.is_internal()) {
      Internal::predict(...)  // Solo corre si Traffic dice que es interno
  }
  ```
- **Problema:** Si Traffic es no fiable (5/10 features constantes), **el gate es arbitrario**.
- **Alternativas:**
   1. **Eliminar la cascada:** Correr **Internal siempre**, desacoplado de Traffic.
      - **Ventaja:** Internal es la cabeza más fiable (7/10 features reales).
      - **Riesgo:** Aumenta el coste computacional (pero es despreciable, §7.1).
   2. **Mantener la cascada, pero con Traffic fiable:**
      - Requeriría **reimplementar Traffic** (P1) antes de usarla como gate.

**Decisión propuesta:**
- **Eliminar la cascada (opción 1)**. **Internal debe correr siempre**, ya que:
   - Es la cabeza más fiable.
   - El coste es mínimo (0.58 μs por predicción).
   - **Traffic no es fiable actualmente**, por lo que su decisión de dominio **no debe gatear nada**.

---

---

### **🟡 Bloque 2: El Cableado (P4–P6)**
#### **P4: ¿Ratificar noisy-OR como operador de combinación?**
**Análisis del operador propuesto:**
```math
P = 1 - \prod_{i=1}^{n} (1 - p_i), \quad \text{donde } p_i = \text{fiabilidad}_i \times \text{score}_i
```
- **Ventajas:**
   - **Monótono:** Una cabeza que dispara (score alto) **no puede ser suprimida** por otras cabezas con score bajo.
   - **Corroboración:** Si dos cabezas disparan (ej: Ransomware + Internal), el veredicto **se refuerza** (P > max(p_i)).
   - **Robusto a cabezas no fiables:** Si una cabeza tiene fiabilidad ≈ 0, su contribución es ≈ 0.
- **Alternativas descartadas:**
   - **Media ponderada:** Diluye señales fuertes (ej: Internal dispara, pero Traffic con peso bajo lo arrastra hacia abajo).
   - **Max de N:** No captura corroboración (dos cabezas disparando no suman más que una).
   - **Dempster-Shafer:** Complejidad innecesaria para este caso.

**Decisión:**
✅ **Ratificar noisy-OR**. Es el operador que mejor se alinea con:
- La necesidad de **no supresión** (monotonía).
- La **corroboración** entre cabezas.
- La **fiabilidad medida** (pesos basados en datos, no en votaciones).

---

#### **P5: ¿Injertar cabezas en `provenance` o mantener eje fast-vs-ml?**
**Análisis:**
- **Opción A: Injertar cabezas en `provenance` (N fuentes homogéneas)**
   - **Ventaja:** Simplifica el código (todas las cabezas son iguales).
   - **Riesgo:** Cambia la semántica de `authoritative_source` (hoy distingue fast vs. ml).
- **Opción B: Mantener eje fast-vs-ml + noisy-OR aparte**
   - **Ventaja:** Preserva la estructura actual del wire.
   - **Riesgo:** Más complejidad (dos lógicas de combinación).

**Decisión propuesta:**
- **Opción A (Injertar en `provenance`)**. Razones:
   - El noisy-OR **ya requiere una colección de veredictos** (provenance).
   - El eje fast-vs-ml **no es necesario** si todas las cabezas (incluyendo fast) se tratan como fuentes homogéneas.
   - **Simplifica el código** y hace el sistema más transparente.

**Acciones:**
1. Añadir las 4 cabezas como `add_verdicts()` en `provenance`.
2. Calcular el noisy-OR sobre `provenance->verdicts()`.
3. **Eliminar `authoritative_source`** (o marcarlo como obsoleto).

---

#### **P6: ¿Cómo coordinar el des-gateo en dos componentes (`ml-detector` + firewall)?**
**Análisis:**
- **Problema:** El firewall filtra eventos con `attack_detected_level1() == false` (L583 en `zmq_subscriber.cpp`).
- **Solución requerida:**
   1. **En `ml-detector`:**
      - Mover el veredicto y las escrituras a disco **después de las cabezas** (post-L819).
      - Eliminar el gate de L1 para Internal (y Traffic, si se recupera).
   2. **En `firewall-acl-agent`:**
      - **Relajar el filtro** para que no descarte eventos basándose **solo en L1**.
      - **Nueva lógica:** Si cualquier cabeza en `provenance` marca el evento como malicioso, el firewall **no lo descarta**.

**Decisión propuesta:**
- **PR atómico** (un solo commit) que:
   1. Modifica `zmq_handler.cpp` para:
      - Mover el veredicto y escrituras a post-L819.
      - Eliminar el gate de L1 para Internal.
      - Injertar cabezas en `provenance` + noisy-OR.
   2. Modifica `zmq_subscriber.cpp` para:
      - Reemplazar `attack_detected_level1()` por una comprobación de `provenance->final_decision()`.
- **Razón:** Un PR atómico **garantiza consistencia** entre ambos componentes.

---

---
### **🟢 Bloque 3: Persistencia y Grafo (P7–P8)**
#### **P7: ¿Cómo garantizar que el reordenamiento no rompe `correlation_v1`?**
**Análisis:**
- Los tests `test_correlation_roundtrip` y `correlation_v1_golden_vectors` validan que:
   - Los datos escritos en bronce **coinciden con un formato esperado**.
   - El grafo (Kuzu) puede leer estos datos sin errores.
- **Riesgo:** Si se reordenan las escrituras, los golden vectors **pueden no coincidir**.

**Solución propuesta:**
1. **Regenerar los golden vectors** con el nuevo orden de escrituras.
   - Ejecutar el pipeline con el nuevo código y **capturar la salida** como nuevos golden vectors.
2. **Validar que el grafo sigue funcionando**:
   - Correr `correlation_v1` con los nuevos datos y verificar que:
      - No hay errores de parsing.
      - Las consultas al grafo devuelven resultados consistentes.
3. **Documentar el cambio** en `docs/BACKLOG.md`:
   - "Los golden vectors se regeneraron en [fecha] debido al reordenamiento de escrituras (Defecto C)."

**Decisión:**
✅ **Regenerar golden vectors**. Es la única forma de garantizar que el contrato `correlation_v1` sigue válido.

---

#### **P8: ¿Debe `ml_context` poblarse con la salida de las cabezas?**
**Análisis:**
- Actualmente, `ml_context` tiene campos como `level_2_category` y `level_3_subcategory` **hardcodeados a "UNKNOWN"** (L505–517).
- **Problema:** Se pierde información valiosa (ej: qué cabeza detectó qué).

**Solución propuesta:**
- **Poblar `ml_context` con:**
   - `level_2_category`: Resultado de DDoS/Ransomware (si aplican).
   - `level_3_subcategory`: Resultado de Internal/Traffic (si aplican).
   - `attack_family`: **No hardcodear**. Usar el valor real de la cabeza que detectó el ataque (ej: si Ransomware dispara, `attack_family = "RANSOMWARE"`).
- **Beneficio:** El RAG y el grafo **tendrán datos más precisos** para análisis posterior.

**Decisión:**
✅ **Poblar `ml_context` con los resultados de las cabezas**. Eliminar el hardcodeo de `"RANSOMWARE"` (Defecto `DEBT-RAG-ATTACKFAMILY-HARDCODED-001`).

---

---
---
## **📌 Plan de Acción Propuesto (Fase 2)**
**Orden de prioridad (P0 → P3):**
| Paso | Acción | Dependencias | Gate de Medición |
|------|--------|--------------|------------------|
| **0** | **Decidir P1–P3** (cabezas rotas) | Ninguna | Consenso del Consejo |
| **1** | **Reimplementar extractores** (Ransomware/Traffic) | P1 | Features reales validados |
| **2** | **PR atómico:** | | |
|      | - Mover veredicto y escrituras a post-L819 | P4–P6 | Tests unitarios (noisy-OR, golden vectors) |
|      | - Injertar cabezas en `provenance` | P5 | `provenance->verdicts()` poblado correctamente |
|      | - Eliminar gate de L1 para Internal | P3 | Internal corre siempre |
|      | - Relajar filtro en firewall | P6 | Firewall no descarta eventos válidos |
| **3** | **Regenerar golden vectors** | P7 | `test_correlation_roundtrip` pasa |
| **4** | **Poblar `ml_context`** | P8 | RAG contiene datos reales |
| **5** | **Stress test con latencia** | Todos | Latencia total < 10 ms |
| **6** | **pcap relay e2e en hardware** | Paso 5 | Números para el paper |

---

---
## **⚠️ Riesgos y Mitigaciones**
| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| **Ransomware/Traffic no son recuperables** | Media | Alto | Documentar y eliminar cabezas no fiables (P2). |
| **Golden vectors no regenerables** | Baja | Alto | Validar manualmente el formato de bronce. |
| **Firewall descarta eventos válidos** | Media | Crítico | Tests de integración con firewall. |
| **Noisy-OR no funciona como esperado** | Baja | Alto | Tests unitarios exhaustivos (P4). |
| **Latencia supera 10 ms** | Baja | Medio | Benchmark en hardware real (Paso 6). |

---

---
## **🎯 Conclusión y Recomendación Final**
1. **Prioridad P0:**
   - **Arreglar Defectos A, B y C** (veredicto precoz, gate de L1, persistencia pre-inferencia).
   - **Mover el veredicto y escrituras a post-L819** + **eliminar gate de L1 para Internal**.
   - **Injertar cabezas en `provenance` + noisy-OR**.

2. **Prioridad P1:**
   - **Decidir el futuro de Ransomware/Traffic** (P1–P3):
      - **Ransomware:** Reimplementar extractor de entropía + reentrenar.
      - **Traffic:** **Eliminar** si no es recuperable (features constantes).
   - **Regenerar golden vectors** (P7).

3. **Prioridad P2:**
   - **Poblar `ml_context`** con resultados reales (P8).
   - **Relajar filtro en firewall** (P6).

4. **Validación:**
   - **Tests unitarios** para noisy-OR, golden vectors, y `provenance`.
   - **Stress test** con tráfico real (latencia, precisión).
   - **pcap relay e2e** en hardware de producción.

---
---
### **📜 Documentación Obligatoria**
- **Actualizar `docs/BACKLOG.md`** con:
   - Las deudas técnicas resueltas (`DEBT-VERDICT-MONOCAPA-001`, `DEBT-BRONZE-WRITTEN-PRE-HEADS-001`, etc.).
   - Los cambios en la arquitectura (tricapa → bicapa si Traffic se elimina).
   - Los nuevos golden vectors.
- **Actualizar el paper (arXiv:2604.04952)** para reflejar:
   - La arquitectura **real** (no la ideal).
   - Los límites de las cabezas (ej: "Ransomware: en desarrollo, peso 0 temporal").

---
---
### **🚀 Próximos Pasos (para el Consejo)**
1. **Votación sobre P1–P3** (cabezas rotas):
   - ¿Se recuperan Ransomware/Traffic o se eliminan?
   - ¿Cabeza con peso 0 vs. ausente?
   - ¿Se elimina la cascada L748?

2. **Asignar responsables:**
   - **Reimplementación de extractores:** [Equipo de ML].
   - **PR atómico:** [Equipo de Backend].
   - **Regeneración de golden vectors:** [Equipo de QA].
   - **Tests de firewall:** [Equipo de Integración].

3. **Fechas tentativas (sin presión, solo orden):**
   - **Semana 1:** Decisión sobre P1–P3 + inicio de reimplementación.
   - **Semana 2:** PR atómico + regeneración de golden vectors.
   - **Semana 3:** Stress test y validación final.

---
---
**Aironman DirtDiver, el listón que has puesto es el correcto.** Un sistema que protege hospitales **no puede tener sombras entre su código y su diagrama**. Con este plan, el `ml-detector` será **fiable, determinista y honesto** —o sabremos exactamente qué parte no lo es y por qué.

**¿Qué decisiones del Consejo (P1–P3) quieres que prioricemos primero?** ¿O prefieres que profundicemos en algún punto técnico concreto?

fdo mistral