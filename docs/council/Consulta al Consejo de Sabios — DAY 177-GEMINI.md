## Acta de Consenso del Consejo de Sabios — DAY 177

**Proyecto:** aRGus NDR

**Línea de Control:** `feature/day170-community-id-protobuf`

**Estatus:** Ratificación unánime con enmiendas operativas en el microscopio de pruebas.

---

### 0. Ratificación de Decisiones (Sección 2) — **APROBADAS 8/8**

* **B/Opción 1 (Aislamiento de C++):** **Ratificado.** Mantener el *correlation-engine* agnóstico a las dependencias de Protobuf mediante strings simbólicos en la columna 17 es una decisión de arquitectura higiénica. Evita la fuga de abstracciones hacia la zona bronce.
* **node_id isomorfo (`synth-node-00`):** **Ratificado.** Conceptualmente impecable. En el diseño de redes, un inyector simula la interfaz de captura de **un** punto de observación. La entropía y unicidad del `flow_uid` debe residir exclusivamente en la dinámica espacial y temporal del tráfico (la 5-tupla combinada en el `community_id`).
* **Alineamiento del protocolo benigno:** **Ratificado.** No se maquilla el motor de correlación para aceptar inconsistencias; se eleva la fidelidad de la simulación del inyector.

---

### 1. Directivas del Consejo (Q1 – Q5)

#### Q1. Dirección del fix de `ROWGAP-001` (Inyector de Test vs. Rigor)

**Fallo de lógica detectado en la hipótesis (d):** El argumento de que *"los reenvíos son inocuos por diseño porque generan distinto `community_id` y por ende distinto flujo"* contiene un riesgo oculto. Si el inyector repite un `event_id` sintético con una 5-tupla mutada aleatoriamente, el motor de correlación procesará **dos flujos válidos pero artificiales**. Esto rompe el determinismo estricto en los tests de integración del pipeline de analítica (CI/CD), donde el número exacto de filas en bronce debe ser un invariante matemático respecto al pcap/set de entrada.

**Consenso:** **Implementar Opción (b).**

* El inyector no requiere la complejidad de un protocolo de confirmación de aplicación (capa superior), pero la infraestructura de transporte local no puede ser destructiva por negligencia de configuración.
* Se descarta (d) por introducir indeterminismo en CI/CD. Se descarta (c) por sobreingeniería en esta fase.
* **Acción:** Cambiar a `send()` bloqueante con un timeout acotado (`zmq::setsockopt(ZMQ_SNDTIMEO, ...)`). Si el pipeline está listo, la entrega local a través de `PUSH/PULL` en memoria/IPC debe ser instantánea. Si salta el timeout, se lanza un `std::runtime_error` que tire el test. El CI debe fallar ante la saturación del buffer, nunca silenciarlo.

---

#### Q2. Realismo del Benigno vs. Cobertura del Descarte (`nullopt`)

**Consenso:** **Dualidad de Operación (Invariante Determinista + Fuzzing de Control).**
No debemos sacrificar la verificación del camino de descarte (`discard path`), pero tampoco podemos permitir que el ruido aleatorio gobierne la Zona Bronce de forma impredecible.

**Acción:** Estructurar el inyector bajo un modelo de **Semilla y Perfil (`Profile`)**:

1. **Perfil por Defecto (`--mode strict-corelight`):** 100% TCP/UDP (50/50). Garantiza que si inyectas $N$ eventos, obtienes exactamente $N$ registros en bronce. Es el guardián del CI.
2. **Perfil de Cobertura (`--mode extended` o parámetro `--icmp-ratio 0.05`):** Inyección fija y determinista de un 5% de tráfico sin puertos (ej. ICMP).

* **El truco del validador:** Para mantener el test automatizado libre de flujos ciegos, el log del propio inyector debe discriminar cuántos flujos eran elegibles para `community_id`. El *diff* de conjuntos propuesto en la Sección 3 se calculará bajo la premisa:

$$\{Written\ in\ Bronze\} == \{Injected\} \setminus \{Injected_{Non-IP/ICMP}\}$$

---

#### Q3. Encomienda y Destino Documental (ADR-055)

**Consenso:** **Absorción Completa en ADR-055.**
No se justifica fragmentar la arquitectura en un ADR exclusivo para `ROWGAP`. El propósito de la **ADR-055** es definir el *Framework de Pruebas Deterministas y Herramientas de Simulación del Ecosistema aRGus*.

El reencuadre de la deuda (de pérdida a comportamiento bidireccional del socket ZMQ) junto con la especificación del *diff de conjuntos* como métrica oficial de salud del pipeline debe quedar consagrado dentro de la sección de **"Garantías de Transporte en Entornos de Simulación"** de la propia ADR-055.

---

#### Q4. Gobernanza y Trazabilidad del Hallazgo de Protocolo

**Consenso:** **No requiere ID de deuda independiente.**
El error de consistencia (`protocol_number` != `protocol_name`) y el descarte masivo por protocolos aleatorios se clasifica como un **bug de bloqueo del camino de ejecución principal (Camino A/B)** descubierto durante la fase de cableado del E2E. El comentario `DAY 177 (A)` es suficiente en el histórico del código, siempre y cuando la resolución del problema quede explícitamente citada en el cierre del *Merge Request* de la rama `feature/day170-community-id-protobuf`. Las deudas (`DEBT-ID`) se reservan para compromisos explícitos de diseño que se postergan; esto fue un fix inmediato.

---

#### Q5. Alerta de Arquitectura: Divergencia en Bronce (`DETECTOR_SOURCE_DIVERGENCE`)

El Consejo toma nota de la evidencia: **9 de 159 filas** marcadas con divergencia de origen. Esto demuestra que la telemetría intermedia funciona y que el motor no homogeneiza los datos a la fuerza.

> ### ⚠️ Directiva Temprana para la Ingesta en Kuzu Graph / Gold
>
>
> La columna 17 simbólica no debe ser aplanada al llegar a la base de datos de grafos. Si un flujo posee el atributo `DETECTOR_SOURCE_DIVERGENCE`, el cargador de la zona Gold deberá tratar este registro con una heurística de **"Voto de Calidad"** o bifurcar las aristas del grafo para reflejar que los sensores no han alcanzado el consenso respecto a la naturaleza del flujo. La divergencia es en sí misma una métrica de detección de anomalías en el despliegue distribuido. Se mantiene la línea de diseño libre hasta el cableado del consumidor.

---

### 2. Síntesis Métrico-Científica para el Diario de Ingenería

El reencuadre del problema de transporte propuesto por el PI es **científicamente correcto**. Al pasar de una métrica escalar (conteo de filas) a una métrica vectorial/conjuntista (intersección de conjuntos de `event_id`), el framework de validación de **aRGus** adquiere inmunidad frente a la anomalía del signo del buffer (duplicaciones vs. pérdidas).

El microscopio está calibrado. Adelante con el cierre de la rama.

FDO 
GEMINI