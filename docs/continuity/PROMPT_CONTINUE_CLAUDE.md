# PROMPT DE CONTINUIDAD — DAY 228 (continúa DAY 227)

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
- **🆕 Lección DAY 227 (la puerta que era un comentario):** el "alcance v1 mono-fuente" del
  `parquet_to_kuzu_loader` resultó ser **un comentario** (línea 17) más tres `using
  argus::correlation::` que son el NAMESPACE del proyecto. Cero comprobaciones en la lógica. Un
  aviso escrito no es una barrera de código. Antes de tratar una advertencia como un muro,
  medirla.
- **🆕 Lección DAY 227 (el artefacto que se evaporó):** las 2.870 filas de DAY 226 vivían en
  `/tmp` de la VM `suricata` y ya no existen. **Lo que importa va a `/vagrant`**, nunca a `/tmp`
  de una VM.
- **🆕 Lección DAY 227 (dos fuentes de verdad para un secreto):** el escritor lee la clave HMAC
  de etcd, el lector la lee del env. Nada las obliga a coincidir, y los dos tests del circuito
  firman *y* verifican con su propia constante, así que el problema es invisible al gate.
- **🆕 Lección DAY 227 (Claude también cae):** Claude afirmó que aRGus firma "con un campo de su
  JSON" infiriéndolo del nombre `config_.hmac_key_hex`. El grep vacío sobre `ml-detector/config/`
  lo refutó. La lección de los nombres que mienten aplica también al asistente.
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
posible — que las señales del resto de componentes lleguen al grafo — y escribir el paper de la
forma más honesta y científica posible. Fin de proyecto: 31-ago / primera semana de septiembre,
repositorio en modo lectura.

### Plan de cierre en 6 pasos
1. Terminar el pipeline aguas abajo; provocar que los datos lleguen al grafo. ← EN CURSO
2. Script MITRE para provocar datos → grafo.
3. Verificar que el grafo se consulta vía Kuzu.
4. Paper con las lecciones aprendidas.
5. README.md de verdad.
6. Repositorio en modo lectura.

---

## Estado — rama `feat/suricata-to-graph`

**El camino de Suricata llega hasta el Parquet oro.** Falta el último tramo: Parquet → Kuzu.

VMs: `defender` **running**, `suricata` **running**, `client` / `zeek` / `wazuh` **not created**.

⚠️ El toolchain de la VM `suricata` sigue instalado a mano, no en el `Vagrantfile`
(`DEBT-VM-SENSOR-NO-TOOLCHAIN-001`). Un `vagrant destroy` lo pierde.

---

## Lo conseguido en DAY 227

**Día de medición pura: NO se cambió ni una línea de código del repo.** Todo lo producido vive
bajo `logs/day227-adapter-out/`, que está ignorado.

### El criterio del día, cumplido

`bronze_to_gold_converter` sobre el CSV del adapter:

```
líneas totales:  2870
filas válidas:   2870
filas descartadas: 0
```

Salidas: `suricata.avro` (947.333 B) y `suricata.parquet` (483.985 B), desde un CSV de 997.065 B.

**El circuito bronce→oro aceptó un segundo sensor con CERO cambios de código.** Es la decisión de
arquitectura de DAY 222 (sin switches, diseño dirigido por datos) validada empíricamente y no por
argumento. Es una de las pocas afirmaciones del proyecto que se sostiene al medirla.

### Determinismo confirmado hasta la firma

La reejecución del adapter dio los contadores exactos de DAY 226
(`leidas=107264 escritas=2870 descartadas=104394 err_to_row=0 err_serialize=0`) y la primera fila
salió **byte a byte idéntica, HMAC incluido**. La clave de juguete de DAY 226 era
`0123456789abcdef` repetido 4 veces.

### El hallazgo: dos fuentes de verdad para la clave HMAC

| Quién | Dónde busca la clave |
|---|---|
| Escritor de aRGus (`correlation_writer.cpp:56` ← `zmq_handler.cpp:157` ← `main.cpp:438-442`) | `etcd_client->get_hmac_key()` |
| Lector / converter (`correlation-engine/src/main.cpp:79`, `bronze_to_gold_converter.cpp:368`) | env `ARGUS_BRONZE_HMAC_KEY_HEX` |

Nada en el código obliga a que coincidan. `git grep -i -e 'key' -e 'secret' -- ml-detector/config/`
confirma que la clave **no está en ningún JSON**: solo en etcd, en runtime.

Y hay dos lectores con exigencias distintas:

- **`bronze_to_gold_converter`**: batch, UN fichero por invocación, una clave por env → cada
  sensor puede usar la suya. Por eso el criterio de hoy no dependía de la clave de aRGus.
- **Consumidor del engine** (watcher inotify sobre el buzón PLANO): UNA sola clave para TODOS los
  ficheros del directorio → aquí todos los productores tienen que firmar igual.

**Consecuencia estructural:** bronce plano (DAY 222) + consumidor de clave única + aRGus firmando
desde etcd = incompatibilidad sin resolver. Salidas posibles: aRGus pasa a leer del env; o el
consumidor recibe un mapa clave-por-sensor; o etcd es fuente única para todos.

Agravante: si `SecretsManager` solo guarda la clave en memoria
(`DEBT-SECRETS-MANAGER-PERSISTENCE-001`), la clave que firmó
`logs/correlation/argus-2026-07-20-094233.csv` podría ser irrecuperable → **el bronce real de
aRGus sería inverificable para siempre**. Un ledger que no se puede verificar no es un ledger.
SOSPECHA, no veredicto: falta medir si etcd-server persiste o siembra determinista.

### Otros hallazgos (no volver a medir)

- El converter **no tiene descubrimiento de ficheros**: `<bronce.csv> <bronce_salida.avro>
  <oro_salida.parquet>`, tres rutas explícitas. La sospecha del basename `suricata-*.csv` se cayó
  por inexistencia del sujeto.
- El converter **sí verifica** el HMAC por fila (`parse_and_verify`, línea 148) y preserva la
  col 18 con `extract_hmac_field`.
- El converter **no tiene target en el Makefile**; se construye desde
  `correlation-engine/CMakeLists.txt:132` y se invoca a mano. Binario ya presente en `defender`:
  `/vagrant/correlation-engine/build/bronze_to_gold_converter`.
- `.gitignore` tiene **dos líneas corruptas** con la misma firma (comentario pegado a un patrón):
  `logs/# ONNX models (generate on-the-fly)` y `contrib/claude/pca_pipeline/*.npz# Build artifacts`.
  La primera sobrevive por casualidad (la `logs/` de debajo hace el trabajo); la segunda deja los
  `.npz` de esa ruta **sin ignorar**. Medir el artefacto, no el fichero:
  `git ls-files | grep -i -e '\.onnx$' -e '\.npz$'`.
- Rot de documentación: `bronze_to_gold_converter.cpp:26` cita
  `logs/correlation/argus/2026-07-04-032653.csv` — subdirectorio por sensor, el mundo anterior a
  la decisión de bronce plano de DAY 222.
- `suricata-adapter/config/suricata_adapter.json` tiene `input_path` **relativo**: el adapter hay
  que lanzarlo desde `/vagrant` o no resuelve.

### El muro del loader, medido

`git grep -i -e 'argus' -e 'source_sensor' -- correlation-engine/tools/parquet_to_kuzu_loader.cpp`:

- línea 17 → **comentario** de alcance mono-fuente
- líneas 68-70 → `using argus::correlation::...`, el **namespace** del proyecto
- líneas 176, 201 → lee `source_sensor` de la columna 1 y lo asigna al record: **dato, no
  constante**

Cero comprobaciones que rechacen un sensor distinto de `argus`. **La puerta es una decisión, no
una refactorización.** Lo que el grep NO cubre: `KuzuGraphSink`, donde vive la persistencia.

---

## Plan DAY 228 — propuesta

**Una batalla: que las filas de Suricata lleguen al grafo Kuzu.** Es el cierre del paso 1 del plan
de cierre.

1. **Leer la invocación del loader** (`sed -n '1,40p'
   correlation-engine/tools/parquet_to_kuzu_loader.cpp`) — CLI y argumentos.
2. **BD Kuzu FRESCA**, no la persistida. Doble motivo: estas filas llevan clave de juguete, y
   `CREATE NODE TABLE IF NOT EXISTS` **no migra catálogos existentes**, así que cualquier BD
   anterior a los cambios de esquema de DAY 222 hay que recrearla igualmente.
3. **Cargar SOLO Suricata.** Sus `NetworkFlow` no van a converger con los de aRGus mientras
   `DEBT-SNIFFER-IP-BYTE-ORDER-001` siga abierta — serían nodos separados, y eso es honesto: es
   exactamente el "grafo de un feed" que el propio diseño declara como configuración legítima.
4. **Criterio de éxito del día:** una consulta Cypher que devuelva un `Alert` con
   `source_sensor = "suricata"` colgando de su `NetworkFlow`. Ni MITRE, ni convergencia.

Verificación gratis por el camino: el converter imprimió
`flow_uid recomputado (fila 0): eCjFUYOr5nsLGWZykRvJBkwFO+wMicFym9oGylrznAk=`, con la nota de
compararlo bit a bit contra la propiedad `flow_uid` materializada en Kuzu.

**Alternativa si prefieres otra batalla:** arreglar `DEBT-SNIFFER-IP-BYTE-ORDER-001` (una palabra
en `ring_consumer.cpp:844-845`) + su test de regresión. Desbloquea la convergencia, que es la
afirmación central del paper, pero exige rebuild de `defender` y pasar EMECAS.

---

## Automatización pedida por Alonso (DAY 227, para después del grafo)

1. Poder **activar/desactivar el feed** de cada sensor a voluntad.
2. **Makefile**: compilación completa del correlation-engine y targets del converter/loader.
3. **Tests e2e para Suricata**, equivalentes a los que ya existen para aRGus
   (`test_flujo_a_b_equivalence`, `test_flujo_b_end_to_end`).
4. Actualizar `make pipeline-start`, `pipeline-status` y demás tareas para que incluyan Suricata,
   el servidor aguas abajo y la ingesta de Kuzu.

⚠️ **Dos matices sobre el punto 1, antes de diseñarlo:**

- Un **interruptor por config contradice la decisión ratificada de DAY 222** ("sin switches en
  ningún JSON; diseño dirigido por datos: si los ficheros del contrato llegan al bronce, el grafo
  los usa"), que es justamente la decisión que DAY 227 validó empíricamente. Para Suricata el
  interruptor **ya existe y es gratis**: el adapter es de lote, se ejecuta o no se ejecuta. El
  caso difícil es aRGus, que exige levantar todo el stack — y esa es la razón de fondo del futuro
  `argus-adapter`.
- "Que Kuzu los procese **según lleguen**" implica pasar por el consumidor con inotify sobre el
  buzón plano, y ahí es donde **muerde la clave única**. Automatizar la ingesta obliga a resolver
  antes las dos fuentes de verdad de la clave HMAC.

---

## Aparcado (no olvidar)

### Nuevo de DAY 227
- Registrar en `docs/BACKLOG.md`: la discrepancia etcd-vs-env de la clave (nota en
  `DEBT-BRONZE-KEY-PROVISIONING-001` y en `DEBT-BRONZE-HMAC-KEY-POLICY-001`), el `.gitignore`
  corrupto, y el rot de `bronze_to_gold_converter.cpp:26`.
- Medir si `SecretsManager` persiste la clave o la pierde con el proceso.
- `git ls-files | grep -i -e '\.onnx$' -e '\.npz$'` — ¿hay blobs de modelo trackeados?

### De DAY 226
- **`DEBT-SNIFFER-IP-BYTE-ORDER-001`** — dos `[PENDIENTE]`: (a) confirmar el sentido de
  `event.src_ip` en el lado eBPF (`git ls-files -- 'sniffer/*' | grep -i -e bpf -e kern`, porque
  el grep en `sniffer/src/ebpf/` salió vacío); (b) si `main_libpcap.cpp` tiene el mismo defecto.
  **Definición de HECHO:** test de regresión que lea una fila real del bronce y compare su
  `community_id` contra el oráculo `pycommunityid` recalculado desde las IPs de esa misma fila.
- **`DEBT-VM-SENSOR-NO-TOOLCHAIN-001`** — bloque `ADAPTER_TOOLCHAIN` en el `Vagrantfile` raíz,
  reutilizable en `zeek` y `wazuh`, con verificación **por invocación** (`cmake --version`,
  `pkg-config --modversion libsodium`), no por "el paquete figura instalado".
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
  (d) **O3 ya está resuelta** — firma el adapter; (e) D5 reforzada por el contrato.
- `evidencia/README.md` con procedencia (pcap, Suricata 7.0.10, 52.003 firmas, comando `-r`).
- Deuda: el provisioning de Suricata no reinicia el servicio tras tocar el YAML.
- PR de `feat/suricata-to-graph` · rama `fix/test-gate-masked` · nota recíproca en
  `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (BACKLOG:5138).
- **Pieza `flow_uid` → rama aparte** (`fix/flow-uid-time-free` desde main).
- P3 sin medir: ¿el `ON MATCH SET` machaca `flow_start`? (`cypher_builder.hpp:103,112`).
- Guard D-D diferido: cuando se active, `"suricata"` debe ser símbolo `DetectorSource` legal.

---

## Punteros
- `suricata-adapter/` — el componente. `src/to_row.cpp` es el mapeo.
- `correlation-engine/tools/bronze_to_gold_converter.cpp` — bronce → Avro + Parquet oro
- `correlation-engine/tools/parquet_to_kuzu_loader.cpp` — Parquet → Kuzu (la batalla de hoy)
- `correlation-engine/src/kuzu_graph_sink.cpp` + `include/.../cypher_builder.hpp` — la persistencia
- `libs/correlation-v1/{include,src}` — contrato, `validate` es notario único
- `ml-detector/src/correlation_writer.cpp:73-100` — el ORÁCULO (`to_correlation_v1_row`)
- `sniffer/src/userspace/ring_consumer.cpp:844` (bug) y `:1235` (arreglo)
- `logs/day227-adapter-out/` — CSV, Avro y Parquet de Suricata (clave de juguete, ignorado por git)

## Comandos útiles
```
make suricata-adapter-test                # build + ctest en la VM suricata
make correlation-engine-test              # HOST -> VM defender
git grep -n '<patrón>' -- <ruta>/         # NUNCA grep -rn desde la raíz
vagrant ssh suricata -c "<comando>"       # `vagrant ssh -c` a secas va a defender

# Regenerar el bronce de Suricata (clave de juguete, directorio scratch)
vagrant ssh suricata -c "cd /vagrant && export ARGUS_BRONZE_HMAC_KEY_HEX=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef && ./suricata-adapter/build-suricata/suricata_adapter logs/day227-adapter-out/suricata_adapter.json"

# Bronce -> Avro + Parquet oro
vagrant ssh -c "cd /vagrant && export ARGUS_BRONZE_HMAC_KEY_HEX=0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef && ./correlation-engine/build/bronze_to_gold_converter <bronce.csv> <salida.avro> <salida.parquet>"
```

## Ritmo

DAY 227 no cambió una línea de código y fue de los días más productivos: el criterio se cumplió
por 2.870, se confirmó determinismo byte a byte, y las dos cosas que de verdad importan salieron
de mirar dónde estaba la clave y de leer entero un grep que parecía un muro.

El marcador de predicciones fue 5 acertadas y 2 refutadas. Las dos refutaciones fueron de Claude
—la clave "en el JSON" (inferida de un nombre, no del cuerpo) y el descubrimiento de ficheros del
converter (que no existe)— y las dos ahorraron trabajo real: el plan escrito del día tenía dos
pasos que no hacían falta.

*Via Appia Quality — un aviso escrito no es una barrera de código.*