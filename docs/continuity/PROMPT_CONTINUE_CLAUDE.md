# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 243

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 242 cerró la **Pieza 1: `wazuh-adapter/`** (alerts.json → bronce host_domain_v1 CSV
sellado). Rama `feat/zeek-to-graph`. Lo primero al arrancar: confirmar que HEAD es el commit
`updated PROMPT and BACKLOG` (encima del `feat(wazuh-adapter): alerts.json -> bronce
host_domain_v1 (Pieza 1)…​`), árbol limpio y pusheado. `git add` explícito (nunca `-a`/`-u`).
**NO mergear a main** (no está integrado; EMECAS+++ aún NO corrido con host). Las VMs
probablemente `aborted`/`poweroff` tras el sueño del host; se recuperan con `vagrant up NAME`
(la lib compila/instala en `defender`; el adapter se construye en `wazuh`).

## Estado que ordena el día — PIEZA 0 y PIEZA 1 CERRADAS
El circuito host va por el bronce. Lo HECHO (medido, no supuesto):
- **✅ Pieza 0 `libs/host-domain-v1/`** (DAY 241, commit `d1374c40`): biblioteca del contrato
  bronce host_domain_v1 (Row de 34 cols, `serialize()`/HMAC-SHA256 col 33, `mint_event_id`
  BLAKE2b `wz1:`, `encode_string_list`, `validate`). Verde en `defender`, dentro de `test-libs`.
- **✅ Pieza 1 `wazuh-adapter/`** (DAY 242): 13 ficheros (forma calcada de suricata/zeek-adapter
    + `to_row` de host). `to_row` VERIFICADO en contenedor: C++ y la referencia Python
      (`host_domain_v1_ref.py`) cruzan **byte-idéntico** sobre las 6 líneas reales del snapshot
      day240 (rule.id 533/503/5502/5402/5501/5715), y la lib revalida su golden de Pieza 0.
      **`make wazuh-adapter-test` en la VM `wazuh` (autoridad final) = 2/2 Passed**:
      `host_domain_v1_golden` (arrastrado por el `add_subdirectory` de la lib en el build suelto)
    + `wazuh_adapter_to_row`. Bloque de Makefile cableado (`wazuh-adapter-build/test/clean/rebuild`,
      `vagrant ssh wazuh`, build dir `/vagrant/wazuh-adapter/build-wazuh`, prereq `host-domain-v1-build`).
- **Contrato del adapter (congelado)**: `schema_version="host_domain_v1"`, `source_sensor="wazuh"`;
  `event_id` acuñado por `mint_event_id` sobre la **línea CRUDA** (idempotencia por fichero);
  `host_id`=`agent.id` (PK; vacío → lo rechaza `serialize()`, no el adapter); `data_json` = volcado
  compacto del bag `data` con **orden de claves preservado** (`ordered_json`), `"{}"` si no hay;
  **saneador de newline** (`\r`/`\n` reales → escape literal en full_log/rule_description/command:
  la 533 netstat es multilínea y así SOBREVIVE en vez de rechazarse); comunes de `data` string
  (`""`=ausente); 10 listas (groups/mitre/cumplimiento) vía `encode_string_list`. El adapter NO
  enlaza libsodium directo (mint vive en la lib → crypto/sodium llegan PUBLIC transitivos); la
  config NO tiene `node_id` (la identidad host viaja en la alerta). Deps ya en el Vagrantfile
  (ADAPTER_TOOLCHAIN en wazuh) → cero provisioning nuevo.

## Candidato de batalla DAY 243 — el bronce host REAL (destroy&up)
Hasta hoy el adapter solo produjo bronce en test (líneas congeladas del snapshot). El siguiente
paso: **filas host firmadas REALES nacidas de `destroy&up`**, no de un toque a mano ni de la
snapshot (invariante: el dato de host_domain_v1 debe nacer de destroy&up + MITRE).
Orden sugerido (medir antes de correr):
1. `destroy&up` del manager `wazuh` (+ agentes en defender/client/suricata/zeek) → `alerts.json`
   fresco de provisioning. Confirmar: manager arranca, agentes enrolan (política `force`, DAY 239),
   `alerts.json` crece. OJO al orden (DEBT-WAZUH-AGENT-INSTALL-ORDER-001): manager ARRIBA antes que
   los agentes.
2. **Clave HMAC REAL compartida** (`ARGUS_BRONZE_HMAC_KEY_HEX`, la de mitre-start), NO la de test
   (0xAB). Medir de dónde la toma la corrida reproducible de red y usar la MISMA (así el bronce host
   es verificable con el mismo mecanismo).
3. Crear/confirmar el buzón `/vagrant/logs/host-domain`. Correr el adapter sobre
   `/var/ossec/logs/alerts/alerts.json` (fichero fresco ENTERO; el watermark por `(inode,offset)`
   es DEBT-HOST-DOMAIN-P2, pieza posterior).
4. **Criterio**: N filas host en `/vagrant/logs/host-domain/wazuh-*.csv`, todas pasando `validate`,
   contadores ruidosos (leidas/escritas/descartadas/err) cuadrando con lo medido en el `alerts.json`.
   NO oro, NO Kuzu todavía.
   Riesgo a evitar (lección suricata DAY 227): NO escribir a `/tmp` de la VM (se evapora); el bronce
   que importa va a `/vagrant/logs/host-domain`.
   Entregable probable: primer **bronce host REAL** firmado con la clave compartida.

## Arco después (no de un día, no desviarse)
- **Pieza 2**: host bronce → **oro Parquet** (host_domain_v1). El `bronze_to_gold_converter` de red
  es `correlation_v1`-específico (19 cols); host necesita su equivalente para 34 cols.
- **Pieza 3**: host oro → **Kuzu, SU PROPIA BD** (esquema host_domain_v1: nodos Host/HostEvent/Rule/
  MitreTechnique, +Control P4 opcional). NUNCA el `$KUZU` de red compartido.
- **Reproducibilidad**: cablear el adapter host en el camino `destroy&up` (equivalente host de
  `mitre-start`), para que una corrida arrastre alerts.json → bronce → oro → grafo host.
- **Paso 3 (DEBT-HOST-DOMAIN-P1)**: técnica MITRE host-touching en `mitre-start` → FIM/SCA/rastro de
  ataque → "Wazuh cazó el ataque", no solo higiene de auth.
- **Gate**: EMECAS+++ con host verde en esta rama → merge a main (DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001).

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando / fichero.
- Un día, una batalla. Vía Appia (el oro/bronce es la fuente de verdad; el grafo es proyección
  reconstruible DESDE EL LEDGER). A horas malas, parar.
- No `grep -rn` desde raíz (usa `git grep` o apunta al fichero/dir). No encadenar salidas grandes.
  `git add` explícito. Build/commit/push desde el host; la compilación ocurre DENTRO de la VM.
- **Wazuh = HOST-DOMAIN, NO red.** Su bronce/oro/grafo van a SU PROPIA BD Kuzu, NUNCA al `$KUZU`
  compartido de red. Contrato `host_domain_v1` separado de `correlation_v1`.
- **El host es hermano fiel de suricata/zeek**: el adapter produce bronce sellado (CSV) y para.
- **El dato de host_domain_v1 debe nacer de `destroy&up` + MITRE**, no de toques a mano.
- **SIN merge a main** hasta EMECAS+++ verde con host en esta rama.

## Deudas vivas (registradas, no urgentes)
- DEBT-HOST-DOMAIN-P2: rotación de `alerts.json` en el watermark (`inode,offset`). Hoy se lee entero.
- DEBT-HOST-DOMAIN-P1: FIM/SCA/rootcheck NO observados; técnica MITRE host-touching en `mitre-start`.
- DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001: EMECAS+++ aún NO corrido con host — gate antes del merge.
- Guards DIFERIDOS de `validate` v1 (host): `rule_id` no vacío, rango de `rule_level`, formato de
  `event_id` → commit de contrato posterior, cuando se mida la necesidad.
- `host-domain-v1-test` self-build: OPCIONAL quitar el prereq `: host-domain-v1-build` ahora que
  `wazuh-adapter-build` es el consumidor real. No urge (el 2/2 salió sin tocarlo).
- P4: nodos `Control`/cumplimiento (implementar o diferir; útil para el encuadre hospitalario
  HIPAA/GDPR — el mapeo ya se captura en el bronce host).
- DEBT-WAZUH-AGENT-INSTALL-ORDER-001; authd abierto → `authd.pass` (familia "dev, no producción").

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. La compilación es DENTRO de la VM (el Makefile
raíz es la fuente de la verdad). Rama `feat/zeek-to-graph`, sin merge a main. Hilos de memoria:
[[wazuh-adapter]] (Pieza 1, cerrada — leer primero), [[host-domain-contract]] (contrato host +
Pieza 0), [[wazuh-host-domain]] (Wazuh/host-domain, agentes), [[suricata-adapter]] (plantilla del
scaffold + lección /tmp), [[cierre-paper]] (criterios de cierre y roadmap del paper honesto).