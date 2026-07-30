# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 239

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 238 metió Wazuh en el laboratorio: manager vivo + los CUATRO agentes enrolados, la instalación de
agentes codificada en el Vagrantfile, y el `.deb` cacheado en el repo. Rama `feat/zeek-to-graph`.
Lo primero al arrancar: confirmar HEAD = `6a6830bf` ("chore(wazuh): cachear wazuh-agent … .deb"),
árbol limpio, pusheado. Debajo, `d31173ea` (Vagrantfile + los 2 scripts). `git add` explícito
(nunca -a/-u). **NO mergear a main** (decisión DAY 237): antes, EMECAS+++ verde en esta rama.

## El estado que ordena el día — A a falta de UN cabo + la prueba final
La batalla A (codificar los agentes en el Vagrantfile para que `destroy&up` los reproduzca) está casi
cerrada. De sus dos cabos, uno ya está saldado:

- **✅ HECHO — el `.deb` está en git.** `git check-ignore` reveló que lo escondía `.gitignore:236 *.deb`
  (patrón global). Resuelto con `git add -f provisioning/wazuh/wazuh-agent_4.14.7-1_amd64.deb` →
  commit `6a6830bf`, pusheado. Un clon limpio ya trae el `.deb` por la carpeta sincronizada → la guarda
  del provision no fallará. (El `.deb` nunca estuvo "atrapado en una VM": `/vagrant` es la raíz del repo
  en el host.)

- **🔴 PENDIENTE (único cabo) — codificar la política `force` del manager.** Se aplicó EN VIVO con
  `tools/fix_authd_force.py` (pone `<force>` = reemplazar-siempre: `disconnected_time enabled="no"`,
  `after_registration_time` 0), pero un `destroy&up` del manager la revierte. Sin ella, el re-enrollment
  de un agente re-imaginado con el manager VIVO vuelve a colisionar por nombre duplicado. Codificarla en
  el provisioning: opciones — (a) editar el heredoc `install-wazuh` (Vagrantfile ~1331-1361) para que
  ANTES de arrancar el manager escriba el `<force>` en `ossec.conf`; o (b) un provision `authd-force`
  propio en el bloque `wazuh` (tras la línea 1362, adapter-toolchain) que corra
  `python3 /vagrant/tools/fix_authd_force.py` + `systemctl restart wazuh-manager`. Para anclar bien el
  inserter, PEGAR el heredoc `install-wazuh` entero; o meter (b) como provision separado.

## Candidato de batalla DAY 239 (Alonso decide el corte midiendo)
**Cerrar A del todo**, y solo entonces empezar el paso 2 (el contrato).
1. Codificar `force` en el provisioning (cabo pendiente de arriba).
2. **PRUEBA FINAL de A** (la que la cierra de verdad): `vagrant destroy -f wazuh && vagrant up wazuh`
   (manager nace con `force` codificada) → luego `vagrant destroy -f zeek && vagrant up zeek` → el
   agente debe enrolarse LIMPIO, sin pasos manuales, y aparecer en `manage_agents -l` del manager.
   Eso prueba que `.deb`-en-repo + `force`-provisionada funcionan desde cero.
3. Commit del cierre de A (git add explícito): el provision de `force`, continuidad + BACKLOG.
4. **DESPUÉS**, el paso 2 de Alonso, la parte "interesante": contrato **`host_domain_v1`** → adapter que
   lea el `alerts.json` del manager → **su propia BD Kuzu** (NO el `$KUZU` de red). Batalla propia,
   probablemente el día siguiente. Ver [[wazuh-host-domain]] y [[contrato-multisensor]].

Opcional apuntado (trivial, con la cabeza fresca): el `.gitignore` sigue con `*.deb` genérico → el
próximo `.deb` (subida de versión del agente) volvería a quedar invisible. Añadir
`!provisioning/wazuh/*.deb` deja la excepción documentada en el repo en vez de depender del `-f`.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando.
- Un día, una batalla. Vía Appia (un criterio que no puede ponerse rojo no mide). A horas malas, parar.
- No `grep -rn` desde raíz (usa `git grep`). No encadenar salidas grandes. `git add` explícito.
  Build/commit/push desde el host. macOS: nunca `sed -i` sin `-e ''`.
- **Wazuh = HOST-DOMAIN, medido DAY 238.** NO emite community_id / 5-tupla (0 sobre 520 eventos); es
  HIDS (FIM, SCA, rootcheck, syscollector, reglas de log). Identidad host+regla+timestamp. Va a **su
  propio grafo / su propia BD Kuzu**, NUNCA al `$KUZU` de red compartido de `mitre-start`. Reconfirma
  DEBT-HOST-DOMAIN-CONTRACT-001 y la decisión DAY 225. Es la mitad EDR/host del híbrido (ADR-046); el
  pipeline NDR de red quedó cerrado en DAY 237 con 3 sensores.
- **Instalación de agentes = `dpkg` del `.deb` cacheado en `/vagrant`, NUNCA `apt`.** Medido DAY 238:
  `client` no tiene salida a internet (ruta default por el intnet, por diseño de VM de ataque), y las
  VMs "peladas" no traen gnupg ni DNS estable. dpkg desde la carpeta sincronizada esquiva todo eso.
  Nombre del agente por `env AGENT_NAME`. **Manager (wazuh) EXCLUIDO** — se automonitoriza vía agente 000.
- **El dato de host_domain_v1 debe nacer de `destroy&up` + MITRE**, no de toques a mano. El
  `/etc/testwazuh` de defender fue sonda de aprendizaje, NO evidencia.
- El re-enrollment de un agente re-imaginado con el manager VIVO exige `force`=reemplazar-siempre
  (colisión de nombre). En el baseline `destroy -f` pelado (borra TODAS) no colisiona porque el registro
  del manager nace vacío — la colisión es artefacto de destroy PARCIAL / re-imaging.

## Estado del tramo Wazuh (DAY 238, HECHO y medido)
- Manager `wazuh` vivo (4.14.7) en `192.168.100.12`. CUATRO agentes enrolados y Active:
  `001 defender · 002 client · 003 suricata · 005 zeek` (zeek es 005 tras el fix de `force` aplicado en
  vivo; el 004 fantasma quedó reemplazado). Todos `IP: any` (authd sin password — deuda).
- Canal agente->manager confirmado E2E: `alerts.json` del manager subía en vivo atribuido a defender
  (215->218). Puertos: 1515 enrollment, 1514 datos, por el intnet.
- Wazuh MEDIDO = host-domain: `alerts.json` = eventos de host (FIM/SCA cis_debian12/rootcheck/
  syscollector/PAM/journald). `grep -c community_id alerts.json` = 0. Evento: `rule`(level/id/groups +
  mapeos pci_dss/hipaa/nist/gdpr) + `agent` + `decoder` + `location` + `full_log` + `data`.
- Vagrantfile (commit `d31173ea`): constante `WAZUH_AGENT_INSTALL` (tras ADAPTER_TOOLCHAIN) + provision
  `wazuh-agent` en defender/client/suricata/zeek (NO wazuh). `ruby -c` / `vagrant validate` OK.
  Instalación reproducible PROBADA: `destroy -f zeek && up zeek` completó -> dpkg del `.deb` sincronizado.
- `.deb` en repo (commit `6a6830bf`). `force` del manager aplicada EN VIVO (no codificada aún, ver arriba).

## Herramientas (DAY 238, commiteadas)
- `tools/add_wazuh_agents.py` — inserta la constante + los 4 provisions en el Vagrantfile. Ya aplicado
  (no re-correr; aborta solo si se re-corre). Anclado/idempotente/backup.
- `tools/fix_authd_force.py` — pone la `<force>` del authd del manager en reemplazar-siempre. Se corrió
  en vivo; FALTA codificarlo en provisioning (usarlo también ahí).

## Notas de fontanería (medidas, no re-medir)
- Topología: manager .12, defender .1 (gateway del intnet), client .50, suricata .10, zeek .11; todos
  en el intnet `ml_defender_gateway_lan` 192.168.100.0/24. VMs de agente `autostart: false` salvo
  defender (`primary: true`).
- `.deb` en `provisioning/wazuh/wazuh-agent_4.14.7-1_amd64.deb` (versión = la del manager, 4.14.7-1).
- El heredoc `WAZUH_AGENT_INSTALL`: instala por dpkg, guarda doble (salta si `wazuh-control info` OK;
  falla ruidoso si no hay `.deb`), `WAZUH_MANAGER=192.168.100.12`, nombre por `env AGENT_NAME`.
- En un `destroy&up`-desde-cero, el manager (autostart:false) debe estar ARRIBA antes que los agentes
  para que el enroll no falle por manager ausente. El orden NO lo garantiza el Vagrantfile (es
  manual/script) -> relevante para EMECAS+++ (DEBT-WAZUH-AGENT-INSTALL-ORDER-001).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. `make pipeline-stop` si procede. Rama
`feat/zeek-to-graph`, sin merge a main hasta EMECAS+++ verde. Hilo de memoria del tema:
[[wazuh-host-domain]]; identidad/contrato: [[contrato-multisensor]] y [[cierre-paper]].