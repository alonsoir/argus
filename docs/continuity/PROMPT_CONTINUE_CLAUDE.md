# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 239

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 238 metió Wazuh en el laboratorio: manager vivo + los CUATRO agentes enrolados, y la
instalación de agentes codificada en el Vagrantfile. Rama `feat/zeek-to-graph`. Lo primero al
arrancar: confirmar HEAD = `d31173ea` ("added Vagrantfile to support Wazuh with server/agents…").
`git add` explícito (nunca -a/-u). **NO mergear a main** (decisión DAY 237): antes, EMECAS+++ verde
en esta rama con los sensores.

## El estado que ordena el día — A CASI cerrada, con DOS cabos sueltos que la bloquean
La batalla A (codificar los agentes en el Vagrantfile para que `destroy&up` los reproduzca) está
**probada en su mitad de instalación** pero NO cerrada. Antes de tocar nada nuevo, cerrar A:

1. **🔴 EL `.deb` NO ESTÁ EN GIT (resolver PRIMERO).** El commit `d31173ea` metió `Vagrantfile` +
   `tools/add_wazuh_agents.py` + `tools/fix_authd_force.py`, pero
   `provisioning/wazuh/wazuh-agent_4.14.7-1_amd64.deb` está **gitignored** (no salió ni staged ni
   untracked en el `git status` de cierre). El Vagrantfile REFERENCIA ese `.deb` → en un clon limpio
   la guarda del provision hace `exit 1` y el agente no instala. Es "reproducible en mi máquina", el
   trap que A venía a matar. MEDIR el `.gitignore` (`git check-ignore -v provisioning/wazuh/wazuh-agent_4.14.7-1_amd64.deb`)
   y DECIDIR:
    - **opción (i)** `git add -f provisioning/wazuh/*.deb` → binario en git (13 MB), versión clavada al
      manager, reproducible desde clon. Recomendada.
    - **opción (ii)** que una VM con internet (defender) baje el `.deb` una vez a `provisioning/wazuh/`
      en su provisioning con guarda `[ -f ] || curl…`; sin binario en git, a costa de internet+orden.
      Es hermano de la deuda de datasets (el `.pcap` del Neris tiene el mismo problema, sin resolver
      desde DAY 234) → lo que decidas aquí es el patrón para ambos.

2. **🔴 LA POLÍTICA `force` DEL MANAGER NO ESTÁ CODIFICADA.** Se aplicó EN VIVO con
   `tools/fix_authd_force.py` (pone `<force>` = reemplazar-siempre: `disconnected_time enabled="no"`,
   `after_registration_time` 0), pero un `destroy&up` del manager la revierte. Codificarla en el
   provisioning `install-wazuh` (heredoc del Vagrantfile ~1331-1361) o como provision `authd-force`
   propio en el bloque `wazuh` (que corra `fix_authd_force.py` + `systemctl restart wazuh-manager`).
   Necesita VER el heredoc `install-wazuh` entero para anclar el inserter, o meterlo como provision
   separado tras la línea 1362 (adapter-toolchain de wazuh).

## Candidato de batalla DAY 239 (Alonso decide el corte midiendo)
**Cerrar A del todo**, y solo entonces empezar el paso 2 (el contrato).
1. Resolver el `.deb` en git (punto 1 de arriba).
2. Codificar `force` en el provisioning (punto 2).
3. **PRUEBA FINAL de A** (la que la cierra de verdad): `vagrant destroy -f wazuh && vagrant up wazuh`
   (manager nace con `force` codificada) → luego `vagrant destroy -f zeek && vagrant up zeek` → el
   agente debe enrolarse LIMPIO, sin pasos manuales, y aparecer en `manage_agents -l` del manager.
   Eso prueba que `.deb`-en-repo + `force`-provisionada funcionan desde cero.
4. Commit del cierre de A (git add explícito): `provisioning/wazuh/*.deb` (si opción i), el
   Vagrantfile/provision de `force`, continuidad + BACKLOG.
5. **DESPUÉS**, el paso 2 de Alonso, ya la parte "interesante": contrato **`host_domain_v1`** →
   adapter que lea el `alerts.json` del manager → **su propia BD Kuzu** (NO el `$KUZU` de red).
   Batalla propia, probablemente el día siguiente. Ver [[wazuh-host-domain]] y [[contrato-multisensor]].

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando.
- Un día, una batalla. Vía Appia (un criterio que no puede ponerse rojo no mide). A horas malas, parar.
- No `grep -rn` desde raíz (usa `git grep`). No encadenar salidas grandes. `git add` explícito.
  Build/commit/push desde el host. macOS: nunca `sed -i` sin `-e ''`.
- **Wazuh = HOST-DOMAIN, medido DAY 238.** NO emite community_id / 5-tupla (0 sobre 520 eventos); es
  HIDS (FIM, SCA, rootcheck, syscollector, reglas de log). Su identidad es host+regla+timestamp. Va a
  **su propio grafo / su propia BD Kuzu**, NUNCA al `$KUZU` de red compartido de `mitre-start`.
  Reconfirma DEBT-HOST-DOMAIN-CONTRACT-001 y la decisión DAY 225. Es la mitad EDR/host del híbrido
  (ADR-046); el pipeline NDR de red quedó cerrado en DAY 237 con 3 sensores.
- **Instalación de agentes = `dpkg` del `.deb` cacheado en `/vagrant`, NUNCA `apt`.** Medido DAY 238:
  `client` no tiene salida a internet (ruta default por el intnet, `via 192.168.100.1`, por diseño de
  VM de ataque), y las VMs "peladas" no traen gnupg ni DNS estable. dpkg desde la carpeta sincronizada
  esquiva todo eso. Nombre del agente por `env AGENT_NAME`. **Manager (wazuh) EXCLUIDO** — es el
  manager, se automonitoriza vía agente 000.
- **El dato de host_domain_v1 debe nacer de `destroy&up` + MITRE**, no de toques a mano. El
  `/etc/testwazuh` de defender fue sonda de aprendizaje, NO evidencia.
- El re-enrollment de un agente re-imaginado con el manager VIVO exige `force`=reemplazar-siempre
  (colisión de nombre duplicado). En el baseline `destroy -f` pelado (borra TODAS) no colisiona porque
  el registro del manager nace vacío — la colisión es artefacto de destroy PARCIAL / re-imaging.

## Estado del tramo Wazuh (DAY 238, HECHO y medido)
- Manager `wazuh` vivo (4.14.7) en `192.168.100.12`. CUATRO agentes enrolados y Active:
  `001 defender · 002 client · 003 suricata · 005 zeek` (zeek es 005 tras el fix de `force`; el 004
  fantasma quedó reemplazado). Todos `IP: any` (authd sin password — deuda).
- Canal agente→manager confirmado E2E (no solo enrollment): `alerts.json` del manager subía en vivo
  atribuido a defender (215→218 entre dos greps). Puertos: 1515 enrollment, 1514 datos, por el intnet.
- Wazuh MEDIDO = host-domain: `alerts.json` = eventos de host (FIM/SCA cis_debian12/rootcheck/
  syscollector/PAM/journald). `grep -c community_id alerts.json` = 0. Forma del evento: `rule`(level/id/
  groups + mapeos pci_dss/hipaa/nist/gdpr) + `agent` + `decoder` + `location` + `full_log` + `data`.
- Vagrantfile modificado (commit `d31173ea`): constante `WAZUH_AGENT_INSTALL` (tras ADAPTER_TOOLCHAIN)
    + provision `wazuh-agent` en defender/client/suricata/zeek (NO wazuh). `ruby -c` y `vagrant validate`
      OK. **Instalación reproducible PROBADA**: `destroy -f zeek && up zeek` completó → dpkg del `.deb`
      sincronizado + arranque, sin manos.
- `force` del manager = reemplazar-siempre APLICADA EN VIVO (no codificada aún, ver cabo suelto 2).

## Herramientas nuevas (DAY 238, commiteadas en d31173ea)
- `tools/add_wazuh_agents.py` — inserta la constante + los 4 provisions en el Vagrantfile. Anclado,
  idempotente, all-or-nothing, backup. Ya aplicado (no re-correr; aborta solo si se re-corre).
- `tools/fix_authd_force.py` — pone la `<force>` del authd del manager en reemplazar-siempre.
  Idempotente, backup. Se corrió en vivo sobre el manager; FALTA codificarlo en provisioning.

## Notas de fontanería (medidas, no re-medir)
- Topología: manager .12, defender .1 (gateway del intnet), client .50, suricata .10, zeek .11; todos
  en el intnet `ml_defender_gateway_lan` 192.168.100.0/24. VMs de agente `autostart: false` salvo
  defender (`primary: true`).
- `.deb` en `provisioning/wazuh/wazuh-agent_4.14.7-1_amd64.deb` (versión = la del manager, 4.14.7-1).
- El heredoc `WAZUH_AGENT_INSTALL`: instala por dpkg, guarda doble (salta si `wazuh-control info` OK;
  falla ruidoso si no hay `.deb`), `WAZUH_MANAGER=192.168.100.12`, nombre por `env AGENT_NAME`.
- En un `destroy&up`-desde-cero, el manager (autostart:false) debe estar ARRIBA antes que los agentes
  para que el enroll no falle por manager ausente. El orden de bring-up NO lo garantiza el Vagrantfile
  (es manual/script) → relevante para la promoción EMECAS+++ (DEBT-WAZUH-AGENT-INSTALL-ORDER-001).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. `make pipeline-stop` si procede. Rama
`feat/zeek-to-graph`, sin merge a main hasta EMECAS+++ verde. El hilo de memoria del tema Wazuh es
[[wazuh-host-domain]]; el de identidad/contrato, [[contrato-multisensor]] y [[cierre-paper]].