# DAY306 — Retirada de la cabeza DDoS v1 (DEBT-DDOS-V1-RETIRE-001)

Rama `feat/ddos-v1-retire`, desde main con el merge de DAY305 (`9dcf014e`). Marca en el código: `[DDOS-V1-RETIRE-D306]`.
Herramientas del día en `scripts/ddos_v1/`.

## Por qué

La cabeza DDoS v1 (bosque sintético de 9 rasgos, detrás de level1) estaba apagada desde DAY305, pero su código, su
configuración, sus campos del proto y su manivela de entrenamiento seguían en el repo. ddos_v2 es la única cabeza
entrenada y certificada. Decisión de Alonso: retirar todo lo que use la v1, respetar lo que use la v2 y, por ahora,
lo que usen las demás cabezas (ransomware, traffic, internal), que están apagadas a sabiendas porque se reescribirán
desde cero.

## Inventario medido (antes de tocar nada)

`inventario_ddos_v1_d306.sh` (quién nombra cada símbolo, por clase de fichero) y `lectura2_d306.sh` (cruces y, para
cada candidato a borrar, si lo cita el paper y quién más lo usa). Predicciones que NO se cumplieron y cambiaron el plan:

- La compuerta `l2_gate` / `FORCE_ALL_HEADS` no era solo de la v1: abre también ransomware, traffic e internal. Se
  queda. ddos_v2 no pasa por ella (corre en todo evento de flujo).
- `source_ip_dispersion` no tenía un segundo significado con ese nombre: solo lo consumía la v1. Alonso: si la v2 no
  lo usa, no tiene sentido capturarlo. Fuera.
- Más restos de los previstos: el CSV del ml-detector escribía los diez rasgos v1 como columnas 76-85.

Hallazgos de la lectura completa:

- Quitar el bloque del JSON a secas tumbaba el ml-detector por dos sitios: `config_loader` (`get_required`) y
  `etcd_client.cpp:155`, donde `operator[]` sobre un JSON no constante crea un null y `value()` lanza.
- El CSV elegía la predicción level2 por POSICIÓN (0 = DDoS, 1 = ransomware). Con ddos_v2 en la posición 0, la v1
  caía en la columna de ransomware. Ahora elige por `model_type`.
- Ninguno de los 40 ficheros borrados de `ml-training`, `models` y la raíz lo nombra código vivo ni lo cita el paper
  (`docs/latex/main.tex`, `docs/paper/v26-pre.tex`).

## Commits

| # | Commit | Qué |
|---|---|---|
| 1 | `349a3a63` | ml-detector: fuera `DDoSDetector`, `ddos_trees_inline.hpp`, el extractor v1, su paso en zmq_handler y `ml.level2.ddos` / `thresholds.level2_ddos`. `[CONFIG-OBSOLETO]` si un JSON aún los trae (el ml-detector arranca igual). `[HEADS]` sin `ddos_v1`, `[DETECCIONES]` sin `ddos`, `[HEAD-SCORES]` con `ddos_v2`. CSV por `model_type`. Dataset DDoS v2: `old_ddos_*` = -1. `test_detectors` con traffic e internal. |
| 2 | `1195f91a` | Proto: `reserved 2, 3, 4, 6, 8, 9, 10` y los siete nombres. Sniffer sin los siete extractores ni sus centinelas. CSV: columnas 77-79, 81 y 83-85 vacías hasta la rama del RAG Logger. Tests y herramientas sintéticas sin campos v1. `.pb.*` y `_pb2.py` regenerados con `make proto`. |
| 3 | `dfa5e0b1` | `sniffer.json` sin el bloque `fast_detector.ddos` PLANNED (nadie lo leía). **Por un error de orden en los comandos, este commit lleva también los 40 borrados** (ver abajo). |
| 4 | `76cecd17` | Makefile (fuera la firma de `xgboost_ddos.ubj` en `sign-models` y el target `ddos-regen`) y `.gitignore`. Su mensaje describe los 40 borrados, que en realidad entraron en el commit 3. |
| 5 | — | Este documento, el BACKLOG y el prompt de DAY307. |

**Erratum de los commits 3 y 4.** `git rm` mete los borrados en el índice en el acto. Los comandos de Claude pedían
`git rm` antes del commit 3, así que el commit 3 (`dfa5e0b1`) se llevó los 40 borrados con un mensaje que solo habla
de `sniffer.json`, y el commit 4 (`76cecd17`) solo lleva Makefile y `.gitignore`, con un mensaje que describe los
borrados. El contenido de la rama es el correcto; lo que no casa es qué mensaje describe qué cambio. No se reescribe
la historia: queda anotado aquí y en la PR.

## Verificación

- Cada parcheador valida todo antes de escribir: sha256 de cada fichero de partida, anclas únicas, sha256 de cada
  bloque borrado, estado "ya aplicado" reconocido. Los tres dieron `[OK]` a la primera.
- Compilación `pipeline-build PROFILE=production` y `tools-build`: 0 diagnósticos en los dos commits de código.
- `test-components PROFILE=production`: 100 % (82/82 en la suite grande).
- `.pb.h` regenerado: 0 apariciones de `packet_symmetry`; los campos v2 presentes.
- Regresión `lab-e2e-protegidos` (ddos_v2), PASA en las tres corridas:

| Corrida | FIN (DROP de .50) | Alertas .61 | Identidad |
|---|---|---|---|
| tras commit 1 | 10 765 | 5383 | exacta |
| tras commit 2 | 10 778 | 5388 | exacta |
| tras commits 3 y 4 | 10 753 | 5377 | exacta |

Referencia de corridas previas: DAY303 10 782 / 5391, DAY305 10 770 / 5384, ocho corridas de EMECAS 10 741-10 787 /
5369-5393. Las tres de hoy caen dentro.

## Lecciones

- **Una regresión de replay se predice como rango, no como identidad.** Predije "idéntico a DAY305" y salió 5 por
  debajo; la comparación con las corridas guardadas mostró que el replay varía ±25 entre corridas. La predicción
  correcta era "dentro de [10 741, 10 787] / [5369, 5393]".
- **`git rm` toca el índice al momento.** Si hay que partir borrados y ediciones en commits distintos, el `git rm` va
  justo antes del commit que debe llevarlos, no antes.
- **Leer el fichero entero sigue mandando.** Los dos puntos que habrían tumbado el ml-detector (`etcd_client` y el
  cargador) solo aparecían leyendo los ficheros completos, no en los conteos del inventario.
- **En el Mac, `cat -A` no existe** (BSD): `cat -vet`.

## Deudas que deja o abre

- DEBT-DDOS-V1-RETIRE-001: CERRADA (pendiente EMECAS+++ y merge).
- DEBT-PROTO-CONTRACTS-SPLIT-001 (nueva, Alonso): contratos protobuf propios sniffer→ml-detector y
  ml-detector→firewall, para repartir la carga; el contrato actual quedará deprecado. Rama propia, más adelante.
- DEBT-DDOS-V2-PINNED-ENV-001 (nueva): `ml-training/requirements-ddos-pinned.txt` lo instala el Vagrantfile; su
  comentario habla del sha de la manivela v1 (`56f0c5ae`). Medir con qué entorno se entrena la v2
  (`export_ddos_v2_fact_rf.py`) y reescribir el comentario o el pin.
- DEBT-REPO-RESIDUOS-001 (ampliada): `tools/generate_synthetic_events` y los targets `day38-step2/3` (escriben a
  `logs/rag/`, RAG retirado); scripts de análisis que parsean formatos de log viejos (`scripts/d279_*`,
  `scripts/d282_head_scores.sh`, `join_flood_escalation*.py`); parcheadores históricos de la raíz;
  `run_crank_sandbox.sh` (sin trackear, en disco local).
- Documentación desfasada (rama del RAG Logger): `ml-detector/docs/feature_schema.md` y los comentarios de
  `csv_event_writer.hpp` describen las columnas v1; `contract_validator.cpp` resume "40 embedded (4x10)".
