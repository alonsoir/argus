# Puerta de diseño — Integración multi-sensor en el grafo

**Estado:** propuesta, pendiente de ratificación
**Fecha:** DAY 225 (2026-07-20)
**Rama:** `feat/suricata-to-graph` (desde `main` fb08e8f6)
**Destino sugerido en el repo:** `docs/design/multisensor-graph-identity/puerta-diseno-multisensor.md`
**Deudas afectadas:** `DEBT-GRAPH-SCHEMA-MULTISENSOR-001`, `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001`, `DEBT-FLOWUID-SEQ-COLLISION-001`, `DEBT-FLOWUID-CANONICAL-ENCODING-001`, `DEBT-NODEID-CRYPTO-IDENTITY-001`, `DEBT-BRONZE-HMAC-KEY-POLICY-001`, `DEBT-HOST-DOMAIN-CONTRACT-001`
**ADRs que requieren enmienda:** ADR-052 (Multi-node Flow Identity), ADR-058 (Circuito completo aguas abajo)

> **Convención de este documento.** Cada afirmación lleva marca de origen:
> **[MEDIDO]** = verificado contra fichero en DAY 224–225, con el comando que lo reproduce.
> **[DECISIÓN]** = elección de diseño, no un hecho.
> **[PENDIENTE]** = no medido todavía; **no implementar nada que dependa de esto sin medirlo antes**.
> Ninguna cifra de este documento procede de memoria ni de otro documento: todas se
> remidieron contra el código o contra la captura.

---

## 0. Resumen ejecutivo

La integración de Suricata (y después Zeek) en el grafo estaba bloqueada por una afirmación
que nunca se midió: que `flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)` hacía
converger dos sensores sobre el mismo nodo `NetworkFlow`.

**Es falsa.** `window_micros()` no ventanea — convierte a microsegundos sin agrupar. La
convergencia exigiría que dos motores fechasen el inicio del mismo flujo con exactitud de
microsegundo, lo cual no ocurre ni con relojes perfectamente sincronizados, porque "inicio de
flujo" es una decisión semántica de cada motor, no una lectura de reloj.

**Decisión central: la identidad de flujo deja de depender del tiempo.**

| ID | Decisión | Sección |
|----|----------|---------|
| D1 | `flow_uid = hash(node_id ‖ community_id)`, tag `argus-flowuid-v2` | §3 |
| D2 | `node_id` identifica el **punto de observación**, no el host | §4 |
| D3 | `event_id` determinista y prefijado por sensor | §5 |
| D4 | La telemetría no materializa `flow_start`; cuelga de la conversación | §6 |
| D5 | Descarte explícito **con contador ruidoso** de eventos sin identidad de flujo | §7 |
| D6 | Los 5 campos de veredicto quedan vacíos para sensores externos, nunca con centinela | §8 |

**Tres objeciones podrían impedir el éxito** aunque las seis decisiones sean correctas. Están
en §9. Una de ellas (O1) es potencialmente fatal y **debe verificarse antes de escribir código**.

---

## 1. Evidencia medida

### 1.1 Suricata sí emite `community_id`

**[MEDIDO]** El campo nunca había aparecido en ningún log del proyecto. Causa raíz doble:

1. Los logs de `logs/experiment/` (barrido completo, 211.136 eventos, **0 ocurrencias**) salieron
   de las VMs de `experiments/suricata-comparative/`, cuyo provisioning es
   `sed -i 's/community-id: false/community-id: yes/' ... || sed -i ...`.
   `sed -i` devuelve 0 aunque no sustituya nada, así que el `||` de respaldo es código muerto.
2. En la VM `suricata` del Vagrantfile raíz, la config **sí** estaba puesta
   (`/etc/suricata/suricata.yaml:136-138`, `community-id: yes` + `community-id-seed: 0`),
   pero se escribió **45 s después** de arrancar el servicio:
   `ActiveEnterTimestamp` 05:12:07 UTC vs `mtime` del YAML 05:12:52 UTC.
   El proceso vivo llevaba la config vieja en memoria. El provisioning aplica el `sed`,
   verifica con `echo`, y **no reinicia el servicio**.

Tras `systemctl restart suricata` y replay offline:

```
suricata -r /vagrant/datasets/ctu13/smallFlows.pcap -l /var/log/suricata-replay-small -v
grep -c community_id /var/log/suricata-replay-small/eve.json   → 1983
```

**Lección de método (para el paper):** verificar el fichero de configuración no basta. Hay que
comparar el `mtime` de la config contra la hora de arranque del proceso. Misma familia que el
`sed` que no distingue "hizo" de "no hizo" y que el `||` enmascarador del Makefile: constructos
que parecen medir y no miden.

### 1.2 Paridad de `community_id` con aRGus

**[MEDIDO]** Diana E2E `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` (flujo Neris
`147.32.84.165:1027 → 74.125.232.195:80`): **aparece 2 veces** en el replay del Neris.
Seed 0 validado extremo a extremo contra el `community_id` nativo de aRGus.

### 1.3 Qué campos trae cada tipo de evento

**[MEDIDO]** Una pasada sobre `/var/log/suricata-replay-medium/eve.json` (replay del
`botnet-capture-20110810-neris.pcap`: 323.154 paquetes, 53 MB, 8,4 s, 2.872 alertas,
0 líneas ilegibles):

| event_type | total | con `community_id` | con `flow.start` | con `flow_id` |
|-----------|------:|------------------:|-----------------:|--------------:|
| dns       | 84.570 | 84.570 | 0 | 84.570 |
| flow      | 17.346 | 17.346 | 17.346 | 17.346 |
| **alert** | **2.872** | **2.870** | **2.870** | **2.870** |
| http      | 1.405 | 1.405 | 0 | 1.405 |
| fileinfo  | 630 | 630 | 0 | 630 |
| anomaly   | 220 | 220 | 0 | 220 |
| smtp      | 114 | 114 | 0 | 114 |
| tls       | 52 | 52 | 0 | 52 |
| smb       | 36 | 36 | 0 | 36 |
| snmp      | 16 | 16 | 0 | 16 |
| **stats** | **2** | **0** | **0** | **0** |
| sip       | 1 | 1 | 0 | 1 |

Tres consecuencias inmediatas:

- **Las alertas traen `flow.start`** (2.870 de 2.872). El adapter de `Alert` es un **traductor
  línea a línea**, sin estado, sin tabla de correlación, sin ventana ni desalojo. Queda
  descartada la hipótesis cara de DAY 224 (que haría falta correlacionar dos eventos).
- **La telemetría no lo trae**, en los nueve tipos. Sí trae `community_id` y `flow_id`.
- **`stats` no tiene identidad de red** y debe descartarse explícitamente.

**[MEDIDO]** Las 2 alertas sin `community_id`/`flow.start`/`flow_id` son ambas la misma firma:
gid 1, sid 2200076 rev 2, *"SURICATA ICMPv4 invalid checksum"*, categoría *Generic Protocol
Command Decode*, ICMP type 3 code 0. Son alertas de **decoder** sobre paquetes a los que nunca
se les creó flujo. Correlacionan con el aviso del propio motor (68/1000 checksums inválidos):
artefacto de la captura de 2011, no ataque.

### 1.4 La identidad de flujo actual no puede converger

**[MEDIDO]** `correlation-engine/include/correlation_engine/flow_uid.hpp`, fichero completo:

```cpp
inline uint64_t window_micros(int64_t seconds, int32_t nanos = 0) {
    return static_cast<uint64_t>(seconds) * 1'000'000ULL + static_cast<uint64_t>(nanos) / 1'000ULL;
}
```

**No hay bucketing.** Ni módulo, ni truncado, ni tamaño de ventana. `flow_start_window` es un
nombre equivocado: no existe ninguna ventana. Los vectores congelados
(1717480800000000, 1717480830000000) parecen redondos únicamente porque los tests usan
`nanos = 0` y segundos redondos; `test_flujo_a_b_equivalence.cpp:231` llama con
`window_micros(1717480800, 123456000)` = 1717480800123456.

**[MEDIDO]** La fórmula tiene **cuatro** entradas, no tres:
`encode_flow_input(node_id, community_id, flow_start_window, seq_in_window = 0)` incluye
`put_be32(buf, seq_in_window)`. La cabecera del propio fichero lo documenta correctamente
(`ENCODE(node_id, community_id, window, seq)`); ADR-058, el BACKLOG y los prompts de
continuidad llevan meses repitiendo la versión de tres. **Segundo número que viajó de documento
a documento sin compararse con el código** (el primero fue el "24 campos" de DAY 224).

**[MEDIDO]** `seq_in_window` es **siempre 0** en producción: `main.cpp:138` y
`segment_processor.cpp:26` llaman con tres argumentos (default 0);
`bronze_to_gold_converter.cpp:171` lo fija explícitamente citando
`DEBT-FLOWUID-SEQ-COLLISION-001`; `parquet_to_kuzu_loader.cpp:45` lo confirma. La equivalencia
Flujo A vs Flujo B es real, no casual.

**Lectura de diseño:** bucketing y `seq_in_window` son las dos mitades de la misma idea — la
ventana agrupa, `seq` desempata los flujos distintos que caen en la misma ventana. **Ninguna de
las dos se implementó.** No es un olvido aislado: es media pieza de diseño que se quedó fuera
entera, y por eso el desempate nunca hizo falta.

### 1.5 Por qué la sincronía de relojes no resolvería nada

**[DECISIÓN — argumento, no medida]** Aunque se desplegara PTP y todos los relojes coincidieran
al nanosegundo, `flow.start` de Suricata y `flow_start` de aRGus seguirían discrepando: cada
motor decide cuándo "empieza" un flujo con su propio criterio (primer paquete asociado a la
entrada de su tabla de flujos, SYN, primer paquete visto). La sincronía resuelve la deriva de
reloj; no resuelve la **divergencia de definición**. Esto convierte la identidad sin tiempo de
compromiso pragmático en requisito estructural.

### 1.6 Coste medido de quitar el tiempo de la identidad

**[MEDIDO]** Sobre los 17.346 eventos `flow` del replay del Neris:

| proto | eventos | `community_id` distintos | colapso | % |
|-------|--------:|-------------------------:|--------:|--:|
| TCP   | 12.305 | 11.686 | 619 | 5,0 % |
| UDP   | 5.039 | 2.758 | 2.281 | 45,3 % |
| ICMP  | 2 | 2 | 0 | 0 % |
| **total** | **17.346** | **14.446** | **2.900** | **16,7 %** |

**[MEDIDO]** Naturaleza del colapso UDP: los repetidos son NetBIOS (`sport = dport = 137` y
`138`, con 27 y 40 repeticiones) y DNS con puerto de origen reutilizado (`dport = 53`,
`sport` 1291 y 2079). Los arranques están separados por **minutos** (2, 3, 13, 37), no por el
timeout UDP de 30–60 s. **No son fragmentos de un mismo intercambio**: son intercambios
distintos que comparten 5-tupla. El colapso es real.

Dos hipótesis se plantearon y **ambas quedaron refutadas contra el fichero**: que el grueso del
colapso fuera ICMP (es 0) y que fuera fragmentación por timeout (los intervalos son de minutos).
Se dejan escritas porque el paper documenta el método, no solo el resultado.

---

## 2. La conclusión que cierra el debate

Los intercambios que colapsan están separados por minutos y a menudo caen dentro de la misma
hora (09:04:32 / 09:06:49 / 09:09:24 / 09:11:23 para un mismo `community_id`).

- **Separarlos** exige una ventana **sub-minuto**.
- **Hacer converger dos sensores** exige una ventana **mucho mayor** que el delta entre ellos.

Son requisitos incompatibles sobre el mismo parámetro. **No existe ningún valor de tamaño de
ventana que satisfaga los dos.** Por tanto:

- La opción "implementar el bucketing de verdad" queda **descartada por datos**.
- La opción "época gruesa (hora/día) como tercera entrada" queda **descartada por datos**.
- La identidad sin tiempo no es la alternativa pragmática: **es la única consistente con lo
  medido**.

---

## 3. D1 — Identidad de flujo sin componente temporal

**Decisión.** `flow_uid = base64_std(BLAKE2b-256(ENCODE(node_id, community_id)))`, con tag de
esquema `argus-flowuid-v2`. `flow_start` deja de ser identidad y pasa a ser **propiedad** del
nodo.

**A favor**

- Convergencia multi-sensor **garantizada**, con probabilidad de fallo silencioso **cero**.
  Cualquier esquema con ventana tiene probabilidad ≈ δ/N de partir un flujo: pequeña, nunca
  nula, y **silenciosa** — la familia de fallo que más ha costado en este proyecto (el `sed`
  que no falla, el `||` del Makefile, la config no releída).
- Es el cambio más pequeño posible: `compute_flow_uid` pierde dos parámetros y el tag sube de
  versión. El `MERGE` con `ON CREATE SET` / `ON MATCH SET` ya existe: el primer sensor que
  llega fija `flow_start`, el segundo se acopla sin machacarlo.
- Coherente con lo que el propio `schema.cypher` declara que es `NetworkFlow`: **identidad pura**.
- Cierra `DEBT-FLOWUID-SEQ-COLLISION-001` por desaparición del objeto: `seq` sale de la
  codificación.
- El tag de versión `argus-flowuid-vN` existe precisamente para esto. Usarlo es lo que estaba
  previsto, no un parche.

**En contra**

- **Colapso medido del 16,7 %** de los flujos de la captura (5 % TCP, 45 % UDP). Intercambios
  distintos que comparten 5-tupla pasan a un único nodo.
- El grafo **no puede distinguir** a cuál de las 40 reutilizaciones pertenece una alerta sin
  bajar al ledger.
- Un despliegue de larga duración acumula nodos "conversación" que nunca se cierran.
- Se pierde la posibilidad de consultas del tipo "flujos iniciados en la ventana X" resueltas
  por identidad; hay que resolverlas por propiedad, que es más caro en Kuzu.

**Reencuadre que hace asumible el coste.** Con D1 el nodo deja de ser una *instancia* de flujo y
pasa a ser la **conversación** (identidad del 5-tupla). No se pierde información: el oro Parquet
es **ledger append-only** y conserva cada fila con su `flow_start` intacto; cada `Alert` y cada
`TelemetryEvent` mantiene su propio timestamp como propiedad y cuelga de la conversación. El
grafo es **proyección reconstruible** (invariante Via Appia): agrega, no destruye. Para los
protocolos de puerto fijo (NetBIOS 137/138, donde `sport = dport` siempre y todo intercambio
entre el mismo par de hosts comparte 5-tupla para siempre), un nodo por conversación es
probablemente **mejor** representación de grafo que 40 nodos casi idénticos.

**Limitación conocida a documentar en el README y en el paper.** El grafo modela conversaciones,
no instancias de flujo. La granularidad de instancia vive en el ledger.

---

## 4. D2 — `node_id` identifica el punto de observación

**Decisión.** `node_id` identifica el **segmento de red observado**, no la máquina que ejecuta
el sensor. Quien distingue al sensor es `source_sensor` (col 1 del contrato), que ya viaja
íntegro por todo el circuito y desde DAY 222 llega al grafo.

**Motivo.** `node_id` entra en el hash del `flow_uid`. aRGus corre en la VM `defender` y
Suricata en la VM `suricata`. Si cada adapter acuña su `node_id` a partir del host, el
`flow_uid` diverge aunque `community_id` coincida — y D1 no habría servido de nada. Este es un
**tercer eje de divergencia** independiente del tiempo, y es tan fatal como el primero.

**A favor.** Hace explícito lo que ya era cierto: dos sensores que vigilan el mismo cable son el
mismo punto de observación. `source_sensor` ya existe exactamente para separar quién habla.

**En contra.** Obliga a una convención de nombrado de puntos de observación que hoy no existe, y
a que la configuración de cada adapter la respete. Un error de configuración aquí produce
divergencia silenciosa — el mismo modo de fallo que estamos eliminando en D1, desplazado a la
config. **Mitigación obligatoria:** el `node_id` debe declararse en un único sitio por punto de
observación y verificarse ruidosamente al arrancar cada productor.

---

## 5. D3 — Acuñación de `event_id`

**[MEDIDO]** `event_id` es `STRING` libre y es PK de `Alert` (`schema.cypher:48`) **y** de
`TelemetryEvent` (`:69`) — dos tablas, dos espacios de nombres, sin colisión entre sí. El
contrato solo restringe formato (rechaza `\r` embebido). `evt-0001` en los tests es placeholder,
no convención. En aRGus el valor procede del protobuf: `event.event_id()`
(`ml-detector/src/correlation_writer.cpp:86`).

**Riesgo.** Nada impide que el `event_id` de Suricata colisione con el de aRGus dentro de
`Alert`. El grafo escribe con `MERGE`: no fallaría, **machacaría** el evento del otro sensor sin
error y sin traza.

**Decisión.** El `event_id` de todo sensor externo se acuña con dos propiedades:

1. **Prefijado por `source_sensor`**, derivado de la misma constante que ya prefija el basename
   del bronce (punto único con la col 1). Elimina la colisión entre espacios de sensores.
2. **Determinista**: reprocesar el mismo `eve.json` debe producir el mismo `event_id`, o cada
   replay duplica nodos en vez de converger. Recomendación: hash del contenido identificador del
   evento (`timestamp` + `flow_id` + `signature_id` + `community_id`), no un contador.

**Aviso.** **No usar `pcap_cnt` como semilla.** Existe en replay offline; en captura viva no está
garantizado, y un `event_id` que cambia de forma según el modo de captura es una bomba de
relojería.

---

## 6. D4 — Telemetría sin `flow.start`

**Decisión.** Los nueve tipos de telemetría (`dns`, `http`, `fileinfo`, `anomaly`, `smtp`,
`tls`, `smb`, `snmp`, `sip`) **no materializan** `flow_start`. Cuelgan de la conversación por
`community_id` y conservan su propio `timestamp` como propiedad del `TelemetryEvent`.

**A favor.** Con D1 el `flow_uid` ya no necesita `flow_start`, así que la ausencia deja de ser un
problema. Evita el correlacionador con estado (tabla `flow_id` → `start`, ventana, desalojo) que
habría hecho falta para el 98,5 % del volumen. Es la decisión que D1 abarata.

**En contra.** El `TelemetryEvent` no puede responder "¿cuándo empezó el flujo al que pertenece
este DNS?" sin saltar al nodo de conversación. Aceptable: es un salto de una arista.

**Alternativa descartada.** Correlacionar por `flow_id` contra los 17.346 eventos `flow`. Es
posible (`flow_id` está en el 100 % de la telemetría) pero exige estado, ventana y política de
desalojo, y solo aportaría un campo que ya no participa en la identidad.

---

## 7. D5 — Política de descarte con contador ruidoso

**Decisión.** El adapter descarta, sin escribir al bronce:

- eventos `stats` (sin `community_id` ni `flow_id`: no son eventos de red);
- alertas de decoder sin flujo asociado (las 2 de *ICMPv4 invalid checksum*).

**Y lleva un contador por categoría, expuesto en el log de arranque y de cierre.**

**Motivo.** Sin `community_id` no hay identidad de flujo y no hay a qué colgar el evento en el
grafo. La alternativa (centinela) contaminaría el grafo con una clave que Suricata nunca emitió.
Pero el descarte **silencioso** es exactamente la familia de fallo que este proyecto lleva
semanas persiguiendo: un `2 eventos descartados (sin community_id)` al final de la corrida es
barato y hace que el número exista.

---

## 8. D6 — Los cinco campos de veredicto sin contrapartida

**[MEDIDO]** De los 19 campos del bronce, cinco no tienen origen posible en Suricata:
`final_classification`, `threat_category`, `fast_detector_score`, `ml_detector_score`,
`overall_threat_score`. Suricata emite `signature`, `category` y `severity` (1–3), no scores.

**Decisión.** Se emiten **vacíos**, nunca con centinela numérico (`0.0`, `-1`) ni con
clasificación inventada. Rellenarlos contaminaría el grafo con un veredicto que Suricata nunca
emitió, y cualquier consulta que agregue scores mezclaría semánticas incompatibles sin avisar.
`source_sensor` (ya en el grafo desde DAY 222) es lo que permite al consumidor filtrar.

`authoritative_source` **sí** tiene sentido y lo fija el adapter, no el sensor.

**Consecuencia para el consumidor del grafo.** Los campos de veredicto solo son interpretables
para `source_sensor = "argus"`. Debe estar escrito en el README y en el paper. Nota de contexto:
tras la decisión de DAY 221 (aRGus desactivado como clasificador), esos campos tienen valor
histórico más que operativo.

**[PENDIENTE — bloqueante menor]** Verificar que el validador del contrato
(`libs/correlation-v1/`) **acepta** esos cinco campos vacíos. Si `validate()` los exige no
vacíos, ninguna fila de Suricata pasaría el contrato y habría que decidir entre relajar el
validador o partir el contrato. Medir con:
`git grep -n 'validate' -- libs/correlation-v1/src/`

---

## 9. Objeciones que podrían impedir el éxito

### O1 — ¿Observan los dos sensores el mismo tráfico? **(potencialmente fatal)**

**[PENDIENTE — medir antes de escribir una línea del adapter]**

Toda la convergencia descansa en que aRGus y Suricata vean **los mismos paquetes**. En la
topología actual del Vagrantfile raíz, aRGus corre en `defender` y Suricata en su propia VM.
Si cada una esnifa su propia interfaz sin mirror/SPAN ni red interna en modo promiscuo, **jamás
verán los mismos flujos**, y entonces ningún diseño de identidad — ni D1, ni ventanas, ni
sincronía — produce convergencia alguna. El grafo tendría dos subgrafos disjuntos.

Ninguna de las decisiones de este documento resuelve O1. Es un problema de **topología de
laboratorio**, no de identidad.

Verificar: configuración de red de las cinco VMs en el Vagrantfile raíz (¿red interna
compartida? ¿`virtualbox__intnet`? ¿promiscuous mode `allow-all`?) y, en su defecto, si la vía
practicable es que **ambos sensores procesen el mismo pcap en modo offline** — que es
exactamente lo que ya se ha hecho hoy con Suricata y lo que `sniffer-libpcap` (Variante B)
permite hacer con aRGus.

**Recomendación:** adoptar el replay offline del mismo pcap como **banco de pruebas oficial de
convergencia**. Es determinista, reproducible desde el Makefile (requisito de cierre del paper),
elimina el techo de ~33–38 Mbps de la NIC de VirtualBox y los artefactos multicast que
introdujeron los 2 FP del CTU-13. El tráfico en vivo se deja como validación posterior con el
script MITRE, no como base de la medición.

### O2 — Wazuh no puede converger por identidad de flujo **(limitación estructural)**

**[MEDIDO]** Ya existe `DEBT-HOST-DOMAIN-CONTRACT-001`: Wazuh es **dominio host**, con contrato
propio `host_domain_v1`, separado de `correlation_v1`. El contrato nunca fue universal para los
cuatro sensores.

Wazuh no emite `community_id` ni observa flujos: emite eventos de host. **El requisito
"correlación entre todos los engines" no es alcanzable vía `flow_uid` para Wazuh.** Tres de los
cuatro componentes (aRGus, Suricata, Zeek) convergen por identidad de flujo; Wazuh se une al
grafo por otra clave — host/IP y proximidad temporal — mediante una arista distinta y con una
semántica de correlación explícitamente más débil.

Esto **no bloquea** la integración de Suricata y Zeek, pero debe estar escrito antes de que el
paper afirme "grafo unificado de los cuatro componentes". Es una afirmación que hoy sería falsa
en el sentido en que se leería.

### O3 — Cadena de custodia del HMAC multi-productor **(decisión pendiente, no bloqueante hoy)**

**[MEDIDO]** `DEBT-BRONZE-HMAC-KEY-POLICY-001` ya cubre esto ("la col 18 (HMAC) no es 'mismos
bytes' entre productores"), junto con `DEBT-SECRETS-MANAGER-PERSISTENCE-001` (el
`SecretsManager` guarda claves solo en memoria).

Dos vías, ninguna gratis:

- **Cada adapter firma** → hay que distribuir la clave a N productores; el bronce sigue siendo
  "lo que emanó el sensor", pero la superficie de la clave se multiplica.
- **Un colector único firma al aterrizar** → una sola clave, pero el bronce deja de ser lo que
  emanó el sensor y la cadena de custodia se rompe conceptualmente.

**Recomendación para el cierre:** vía del colector único, documentada como tal, dado que el
`SecretsManager` no persiste claves y el proyecto entra en modo lectura el 31-ago. Es la que
menos superficie nueva abre. **Es una decisión de custodia, no de código.**

### O4 — `parquet_to_kuzu_loader` declara alcance mono-fuente

**[MEDIDO]** El loader declara alcance v1 `source_sensor = "argus"` y advierte explícitamente de
no generalizar sin pasar antes por `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001`. Este documento es
esa puerta. Al ratificarse, hay que **actualizar el comentario del loader**, no ignorarlo: un
aviso que se queda escrito después de dejar de ser cierto es otra afirmación que viaja sin
medirse.

### O5 — La base Kuzu persistida queda obsoleta

**[MEDIDO]** `CREATE NODE TABLE IF NOT EXISTS` **no migra** catálogos Kuzu existentes. Al
cambiar la codificación del `flow_uid` (v1 → v2), **todos** los `flow_uid` cambian: cualquier BD
persistida anterior queda inconsistente. Los tests y EMECAS+++ no lo detectan porque parten de
base fresca / VM destruida.

**Recomendación:** recreación explícita, documentada en el Makefile, y una nota en el README.
No intentar migración: el proyecto cierra en seis semanas y una migración de catálogo es
superficie nueva sin retorno.

---

## 10. Pendientes de medir antes de implementar

| # | Qué | Comando | Bloquea |
|---|-----|---------|---------|
| P1 | ¿Ven los dos sensores el mismo tráfico? (O1) | inspección de red en el Vagrantfile raíz | **Todo** |
| P2 | ¿`validate()` acepta los 5 campos de veredicto vacíos? | `git grep -n 'validate' -- libs/correlation-v1/src/` | D6 |
| P3 | ¿El `ON MATCH SET` machaca `flow_start`? | `cypher_builder.hpp:103,112` | D1 |
| P4 | Delta real Suricata↔aRGus sobre el mismo pcap | `sniffer-libpcap` + cruce por `community_id` | Nada — es figura del paper |

P3 merece detalle: con D1, si el `ON MATCH SET` incluye `flow_start_window`, el segundo sensor
en llegar **sobrescribiría** la marca temporal del primero. Debe estar solo en `ON CREATE SET`.
Ambos bloques Cypher (líneas 103 y 112) hay que leerlos enteros — no un `sed -n` — antes de
tocarlos.

P4 no bloquea, pero es una figura valiosa: *por qué la identidad de flujo compartida entre
sensores no puede depender del tiempo*, con la distribución real del delta. Es material de
publicación y respalda D1 empíricamente en vez de solo por argumento.

---

## 11. Plan de implementación por piezas

Estrictamente en este orden. Cada pieza con verificación ruidosa detrás.

1. **P1** (topología). Si sale rojo, todo lo demás se replantea sobre replay offline.
2. **`flow_uid.hpp`**: `encode_flow_input` y `compute_flow_uid` pierden `flow_start_window` y
   `seq_in_window`; tag `argus-flowuid-v1` → **`argus-flowuid-v2`**.
3. **Vectores congelados**: regenerar `tests/vectors/correlation_vectors.json` y
   `test_flow_uid.cpp` contra `hashlib.blake2b(digest_size=32)`, igual que se congelaron.
4. **Tres llamantes**: `main.cpp:138`, `segment_processor.cpp:26`,
   `bronze_to_gold_converter.cpp:174`.
5. **P3** y ajuste de `cypher_builder` si procede. `flow_start_window` sigue siendo propiedad;
   el esquema no se toca.
6. **Suite completa** del correlation-engine (9/9) sobre árbol limpio:
   `make correlation-engine-clean && make correlation-engine-test`.
7. **Adapter de Suricata**: traductor línea a línea para `alert`, ruta de telemetría, descarte
   contado. JSON propio con `base_dir` al buzón plano y `source_sensor = "suricata"`. **Nunca se
   toca la config interna de Suricata.**
8. **BACKLOG**: cerrar `DEBT-FLOWUID-SEQ-COLLISION-001`; enmendar ADR-052 y ADR-058; corregir la
   fórmula de tres entradas allí donde esté escrita; actualizar el comentario de alcance del
   loader; nota recíproca en `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001`.

El Parquet oro **conserva** `flow_start_window` (col 19) y `seq_in_window` (col 20): el ledger
preserva. Solo dejan de alimentar el hash.

---

## 12. Lo que este documento **no** resuelve

Dicho explícitamente para que nadie lo dé por cerrado:

- **O1 no está verificado.** Es la única objeción que puede invalidar la integración entera.
- **Wazuh no converge por flujo** (O2). Cualquier afirmación de "grafo unificado de los cuatro
  componentes" necesita matiz.
- **Zeek no se ha medido.** Se asume simetría con Suricata por emitir `community_id` con el
  mismo seed, pero **eso es una suposición, no una medida**. Zeek emite `conn.log` con otra
  estructura, y la lección de este mismo documento es que las suposiciones sobre formatos de
  sensor sobreviven meses sin que nadie las compruebe.
- **Las columnas 22 (`ingested_at`) y 23 (`temporal_anomaly`)** del diseño del Eslabón 1 siguen
  sin implementar, ni siquiera para aRGus (`DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001`). No
  bloquean la integración multi-sensor, pero el oro sigue teniendo 22 de las 24 columnas
  diseñadas.

---

*Via Appia Quality — medir quién habla, no solo qué dice. Y medir el número antes de escribirlo.*