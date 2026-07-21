# PROMPT DE CONTINUIDAD — DAY 227 (continúa DAY 226)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. Cada línea rastreable a lo pedido.
4. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria.
- **Lección DAY 211 (lecturas parciales):** no concluir "X no existe" desde un `sed -n`, un
  `head` o un grep de filtro estrecho. Fichero entero antes de afirmar ausencia. *(Reforzada
  DAY 226: `git grep 'src_ip' -- sniffer/src/ebpf/` salió vacío y NO prueba nada — la ruta
  probablemente no es esa.)*
- **Lección DAY 223 (el grep que costó una noche):** `grep -rn` desde la raíz arrastra `build/`,
  `.git/`, `.venv/`, `vendor/`. Usar `git grep` o acotar con `-- ruta/`. Y **nunca encadenar dos
  comandos de salida grande**: el segundo se come la salida del primero.
- **Lección DAY 223 (BACKLOG):** ninguna deuda vive en fichero propio. Todas son secciones `###`
  dentro de `docs/BACKLOG.md`.
- **Lección DAY 224 (el número que nadie midió):** el "24 campos" llevaba 17 días mintiendo.
  Antes de propagar una cifra al paper, medirla.
- **Lección DAY 224 (constructos que no distinguen "hizo" de "no hizo"):** `sed -i` devuelve 0
  aunque no sustituya nada → el fallback del `||` está muerto. Igual el `||` del Makefile.
- **Lección DAY 225 (la config que el proceso no ha leído):** verificar el FICHERO no basta.
  Comparar **mtime de la config contra la hora de arranque del proceso**. El sujeto de la
  verificación es el proceso, no el fichero.
- **Lección DAY 225 (nombres que mienten):** `flow_start_window` no ventanea, `emecas+++` es un
  alias de `emecas++`, y un "campo vacío" resultó no poder estar vacío (es `double`). Leer el
  cuerpo, no el nombre.
- **🆕 Lección DAY 226 (verde en la capa equivocada):** el `community_id` de aRGus pasó 8/8
  contra el oráculo `pycommunityid` en DAY 170 y **el pipeline llevaba 56 días escribiendo
  `community_id` corruptos**. El test validaba la función; nadie validó el ARTEFACTO FINAL. Un
  verde en una capa intermedia no dice nada de la salida. Medir el fichero que se produce.
- **🆕 Lección DAY 226 (dos caminos que discrepan):** `ring_consumer.cpp:844` y `:1235` hacen lo
  mismo de dos formas distintas (uno con `htonl`, otro sin). Cuando el mismo fichero implementa
  la misma conversión dos veces, **una de las dos está mal por definición**. Buscar duplicados
  antes que bugs.
- **🆕 Lección DAY 226 (el nivel superior no es el flujo):** en `eve.json` el par src/dest de
  nivel superior es el del PAQUETE; el objeto `flow` lleva el del ORIGINADOR, y en el 99,4% de
  las alertas están invertidos entre sí. Leer la estructura anidada, no el primer campo con el
  nombre correcto.
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
forma más honesta y científica posible, mostrando los datos, para que en el futuro alguien pueda
retomar la investigación. Fin de proyecto: 31-ago / primera semana de septiembre, repositorio en
modo lectura.

### Plan de cierre en 6 pasos
1. Terminar el pipeline aguas abajo; provocar que los datos lleguen al grafo. ← EN CURSO
2. Script MITRE para provocar datos → grafo.
3. Verificar que el grafo se consulta vía Kuzu.
4. Paper con las lecciones aprendidas.
5. README.md de verdad.
6. Repositorio en modo lectura.

---

## Estado — rama `feat/suricata-to-graph`

**El `suricata-adapter` existe, compila y produce filas válidas.** DAY 226 lo escribió entero,
lo construyó dentro de la VM `suricata` y lo ejecutó sobre el `eve.json` del Neris.

VMs (medido DAY 226): `defender` **running**, `suricata` **running**, `client` / `zeek` /
`wazuh` **not created**.

⚠️ El toolchain de la VM `suricata` (`build-essential cmake pkg-config libsodium-dev
nlohmann-json3-dev libssl-dev`) se instaló **a mano**. No está en el `Vagrantfile`: un
`vagrant destroy` lo pierde. → `DEBT-VM-SENSOR-NO-TOOLCHAIN-001`.

---

## Lo conseguido en DAY 226

### El adapter, verde extremo a extremo

`make suricata-adapter-test` → 2/2 verdes (`correlation_v1_tests` 3,74 s + `suricata_adapter_to_row`
0,02 s). El build suelto arrastra `libs/correlation-v1` por la guarda del CMakeLists, así que el
contrato entero queda validado también dentro de la VM `suricata`.

Ejecución sobre `logs/day225-suricata-neris/eve.json` (55.442.376 B), contadores **exactamente**
los predichos contra la tabla de DAY 225:

```
leidas=107264  escritas=2870  descartadas=104394  err_to_row=0  err_serialize=0
```

`err_serialize=0` significa que **las 2.870 filas pasaron `validate()`**. El criterio del día
era una. Salida: 997.065 B, ~347 B/fila.

Primera fila producida (19 columnas verificadas; `event_id` 44 chars base64 = 32 B de BLAKE2b;
HMAC 64 hex de SHA256):

```
1,suricata,suricata:P7D/AmXaM0z8rN89xkIsMVu7AFD7qOgp9kflk+gFoWM=,cpp_sniffer_v33_day12,
1:MuSlbWV2Dy5Z168c5sxOWncbYyQ=,1312967196,78254000,147.32.84.165,94.63.149.152,1040,80,TCP,
SURICATA TCPv4 invalid checksum,Generic Protocol Command Decode,0.000000,0.000000,0.000000,
suricata,21def7767b42d30731bab0d9e92a577d2b45923aa4b8ca008be34bc8468d3bc3
```

La col 7 es `147.32.84.165` (orientación del objeto `flow`) y no `94.63.149.152` (la del
paquete). Sin comillas, coherente con las **cero comas** medidas en las firmas del Neris.

### El bug gordo: DEBT-SNIFFER-IP-BYTE-ORDER-001

La primera fila del bronce de aRGus (`logs/correlation/argus-2026-07-20-094233.csv`) trae las
IPs con los bytes invertidos: `1.56.168.192` es `192.168.56.1`, y `255.56.168.192` es
`192.168.56.255`. Y el `community_id` de esa fila **coincide con el calculado desde los bytes
invertidos** (verificado con el estándar Corelight, seed 0, UDP; con las IPs correctas sale
`1:hF8qbh3/+MvwfDC6onu0ugDlH/8=`).

Causa raíz localizada, y el arreglo ya existe 390 líneas más abajo en el mismo fichero:

| Fichero:línea | Código | Veredicto |
|---|---|---|
| `ring_consumer.cpp:844-845` | `struct in_addr src_addr = {.s_addr = event.src_ip};` | ❌ sin `htonl` — **camino que alimenta el bronce** |
| `ring_consumer.cpp:1235-1236` | `src_addr.s_addr = htonl(event.src_ip);` | ✅ correcto — camino de alerta |

`compute_community_id()` es inocente: recibe las IPs como `std::string` ya formateado, así que el
hash y la cadena del CSV beben de la misma fuente. **Un solo arreglo repara las dos.**

**Consecuencia viva:** las filas de Suricata y las de aRGus **no convergen** hasta arreglarlo.
El adapter es correcto; su contraparte no.

### Otros hallazgos de DAY 226 (no volver a medir)

- `csv_string()` (correlation_v1.cpp:33-40) **sí** entrecomilla y escapa (coma, comilla, `\n`;
  duplica comillas internas). `fmt_double` hace `imbue(classic())` + `setprecision(6)`. El
  adapter lo hereda gratis por usar `serialize()`. **No hay nada que arreglar en Suricata**:
  `eve.json` es JSON y ya entrecomilla de forma nativa.
- **Cero firmas con coma** en el eve.json del Neris.
- `node_id` real de aRGus = `cpp_sniffer_v33_day12` → es una **etiqueta de versión del sniffer**,
  ni host ni punto de observación. D2 no está implementada de facto, y un bump de versión
  cambiaría todos los `flow_uid`.
- `event_id` de aRGus (`ring_consumer.cpp:854`) = `timestamp + "_" + (src_ip ^ dst_ip)`, con
  `timestamp` de **reloj monotónico de uptime** (~10.304 s). No es reproducible entre arranques,
  y confirma que `flow_start_sec` de aRGus **no es hora de pared**.
- `compute_community_id` devuelve `nullopt` para no-TCP/UDP → **aRGus no aporta ni una fila de
  ICMP al bronce**, mientras Suricata sí. Asimetría de cobertura entre sensores, para el paper.
- El comentario de `serialize()` ya dice de dónde saca la clave cada productor: *"ARGUS_BRONZE_
  HMAC_KEY_HEX en test, etcd-server en el adapter"*. **Resuelve el conflicto O3** de la puerta de
  diseño: no hay colector único que firme; firma el adapter.
- El target de `libs/correlation-v1` se llama `correlation_v1` y es **SHARED**.
- El repo localiza libsodium con `pkg_check_modules(LIBSODIUM REQUIRED libsodium)`
  (`correlation-engine/CMakeLists.txt:10`).
- Patrón del Makefile: **todos** los componentes se construyen dentro de una VM con
  `vagrant ssh -c`; a secas va a `defender`. Solo `eslabon1-smoke-build` nombra la VM.

---

## El estándar de adapters (fijado DAY 226)

Cada adapter es un **componente de primer nivel** `<sensor>-adapter/`, hermano de `sniffer/` y
`ml-detector/`. Generador: `tools/scaffold_adapter.py --sensor <nombre>` (idempotente, `--force`,
`--dry-run`, `--root`). Solo `suricata` tiene mapeo escrito; otros sensores reciben un `to_row.cpp`
stub que devuelve `Error` a propósito.

```
<sensor>-adapter/
├── CMakeLists.txt · README.md · .gitignore
├── config/<sensor>_adapter.json
├── include/<sensor>_adapter/{to_row,batch_writer,config}.hpp
├── src/{to_row,batch_writer,config,main}.cpp
└── tests/{CMakeLists.txt,test_to_row.cpp}
```

Corte en tres capas heredado de `correlation_v1.hpp`:
`[nativo→Row]` `to_row.cpp` del adapter (**puro**: sin fichero, sin reloj, sin red) ·
`[Row→bytes]` `serialize()` de la librería (**notario único, nunca reimplementar**) ·
`[bytes→disco]` `BatchWriter` propio (lote, un fichero por ejecución, `.tmp`→`rename`).

**Alonso quiere que el adapter de aRGus, hoy incrustado en `ml-detector`
(`to_correlation_v1_row`), salga de ahí en una refactorización y cumpla este mismo estándar.**

---

## Plan DAY 227 — propuesta

**Una batalla: que las filas de Suricata lleguen al Parquet oro.** Es el paso 1 del plan de
cierre y no depende de arreglar el bug de orden de bytes (Suricata solo ya puede recorrer el
circuito; la convergencia con aRGus es otra cosa).

1. **Clave HMAC real.** Medir de dónde la saca aRGus hoy (`ARGUS_BRONZE_HMAC_KEY_HEX` en el
   entorno de la VM `defender`, o etcd-server). Sin la misma clave, el lector de aguas abajo
   rechazará las filas de Suricata. La pasada de DAY 226 usó una clave de juguete.
2. **Escribir al buzón real** `/vagrant/logs/correlation` en vez de a `/tmp/adapter-out`.
   Cuidado: ahí escribe aRGus; no contaminar hasta tener la clave buena.
3. **Pasar el `bronze_to_gold_converter`** sobre el buzón y medir si acepta filas con
   `source_sensor=suricata`. Sospechas a verificar, no a asumir: ¿asume `argus` en algún sitio?
   ¿el basename `suricata-*.csv` casa con su patrón de descubrimiento de ficheros?
4. **Criterio de éxito del día:** una fila de Suricata en el Parquet oro. Ni Kuzu, ni grafo.

**Alternativa si prefieres otra batalla:** arreglar `DEBT-SNIFFER-IP-BYTE-ORDER-001` (una palabra
en `ring_consumer.cpp:844-845`) + su test de regresión. Desbloquea la convergencia, que es la
afirmación central del paper, pero exige rebuild de `defender` y pasar EMECAS.

---

## Aparcado (no olvidar)

### De DAY 226
- **`DEBT-SNIFFER-IP-BYTE-ORDER-001`** — escrita en el BACKLOG. Dos `[PENDIENTE]` antes de
  aplicar el arreglo: (a) confirmar el sentido de `event.src_ip` en el lado eBPF —el grep en
  `sniffer/src/ebpf/` salió vacío, hay que localizar la struct del evento con
  `git ls-files -- 'sniffer/*' | grep -i -e bpf -e kern`—; (b) si `main_libpcap.cpp` tiene el
  mismo defecto (el tramo 120-150 no llega a donde se fija `nf->source_ip()`).
  **Definición de HECHO:** test de regresión que lea una fila real del bronce y compare su
  `community_id` contra el oráculo `pycommunityid` recalculado desde las IPs de esa misma fila.
- **`DEBT-VM-SENSOR-NO-TOOLCHAIN-001`** — bloque `ADAPTER_TOOLCHAIN` en el `Vagrantfile` raíz,
  reutilizable en `zeek` y `wazuh`, con verificación **por invocación** (`cmake --version`,
  `pkg-config --modversion libsodium`), no por "el paquete figura instalado".
- Nota recíproca en `DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001`: su cierre cubre la función, **no el
  llamante**; el camino a producción está bloqueado por la deuda del orden de bytes.
- **Telemetría (D4)**: hoy el adapter descarta los 104.392 eventos de dns/http/tls/… El 98,7% del
  volumen de Suricata no llega al grafo todavía.
- **Decisión no ratificada**: la preimagen del `event_id` (D3) usa separador `\x1f`, mientras
  `flow_uid.hpp` usa length-prefix canónico. Unificar o documentar la diferencia.
- Para el paper: aRGus no aporta ICMP; el `event_id` de aRGus usa reloj monotónico; las primeras
  filas del adapter son ruido de checksum (artefacto de la captura), no ataques.

### Arrastrado de DAY 225
- Sección de rangos de timestamp en `tools/eval/eve_field_coverage.py`, para que
  `eve-coverage-stale-config.txt` demuestre por sí solo la transición 05:12 → 05:24.
- Retocar la puerta de diseño: (a) el 16,7% es propiedad de la captura, no del diseño (rango
  1,2–16,7%); (b) §1.6 dice "puerto efímero" y hay clientes FTP que FIJAN el puerto; (c)
  smallFlows es de 2011-01-25, no de 2015; (d) **O3 ya está resuelta** — el comentario de
  `serialize()` dice que firma el adapter; (e) D5 reforzada por el contrato.
- `evidencia/README.md` con procedencia (pcap, Suricata 7.0.10, 52.003 firmas, comando `-r`).
- Deuda: el provisioning de Suricata no reinicia el servicio tras tocar el YAML.
- PR de `feat/suricata-to-graph` · rama `fix/test-gate-masked` · nota recíproca en
  `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (BACKLOG:5138).
- **Pieza `flow_uid` → rama aparte** (`fix/flow-uid-time-free` desde main): toca identidad del
  sistema entero. Vectores congelados a regenerar; BD Kuzu persistida queda obsoleta.
- P3 sin medir: ¿el `ON MATCH SET` machaca `flow_start`? (`cypher_builder.hpp:103,112`).
- Guard D-D diferido: cuando se active, `"suricata"` debe ser símbolo `DetectorSource` legal.
- Makefile multicomponente: ya hay un segundo productor, así que **ya toca**.

---

## Punteros
- `suricata-adapter/` — el componente. `src/to_row.cpp` es el mapeo; el resto es andamiaje.
- `tools/scaffold_adapter.py` — generador del estándar de adapters.
- `docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md` + `evidencia/`
- `libs/correlation-v1/{include,src}` — contrato, `validate` es notario único
- `ml-detector/src/correlation_writer.cpp:73-100` — el ORÁCULO (`to_correlation_v1_row`)
- `sniffer/src/userspace/ring_consumer.cpp:844` (bug) y `:1235` (arreglo)
- `correlation-engine/include/correlation_engine/flow_uid.hpp` — identidad, tag de versión
- `tools/eval/eve_field_coverage.py` — reproduce las cifras de la puerta de diseño
- `DEBT-HOST-DOMAIN-CONTRACT-001` — Wazuh es dominio host (`host_domain_v1`), **no converge por
  `flow_uid`**. El paper no puede decir "grafo unificado de los cuatro" sin matiz.

## Comandos útiles
```
make suricata-adapter-test                # build + ctest en la VM suricata
make correlation-engine-test              # HOST -> VM defender
python3 tools/scaffold_adapter.py --sensor <nombre> [--force|--dry-run]
python3 tools/eval/eve_field_coverage.py <eve.json>
git grep -n '<patrón>' -- <ruta>/         # NUNCA grep -rn desde la raíz
vagrant ssh suricata -c "<comando>"       # `vagrant ssh -c` a secas va a defender
```

## Ritmo

DAY 226 cumplió su criterio (una fila) por un factor de 2.870, pero lo importante fueron los dos
hallazgos que no estaban en el plan. El bug de orden de bytes llevaba **56 días** escribiendo
`community_id` corruptos con un test unitario en verde encima. Y la orientación de las columnas
7-10 habría envenenado el 99,4% de las filas si el adapter hubiera copiado el campo con el nombre
correcto en vez del sitio correcto. Ninguno de los dos salió de leer documentación: el primero
salió de mirar una línea del CSV que el pipeline había escrito de verdad, y el segundo de mirar
la línea de `eve.json` que íbamos a parsear.

Tres de las predicciones de Claude quedaron refutadas por la medida ese día (el `node_id`, el
formateo manual de las IPs, y que el componente no compilaría a la primera). Es la señal de que
el ciclo funciona: predecir en voz alta y dejar que el fichero conteste.

*Via Appia Quality — un verde en la capa de abajo no dice nada de lo que sale por arriba.*