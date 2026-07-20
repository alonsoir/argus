# PROMPT DE CONTINUIDAD — DAY 226 (continúa DAY 225)

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
- **Lección DAY 224 (el número que nadie midió):** el "24 campos" llevaba 17 días mintiendo.
  Antes de propagar una cifra al paper, medirla.
- **Lección DAY 224 (constructos que no distinguen "hizo" de "no hizo"):** `sed -i` devuelve 0
  aunque no sustituya nada → el fallback del `||` está muerto. Igual el `||` del Makefile.
- **🆕 Lección DAY 225 (la config que el proceso no ha leído):** verificar el FICHERO no basta.
  Suricata tenía `community-id: yes` en el YAML y emitía 0 `community_id` porque el servicio
  arrancó 45 s ANTES de que el provisioning escribiera la config. Comparar **mtime de la config
  contra la hora de arranque del proceso**. El sujeto de la verificación es el proceso, no el fichero.
- **🆕 Lección DAY 225 (nombres que mienten):** `flow_start_window` no ventanea, `emecas+++` es un
  alias de `emecas++`, y un "campo vacío" resultó no poder estar vacío (es `double`). Leer el
  cuerpo, no el nombre.
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

## Estado — rama `feat/suricata-to-graph` (HEAD 253a80fe, pusheada)

DAY 225 pasó `make emecas+++` en verde y commiteó la puerta de diseño + evidencia + script.
**El adapter de Suricata todavía no tiene ni una línea escrita.** Todo lo de ayer fue medición y
decisión, que era lo que faltaba.

**AVISO:** el EMECAS+++ destruyó la VM `suricata` (`vagrant destroy -f` ignora `autostart:false`;
`vagrant up` pelado solo levanta `defender`). Los logs están a salvo en `logs/day225-*` del host.
Al recrearla: `vagrant up suricata` **y después `systemctl restart suricata`** — el provisioning
escribe el YAML tras arrancar el servicio y sin reinicio vuelves a tener 0 `community_id`.

---

## Lo medido en DAY 225 (no repetir)

**Suricata emite `community_id`.** Diana E2E `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` presente 2 veces en
el replay del Neris → seed 0 validado contra el `community_id` nativo de aRGus.

**Cobertura por tipo de evento** (replay Neris, 107.264 eventos, 0 líneas ilegibles):
`alert` 2.872 con `community_id` en 2.870 **y `flow.start` en 2.870** → el adapter de Alert es un
**traductor línea a línea, sin estado**. La telemetría (dns 84.570, http, fileinfo, anomaly, smtp,
tls, smb, snmp, sip) trae `community_id` y `flow_id` pero **`flow.start` = 0 en los nueve tipos**.
`stats` (2) no trae nada. Las 2 alertas sin identidad son gid 1 sid 2200076 "SURICATA ICMPv4
invalid checksum" — decoder sobre paquetes sin flujo.

**La identidad de flujo actual NO puede converger.** `window_micros()` no ventanea: es
`seconds*1e6 + nanos/1e3`, sin bucketing. Convergir exigiría exactitud de **microsegundo**, y ni
con relojes perfectos: "inicio de flujo" es decisión semántica de cada motor. Además la fórmula
tiene **4 entradas** (incluye `seq_in_window`), no 3 como dicen ADR-058 y BACKLOG; `seq` es 0 en
los tres llamantes de producción.

**Coste medido de quitar el tiempo:** colapso TCP 619/12.305 (5%), UDP 2.281/5.039 (45%),
ICMP 0/2, total 2.900/17.346 (16,7%). Los repetidos son NetBIOS 137/138 (`sport=dport`), FTP con
puerto de origen fijo (2048/2049→21) y DNS. Separación de **minutos**, misma hora → **ninguna
ventana puede a la vez separarlos y hacer converger dos sensores**. Opciones A y C descartadas
POR DATOS. Y el colapso **depende de la captura**: smallFlows da 1,2%.

**Contrato:** `validate()` solo exige (1) `community_id` no vacío y (2) sin `\n`/`\r` en 11
campos de texto. Los campos de veredicto vacíos PASAN. `schema_version` = `"1"`,
`source_sensor` = `"argus"` (constantes), `node_id` = `event.originating_node_id()` ← viene de
`config_.node_id` del sniffer (`ring_consumer.cpp:860`) → **es configuración, D2 es implementable**.
`to_correlation_v1_row` devuelve `skip()` si `community_id` vacío: el adapter debe imitar esa forma.

---

## Decisiones ratificadas (documento commiteado)

`docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md`

- **D1** `flow_uid = hash(node_id ‖ community_id)`, tag `argus-flowuid-v2`. `flow_start` pasa a
  propiedad (`ON CREATE SET` ya existe). El nodo es la **conversación**, no la instancia.
- **D2** `node_id` = punto de observación, no host. `source_sensor` distingue al sensor.
  Si dos sensores escuchan interfaces distintas, **es correcto que generen grafos distintos**.
- **D3** `event_id` = `"suricata:" + base64(BLAKE2b-256(timestamp ‖ flow_id ‖ signature_id ‖
  community_id))`. Determinista. NO usar `pcap_cnt`.
- **D4** Telemetría sin `flow_start`; cuelga de la conversación por `community_id`.
- **D5** Descarte con contador ruidoso, implementado como `skip()` igual que el oráculo.
- **D6 (REESCRITA DAY 225):** los scores son `double` → "vacío" no existe. **Opción A**: quedan a
  `0.0` como ausencia documentada, el consumidor filtra por `source_sensor`. (C: NaN, descartada
  por riesgo de round-trip en CSV/Parquet/Kuzu). Los de texto SÍ se mapean:
  `final_classification` ← `alert.signature`, `threat_category` ← `alert.category`.
  **`alert.severity` se pierde**, documentado: rederivable desde la `signature`.
- `flow.start` viene ISO-8601 con offset (`2011-08-10T09:04:32.432327+0000`, micros):
  `flow_start_nano` = micros × 1000, respetando el offset **del evento**, no el de la VM.

---

## Plan DAY 226

1. **`head -1 logs/correlation/argus-2026-07-20-094233.csv`** — el pipeline de aRGus estuvo
   escribiendo bronce ayer (11:26-11:43). La **col 3** de esa línea es el `node_id` real que el
   adapter debe replicar. Y la línea entera es el formato exacto a imitar (entrecomillado,
   serialización de los `double`, HMAC col 18).
2. **Escribir el adapter**: `eve.json → CorrelationV1Row`, espejo de `to_correlation_v1_row`.
   C++ reutilizando `libs/correlation-v1` (serialize/HMAC/validate compartidos — nunca
   reimplementar el contrato). Modo **lote**, no `tail -f`. Escritura `.tmp`→rename, basename
   `suricata-%Y-%m-%d-%H%M%S.csv` desde su propia constante `CORRELATION_SOURCE_SENSOR`.
   JSON propio con `base_dir` al buzón plano `/vagrant/logs/correlation`.
3. **Criterio de éxito del día: UNA fila de Suricata en el bronce que pase `validate()`.**
   Ni Parquet, ni Kuzu, ni grafo.
4. Fuente de datos sin VM: `logs/day225-suricata-neris/eve.json` (55 MB, 2.872 alertas).

## Aparcado (no olvidar)
- Sección de rangos de timestamp en `tools/eval/eve_field_coverage.py`, para que
  `eve-coverage-stale-config.txt` demuestre por sí solo la transición 05:12 → 05:24.
- Retocar el documento: (a) el 16,7% es propiedad de la captura, no del diseño (rango 1,2–16,7%);
  (b) §1.6 dice "puerto efímero" y hay clientes FTP que FIJAN el puerto; (c) smallFlows es de
  2011-01-25, no de 2015; (d) **O3 miente**: dice "colector único firma" pero el adapter firmará
  con `ARGUS_BRONZE_HMAC_KEY_HEX` vía `serialize()`; (e) D5 queda reforzada por el contrato
  (`validate` rechaza `community_id` vacío, así que `stats` y decoder no podrían emitirse).
- `evidencia/README.md` con procedencia (pcap, Suricata 7.0.10, 52.003 firmas, comando `-r`).
- Deuda nueva: el provisioning de Suricata no reinicia el servicio tras tocar el YAML.
- PR de `feat/suricata-to-graph` · rama `fix/test-gate-masked` · nota recíproca en
  `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` (BACKLOG:5138).
- **Pieza `flow_uid` → rama aparte** (`fix/flow-uid-time-free` desde main): toca identidad del
  sistema entero. Vectores congelados a regenerar; BD Kuzu persistida queda obsoleta.
- P3 sin medir: ¿el `ON MATCH SET` machaca `flow_start`? (`cypher_builder.hpp:103,112`).
- Guard D-D diferido: cuando se active, `"suricata"` debe ser símbolo `DetectorSource` legal.
- Makefile multicomponente: **después** de que exista un segundo productor, no antes.

## Punteros
- `docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md` + `evidencia/`
- `libs/correlation-v1/{include,src}` — contrato, `validate` es notario único
- `ml-detector/src/correlation_writer.cpp:73-100` — el ORÁCULO (`to_correlation_v1_row`)
- `correlation-engine/include/correlation_engine/flow_uid.hpp` — identidad, tag de versión
- `tools/eval/eve_field_coverage.py` — reproduce todas las cifras del documento
- `DEBT-HOST-DOMAIN-CONTRACT-001` — Wazuh es dominio host (`host_domain_v1`), **no converge por
  `flow_uid`**. El paper no puede decir "grafo unificado de los cuatro" sin matiz.

## Comandos útiles
```
make correlation-engine-test              # HOST, rm -rf build + cmake + ctest
python3 tools/eval/eve_field_coverage.py <eve.json>
git grep -n '<patrón>' -- <ruta>/         # NUNCA grep -rn desde la raíz
vagrant up suricata && vagrant ssh suricata -c "sudo systemctl restart suricata"
```

## Ritmo
DAY 225 fue de medición pura y desmontó tres afirmaciones que llevaban meses circulando sin
comprobarse: que Suricata no emitía `community_id` (sí lo emite, el proceso no había releído la
config), que el `flow_uid` hacía converger dos sensores (no puede: exige microsegundo exacto), y
que la fórmula tenía tres entradas (tiene cuatro). Ninguna se descubrió leyendo documentación:
las tres salieron de abrir el fichero.

*Via Appia Quality — medir quién habla, no solo qué dice. Y medir el número antes de escribirlo.*