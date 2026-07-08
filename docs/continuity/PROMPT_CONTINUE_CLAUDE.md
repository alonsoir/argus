# PROMPT DE CONTINUIDAD — DAY 212 → 213
## Rama `fix/verdict-multihead-honest` · Fase 2 del veredicto multicabeza

> Este fichero es la memoria de sesión. Claude no recuerda entre ventanas; esto
> es lo que necesita para arrancar 1b sin re-auditar. Fuente de verdad para el
> PLAN de campaña sigue siendo el PLAN, no este fichero — aquí sólo el estado
> operativo de la rama.

---

## DÓNDE ESTAMOS: commit 1a CERRADO (triple verde)

**Rama:** `fix/verdict-multihead-honest` (nace de `main` tras PR docs/day211).
**NO mergeada a main.** La rama acumula 1a + 1b + commit 2; merge cuando la
Fase 2 esté entera. `docs/BACKLOG.md` y `README.md` se actualizan AL MERGE, no
antes (ahorro de tokens — decisión Alonso DAY 212).

**Commit 1a — refactor(ml-detector): extraer cabeza interna a run_internal_head
+ lógica pura testeada.** Comportamiento IDÉNTICO al anterior verificado por:
- `test_internal_head_logic`: 25/25 verdes
- `make test-all`: ALL TESTS COMPLETE
- `make emecas+++`: PASSED (circuito bronce→Kuzu, ~79 min)

### Qué hace 1a (estructura, no comportamiento)
El bloque interno (2 `try` anidados, ~59 líneas, enterrado 3 niveles: gate L1 →
cascada traffic → gate confianza) se reescribió limpio en:

1. **`ml-detector/include/ml_defender/internal_head_logic.hpp`** (NUEVO) — lógica
   PURA sin dependencias del handler:
    - `build_internal_features(vector<float>) -> Features` — mapeo de índices.
      Auditado DAY 211: [5]=lateral, [7]=exfil son REALES; [1],[2] constantes.
      Lanza `std::invalid_argument` si size != 10.
    - `evaluate_internal(pred, threshold, int64_t label_l1) -> {suspicious, is_discrepancy}`
      — is_discrepancy = suspicious && L1-dijo-benigno. Métrica central de la DEBT.
    - Es el PATRÓN para las 4 cabezas: lógica pura testeable, handler sólo orquesta.

2. **`ml-detector/tests/unit/test_internal_head_logic.cpp`** (NUEVO) — la red que
   faltaba (ningún test cubría la orquestación del veredicto). 25 asserts:
   mapeo de los 10 índices, validación de tamaño, lógica de discrepancia (4 casos),
   detector real sobre perfil lateral/exfil.

3. **`run_internal_head`** en `zmq_handler.cpp` — observador puro:
   `std::optional<InternalDetector::Prediction> run_internal_head(nf, int64_t label_l1, TricapaMLAnalysis*)`.
   Extrae → mapea (pura) → infiere → registra en informe → cuenta discrepancia.
   Devuelve Prediction (nullopt si no pudo opinar). **NO sella el veredicto.**
   nullopt != benigno (no colapsar "no opinó" con "opinó benigno").

4. **Sellado** (`set_threat_category`/`set_final_threat_classification`) queda en
   `process_event`, leyendo el optional. Idéntico al original. Commit 2 lo
   reemplaza por noisy-OR.

5. **`stats_.internal_l1_discrepancies`** (uint64_t) añadido al struct Stats.
   En 1a NO dispara (la llamada vive dentro del gate → label_l1 siempre 1 ahí).

### Detalles técnicos que mañana ahorran tiempo
- Namespace del proto: `protobuf::` (NO ml_detector::protobuf). Tipo del informe:
  `protobuf::TricapaMLAnalysis` (el nombre "Tricapa" sobrevive aunque el veredicto
  sea monocapa — renombrar es terremoto post-FEDER, anotado, no tocar).
- `label_l1` es **int64_t** (fix -Werror=conversion — la firma pedía int, mal).
- Build: `make ml-detector` (NO `make pipeline-build`, no hace falta reconstruir
  el pipeline entero). Test de lógica compila con:
  `g++ -std=c++20 -O2 -I include -I include/ml_defender tests/unit/test_internal_head_logic.cpp src/internal_detector.cpp -o /tmp/test_ihl`
- EMECAS+++ tarda ~79 min. Correr sólo antes de merge/al cerrar hito, no en cada iteración.
- Máquina de build/test: VM Vagrant `defender` (x86, = producción). Repo en VM: `/vagrant`.
- Backups del corte 1a (por si acaso, borrar cuando la rama esté sólida):
  `.bak_1a` / `.bak_1a_method` / `.bak_1a_cut`.

---

## PRÓXIMO: commit 1b — sacar el interno del gate L1

**Objetivo:** mover la llamada `run_internal_head` FUERA del gate L1 y de la
cascada traffic, para que el interno corra en TODOS los flujos (no sólo cuando
L1 dice ATTACK). Es el pago real de la Fase 2: el interno empieza a ver los
flujos que L1 marca BENIGN, y `internal_l1_discrepancies` empieza a medir el
hueco de cobertura de verdad.

**Coste: ya medido, no bloquea.** Bench DAY 211: extract_level3_internal_features
p99 ~440 ns sobre hardware producción, <0.005% del presupuesto 10ms. `predict`
es pura (<100μs). `nf` preexiste en el evento (event.network_features()).
Des-gatear = "subir la llamada", no "desenredar estado".

### Estructura actual del gate (post-1a, números DESPLAZARON ~48 líneas por la
### inserción del método — RE-ANCLAR con grep, no fiarse de números viejos)
```
if (label_l1 == 1 && confidence_l1 >= level1_attack) {   ← GATE L1
    ... DDoS, ransomware, traffic ...
    if (traffic == INTERNAL) {                            ← CASCADA traffic
        auto internal_pred = run_internal_head(nf, label_l1, ml_analysis);  ← 1a puso esto aquí
        if (internal_pred && internal_pred->is_suspicious(...)) {           ← SELLADO
            event.set_threat_category("SUSPICIOUS_INTERNAL");
            ml_analysis->set_final_threat_classification("SUSPICIOUS_INTERNAL");
        }
    }
} else {
    event.set_threat_category("NORMAL");                 ← el else que entierra al interno
}
```

### Decisión de diseño de 1b (pensar con cabeza fresca — aquí Defecto A y B se tocan)
Al mover la llamada fuera del gate, el interno corre siempre. Pero **¿qué pasa
con el sellado cuando el interno detecta amenaza en un flujo que el `else`
sellaría como NORMAL?**
- Opción conservadora (1b puro): el interno corre y CUENTA la discrepancia
  (contador + warn), pero NO cambia todavía el veredicto. El `else` sigue
  sellando NORMAL. Observable: contador sube en flujos BENIGN-para-L1. Genera el
  dataset del hueco SIN tocar el veredicto. Riesgo mínimo.
- Opción agresiva: el interno ya corrige el veredicto (sella SUSPICIOUS_INTERNAL
  aunque L1 dijera benigno). Esto YA es lógica de veredicto = pertenece al
  commit 2 (noisy-OR), no a 1b. NO hacerlo en 1b.
  **Recomendación:** 1b = opción conservadora. El interno corre siempre + mide el
  hueco. El veredicto lo escucha en commit 2 vía noisy-OR. Separar correr de decidir.

### Pasos de 1b (cuando se retome)
1. `grep -n 'run_internal_head(nf, label_l1, ml_analysis)' zmq_handler.cpp` —
   localizar la llamada actual (dentro del gate).
2. Localizar el cierre del gate L1 y su `else NORMAL` (grep 'set_threat_category("NORMAL")').
3. Mover la llamada + el bloque de sellado a DESPUÉS del if/else del gate
   (fuera, corre siempre). `nf` se toma de `event.network_features()`.
4. El `else NORMAL` se queda (commit 2 lo modifica). En 1b el interno sólo observa.
5. Verificar contador dispara: test/pcap con flujo lateral/exfil que L1 marca BENIGN.
6. `make ml-detector` → test-all → EMECAS+++ → commit 1b en la rama.

---

## DESPUÉS: commit 2 — noisy-OR (el que mata el monocapa)
Reemplazar el `if` de sellado por combinador:
`P = 1 − ∏(1 − pᵢ)`, `pᵢ = fiabilidad_i · score_crudo_i`.
- ransomware/ddos entran con fiabilidad ≈0 (features rotas, auditadas): honesto,
  no envenenan. Reconectarlos post-FEDER = cambiar 1 peso de config.
- Tests del combinador OBLIGATORIOS: (a) una cabeza dispara; (b) dos corroboran;
  (c) cabeza fiabilidad-0 NO envenena.
- Paper (Camino A): narrativa tricapa→monocapa como HUECO DE COBERTURA, nunca
  como divergencia predicha con Suricata/Zeek.

---

## HOUSEKEEPING PENDIENTE (no bloquea 1b, hacer al merge o cuando apetezca)
- `git rm` del `proto_aligned` con su DEBT (localizar: `git ls-files | grep proto_aligned`).
- Anexar DAY 212 al PLAN DE CAMPAÑA (fuente de verdad — Alonso, no regenerar).
- Al MERGE: actualizar `docs/BACKLOG.md` (marcar 1a/1b hechos en DEBT-VERDICT-MONOCAPA-001)
    + `README.md` DAY-STATUS.
- Los 19 duplicados históricos de BACKLOG.md → candidato a DEBT-DOCS-BACKLOG-DEDUP-002.
- Nota (no DEBT aún): el umbral `config_.ml.thresholds.level3_internal` — cuando
  entre el noisy-OR, revisar si el umbral duro encima del combinador distorsiona.

---
## MÉTODO (recordatorio de disciplina que funcionó DAY 212)
- Medir, no votar: greps de la función ENTERA, awk de profundidad de llaves antes
  de cortar, validar fronteras antes de tocar, sanity check de balance de llaves.
- Cambios pequeños y verificables > cirugía grande. Reescribir limpio > operar lo malo.
- Cada cabeza: lógica pura sin dependencias + test de asserts rápidos. Keep it simple.
- Los números de línea se DESPLAZAN tras cada inserción — re-anclar con grep de texto.
- macOS BSD (no GNU): cat -et, no cat -A. /tmp de la Mac ≠ /tmp del sandbox de Claude.