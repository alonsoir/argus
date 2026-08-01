# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 244

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
HEAD = el commit de cierre DAY 243 ("updated PROMPT and BACKLOG (DAY 243: primer bronce
host REAL…)"), rama feat/zeek-to-graph, árbol limpio, al día con origin. SIN merge a main.
Untracked benigno: create_wazuh_adapter_skeleton.py (no es entregable). VMs probablemente
aborted/poweroff tras el sueño del host.

## Estado que ordena el día — Piezas 0, 1 CERRADAS; PRIMER BRONCE HOST REAL producido
- ✅ Pieza 0 libs/host-domain-v1/ (DAY 241, d1374c40) — contrato bronce, 34 cols, verde en test-libs.
- ✅ Pieza 1 wazuh-adapter/ (DAY 242, 11f48096) — alerts.json → bronce host_domain_v1, 2/2 en VM wazuh.
- ✅ Bronce host REAL (DAY 243): destroy&up de wazuh + 4 agentes (defender/client/suricata/zeek)
  → adapter sobre alerts.json vivo con TOY_KEY (0123…×4, la misma que suricata/zeek en mitre-start)
  → 10419 filas en /vagrant/logs/host-domain/, todas 34 cols, 5 host_id (000+001-004), HMAC 10419/10419
  verificado. Bronce REGENERABLE, FUERA de git (buzón gitignored). NO oro, NO Kuzu (fuera de alcance).
  Receta para regenerarlo: destroy&up wazuh+agentes (manager ARRIBA primero) → export
  ARGUS_BRONZE_HMAC_KEY_HEX=0123…×4 → ./build-wazuh/wazuh_adapter config/wazuh_adapter.json.

## Batalla candidata DAY 244 — DEBT-HOST-ADAPTER-ALERTS-PERMS-001 (cablear + reproducible)
Justificación: el bronce host de DAY 243 salió con un `usermod` MANUAL. Mientras eso no viva en
el provision, el bronce no es reproducible desde cero (choca con "reproducibilidad = propiedad del
repo"). Es barato y desbloquea la Pieza 2, que consumirá ese bronce.
1. Añadir al provision `wazuh` del Vagrantfile: `usermod -aG wazuh vagrant` + `mkdir -p
   /vagrant/logs/host-domain` (dueño vagrant). DEPENDE de install-wazuh (crea el grupo wazuh) →
   respetar orden en el bloque.
2. Verificación por invocación, no `test -f` (lección DAY 230/ADAPTER_TOOLCHAIN): que el provision
   compruebe `id vagrant | grep wazuh` y el buzón exista.
3. CIERRE con dientes (lección DAY 230 — las VMs autostart:false no se ejercitan en un EMECAS a secas):
   destroy&up de wazuh DESDE CERO → sin un solo paso manual, el usuario vagrant lee alerts.json y el
   adapter produce N filas validadas en el buzón. Si hace falta el multi-host, destroy&up también de
   los 4 agentes (receta arriba). Criterio: bronce host REAL nacido de destroy&up con CERO pasos
   manuales de permisos.

## Arco después (una batalla por sesión, no desviarse)
- Pieza 2 (DEBT-HOST-PIEZA-2-GOLD-001): host bronce → oro AVRO/Parquet host_domain_v1 (34 cols;
  el converter de red es correlation_v1/19 cols → escribir el de host).
- Pieza 3 (DEBT-HOST-PIEZA-3-KUZU-001): host oro → Kuzu SU PROPIA BD (nunca el $KUZU de red).
- mitre-start reacciona a Wazuh (DEBT-MITRE-START-WAZUH-REACT-001) → EMECAS+++ con host verde
  en esta rama → PR a main.
- Post-main: migración de secretos (DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001): vault-client HTTPS,
  etcd-client solo liveness, rotación con solape de 2 claves.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando / fichero.
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; el grafo es proyección). A horas malas, parar.
- No `grep -rn` desde raíz (git grep o apunta al fichero). No encadenar salidas grandes. git add explícito.
- Wazuh = HOST-DOMAIN. Su bronce/oro/grafo → SU PROPIA BD Kuzu, nunca el $KUZU de red.
- El dato de host_domain_v1 nace de destroy&up + MITRE, no de toques a mano.
- SIN merge a main hasta EMECAS+++ verde con host en esta rama.
- Trazabilidad: cada tarea de este prompt cita la deuda del BACKLOG que la justifica (BACKLOG↔PROMPT).

## Deudas vivas (en docs/BACKLOG.md)
DEBT-HOST-ADAPTER-ALERTS-PERMS-001 (batalla de hoy) · DEBT-HOST-PIEZA-2-GOLD-001 ·
DEBT-HOST-PIEZA-3-KUZU-001 · DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001 ·
DEBT-MITRE-START-WAZUH-REACT-001 · DEBT-WAZUH-AGENT-IN-EACH-PROVISION-001 ·
DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001 · DEBT-HOST-DOMAIN-P1 (host-touching) ·
DEBT-HOST-DOMAIN-P2 (watermark inode,offset) · DEBT-WAZUH-AGENT-INSTALL-ORDER-001.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. La compilación es DENTRO de la VM. Rama
feat/zeek-to-graph, sin merge a main. Hilos de memoria: [[host-domain-contract]] (contrato +
DAY 243 completo), [[wazuh-adapter]] (Pieza 1), [[wazuh-host-domain]] (Wazuh/agentes),
[[hmac-secrets-provisioning]] (arquitectura futura de la clave), [[cierre-paper]] (roadmap).