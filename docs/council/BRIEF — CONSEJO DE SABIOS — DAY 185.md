# BRIEF — CONSEJO DE SABIOS — DAY 185
## Extracción de `libcorrelation_v1` (capa de serialización bronce)

---

## Cómo leer este brief

Esto es **peer review adversarial**. Vuestro trabajo no es validar ni aplaudir: es
encontrar el agujero. El brief presenta lo que se construyó **y** los cinco frentes
donde el autor (Alonso, con Claude) desconfía de su propio trabajo. Atacad esos
frentes con saña. Si veis un sexto que no he listado, mejor todavía.

Principios del proyecto que aplican como criterio: **medir, no votar**; **Via Appia
Quality** (construir para durar décadas, piedra a piedra); **honestidad científica**
(el claim se publica salga como salga; la precisión del claim *es* el producto).

---

## 0. Contexto mínimo (para quien entra fresco)

aRGus NDR es un sistema open-source de detección y respuesta de red (C++20), para
hospitales, ayuntamientos y organizaciones pequeñas. Su eje científico: *¿pueden
modelos ensemble aprender de la experiencia acumulada de nodos distribuidos?*,
validado con un split MITRE disjunto. Todo lo de estos días es **"suelo que protege
la medición"**, no production-readiness.

El **contrato bronce `correlation_v1`** es una fila CSV de 19 columnas (0–17 datos,
18 = HMAC-SHA256 sobre 0–17) que alimenta el grafo Kuzu. Hoy lo produce solo aRGus.
Mañana lo producirán adaptadores de Suricata, Zeek, Wazuh y uno de un colaborador
("Andrés"). Todos deben escribir **los mismos bytes** para el mismo dato lógico, o el
grafo recibe dialectos incompatibles del "mismo" contrato.

---

## 1. El problema y la decisión de diseño

La serialización del contrato vivía **soldada** dentro de `ml-detector` (función
`build_row`, que lee un `NetworkSecurityEvent` de protobuf y emite la fila CSV).
Problema: para que el futuro injector adversarial y los adaptadores produzcan bronce
**byte-fiel al de producción**, necesitan *la misma* serialización. Si cada uno
reimplementa, divergen, y cualquier medición de pérdida en el grafo mide una
serialización distinta a la real. Eso envenena el claim en la raíz.

**Decisión: corte en TRES capas, con un struct como frontera.**

```
[protobuf -> Row]   to_row()       EXCLUSIVO de ml-detector (solo él habla protobuf)
[Row -> bytes]      serialize()    LIB COMPARTIDA (libcorrelation_v1) = notario único
[bytes -> disco]    CorrelationWriter   ml-detector (rotación, fichero, reloj)
```

`build_row` escondía dos responsabilidades fundidas: el **mapeo protobuf→campos**
(exclusivo, se queda) y la **serialización campos→bytes** (común, se extrae a la lib).
La struct `CorrelationV1Row` es la *lingua franca*: los cinco productores la rellenan
a su manera y la pasan por el **mismo** `serialize`, que es el único que decide los
bytes. La extracción la justifican dos consumidores reales (ml-detector + injector),
no el adaptador hipotético.

---

## 2. Las seis decisiones congeladas

- **D-A** — `serialize`/`validate` devuelven **error tipado** (`[[nodiscard]]` sobre
  el tipo), nunca excepción ni línea silenciosa. El fallo de validez no se puede
  descartar bajo `-Werror`. (Mismo espíritu que `FlushResult` del DAY 184.)
- **D-B** — La propiedad "toda fila válida está en la imagen del event-path" **no se
  prueba** (espacio intratable): se **acota** por vectores adversariales enumerados.
  El claim honesto es "rechaza las clases conocidas", no "caracteriza la imagen".
- **D-C** — `schema_version` y `source_sensor` son **campos del Row**, no constantes.
  aRGus los fija a `"1"`/`"argus"`; Suricata fijará `"suricata"`. La lib no los conoce.
- **D-D** — El símbolo de col 17 llega ya resuelto como string. El **guard de
  "símbolo de enum legal"** se DIFIERE a un commit aparte (ver Frente 3).
- **D-E** — `serialize` hace `imbue(std::locale::classic())` en cada stream. El
  `build_row` viejo NO lo hacía: formateaba con el locale global del proceso. (Frente 2.)
- **D-F** — `community_id` vacío = **SKIP** (filtrado legítimo, no pérdida), gestionado
  por `to_row`. La lib nunca ve esas filas; si una llega, `validate` la rechaza.

---

## 3. Lo construido y PROBADO (B1–B3) — retrospectivo

Se siguió un plan Via Appia "por adición": nunca destruir el oráculo hasta tener su
huella congelada. Cuatro piedras; las tres primeras están **hechas y verdes**:

**B1 — `to_row` por adición.** Se añadió `to_correlation_v1_row(event) ->
{Ok(row) | Skip | Error}` como función libre en ml-detector, SIN tocar `build_row`.
Conviven el oráculo (`build_row`) y su réplica (`to_row` + `serialize`), lado a lado.
*Prueba:* ml-detector compila limpio bajo `-Werror`.

**B2 — captura del golden.** Una herramienta (`capture_golden`) escribe 27 vectores
deterministas con el `CorrelationWriter` REAL (path del oráculo, nunca `serialize`),
lee los bytes exactos del CSV y los congela a `correlation_v1_golden.tsv`. Vectores:
3 realistas (heredados de un test existente) + 24 rincón (comas, comillas, `\n`/`\r`/
`\t` embebidos, NaN, Inf, negativos, alta precisión, UTF-8, vacíos, puertos/timestamps
extremos, los 7 enums de `DetectorSource`, un enum desconocido, y el `community_id`
vacío que dispara SKIP). Resultado: `WRITTEN=26 SKIPPED=1 mismatches=0`.

**B3 — test de oráculo.** Por cada vector: `serialize(to_row(event))` debe ser
byte-idéntico (a) al golden congelado **y** (b) a `write_record` EN VIVO. Vectores
SKIPPED: `to_row` debe devolver `Skip` exacto. En divergencia, diagnóstico por byte
(offset, byte esperado vs obtenido, columna, contexto). *Resultado: verde, 27/27.*

**Qué prueba esto, con precisión:** que la serialización extraída produce **los mismos
bytes** que el oráculo original, sobre 27 casos incluidos los rincones peligrosos,
**bajo locale classic** (ver Frente 2). NO prueba production-readiness ni cobertura
exhaustiva del espacio de entradas.

---

## 4. El plan de B4 — prospectivo (aún NO ejecutado)

B4 es el rewire: `write_record` deja de llamar a su `build_row`/`compute_hmac` internos
y pasa a `to_row(event)` → si `Ok`, `serialize(row, hmac_key)` → escribe la línea. Se
**borran** `build_row` y `compute_hmac` de `CorrelationWriter` (su lógica ya vive en
la lib). Se hará como commit separado, con la cabeza fresca.

**Cambio de naturaleza del test en B4 (sin ambages):** hoy B3 compara `serialize`
contra `write_record`, y `write_record` usa `build_row` (el oráculo). Tras el rewire,
`write_record` *será* `serialize` por dentro. Por tanto "comparar serialize contra
write_record en vivo" pasará a ser **comparar serialize consigo mismo: no prueba nada**
(es tautológico). La única red que **sobrevive con fuerza** es la comparación contra el
**golden**, que se capturó del `build_row` viejo y por eso sigue probando que el
`write_record` nuevo emite los bytes del oráculo original. Esto es exactamente por qué
el golden tuvo que congelarse ANTES de B4.

---

## 5. Los cinco frentes de duda — ATACAD AQUÍ

### Frente 1 — ¿Basta un golden de 27 vectores como red PERMANENTE?

Tras B4 desaparece el guard en vivo (se vuelve tautológico) y el golden de 27 casos
queda como **única** red permanente de byte-identidad. La lib tiene además su propio
test de propiedad (determinismo, inmunidad a locale, confinamiento), pero la
byte-identidad-con-el-oráculo descansa solo en esos 27 vectores enumerados (D-B:
acotado, no probado).
**Riesgo:** un caso no enumerado donde `serialize` diverja del oráculo y nadie lo vea
porque `build_row` ya no existe para comparar.

### Frente 2 — Locale: ¿inmunidad probada o asunción no verificada?

El contrato bronce **debe ser locale-invariante por diseño**: `0.910000` debe
escribirse igual en Badajoz, Tokio o São Paulo, porque si el formato numérico depende
del locale del nodo, dos sensores del mismo despliegue producen bronce incompatible.
`serialize` fuerza `classic` (D-E) precisamente para esto. PERO:
- El golden se capturó **forzando classic**, porque el autor corre bajo `es_ES`. Sin
  ese pin, el `build_row` viejo *en ese mismo entorno* habría escrito millares y coma
  decimal.
- **No se ha verificado bajo qué locale arranca el daemon en producción.** Si arranca
  bajo `es_ES` (u otro con coma decimal), el bronce viejo está corrupto **ahora mismo**,
  y el D-E no es una mejora sino la corrección de un bug activo.
- El test de la lib prueba inmunidad ante **un** locale hostil (`es_ES`). No hay matriz.

**El reencuadre correcto:** la meta no es "soportar todos los locales", es **ser
inmune a todos ellos**. La pregunta es de *comprobación*, no de soporte.

### Frente 3 — D-D diferido: ¿legítimo o aplazamiento indefinido?

El guard de "símbolo de enum desconocido en col 17" se difirió a un commit aparte.
**Defensa del autor:** es **endurecimiento de contrato, no corrección de bug**. El
`write_record` actual YA emite `""` para un enum desconocido (lleva así desde siempre),
y el refactor lo **preserva byte a byte** (está en el golden, vector `rincon_16`).
Diferir D-D no introduce ninguna regresión; solo pospone hacer *más estricto* algo que
hoy es permisivo. Por eso el autor sostiene que **no debe bloquear el merge**.
**Lo que el autor espera que le impongáis como condición:** que D-D quede como DEBT
explícito con criterio de cierre, no como "ya lo haré".

### Frente 4 — `DEBT-BRONZE-EMBEDDED-NEWLINE-001`

El vector con `\n` embebido en un campo string reveló que `serialize` (y el oráculo) lo
entrecomillan pero mantienen el `\n` literal → la "línea" bronce ocupa **dos líneas
físicas**. El reader downstream (`parse_and_verify`, basado en `getline`)
probablemente parta ese registro y el HMAC no valide. Es una debilidad del **formato**,
no del refactor (el golden lo captura bien leyendo el fichero entero).
**Pregunta:** ¿bloqueante, o post-FEDER?

### Frente 5 — El claim central: ¿honesto?

Claim propuesto: *"Refactor de la capa de serialización a una librería compartida,
probado byte-idéntico contra un golden congelado y contra el oráculo en vivo, sobre 27
vectores incluidos los rincones del serializador, bajo locale classic, con el guard de
enum desconocido (D-D) diferido a commit aparte sin regresión."*
**Pregunta:** ¿es ese el claim honesto, o se concede más de lo probado? ¿Falta alguna
salvedad?

---

## 6. Lo que cada modelo debe responder

Para cada frente (1–5), una respuesta concreta y accionable:

1. **F1:** ¿Es suficiente el golden de 27 vectores como red permanente, o exigís algo
   más (p.ej. fuzzing de structs aleatorios serializados y comparados contra una
   referencia)? Si exigís fuzzing, ¿contra qué oráculo, si `build_row` ya no existe?
2. **F2:** ¿Una matriz de locales hostiles (es_ES, de_DE, ar_SA, ja_JP…) como gate, o
   basta el caso es_ES actual? ¿Y la verificación del locale de producción debe ser
   condición de merge, sí o no?
3. **F3:** ¿Diferir D-D desbloquea el merge legítimamente? ¿Qué criterio de cierre
   exigís para el DEBT?
4. **F4:** ¿`DEBT-BRONZE-EMBEDDED-NEWLINE-001` bloquea, o post-FEDER? Justificad.
5. **F5:** Reescribid el claim si lo veis sobre-concedido. Señalad la salvedad que falte.

Y una transversal: **¿el plan de B4 (sección 4) es seguro y suficiente, o hay un riesgo
que no se ha visto?**

---

## 7. Lo que NO aporta señal (no malgastéis aquí)

- Sugerir que NO se difiera D-D "por si acaso" sin un argumento de regresión concreto.
- Pedir production-readiness: esto es "suelo que protege la medición", no producto.
- Reabrir el corte en tres capas: está decidido y probado.
- Elogiar la cobertura de vectores sin señalar el caso que falta.

---

*Metodología: brief → 8 respuestas (Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini,
Kimi, Mistral) → síntesis (señal vs ruido) → arbitraje de Alonso. El riesgo de este
trabajo no es construir mal, es etiquetar mal lo que se mide.*