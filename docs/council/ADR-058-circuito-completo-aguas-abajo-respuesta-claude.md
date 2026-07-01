Bien hecho en pasármelo en vez de dejar que lo reconstruyera de memoria — eso habría sido yo revisando contra una suposición, que es exactamente el anti-patrón. Reviso contra estos bytes. Modo adversario, sin cortesías.

Lo que sigue son objeciones por severidad. Algunas hunden afirmaciones del ADR, otras solo piden una palabra más.

**A1 — La afirmación "lossless por tipo" de §3.1 es más débil de lo que está escrita. (severidad: media-alta)**

El texto dice que AVRO→Parquet→double "preserva los bits salvo (a) truncado a float32, (b) recompute, (c) texto intermedio". Esa lista no es exhaustiva, y presentarla como cerrada es justo el tipo de sobre-afirmación que el Consejo debería cazar. Faltan al menos:

- **(d) Parquet con compresión/encoding con pérdida.** El tipo físico DOUBLE es binary64, sí, pero Parquet aplica *encodings* a nivel de columna. BYTE_STREAM_SPLIT y dictionary son lossless; pero si alguien activa una codificación de coma flotante con pérdida, o si el converter pasa por un cast intermedio en Arrow (`float` vs `double` en un esquema Arrow mal tipado), pierdes bits sin tocar ninguno de tus tres puntos. El bug no estaría en "tu" código sino en la *config del writer Parquet*.
- **(e) `-0.0` vs `+0.0`.** Bit-distintos (`0x8000...0` vs `0x0`), pero `==` en C++ los iguala. Si tu predicado se implementa con `==` de C++ sobre el double, dos representaciones bit-distintas pasan como iguales — lo cual rompe tu propia premisa de que "bit-exacto == `==`". Y si lo implementas con `memcmp` (como propones para NaN), entonces `-0.0` y `+0.0` *fallan* la equivalencia aunque numéricamente sean idénticos. **No puedes usar la misma regla para NaN y para cero.** Tu guarda NaN, tal como está escrita, introduce este conflicto y el ADR no lo resuelve.

El arreglo no es retirar bit-exacto — tu decisión de fondo es correcta. Es **dejar de afirmar que la lista (a)(b)(c) es completa** y reformular la guarda de comparación: el predicado se implementa sobre el *patrón de bits canonicalizado*, donde canonicalización = {NaN → un patrón único, `-0.0` → `+0.0`}, y entonces `==` bit a bit sobre eso. Eso te da una sola regla coherente. Ahora mismo §3.1 tiene dos reglas que se contradicen en el caso cero.

**A2 — "El mismo bronce CSV ⇒ la degradación texto→double se cancela" tiene un agujero medible. (severidad: media)**

El argumento es que ambos caminos llaman a `parse_double` sobre el mismo texto, luego parten del mismo double. Cierto **solo si ambos caminos usan literalmente el mismo parser**. Pero el ADR dice (§3.1, acción residual) que el converter Flujo A "si es Python, los vectores golden congelados". Si el Flujo A es Python, no está usando `std::from_chars`/tu `parse_double` de C++ — está usando el parser de float de Python (o de pyarrow al leer el CSV). **`strtod` de C++ y el parser de CPython no garantizan el mismo double para todo string decimal** — ambos son correctos-redondeados en implementaciones modernas, pero "ambos correctos-redondeados" es una afirmación que hay que *verificar*, no asumir, y depende de la versión de la libc y de si pyarrow usa su propio parser rápido (que históricamente *no* era correctly-rounded). Acabas de mover el riesgo de precisión del lado Parquet (que neutralizaste bien) al lado del parser de entrada, y el ADR no lo menciona. La frase "se cancela en el predicado" solo es verdad si el lenguaje del Flujo A comparte parser con Camino 0. Eso es greenfield no medido → debe ir como nota de riesgo, no como hecho cerrado.

**A3 — Contradicción interna en la cabecera vs. el cuerpo. (severidad: baja, pero es el tipo de cosa que un revisor adversario marca)**

Cabecera: "Fecha: DAY 199 (hoy)". §1: "evidencia medida en el gate de DAY 198 (**6** verificaciones)". §4 título: "Gate DAY 198 (**9/9** contra bytes)". El "6" de §1 es un fósil de una versión anterior — mediste 9, no 6. Es un número equivocado en la línea de apertura del documento. Un Consejo que lee "6" en §1 y "9/9" en §4 tiene derecho a preguntar cuál es. Corrige §1 a 9.

**A4 — §2.6 referencia cruzada rota. (severidad: trivial pero real)**

En §6, `DEBT-DOCS-MEDALLION-DUALITY-001` dice "ver §2.6". No hay §2.6 — la integridad del oro es el corolario **6 de §2**, no una subsección §2.6. Tu propia regla "trazar contra fichero" aplica también a las referencias internas. O numeras los corolarios como §2.N de verdad, o cambias la referencia a "§2 corolario 6".

**A5 — La pregunta que el ADR no se hace: ¿quién computa los scores? (severidad: alta — es la grieta estructural)**

Esta es la que de verdad importa y ninguna de las notas la toca de frente. El predicado asume que los 3 scores son **datos que viajan** bronce→oro y deben preservarse byte a byte. Pero el supuesto operativo de §1 es que **la inferencia ML está rota/incompleta** (`DEBT-RANSOMWARE-ML-HEAD-INERT-001`). Entonces, ¿qué hay hoy en esas tres columnas double del bronce? Si son ceros, o un valor por defecto del head inerte, tu test de equivalencia bit-exacta va a pasar trivialmente — estás verificando que `0.0 == 0.0` por dos caminos. **El test sería verde y no probaría nada sobre el camino de scores reales**, porque no hay scores reales todavía. Eso no invalida bit-exacto, pero sí significa que el criterio de cierre del medallón, tal como está, **puede declarar el medallón cerrado sobre datos degenerados**. El ADR necesita una frase que diga: el test de equivalencia es necesario pero no suficiente mientras `ML-HEAD-INERT` esté abierto; el cierre del medallón sobre scores no-triviales se re-valida cuando la inferencia esté viva. Si no, te arriesgas a "cerrar" el circuito y descubrir en post-FEDER que nunca ejercitaste el path de scores con datos que varían.

---

Resumen de a qué me opongo y a qué no. **No** me opongo a bit-exacto por defecto — es correcto, y el cambio que hiciste ayer mejora el ADR. Me opongo a: la lista (a)(b)(c) presentada como cerrada (A1), la guarda NaN que rompe el caso `-0.0` (A1), "se cancela en el predicado" presentado como hecho cuando depende del parser del Flujo A (A2), y sobre todo a cerrar §8 sin nombrar que el test puede pasar vacío con el ML head inerte (A5). A3 y A4 son higiene.

Mi recomendación concreta: A3 y A4 los corriges sin debate. A1 y A5 merecen una nota cada uno en §3.1 y §8 respectivamente **antes** de subir — porque son justo lo que un revisor competente del Consejo va a encontrar, y es más fuerte que los lleves tú puestos. A2 puede ir como una línea de riesgo en la acción residual del converter.

¿Quiero que te redacte las notas de A1 (regla de comparación canónica única) y A5 (necesario-no-suficiente con ML inerte) como ediciones quirúrgicas, mismo formato que ayer? ¿O prefieres discutir primero si A5 te cambia el criterio de cierre de fondo — porque si te lo cambia, eso es más que una nota?

FDO

Claude