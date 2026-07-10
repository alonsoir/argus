# PROMPT DE CONTINUIDAD — DAY 214 → 215
## Rama `fix/verdict-multihead-honest` · Fase 2 del veredicto multicabeza

> Memoria de sesión. Claude no recuerda entre ventanas. Fuente de verdad del PLAN
> sigue siendo el PLAN, no este fichero — aquí sólo el estado operativo de la rama.

---

## ⚠️ AL ABRIR — ESTADO DE CIERRE DAY 214

**1b-hoist COMMITEADO, PUSHEADO y CERTIFICADO.** Nada pendiente de ayer.
- Commit `12ae89f7` en rama `fix/verdict-multihead-honest` (NO merge a main).
- Pusheado a `origin/fix/verdict-multihead-honest` (`1dee11ad..12ae89f7`).
- `make test-all`: **14/14 verde** (13 previos + test_verdict_decision_logic #14).
- `make emecas+++`: **PASSED** (~1:13:10; circuito bronce->Kuzu verificado,
  test_bronze_to_kuzu_circuit). Scan de secretos: limpio.

**WATCH-POINT adapter bronce->gold: MUERTO, MEDIDO DOS VECES.** Ya no es riesgo.
- Primero con `file:line` (mañana DAY 214): CSV forma fija (127 cols, secciones
  rellenas con ceros — csv_event_writer.cpp:395-463) + contrato correlation_v1
  (19 cols, NINGUNA es predicción-por-cabeza — correlation_v1.hpp:64-82) +
  veredicto congelado ⟹ el hoist NO cruza a bronce/gold. La info nueva del hoist
  (level3_traffic_pred, internal_pred) muere en el corte protobuf->Row (to_row,
  "la struct es la frontera donde el protobuf muere"), no hay columna destino.
- Luego empíricamente: EMECAS+++ verde en circuito. El adapter NO se tocó.
- El golden es RED DE SEGURIDAD, no riesgo: si algún día salta rojo en circuito
  tras tocar el veredicto, es un veredicto que se movió = BUG REAL, no falso
  positivo del adapter.

**PRIMERA ACCIÓN HOY: arrancar commit 2 (noisy-OR).** Pero NO cortar a ciegas —
hay 2 preguntas de diseño que resolver ANTES (abajo, "ENTENDER PRIMERO"). Sanity
opcional:
```
git -C ml-detector log --oneline -3     # confirmar 12ae89f7 (1b-hoist) en HEAD
git -C ml-detector status --short        # árbol limpio salvo el prompt de continuidad
```

---

## DÓNDE ESTAMOS: Fase 2 con 1a + 1b-extract + 1b-hoist acumulados

**Rama:** `fix/verdict-multihead-honest`. **NO mergeada a main.** Acumula:
- `1a` — extract cabeza interna a run_internal_head + internal_head_logic.
- `05f1c263` (1b-extract) — extract cabeza traffic a run_traffic_head.
- `12ae89f7` (1b-hoist) — cabezas IZADAS fuera del gate L1 + decide_l3_verdict.

Falta **commit 2 (noisy-OR)** antes del merge. `docs/BACKLOG.md` y `README.md` se
actualizan AL MERGE, no antes (decisión Alonso DAY 212).

### Qué dejó 1b-hoist (12ae89f7) — estructura, para entender el punto de partida de commit 2
Los **5 ficheros**:
- `ml-detector/include/ml_defender/verdict_decision_logic.hpp` (nuevo) — la fn pura.
- `ml-detector/tests/unit/test_verdict_decision_logic.cpp` (nuevo) — 14 checks.
- `ml-detector/tests/CMakeLists.txt` — registra test_verdict_decision_logic (#14).
- `ml-detector/include/zmq_handler.hpp` — include de verdict_decision_logic.hpp.
- `ml-detector/src/zmq_handler.cpp` — izado + sellado vía decide_l3_verdict.

**El corte en process_event (zmq_handler.cpp):**
1. **ARRIBA del gate L1** (~línea 655): run_traffic_head + run_internal_head IZADOS.
   Corren en TODOS los flujos. Guard is_internal conservado (opción a): el interno
   sólo corre en flujos internos, NO externos. Las Prediction se guardan en
   `std::optional traffic_result` e `internal_pred` a scope de gate.
   ```
   std::optional<TrafficDetector::Prediction>  traffic_result;
   std::optional<InternalDetector::Prediction> internal_pred;
   if (traffic_detector_ && web.enabled && event.has_network_features()) {
       const auto& nf = event.network_features();
       traffic_result = run_traffic_head(nf, ml_analysis);
       if (traffic_result && traffic_result->is_internal(level3_web) &&
           internal_detector_ && internal.enabled) {
           internal_pred = run_internal_head(nf, label_l1, ml_analysis);
       }
   }
   ```
2. **DENTRO del gate L1-attack** (~línea 813): SÓLO el sellado, vía la fn pura.
   ```
   const auto l3_decision = decide_l3_verdict({
       .l1_gate_open           = true,   // dentro del gate por construcción
       .traffic_is_internal    = traffic_result && traffic_result->is_internal(level3_web),
       .internal_ran           = internal_pred.has_value(),
       .internal_is_suspicious = internal_pred && internal_pred->is_suspicious(level3_internal),
   });
   if (l3_decision.seal_suspicious_internal) {
       event.set_threat_category("SUSPICIOUS_INTERNAL"); ...
   }
   ```

### La función que commit 2 MODIFICA (verdict_decision_logic.hpp)
```
struct L3VerdictInputs {          // hoy: SÓLO booleanos
    bool l1_gate_open;
    bool traffic_is_internal;
    bool internal_ran;
    bool internal_is_suspicious;
};
struct L3VerdictDecision { bool seal_suspicious_internal = false; ... };

constexpr L3VerdictDecision decide_l3_verdict(const L3VerdictInputs& in) noexcept {
    d.seal_suspicious_internal =
        in.l1_gate_open && in.internal_ran && in.internal_is_suspicious;  // ← commit 2 reemplaza ESTO
    return d;
}
```
- Es PURA, constexpr-evaluable, anclada por test_verdict_decision_logic (14 checks).
- NO re-implementa umbrales: recibe is_internal/is_suspicious YA evaluados por las
  Prediction (fuente de verdad única). Diseño deliberado.
- **AVISO HONESTO (corrección de lo dicho DAY 214):** se dijo "commit 2 reemplaza
  sólo el CUERPO sin tocar process_event". Eso es OPTIMISTA. El noisy-OR necesita
  SCORES CRUDOS, no booleanos → el struct L3VerdictInputs casi seguro CRECE para
  llevar floats (score_i + fiabilidad_i por cabeza). Y si el struct crece, el sitio
  de construcción en process_event TAMBIÉN cambia. No es body-swap limpio. Ver
  "ENTENDER PRIMERO" abajo.

---

## PRÓXIMO: commit 2 — noisy-OR (el que mata el monocapa)

**Objetivo:** reemplazar el `&&` de sellado por combinador probabilístico:
`P = 1 − ∏(1 − pᵢ)`, con `pᵢ = fiabilidad_i · score_crudo_i`.
- ransomware/ddos entran con **fiabilidad ≈0** (features rotas, auditadas
  DEBT-RANSOMWARE-ML-HEAD-INERT-001): honesto, NO envenenan (1 − 0·score = 1, no
  cambian el producto). Reconectar post-FEDER = cambiar 1 peso de config.
- Paper (Camino A): tricapa→monocapa como **HUECO DE COBERTURA**, nunca como
  divergencia predicha con Suricata/Zeek.

### ⚠️ ENTENDER PRIMERO — 2 preguntas de diseño ANTES de cortar (medir, no votar)
El método de ayer (entender → extraer/ajustar puro + test → sólo entonces mover)
funcionó dos días seguidos. Aplicarlo aquí. NO cortar hasta responder estas 2 con
`file:line`, no de memoria:

**PREGUNTA 1 — ¿de dónde salen los 4 scores crudos en el punto de sellado?**
El noisy-OR combina las 4 cabezas (ddos, ransomware, traffic, internal). Pero:
- traffic (`traffic_result->probability`) e internal (`internal_pred->suspicious_prob`)
  están IZADOS → visibles a scope de gate. OK.
- **ddos y ransomware NO fueron izados.** `ddos_result` y `ransomware_result` son
  locales DENTRO de sus try/catch, dentro del gate. ¿Son visibles en el punto de
  sellado (~línea 813)? CASI SEGURO NO — scope limitado a su bloque.
  → grep/leer el scope real antes de decidir. Si no son visibles, commit 2 debe
  CAPTURARLOS a optionals de scope-gate (como se hizo con traffic/internal),
  o el combinador corre DENTRO del bloque donde los 4 existen.
- NOTA: con fiabilidad≈0 para ddos/ransomware, su score da igual (no mueven P).
  Así que una opción CONSERVADORA es: noisy-OR sólo con traffic+internal reales,
  ddos/ransomware entran con fiabilidad 0 literal (ni hace falta su score crudo).
  Eso EVITA tener que izar ddos/ransomware hoy. DECISIÓN DE ALONSO.

**PREGUNTA 2 — ¿el struct L3VerdictInputs crece o se hace uno nuevo?**
noisy-OR necesita floats (score + fiabilidad por cabeza). Opciones:
- (a) Extender L3VerdictInputs con los floats. El sitio de construcción en
  process_event pasa a construir con floats → se toca process_event (poco, pero
  se toca). Honesto: NO es "sólo el cuerpo".
- (b) Struct nuevo `L3NoisyOrInputs` + fn nueva `combine_noisy_or`, y
  decide_l3_verdict queda como está (o se retira). Más limpio conceptualmente,
  pero 2 fns donde había 1.
- Sea cual sea: el umbral level3_internal HOY vive encima del `is_suspicious`. Con
  noisy-OR, revisar si el umbral duro ENCIMA del combinador distorsiona (housekeeping
  ya anotado). El combinador produce una P ∈ [0,1]; el sellado será `P >= umbral`.

### Asimetría label_l1 / confidence_l1 — ALINEAR AQUÍ (estaba diferida a commit 2)
run_internal_head recibe label_l1 pero NO confidence_l1. El contador
internal_l1_discrepancies mide "L1-benigno" = label_l1 != 1. Pero el else NORMAL se
alcanza si label_l1 != 1 O confidence_l1 < level1_attack. En el borde (L1 attack,
confianza baja → NORMAL) el contador lo ve como no-discrepancia.
- Commit 2 es el sitio para: o anotar como definición consciente ("hueco =
  discrepancia de CLASE, no de confianza") para el paper (Camino A), o pasar
  confidence_l1 a las cabezas. DECISIÓN DE ALONSO.

### Tests OBLIGATORIOS en commit 2 (patrón: función pura + test, como DAY 212-214)
Extender/crear el test de la fn pura del combinador. Los 3 del prompt original:
1. **Una cabeza dispara** → P supera umbral → sella.
2. **Dos cabezas corroboran** → P mayor que cualquiera sola (noisy-OR sube).
3. **Cabeza fiabilidad-0 NO envenena** → meter una cabeza con fiabilidad 0 y score
   alto NO cambia P. **ESTE ES EL CRÍTICO** — es lo que hace honesto meter
   ddos/ransomware rotos sin que contaminen. Sin él, un peso mal puesto pasa en verde.
   Además, mantener los 4 contornos de 1b-hoist que sigan aplicando (hot path
   byte-idéntico donde el veredicto no deba cambiar).

### Verificación de cierre (igual que DAY 214)
- `g++ suelto` aislado del test de la fn pura (rápido, Mac).
- Registrar en ctest si es fichero nuevo (`ctest -N` confirma REGISTRO, no existencia).
- `make ml-detector` → `make test-all` (objetivo 15/15 si hay test nuevo) →
  `make emecas+++`. EMECAS debe seguir verde en circuito: el combinador cambia el
  VEREDICTO, no lo que llega a bronce (correlation_v1 sigue sin columna de scores
  crudos). Si el golden salta, es veredicto movido = mirar qué flujo cambió.

---

## HOUSEKEEPING PENDIENTE (al merge o cuando apetezca)
- Umbral level3_internal: con noisy-OR entrando, revisar si el umbral duro encima
  del combinador distorsiona (ver PREGUNTA 2).
- `git rm` del proto_aligned con su DEBT (`git ls-files | grep proto_aligned`).
- Anexar DAY 214 al PLAN DE CAMPAÑA (fuente de verdad — Alonso, no regenerar).
- Al MERGE: docs/BACKLOG.md (marcar 1a/1b-extract/1b-hoist en
  DEBT-VERDICT-MONOCAPA-001) + README.md DAY-STATUS.
- Los 19 duplicados históricos de BACKLOG.md → DEBT-DOCS-BACKLOG-DEDUP-002.
- "Tricapa" en protobuf::TricapaMLAnalysis sobrevive aunque el veredicto sea
  monocapa. Renombrar = terremoto post-FEDER. NO tocar.
- Si commit 2 iza ddos/ransomware: NO mezclar ese izado con el noisy-OR en un solo
  commit. Izado (con red, comportamiento idéntico) primero, combinador después.

---
## MÉTODO (confirmado DAY 214 — funcionó tres días seguidos)
- ENTENDER primero, EXTRAER/AJUSTAR a función pura + test, y SÓLO ENTONCES mover.
  DAY 214: el watch-point que parecía riesgo estructural resultó MUERTO al medirlo
  con `file:line`; sin medir, se habría "tolerado en el adapter" una sección que
  nunca cruza la frontera protobuf->Row. Ausencia de evidencia (grep 'AdapterV1'
  vacío) NO es evidencia de ausencia — se persiguió el nombre real
  (CorrelationWriter / correlation_v1) hasta el header-contrato. El timing ("se
  escribe post-firewall") sugería la respuesta pero NO la probaba; sólo el header
  la cerró.
- La función pura paga dos veces: decide_l3_verdict hizo el hoist verificable sin
  montar medio sistema, y hace commit 2 un cambio localizado en vez de cirugía en
  process_event otra vez.
- Medir, no votar: grep de la función entera, balance de llaves antes de cortar,
  ver el bloque completo antes de tocar. Números de línea se DESPLAZAN — re-anclar
  con grep de texto. Re-anclar SIEMPRE tras cada edición aplicada (el índice y las
  líneas bailan).
- El test que no corre es PEOR que el que falla. `ctest -N` confirma REGISTRO. El
  `|| echo "No tests configured"` de test-components traga fallos de registro.
- NO hacer `make` entre ediciones encadenadas que dejan estado transitorio
  (variables izadas arriba + locales abajo con mismo nombre = shadow, no compila
  bajo -Werror). Aplicar el juego completo de ediciones y ENTONCES compilar.
- Reescribir limpio > operar lo malo. Cambios pequeños y verificables > cirugía grande.
- macOS BSD (no GNU). $ML_DETECTOR_BUILD_DIR no existe en shell remota — ruta
  literal `/vagrant/ml-detector/build-debug`. ctest en VM vía `vagrant ssh -c`.
- Editar tras `git add` desincroniza el índice (AM en status) — re-add + verificar
  columna derecha vacía en `git status --short` antes de commitear.
- Commits limpios: código y docs de continuidad en commits SEPARADOS. El prompt de
  continuidad va en su propio `docs(continuity)` commit, nunca mezclado con el
  refactor.
- macOS heredoc entrecomillado (`<<'EOF'`) para mensajes de commit multilínea con
  símbolos (→ ∧ ⟹) — evita expansión del shell. Nunca `sed -i` sin `-e ''`.
- FEDER go/no-go ~August 1, 2026; deadline September 22, 2026.