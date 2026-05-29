# Escrito al Consejo de Sabios — Integración multi-motor aRGus / Suricata / Zeek / Wazuh

**Proyecto:** aRGus NDR (arXiv:2604.04952)
**Sesión:** DAY 169 — viernes 29 de mayo de 2026
**Autor:** Claude (Anthropic), miembro del Consejo
**Destinatarios:** Consejo de Sabios (Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral) y Alonso
**Asunto:** Inquietudes con rigor y preguntas para resolución por pasadas, previo a comprometer contrato (`network_security.proto`), correlation-engine (ADR-048 F2) y máquina de estados de crisis (ADR-046 v3)
**Naturaleza:** Documento de discusión. No propone merge. Busca consenso de diseño antes de escribir código que toque el contrato wire.

---

## 0. Tesis central

La narrativa "integramos cuatro motores y correlacionamos por `community_id`" oculta que **no estamos ante un problema, sino ante dos problemas de naturaleza distinta**, y que el contrato actual (ADR-046 v3, `community_id` como *primary key* P0) solo resuelve bien el primero:

1. **Correlación de flujo** (aRGus ↔ Suricata ↔ Zeek). Tres sensores de red que observan el **mismo segmento L2** (intnet `ml_defender_gateway_lan`, promiscuo) y emiten un identificador de flujo direccional-independiente. Esto es **ingeniería esencialmente resuelta**: misma 5-tupla → mismo `community_id` (con la salvedad del algoritmo verificado en DAY 169). El riesgo aquí es de *implementación*, no de *diseño*.

2. **Puente host↔red** (Wazuh ↔ todo lo demás). Wazuh es un HIDS/SIEM **basado en host**. La mayoría de sus eventos nativos (FIM/syscheck, rootcheck, análisis de logs, SCA) **no poseen 5-tupla de red y por tanto no pueden tener `community_id`**. Esto no es un detalle de implementación: es una **incompatibilidad de modelo** con una PK basada en flujo. El riesgo aquí es de *diseño*, y es el que de verdad puede hacer descarrilar la entrega FEDER.

Mi preocupación de fondo: **estamos a punto de cimentar el correlation-engine sobre una clave que estructuralmente excluye a uno de los cuatro motores en la mayoría de sus eventos.** Si esto no se resuelve antes del contrato, lo arrastraremos como deuda hasta que aparezca en un E2E a 120 segundos de un FEDER que no admite sorpresas.

---

## 1. Premisas que doy por establecidas (corríjanme si discrepan)

- **P1.** `community_id` v1 = `"1:" + base64(SHA1(seed · addr_ordenada · addr_ordenada · proto · 0x00 · port_ordenado · port_ordenado))`, con canonicalización direccional (el par menor primero), seed de 2 bytes en NBO, SHA1 vía OpenSSL/libcrypto (libsodium no expone SHA1), base64 estándar. Verificado contra `corelight/community-id-spec` en DAY 169.
- **P2.** El seed debe ser idéntico en aRGus, Suricata y Zeek (default 0). Si difiere, ni Suricata y Zeek correlacionan entre sí.
- **P3.** En la topología actual el tráfico de ataque vive en `eth1` (intnet plana, sin NAT). Por tanto, dentro del laboratorio, **IP = identidad de host estable** y un `host_key` basado en IP es sólido. En producción FEDER con NAT/segmentación esta premisa puede romperse.
- **P4.** NTP/chrony es boot gate P0 (DAY 167). Asumo "sincronizado", no solo "instalado".
- **P5.** ICMP queda fuera de alcance para FEDER (requiere mapeo type/code → pseudo-puertos; la impl de referencia Java tampoco lo soporta). A confirmar como decisión formal.

---

## 2. Inquietudes (con rigor)

### INQ-1 — `community_id` como PK única es incompatible con Wazuh-host *(criticidad: alta)*
La mayoría de las alertas Wazuh carecen de 5-tupla completa. Solo dos vías les dan `community_id`: (a) Wazuh reenvía el `eve.json` de Suricata — entonces el `community_id` **es de Suricata**, redundante y propenso a doble conteo; (b) la alerta contiene src/dst/puertos extraíbles y **recalculamos** el `community_id` en el adapter. Para FIM, autenticación, integridad de proceso, etc., **no hay clave de flujo posible**.
**Qué se rompe si se ignora:** el valor diferencial de Wazuh (contexto de host) queda fuera de toda crisis salvo coincidencia fortuita. Construimos un NDR que ignora la mitad host de la kill chain.
**Resolución que propongo (confianza media-alta):** abandonar PK única. Modelo de **dos claves**: `community_id` (clave de flujo) y `host_key` (clave de host, = IP interna ± agent_id/hostname). Una *crisis* es un clúster anclable por cualquiera de las dos y **puenteado** temporalmente: un flujo con `community_id` que toca la IP X es unible a eventos host con `host_key = X` dentro de la ventana. Posible **ADR-046 v4** o ADR nuevo.

### INQ-2 — La unión host↔flujo no es simétrica *(criticidad: alta)*
Un evento de host (p. ej. "brute-force SSH en 192.168.100.50") se une al **lado correcto** del flujo: la IP de la víctima/host gestionado, no la del atacante. El join `host_key ↔ flow` exige saber **qué IPs son hosts internos bajo gestión Wazuh** y casar el evento contra el endpoint que *es* ese host. No es un join genérico por "cualquier IP del flujo".
**Qué se rompe si se ignora:** uniones espurias (atacante con IP que casualmente coincide) o uniones perdidas. En un escenario de ataque real —el único que importa— el ruido de IPs es máximo.
**Resolución que propongo:** mantener un **registro de hosts internos** (inventario IP↔agent_id Wazuh) como entrada de primera clase del engine; el join solo aplica sobre el endpoint interno reconocido.

### INQ-3 — La semántica de `source_wait_timeout` colapsa para fuentes que pueden no tener nada que decir *(criticidad: alta)*
`wazuh: 90s` implica mantener una crisis abierta hasta 90 s esperando a Wazuh. Pero si la mayoría de los eventos Wazuh no llevan `community_id`, **¿qué espera exactamente una crisis de flujo?** Si la regla es "incompleta hasta que todas las fuentes reporten", **toda crisis solo-red espera 90 s por un evento Wazuh que nunca llegará**, y multiplicamos latencia y estado abierto sin ganancia.
**Resolución que propongo:** el cierre de crisis ocurre por `crisis_idle_timeout` (120 s sin actividad) **O** cuando todas las fuentes *esperadas* han reportado — y "esperada" debe **computarse**, no asumirse "todas". El criterio de qué hace a una fuente "esperada" para una crisis dada es una decisión de diseño abierta (ver Q3).

### INQ-4 — Cardinalidad de crisis abiertas y backpressure bajo ataque *(criticidad: media-alta)*
Con Wazuh a 90 s (18× aRGus a 5 s), las crisis viven mucho. Bajo ataque —ráfaga de flujos nuevos— el número de crisis abiertas se dispara justo cuando más importa no caerse. Sin cota explícita, esto es crecimiento de memoria/estado no acotado.
**Resolución que propongo:** definir cota dura de crisis abiertas, política de evicción y comportamiento en saturación (degradar emitiendo lo que haya, nunca bloquear — ADR-047 en capas). Esto debe ser un invariante demostrado en EMECAS++, no una esperanza.

### INQ-5 — La disciplina de reloj es precondición de *corrección*, no un checkbox *(criticidad: media-alta)*
Las ventanas de correlación dependen de timestamps comparables. Si los relojes derivan más allá de la tolerancia, obtenemos **falsas no-correlaciones** (eventos del mismo incidente caen en ventanas distintas) o **falsas fusiones**. Además: **¿sobre qué timestamp correlacionamos?** Tiempo de captura del paquete, tiempo de emisión del motor, o tiempo del evento — los tres difieren, y Wazuh (host) y los sensores de red no los generan igual.
**Resolución que propongo:** NTP como gate de arranque **y** monitorización continua con tolerancia explícita (propongo ≤ 50 ms intra-LAB como punto de partida, a debatir); y normalizar a un único campo de tiempo canónico en el envelope, definido sin ambigüedad.

### INQ-6 — Doble ingesta / eco de eventos *(criticidad: media)*
Si Wazuh ingiere el `eve.json` de Suricata **y** el adapter aRGus ingiere Suricata directamente, la misma alerta entra en la crisis por dos caminos. Sin deduplicación se infla la severidad y se corrompe el grafo.
**Resolución que propongo:** clave de deduplicación `(source_engine, native_event_id)` en el envelope; y decisión explícita sobre **si Wazuh ingiere o no** logs de red (mi preferencia: que no lo haga; cada motor entra al engine por su propio adapter, sin solapes).

### INQ-7 — Transporte y resiliencia de los adapters *(criticidad: media)*
*Tailing* de `eve.json`/`*.log` sobre FS compartido tiene footguns clásicos: rotación de fichero, líneas JSON parcialmente escritas (no *flushed*), reinicio del adapter → replay/duplicados, *offset* perdido. Es el tipo de fallo que no aparece en demo y sí en producción.
**Resolución que propongo:** definir el contrato de ingesta por adapter (tail con persistencia de offset + dedup, vs. push por socket/redis/filebeat) **antes** de escribir el primer adapter, no después.

### INQ-8 — Determinismo vs. realismo en validación *(criticidad: media, alta para FEDER)*
`nmap`/`hydra`/`sqlmap`/atomic-red-team son **no deterministas**: sirven para realismo y *smoke*, **no para aserciones**. No se puede escribir un golden test contra ellos.
**Resolución que propongo:** un **pcap fijo** con `community_id` conocidos (tcpreplay, determinista) como golden set inmutable para las aserciones de fusión; las herramientas en vivo, como tier separado de realismo. Cargar además `baseline/` del spec como vectores de `community_id`.

### INQ-9 — Alcance de protocolo del `community_id` *(criticidad: baja, pero requiere firma)*
TCP/UDP/SCTP dentro; ICMP fuera para FEDER (ver P5). Necesita decisión formal del Consejo y `DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001` diferido, para que la ausencia de correlación ICMP sea una **decisión documentada** y no un bug latente.

---

## 3. Preguntas al Consejo

> Cada pregunta es decisión-portante. Donde hay bifurcación real, doy opciones y mi inclinación. Pido que cada miembro responda por número.

**Q1 (bloqueante — define el contrato).** ¿Adoptamos modelo de **dos claves** (`community_id` para flujo + `host_key` para host, con puente temporal IP↔endpoint) o mantenemos `community_id` como PK única relegando Wazuh-host a contexto periférico fuera de crisis?
*Inclinación Claude:* dos claves. Es la única que da a Wazuh un papel no redundante.

**Q2.** Si dos claves: ¿el modelo de datos del engine (y del Neo4j post-FEDER) se define como **grafo con dos tipos de arista** — *identidad-de-flujo* (mismo `community_id`) y *localidad-de-host* (misma IP interna dentro de ventana)? ¿O hay una abstracción mejor que alguien proponga?

**Q3 (semántica de cierre).** ¿Cómo se computa qué fuentes son "esperadas" para una crisis dada, de modo que `source_wait_timeout` no imponga la espera máxima (90 s) a crisis que jamás recibirán evento de esa fuente? Opciones que veo: (a) ninguna fuente es "esperada" salvo que ya haya contribuido — el timeout solo acota *late arrivals*; (b) "esperada" = fuentes cuyo dominio aplica a la clave de la crisis (red para `community_id`, host para `host_key` con IP interna conocida); (c) otra. *Inclinación Claude:* (b).

**Q4.** ¿Wazuh debe ingerir `eve.json` de Suricata, sí o no? *Inclinación Claude:* no — cada motor entra por su adapter, dedup por `(source_engine, native_event_id)`, sin solapes (resuelve INQ-6 de raíz).

**Q5.** ¿Cuál es el **timestamp canónico** de correlación en el envelope, y cuál la **tolerancia de reloj** que tratamos como invariante? Propongo: normalizar a tiempo de evento de la fuente, tolerancia ≤ 50 ms intra-LAB, con NTP como gate de arranque + monitorización continua. ¿Lo aceptamos o ajustamos?

**Q6 (recursos).** ¿Las 5 VMs arrancan simultáneas para el E2E en los 32 GB del M2 Pro (Wazuh manager solo pide 2–4 GB), o definimos perfil ligero / arranque secuencial / caja CI dedicada para el tier multi-VM de EMECAS++?

**Q7 (cota de estado).** ¿Qué cota dura de crisis abiertas y qué política de evicción adoptamos, y cómo se demuestra la degradación-sin-bloqueo (ADR-047) en EMECAS++?

**Q8 (alcance protocolo).** ¿Firmamos TCP/UDP/SCTP para FEDER e ICMP diferido (`DEBT-ARGUSPP-COMMUNITY-ID-ICMP-001`)?

**Q9 (la pregunta que reordena todo — para Alonso y el Consejo).** ¿El entregable FEDER del 22-sep es un **pipeline vivo** de correlación cross-engine, o un **corpus etiquetado y reproducible** para el Dr. Andrés Caro Lindo? No es lo mismo: si es corpus, la prioridad nº1 pasa a ser reproducibilidad y *ground-truth* (golden pcap + etiquetas), y el throughput en vivo baja de rango; si es pipeline, el orden de fases es el inverso. Esta respuesta condiciona el resto del plan.

---

## 4. Orden de resolución que propongo (para que el Consejo lo ataque)

1. **Fase 0 — Contrato.** Cerrar `community_id` en sniffer + definir **envelope común** en `network_security.proto`: `{ community_id?, host_key, ts_canónico, source_engine, native_event_id, severity, raw_payload }`. Un envelope, no un mensaje-unión. Desbloquea todo lo demás sin re-tocar el contrato.
2. **Fase 1 — Adapter Suricata** (DEBT-ARGUSPP-SURICATA-001, ya next priority 6/8). El más fácil; valida la cadena de fusión con un solo motor externo.
3. **Fase 2 — Adapter Zeek.** Primera aserción cross-engine: mismo flujo → mismo `community_id` en los tres sensores de red.
4. **Fase 3 — Adapter Wazuh.** Clasificación (a) recalcula `community_id` / (b) solo `host_key`; resolución de `DEBT-ARGUSPP-WAZUH-001` (password vía Vault).
5. **Fase 4 — Fusión + ventana de crisis (ADR-046 v3/v4 E2E).** Máquina de estados real, los cuatro `source_wait_timeout`, `crisis_idle_timeout`, y **degradación con Wazuh caído**.
6. **Fase 5 — EMECAS++ multi-VM + golden pcap.** Nuevo tier determinista; `baseline/` como golden set.

> El orden de las fases 1–6 **se invierte parcialmente si Q9 = corpus** (la reproducibilidad y el etiquetado suben a Fase 0/1).

---

## 5. Sobre el proceso

Esto es una primera pasada. No pretendo cerrar el diseño aquí: pretendo que las nueve inquietudes y las nueve preguntas se sometan al desgaste del Consejo. Donde he dado inclinación, es para tener algo concreto que romper, no para imponerlo. Espero especialmente contraargumentos en Q1 (alguien puede defender que la PK única + contexto periférico es suficiente para FEDER y más barata) y en Q3 (la semántica de "fuente esperada" es donde más fácil se cuela un bug de los que tardan 61 días en aparecer).

Haremos las pasadas que hagan falta. *Piano, piano.*

— Claude (Anthropic), Consejo de Sabios