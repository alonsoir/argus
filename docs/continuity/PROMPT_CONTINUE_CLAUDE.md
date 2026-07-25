# PROMPT DE CONTINUIDAD — DAY 229 (continúa DAY 228)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. Cada línea rastreable a lo pedido.
4. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria.
- **Lección DAY 211 (lecturas parciales):** no concluir "X no existe" desde un `sed -n`, un
  `head` o un grep de filtro estrecho. Fichero entero antes de afirmar ausencia.
- **Lección DAY 223 (el grep que costó una noche):** `grep -rn` desde la raíz arrastra `build/`,
  `.git/`, `.venv/`, `vendor/`. Usar `git grep` o acotar con `-- ruta/`. Y **nunca encadenar dos
  comandos de salida grande**: el segundo se come la salida del primero.
- **Lección DAY 223 (BACKLOG):** ninguna deuda vive en fichero propio. Todas son secciones `###`
  dentro de `docs/BACKLOG.md`.
- **Lección DAY 224 (el número que nadie midió):** antes de propagar una cifra al paper, medirla.
- **Lección DAY 224 (constructos que no distinguen "hizo" de "no hizo"):** `sed -i` devuelve 0
  aunque no sustituya nada. Igual el `||` del Makefile.
- **Lección DAY 225 (la config que el proceso no ha leído):** comparar mtime de la config contra
  la hora de arranque del proceso. El sujeto de la verificación es el proceso, no el fichero.
- **Lección DAY 225 (nombres que mienten):** leer el cuerpo, no el nombre.
- **Lección DAY 226 (verde en la capa equivocada):** un verde en una capa intermedia no dice nada
  de la salida. Medir el fichero que se produce.
- **Lección DAY 226 (dos caminos que discrepan):** si el mismo fichero implementa la misma
  conversión dos veces, una de las dos está mal por definición.
- **Lección DAY 226 (el nivel superior no es el flujo):** leer la estructura anidada, no el primer
  campo con el nombre correcto.
- **Lección DAY 227 (la puerta que era un comentario):** un aviso escrito no es una barrera de
  código. Antes de tratar una advertencia como un muro, medirla.
- **Lección DAY 227 (el artefacto que se evaporó):** lo que importa va a `/vagrant`, nunca a
  `/tmp` de una VM.
- **Lección DAY 227 (dos fuentes de verdad para un secreto):** el escritor lee la clave HMAC de
  etcd, el lector del env. Nada las obliga a coincidir.
- **🆕 Lección DAY 228 (dos decisiones que nunca se vieron la cara):** el enrutado del grafo es
  `is_alert == (final_classification == "MALICIOUS")` (`cypher_builder.hpp:40`), y DAY 225 decidió
  mapear `final_classification` ← `alert.signature` de Suricata. Seis días de distancia, ningún
  conflicto visible, criterio del día inalcanzable. **Antes de escribir el criterio de éxito,
  medir el discriminador del que depende.**
- **🆕 Lección DAY 228 (el negativo que abre camino):** "no hay CLI de Kuzu" no fue un obstáculo,
  fue el descubrimiento de que faltaba la herramienta del paso 3 del plan de cierre. Un negativo
  que revela trabajo necesario vale más que un rodeo que lo esquiva.
- **🆕 Lección DAY 228 (el idioma ya estaba en casa):** la API de Kuzu no se infirió ni se buscó
  fuera: estaba en `test_flujo_b_end_to_end.cpp`. Antes de escribir contra una librería, buscar
  quién en el repo ya la usa.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable;
  Kuzu = proyección reconstruible por MERGE).
- **EMECAS+++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- macOS/zsh: comillas en globs, NUNCA `sed -i`, Python3 heredoc para editar.
  Commits/push desde el HOST. `git add` explícito por fichero, nunca `-u` ni `-a`.
- Rama ANTES del primer `git add`. Scripts scratch → `.gitignore` al crearlos.
- **Guardar SIEMPRE en la rama remota al cerrar sesión.**
- Un día, una batalla.

---

## Contexto estratégico (vigente desde DAY 223)

Ya NO se presenta nada ante Andrés ni ante FEDER. **Objetivo:** cerrar el pipeline lo mejor
posible y escribir el paper de la forma más honesta y científica posible. Fin de proyecto:
31-ago / primera semana de septiembre, repositorio en modo lectura.

### Plan de cierre en 6 pasos
1. ~~Terminar el pipeline aguas abajo; provocar que los datos lleguen al grafo.~~ ✅ **HECHO
   DAY 228 para Suricata** (falta Zeek y Wazuh).
2. Script MITRE para provocar datos → grafo.
3. Verificar que el grafo se consulta vía Kuzu. ← **parcialmente hecho**: existe `kuzu_query`.
4. Paper con las lecciones aprendidas.
5. README.md de verdad.
6. Repositorio en modo lectura.

---

## Estado — rama `feat/suricata-to-graph`

**El camino de Suricata llega hasta el grafo Kuzu, extremo a extremo, y se consulta.**

VMs: `defender` **running**, `suricata` **running**, `client` / `zeek` / `wazuh` **not created**.

⚠️ El toolchain de la VM `suricata` sigue instalado a mano, no en el `Vagrantfile`
(`DEBT-VM-SENSOR-NO-TOOLCHAIN-001`). Un `vagrant destroy` lo pierde.

---

## Lo conseguido en DAY 228

### El criterio del día, cumplido

```
MATCH (e:TelemetryEvent)-[:TELEMETRY_ABOUT]->(f:NetworkFlow)
RETURN e.source_sensor, e.event_id, e.final_classification, f.flow_uid LIMIT 3

suricata | suricata:P7D/AmXa... | SURICATA TCPv4 invalid checksum | eCjFUYOr5nsLGWZykRvJBkwFO+wMicFym9oGylrznAk=
```

**Un sensor que no es aRGus llega al grafo.** El paso 1 del plan de cierre está cerrado y
demostrado con una consulta, no argumentado.

### Recuentos medidos (BD `logs/day228-kuzu/suricata.kuzu`, ignorada por git)

| Consulta | Resultado |
|---|---|
| `MATCH (e:TelemetryEvent) RETURN count(*)` | **2870** |
| `MATCH (a:Alert) RETURN count(*)` | **0** |
| `MATCH (f:NetworkFlow) RETURN count(*)` | **775** |
| `MATCH (e:TelemetryEvent) RETURN e.source_sensor, count(*)` | `suricata\|2870` |

**Número nuevo para el paper: 2.870 alertas sobre 775 flujos (3,70 por flujo).**
⚠️ CAVEAT a escribir junto al número: 775 son tripletas distintas
`node_id ‖ community_id ‖ flow_start_window`, no necesariamente flujos reales — DAY 225 midió
16,7% de colapso de `community_id` en esta captura.

### El hallazgo del día: el enrutado es una igualdad contra un literal

`cypher_builder.hpp:40` → `is_alert(r) { return r.final_classification == "MALICIOUS"; }`

Como DAY 225 decidió `final_classification` ← `alert.signature`, **ninguna fila de Suricata puede
ser un `Alert`**. Todas caen a `TelemetryEvent`. No es un bug: es el choque entre dos decisiones
tomadas con seis días de distancia.

`final_classification` hace dos trabajos incompatibles: discriminador de enrutado (binario,
vocabulario de aRGus) **y** campo de veredicto en texto libre del sensor externo.

**Confirmado independientemente:** `test_flujo_b_end_to_end` escribe una fila MALICIOUS y una
BENIGN y asserta `Alert=1`, `TelemetryEvent=1`, `ALERT_ABOUT=1`, `TELEMETRY_ABOUT=1`. El gate ya
verificaba este comportamiento.

**DECISIÓN DAY 228 (Alonso): Opción A** — aceptar `TelemetryEvent` por ahora. Motivo: no se
pueden valorar las implicaciones del enrutado sin datos con intención real. Se afinará con MITRE.
Las otras dos opciones quedan escritas en `DEBT-GRAPH-ALERT-ROUTING-MONOSENSOR-001`:
(B) que el adapter emita `"MALICIOUS"` — sobreafirma, convierte errores de checksum en alertas;
(C) cambiar el discriminador a `!= "BENIGN"` — semánticamente correcto, toca el enrutado
compartido por los cinco productores, exige RED→GREEN sobre `test_graph_sink_loop`.

### Herramienta nueva: `correlation-engine/tools/kuzu_query.cpp`

`kuzu_query <kuzu_db_path> <cypher>`. Existe porque en `defender` **no hay CLI de Kuzu ni módulo
Python**, y un `pip install kuzu` a mano (a) podría no casar con el formato de almacenamiento de
la v0.11.3 embebida y (b) repetiría el patrón de `DEBT-VM-SENSOR-NO-TOOLCHAIN-001`.

Idioma tomado de `test_flujo_b_end_to_end.cpp`, no inventado. Con `try/catch`, a diferencia del
loader. Compiló limpio a la primera. **Es la herramienta que pedía el paso 3 del plan de cierre.**

### Otros hallazgos medidos (no volver a medir)

- **Kuzu es v0.11.3 embebido**: `libkuzu.so` precompilada en `/usr/local/lib` por el
  provisioning, `find_library`/`find_path` REQUIRED en `CMakeLists:36-37`. `KUZU_LIB` se enlaza
  **PUBLIC** en `correlation_engine` → se propaga solo a binarios y tests nuevos.
- El loader **no verifica HMAC** (col 18 deliberadamente no leída). Es el único eslabón de la
  cadena que no necesita `ARGUS_BRONZE_HMAC_KEY_HEX`. La clave de juguete no bloqueó nada.
- **NO existe ningún `ON MATCH SET`** en las plantillas Cypher, solo `ON CREATE SET`. Esto
  **contesta el P3 aparcado** ("¿machaca `flow_start`?"): no machaca nada. Consecuencias: recargar
  el mismo Parquet es idempotente; y cuando la convergencia funcione, el primer sensor que llegue
  fija las propiedades del `NetworkFlow`.
- `temporal_anomaly` es **unilateral** (solo marca futuro), con `kTemporalMarginNs = 2s` declarado
  placeholder "a calibrar con dato real". Los relojes rotos hacia el pasado no se marcan: ni el
  `flow.start` de 2011 de Suricata ni el reloj monotónico de aRGus.
- El sink hace flush por lotes de 512 filas. Carga completa: **26,6 s para 2.870 filas
  (~108 filas/s)**. Cifra medida, para cuando se hable de "procesar según lleguen".
- Kuzu quiere el **directorio padre** existente y crea él la BD (`mkdir -p` antes de invocar).

### 🟢 D2 CUMPLIDA — el byte order es el ÚNICO bloqueo pendiente para la convergencia

```
MATCH (f:NetworkFlow) RETURN DISTINCT f.node_id
→ cpp_sniffer_v33_day12   (1 fila)
```

Valor único, y es **el mismo `node_id` que escribe aRGus**. El adapter de Suricata sí imitó el
valor real. Importa porque `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)` —
`node_id` es ingrediente de la clave, así que un `node_id` distinto habría roto la convergencia
por un segundo motivo, independiente del byte order, e invisible hasta que los dos motores
escribieran juntos.

**Consecuencia: nada se interpone ya entre los dos sensores y el mismo nodo `NetworkFlow` salvo
`DEBT-SNIFFER-IP-BYTE-ORDER-001`.**

⚠️ **Grieta a registrar:** `cpp_sniffer_v33_day12` es una **etiqueta de versión** del sniffer de
aRGus (medido DAY 226), ni host ni punto de observación. La convergencia multi-sensor se sostiene
hoy sobre que el adapter de Suricata **hardcodea la cadena de versión de otro componente**. Un
bump de versión del sniffer cambiaría todos los `flow_uid` y rompería la convergencia **en
silencio**, salvo que se actualicen todos los adapters a la vez. **D2 se cumple por imitación, no
por diseño.** Material honesto de paper.

### Estado del repo

Commit de DAY 228 sobre `feat/suricata-to-graph`: `correlation-engine/tools/kuzu_query.cpp`
(nuevo) + bloque en `correlation-engine/CMakeLists.txt` + este prompt.
`make correlation-engine-test` (reconstrucción entera + ctest): **9/9 Passed, 2,67 s**.

🟢 **En remoto:** `09518d0c → f2c513ce → ce2c4805` (dos push).

### Aclaración del modelo del grafo (surgió al cerrar DAY 228)

Las ramas de cada sensor **no se unen por `community_id`**. Se unen por `flow_uid`, y
`flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)` — el `community_id` es uno de los
tres ingredientes, no la clave. Los tres tienen que coincidir entre sensores para converger.

Y lo que hoy hay **no es un upsert**: las plantillas solo tienen `ON CREATE SET`. La semántica
real es *insertar si no está, ignorar si está*. Cuando los dos motores escriban sobre el mismo
`NetworkFlow`, el primero que llegue fija `node_id`, `community_id`, `flow_start_window` e
`ingested_at`, y el segundo **no aporta nada al nodo de flujo**; solo cuelga su propio evento.
Coherente con "NetworkFlow identidad pura", pero conviene saberlo antes de que sorprenda.

---

## Plan DAY 229 — opciones

**La intención declarada al cerrar DAY 227 era: si el grafo sale rápido, empezar con Zeek.**
Salió en una sesión. Pero antes de elegir, un aviso de orden:

⚠️ **La VM `zeek` está `not created`, así que `DEBT-VM-SENSOR-NO-TOOLCHAIN-001` deja de ser deuda
aparcada y pasa a bloquear.** Pagarla ahora (bloque `ADAPTER_TOOLCHAIN` en el `Vagrantfile` raíz,
con verificación **por invocación** — `cmake --version`, `pkg-config --modversion libsodium` — no
por "el paquete figura instalado") tiene un retorno doble: sirve para `zeek` **y** para `wazuh`.
Hacerlo a mano una tercera vez es la decisión cara disfrazada de barata.

**Opción 1 — Zeek (adapter completo).** Alcance ya decidido (DAY 227): sacarle **todo el jugo**,
y si hace falta procesar **N ficheros de log** se hace — el adapter de Zeek no está limitado a la
forma "un fichero de entrada" del de Suricata. `scaffold_adapter.py --sensor zeek` da el
andamiaje con un `to_row.cpp` stub que falla a propósito. Zeek sí emite `community_id` y su
paridad se verificó E2E contra Suricata en DAY 185-194. Batalla larga: VM + toolchain + mapeo.

**Opción 2 — Script MITRE (paso 2 del plan de cierre).** Es lo que desbloquea la decisión de
enrutado aparcada hoy, y lo que da datos con intención real en vez de ruido de checksum de 2011.
Alonso dijo explícitamente que quiere ver esos datos antes de afinar.

**Opción 3 — `DEBT-SNIFFER-IP-BYTE-ORDER-001`.** Una palabra en `ring_consumer.cpp:844-845`, más
su test de regresión (definición de HECHO: leer una fila real del bronce y comparar su
`community_id` contra `pycommunityid` recalculado desde las IPs de esa misma fila). Desbloquea la
convergencia, que es la afirmación central del paper. Exige rebuild de `defender` y EMECAS.

**Opción 4 — Automatización** (lista de Alonso, DAY 227): targets del Makefile para
converter/loader/`kuzu_query`, tests e2e de Suricata equivalentes a los de aRGus, y actualizar
`pipeline-start`/`pipeline-status`. ⚠️ El punto "que Kuzu los procese según lleguen" **obliga a
resolver antes las dos fuentes de verdad de la clave HMAC** (etcd vs env).

**Opción 5 — Medir el premio del 98,7% (objetivo declarado por Alonso al cerrar DAY 228).**
Quiere ampliar el adapter para traer al grafo todo lo que trae Suricata y dejar de descartar los
104.394 eventos de dns/http/tls/flow/stats. **El obstáculo no es el adapter: es el contrato.**
`correlation_v1` tiene 19 columnas y **ninguna donde meter la carga útil** de un evento dns, http
o tls — el dominio consultado, el `Host`, el SNI. Para las alertas se resolvió en DAY 225 mapeando
`signature` → `final_classification`, y funcionó porque una firma *es* un veredicto; un dominio
DNS no lo es. Bajo el contrato de hoy esos eventos entrarían como **identidad sin información**.

Lo que **sí** aportarían es **topología**: hoy el grafo solo conoce los 775 flujos que dispararon
alerta; los eventos `flow` revelarían todos los flujos que existieron, con protocolo y extremos.
No es carga útil, pero es el contexto sobre el que se detecta daño (reencuadre de Matzinger,
*future work* del paper).

**Primer paso, barato y sin escribir mapeo:** medir cuántos eventos de cada tipo llevan
`community_id` — requisito duro, porque `validate()` rechaza los que no lo tienen. Eso convierte
"el 98,7%" en un número real de filas aprovechables y decide sola la conversación de si hay que
tocar el contrato o basta con los eventos `flow`. `tools/eval/eve_field_coverage.py` puede que ya
lo conteste sin una línea nueva. **Medir el premio antes de construir para él.**

**Recomendación de Claude:** la 3 antes que la 1. El arreglo del byte order es de una palabra,
desbloquea la afirmación central del paper, y hoy hemos comprobado que el circuito entero funciona
— es el mejor momento para tocar aguas arriba, con todo lo de abajo verde y medido. Zeek es una
batalla larga que además arrastra la deuda del toolchain. **Y con la D2 confirmada, la Opción 3 se
refuerza: el byte order es literalmente lo único que queda entre los dos sensores y el mismo
nodo.** Si se cierra rápido, la Opción 5 son media hora limpia y cabe en la misma sesión.

---

## Aparcado (no olvidar)

### Nuevo de DAY 228 — registrar en `docs/BACKLOG.md`
- **`DEBT-GRAPH-ALERT-ROUTING-MONOSENSOR-001`** (nueva): el discriminador `Alert`/`TelemetryEvent`
  es una igualdad contra `"MALICIOUS"`, vocabulario de aRGus. Ningún sensor externo puede producir
  un `Alert`. Tres opciones escritas arriba. **Decidir con datos de MITRE.**
- **`kuzu_query` no está en el Makefile** — mismo patrón que el converter y el loader, que se
  invocan a mano. Va con la Opción 4.
- **El loader no captura la excepción al abrir Kuzu**: `terminate called after throwing
  kuzu::common::IOException` si el directorio padre no existe. Tiene manejo explícito y con
  mensaje para el Parquet ausente (petición de GLM, Consejo DAY 207) y ninguno para la BD.
  Asimetría en el mismo fichero, familia "dos caminos que discrepan".
- **El loader accede a las columnas por índice posicional** con `static_pointer_cast` al tipo
  Arrow esperado, **sin validar el esquema**. Un desajuste de orden o tipo no daría error: sería
  comportamiento indefinido. Inofensivo hoy (mismo productor), trampa latente en multi-sensor.
- **`DEBT-NODE-ID-VERSION-LABEL-001`** (nueva): `node_id` es ingrediente de `flow_uid`, y su valor
  real es `cpp_sniffer_v33_day12` — una **etiqueta de versión** del sniffer de aRGus. El adapter de
  Suricata la hardcodea para converger. Un bump de versión del sniffer cambiaría todos los
  `flow_uid` y rompería la convergencia **en silencio** salvo que se actualicen todos los adapters
  a la vez. D2 se cumple por imitación, no por diseño. Toca a los cinco productores.

### Arrastrado de DAY 227
- Registrar: discrepancia etcd-vs-env de la clave HMAC (nota en `DEBT-BRONZE-KEY-PROVISIONING-001`
  y `DEBT-BRONZE-HMAC-KEY-POLICY-001`), el `.gitignore` con dos líneas corruptas, y el rot de
  `bronze_to_gold_converter.cpp:26`.
- Medir si `SecretsManager` persiste la clave o la pierde con el proceso. Si no persiste, el
  bronce real de aRGus sería **inverificable para siempre**. SOSPECHA, no veredicto.
- `git ls-files | grep -i -e '\.onnx$' -e '\.npz$'` — ¿hay blobs de modelo trackeados?

### De DAY 226
- **`DEBT-SNIFFER-IP-BYTE-ORDER-001`** — dos `[PENDIENTE]`: (a) confirmar el sentido de
  `event.src_ip` en el lado eBPF (`git ls-files -- 'sniffer/*' | grep -i -e bpf -e kern`);
  (b) si `main_libpcap.cpp` tiene el mismo defecto.
- **`DEBT-VM-SENSOR-NO-TOOLCHAIN-001`** — bloque `ADAPTER_TOOLCHAIN` en el `Vagrantfile` raíz.
- **Telemetría (D4)**: el adapter descarta los 104.392 eventos de dns/http/tls/… — el 98,7% del
  volumen de Suricata no llega al grafo todavía.
- **Decisión no ratificada**: la preimagen del `event_id` (D3) usa separador `\x1f`, mientras
  `flow_uid.hpp` usa length-prefix canónico. Unificar o documentar.
- Para el paper: aRGus no aporta ICMP; su `event_id` usa reloj monotónico; las primeras filas del
  adapter son ruido de checksum, no ataques.

### Arrastrado de DAY 225
- Sección de rangos de timestamp en `tools/eval/eve_field_coverage.py`.
- Retocar la puerta de diseño: (a) el 16,7% es propiedad de la captura (rango 1,2–16,7%);
  (b) §1.6 y los clientes FTP que FIJAN el puerto; (c) smallFlows es de 2011-01-25;
  (d) O3 ya está resuelta; (e) D5 reforzada por el contrato.
- `evidencia/README.md` con procedencia (pcap, Suricata 7.0.10, 52.003 firmas, comando `-r`).
- Deuda: el provisioning de Suricata no reinicia el servicio tras tocar el YAML.
- PR de `feat/suricata-to-graph` · rama `fix/test-gate-masked` · nota recíproca en
  `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (BACKLOG:5138).
- **Pieza `flow_uid` → rama aparte** (`fix/flow-uid-time-free` desde main).
- ~~P3 sin medir: ¿el `ON MATCH SET` machaca `flow_start`?~~ ✅ **CONTESTADO DAY 228: no existe
  `ON MATCH SET`.**
- Guard D-D diferido: cuando se active, `"suricata"` debe ser símbolo `DetectorSource` legal.

---

## Punteros
- `suricata-adapter/` — el componente. `src/to_row.cpp` es el mapeo.
- `correlation-engine/tools/bronze_to_gold_converter.cpp` — bronce → Avro + Parquet oro
- `correlation-engine/tools/parquet_to_kuzu_loader.cpp` — Parquet → Kuzu (CLI de 3 args)
- `correlation-engine/tools/kuzu_query.cpp` — 🆕 consulta ad-hoc contra una BD Kuzu
- `correlation-engine/include/correlation_engine/cypher_builder.hpp` — `is_alert` (línea 40),
  plantillas parametrizadas, `make_bindings`
- `correlation-engine/tests/test_flujo_b_end_to_end.cpp` — el molde: binarios reales + verificación
  en Kuzu + recomputación INDEPENDIENTE del `flow_uid`
- `libs/correlation-v1/{include,src}` — contrato, `validate` es notario único
- `ml-detector/src/correlation_writer.cpp:73-100` — el ORÁCULO (`to_correlation_v1_row`)
- `sniffer/src/userspace/ring_consumer.cpp:844` (bug) y `:1235` (arreglo)
- `logs/day227-adapter-out/` — CSV, Avro y Parquet de Suricata (clave de juguete, ignorado)
- `logs/day228-kuzu/suricata.kuzu` — el grafo de hoy (clave de juguete, ignorado)

## Comandos útiles
```
make suricata-adapter-test                # build + ctest en la VM suricata
make correlation-engine-test              # HOST -> VM defender (rm -rf build + ctest)
git grep -n '<patrón>' -- <ruta>/         # NUNCA grep -rn desde la raíz
vagrant ssh suricata -c "<comando>"       # la máquina va ANTES del -c
vagrant ssh -c "<comando>"                # a secas va a defender

# Build incremental de un solo target (sin rm -rf build)
vagrant ssh -c "cd /vagrant/correlation-engine/build && cmake .. -DCMAKE_BUILD_TYPE=Debug > /dev/null && make <target> -j4"

# Bronce -> Avro + Parquet oro
vagrant ssh -c "cd /vagrant && export ARGUS_BRONZE_HMAC_KEY_HEX=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef && ./correlation-engine/build/bronze_to_gold_converter <bronce.csv> <salida.avro> <salida.parquet>"

# Parquet oro -> Kuzu (NO necesita clave: el loader no verifica HMAC)
vagrant ssh -c "mkdir -p /vagrant/logs/<dir>"
vagrant ssh -c "cd /vagrant && ./correlation-engine/build/parquet_to_kuzu_loader <oro.parquet> <dir>/<bd>.kuzu correlation-engine/schema/schema.cypher"

# Consultar el grafo (comillas simples dentro, dobles fuera)
vagrant ssh -c "cd /vagrant && ./correlation-engine/build/kuzu_query logs/day228-kuzu/suricata.kuzu 'MATCH (f:NetworkFlow) RETURN count(*)'"
```

## Ritmo

DAY 228 cerró el paso 1 del plan de cierre en una sesión: las 2.870 filas de Suricata están en el
grafo y se consultan con una herramienta que ahora forma parte del repo.

Marcador de predicciones: 9 acertadas, 0 refutadas. **Con caveat honesto:** siete eran de bajo
riesgo, leídas del fuente treinta segundos antes de enunciarlas. Las dos que aportaron valor real
fueron detectar el bloqueo del enrutado **antes** de ejecutar (sin ella, el diagnóstico al ver
cero `Alert` habría sido "el loader no escribe alertas" y se habría destripado un loader que
estaba perfecto) y predecir que `NetworkFlow` sería muy inferior a 2.870, que produjo el 775.

El día no cambió de rumbo por lo que se ejecutó, sino por lo que se leyó antes de ejecutar.

*Via Appia Quality — antes de escribir el criterio de éxito, medir el discriminador del que depende.*