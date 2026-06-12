## Acta de Ratificación y Validación de Fidelidad — ADR-055 (v1)

**Proyecto:** aRGus NDR

**Línea de Control:** `feature/day170-community-id-protobuf`

**Estatus:** **APROBADO 8/8 (Consenso de Fidelidad Alcanzado)** **Ámbito:** Revisión de la integración del arbitraje de Alonso (Q1) y consistencia del borrador.

---

### 1. Confirmación de Fidelidad y Validación de Anulación de Árbitro (§3.3)

El Consejo de Sabios, en su sesión plenaria virtual, ha examinado la **Versión 1 del ADR-055** presentada por el Investigador Principal (PI). Los 8 asientos certifican de forma unánime que **este borrador refleja con precisión matemática y conceptual las deliberaciones y acuerdos del DAY 177**.

Respecto a la **anulación de árbitro efectuada por Alonso en la Pregunta 1 (Semántica de Entrega)**, el Consejo ratifica la validez formal del diseño bajo el siguiente dictamen técnico:

1. **Aceptación del Argumento de Fidelidad Coherente:** El Consejo asume el **Principio ordenador (§0)** como el axioma supremo de la zona `tools/`. Añadir un bucle de reintentos (Opción A) o bloquear con timeout el socket local (Opción B) para maquillar las métricas de la herramienta de pruebas habría violado la paridad operativa con el *sniffer* real, el cual opera bajo la misma restricción de `dontwait`. El suplantador debe reflejar la fragilidad o la robustez de la producción; de lo contrario, deja de ser un espejo válido.
2. **Legalidad del Precedente:** La anotación explícita de la anulación del árbitro en el §3.3 se considera técnicamente vinculante y consistente con el precedente del proyecto (**ADR-052 §3.11**). La gobernanza queda debidamente registrada para futuras auditorías del código o revisiones científicas del pipeline.

---

### 2. Desglose de Puntos Críticos y Enmiendas Menores por Componente

Los consejeros aportan los siguientes matices de estabilización antes del cierre y congelación del documento:

#### 2.1 Cobertura Determinista y el "Truco de la Semilla" (Sección 3.2 — Aportes de DeepSeek y Gemini)

El Consejo celebra la redacción de las "Dos Perillas" basadas en variables de entorno o flags (`ARGUS_PROTO_MIX=deterministic|realistic`).

* **Control de Regresión:** La fórmula de validación conjuntista basada en el conjunto complementario:

$$\{Written\ in\ Bronze\} == {Injected} \setminus \{Injected_{Non-IP/ICMP}\}$$



garantiza que el modo `realistic` no introduzca indeterminismo en el CI/CD, siempre que la semilla pseudoaleatoria esté fija en el *test harness*. Se da el visto bueno a la creación de la deuda `DEBT-INJECTOR-PROTO-MIX-001`.

#### 2.2 Trazabilidad Extrema de la Divergencia (Sección 3.5 — Aportes de ChatGPT y Gemini)

Se confirma el registro del aviso en la sección correspondiente. La preservación de `DETECTOR_SOURCE_DIVERGENCE` en la columna 17 simbólica de la Zona Bronce es un hito de telemetría fundamental. El Consejo reitera el mandato: **el lado consumidor (Gold / Kuzu Graph) en el ADR-054 tendrá prohibido realizar operaciones de aplanamiento sobre esta columna**. La divergencia no es ruido; es un dato analítico de primer orden.

#### 2.3 Evaluación del Riesgo de Secuencia (Sección 6 — Riesgos Adicionales)

El Consejo advierte que el **Riesgo 2 (`seq_in_window`)** debe ser monitorizado de cerca. En el tráfico real del *Neris*, el reúso de la 5-tupla dentro de una misma ventana de tiempo es un escenario posible en ataques de denegación de servicio o escaneos agresivos. Si el inyector sintético no transporta la secuencia, podríamos experimentar colisiones de `flow_uid` no deseadas en escenarios de estrés profundo. La inclusión de `DEBT-INJECTOR-SEQWINDOW-001 (P3)` en el radar de deudas es una medida de mitigación prudente.

---

### 3. Matriz de Cierre de Compromisos Operativos

Con la firma de este acta, se autorizan las siguientes acciones en el repositorio de la rama `feature/day170-community-id-protobuf`:

* [x] **ADR-055:** Pasa de estado `BORRADOR` a **`APROBADO`**. Se fusionará en la raíz de documentación técnica del proyecto.
* [x] **DEBT-INJECTOR-NODEID-001 (P0):** Se declara formalmente **CERRADA** tras la verificación empírica de las 102 filas isomorfas en la zona bronce.
* [x] **DEBT-INJECTOR-ROWGAP-001 (P1):** Se declara formalmente **REENCUADRADA Y CERRADA COMO CARACTERÍSTICA**.
* [ ] **DEBT-INJECTOR-DELIVERY-METRIC-001 (P2):** **ABIERTA**. Se delega en el PI el desarrollo del instrumento de *diff de conjuntos* en el script del E2E sintético.

---

El Consejo concluye la sesión felicitando al Investigador Principal por el rigor metodológico demostrado en el cableado final de la rama. La Zona Bronce cuenta ahora con un marco conceptual y práctico inmune a desviaciones de diseño.

**Adelante con el *Merge Request*. El microscopio está bloqueado y verificado.**

FDO
GEMINI
