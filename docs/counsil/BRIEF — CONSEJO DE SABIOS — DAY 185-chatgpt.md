# Revisión adversarial — Consejo de Sabios (síntesis técnica)

Voy a responder como si estuviera intentando invalidar el diseño, no defenderlo.

---

# Frente 1 — ¿27 vectores son suficiente red permanente?

## Veredicto

**No son suficientes como única red permanente**, pero tampoco considero que bloqueen B4.

El problema no es el número 27. El problema es que los 27 casos son **ejemplos concretos**, mientras que la superficie real del serializador está dominada por interacciones:

* locale × float
* quoting × UTF-8 × delimitadores
* campos vacíos × HMAC
* extremos numéricos × precisión
* combinaciones simultáneas de caracteres especiales

Los bugs de serialización suelen aparecer precisamente en las combinaciones.

## Qué exigiría

Mantener:

* golden de 27 vectores (regresión histórica)

Añadir:

* property-based fuzzing sobre `CorrelationV1Row`

No contra `build_row` (ya no existirá).

Contra propiedades invariantes:

### P1 — determinismo

```text
serialize(row) == serialize(row)
```

siempre.

### P2 — locale immunity

```text
serialize(row)
```

idéntico bajo múltiples locales.

### P3 — parseabilidad

Si existe parser oficial:

```text
row -> serialize -> parse
```

debe preservar todos los campos válidos.

### P4 — estabilidad del HMAC

Modificar un byte de columnas 0–17:

```text
HMAC nuevo != HMAC viejo
```

### P5 — confinamiento CSV

Ningún campo puede escapar de su columna.

---

## Mi condición

No bloquearía B4.

Pero abriría un debt explícito:

```text
DEBT-BRONZE-PBT-001
```

(property-based testing)

porque tras eliminar el oráculo ya no existe forma de recuperar cobertura exploratoria.

---

# Frente 2 — Locale

## Veredicto

Aquí veo el mayor riesgo real.

No porque el nuevo código sea incorrecto.

Sino porque habéis descubierto accidentalmente un posible bug histórico.

---

## Lo que realmente se ha demostrado

No habéis demostrado:

```text
el sistema era locale-invariante
```

Habéis demostrado:

```text
la nueva librería es locale-invariante bajo es_ES
```

Son cosas distintas.

---

## ¿Matriz de locales?

No.

No aporta demasiada señal.

Si el código hace:

```cpp
imbue(std::locale::classic())
```

el comportamiento debería ser independiente del locale global.

---

## Lo que sí exigiría

Locales representativos:

* es_ES
* de_DE
* ar_SA

porque cubren:

* coma decimal
* formatos europeos
* numeración no latina

Con tres ya detectas prácticamente cualquier fuga.

---

## ¿Verificar el locale de producción antes del merge?

No.

No es requisito del refactor.

Es una investigación aparte.

Lo documentaría como:

```text
RISK-PROD-LOCALE-001
```

porque podría revelar que el sistema histórico generaba bronce inconsistente.

Pero no condicionaría B4.

---

# Frente 3 — D-D diferido

## Veredicto

Legítimamente diferible.

La pregunta clave es:

> ¿preserva el comportamiento observable?

Respuesta:

Sí.

El golden contiene el caso.

El comportamiento previo era:

```text
enum desconocido -> ""
```

El nuevo comportamiento sigue siendo:

```text
enum desconocido -> ""
```

No hay regresión.

---

## Lo que exigiría

Debt formal.

No un comentario.

Algo tipo:

```text
DEBT-BRONZE-ENUM-GUARD-001
```

### Criterio de cierre

Cuando:

```text
validate()
```

rechace explícitamente símbolos fuera del conjunto permitido.

Y exista:

* test positivo para todos los símbolos válidos
* test negativo para símbolos inválidos

Sin eso el debt no puede cerrarse.

---

# Frente 4 — Embedded newline

## Veredicto

Este es el frente más delicado.

Porque aquí sí hay una posible ruptura de contrato downstream.

---

## Pregunta crítica

¿El contrato bronce permite strings arbitrarios?

Si la respuesta es:

```text
sí
```

entonces el formato actual está roto.

Porque:

```text
CSV multilinea
```

*

```text
getline()
```

=

lector inconsistente.

---

## ¿Bloqueante?

Para FEDER:

**No.**

Para producción:

**Sí.**

Motivo:

el refactor no introduce el problema.

Lo descubre.

Eso es importante.

Bloquear un refactor por revelar un bug preexistente suele ser mala ingeniería.

---

## Qué haría

Abriría:

```text
DEBT-BRONZE-EMBEDDED-NEWLINE-001
```

con severidad alta.

Y exigiría:

* reproducción automatizada
* test rojo del reader
* decisión formal sobre el contrato

Opciones:

1. prohibir CR/LF
2. escapar CR/LF
3. abandonar CSV físico multilinea

Pero debe resolverse antes de considerar estable el contrato.

---

# Frente 5 — Honestidad del claim

## Veredicto

El claim actual está ligeramente sobre-concedido.

No mucho.

Pero hay una frase que me preocupa:

> probado byte-idéntico

porque puede interpretarse como universal.

No lo es.

---

## Claim que yo publicaría

> Se extrajo la serialización del contrato `correlation_v1` a una librería compartida. La nueva implementación fue validada frente al oráculo histórico mediante un golden capturado antes del refactor y mediante comparación en vivo sobre 27 vectores deterministas que cubren casos normales y rincones relevantes del serializador. En esos vectores, la salida resultó byte-idéntica al comportamiento previo. La serialización resultante es inmune al locale global mediante uso explícito de `std::locale::classic()`. El endurecimiento del tratamiento de enums desconocidos queda diferido a trabajo posterior sin modificar el comportamiento observable actual.

---

## Salvedad obligatoria

Añadiría explícitamente:

> No constituye una demostración exhaustiva de equivalencia para todas las entradas posibles.

Porque eso es exactamente lo que D-B reconoce.

---

# Riesgo transversal de B4

Hay uno que no aparece en el brief.

## Riesgo: cambio accidental de ownership semántico

Antes:

```text
CorrelationWriter
 ├─ build_row
 ├─ compute_hmac
 └─ write
```

Después:

```text
to_row
serialize
write
```

Cuando se eliminan implementaciones duplicadas es habitual perder alguna regla implícita que nadie sabía que existía.

No me preocupa la serialización.

Me preocupa:

```text
SKIP
Error
Ok
```

La semántica operacional.

---

## Lo que añadiría antes de borrar código

Un test de comportamiento completo:

```text
evento
   ↓
write_record
   ↓
WRITTEN / SKIPPED / ERROR
```

comparando:

* versión pre-B4
* versión post-B4

para los 27 vectores.

No compara bytes.

Compara decisiones operativas.

Porque es el único sitio donde todavía puede esconderse una divergencia no detectada por el golden.

---

# Dictamen final

* **F1:** merge permitido; añadir property-based testing como debt.
* **F2:** merge permitido; añadir 2–3 locales hostiles y abrir investigación del locale real de producción.
* **F3:** diferimiento legítimo; debt formal con criterio de cierre verificable.
* **F4:** no bloquea FEDER; sí debe tratarse como debt de alta severidad.
* **F5:** el claim necesita aclarar que la equivalencia observada está limitada a los vectores ensayados.

**B4 me parece seguro**, siempre que se añada una última prueba de equivalencia de comportamiento (`WRITTEN/SKIPPED/ERROR`) antes de eliminar definitivamente el código antiguo.

FDO

CHATGPT