# Prompt de continuidad DAY306 — aRGus NDR

Usa las sesiones anteriores relevantes (DAY300-DAY305) para crear el contexto. Base en el repo:
`docs/ml-heads/prompt_day306.md` (este), `docs/ml-heads/day305_interruptor_cabezas.md`, `docs/BACKLOG.md`
(sección "Cierre DAY305").

## Estado al cerrar DAY305 (23-oct-2026)

- Rama `feat/heads-switch` (8 commits, de `57466e12` a `f036bd57`). EMECAS+++ `PROFILE=production` desde cero:
  28/28, rc=0, 2h04m, con los cinco E2E del laboratorio en PASA (`logs/lab/emecas/emecas_20261023_112031.log`).
  PR abierta contra main. Tras el merge: etiqueta `pre-release-heads-switch-0.0.6`.
- **Modelo (decisión de Alonso):**
  - El sniffer recoge rasgos SIEMPRE y su única cabeza es el fast-path (`fast_detector.enabled`: alerta por
    paquete y ventanas de ransomware).
  - La inferencia de las cabezas vive solo en el ml-detector, con un `enabled` por cabeza.
  - Regla de `enabled`: booleano o texto true/false sin distinguir mayúsculas; si falta o es inválido, apagada con
    `[CONFIG-DEFAULT]`.
  - Línea `[HEADS]` al arrancar y cada `monitoring.heads_log_interval_seconds`.
  - Laboratorio: solo ddos_v2 encendida, fast-path apagado.
- Retirada del sniffer la inferencia duplicada (`run_ml_detection`, unos 20 µs por evento que se tiraban).
  Cerradas DEBT-HEADS-SWITCH-001 y DEBT-SNIFFER-RANSOMWARE-STOP-RACE-001.
- Pruebas: `heads_config.hpp` y `test_heads_config` en ml-detector y sniffer (71 comprobaciones cada uno).
  Regresión ddos_v2 (`lab-e2e-protegidos`): FIN 10 770 de .50, 5384 alertas de .61 protegido, identidad exacta,
  0 del inocente.
- Parcheadores del día en `scripts/heads/`.

## Reglas de trabajo (las de siempre)

Medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR. Comandos exactos y
completos, en orden, diciendo dónde se ejecuta cada uno (Mac / defender / client), con la salida redirigida a
fichero + `; cat`. Ficheros generados como descarga con sha256. Parcheadores que validen TODO antes de escribir
NADA (anclas únicas, sha256 de los bloques que se borran, marca de idempotencia, `--check`/`--apply`). `git grep`,
nunca `grep -rn .` en la raíz. awk con `LC_ALL=C`. El JSON es la ley; ningún campo se lee en silencio. Compilar
siempre en producción y el pipeline completo (`make pipeline-build PROFILE=production`). Diagnósticos del
compilador: `grep -E ':[0-9]+:[0-9]+: (warning|error):'` (no `error|warning`, que caza `-Werror`). Pruebas:
`make test-components PROFILE=production`. E2E: `make lab-e2e-protegidos LAB_E2E_DIA=dayNNN` (unos 10 min) o
`make lab-e2e` (los cinco). `vagrant up` sin nombre solo levanta el defender: `vagrant up client`, y después
`make lab-clock-step`. No se mantiene código deprecado: se borra; la historia de git lo conserva.

## Lecciones de DAY305

- **Antes de poner un interruptor, medir qué hace de verdad lo que se va a apagar.** El sniffer ejecutaba cabezas
  que nadie sabía que corrían allí, y tiraba el resultado.
- **Un interruptor que solo cambia un mensaje es peor que no tenerlo** (`fast_detector.enabled`,
  "Ransomware Detection: DISABLED").
- **Leer el fichero entero antes de afirmar.** Con fragmentos di por ocurrido un "ATTACK" fantasma que no ocurría.
- **Patrones de búsqueda en logs del build:** CMake escribe rutas relativas (`ml-detector.dir/src/x.cpp.o`).

## Orden decidido por Alonso

1. **Retirar la cabeza DDoS v1 entera** (DEBT-DDOS-V1-RETIRE-001), para que no interfiera con ddos_v2:
   - ml-detector: DDoSDetector, ddos_trees_inline.hpp, el bloque `ml.level2.ddos` del JSON, su paso en
     zmq_handler y el `test_detectors` que la compila;
   - sniffer: los rasgos v1 del recolector (packet_symmetry, source_ip_dispersion, protocol_anomaly,
     amplification, geo, escalation, saturation);
   - protobuf: los campos se marcan como obsoletos, sin reutilizarlos.
   Inventario primero, midiendo quién nombra y quién cuenta.
2. **Caducidad de flujos** (DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001). Medir primero la RAM
   por flujo con la tabla llena, y la batería de la etapa 2 antes y después.
3. **Rama RAG Logger del ml-detector** (DEBT-RAG-LOGGER-BRANCH-001).
4. **Residuos del repo** (DEBT-REPO-RESIDUOS-001, ampliada DAY305).
5. **REA, al final.**

Pendiente sin bloquear: la medida de herramienta (CPU con todo apagado frente a solo ddos_v2, coste de `populate`
por evento y tamaño del protobuf), que decide si la recogida selectiva de rasgos merece la pena
(DEBT-ETCD-REMOTE-ADMIN-001).
