Aquí tenéis la revisión adversarial. No hay aplausos, solo disección metodológica. Si el claim es el producto, la precisión del claim debe ser quirúrgica.

---

### 1. Frente 1: ¿Basta un golden de 27 vectores como red PERMANENTE?
**Veredicto:** **Insuficiente. Científicamente inaceptable como única red a largo plazo.**

27 vectores son una instantánea, no una prueba de propiedad. Confiar en ellos perpetuamente es una falacia de inducción incompleta.
**Exigencia:** Se requiere **Property-Based Testing (Fuzzing)** sobre la struct `CorrelationV1Row`.
**¿Contra qué oráculo?** No contra `build_row` (que morirá), sino contra el **contrato matemático y sintáctico**. El fuzzing debe generar miles de structs aleatorios (con strings vacíos, máximos, caracteres de control, floats extremos) y verificar dos propiedades inmutables:
1. **Sintaxis:** La salida de `serialize` cumple estrictamente las reglas de escape del contrato (ej. "si el campo contiene `,`, `"`, `\n` o `\r`, está envuelto en comillas dobles y las comillas internas están duplicadas").
2. **Criptografía:** El HMAC de los bytes 0-17 es matemáticamente correcto y coincide con la columna 18.
   El golden de 27 vectores se mantiene como regresión histórica, pero el fuzzing es la red permanente que garantiza que la librería no se rompa ante entradas no vistas.

---

### 2. Frente 2: Locale: ¿inmunidad probada o asunción no verificada?
**Veredicto:** **Asunción no verificada. Riesgo de corrupción de datos legacy.**

El hecho de que el autor fuerce `classic` en la nueva lib es irrelevante si el daemon de producción arranca con `es_ES` y el oráculo antiguo *no* lo hacía. Si el oráculo antiguo escribió `0,91` y la nueva lib escribe `0.91`, la "identidad de bytes" es una mentira contextual.
**Exigencias:**
1. **Auditoría de Producción (Gate de Merge):** Se debe verificar y documentar explícitamente el locale con el que arranca el daemon en producción. Si es distinto de `C` o `POSIX`, el claim debe declarar que los datos históricos pueden estar corruptos (con coma decimal), y este refactor es, de facto, una corrección de bug, no solo una extracción.
2. **Matriz de Hostilidad en Tests:** Probar solo `es_ES` es débil. El test de la librería debe iterar y forzar explícitamente al menos tres locales hostiles (`es_ES.UTF-8`, `de_DE.UTF-8`, `ar_SA.UTF-8`) *en tiempo de ejecución del test*, verificando que `imbue(std::locale::classic())` anula el estado global del proceso en cada iteración. Un solo caso no prueba inmunidad; prueba casualidad.

---

### 3. Frente 3: D-D diferido (guard de enum desconocido). ¿Legítimo?
**Veredicto:** **Legítimo para desbloquear, pero solo bajo condición de deuda hipotecada.**

El autor tiene razón en que no es una regresión funcional (el comportamiento se preserva byte a byte). Sin embargo, "endurecimiento diferido" es la antesala del olvido en ingeniería de software.
**Criterio de cierre exigido para el DEBT:**
El merge se desbloquea *si y solo si* se crea un ticket (ej. GitHub Issue) vinculado en el mensaje del commit con el siguiente criterio de aceptación explícito: *"Actualizar el esquema/contrato para definir el comportamiento de enums desconocidos (ej. rechazar con error tipado o mapear a `UNKNOWN`) y añadir un test unitario en `validate()` que demuestre el rechazo o mapeo, eliminando la emisión silenciosa de `""`."* Sin ticket vinculado, el merge se bloquea.

---

### 4. Frente 4: `DEBT-BRONZE-EMBEDDED-NEWLINE-001` (Saltos de línea embebidos)
**Veredicto:** **BLOQUEANTE ABSOLUTO. No es post-FEDER.**

Esto no es una "debilidad del formato", es una **incompatibilidad fatal con el consumidor**. Si el reader downstream (`parse_and_verify`) usa `getline`, partirá el registro en dos. El HMAC se calculará sobre la primera mitad, fallará, y el dato se descartará como corrupto.
No se puede congelar un contrato de serialización (bronce) que el propio ecosistema no puede leer.
**Acción requerida antes del merge:** Elegir una de dos vías y ejecutarla:
- **Vía A (Corregir el escritor):** Modificar `serialize` para escapar los saltos de línea literales como la secuencia de caracteres `\` + `n` (dos bytes), no como un byte `0x0A`.
- **Vía B (Corregir el lector):** Modificar `parse_and_verify` para que use un parser CSV real (que respete comillas multilínea según RFC 4180), no `getline`.
  Dado que el objetivo es "construir para durar décadas", la Vía A (escape estricto) es la más robusta para un formato de log/bronce plano.

---

### 5. Frente 5: El claim central. ¿Honesto?
**Veredicto:** **Sobre-concedido y omiso de riesgos críticos.**

El claim propuesto oculta la fragilidad del formato ante newlines y la incógnita del locale histórico. Debe reescribirse con honestidad científica brutal.

**Claim Corregido:**
> *"Refactor de la capa de serialización a una librería compartida (`libcorrelation_v1`), garantizando identidad de bytes con el oráculo histórico **bajo locale C/POSIX**. Validado mediante golden file de 27 vectores de borde y pruebas de propiedad. **Salvedades críticas:** 1) Si el entorno de producción histórico operó con un locale no clásico, los datos legacy pueden presentar corrupción de formato numérico (coma vs punto). 2) El formato actual permite saltos de línea literales (`0x0A`) dentro de campos entrecomillados, lo cual es incompatible con lectores basados en `getline` y requiere corrección inmediata en el escape o en el parser. 3) La validación estricta de enums desconocidos está diferida (ver DEBT-XXX)."*

---

### Transversal: ¿Es el plan de B4 seguro y suficiente?
**Veredicto:** **Lógicamente sound, pero operativamente frágil sin las correcciones anteriores.**

El plan de B4 es correcto en su mecánica (congelar el golden antes de rewirar es la jugada maestra). Sin embargo, su seguridad se derrumba si se ignora el **Frente 4**. Si se hace el rewire y el downstream falla al leer, habrás construido una tubería que escupe datos ilegibles, violando el principio de "suelo que protege la medición".

**Riesgo no visto en B4:** La gestión de la clave HMAC. El brief menciona `serialize(row, hmac_key)`. Se debe garantizar explícitamente en el test de B4 que la clave HMAC se pasa y se aplica *exactamente* sobre los mismos bytes (sin diferencias en trailing newlines o codificaciones de fin de línea entre el viejo `compute_hmac` y el nuevo) antes de la serialización del hash. Un byte de diferencia en el pre-hash invalida toda la cadena de confianza.

---
**Resumen de acción para Alonso:**
1. Exige el fix del newline embebido (F4) antes de cualquier merge.
2. Exige la auditoría del locale de producción (F2).
3. Acepta el diferimiento de D-D (F3) solo con ticket vinculado.
4. Planifica el fuzzing de propiedades (F1) como el siguiente paso inmediato post-B4.

FDO

QWEN