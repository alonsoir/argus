# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 242

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 241 cerró la **Pieza 0: `libs/host-domain-v1/`** (biblioteca del contrato bronce
`host_domain_v1`, dominio host/Wazuh). Rama `feat/zeek-to-graph`. Lo primero al arrancar:
confirmar que HEAD es el commit `feat(host-domain-v1): contrato bronce host_domain_v1 (Pieza 0)`,
árbol limpio y pusheado. `git add` explícito (nunca `-a`/`-u`). **NO mergear a main** (no está
integrado; EMECAS+++ aún NO corrido con host). Las VMs probablemente `aborted`/`poweroff` tras el
sueño del host; se recuperan con `vagrant up NAME` (la lib compila en `defender`).

## Estado que ordena el día — PIEZA 0 CERRADA, empieza la Pieza 1
`libs/host-domain-v1/` está **completa, verde en la VM `defender` (autoridad final) y dentro del gate**:
- **✅ 7 ficheros**: `include/host_domain_v1/host_domain_v1.hpp` (Row de 34 cols, `TOTAL_COLS=34`),
  `src/host_domain_v1.cpp`, `tests/test_host_domain_v1.cpp` (bloques de propiedad + golden),
  `tests/vectors/host_domain_v1_vectors.json`, `tests/ref/host_domain_v1_ref.py` (referencia Python =
  definición primaria del golden, sin oráculo C++), `CMakeLists.txt` (patrón `correlation-v1`), + el
  bloque de targets en `Makefile`.
- **✅ En el gate**: `make test-libs` corre `host-domain-v1-test` → `1/1 Passed`, junto a las demás libs.
- **✅ Contrato congelado**: HMAC-SHA256 col 33 (clave **COMPARTIDA** `ARGUS_BRONZE_HMAC_KEY_HEX`);
  `event_id` BLAKE2b prefijo `wz1:`, acuñado por `mint_event_id` sobre la línea CRUDA de `alerts.json`;
  10 columnas-lista en JSON-celda (`encode_string_list`); error fundamental de `validate` = `host_id`
  vacío; golden byte-idéntico contra la referencia Python.
- Se compila e instala en `defender` (todo el toolchain), NO en `wazuh`. Deps ya en el Vagrantfile
  (`libsodium-dev`/`nlohmann-json3-dev`/`libssl-dev` + libsodium 1.0.19 de fuente) — cero provisioning nuevo.

## Candidato de batalla DAY 242 — Pieza 1: `wazuh-adapter/`
Crear el componente que CONSUME la lib: `alerts.json` (JSON por línea) → parseo → `mint_event_id(raw_line)`
→ construir `HostDomainV1Row` → `serialize()` → **bronce sellado CSV** (append-only) y **parar** (el
bronze→oro→Kuzu es aguas abajo; hermano fiel de suricata/zeek). Vive en la VM `wazuh`, con `build-wazuh`
sufijado (patrón suricata/zeek-adapter; `/vagrant` es carpeta COMPARTIDA — un `build/` pelado se pisa entre VMs).

Orden sugerido (medir la plantilla antes de escribir):
1. **Medir el scaffold de `suricata-adapter/`** como plantilla: `git ls-files suricata-adapter/` (13 ficheros:
   CMakeLists, README, config/*.json, include/<n>/{batch_writer,config,to_row}.hpp,
   src/{batch_writer,config,main,to_row}.cpp, tests/{CMakeLists,test_to_row}.cpp) + su target de Makefile
   (`suricata-adapter-build`, `vagrant ssh suricata`, `build-suricata`). Copiar la forma, no reinventarla.
2. **El `to_row` de host**: línea JSON → `HostDomainV1Row`. AQUÍ se llama `mint_event_id` con la línea
   CRUDA (antes de parsear, para la idempotencia por fichero), se extraen las comunes del bag `data`
   (srcuser/dstuser/srcip/srcport/uid/command; `""`=ausente) y se codifican las 10 listas con
   `encode_string_list`. **OJO al newline-guard**: `full_log`/`data_json`/`rule_description` deben quedar
   JSON-escapados o `validate` los rechaza (correctamente) — en host el guard SÍ dispara de verdad.
3. **watermark/offset** por `(inode, offset)` — `alerts.json` es live y rota (DEBT-HOST-DOMAIN-P2).
   Para el camino reproducible del paper (`destroy&up`) lee el fichero fresco entero.
4. **Makefile**: `wazuh-adapter-build/test/clean` calcado de suricata-adapter, con **`host-domain-v1-build`
   como PREREQ** (el consumidor real que hoy falta; análogo a ml-detector↔correlation-v1 — entonces
   `host-domain-v1-test` puede dejar de ser self-building).

Entregable probable del día: `wazuh-adapter/` compilando en la VM `wazuh`, con `test_to_row` verde contra
un `alerts.json` de muestra. **NO el bronze→oro→Kuzu todavía** (piezas posteriores).

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
- Guards DIFERIDOS de `validate` v1 (host): `rule_id` no vacío, rango de `rule_level`, formato de
  `event_id` → commit de contrato posterior, cuando se mida la necesidad (no votar).
- DEBT-HOST-DOMAIN-P1: FIM/SCA/rootcheck NO observados; se provocan con técnica MITRE host-touching en
  `mitre-start` (paso 3). Sin eso el grafo host solo muestra higiene de auth, no "Wazuh cazó el ataque".
- DEBT-HOST-DOMAIN-P2: rotación de `alerts.json` en el watermark (batalla Pieza 1).
- P4: nodos `Control`/cumplimiento (implementar o diferir; útil para el encuadre hospitalario HIPAA/GDPR).
- EMECAS+++ aún NO modificado/corrido con host — gate pendiente antes del merge.
- DEBT-WAZUH-AGENT-INSTALL-ORDER-001; authd abierto → `authd.pass` (familia "dev, no producción", P2/P3).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. La compilación es DENTRO de la VM (el Makefile raíz es
la fuente de la verdad). Rama `feat/zeek-to-graph`, sin merge a main. Hilos de memoria:
[[host-domain-contract]] (contrato host + Pieza 0 cerrada — leer primero), [[wazuh-host-domain]]
(Wazuh/host-domain), [[suricata-adapter]] (plantilla del scaffold para la Pieza 1),
[[contrato-multisensor]], [[cierre-paper]] (criterios de cierre y roadmap del paper honesto).