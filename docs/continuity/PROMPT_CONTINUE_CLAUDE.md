# PROMPT DE CONTINUIDAD — DAY 230 (continúa DAY 229)

## Instrucciones generales para Claude
1. Piensa antes de codificar. Expón suposiciones. Pregunta cuando no estés seguro. Nunca adivines.
2. Simplicidad primero. Código mínimo. Sin abstracciones que nadie pidió.
3. Cambios quirúrgicos. Cada línea rastreable a lo pedido.
4. Instrucciones vagas → criterios de éxito verificables.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria.
- **Lección DAY 211 (lecturas parciales):** no concluir "X no existe" desde un `sed -n`, un
  `head` o un grep de filtro estrecho. Fichero entero antes de afirmar ausencia.
  *(DAY 229 la cobró DOS veces: el código eBPF sí existía —en `src/kernel/`, no en `src/ebpf/`—
  y los tests "sin `add_test`" sí se ejecutaban, desde el Makefile.)*
- **Lección DAY 223 (el grep que costó una noche):** `grep -rn` desde la raíz arrastra `build/`,
  `.git/`, `.venv/`, `vendor/`. Usar `git grep` o acotar con `-- ruta/`. Y **nunca encadenar dos
  comandos de salida grande**.
- **Lección DAY 223 (BACKLOG):** ninguna deuda vive en fichero propio. Todas son secciones `###`
  dentro de `docs/BACKLOG.md`.
- **Lección DAY 224 (el número que nadie midió):** antes de propagar una cifra al paper, medirla.
- **Lección DAY 224 (constructos que no distinguen "hizo" de "no hizo"):** `sed -i` devuelve 0
  aunque no sustituya nada. Igual el `||` del Makefile.
- **Lección DAY 225 (la config que el proceso no ha leído):** el sujeto de la verificación es el
  proceso, no el fichero.
- **Lección DAY 225 (nombres que mienten):** leer el cuerpo, no el nombre.
- **Lección DAY 226 (verde en la capa equivocada):** un verde en una capa intermedia no dice nada
  de la salida. Medir el fichero que se produce.
- **Lección DAY 226 (dos caminos que discrepan):** si el mismo fichero implementa la misma
  conversión dos veces, una de las dos está mal por definición.
- **Lección DAY 227 (la puerta que era un comentario):** un aviso escrito no es una barrera de
  código.
- **Lección DAY 227 (el artefacto que se evaporó):** lo que importa va a `/vagrant`, nunca a
  `/tmp` de una VM.
- **Lección DAY 228 (dos decisiones que nunca se vieron la cara):** antes de escribir el criterio
  de éxito, medir el discriminador del que depende.
- **Lección DAY 228 (el idioma ya estaba en casa):** antes de escribir contra una librería, buscar
  quién en el repo ya la usa.
- **🆕 Lección DAY 229 (el criterio que no puede fallar):** la definición de HECHO de
  `DEBT-SNIFFER-IP-BYTE-ORDER-001` era "recomputar el `community_id` desde las IPs de la propia
  fila". Pasaba VERDE con el bug presente, porque hash y cadena beben de la misma fuente
  corrupta. **Antes de aceptar un criterio, comprobar que puede ponerse rojo.**
- **🆕 Lección DAY 229 (un sensor único no puede auditarse a sí mismo):** con una sola fuente,
  toda verificación interna sale coherente porque todo está igual de mal. Hizo falta un
  observador externo (Suricata, fórmula Corelight) para que la discrepancia existiera. Es el
  argumento empírico más fuerte del proyecto a favor del multi-sensor.
- **🆕 Lección DAY 229 (la alarma con la explicación puesta de antemano):** `crosscheck-run`
  trata el `exit 2` del verificador de paridad como "anomalías esperadas por cobertura asimétrica
  aRGus". La puerta existía y disparaba; su señal venía preetiquetada como ruido. **HIPÓTESIS SIN
  MEDIR** — confirmar o descartar en DAY 230.
- **🆕 Lección DAY 229 (el bug que solo se ve en las IPs que reconoces):** invertir cuatro octetos
  produce otra IP sintácticamente válida. `165.84.32.147` no llama la atención de nadie; por eso
  sobrevivió cinco meses sobre el CTU-13. Solo chirriaba en `192.168.` y `255`.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable;
  Kuzu = proyección reconstruible por MERGE).
- **EMECAS+++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- macOS/zsh: comillas en globs, NUNCA `sed -i`, Python3 heredoc para editar. Commits/push desde
  el HOST. `git add` explícito por fichero, nunca `-u` ni `-a`.
- Parches idempotentes: **anclar el guard en el RESULTADO, no en el punto de inserción**
  (validado en vivo DAY 229: el `YA ESTABA — no se toca` evitó una duplicación).
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
3. ~~Verificar que el grafo se consulta vía Kuzu.~~ ✅ **HECHO DAY 228** (`kuzu_query`).
4. Paper con las lecciones aprendidas.
5. README.md de verdad.
6. Repositorio en modo lectura.

---

## Estado — DOS ramas vivas

| rama | estado |
|---|---|
| `fix/sniffer-ip-byte-order` | **actual**, pusheada, base main `fb08e8f6`. El arreglo del byte order |
| `feat/suricata-to-graph` | pusheada, **sin mergear a main**. Todo el trabajo del adapter + grafo |

**Orden acordado:** esta rama a main primero (es pequeña y aislada), luego rebasar
`feat/suricata-to-graph` sobre el main ya arreglado, para que el adapter herede el sniffer bueno.

VMs: `defender` **running**, `suricata` **running**, `client` / `zeek` / `wazuh` **not created**.

⚠️ **EMECAS+++ destruye la VM `suricata`** (`vagrant destroy -f` ignora `autostart:false`, medido
DAY 226) y con ella su toolchain instalado a mano. Sería la tercera vez. Pagar antes
`DEBT-VM-SENSOR-NO-TOOLCHAIN-001` (bloque `ADAPTER_TOOLCHAIN` en el Vagrantfile raíz) lo convierte
en no destructivo, y además sirve para `zeek` y `wazuh`.

⚠️ **El bronce de ESTA rama cae en `/vagrant/logs/correlation/argus`** (ruta por sensor,
`correlation_engine.json:32` + `ml_detector_config.json:422`). El bronce PLANO con prefijo
`argus-` de DAY 222 vive solo en `feat/suricata-to-graph`. No buscar el CSV en el sitio de la otra
rama.

---

## Lo conseguido en DAY 229 — `DEBT-SNIFFER-IP-BYTE-ORDER-001` arreglado por la raíz

### Causa raíz, medida en el kernel (no inferida)

`sniffer/src/kernel/sniffer.bpf.c:232`:

```c
event->src_ip = (ip[12] << 24) | (ip[13] << 16) | (ip[14] << 8) | ip[15];
```

Ensambla la IP a mano como **entero en orden de HOST** — correcto y deliberado, e independiente
del endianness de la máquina. `ring_consumer.cpp:844` se lo pasaba a `inet_ntop` **sin deshacer la
conversión**, y en x86 los bytes en memoria quedan al revés:

| paso | valor |
|---|---|
| cable `ip[12..15]` | `C0 A8 38 01` |
| `event->src_ip` | `0xC0A83801` |
| memoria (little-endian) | `01 38 A8 C0` |
| `inet_ntop` | **`1.56.168.192`** |

Cuadra exactamente con el CSV medido en DAY 226. El falsador (que el kernel asignara
`iph->saddr` en crudo) quedó descartado.

**Contrato del evento eBPF, ahora explícito:** todos los campos son NÚMEROS en orden de host.
Userspace solo debe convertir donde use una API orientada a BYTES. `ring_consumer.cpp:844` era la
ÚNICA violación → el arreglo es seguro, ningún otro campo la necesitaba.

### Tres sitios de conversión, no dos

| sitio | forma | veredicto |
|---|---|---|
| `ring_consumer.cpp:844` | `s_addr = event.src_ip` | 🔴 mal |
| `ring_consumer.cpp:1235` | `s_addr = htonl(event.src_ip)` | 🟢 bien |
| `main_libpcap.cpp:115` | puntero a `iph->ip_src` | 🟢 bien |

Consecuencia cerrada por el propio arreglo: la Variante A (eBPF) y la Variante B (libpcap)
producían `community_id` **incompatibles entre sí**. Ya no. Y explica por qué el bug sobrevivió:
quien probara por libpcap veía `community_id` correctos.

### Lo que se hizo

- `sniffer/include/ip_format.hpp` (nuevo) — `ip_host_to_buffer(uint32_t, char*, size_t)`, punto
  ÚNICO de conversión, **sin asignar memoria** (el camino principal usa buffers preasignados
  reutilizados; devolver `std::string` habría metido una asignación por paquete).
- `sniffer/tests/test_ip_format.cpp` (nuevo) — oráculo EXTERNO (aritmética de la RFC). **Sin
  `assert()`**: el perfil `production` lleva `-DNDEBUG` y habría vaciado el test. Devuelve
  código != 0 explícito.
- Los cuatro `inet_ntop` de `ring_consumer.cpp` pasan por la función. El camino de alerta pierde
  su `htonl` externo. **La duplicación que causó el fallo desaparece.**
- Bloque en `sniffer/CMakeLists.txt` con `add_test`.

### Medido

- **RED:** `test_ip_format` falla **3 de 6** e imprime `0xC0A83801 esperado 192.168.56.1 obtenido
  1.56.168.192` — el bug de producción reproducido en **0,02 s**, sin VM de Suricata, sin pcap y
  sin kernel.
- **GREEN:** 6/6 con `htonl` dentro de la función.
- Línea base ANTES de tocar los llamantes: `ctest` 12/12. Después: 12/12 + `test_ring_consumer_protobuf` 4/4.
- `make sniffer -j4` limpio con `-Werror` (confirma que `src_addr`/`dst_addr` no se usaban en
  ningún otro sitio).
- Diff total: 4 ficheros, 94 inserciones, 10 borrados.
- 🟢 **En remoto:** `fix/sniffer-ip-byte-order` pusheada, tracking configurado.

### ⚠️ Lo que NO está demostrado

| afirmación | estado |
|---|---|
| la conversión IP es correcta | 🟢 `test_ip_format` |
| no hemos roto nada | 🟢 12/12 + 4/4 |
| **el bronce sale con IPs reales** | ⚪️ **SIN VERIFICAR** |
| aRGus y Suricata convergen al mismo `NetworkFlow` | ⚪️ sin verificar |

`test_ring_consumer_protobuf` pasa, pero ejercita la extracción de **features** (40 ML + 102
base): no imprime ni asserta `source_ip`. Es no-regresión, **no** verificación. Y `ctest` no
cubre `ring_consumer` en absoluto.

### El hallazgo que puede ser la mejor página del paper (HIPÓTESIS, sin medir)

`crosscheck-run` (Makefile ~2932):

```
if [ $$rc -eq 2 ]; then echo "   [i] exit 2 = hay anomalias (esperado por cobertura asimetrica aRGus)..."
```

El verificador de paridad `tools/community_id_crosscheck.py` **existía desde DAY 171/172**,
comparaba aRGus contra Zeek y Suricata — el oráculo externo exacto que hacía falta — y su código
de salida 2 estaba preetiquetado como ruido esperado. **Si las anomalías eran el byte order, la
puerta disparó durante cinco meses y nadie la miró.** Confirmar o descartar leyendo
`anomalies.tsv` y el script.

---

## Plan DAY 230 — opciones

**Recomendación de Claude: la 1 antes que la 2.** Leer es más barato que ejecutar, y lo que diga
`anomalies.tsv` puede cambiar qué tiene que demostrar el E2E.

**Opción 1 — Confirmar o descartar la hipótesis del `exit 2`.** Puro trabajo de lectura, sin VMs
ni builds: `tools/community_id_crosscheck.py` (¿qué compara, contra qué oráculo, qué cuenta como
anomalía?) y el `anomalies.tsv` que haya en el repo o en `logs/lab/`. Alto valor para el paper,
coste casi nulo. Si se confirma, hay que escribir la sección.

**Opción 2 — E2E barato del bronce (cierra la deuda de verdad).** No necesita `zeek` ni
`suricata`: replayar el Neris con `test-replay-neris` y comprobar que el bronce de
`/vagrant/logs/correlation/argus` trae `147.32.84.x` donde antes traía `165.84.32.147`. Las IPs
del pcap son verdad de campo externa y conocida.
⚠️ `pipeline-start` arrastra `test-provision-1`, que es un CI gate de OCHO checks (claves, firmas
de plugins, configs de producción). No es una operación de diez minutos.
⚠️ Verificar que el proceso que corre es el binario recién compilado (lección DAY 225): el sujeto
es el proceso, no el fichero.

**Opción 3 — Registrar el lote de deudas de DAY 229 en `docs/BACKLOG.md`** (lista abajo). Trabajo
de escritura, cierra la sesión limpia.

**Opción 4 — EMECAS+++ y PR de `fix/sniffer-ip-byte-order`.** Decisión de orden, no técnica:
o se paga antes `DEBT-VM-SENSOR-NO-TOOLCHAIN-001`, o se asume reinstalar el toolchain de
`suricata` a mano por tercera vez.

**Opción 5 — Volver a `feat/suricata-to-graph`** y llevarla a main (arrastrado desde DAY 223).

---

## Aparcado (no olvidar)

### Nuevo de DAY 229 — registrar en `docs/BACKLOG.md`
- **`DEBT-EVENT-STRUCT-DUPLICADA-001`** (nueva): la struct del evento del ring buffer está
  declarada DOS veces — `sniffer.bpf.c:87` (`__u32 src_ip`) y `sniffer/include/main.h:22`
  (`uint32_t src_ip`, incluida vía `ring_consumer.hpp:5`). Ninguno de los 18 includes de
  `ring_consumer.cpp` es cabecera compartida con el kernel. El ring buffer transporta bytes
  crudos: un desajuste de orden de campos o padding **no daría error de compilación**, daría
  corrupción silenciosa. Es el patrón eBPF habitual, pero sin gate. **PENDIENTE:** comparar las
  dos structs campo a campo (`sniffer.bpf.c` ~75-110 vs `main.h` ~10-45).
- **No existe target `sniffer-test`** en el Makefile, mientras `correlation-engine-test` sí
  existe y escala fallos. El sniffer tiene 12 tests en ctest y ningún target propio. Va con la
  Opción 4 de automatización de DAY 228.
- **`Makefile:1197`** confirmado: el `||` de `DEBT-MAKEFILE-TEST-GATE-MASKED-001` sigue ahí. La
  invocación SIN máscara de la 2150 pertenece a `tsan-quick` (perfil TSAN, otro build dir): no es
  un gate honesto escondido.
- **`test_payload_analyzer` y `test_proto3_embedded_serialization`**: sin `add_test` y sin
  invocación conocida en el Makefile. (Los otros tres que parecían huérfanos —
  `test_sharded_flow_full_contract`, `test_ring_consumer_protobuf`,
  `test_sharded_flow_multithread` — sí se ejecutan, desde `Makefile:2275-2277`.)
- **`commit-message.txt` está trackeado** y bloquea `git checkout` con cualquier borrador a
  medias. `git rm --cached` + línea en `.gitignore`. Va con las dos líneas corruptas del
  `.gitignore` de DAY 227.
- **Dos ficheros de respaldo trackeados**: `sniffer/src/kernel/sniffer.bpf.c.backup` y
  `sniffer/src/userspace/ml_defender_features.cpp.bak.day79`. Familia "dos caminos que discrepan";
  sin medir si difieren del fuente vivo.
- **`build-prod` y `build-production`** conviven como dos directorios de perfil. Sin medir.
- **Para el paper:** el bronce histórico de aRGus (`logs/correlation/argus-*.csv` anteriores a
  hoy) lleva IPs invertidas y `community_id` calculados sobre ellas. No es comparable con nada
  producido después del arreglo. Declararlo como procedencia.

### Arrastrado de DAY 228
- **`DEBT-GRAPH-ALERT-ROUTING-MONOSENSOR-001`**: `is_alert(r) { return r.final_classification ==
  "MALICIOUS"; }` (`cypher_builder.hpp:40`) — ningún sensor externo puede producir un `Alert`.
  Decisión DAY 228: Opción A (aceptar `TelemetryEvent`), **afinar con datos de MITRE**.
- **`DEBT-NODE-ID-VERSION-LABEL-001`**: `node_id = cpp_sniffer_v33_day12` es una etiqueta de
  VERSIÓN del sniffer; el adapter de Suricata la hardcodea para converger. D2 se cumple por
  imitación, no por diseño.
- `kuzu_query` no está en el Makefile · el loader no captura la excepción al abrir Kuzu · el
  loader accede a las columnas por índice posicional sin validar el esquema.
- El escáner de secretos del pre-commit avisa `Warning: Unrecognized key in config: paths_ignore`
  — una clave que la herramienta ignora en silencio. Familia DAY 224.
- **Opción 5 de DAY 228 (el premio del 98,7%)**: primer paso barato y sin escribir mapeo — medir
  cuántos eventos de cada tipo llevan `community_id` (requisito duro de `validate()`).
  `tools/eval/eve_field_coverage.py` puede que ya lo conteste.

### Arrastrado de DAY 227 y anteriores
- Discrepancia etcd-vs-env de la clave HMAC · medir si `SecretsManager` persiste la clave ·
  `git ls-files | grep -i -e '\.onnx$' -e '\.npz$'`.
- **`DEBT-VM-SENSOR-NO-TOOLCHAIN-001`** — bloque `ADAPTER_TOOLCHAIN` en el Vagrantfile raíz.
- **Telemetría (D4)**: el adapter descarta 104.392 eventos de dns/http/tls/… (98,7% del volumen).
- **Decisión no ratificada**: preimagen del `event_id` (D3) con separador `\x1f` vs length-prefix
  canónico de `flow_uid.hpp`.
- Sección de rangos de timestamp en `tools/eval/eve_field_coverage.py` · retoques de la puerta de
  diseño (16,7% es propiedad de la captura; FTP fija el puerto; smallFlows es de 2011-01-25) ·
  `evidencia/README.md` con procedencia · el provisioning de Suricata no reinicia el servicio tras
  tocar el YAML.
- Rama `fix/test-gate-masked` · nota recíproca en `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001`
  (BACKLOG:5138) · **Pieza `flow_uid` → rama aparte** (`fix/flow-uid-time-free` desde main).
- Guard D-D diferido: cuando se active, `"suricata"` debe ser símbolo `DetectorSource` legal.

---

## Punteros
- `sniffer/include/ip_format.hpp` — 🆕 punto único de conversión IP → texto
- `sniffer/tests/test_ip_format.cpp` — 🆕 el oráculo externo
- `sniffer/src/kernel/sniffer.bpf.c:232` — donde se ensambla la IP (orden de host)
- `sniffer/src/userspace/ring_consumer.cpp:843` y `:1231` — los dos llamantes, ya unificados
- `sniffer/include/main.h:22` — la SEGUNDA declaración de la struct del evento
- `tools/community_id_crosscheck.py` — el verificador de paridad (hipótesis del `exit 2`)
- `suricata-adapter/src/to_row.cpp` — el mapeo del adapter
- `correlation-engine/tools/{bronze_to_gold_converter,parquet_to_kuzu_loader,kuzu_query}.cpp`
- `correlation-engine/include/correlation_engine/cypher_builder.hpp` — `is_alert` (línea 40)
- `correlation-engine/tests/test_flujo_b_end_to_end.cpp` — el molde
- `libs/correlation-v1/{include,src}` — contrato, `validate` es notario único
- `ml-detector/src/correlation_writer.cpp:73-100` — el ORÁCULO (`to_correlation_v1_row`)

## Comandos útiles
```
# Build incremental de un target del sniffer (PROFILE ?= debug → build-debug)
vagrant ssh -c "cd /vagrant/sniffer/build-debug && cmake .. > /dev/null && make <target> -j4"

# Suite del sniffer SIN pasar por el target enmascarado del Makefile
vagrant ssh -c "cd /vagrant/sniffer/build-debug && ctest --output-on-failure"

# El test que ejercita ring_consumer NO está en ctest — se lanza a mano
vagrant ssh -c "cd /vagrant/sniffer/build-debug && ./test_ring_consumer_protobuf"

git grep -n '<patrón>' -- <ruta>/         # NUNCA grep -rn desde la raíz
vagrant ssh suricata -c "<comando>"       # la máquina va ANTES del -c
vagrant ssh -c "<comando>"                # a secas va a defender

# Grafo de DAY 228 (rama feat/suricata-to-graph)
vagrant ssh -c "cd /vagrant && ./correlation-engine/build/kuzu_query logs/day228-kuzu/suricata.kuzu 'MATCH (f:NetworkFlow) RETURN count(*)'"
```

## Ritmo

DAY 229 fue una sesión de lectura con veinte líneas de código al final. El arreglo era una
palabra; lo que costó fue **saber que era la palabra correcta** y **construir un criterio que
pudiera ponerse rojo**. El criterio que llevaba escrito en la deuda desde DAY 227 no podía.

Marcador de predicciones DAY 229: **10 acertadas, 1 refutada** (dije "fallan 4 de 6" y fallan 3:
solo tres de los seis casos son no-capicúa), **1 sospecha refutada** (el filtro de puertos de los
mapas eBPF estaba bien; ni un `htons` fuera de sitio).

Lo que de verdad se llevó el día: el bug lo cazó **la comparación**, no la inspección. Un sensor
único es autoconsistente por construcción — su hash y sus IPs beben de la misma fuente corrupta,
así que ninguna verificación interna puede delatarlo. Hizo falta integrar Suricata para que la
discrepancia existiera. Eso, que hace tres días parecía fontanería de integración, es la
evidencia empírica de la tesis del paper.

*Via Appia Quality — antes de aceptar un criterio, comprobar que puede ponerse rojo.*