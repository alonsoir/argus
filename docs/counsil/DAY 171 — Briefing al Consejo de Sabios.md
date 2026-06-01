# DAY 171 — Briefing al Consejo de Sabios
## Cross-check operacional de community_id (paridad de los 3 sensores de red)

| Campo | Valor |
|---|---|
| **Fecha** | 2026-06-01 (DAY 171) |
| **Rama** | feature/day170-community-id-protobuf |
| **Tag estable** | v1.0.0-day166 |
| **Estado** | mitad-sniffer CERRADA con test; verificador validado en dry-run; replay en vivo PENDIENTE |
| **Relaciona** | ADR-046 v4 §3.10, AdapterSpec v1, ADR-051/052 (pendientes) |

---

## 1. Objetivo del dia

Cerrar la paridad **OPERACIONAL** del community_id (la de especificacion + provision
ya se cerro DAY 170). Es decir: pasar de "los tres sensores deberian emitir el mismo
community_id porque la canonicalizacion es identica" a "OBSERVAMOS que los tres emiten
el mismo string sobre el MISMO paquete real".

Distincion clave (P2 del Consejo, DAY 170): se valida lo que el binario EMITE
(data-plane), no lo que dice la config. El cross-check valida empiricamente el
CIMIENTO sobre el que se apoya todo el AdapterSpec §10.

---

## 2. Lo que se ha hecho hoy (CERRADO)

### 2.1 aRGus surfacea el community_id de forma observable

Hasta hoy aRGus sellaba el community_id en el campo protobuf (field 18) pero NO lo
exponia en claro en ningun sitio. Anadido un canal de telemetria dedicado:

- **`compute_community_id` permanece PURA** (5-tupla -> optional<string>). No se toco.
- Nuevo helper `sniffer::flow::log_community_id_emission(cid, saddr, daddr, sport,
  dport, proto)` — `sniffer/src/flow/community_id_log.{hpp,cpp}`.
- **Gateado por env var** `ARGUS_CID_CROSSCHECK=1`: OFF por defecto (coste nulo en
  hot path: una lectura de atomic cacheado + branch no tomado), ON solo para el test.
  Apagado para el test de RSS bajo carga (#5).
- **Punto unico de log invocado desde los 3 call-sites** de sellado
  (ring_consumer.cpp x2: features y net_features; main_libpcap.cpp x1). El log NO
  esta dentro de compute_community_id (que no ve timestamps ni 5-tupla completa);
  esta en los call-sites, donde la 5-tupla ya esta en scope. Un solo helper, cero
  duplicacion de logica de log.
- **Escribe a fichero dedicado** `/vagrant/logs/lab/cid-xcheck-argus.tsv`, TSV de 7
  campos (`cid saddr daddr sport dport proto ts_emision_ns`), con mutex (ring_consumer
  es multihilo) y fflush (visible para el parser sin esperar cierre). NO a stdout
  (que ya esta contaminado con [DUAL-NIC]/[PKT #]).
- **Compila y linka en Variant A (eBPF) y Variant B (libpcap)** — un solo .cpp sirve
  a ambos binarios.
- **Test TDH `test_community_id_log.cpp`**: verifica la diana DAY 170
  (147.32.84.165:1027 -> 74.125.232.195:80 TCP seed 0 -> 1:IN7uqVpMWxpmuhQTowSQB2XEe0E=)
  y las 7 columnas del TSV por contenido. Robusto a NDEBUG (checks explicitos con
  return 1, no assert que -DNDEBUG borraria). PASSED.

### 2.2 Verificador de paridad cross-sensor

`tools/community_id_crosscheck.py` (HOST, no pipeline). Lee las salidas crudas de los
tres motores via `vagrant ssh`, normaliza a `(cid, 5-tupla)`, compara.

Decision de diseno acordada: **paridad por VALOR de community_id** (el cid encapsula
la 5-tupla canonica del hash Corelight). La 5-tupla se conserva como ETIQUETA forense,
no como clave de comparacion (evita el problema de que cada motor nombra el proto
distinto: Suricata "TCP", Zeek "tcp", aRGus 6).

Tres categorias:
- **agree** — cids en la interseccion de los tres. El solomillo.
- **expected_diff** — cids que Suricata/Zeek emiten y aRGus difiere POR DISENO
  (ICMP/IPv6-ICMP/no-TCP-UDP -> compute_community_id = nullopt). Filtrado por proto.
- **anomaly** — todo lo demas. **NO se descarta**: se vuelca a
  `cid-xcheck-anomalies.tsv` con la 5-tupla de cada sensor, para investigacion.

**Guard N>0** antes de comparar: si un sensor capturo 0 flujos -> ERROR ruidoso +
exit 1, nunca "coinciden". Mata el falso verde de "tres logs vacios coinciden"
(p.ej. intnet sin promisc allow-all: nadie ve el trafico).

Rutas reales fijadas (verificadas, no de memoria):
- Suricata: `/var/log/suricata/eve.json` (de su default-log-dir), community_id raiz.
- Zeek: `/vagrant/logs/lab/zeek/conn.log` (cwd elegido al arrancar; Zeek manual, sin
  zeekctl ni systemd en la VM). community-id-logging + seed=0 ya en local.zeek
  (lineas 103/115), PERSISTENTE.
- aRGus: `/vagrant/logs/lab/cid-xcheck-argus.tsv` (el helper).

### 2.3 Decision sobre las anomalias (importante)

Las discrepancias NO se descartan. Una discrepancia de community_id sobre el mismo
paquete puede ser: (a) bug propio de canonicalizacion en un edge case, (b) diferencia
de capa (Suricata reensambla, Zeek sigue estado TCP, aRGus captura por flujo), o
(c) EVASION — un atacante que fragmenta/reordena para que dos sensores deriven tuplas
distintas. El caso (c) es exactamente lo que un NDR existe para ver. Tratar la
discrepancia como ruido a descartar nos cegaria ante la senal. Se capturan para
acumular evidencia y, cuando el correlation-engine gradue, alimentar el grafo Neo4j
como arista "sensores en desacuerdo sobre este flujo" (puente con ADR-052).

Etiqueta de anomalia: hoy por 5-tupla + cid. Cuando el tier golden formalice el
native_event_id determinista (AdapterSpec §4), se anade como segunda etiqueta y se
verifica que ambas senalan el mismo flujo (prueba cruzada gratis).

### 2.4 Validacion en dry-run (datos Neris offline, no replay en vivo)

Los tres motores leyeron el mismo pcap (Neris) en modo offline. Resultado:
- Guard: los tres OK (Suricata 107260, Zeek 31735, aRGus 3 lineas sinteticas).
- agree = 2: la diana TCP y una UDP/DNS reales cayeron en la interseccion. **El
  matching por cid funciona end-to-end.**
- expected_diff = 76: cids ICMP/IPv6-ICMP filtrados por proto. Correcto.
- anomaly = 14443: artefacto de 3 lineas de aRGus vs 14K de los otros (datos no
  homogeneos). Una linea sintetica only-argus cayo aqui como debia. El volcado
  forense escribio 43330 lineas con 5-tupla por sensor. Correcto.

El dry-run cazo dos bugs reales antes del replay: printf con \t literal (escaping
perdido en vagrant ssh) y el adaptador de Suricata leyendo /var/log produccion en vez
del Neris. Corregidos. El adaptador de Zeek (zeek-cut + bash -lc, el punto fragil)
funciono a la primera: 31735 records.

---

## 3. Lo que queda (PENDIENTE, manana o despues)

1. **Replay en vivo (#1 real)**: orquestacion que arranque aRGus
   (ARGUS_CID_CROSSCHECK=1) + Suricata + Zeek, los tres en eth1 PROMISCUO en el mismo
   intnet ml_defender_gateway_lan, luego UN solo tcpreplay del Neris a TASA BAJA desde
   el client (sin perdidas: que los tres vean TODOS los paquetes; el RSS bajo carga es
   el #5, deliberadamente opuesto y separado). Parar Zeek tras el replay (flushea al
   cierre TCP). Correr el verificador sin flags (rutas de produccion).
2. **Caso de IPs invertidas** (paquete de respuesta -> mismo community_id): prueba de
   bidireccionalidad canonica. El Neris ya trae ambas direcciones; un pcap de 2
   paquetes (SYN + SYN-ACK invertido) lo aisla mas limpio.
3. **Delta de timestamps de emision** (anadido Kimi/Grok/Mistral): el .tsv ya captura
   ts_emision_ns; falta el parser que compare cuando emite cada sensor (Suricata
   flow.timeout, Zeek cierre TCP, aRGus casi-real) para calibrar los source_wait_timeout
   (argus 5s / suricata 10s / zeek 20s) con datos reales en vez de estimaciones.

---

## 4. Preguntas al Consejo

### P1 — Lenguaje del verificador: ¿Python o migrar a C++?

Alonso plantea migrar `community_id_crosscheck.py` a C++ por coherencia con el
pipeline. Mi recomendacion es NO, y quiero contraste:

- El verificador es **andamiaje de host** (corre en macOS, una vez por replay,
  orquesta vagrant ssh). NO comparte runtime, VM ni criticidad con el pipeline C++
  (sniffer/detector/firewall, 24/7, hot path, -Werror, TSAN). Su coherencia real es
  con las OTRAS herramientas de host (parse_results.py de experiments/, scripts/),
  que ya son Python.
- Migrarlo a C++ no lo acerca al pipeline (seguiria siendo proceso aparte en el host);
  solo multiplica el coste de mantenimiento de un verificador que cambia a menudo.

**La pregunta C++ legitima esta en otro sitio**: el ADAPTADOR de ingesta real del
AdapterSpec (el que leera eve.json/conn.log y publicara SecurityEvent por ZeroMQ al
correlation-engine). ESE si es pipeline, corre en las VMs, y ahi el lenguaje es
decision de peso — sabiendo que el engine es C++ pero las fuentes hablan JSON/redis/
kafka, y que Zeek tiene plugins nativos y Suricata habla redis. ¿Como ve el Consejo
el lenguaje/forma de los adaptadores de ingesta, separados del verificador de hoy?

### P2 — ¿Que hacer con el volumen de anomalias?

En el replay real, con aRGus emitiendo decenas de miles de cids, el anomaly deberia
colapsar a un numero pequeno y real. Pero: ¿que umbral de anomaly aceptamos como
"verde" del #1? ¿Cero estricto (cualquier discrepancia TCP/UDP es fallo), o un % dado
que las diferencias de capa (reensamblado Suricata vs flujo aRGus) pueden producir
discrepancias legitimas no-evasion? Necesitamos definir el criterio de aceptacion
ANTES del replay para no racionalizar el resultado a posteriori.

### P3 — Promiscuidad del intnet (riesgo de falso verde)

El replay con MACs originales del pcap es unknown-unicast: el intnet de VirtualBox
solo lo inunda a un puerto si el adapter tiene PromiscModePolicy=allow-all. Si falta
en el Vagrantfile para suricata/zeek/defender, los tres ven 0 paquetes y sus logs
vacios "coinciden" (el guard N>0 lo caza, pero preferimos que no llegue ahi).
¿Confirmamos allow-all en eth1 de las tres VMs en el Vagrantfile como invariante
documentado antes del replay?

---

— Briefing DAY 171. Pendiente: replay en vivo, criterio de aceptacion, orquestacion.