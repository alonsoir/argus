# DAY 171 — Segunda Ronda al Consejo de Sabios
## Solo P2 (criterio de aceptacion) + un prerequisito que nadie recogio

| Campo | Valor |
|---|---|
| **Fecha** | 2026-06-01 (DAY 171, segunda ronda) |
| **Alcance** | SOLO P2. P1 y P3 quedan CERRADOS (consenso 8/8). |
| **Motivo** | Grieta real en P2: el Consejo se partio en dos criterios incompatibles. |

---

## 0. Lo que NO se reabre (cerrado 8/8)

**P1 — Lenguaje.** Consenso unanime: verificador en Python; adaptadores de
ingesta es otra decision (C++ probable, con sub-debate Zeek plugin-nativo vs
tail-externo que se difiere a cuando el correlation-engine gradue). Accion
aceptada: documentar la frontera "si publica SecurityEvents -> C++; si produce
evidencia humana -> Python" en ADR-051 (Polyglot Boundary). NO debatir mas.

**P3 — Promiscuidad.** Consenso unanime: allow-all invariante documentado en
Vagrantfile + pre-flight check (ip link / tcpdump) ANTES del replay, ademas del
guard N>0 despues. Tres capas: config + pre-flight + guard. Accion clara, solo
implementar. NO debatir mas.

---

## 1. La grieta de P2

El Consejo se partio en dos criterios de aceptacion INCOMPATIBLES para el
replay #1:

- **Cero estricto sobre TCP/UDP** (Claude, DeepSeek, Kimi): cualquier
  discrepancia de community_id en flujo TCP/UDP completo visto por los tres es
  bug o evasion. Cero, sin tolerancia.
- **Umbral porcentual** (ChatGPT >99.9%, Grok <2%, Qwen <=1%, Gemini "tolerable
  bajo lupa"): aceptan un % por "diferencias de capa legitimas" (reensamblado
  Suricata vs estado Zeek vs flujo aRGus).

Esto NO es un matiz de grado. Son dos premisas tecnicas, y una esta equivocada.
Hay que dirimirla antes de congelar el criterio, o el replay de manana arranca
con un criterio que esconde justo lo que buscamos.

---

## 2. La pregunta afilada que dirime P2

> **¿Puede el reensamblado, el estado de conexion, o cualquier diferencia de
> capa producir un community_id de VALOR DISTINTO sobre el mismo flujo TCP/UDP
> visto integro por los tres sensores (tasa baja, sin perdida)?**

Si la respuesta es NO, entonces el "1% legitimo" no existe en el #1, y los
cuatro consejeros del umbral porcentual estan tolerando un ruido que el diseno
no puede producir.

Nuestra tesis (los del cero estricto): la respuesta es NO, por construccion.

- El community_id se computa sobre la 5-tupla: IPs, puertos, proto. Cabeceras
  que NO dependen de reensamblado, estado, ni heuristica.
- Si los tres ven los mismos paquetes, extraen la misma 5-tupla, y el cid es
  identico por el hash Corelight determinista (seed=0, validado byte a byte
  DAY 170).
- El reensamblado/estado afecta a QUE eventos genera cada motor y a CUANDO, NO
  al VALOR del cid de un flujo dado.

**Reto explicito a los del umbral porcentual:** si sostienen el 1%, que
justifiquen tecnicamente de donde sale ese 1% de discrepancia de VALOR a tasa
sin perdida. Si no pueden nombrar el mecanismo, el umbral es racionalizacion
post-hoc — exactamente lo que el criterio de aceptacion debe impedir.

---

## 3. La confusion que origina la grieta (y su sintesis)

Creemos que los del % estan viendo algo real pero lo estan etiquetando mal. Hay
DOS tipos de discrepancia, y el diseno los separa:

| Tipo | Definicion | ¿Posible a tasa sin perdida? | Causa |
|---|---|---|---|
| **Valor** | Mismo flujo, cid DISTINTO | NO | Solo bug o evasion |
| **Presencia** | Un sensor emite un cid que otro NO | En #1, NO (sin perdida) | Drop o timing |

El "1% legitimo" que ven los del umbral es discrepancia de PRESENCIA, no de
valor. Y en el #1, a tasa baja sin perdida, la presencia tambien debe ser cero —
si no lo es, es senal de que la tasa no era tan limpia (hallazgo, no umbral a
tolerar).

**Sintesis propuesta (reconcilia ambos bandos):** el criterio NO es un numero,
es CLASIFICACION OBLIGATORIA antes del verde:

- Cero discrepancias de VALOR sin clasificar.
- Cada anomalia se etiqueta: (a) bug, (b) drop/presencia, (c) inexplicable ->
  evasion candidata.
- **VERDE del #1** = cero (a) y cero (c), y cero (b) porque la tasa baja sin
  perdida lo garantiza.
- El "%" de los del umbral se convierte en "cuantas (b) toleras", y en el #1 la
  respuesta es ninguna, porque no hay drop.

Esto no es ni "cero ciego" ni "% que esconde". Es el microscopio: cada anomalia
mirada y nombrada, no contada y descartada. Coherente con la decision ya tomada
(8/8) de no descartar anomalias.

---

## 4. El prerequisito que NADIE recogio (y hace P2 decidible)

Ningun consejero respondio a esto en la primera ronda, y es lo que convierte la
clasificacion (a)/(b)/(c) de adivinanza en medicion:

> **¿Exponen aRGus, Suricata y Zeek cada uno su contador de paquetes
> capturados / perdidos durante el replay?**

Sin contadores de drop por sensor, NO se puede distinguir una anomalia de
presencia (b) "drop legitimo" de un bug de no-emision (a). La clasificacion
obligatoria del punto 3 se vuelve indecidible. Por tanto:

- ¿Es instrumentar el drop por sensor un PREREQUISITO BLOQUEANTE del replay #1,
  o se puede diferir?
- aRGus ya tiene stats (events_processed/dropped en ring_consumer; pkts_sent/
  send_failures en libpcap). Suricata tiene stats.log. Zeek tiene capture_loss.log
  / stats.log. ¿Basta con recogerlos en el volcado del verificador, o hace falta
  instrumentacion nueva?

Nuestra posicion: es prerequisito, pero BARATO — los tres ya exponen los
contadores, solo hay que recogerlos junto a los logs de cid. Una columna mas en
el reporte del verificador, no codigo nuevo en los sensores.

---

## 5. Pregunta de vuelta a Gemini (timing de flush)

Gemini pregunto: ¿inyectar rafagas de inactividad artificiales en el pcap para
forzar el flush de flujos de Suricata/Zeek, o usar la distribucion temporal
natural del Neris?

Respuesta del equipo (a validar por el Consejo): **distribucion natural del
Neris para el #1.** Inyectar rafagas artificiales contaminaria la paridad de
VALOR con un artefacto nuestro — y el #1 valida valor, no timing. El timing
(delta de ts_emision_ns, calibracion de source_wait_timeout) es un experimento
POSTERIOR y separado, y ahi si tendria sentido forzar flush con rafagas
controladas. No mezclar el experimento de valor (#1) con el de timing.

¿El Consejo coincide en separar valor (natural, #1) de timing (rafagas, despues)?

---

## 6. Lo que se pide a esta segunda ronda

1. **Dirimir P2** con la pregunta del punto 2: ¿existe discrepancia de VALOR
   legitima a tasa sin perdida, si o no? Si no -> cero-valor + clasificacion
   obligatoria es el criterio. Si si -> que se nombre el mecanismo.
2. **Decidir el prerequisito del drop** (punto 4): bloqueante o diferible.
3. **Confirmar la separacion valor/timing** (punto 5).

Nada mas. P1 y P3 estan cerrados.

---

— Segunda ronda DAY 171. Solo P2 + prerequisito drop + separacion valor/timing.

# Criterio de Aceptación — Replay #1 (paridad de valor de community_id)
## Consolidado de las dos rondas del Consejo de Sabios — DAY 171

| Campo | Valor |
|---|---|
| **Fecha** | 2026-06-01 (DAY 171) |
| **Origen** | Segunda ronda del Consejo (convergencia 8/8 en P2). |
| **Estado** | CONGELADO. Cualquier cambio requiere nueva deliberación. |
| **Aplica a** | Replay #1: paridad operacional de community_id (aRGus/Suricata/Zeek). |
| **NO aplica a** | #5 (RSS bajo carga, con drop) ni #3 (timing de emision). |

---

## 0. Nota sobre el algoritmo (corrección de la segunda ronda)

Dos consejeros (Qwen, Mistral) escribieron en sus respuestas el hash como
"HMAC-SHA256" o "sha256". **Es incorrecto.** El community_id v1 de Corelight, y
la implementacion de aRGus en `sniffer/src/flow/community_id.cpp`, usan:

> **SHA1 puro** (sin clave, sin HMAC), via `EVP_Digest(..., EVP_sha1(), ...)`
> sobre el buffer canonico `seed(2 BE) || ip_lo || ip_hi || proto(1) || 0x00 ||
> port_lo(2 BE) || port_hi(2 BE)`, resultado en base64 con prefijo `"1:"`.

No se cambia nada del cripto: el codigo ya es correcto y conforme al spec. Esta
nota existe solo para que el error de los pseudocodigos del Consejo NO se propague
a ADRs ni documentacion. La fuente de verdad es el codigo, no los pseudocodigos.

---

## 1. Veredicto de P2 (dirimido 8/8)

**NO existe discrepancia de VALOR legitima** sobre un flujo TCP/UDP visto integro
por los tres sensores a tasa baja sin perdida. El community_id se computa solo
sobre la 5-tupla (IPs, puertos, proto) + seed=0; reensamblado, estado de conexion
y heuristicas operan por encima de esas cabeceras y no alteran el valor del hash.

Por tanto, el "umbral porcentual" (1%, <2%) queda **rechazado**: no hay mecanismo
fisico que produzca ese porcentaje de discrepancia de valor en las condiciones del
#1. Lo que se interpretaba como "1% legitimo" era discrepancia de PRESENCIA o de
TIMING, no de VALOR.

**Casos de borde registrados (para vigilancia futura, NO aplican al #1):**
- **Tuneles (VXLAN/GRE/QinQ)** — decapsulacion divergente entre sensores SI puede
  producir VALOR distinto, y NO seria bug ni evasion (Gemini). No aplica al #1
  porque el Neris es Ethernet directo. Vigilar cuando haya trafico tunelizado.
- **Fragmentacion IP** — fragmentos posteriores sin puertos producen PRESENCIA
  (nullopt/expected_diff), no VALOR distinto (Kimi).
- **GRO/LRO** — el kernel fusiona paquetes; menos paquetes, misma 5-tupla, mismo
  valor (Qwen). Afecta a #5, no a #1.

---

## 2. Precondiciones (si fallan, el replay es INVALIDO, no rojo)

1. **Promiscuidad:** `allow-all` en eth1 de las 3 VMs (suricata/zeek/defender) +
   pre-flight `ip link show eth1 | grep PROMISC` en cada una ANTES del replay.
   Si falla -> abortar, no ejecutar.
2. **Contadores de drop recogidos:** drop de los 3 sensores leido y reportado por
   el verificador (prerequisito BLOQUEANTE, ver §4). Si no se puede leer el drop
   de los tres, el replay NO se declara verde (la clasificacion de presencia se
   vuelve indecidible).
3. **Drop = 0 deseable:** la tasa del replay debe ser tan baja que el drop de los
   tres sea 0. Con drop=0, la causa DROP queda eliminada y la clasificacion de
   presencia es mecanica. Si drop>0, el replay no es invalido pero entra juicio
   (ver §3, categoria DROP).

---

## 3. Clasificación obligatoria de anomalías

Ninguna anomalia se descarta. Cada una se etiqueta. (Decision 8/8 DAY 170: las
discrepancias son evidencia, no ruido.)

### Discrepancia de VALOR (mismo flujo, cid distinto)
- **(a) bug** — error de canonicalizacion / parsing / race en el sellado.
- **(c) evasion** — sin bug identificable, misma 5-tupla aparente, cid distinto.
  Hallazgo de seguridad. Alimenta el grafo Neo4j (ADR-052) como arista de
  desacuerdo entre sensores.
- (futuro, con tuneles) decapsulacion divergente — ni (a) ni (c). No aplica al #1.

### Discrepancia de PRESENCIA (un sensor emite un cid que otro no)
Refinamiento de ChatGPT (segunda ronda): la presencia NO es solo "drop o bug".
Categorias:
- **DROP** — el sensor perdio el paquete. Confirmable con contadores (§4).
- **CONFIG** — diferencia de configuracion del sensor.
- **POLICY** — politica de logging legitima (p.ej. Zeek no emite conn.log para
  cierto tipo de flujo). NO es bug.
- **BUG** — el sensor vio el paquete (drop=0) y no emitio. Defecto a corregir.
- **UNKNOWN** — no clasificable con la evidencia disponible.

---

## 4. Prerequisito de contadores de drop (BLOQUEANTE, barato)

Sin contadores por sensor, distinguir DROP de BUG en una presencia es adivinar.
Los tres ya exponen los contadores; el verificador los recoge:

| Sensor | Fuente | Campos | Coste |
|---|---|---|---|
| Suricata | `stats.log` (o stats event en eve.json) | `capture.kernel_packets`, `capture.kernel_drops` | leer fichero existente |
| Zeek | `capture_loss.log` / `stats.log` | `pkts_processed`, `pkts_dropped` | leer fichero existente |
| aRGus | ring_consumer (`events_processed`/`events_dropped`) y libpcap (`pkts_sent`/`send_failures`) | **OJO: hoy van a stdout/log, NO a fichero estructurado** | requiere volcado parseable nuevo (pequeño, pero NO gratis) |

**Matiz no trivial:** Suricata y Zeek se leen de ficheros que ya existen. aRGus,
NO: sus contadores se imprimen a stdout/log periodicamente, no a un fichero
parseable. Hace falta que el sniffer (o el helper de cross-check) vuelque sus
stats a un fichero al cierre (p.ej. `cid-xcheck-stats-argus.json` al SIGTERM).
Es codigo nuevo pequeño, no "leer un log que ya existe". Tarea de DAY 172.

---

## 5. Veredicto

```
VERDE   = cero discrepancias de VALOR (TCP/UDP)
        + cero presencias BUG
        + cero presencias UNKNOWN
        + toda presencia residual clasificada DROP/CONFIG/POLICY y explicada
        + expected_diff (ICMP/no-TCP-UDP) 100% explicado por filtro de proto

AMARILLO = valor = 0, pero alguna presencia UNKNOWN sin clasificar
         (pausa para investigar antes de declarar verde)

ROJO    = cualquier discrepancia de VALOR
        | cualquier UNKNOWN persistente tras investigacion
        | evidencia de perdida de captura no contemplada (drop>0 no explicado)
```

El criterio NO es un porcentaje. Es cobertura de diagnostico: el % de anomalias
SIN clasificar debe ser 0. Microscopio, no colador.

---

## 6. Separación valor/timing (confirmada 8/8)

- **#1 (este criterio):** valida VALOR. Replay Neris a distribucion temporal
  natural. Sin inyeccion de pausas. Timing irrelevante.
- **#3 (posterior, otro experimento):** valida TIMING (delta de ts_emision_ns,
  calibracion de source_wait_timeout argus 5s/suricata 10s/zeek 20s). Pcap con
  pausas controladas (`tc qdisc delay` o gaps) para forzar flush. Solo tras #1 verde.

No mezclar. Son experimentos ortogonales.

---

— Criterio congelado, segunda ronda DAY 171. Consenso 8/8 en P2.