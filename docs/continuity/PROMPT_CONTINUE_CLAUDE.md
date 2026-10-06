cat > docs/continuity/PROMPT_CONTINUE_CLAUDE.md <<'EOF'
# Prompt de continuidad — aRGus NDR, DAY289 → DAY290

Reglas de trabajo (sin cambios): medir, no votar; predicción escrita antes de medir; comandos
separados o cada salida a su fichero; nunca `grep -rn` desde la raíz (usar `git grep` o el fichero
concreto); los scripts/patchers los ejecuta Alonso en su VM; scripts como bloque `cat > f <<'EOF'`;
si algo no da lo esperado, parar; `LC_ALL=C` en todo script con aritmética en awk; en scripts con
`set -e` NO usar `pipefail` junto a `| head`. Tras un cambio, compilar TODO el pipeline
(`make pipeline-build PROFILE=production`). Dar comandos EXACTOS y COMPLETOS, uno a uno, en orden,
diciendo dónde se ejecuta cada uno (Mac / defender / client), sin nada que sustituir a mano.
Patchers atómicos e idempotentes con `--check` / `--apply` y marca en el código.

**Foco único: la cabeza DDoS.** Orden (DAY281): (1) observabilidad ✅, (2) contrato v2 ✅,
(3) reentrenar y medir [primer entrenamiento HECHO DAY289, PROVISIONAL; falta regenerar dataset],
(4) fast-alert como entrada propia a la fusión, (5) fusión + firewall por `final_decision`
(DEBT-FIREWALL-GATES-ON-LEVEL1-001, P0).

Operativa: targets del Makefile en el **Mac**; scripts en el **defender** desde `/vagrant`;
tráfico en el **client** (`eth1`, .50 → defender .1). Logs `/vagrant/logs/lab/{sniffer,ml-detector}.log`
(rotar SIEMPRE con `sudo truncate -s 0`). Escritor de dataset: `python3 /vagrant/day289_dataset_writer.py
on|off|estado` (quedó APAGADO). `day288_post.sh` acepta `REG=contraste` (por defecto `runs`).

## 0. Estado de git
Rama `feat/ddos-head-contract`, NO mergeada. DAY289: commit `perf(sniffer) [WINSTATS-CACHE-D289]`,
commit de herramientas DAY289 y commit de docs (este prompt, BACKLOG DAY289, paper_notes_day289.md).
Comprobar con `git log --oneline -5 origin/feat/ddos-head-contract`.

## 1. Lo que DAY289 dejó MEDIDO

### 1.1 Benigno con reflection_signature=1 (§4.1)
- Ambiente con rasgos: 10133 filas; con refl=1: **0**. El sniffer (XDP de ingreso en eth2, cara LAN)
  ve las CONSULTAS del client (.50 → 1.1.1.1:53, 8.8.8.8:53, NTP :123) pero NUNCA las respuestas:
  entran por la WAN (eth1) y salen por eth2 como egreso. Estructural, no falta de corridas.

### 1.2 Consolidación (`day289_consolidar.sh`, solo lectura)
- 19 corridas de `runs.tsv` → `logs/lab/day289/consolidado.csv`: 39165 ataque / 19399 benigno
  (9266 benigno de corrida + 10133 ambiente). Supervivencia 100 %. Línea base DAY288 reproducida al
  decimal. Bosque viejo: **48,6 % FP sobre el ambiente**. Manifiesto sha256 completo.

### 1.3 Primer entrenamiento PROVISIONAL (`day289_entrenar.py`)
- RF por defecto, random_state=42, sin scaler; pesos por celda (familia, tasa) dentro de cada clase,
  clases iguales; split temporal 70/30 por (fichero, familia). Modelo sha `4bf3f6ec…` (4728 nodos, prof. 16).
- Test: recall 100 %, FP 0 % (viejo: 18,8 % / 71,1 %). Caliente: syn 99,3 %, benignhot 0 %.
- Dejar una familia fuera: **syn 0 %**, udpA 95,7 %, udpB 99,8 %, ntp/dns 100 %.
  ⇒ separa por FIRMA, no por agregado.
- Importancias por impureza y por permutación discrepan (rasgos redundantes): no sirven para decidir
  qué rasgo quitar. Hace falta quitar columnas o permutar por grupos.

### 1.4 Contraste benigno de reflexión (`gen_benign_dns_ntp.py`, MANIFEST actualizado)
- bdns_small (DNS 80–250 B + NTP 90 B) 10 pps; bdns_large (DNS 1200–1442 B) 5/10/20 pps. Origen .50,
  un flujo por respuesta. Registradas en `logs/lab/day288/contraste.tsv` (4 FRÍAS, ACEPTADAS).
- Modelo provisional SIN reentrenar: bdns_small **73,7 % FP** (prob ~0,56, fuera de distribución);
  bdns_large **100 % FP** a 5/10/20 pps, sonda de victim_pps plana. Bosque viejo: 0 % en las cuatro.
- En frío, victim_rate_ratio benigno 20 pps = 1,17 ≈ ataque 30 pps = 1,18.

### 1.5 Reentreno-medida con contraste (`day289_reentrenar_contraste.py`, modelo sha `f65719e9…`)
- A: todo 100 %/0 %; victim_pps primera por permutación (0,22); victim_rate_ratio 0,0001.
- **Sonda: en TODAS las familias UDP con puerto de servicio la decisión salta en victim_pps 20→25**,
  sin importar tamaño ni familia. B (20 pps fuera de train): 90,6 % FP, frontera 10–15. C (5 pps fuera):
  0,2 %. ⇒ para reflexión el modelo es un UMBRAL ABSOLUTO de pps fijado por las tasas del dataset.
  No es detector de comportamiento. Etiquetado como frontera de laboratorio.

### 1.6 Rendimiento del consumidor del anillo (`day289_anillo_medir.sh`)
- CORRECCIÓN al prompt DAY288: `STAT_RESERVE_FAIL` (stats[1]) EXISTE desde DAY275; no hizo falta
  instrumentar. Invariante: ddos_victims(suma) = EVENTS + RESERVE_FAIL + FILTER_DISCARD + FRAG_SKIPPED.
- `perf` instalado A MANO en el defender (`linux-perf`); en perf 6.1 la clave por hilo es `pid`.
  Pilas DWARF sin resolver (atribución por hilo + símbolo + lectura de código).
- Medir con la medida EN SEGUNDO PLANO (ventana 90 s) y tcpreplay después: la sincronía manual falló
  una vez (anillo_1000 inválida, conservada como evidencia).
- Causa medida: `get_window_stats` (O(eventos en ventana), 4 inserts en unordered_set locales,
  malloc/free) llamado 9 veces por evento desde `MLDefenderExtractor::populate_ml_defender_features`
  (ring_consumer.cpp:851 → ml_defender_features.cpp), los 9 con la MISMA ventana de 30 s.
- Arreglo [WINSTATS-CACHE-D289] (una pasada por evento, caché solo dentro de populate):
  | | antes | después |
  |---|---|---|
  | techo consumidor | ~175 ev/s | **~305 ev/s** |
  | RESERVE_FAIL 1000 pps | 82,7 % | **69,0 %** |
  | RESERVE_FAIL 100 pps | 0 | 0 |
- Lo que queda: la pasada única sigue siendo O(10 000) con el búfer al tope. Agregador incremental
  estimado ~2× (~600 ev/s): al BACKLOG. Por encima manda el coste fijo por evento ⇒ un flood realista
  no cabe en un consumidor que emite por paquete.

## 2. Decisiones de Alonso DAY289
- Primer entrenamiento PROVISIONAL aunque faltara benigno con refl=1. No se cablea.
- `source_ip_dispersion` se sigue calculando (barato); redefinir con clave al BACKLOG.
- **Próxima regeneración del dataset: ataque SOBRE línea base benigna sostenida contra la misma
  víctima (clave caliente)**, no régimen frío. Opción abierta, sin decidir: modelo que aprende forma y
  salto relativo + umbral absoluto de tasa como parámetro medido por despliegue.
- **Se cambia la emisión a POR FLUJO (palanca 1) ANTES de regenerar**; una sola regeneración cubre
  emisión nueva + régimen caliente. Después, reentrenar y cablear.
- Cuantificar cuántas instancias protegen una instalación exige hardware y carga distribuida reales;
  los números de Vagrant no responden a eso.

## 3. Siguiente (DAY290): emisión por flujo — diseñar antes de escribir
1. Medir el camino actual por evento en `ring_consumer.cpp`: dónde se lee el anillo, dónde se actualiza
   FlowStatistics, dónde se llama `populate_protobuf_event`, la fast alert (event_kind=1) y el envío ZMQ.
2. Diseño con predicción por decisión: puntos de emisión (nacimiento, cada N paquetes o T ms, cierre o
   timeout); qué sigue siendo por paquete (actualizar FlowStatistics, alimentar el agregador, fast alert
   en el sniffer); qué pasa a ser por emisión (rasgos, protobuf, ZMQ). Valores N/T los decide Alonso.
3. Efectos a prever y medir: filas por flujo en el escritor de dataset; momento de la foto de
   flow_packet_count y de victim_*; carga del ml-detector; ZMQ-DROP.
4. Patcher atómico, compilación completa, `make test-components` (mirar el texto: el gate está
   enmascarado con `|| echo`), y repetir `anillo_100` / `anillo_1000` con el mismo protocolo.
5. Después: protocolo de corridas en régimen CALIENTE (línea base benigna sostenida → ataque encima),
   familias ntp/dns/syn/udpA/udpB, contrastes bdns_small/bdns_large + los pendientes (ráfaga legítima
   de conexiones TCP cortas; UDP benigno hacia .1), tasas más altas si el techo lo permite.
6. Reentrenar con la misma batería: test, dejar una familia fuera, tasa reservada, sonda de victim_pps,
   caliente, contraste. Solo entonces cablear (pasos 4–5).

## 4. Herramientas DAY289 (raíz, commiteadas)
`day289_refl_ambiente.sh`, `day289_consolidar.sh`, `day289_entrenar.py`, `day289_eval_contraste.py`,
`day289_reentrenar_contraste.py`, `day289_dataset_writer.py`, `day289_patch_post_reg.py`,
`day289_anillo_medir.sh`, `day289_patch_winstats_cache.py`; `scripts/dataset_lab/gen_benign_dns_ntp.py`.
Evidencia (NO trackear): `/vagrant/logs/lab/day289/` (consolidado, modelos .joblib + sha256,
predicciones, anillo/) y `/vagrant/logs/lab/day288/contraste*.tsv`.
EOF