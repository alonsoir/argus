Aironman DirtDiver, tu brief es exhaustivo y refleja una disciplina técnica admirable. Vamos a desglosar las preguntas clave para el Consejo, **centrándonos en la evidencia, el riesgo medible y la economía de esfuerzo**. Aquí tienes un análisis estructurado, con preguntas concretas para cada punto y propuestas de experimentos o métricas que validarían las decisiones.

---

## **1. ¿Medir primero vs. Construir la capa Avro?**

### **Tesis actual:**
Medir el camino **CSV directo → correlation-engine → Kuzu** es suficiente para validar la **no-pérdida de datos** en el pipeline actual. Construir Avro/Parquet/Iceberg antes de la primera tortura sería **asumir** que el cuello de botella está en la serialización, no en la ingesta o el grafo.

### **Argumentos a favor de medir primero:**
- **Economía de esfuerzo:** Si el pipeline actual (CSV → Kuzu) ya pierde filas a caudal alto, el problema es **anterior a Avro**. Construir Avro no lo resolvería.
- **Aislamiento de variables:** El eje no negociable es la **aprendizaje de modelos ensemble desde nodos distribuidos**. La serialización es un detalle de implementación; el riesgo crítico es la **durabilidad y consistencia** de los datos.
- **Baseline medible:** El coste actual del `KuzuGraphSink` (0.86s/batch) es un dato concreto. Si la tortura demuestra que este coste es aceptable, se valida el suelo.

### **Argumentos en contra (para debate):**
- **Falso verde:** Si el pipeline CSV-directo **no pierde filas**, pero el **volumen real de producción** (con Avro/Parquet) sí lo haría (por ejemplo, por overhead de serialización), la medición sería **optimista**.
- **Costo de cambio:** Si luego se descubre que Avro es necesario, el refactor de `CorrelationWriter` podría requerir cambios en el injector y el consumidor.

### **Propuesta de validación:**
- **Experimento:** Ejecutar el injector adversarial con **CSV directo** y medir:
    - **Pérdida de filas** (comparar `rows_flushed` en `FlushResult` vs. filas inyectadas).
    - **Latencia por batch** (¿0.86s se mantiene estable bajo carga?).
    - **Uso de memoria** (¿el acumulador de `KuzuGraphSink` desborda?).
- **Métrica de corte:** Si la pérdida es **0%** y la latencia es **<1s/batch** a caudal máximo, el CSV-directo es válido para la primera tortura. Si no, se prioriza Avro.

---
## **2. Opción B (struct plano) vs. A (protobuf)**

### **Tesis actual:**
**Opción B** (`CorrelationV1Row` + adaptador) es mejor porque:
- **Desacople:** El injector no depende de protobuf.
- **Peso ligero:** No arrastra el schema completo de `NetworkSecurityEvent`.
- **Unificación:** El contrato ya existe como struct en el consumidor (`CorrelationRecord`).

### **Riesgos de B:**
- **Divergencia:** La conversión `protobuf → CorrelationV1Row` podría no ser byte-idéntica.
- **Mantenimiento:** Si el schema de `CorrelationV1Row` cambia, hay que actualizar **dos lugares** (productor y consumidor).

### **Mitigación propuesta:**
- **Test de equivalencia byte-idéntica:**
    - Input: Un `NetworkSecurityEvent` con todos los campos posibles (incluyendo edge cases: strings con comillas, timestamps límite, etc.).
    - Output: Comparar la salida de `build_row(event)` (viejo) vs. `event → row → build_row(row)` (nuevo).
    - **Assert:** Los bytes deben ser **idénticos**. Si falla, el test lo detecta **antes de merge**.

### **Pregunta al Consejo:**
¿Es suficiente este test para garantizar que **no hay divergencia**? ¿O hay casos donde la serialización de protobuf podría introducir diferencias no detectables por este test (ej: orden de campos, metadatos ocultos)?

---
## **3. ¿Qué le falta al injector adversarial?**

### **Casos actuales cubiertos:**
- `node_id` con comillas/backslash (H-1).
- Timestamps que disparan `temporal_anomaly`.
- Colisiones de `flow_uid`.
- Ráfagas que fuerzan flush inline.
- Volumen que desborda el acumulador.

### **Posibles casos faltantes:**
| **Categoría**               | **Ejemplo**                                                                 | **¿Por qué rompería el pipeline?**                          |
|----------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------|
| **Corrupción de datos**    | HMAC inválido (pero no por clave, sino por datos mal formados).           | El consumidor descarta la fila → pérdida de datos.         |
| **Esquemas incompatibles** | Campos faltantes en `CorrelationV1Row` (ej: `src_ip` vacío).               | Error en `build_row` o en Kuzu (NULL no esperado).          |
| **Carga maliciosa**        | `payload` con bytes no UTF-8 o SQL injection (ej: `'; DROP TABLE--`).    | Fallo en `execute(prepared)` o corrupción de la BD.         |
| **Concurrencia**           | Múltiples hilos escribiendo al mismo fichero CSV.                          | Corrupción del fichero → pérdida de filas.                 |
| **Límites de Kuzu**        | Batch con >10K filas (¿límite de transacción en Kuzu?).                   | Fallo en `COMMIT` → rollback silencioso.                    |
| **Tiempo real**            | Timestamps fuera de orden (ej: `ingested_at` futuro).                       | Fallo en `temporal_anomaly` o en el grafo.                  |

### **Propuesta:**
- **Añadir al injector:**
    - **HMAC inválido** (pero con datos bien formados, para probar el descarte).
    - **Campos nulos** (ej: `src_ip = ""`).
    - **Batch gigante** (ej: 50K filas) para probar límites de Kuzu.
    - **Timestamps desordenados** (ej: `ingested_at` en el pasado lejano).
- **Métrica:** % de filas descartadas por el consumidor (debe ser **0%** si el injector es correcto).

---
## **4. Injector-a-fichero vs. tcpreplay**

### **Tesis actual:**
El **NIC de VirtualBox** es un cuello de botella conocido ("Message too long", drops de MTU). Usar **injector-a-fichero** aísla el pipeline de este problema.

### **Argumentos a favor:**
- **Aislamiento:** Mide **solo el código de aRGus** (ingesta, grafo, durabilidad).
- **Reproducibilidad:** El fichero CSV puede reutilizarse para múltiples pruebas.

### **Argumentos en contra:**
- **Falso aislamiento:** En producción, el cuello podría ser **el NIC de las Raspberries** (no VirtualBox). Si no se mide ahora, se descubrirá tarde.
- **Diferencias de comportamiento:** Un fichero CSV no simula la **latencia de red** o **pérdida de paquetes** de un tcpreplay real.

### **Propuesta de compromiso:**
1. **Primera tortura:** Injector-a-fichero (para validar el pipeline interno).
2. **Segunda tortura:** tcpreplay con **CTU-13 Neris** (para medir el sistema completo, aceptando el techo de VirtualBox).
3. **Métrica clave:** Comparar la **pérdida de filas** entre ambos métodos. Si es similar, el NIC no es el cuello. Si es mayor en tcpreplay, el NIC es el problema.

---
## **5. Refactor `CorrelationWriter` → librería compartida**

### **Tesis actual:**
Extraer `CorrelationWriter` a `libcorrelation_v1` es el **primer ladrillo** del `argus-adapter-producer`, porque:
- **Reutilización:** Sirve a ml-detector, injector de tortura y futuro producer.
- **Desacople:** Separar serialización de lógica de negocio (ml-detector no debe saber cómo se serializa).

### **Riesgos:**
- **Sobre-anticipación:** El producer real podría necesitar **leer de log + ZMQ**, no solo serializar desde struct.
- **Acoplamiento oculto:** Si `libcorrelation_v1` asume que el input es siempre un struct, podría no servir para el producer real (que lee de logs).

### **Pregunta al Consejo:**
¿Es mejor **esperar** a tener el producer real y extraer entonces la librería (con requisitos claros), o **construir ahora** con la suposición de que el contrato `CorrelationV1Row` es estable?

### **Propuesta:**
- **Validar la suposición:** ¿El producer real **necesitará** leer de log + ZMQ, o puede adaptarse a `CorrelationV1Row`?
    - Si la respuesta es **sí**, entonces `libcorrelation_v1` es un buen ladrillo.
    - Si la respuesta es **no**, entonces el refactor actual podría ser **prematuro**.

---
## **6. HMAC en el banco de tortura**

### **Tesis actual:**
El HMAC en el injector **no es seguridad**, sino **correctitud de medición**:
- Sin HMAC válido, el consumidor descarta la fila → **pérdida de datos ficticia**.
- El objetivo es **garantizar que el consumidor acepte todas las filas inyectadas**.

### **Argumentos a favor:**
- **Aislamiento:** El banco de tortura no debe depender de la provisión de claves (DEBT-BRONZE-KEY-PROVISIONING-001).
- **Simplicidad:** Usar la misma clave para firmar y verificar es suficiente para el test.

### **Argumentos en contra:**
- **Acoplamiento:** Si el HMAC se genera en el injector con una clave fija, el banco **sí depende** de esa clave (aunque sea local).
- **Falso positivo:** Si el HMAC es incorrecto, el consumidor descarta filas → la medición sería **pérdida de datos**, no un fallo del pipeline.

### **Propuesta:**
- **Solución:** Que el injector **no firme** las filas, pero el consumidor **no verifique el HMAC** en modo tortura (flag `--skip-hmac`).
    - **Ventaja:** El banco no depende de claves.
    - **Riesgo:** Si el consumidor **sí verifica HMAC en producción**, el test no sería representativo.
- **Alternativa:** Usar una **clave de test fija** (ej: `0xDEADBEEF`) en el injector y el consumidor, documentada como **solo para tortura**.

---

---
## **Resumen de decisiones pendientes y experimentos propuestos**

| **Pregunta**                          | **Decisión actual**               | **Experimento/Validación propuesta**                          | **Métrica clave**                     |
|---------------------------------------|-----------------------------------|---------------------------------------------------------------|---------------------------------------|
| ¿Medir primero?                       | Sí (CSV directo)                  | Injector adversarial → medir pérdida de filas y latencia.     | % pérdida, latencia/batch.            |
| Opción B vs A                         | B (struct plano)                  | Test de equivalencia byte-idéntica.                           | Bytes idénticos en salida.            |
| ¿Qué falta en el injector?            | Casos de corrupción y límites.    | Añadir HMAC inválido, campos nulos, batch gigante.             | % filas descartadas.                  |
| Injector-a-fichero vs tcpreplay       | Injector-a-fichero (primera)     | Comparar pérdida de filas entre ambos métodos.               | Diferencia en % pérdida.              |
| Refactor `CorrelationWriter`          | Extraer a librería.               | Validar si el producer real usará `CorrelationV1Row`.         | Requisitos del producer.             |
| HMAC en tortura                       | Usar clave fija o `--skip-hmac`.  | Probar con y sin verificación de HMAC.                         | % filas aceptadas.                    |

---
## **Preguntas directas al Consejo de Sabios**

1. **¿Aceptáis el orden "medir primero" con el experimento propuesto (injector adversarial + CSV directo)?** ¿O veis un riesgo crítico que no se cubre?

2. **¿El test de equivalencia byte-idéntica es suficiente para validar la Opción B?** ¿O hay casos donde protobuf podría introducir diferencias no detectables?

3. **¿Qué otros casos de tortura añadiríais al injector?** (Ej: ¿ataques de inyección SQL en `payload`? ¿Batch con 100K filas?)

4. **¿Es legítimo posponer tcpreplay hasta después de validar el pipeline interno?** ¿O el NIC de VirtualBox es un cuello que debe medirse **ya**?

5. **¿El refactor a `libcorrelation_v1` es el primer paso correcto, o es prematuro?** ¿Deberíamos esperar a tener el producer real?

6. **¿Cómo manejar el HMAC en el banco de tortura sin acoplarlo a la provisión de claves?** ¿Clave fija? ¿Flag `--skip-hmac`?

---
**Observación final:**
El enfoque actual es **científico y pragmático**: cada decisión se basa en **mediciones concretas** (ej: `FlushResult`, test de equivalencia, % pérdida de filas). El Consejo debería validar si los experimentos propuestos **cubren todos los riesgos críticos** o si hay huecos. **¿Qué medición falta para estar seguros de que el pipeline no perderá datos en producción?**

FDO

MISTRAL