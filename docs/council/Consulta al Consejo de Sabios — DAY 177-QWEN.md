Estimado equipo de aRGus NDR,

El Consejo ha revisado detenidamente los hallazgos, evidencias y propuestas del **DAY 177**. Se valora enormemente la rigurosidad en la verificación E2E y, sobre todo, la capacidad de diagnóstico para transformar un síntoma confuso (row-gap) en una causa raíz clara (garantías de entrega ZMQ).

A continuación, se emite la ratificación de las decisiones y las respuestas consensuadas a las preguntas planteadas.

---

### 0. Ratificación de Decisiones Tomadas (Sección 2)

El Consejo **ratifica por unanimidad** las tres decisiones de diseño:
1. **Col 17 como string:** Excelente decisión de arquitectura. Mantiene el `correlation-engine` agnóstico a protobuf, delegando la serialización/deserialización en los bordes (writer/reader). El contrato auto-descriptivo es más resiliente a la evolución del esquema.
2. **`node_id` isomorfo fijo (`synth-node-00`):** Pragmático y correcto. La unicidad del `flow_uid` debe depender de la 5-tupla (a través del `community_id`), no de la variabilidad artificial del inyector.
3. **Proto benigno forzado a TCP/UDP:** Correcto como solución inmediata para desbloquear la verificación E2E del camino feliz (camino A).

---

### 1. Respuestas a las Preguntas del Consejo

#### **Q1: Dirección del fix de ROWGAP-001 (Rigor de entrega del injector)**
**Veredicto del Consejo:** Optar por una combinación de **(a)** y **(b)**, rechazando **(d)** para el entorno de CI.
* **Razonamiento:** Aunque el injector es una herramienta de prueba, **la determinismo en CI es sagrado**. Un test que falla o pasa de forma no determinista (flaky test) erosiona la confianza en el pipeline y enmascara fallos reales. La opción (d) es inaceptable para CI. La opción (c) es sobre-ingeniería para una herramienta de test.
* **Recomendación específica:** Implementar **(b) `send()` bloqueante con un timeout corto y razonable** (ej. 100-500ms). A diferencia del sniffer de producción (que no puede permitirse bloquear el hilo de captura de paquetes), el inyector sintético *no tiene restricciones de rendimiento en tiempo real*. Su único trabajo es garantizar que el mensaje se encole para la prueba. Si se desea mantener la filosofía no bloqueante, entonces **(a) comprobar el return code de `dontwait` + 1 reintento acotado** es el mínimo indispensable.
* **Métrica:** Se aprueba el cambio de métrica propuesto: el éxito del test debe medirse con **diff de conjuntos** (`set(sent_event_ids) == set(written_event_ids)`), no con conteo de filas, eliminando la ambigüedad entre pérdida y reenvío.

#### **Q2: Realismo del benigno vs. cobertura del camino de descarte**
**Veredicto del Consejo:** Implementar **dos perillas (modos)** en el inyector.
* **Razonamiento:** Forzar 100% TCP/UDP es perfecto para el "camino feliz" y las aserciones deterministas de conteo en CI. Sin embargo, un sistema robusto debe probar explícitamente sus caminos de descarte (`nullopt`).
* **Recomendación:**
  - Modo `--deterministic` (por defecto en CI rápido): 100% TCP/UDP. Aserción: `count(written) == count(sent)`.
  - Modo `--realistic` (en suites de integración más profundas): ~90-95% TCP/UDP, 5-10% ICMP/otros. Aserción: `count(written) < count(sent)` Y `count(discarded_logs) > 0`. Esto valida que el descarte es una *característica* y no un *bug*.

#### **Q3: Alcance (¿Esto alimenta ADR-055?)**
**Veredicto del Consejo:** **Sí, absorber todo en ADR-055.**
* **Razonamiento:** El ADR-055 está definido para decisiones de injectors/golden/lib. La normalización del `node_id`, el tipo de dato de `authoritative_source` y, crucialmente, el **reencuadre metodológico de ROWGAP** (reconocer las limitaciones de ZMQ PUSH/PULL en el harness de pruebas y adoptar la métrica de diff de conjuntos) son decisiones arquitectónicas y de metodología de prueba que pertenecen a este documento. No amerita un ADR separado; enriquece el existente.

#### **Q4: Gobernanza (DEBT id para el hallazgo de proto)**
**Veredicto del Consejo:** **No crear un DEBT ID nuevo.**
* **Razonamiento:** Fue un bug latente descubierto y resuelto en el mismo ciclo de desarrollo (wiring y verificación del día). No es una deuda que se arrastra, sino un objetivo ("Completar A") que se cerró con éxito. El comentario `DAY 177 (A)` en el código y este acta del Consejo son suficiente trazabilidad. Crear un ticket de deuda para un bug corregido al instante es burocracia innecesaria.

#### **Q5: Aviso sobre Oracle Divergence en bronce**
**Veredicto del Consejo:** **Registrado como señal de éxito (Success Signal).**
* **Razonamiento:** Que 9 de 159 filas muestren `DETECTOR_SOURCE_DIVERGENCE` demuestra que la Decisión 1 (col 17 como string) está funcionando exactamente como se diseñó: el sistema preserva la procedencia real de la alerta sin forzar un valor por defecto.
* **Acción:** Ninguna por ahora. Este es un *hallazgo positivo* que se marcará como punto de verificación clave (checkpoint) cuando se cablee el lado consumidor (Kuzu / decisión gold) en días futuros.

---

### 2. Observación Final del Consejo

El trabajo del DAY 177 ejemplifica la madurez ingenieril: no se conformó con que el test "pasara" parcheando el síntoma, sino que se investigó el comportamiento de ZMQ, se entendió la dualidad pérdida/reenvío, y se propuso una métrica más honesta (diff de conjuntos).

Se autoriza proceder con la implementación del fix de Q1 (bloqueo controlado o reintento acotado en el injector) y la adición de la perilla de realismo (Q2) antes de dar por cerrada la rama `feature/day170-community-id-protobuf`.

*El Consejo queda a disposición para la revisión del PR resultante.*

FDO
QWEN