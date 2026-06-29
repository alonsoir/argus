Leídas las 8. El feedback es duro pero está bien dirigido — y antes de entrar frente por frente, una observación de arbitraje que vale más que cualquier veredicto individual:

**Cuidado con tomar el 8/8 en F1, F2 y F4 como confirmación independiente.** Yo redacté el brief, y en él etiqueté esos tres como "los frentes que dan miedo". Ocho revisores entraron por la puerta que les abrí. Que coincidan ahí no prueba que tenga razón; prueba que el encuadre funcionó como profecía autocumplida — justo el sesgo del que te avisé en mi respuesta. **La señal de oro está en lo que nadie pidió que buscaran:** los hallazgos que aparecieron *sin* que el brief los teleara. Esos son cuatro, y son los que de verdad importan:

1. **DeepSeek (F6, no listado): el HMAC rompe la promesa "mismos bytes" entre productores.** Si cada adaptador firma con su clave, dos filas con columnas 0-17 idénticas tendrán col 18 distinta → no son "los mismos bytes". Es real, y reencuadra el claim del contrato: lo que es común entre productores son las **columnas 0-17**; la 18 es integridad por-productor, no identidad. No bloquea B4 (DeepSeek exagera ahí — B4 no toca la semántica HMAC), pero **sí obliga a precisar el claim del contrato** cuando lleguen los adaptadores. Señal alta.

2. **Kimi/DeepSeek/Qwen, convergentes: el golden capturado bajo classic forzado NO es el oráculo histórico si producción corre es_ES.** Esto es lo más afilado de todo el feedback. El golden congela "lo que *debería* haber sido" (classic), no "lo que *fue*" (es_ES con coma). Si el bronce histórico tiene comas, entonces post-B4 produces bronce *incompatible con el histórico* — D-E deja de ser refactor transparente y pasa a ser **corrección de bug con breaking change**. Tres modelos llegaron ahí solos. Señal máxima.

3. **Gemini/ChatGPT/DeepSeek, convergentes: shadow mode para B4.** Correr ambos caminos en paralelo comparando buffers antes de borrar `build_row`. Y aquí está la elegancia: **eso es exactamente el fuzzing pre-B4 de F1.** Los dos frentes colapsan en una sola acción.

4. **Kimi/Qwen: encapsular el formateo numérico en función locale-agnóstica** (`std::to_chars`/`snprintf`, no `operator<<`+`imbue`). Inmunidad por construcción, no por disciplina. DEBT, no urgente.

Ahora los frentes, con el tally y separando señal de ruido:

**F1 — 8/8: el golden de 27 no basta como red permanente.** Unánime, y aquí sí lo descuento por framing, pero el fondo es correcto. La división real es *cómo*: cuatro (ChatGPT, Gemini, Kimi, Qwen) dicen fuzzear contra **invariantes** (determinismo, reglas de escape, HMAC correcto) sin oráculo; cuatro (yo, DeepSeek, Grok, Mistral) contra un **oráculo congelado**. **Se reconcilian, y barato:** fuzzea `serialize(to_row(e))` contra `write_record` en vivo **antes de B4**, mientras el oráculo aún existe — reutiliza el harness de B3 cambiando los 27 por N millones de eventos aleatorios. Cero divergencias sobre N millones es evidencia masivamente más fuerte que 27 puntos, y *de paso es el shadow mode de B4*. Tras B4, los invariantes de propiedad quedan como red permanente. **Ruido a descartar:** DeepSeek quiere congelar el binario viejo en Docker para siempre — innecesario si fuzzeas antes de B4. No bloquea (7/8).

**F2 — 7/8: verificar el locale de producción debe condicionar el merge.** El consenso más fuerte de todo el feedback (solo ChatGPT lo deja como investigación aparte). Combínalo con el hallazgo #2 de arriba y la acción es nítida: **un `grep` de 5 minutos al systemd unit + una muestra del bronce histórico buscando comas.** Si producción es classic → D-E es endurecimiento puro, el golden casa con la historia, todo limpio. Si es es_ES → el bronce histórico está corrupto *ahora*, D-E es bug-fix con breaking change, y hay que coordinarlo con la capa Kuzu y declararlo. Matriz de locales: es_ES (coma), de_DE (millares), ar_SA (dígitos no latinos), C — cuatro bastan, y es *verificación* barata (parametrizar el P0b), no soporte. Más de cinco es rendimiento decreciente.

**F3 — 8/8: diferir D-D es legítimo y desbloquea.** Sin disidencia. Condición unánime: DEBT formal con criterio de cierre explícito, nunca "ya lo haré". Y tres modelos (yo, DeepSeek, Gemini) convergieron solos en mi criterio: **cerrar cuando el primer adaptador no-aRGus (Suricata) entre al pipeline** — atado a evento real, no a fecha. DeepSeek añade algo bueno: nota de breaking change en el CHANGELOG, porque productores que hoy emiten `""` empezarían a ser rechazados. Cero ruido aquí.

**F4 — nadie dice ignorarlo; el suelo unánime es defensa barata ya.** Cuatro lo marcan bloqueante absoluto (DeepSeek, Grok, Mistral, Qwen), cuatro "actúa ya pero no bloquees" (yo, ChatGPT, Gemini, Kimi). Pero fíjate: *todos* aceptan como mínimo añadir detección ruidosa ahora. El "BLOQUEANTE ABSOLUTO" de Qwen es en parte mi framing rebotando. La posición honesta la afina Kimi: **la pregunta real es si `parse_and_verify` usa `getline`.** Si sí, puede haber corrupción activa → investiga el reader. La acción de mínimo común: **rechazar `\n`/`\r` embebido en `validate`/`to_row` ahora** (3 líneas, error ruidoso), investigar el reader, y decidir el arreglo completo (escapar) según lo que revele. **Consecuencia que ningún modelo vio:** esa defensa hace que `rincon_04` deje de producir bytes → su entrada en el golden pasa de WRITTEN a rechazado, y hay que regenerarla. No es gratis del todo.

**F5 — 8/8: el claim está sobre-concedido.** Consenso total. Consolidando las ocho reescrituras, el claim honesto es:

> *"Extracción de la serialización del contrato `correlation_v1` a `libcorrelation_v1`. Verificada byte-idéntica contra el oráculo `build_row` sobre 27 vectores enumerados y bajo locale classic. Salvedades: (a) la equivalencia general está **acotada por enumeración, no probada** (D-B); (b) el golden se capturó forzando classic — si el daemon de producción operó bajo un locale no-C, el bronce histórico puede divergir y este refactor sería de facto una corrección con breaking change; (c) el formato permite `\n` embebidos que rompen readers basados en `getline` (DEBT-BRONZE-EMBEDDED-NEWLINE-001); (d) el guard de enum desconocido (D-D) queda diferido sin regresión; (e) la identidad entre productores cubre las columnas 0-17; la columna 18 (HMAC) depende de la política de claves, aún sin definir."*

Y ahora lo que de verdad necesitas: **el plan, separando lo que ya es tuyo de lo que condiciona B4.**

*Commiteable AHORA (hito B1-B3) — nada en el feedback lo invalida:* la lib, `to_row`, el golden, los tres tests verdes. Lo único que cambia es el **mensaje del commit / claim**, que va con la versión honesta de F5. Esto se commitea hoy, no espera al Consejo.

*Antes de B4 (medio día de endurecimiento barato que el Consejo acertó en pedir):*
- `grep` del locale de producción + muestra del bronce histórico (F2). 5 minutos, y es bloqueante si sale es_ES.
- Fuzz `serialize` vs `write_record` en vivo, N millones de eventos (F1 + shadow mode de B4 en una sola acción).
- Decidir el camino de fallo de clave HMAC: excepción en constructor vs error tipado en serialize (mi transversal). 10 minutos.
- `grep -r build_row` para dependencias ocultas antes de borrarlo (Kimi). 1 minuto.
- Defensa anti-`\n`/`\r` en validate + regenerar `rincon_04` (F4, suelo unánime).

*DEBT a registrar, NO bloquean:* D-D (cierra con Suricata), arreglo completo del newline (post-FEDER, según investigación del reader), fuzzing de invariantes como red permanente, política de clave HMAC entre productores, formateo numérico locale-agnóstico.

*Ruido a no perseguir:* el binario viejo en Docker (DeepSeek), la semana de doble escritura en staging (DeepSeek — es production-readiness, fuera de alcance por la sección 7 del propio brief), la matriz de 5+ locales (cuatro bastan).

Una cosa importante de honestidad: **nadie dijo "no hagas B4".** Dijeron "haz estas cinco cosas baratas antes", y tienen razón en que son baratas. B4 no está bloqueado; está condicionado a medio día de suelo. Eso es exactamente lo que querías del Consejo.

Vamos por partes, como dijiste. ¿Quieres que el siguiente paso sea redactar las entradas de `docs/BACKLOG.md` (los cinco DEBT con sus criterios de cierre), o prefieres primero el `grep` del locale de producción —que es la única pieza que podría cambiar el claim de "refactor limpio" a "bug-fix con breaking change" y conviene saberlo ya?