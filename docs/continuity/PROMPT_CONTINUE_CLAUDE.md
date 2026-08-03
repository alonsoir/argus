# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 247

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
HEAD = cierres DAY 246: (A) mitre-start clave real + host-engine target WIP + PROMPT/BACKLOG,
en feat/zeek-to-graph. Untracked scratch benigno: build-hostfile.sh,
create_wazuh_adapter_skeleton.py, verify_host_gold.py. SIN merge a main. VMs aborted tras el sueño.

## Estado que ordena el día — (A) hecha y probada; falta rematarla + host en el gate
- ✅ (A) CLAVE REAL EN mitre-start: aRGus/suricata/zeek firman el bronce con la clave HMAC
  REAL de etcd, no toy. Diente DAY 246: head=0450d862, 0 descartes HMAC (2890/81/1255),
  1123 flujos cross-sensor. Committeada.
- 🟡 (A) SIN REMATAR (10 min): faltan 2 guards (suricata/zeek converter:
  `grep -q "descartadas: 0" /tmp/<s>-conv.log || die`, paridad con el de aRGus) + cosméticos
  (comentario l.54 "clave de juguete" ya es mentira → "clave real"; borrar def huérfana TOY_KEY l.8).
- 🟡 host-engine EN EL GATE (DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001): target build/test
  committeado, VERDE en aislado. FALTA: engancharlo a test-all (l.1236, línea propia — isla,
  NO test-libs/test-components) + `make emecas+++` verde CON host. Batalla original DAY 246,
  aparcada. Owed antes del PR a main.
- 🔴 ÓXIDO MEDIDO DAY 246: el entorno NO es reproducible sin bootstrap. pipeline-start ya no
  arrastra pipeline-build (Alonso lo quitó hace tiempo) → hoy faltaban libcorrelation_v1.so,
  ml-detector caído, tools de mitre-start sin construir (4 tropiezos, mismo hueco). emecas SÍ
  bootstrapea (destroy→up→bootstrap), así que el GATE no se afecta; el problema es correr cosas
  FUERA de emecas.

## Batalla candidata DAY 247 — camino al PR: emecas+++ verde CON host (medir primero)
0. REMATE de (A) (10 min): pegar los 2 guards + cosméticos + commit. Cierra (A) con dientes.
1. BASELINE del gate: `make emecas+++` from-scratch SIN host — ¿va verde hoy tras el óxido?
   Si sí, el óxido fue artefacto de correr-fuera-de-emecas y el gate es sano. Si no, hay rotura
   real que arreglar antes de meter host. MEDIR, no asumir.
2. ENGANCHE de host: `host-engine-test` a test-all (l.1236). Confirmar hipótesis
   kuzu-en-provisioning-de-defender en la 1ª corrida from-scratch (crypto_transport/kuzu ya
   instalados por pipeline-build en defender).
3. CIERRE: `make emecas+++` verde CON host → desbloquea el PR de feat a main.

## Arco después (una batalla por sesión)
- (B) adapter AUTÓNOMO (lo que Alonso pedía de fondo): que el adapter se AUTO-obtenga la clave
  (curl LIGERO a etcd-server /secrets/ml-detector, NO la lib etcd-client pesada — su cadena
  crypto_transport+seed_client+libsodium-1.0.19-fuente NO está en la VM sensor) + bucle
  folder-watch + carpeta procesados/. Proyecto multi-sesión (curl=20%, bucle=80%).
- bootstrap dentro de pipeline-build → entorno reproducible sin ceremonia.
- mitre-start en emecas+++ como check e2e real (valida PIPELINE e2e, NO self-provisioning del
  adapter; cuesta zeek en el `up` + tiempo de nmap en CI).
- Migración secretos "correcta": vault-client HTTPS + etcd-client-solo-liveness + rotación (post-main).

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando/fichero.
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; grafo = proyección).
- Circuito host = ISLA (BD/converter/loader propios, en defender, NUNCA $KUZU red).
- No `grep -rn` desde raíz (git grep o apunta al fichero). No encadenar salidas grandes. git add explícito.
- SIN merge a main hasta EMECAS+++ verde CON host en esta rama.
- sed -i de macOS/BSD exige sufijo de backup: `sed -i ''`.

## Deudas vivas (docs/BACKLOG.md)
DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001 · DEBT-ENV-BOOTSTRAP-NOT-REPRODUCIBLE-001 (nuevo) ·
DEBT-MITRE-START-GUARDS-SENSOR-001 (nuevo) · DEBT-HMAC-KEY-INSECURE-TRANSPORT-001 ·
DEBT-TEST-ALL-NOT-STANDALONE-001 (nuevo) · DEBT-TEST-INTEG-SIGN-ABORT-001 (nuevo) ·
DEBT-SIGN-PLUGINS-ON-BUILD-001 (nuevo) · DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001 (=B) ·
DEBT-MITRE-START-WAZUH-REACT-001.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Compilación DENTRO de la VM (defender para
host-engine/tools). Rama feat/zeek-to-graph, sin merge a main. Hilos de memoria:
[[hmac-secrets-provisioning]] (A/B/secretos), [[emecas-host-integration]] (host en el gate),
[[host-a-kuzu]] (grafo host), [[emecas-vagrant]] (gate+Vagrantfile), [[cierre-paper]] (roadmap).