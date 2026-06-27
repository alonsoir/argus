Feedback completo de los ocho. Lo sintetizo por pregunta para que veas dónde hay consenso de hierro y dónde hay matices que merecen decisión tuya.

**Q1 — Orden de batalla: UNANIMIDAD ABSOLUTA. (A) injectors primero.** Los ocho coinciden, y por la misma razón de fondo: sin injectors no hay generación determinista de bronce en CI, y depender de pcap+eBPF para cada regresión es frágil y caro. No hay nada que decidir aquí — está zanjado.

Pero ojo a un matiz donde el Consejo **se divide**, y es importante: **¿qué `community_id` generan los injectors?** Hay dos campos:
- **Claude, Gemini, Kimi, DeepSeek**: reusar `compute_community_id` real / generar un ID *isomorfo* al del sniffer (mismo algoritmo, hash del flujo de 5 tuplas). Kimi lo dice con más fuerza: "si los injectors fabrican IDs con formato distinto, entrenas el pipeline con datos que no representan la realidad del eBPF."
- **Qwen**: un `community_id` mock con formato distinto (`"synth:test:hash"`) — explícitamente marcado como sintético.

Esto **sí** es una decisión tuya, y no es menor. El mock de Qwen tiene una ventaja que nadie más señaló: es **auto-identificable** — una fila de bronce con `synth:test:hash` nunca se confunde con tráfico real, lo cual es oro para no contaminar análisis. Pero rompe el isomorfismo que defienden los otros cuatro. Mi lectura: depende de para qué uses el injector. Si es para validar el *contrato y el cableado* (que la fila viaja entera writer→reader), el mock de Qwen basta y es más seguro. Si es para validar *correlación realista* (que el join por community_id funciona como en producción), necesitas el isomorfismo de Claude/Kimi. Probablemente quieras **ambos modos**, pero esa es tu llamada.

**Q2 — int vs string: el Consejo se parte casi por la mitad, y esto es lo más jugoso del feedback.**

Campo **string simbólico** (cambiar): **Claude, Gemini, Qwen.** Argumento: fragilidad ante evolución del enum, auto-descripción, y —dato técnico de Qwen que zanja el contraargumento del tamaño— *Parquet aplica dictionary encoding nativo, así que el ahorro del int es prácticamente nulo tras compresión*. Ese dato es fuerte: mata la única ventaja real del int.

Campo **int** (mantener): **Grok, Mistral.** Argumento: bronce mínimo y fiel, mapeo en plata/gold.

Campo **AMBOS / int + versión** (la tercera vía): **ChatGPT, DeepSeek, Kimi.** ChatGPT propone dos columnas (`authoritative_source=4` y `authoritative_source_name=ML_PRIORITY`). DeepSeek y Kimi proponen int + un `proto_version`/`enum_version` en el esquema que permita detectar bronce escrito con mapeo antiguo.

Aquí no hay unanimidad y la decisión es tuya. Pero fíjate en una cosa: **incluso los que dicen "mantener int" (Grok, Mistral) y los de la tercera vía coinciden en que el mapeo NO puede ser implícito en el código del reader.** Todos piden que el contrato int→enum esté explícito y versionado en algún sitio (ADR, YAML de esquema, columna extra). O sea: el consenso real no es "int vs string", es **"el significado de la columna 17 debe ser recuperable sin leer el código fuente de la versión que la escribió"**. String lo logra por construcción; int+versión lo logra con maquinaria. Esa es la decisión de fondo.

Mi voto sigue siendo string (sobre todo tras el dato de Qwen sobre dictionary encoding, que demuele el argumento del tamaño), pero la tercera vía de ChatGPT/Kimi es defendible y más conservadora. Lo que NO es defendible, según los ocho, es dejarlo como está hoy: int crudo con mapeo implícito.

**Q3 — Modelo de confianza: UNANIMIDAD en el qué, divergencia en el cómo.** Los ocho dicen: HMAC simétrico vale para hoy/intra-nodo, pero **no escala a N sensores → Kuzu central, y merece ADR YA, antes de escribir el consumidor.** El no-repudio y la gestión de N secretos son los dos argumentos repetidos. Todos apuntan a Ed25519 (que ya tienes para plugins) como destino.

La divergencia es de diseño del ADR:
- **Camino simple (Claude, Gemini, Qwen, DeepSeek, Grok)**: firma asimétrica Ed25519 por sensor; el central valida con la pública. Directo.
- **Camino jerárquico (Kimi)**: Ed25519 firma una clave HMAC de sesión de corta vida, y el HMAC valida el volumen de filas. Lo mejor de ambos: no-repudio del asimétrico para el provisioning + velocidad del simétrico para el dato de alto volumen. Kimi señala que firmar Ed25519 *cada fila* sería lento dado el volumen del bronce.

El punto de Kimi es técnicamente el más afilado: el bronce es alto volumen, y Ed25519 por fila tiene coste. Su esquema jerárquico lo resuelve. Si abres el ADR, ese es el matiz que más merece estar dentro.

Sobre el **número del ADR**: cuidado, hay colisión. Gemini dijo "ADR-046" pero ese ya existe (CrisisWindow). Yo propuse ADR-051. Conviene que confirmes cuál es el siguiente libre antes de redactarlo.

**Deudas nuevas que el Consejo propone y que conviene capturar:**
- **ChatGPT → `DEBT-BRONZE-PROVISIONING-E2E-001`**: un test que demuestre que writer y reader obtienen la misma clave *desde el mecanismo real de provisioning*, no hardcodeada. Es la respuesta directa al falso verde de hoy.
- **Qwen** lo refina: modificar `test_correlation_roundtrip` para que la clave venga de env-var o mock de etcd que ambos lados consulten — validar el *mecanismo de obtención de confianza*, no solo el contrato.
- **Mistral → checklist de "validación de secretos"** en CI para todo componente que use HMAC/etcd.
- **Mistral, riesgo concreto**: asegurar que `parse_and_verify` sea el PRIMER paso del consumidor (validar antes de tocar Kuzu), para que una clave mala no corrompa el grafo.

---

Resumen de lo que está **zanjado** (no necesita tu decisión): Q1=injectors primero; Q3=abrir ADR de confianza federada antes del consumidor. Y lo que **sí necesita tu decisión**:

1. **Q2**: string (Claude/Gemini/Qwen) vs int+versión (ChatGPT/Kimi/DeepSeek) vs int+columna-extra (ChatGPT). Lo único descartado por consenso es el statu quo.
2. **Q1-matiz**: community_id isomorfo (realista) vs mock auto-identificable (Qwen) vs ambos.
3. **ADR de Q3**: ¿Ed25519 directo o jerárquico (Kimi)? Y confirmar número de ADR libre.

Te propongo que decidas esos tres y con eso ya tengo todo para actualizar `docs/BACKLOG.md` (con las deudas nuevas), el prompt de continuidad y el resto de tu lista. ¿Cómo lo ves — empezamos por tus decisiones sobre esos tres puntos, o prefieres que te dé mi recomendación cerrada para cada uno antes de que decidas?

Mis respuestas:

Q1. Queremos ambos modos.

Q2. Coincido contigo, cambio a STRING

Q3. Abrimos ADR para introducir y usar Ed25519 junto con HMAC, o en vez de. Sería ADR-053. Exploramos las dos opciones hablandolo un poco más en el consejo. Me preocupa el posible volumen y el coste en CPU y RAM si el servidor va a estar más tiempo validando fila por fila con Ed25519 de cada fichero bronce. Potencialmente pueden ser cientos o miles.