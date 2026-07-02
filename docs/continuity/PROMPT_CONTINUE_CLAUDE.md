# PROMPT DE CONTINUIDAD — DAY 204 (continúa DAY 203)
# Instrucciones generales para Claude:

1. Piensa antes de codificar
   Expón tus suposiciones. Pregunta cuando no estés seguro. Nunca adivines.

2. Simplicidad primero
   Escribe el código mínimo que resuelva el problema.
   Sin abstracciones que nadie pidió.

3. Cambios quirúrgicos
   No toques código no relacionado con la solicitud.
   Cada línea cambiada debe rastrearse hasta lo que se pidió.

4. Ejecución orientada a metas
   Convierte instrucciones vagas en criterios de éxito verificables
   antes de escribir una sola línea.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable durable y verificable; Kuzu = proyección reconstruible).
- **EMECAS++** antes de cualquier merge · **PR obligatorio**.
- **Consejo de Sabios** (8 modelos) ratifica decisiones de arquitectura.
- Python3 heredoc (lectura→memoria→escritura) para editar ficheros en macOS · NUNCA `sed -i` · `vagrant ssh -c` para comandos del VM · commits/push desde el HOST.
- Un día, una batalla. Features pequeñas (días, no semanas), merge frecuente a main vía EMECAS++.

## Estado al cierre de DAY 203 — Eslabón 0 CERRADO (3/3 sub-features, merge a main)

**DAY 203 fue una sesión larga (06:00–14:11) y productiva.** Tres PRs pequeños, cada uno su propio EMECAS++ verde, merge inmediato a main:

1. **DAY 201** — `correlation_writer.base_dir` desde JSON (mitad WRITER de `DEBT-CONFIG-BRONZE-HARDCODE-001`). Merged.
2. **DAY 202** — `correlation-engine` deriva `bronze_root` desde `correlation_engine.json` nuevo (mitad READER de la misma deuda). JSON con esqueleto completo (component/node_id/profiles/etcd) para crecimiento incremental — solo `bronze.root_dir` consumido hoy. Merged.
3. **DAY 203** — Bronce SEGMENTADO + escritura atómica `.tmp→rename` + `BronzeDirWatcher` (inotify puro, `IN_MOVED_TO`) en el reader. Cierra `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`. Merged (`aa74dcd0..6808e847`).

**Diseño DAY 203 (verificado en VM real, no solo en teoría):**
- Writer: cada segmento `<fecha>-<HHMMSS-apertura>.csv`, escrito a `.csv.tmp`, cerrado+renombrado atómicamente al rotar. Rotación por **tiempo absoluto desde apertura** (`correlation_writer.rotation_seconds`, JSON, default **30s** — valor elegido explícitamente para el prototipo del Eslabón 0, ver nota de Alonso: "esto es para asegurar que todo funciona con una aproximación basada en leer ficheros del FS estando las dos ramas en el mismo FS"; en producción real, componentes en intranets distintas del servidor central, el valor sube).
- Reader: `BronzeDirWatcher` nuevo en `correlation-engine` (NO enlaza rag-ingester — reescrito desde cero calcando el patrón de `CsvDirWatcher` de rag-ingester, pero con semántica distinta: `IN_MOVED_TO` sobre segmentos ya inmutables, no `IN_MODIFY`+offset sobre un fichero que nunca se cierra). Modo directorio nuevo (replay de segmentos existentes + `--follow` con watcher bloqueante) coexiste con el modo legacy `--bronze`/`ARGUS_BRONZE_CSV` explícito, que queda **intacto** — compatibilidad total con tests/scripts existentes.
- **Verificado en corrida real de EMECAS++:** segmentos rotando cada ~30-70s bajo carga sintética (la variación por encima de 30s es esperada: `rotate_if_needed()` solo se evalúa al llegar un evento nuevo, no hay timer independiente — anotado, no es bug). Cero fallos de rename atómico en el log. 3 `.tmp` huérfanos al final de la corrida, esperados (proceso detenido a media escritura).

**Hallazgo importante DAY 203 (no bloqueante, pero real):** al verificar por qué EMECAS++ pasaba verde tras un cambio de arquitectura de rotación tan grande, se descubrió que `test_correlation_roundtrip.cpp` (en `ml-detector/tests/integration/`) **existe como fuente pero nunca estuvo enganchado a ningún `add_test`** — ni antes ni después de este cambio. No es una regresión introducida hoy; es una laguna de cobertura preexistente que nadie había verificado. Registrada como `DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001` (P1) en `docs/BACKLOG.md`.

## Acciones DAY 204 (en orden)

1. **Revisar y actualizar tests.** Con el cambio de arquitectura de bronce (fichero único por día → segmentos rotados), verificar si algún test existente (`correlation-engine` GTest suite: `test_correlation_reader`, `test_graph_sink_loop`, `test_kuzu_graph_sink`, `test_cypher_prepared`) tiene supuestos implícitos sobre el formato de fichero de bronce que convenga actualizar o reforzar explícitamente contra el formato nuevo (`<fecha>-<HHMMSS>.csv`).
2. **Cerrar `DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001`** — enganchar `test_correlation_roundtrip.cpp` con `add_test` en `ml-detector/tests/CMakeLists.txt`, verificar que corre dentro de `test-all`/`test-components`, PASSED contra el bronce segmentado.
3. **Evaluar si EMECAS++ necesita un protocolo nuevo (EMECAS+++, propuesto por Alonso DAY 203).** EMECAS/EMECAS++ validan "¿compila y pasan los tests de cada componente?" (mirada hacia el software de los componentes). El circuito que se está construyendo (adapters → bronce → LZ → Kuzu → dashboard) necesita además "¿fluye el dato extremo a extremo por el río?" — el test E2E que define ADR-058 §1 (inyectar evento sintético, verificar HMAC en bronce, verificar `MATCH` en Kuzu, fallar si cualquier paso cae). Decidir si esto se formaliza ya como target `make emecas+++` o se difiere hasta tener el primer tramo de Eslabón 1 vivo.
4. **Poner al día `docs/BACKLOG.md`** — marcar como CERRADAS las entradas DAY200 correspondientes a `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` y `DEBT-CONFIG-BRONZE-HARDCODE-001` (Eslabón 0 las cierra ambas). Revisar si `rotation_seconds` merece nota propia de "valor de prototipo, no de producción" en la entrada correspondiente.
5. **Poner al día `README.md`** — sección DAY-STATUS, hitos del día, tabla de estado global (Eslabón 0 pasa de 0% a 100%).
6. **Higiene pendiente, no bloqueante:** limpiar basura en `/vagrant/logs/correlation/argus` de sesiones anteriores al patrón segmentado (`2026-06-*.csv`, `2026-07-01.csv` sin sufijo de hora) — vive en carpeta compartida host↔VM, `vagrant destroy` no la toca. Considerar si merece un target `make clean-logs` o similar.
7. **Después de 1-4:** decidir si se abre ya Eslabón 1 (Landing Zone / Flujo A: bronce→AVRO→Parquet oro) o si primero conviene consolidar EMECAS+++ como gate formal antes de construir más río abajo.

## Deudas cerradas DAY 203
- `DEBT-CONFIG-BRONZE-HARDCODE-001` (P0) — CERRADA (DAY 201 + DAY 202, writer + reader).
- `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` (P0) — CERRADA (DAY 203, segmentación + watcher).

## Deudas abiertas nuevas DAY 203
- `DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001` (P1) — `test_correlation_roundtrip.cpp` sin `add_test`, laguna preexistente expuesta hoy.
- (nota, no formal aún) higiene `/vagrant/logs/correlation/argus` — basura de sesiones anteriores al patrón segmentado.
- (nota, no formal aún) posible `make emecas+++` — gate E2E río-abajo, ver acción 3.

## Rama
`main`, al día (`6808e847`). Sin rama de trabajo abierta — DAY 204 empieza limpio.

## Punteros
- `ml-detector/include/correlation_writer.hpp` + `.cpp` — segmentación, `finalize_segment_locked()`, rename atómico.
- `correlation-engine/include/correlation_engine/bronze_dir_watcher.hpp` + `.cpp` — watcher inotify nuevo.
- `correlation-engine/src/main.cpp` — modo directorio vs modo legacy, `process_segment()` compartido.
- `ml-detector/tests/integration/test_correlation_roundtrip.cpp` — existe, huérfano, objetivo DAY 204 acción 2.
- `docs/BACKLOG.md` — `DEBT-CORRELATION-ROUNDTRIP-ORPHANED-001` recién añadida.

*Via Appia Quality — Un escudo que aprende de su propia sombra.*