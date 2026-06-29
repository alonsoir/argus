**CONSEJO DE SABIOS — REVISIÓN ADVERSARIAL DAY 185**
*Sesión metodológica: no se aplaude, se cuartean las juntas de la arquitectura.*

---

### FRENTE 1 — Insuficiencia del golden de 27 vectores como única red permanente

**Dictamen:** Inadmisible. 27 vectores, por muy “rinconeros” que sean, son una cobertura anecdótica frente a un espacio de entradas de 18 columnas con tipos compuestos y semántica acoplada. Tras B4, la red tautológica cae y la única defensa es ese golden. Esto equivale a fiarlo todo a una muestra a mano, no a una propiedad.

**Ataque concreto:**
- La promesa “byte-idéntico al oráculo original” se sostiene sobre un conjunto de entrenamiento, no sobre un test. Si el oráculo tenía algún comportamiento no modelado en esos 27 vectores (p.ej., un path de escape de comillas con UTF-8 + backslash, o una combinación de campos que altera el orden de entrecomillado), no hay forma de detectarlo. Peor aún: el oráculo original ya no existirá para regenerar el golden.
- Los vectores fueron elegidos por el mismo autor que escribió el código. Hay un sesgo de confirmación estructural: se testean los rincones que él *vio*, no los que no vio.
- La decisión D‑B (“acotado por vectores adversariales enumerados”) se convierte en coartada para no hacer ingeniería de verdad. El claim “rechaza las clases conocidas” es honesto si se enumeran exhaustivamente; aquí la enumeración es artesanal, no sistemática.

**Exigencia mínima para el merge:**
- Un **fuzzer estructural** que genere filas `CorrelationV1Row` pseudoaleatorias (con distribución consciente de los dominios: strings con caracteres de control, doubles extremos, timestamps inválidos, longitudes de campo en el límite), las serialice con `serialize` y las compare **bit a bit** contra una *nueva referencia producida por el oráculo antiguo*, que debe mantenerse vivo en un binario separado *exclusivamente para el fuzz test*. Esto requiere congelar el binario del `CorrelationWriter` original antes de B4 (p. ej., en un contenedor Docker) y usarlo como oráculo determinista durante el fuzzing. Si B4 se despliega sin este arnés, el riesgo es irreversible.

---

### FRENTE 2 — Locale: la inmunidad no está probada, y la corrupción en producción es plausible

**Dictamen:** La situación es más grave de lo que el brief admite. No se ha verificado que el daemon de producción no esté corrompiendo el bronce hoy mismo. El D‑E no es una mejora: es un parche sobre una herida abierta cuyo alcance se desconoce.

**Anatomía de la duda:**
- El autor *cree* que corre bajo `es_ES` y por eso el locale global del proceso usaría coma decimal, pero el `build_row` original no forzaba `classic`. Si el daemon hereda `LANG=es_ES.UTF-8` (común en sistemas de ayuntamientos españoles), entonces `0.910000` se escribe como `0,910000` en el CSV actual. Esto rompe la validez del HMAC y la capacidad de cualquier consumidor que espere punto decimal.
- El golden fue capturado **pinchando artificialmente** `classic`. Eso no demuestra que el viejo código se comportara igual en producción. De hecho, si el locale de producción no era `C`/`POSIX`, el golden podría estar *inventando* un pasado que nunca existió. La “byte-identidad” probada es contra un artefacto de laboratorio, no contra el histórico real.
- El test de inmunidad con un único locale hostil (`es_ES`) es un teatrillo. Demuestra que `serialize` ignora ese locale, pero no que el `build_row` original no estuviera ya intoxicado. La pregunta fundamental no es si la lib nueva es robusta, sino **¿cuál es el bronce canónico?** Si el bronce histórico está corrupto, la lib debería replicar la corrupción (para no romper la continuidad) y luego planificar una migración. Si no lo está, hay que demostrarlo.

**Exigencias:**
- **Verificación del locale de producción real** antes de B4: capturar una muestra del CSV emitido por el daemon en su entorno de despliegue y comprobar el carácter del separador decimal. Esto es **condición de merge** sin excepciones.
- **Matriz de locales hostiles** (`de_DE.UTF-8`, `ar_SA.UTF-8`, `ja_JP.UTF-8`, `ru_RU.UTF-8`, `C`) ejecutando tanto el oráculo como la nueva lib en un entorno controlado. No se trata de “soportar”, sino de comprobar que bajo cualquier locale el oráculo y la lib producen exactamente la misma deriva (sea punto o coma), o bien que el oráculo siempre escribió punto porque su `ofstream` no heredaba locale (habría que inspeccionar la implementación de `operator<<` para `double` sin `imbue`). El brief debe documentar este comportamiento con precisión quirúrgica.

---

### FRENTE 3 — D‑D diferido: legítimo pero peligrosamente ambiguo

**Dictamen:** La decisión de diferir es técnicamente defendible (no regresión), pero la falta de un criterio de cierre blindado lo convierte en un agujero de *accountability*.

**Lo que se aplaza:**
- Hoy, un `DetectorSource` desconocido produce `""` en la columna 17. Eso es un agujero semántico: un valor desconocido no es lo mismo que “vacío”. El grafo Kuzu tratará ese string vacío como un valor legítimo, y cualquier agregación por `source` mezclará eventos sin fuente con eventos de fuente desconocida, envenenando las métricas.
- Diferirlo “un commit aparte” sin un issue formal, sin un deadline y sin un test que falle (porque la feature no existe) es una receta para que se pudra en el backlog.

**Condiciones para desbloquear el merge:**
- Apertura de un **DEBT issue** con:
    - Etiqueta `DEBT-BRONZE-ENUM-GUARD`.
    - Criterio de cierre: *“`validate()` rechazará filas cuyo `detector_source` no case con ninguno de los valores del enum `DetectorSource` definido en el contrato v1. La lista de valores legales estará incrustada en la lib (no en el adapter). Se añadirá un test que verifique que cualquier valor desconocido (fuzzing del entero subyacente) provoca error de validación.”*
    - Fecha límite de resolución: antes de que el primer adaptador externo (Suricata/Zeek) comience a escribir bronce. Si no hay fecha de adaptador, se fija un plazo máximo de 2 sprints.
- El commit de D‑D no puede ser silencioso: debe ir acompañado de una nota de breaking change en el CHANGELOG del contrato bronce (porque productores que ya emitieran `""` empezarían a ser rechazados). Esto obliga a una coordinación explícita.

---

### FRENTE 4 — `DEBT-BRONZE-EMBEDDED-NEWLINE-001`: bloqueante, no difierible

**Dictamen:** No es un defecto del formato, es una **bomba de relojería en el pipeline de ingestión**. Diferirla a post‑FEDER es aceptar que el grafo Kuzu ingerirá basura silenciosa durante un período indefinido, invalidando cualquier medición de pérdida.

**Razonamiento:**
- El formato bronce se define como “una fila por línea”. Si un campo legítimo (p.ej., `detector_tactic` con un salto de línea embebido por un sensor mal configurado) parte la línea física, el `parse_and_verify` basado en `getline` leerá dos registros espurios: uno truncado (HMAC inválido → descartado) y otro con los restos. La pérdida de datos es silenciosa, porque el HMAC del fragmento no validará y se tirará sin alarma aparente.
- El brief admite que el golden se capturó leyendo el fichero entero, no con `getline`. Es decir, el test de oráculo esquivó el problema real. La red del golden no cubre el parser.
- Si el primer adaptador externo (Suricata) empieza a producir eventos con `\n` en campos de texto libre, el sistema entrará en un estado de corrupción indetectable. La medición de “pérdida” que se pretende hacer con el injector adversarial quedará contaminada por pérdidas de serialización, no por el modelo.

**Condición de merge:**
- **Corrección del formato** antes de B4: o bien escapar los caracteres `\n`/`\r` en `serialize` (p.ej., `\n` → `\\n`) y actualizar el parser, o bien prohibir explícitamente esos caracteres en `validate()` y hacer que `to_row()` los filtre. La primera opción es más robusta.
- Si por algún motivo se decide no hacerlo, se debe documentar como una **limitación conocida del contrato v1**, con un mecanismo de defensa en el parser (al menos un contador de líneas malformadas y una alerta). Aun así, para una librería que se pretende notario único, delegar la integridad al parser es una negligencia.

---

### FRENTE 5 — El claim central: sobreconcedido y con omisiones graves

**Claim propuesto:** *"Refactor de la capa de serialización a una librería compartida, probado byte-idéntico contra un golden congelado y contra el oráculo en vivo, sobre 27 vectores incluidos los rincones del serializador, bajo locale classic, con el guard de enum desconocido (D-D) diferido a commit aparte sin regresión."*

**Salvedades que faltan y reescritura honesta:**

- **Sobre la cobertura:** “27 vectores” no son “los rincones del serializador”. Son 27 ejemplos seleccionados manualmente. El espacio real incluye interacciones no exploradas. El claim debe decir “27 vectores de regresión”, no “rincones del serializador”.
- **Sobre el oráculo:** se omite que el oráculo vivo desaparece en B4, dejando la verificación byte-idéntica dependiente exclusivamente de ese golden. Esto es una degradación crítica de la garantía que no se menciona.
- **Sobre el locale:** se omite que el golden fue capturado forzando `classic`, y que no se ha verificado el locale de producción real. El claim sugiere una inmunidad que no está comprobada.
- **Sobre el HMAC:** (ver Frente 6 abajo) no se menciona que la identidad de bytes de la columna HMAC depende de una clave secreta compartida; si no se garantiza su unicidad entre productores, el claim “mismos bytes para el mismo dato lógico” es falso para la columna 18.

**Claim honesto alternativo:**
*“Extracción de la serialización a `libcorrelation_v1`, verificada mediante un golden file de 27 casos capturados del oráculo original bajo locale C. Tras la sustitución del oráculo (B4), la única defensa de byte-identidad contra el viejo `build_row` será ese golden, sin cobertura exhaustiva ni fuzzing. Se desconoce el locale real del daemon en producción; si no es C, el bronce histórico puede estar corrupto. El guard de `detector_source` desconocido permanece ausente (comportamiento permisivo heredado). El formato no escapa saltos de línea embebidos, lo que puede romper el parser de ingesta. La identidad del HMAC entre productores requiere una clave secreta común, aún no definida en el contrato.”*

---

### FRENTE 6 (TRANSVERSAL, NO LISTADO) — El HMAC como parte del contrato destruye la promesa “mismos bytes”

**Ataque de raíz:**
El brief define el contrato bronce como 19 columnas, siendo la 18 un HMAC-SHA256 sobre las 0‑17. Exige que todos los productores escriban **los mismos bytes** para el mismo dato lógico. Pero la función `serialize(row, hmac_key)` recibe la clave de fuera. Si cada adaptador usa una clave distinta (o peor, si la rota), dos filas con idénticas columnas 0‑17 tendrán HMAC distintos. Por tanto, **no son los mismos bytes**. Esto rompe la premisa de que el grafo recibe un formato uniforme: el HMAC se convierte en un identificador del productor, no en un integrity check del dato.

**Implicaciones:**
- Cualquier comparación de filas entre fuentes (ej: Suricata vs aRGus para el mismo evento sintético) fallará, porque el HMAC diferirá.
- El golden congelado incluye HMAC calculado con la clave de ml‑detector. Si otro productor no usa la misma clave, la comparación byte-idéntica con el golden no aplica, y la lib compartida es papel mojado para esa columna.
- Si el propósito del HMAC es asegurar que la fila no fue manipulada *en tránsito*, el secreto debe ser compartido entre el escritor y el lector. Pero el lector (grafo) necesita conocer la clave de cada productor para validar, lo cual es una pesadilla de gestión de secretos.

**Solución de diseño exigible:**
- El HMAC **no debe formar parte de los “mismos bytes”** que definen la compatibilidad entre productores. Es una capa de integridad por encima del contrato. El contrato deberían ser las columnas 0‑17, y el HMAC un apéndice opcional o gestionado por cada productor con su propia clave. Así, la lib `serialize` produciría solo los bytes 0‑17, y el HMAC se calcularía externamente.
- O bien, el secreto HMAC se convierte en parte de la especificación del contrato bronce v1 (mismo valor para todos los productores), almacenado de forma segura y distribuido. Esto convierte a la lib en custodio de un secreto compartido, con el consiguiente riesgo de fuga. ¿Es eso aceptable para un sistema open-source?
- Esta decisión es previa a B4 y **bloquea el diseño actual**. No se puede diferir.

---

### CUESTIÓN TRANSVERSAL — ¿Es seguro y suficiente el plan de B4?

**Respuesta: No es seguro, y es insuficiente si no se atienden los frentes anteriores.**
- B4 elimina la comparación viva y reduce la defensa al golden. Sin fuzzing ni verificación del locale de producción, la probabilidad de introducir divergencias no detectadas es alta.
- La transición debe incluir un período de **doble escritura** (write_record antiguo y nuevo lado a lado) en un entorno de staging, con un diff automático de los CSV resultantes durante al menos una semana de tráfico real, antes de eliminar el oráculo. El golden es una instantánea; la doble escritura es un test de regresión continuo sobre datos vivos.
- El riesgo oculto de la clave HMAC (Frente 6) invalida el concepto mismo de “lib compartida para bytes idénticos” si no se resuelve. B4 no debería ejecutarse sin una decisión firme sobre la gestión de esa clave.

---

**Conclusión del consejo:** El refactor tiene mérito estructural, pero la verificación es insuficiente, la semántica del HMAC está rota, y la confianza en el golden como única red es una ingenuidad peligrosa. Se requiere trabajo adicional antes del merge.

FDO

DEEPSEEK