# Consejo de Sabios — Day 185: Peer Review Adversarial (Kimi)

Aplico el mandato del brief: **no validar, atacar**. Mi objetivo es encontrar el agujero, no aplaudir la arquitectura.

---

## F1 — ¿Basta un golden de 27 vectores como red PERMANENTE?

**Veredicto: NO basta. Exigiría más, pero con una estrategia específica.**

El problema no es el número (27 es razonable para un espacio enumerado), sino la **naturaleza del espacio de entrada**. Los 24 vectores "rincon" fueron diseñados por un humano (Alonso+Claude) con sesgos de quien ya conoce la implementación. Esto es **test por enumeración de sospechas**, no por exploración sistemática del espacio.

**Ataque concreto:** El espacio de `CorrelationV1Row` tiene campos de tipos heterogéneos (strings, doubles, enums, timestamps). La interacción combinatoria entre:
- Strings con delimitadores CSV (`,`, `"`, `\n`, `\r`, `\t`)
- Doubles en fronteras de precisión (epsilon, max, min, subnormal, NaN, ±Inf)
- Timestamps en fronteras de epoch y overflow
- Combinaciones de campos opcionales/vacíos

...no está cubierta exhaustivamente. Un vector que pase `to_row` pero produzca una fila que `serialize` formatee diferente al oráculo podría existir en la intersección de dos rincones no considerados.

**Lo que exijo como condición de merge:**

1. **Fuzzing estructurado de la struct `CorrelationV1Row`** (no del protobuf): generar structs aleatorias válidas, serializar con `libcorrelation_v1`, y verificar que `validate` las acepta y que la serialización es determinista. Esto no requiere oráculo de bytes — prueba coherencia interna.

2. **Mutación del golden**: tomar los 27 vectores golden y aplicar mutaciones sistemáticas (cambiar un byte, cambiar un campo, permutar columnas) para verificar que `validate` rechaza lo que debe rechazar. Esto prueba la **frontera de validez**.

3. **Propiedad adicional a probar**: para cualquier `Row` que pase `validate`, `serialize(row) == serialize(deserialize(serialize(row)))` (si existe deserialización en la lib; si no, es deuda).

**Sobre "¿contra qué oráculo si build_row ya no existe?":** El oráculo de B4 no es `build_row`, es el **golden congelado**. El fuzzing no compara contra oráculo de bytes, compara contra invariantes (determinismo, validez, no-crash). Eso es suficiente para una red permanente complementaria.

---

## F2 — Locale: ¿inmunidad probada o asunción no verificada?

**Veredicto: La inmunidad está parcialmente probada; la asunción sobre producción es NO verificada. Este frente es el más peligroso del brief.**

**Ataque en tres capas:**

**Capa A — El test actual es insuficiente.** `es_ES` como único locale hostil es un caso de conveniencia (el del autor), no de diseño. Los locales problemáticos para CSV numérico incluyen:
- `de_DE` (coma decimal, punto como separador de millares)
- `fr_FR` (espacio como separador de millares)
- `ar_SA` (dígitos arábigos orientales, RTL potencial)
- `ja_JP` (dígitos de ancho completo en algunos contextos)
- `C` vs `POSIX` vs `en_US.UTF-8` (diferencias sutiles en grouping)

Una matriz de CI con al menos estos 5 locales debe ser **gate de merge**, no nice-to-have.

**Capa B — La pregunta de producción es crítica y no respondida.** El brief dice: "No se ha verificado bajo qué locale arranca el daemon en producción." Esto es **un bug activo potencial**, no una hipótesis. Si el daemon de aRGus arranca bajo `es_ES` (lo cual es plausible en un hospital de Badajoz), el bronce viejo **está emitiendo comas decimales ahora mismo**. Eso significa:
- El grafo Kuzu downstream recibe `0,910000` en lugar de `0.910000`
- El HMAC se computa sobre bytes con coma, no punto
- Cualquier adaptador futuro que fuerce `classic` producirá bronce **incompatible** con el histórico

**Esto es una ruptura de contrato silenciosa.** El D-E no es una mejora, es una corrección de bug. Y como corrección de bug, debe documentarse como **breaking change** para cualquier consumidor del bronce histórico.

**Capa C — El imbue por stream es correcto pero frágil.** `std::ostringstream` con `imbue` es locale-safe, pero cualquier código futuro que use `std::to_string`, `printf`, `fmt::format` sin locale explícito romperá la invariante. Recomendaría encapsular la formateación numérica en una función interna de la lib que **nunca** use `operator<<` directamente, sino una implementación locale-agnóstica propia (ej: `snprintf` con `"%.6f"` o `std::to_chars` si C++17+).

**Condición de merge:**
1. Matriz de CI con mínimo 5 locales hostiles como gate.
2. **Investigación documentada** del locale de arranque del daemon en producción (systemd service, contenedor, init script). Si es `es_ES`, el bronce histórico está corrupto y debe documentarse como known issue.
3. Encapsular formateo numérico en función interna de la lib, no depender de `operator<<` con `imbue`.

---

## F3 — D-D diferido: ¿legítimo o aplazamiento indefinido?

**Veredicto: LEGÍTIMO como no-bloqueante, pero con condiciones estrictas de cierre.**

**Análisis:** El argumento del autor es sólido. El `write_record` actual emite `""` para enum desconocido (preservado byte a byte en el golden, vector `rincon_16`). Diferir D-D no introduce regresión porque:
- El comportamiento observable no cambia
- El golden lo captura
- Es un endurecimiento (rechazar en lugar de aceptar silenciosamente), no una corrección

**Pero el peligro está en la semántica del enum desconocido.** Si col 17 es `DetectorSource` (7 valores conocidos), un enum desconocido en producción significa:
- Un nodo con versión más nueva de protobuf recibe un valor que un nodo más viejo no conoce
- El nodo viejo serializa `""` (el bronce pierde información)
- El grafo Kuzu no puede correlacionar por `source_sensor` porque el campo está vacío

Esto no es un bug del refactor, es una **limitación del contrato bronce v1**. D-D debería ser parte del diseño de `correlation_v2`, no un parche sobre v1.

**Condición de merge:**
1. **DEBT ticket con criterio de cierre explícito:** "Implementar guard de enum en col 17 con política de rechazo + logging; evaluar si el rechazo debe ser Error (fila descartada) o Warning (fila escrita con valor vacío pero trazable)". No "ya lo haré", sino "se hará en el sprint X con este criterio".
2. **Documentar en el contrato** que col 17 acepta valores fuera del enum conocido y los normaliza a `""`. Esto es honestidad científica: el claim actual debe reflejar que el contrato es permisivo, no estricto.

---

## F4 — DEBT-BRONZE-EMBEDDED-NEWLINE-001: ¿bloqueante o post-FEDER?

**Veredicto: POST-FEDER, pero con una salvedad crítica que el brief no menciona.**

**Análisis:** El vector con `\n` embebido produce una "línea" bronce que ocupa dos líneas físicas. El `parse_and_verify` basado en `getline` partirá el registro. Esto es una debilidad del **formato CSV**, no del refactor.

**PERO — y aquí está el ataque — el brief dice que el golden "lo captura bien leyendo el fichero entero".** Eso esconde una suposición: el reader downstream **también** lee el fichero entero. Si `parse_and_verify` usa `getline`, está roto. Si el reader de producción usa `getline`, está roto. La pregunta no es si el formato es débil (lo es), sino si **la producción actual ya está rota** para este caso.

**Investigación requerida antes de FEDER:**
1. ¿El reader downstream en producción usa `getline` o un parser CSV real?
2. ¿Ha habido eventos con `\n` embebido en campos string en el último mes? (query al bronce histórico)
3. Si la respuesta a (1) es `getline` y a (2) es "sí", entonces el bronce histórico tiene registros partidos y el HMAC no valida para ellos. Eso es un **bug de integridad de datos activo**.

**Si la producción usa un parser CSV real (que maneja comillas correctamente):** post-FEDER, con ticket de deuda para evaluar formatos alternativos (JSON Lines, Parquet, etc.) para `correlation_v2`.

**Si la producción usa `getline`:** esto es un bug activo que debe documentarse como known issue con workaround (escapar `\n` como `\n` literal o rechazar filas con `\n` embebido).

---

## F5 — Reescritura del claim

**Claim propuesto por el autor:**
> "Refactor de la capa de serialización a una librería compartida, probado byte-idéntico contra un golden congelado y contra el oráculo en vivo, sobre 27 vectores incluidos los rincones del serializador, bajo locale classic, con el guard de enum desconocido (D-D) diferido a commit aparte sin regresión."

**Claim corregido (honesto):**
> "Refactor de la capa de serialización a una librería compartida, probado byte-idéntico contra un golden congelado de 27 vectores (3 realistas + 24 rincones del serializador) y contra el oráculo en vivo bajo `std::locale::classic`, con cobertura de casos adversariales **acotada pero no exhaustiva** (D-B). El guard de enum desconocido (D-D) se preserva byte-idéntico al comportamiento permisivo existente (emisión de `""`) y se diferencia a commit posterior. La inmunidad a locale se verifica bajo `es_ES`; **no se ha verificado el locale de arranque del daemon en producción**. El formato bronce v1 tiene una debilidad conocida con newlines embebidos en campos string que afecta a readers basados en `getline`."

**Diferencias clave:**
- "acotada pero no exhaustiva" en lugar de implícitamente exhaustiva
- "preserva byte-idéntico al comportamiento permisivo existente" en lugar de "sin regresión" (que suena a mejora)
- "no se ha verificado el locale de arranque" como salvedad explícita
- "debilidad conocida con newlines embebidos" como parte del claim, no como deuda escondida

---

## Transversal: ¿El plan de B4 es seguro y suficiente?

**Veredicto: El plan de B4 es lógicamente correcto pero tiene un riesgo no mencionado.**

**Riesgo identificado — El golden captura `build_row` bajo `locale::classic`, pero `build_row` original NO forzaba `classic`.** Esto significa que el golden **no es byte-idéntico al oráculo histórico** si el oráculo histórico corría bajo `es_ES`. El golden captura "lo que debería haber sido", no "lo que fue".

**Consecuencia:** Tras B4, `write_record` emitirá bytes que coinciden con el golden, pero si el bronce histórico en producción tiene comas decimales (por `es_ES`), el nuevo `write_record` producirá **bronce incompatible con el histórico**. Esto es una ruptura silenciosa de compatibilidad hacia atrás.

**Mitigación requerida:**
1. Antes de B4, verificar una muestra del bronce histórico en producción. Si contiene comas decimales, el D-E es una **corrección de bug con breaking change**, no un refactor transparente.
2. Si hay comas decimales en producción, documentar el cambio de formato como breaking change y coordinar con el equipo del grafo Kuzu.

**Segundo riesgo (menor):** El rewire B4 elimina `build_row` y `compute_hmac`. Si algún otro módulo (test, herramienta de diagnóstico, script de migración) depende de ellos indirectamente, B4 romperá compilación. Recomendaría una búsqueda de símbolos (`grep -r build_row`) antes del commit.

---

## Resumen de condiciones de merge (Kimi)

| # | Condición | Prioridad |
|---|-----------|-----------|
| 1 | Fuzzing estructurado de `CorrelationV1Row` + mutación del golden | Alta |
| 2 | Matriz de CI con 5+ locales hostiles como gate | Alta |
| 3 | Investigación documentada del locale de arranque en producción | Alta |
| 4 | Encapsular formateo numérico en función interna locale-agnóstica | Media |
| 5 | DEBT ticket D-D con criterio de cierre explícito (no "ya lo haré") | Media |
| 6 | Verificar si bronce histórico tiene comas decimales (breaking change D-E) | Alta |
| 7 | Documentar DEBT-BRONZE-EMBEDDED-NEWLINE-001 con investigación de reader downstream | Media |
| 8 | Búsqueda de dependencias de `build_row`/`compute_hmac` antes de B4 | Baja |
| 9 | Reescribir claim con salvedades de F5 | Media |

**Señal vs ruido:** La señal más fuerte está en F2 (locale de producción) y en el riesgo transversal de B4 (breaking change silencioso por D-E). El ruido sería pedir más vectores golden sin estrategia, o bloquear por D-D sin argumento de regresión.

---

*Metodología aplicada: ataque sistemático a cada frente, distinción entre "no probado" y "probado insuficientemente", y búsqueda de interacciones no consideradas (D-E + bronce histórico).*

FDO

KIMI