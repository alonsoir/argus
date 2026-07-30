# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 240

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 239 cerró la batalla **A** (agentes Wazuh reproducibles desde el Vagrantfile). Rama
`feat/zeek-to-graph`. Lo primero al arrancar: confirmar que HEAD es el último commit de DAY 239
(la cadena, de arriba abajo: prompt de continuidad DAY 240 → `docs/BACKLOG.md` → `.gitignore`
`!provisioning/wazuh/*.deb` → **`48fa558f`** "feat(wazuh): provision authd-force … (cierra A)").
Árbol limpio, pusheado. `git add` explícito (nunca `-a`/`-u`). **NO mergear a main** (decisión
DAY 237, reafirmada DAY 239: no está integrado, hay que probar en esta rama primero + EMECAS+++
verde). Las VMs probablemente `aborted` tras el sueño del host; se recuperan con `vagrant up NAME`.

## Estado que ordena el día — A CERRADA, empieza el paso 2
La batalla A está **cerrada y commiteada** (`48fa558f`):
- **✅ `.deb` en git** (`6a6830bf`) — un clon limpio trae el agente por la carpeta sincronizada.
- **✅ `force` provisionada** — provision `authd-force` en el bloque wazuh (tras adapter-toolchain):
  `fix_authd_force.py` + `systemctl restart wazuh-manager` + grep fail-loud del marcador
  `<disconnected_time enabled="no">0` en `ossec.conf`. Sin poll de liveness (lección: `wazuh-control
  status` sale exit≠0 por daemons opcionales → falso negativo bajo `pipefail`).
- **✅ Prueba de enroll con dientes**: manager fresco → `zeek 001` limpio; re-imaging con manager
  vivo → `zeek 002`, `force` reemplaza el registro viejo, SIN `Duplicate agent name`.
  DEBT-WAZUH-AUTHD-FORCE-NOT-PROVISIONED-001 RESUELTA. El detalle vive en [[wazuh-host-domain]].

## Candidato de batalla DAY 240 (Alonso decide el corte midiendo)
**Paso 2 — arrancar el contrato `host_domain_v1`.** Es el PRIMER día de la sub-línea host, así que
la batalla honesta es **medir + diseñar**, no escribir el adapter a ciegas. Orden sugerido:
1. **Medir qué emite el manager AHORA, con agentes enrolados de verdad** (no solo el agente 000 del
   DAY 238). Levantar el lab (manager + al menos un agente), y sobre `/var/ossec/logs/alerts/alerts.json`
   inventariar: qué `rule.groups`, qué `decoder`, qué `location`, qué trae `data`, y con qué `agent`
   (id/name/ip) se atribuye. Barrido completo, no muestra. Esto fija los campos reales de origen.
2. **Definir el contrato `host_domain_v1`** (separado de correlation_v1, por diseño): qué campos son
   universales del dominio host (identidad = host + regla + timestamp, NO 5-tupla), cuáles los
   producimos nosotros (schema_version, source_sensor=wazuh, node_id/host_id, hmac_row…), cuál es la
   PK del nodo y cómo se evita colisión de event_id entre agentes/reprocesados (mismo cuidado que en
   [[contrato-multisensor]]: determinista, sin colisión). Decidir el modelo de nodos del grafo host
   (¿Host, Rule, HostEvent? ¿relaciones a MITRE/cumplimiento?).
3. **Plan del adapter host + su PROPIA BD Kuzu** (NO el `$KUZU` de red de mitre-start). Solo el plan;
   la escritura del adapter es batalla siguiente.
   Entregable probable del día: un doc de diseño (estilo puerta-diseño-multisensor) con cada afirmación
   marcada [MEDIDO]/[DECISIÓN]/[PENDIENTE], + evidencia en directorio trackeado (no en .gitignore).

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando / fichero.
- Un día, una batalla. Vía Appia (un criterio que no puede ponerse rojo no mide; y uno que se pone
  rojo sobre un sistema sano tampoco — ver la sonda de authd de DAY 239). A horas malas, parar.
- No `grep -rn` desde raíz (usa `git grep` o apunta al fichero). No encadenar salidas grandes.
  `git add` explícito. Build/commit/push desde el host. macOS: nunca `sed -i` sin `-e ''`.
- **Wazuh = HOST-DOMAIN, NO red.** No emite community_id / 5-tupla (medido: 0 sobre 520 eventos). Su
  dato va a SU PROPIO grafo / SU PROPIA BD Kuzu, NUNCA al `$KUZU` compartido. Reconfirma
  DEBT-HOST-DOMAIN-CONTRACT-001 y la decisión DAY 225.
- **Instalación de agentes = `dpkg` del `.deb` cacheado en `/vagrant`, NUNCA `apt`.** Nombre por
  `env AGENT_NAME`. Manager (wazuh) EXCLUIDO (se automonitoriza vía agente 000).
- **El dato de host_domain_v1 debe nacer de `destroy&up` + MITRE**, no de toques a mano (el
  `/etc/testwazuh` de DAY 238 fue sonda de aprendizaje, NO evidencia).
- **SIN merge a main** hasta probar en esta rama + EMECAS+++ verde.

## Deudas vivas (registradas, no urgentes)
- DEBT-WAZUH-AGENT-INSTALL-ORDER-001: en destroy&up-desde-cero el manager debe estar arriba antes que
  los agentes; el orden no lo garantiza el Vagrantfile (relevante para EMECAS+++).
- authd abierto (enrollment sin contraseña) → `authd.pass`. Familia "dev, no producción", P2/P3.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Rama `feat/zeek-to-graph`, sin merge a main. Hilos
de memoria: [[wazuh-host-domain]] (Wazuh/host-domain, A cerrada), [[contrato-multisensor]]
(identidad/contrato, plantilla del Eslabón 1), [[cierre-paper]] (criterios de cierre y paper honesto).