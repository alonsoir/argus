# PROMPT DE CONTINUIDAD — DAY 213 → 214
## Rama `fix/verdict-multihead-honest` · Fase 2 del veredicto multicabeza

> Memoria de sesión. Claude no recuerda entre ventanas. Fuente de verdad del PLAN
> sigue siendo el PLAN, no este fichero — aquí sólo el estado operativo de la rama.

---

## ⚠️ AL ABRIR — ESTADO DE CIERRE DAY 213

**1b-extract COMMITEADO y CERTIFICADO.** Nada pendiente de anoche.
- Commit `05f1c263` en rama `fix/verdict-multihead-honest` (NO merge a main).
- `make test-all`: 13/13 verde.
- `make emecas+++`: PASSED (circuito bronce->Kuzu verificado, test_bronze_to_kuzu_circuit).
- El watch-point del adapter bronce->gold quedó DESPEJADO para el extract: la
  sección interna nueva en flujos internos-benignos NO rompió el circuito.

**PRIMERA ACCIÓN HOY: arrancar 1b-hoist.** Decisión (a) ya tomada (abajo). No hay
que re-auditar 1b-extract. Sanity opcional antes de empezar:
```
git -C ml-detector log --oneline -2     # confirmar 05f1c263 (1b-extract) presente
git -C ml-detector status --short        # árbol limpio salvo lo que empieces a tocar
```

---

## DÓNDE ESTAMOS: commit 1b-extract HECHO (05f1c263) — test-all 13/13 + EMECAS+++ verdes

**Rama:** `fix/verdict-multihead-honest`. **NO mergeada a main.** Acumula
1a + 1b-extract; faltan 1b-hoist + commit 2 antes del merge. `docs/BACKLOG.md` y
`README.md` se actualizan AL MERGE, no antes (decisión Alonso DAY 212).

**Los 5 ficheros de 1b-extract (staged anoche, verificados en índice):**
- `ml-detector/include/ml_defender/traffic_head_logic.hpp` (nuevo)
- `ml-detector/tests/unit/test_traffic_head_logic.cpp` (nuevo)
- `ml-detector/tests/CMakeLists.txt` (registra los 2 tests en ctest)
- `ml-detector/include/zmq_handler.hpp` (include + declaración run_traffic_head)
- `ml-detector/src/zmq_handler.cpp` (método run_traffic_head + call_site)

**Mensaje del commit 05f1c263 (ya aplicado):**
```
refactor(ml-detector): extraer cabeza traffic a run_traffic_head + test (1b-extract)

- traffic_head_logic.hpp: build_traffic_features (mapeo puro de 10 índices,
  espejo de internal_head_logic), lanza invalid_argument si size!=10.
- run_traffic_head: observador puro, registra level3_traffic_pred y devuelve
  Prediction. Comportamiento byte-idéntico al bloque inline, incluido el doble
  contador de error (feature_extraction + inference vía re-throw).
- Llamada en el MISMO sitio dentro del gate L1 (guard estricto conservado).
  El hoist fuera del gate es 1b-hoist, commit aparte.
- test_traffic_head_logic: 29 asserts (mapeo, tamaño, is_internal/is_internet).
- tests/CMakeLists.txt: registra test_traffic_head_logic Y test_internal_head_logic
  en ctest (el de 1a existía pero nunca corría en test-all — cabo cerrado hoy).
- test-all 13/13 verde: neutralidad del extract certificada. NO merge a main.
```

### Verificación de 1b-extract (hecha DAY 213)
- `ctest -R head`: test_traffic_head_logic 29/29 + test_internal_head_logic 25/25
- `make test-all`: 13/13 ALL TESTS COMPLETE (11 preexistentes + 2 nuevos)
- Neutralidad: los 11 tests previos siguen verdes idénticos.

### Qué hace 1b-extract (estructura, no comportamiento) — espejo del patrón de 1a
1. **traffic_head_logic.hpp** — `build_traffic_features(vector<float>) ->
   TrafficDetector::Features`. Mapeo puro de los 10 índices (0=packet_rate ...
   9=temporal_consistency). Lanza `invalid_argument` si size != 10.
2. **test_traffic_head_logic.cpp** — 29 asserts. NO usa GTest: main() propio +
   macro CHECK (return 1 al fallo). Enlaza traffic_detector.cpp.
3. **run_traffic_head(nf, ml_analysis) -> optional<TrafficDetector::Prediction>**
   (~línea 331, ANTES de run_internal_head). Extrae → build_traffic_features →
   predict → registra level3_traffic_pred → devuelve Prediction. NO decide.
   **Preserva el DOBLE contador de error**: feature_extraction_errors (re-throw)
    + inference_errors (catch externo). NO unificado con run_internal_head (que
      sólo cuenta inference_errors) — distintos en main, el extract los respeta.
4. **Call site** (dentro del gate L1): la llamada sustituye al bloque inline EN EL
   MISMO SITIO. Guard estricto `if (traffic_detector_ && web.enabled)` conservado.
   Sellado interno (is_internal → run_internal_head → SUSPICIOUS_INTERNAL) INTACTO.
5. **tests/CMakeLists.txt** — registró en ctest AMBOS head tests. HALLAZGO DAY 213:
   el test de 1a existía pero NUNCA estaba en ctest — el "25/25" de DAY 212 fue el
   g++ suelto, no test-all. Ahora ambos corren vía test-components → ctest.

### Detalles técnicos que ahorran tiempo
- Retorno confirmado contra header real: `TrafficDetector::Prediction`
  {class_id, probability, internet_prob, internal_prob} + is_internal/is_internet.
- Test aislado (Mac) contra traffic_detector.cpp REAL:
  `cd ml-detector && g++ -std=c++20 -O2 -I include -I include/ml_defender \
   tests/unit/test_traffic_head_logic.cpp src/traffic_detector.cpp -o /tmp/test_thl && /tmp/test_thl`
- ctest en VM: $ML_DETECTOR_BUILD_DIR NO existe en shell remota. Ruta literal:
  `vagrant ssh -c "cd /vagrant/ml-detector/build-debug && ctest -N"` (PROFILE=debug).
  `ctest -N` lista sin ejecutar — prueba anti-|| del test-components (que traga
  fallos de registro con `|| echo "No ml-detector tests configured"`).
- Los 13 tests: 11 preexistentes + test_traffic_head_logic (#12) + test_internal_head_logic (#13).
- Build: `make ml-detector` (reconfigura cmake + compila). Máquina: VM `defender` (x86), repo /vagrant.

---

## PRÓXIMO: commit 1b-hoist — sacar las cabezas del gate L1

**Objetivo:** mover `run_traffic_head` + `run_internal_head` FUERA del gate L1,
para que corran en TODOS los flujos. Pago real de la Fase 2: el interno empieza a
ver los flujos BENIGN-para-L1 y `internal_l1_discrepancies` mide el hueco de verdad.

### Decisión ya tomada (DAY 213): OPCIÓN (a)
Saca del gate L1 pero MANTIENE el guard `is_internal` sobre run_internal_head. El
interno corre en flujos internos que L1 marcó benigno — NO en externos. Contador
interpretable. Lo externo (y "L1 misclasifica interno como externo") es OTRA
instrumentación, a su propio backlog, NO se mezcla en internal_l1_discrepancies.

### Estructura del corte (post-1b-extract)
```
auto traffic_result = run_traffic_head(nf, ml_analysis);   // FUERA del gate, corre siempre
bool is_internal = traffic_result &&
                   traffic_result->is_internal(config_.ml.thresholds.level3_web);
std::optional<InternalDetector::Prediction> internal_pred;
if (is_internal) {                                          // (a): guard INTERNAL conservado
    internal_pred = run_internal_head(nf, label_l1, ml_analysis);
}
if (label_l1 == 1 && confidence_l1 >= level1_attack) {      // gate L1 INTACTO
    ... ddos, ransomware ...
    if (is_internal) {
        if (internal_pred && internal_pred->is_suspicious(...)) {  // SELLADO se queda
            event.set_threat_category("SUSPICIOUS_INTERNAL"); ...
        }
    }
} else {
    event.set_threat_category("NORMAL");                   // benigno; las llamadas YA corrieron arriba
}
```
Interno L1-attack: byte-idéntico a extract. Interno L1-benigno: llamadas disparan
arriba (contador sube), veredicto cae al else NORMAL. CONSERVADOR: correr izado,
decidir congelado. El veredicto lo escucha commit 2.

### Anclas para 1b-hoist (re-anclar con grep — números desplazados por el extract)
```
grep -n 'run_traffic_head(nf, ml_analysis)' src/zmq_handler.cpp
grep -n 'level1_attack' src/zmq_handler.cpp
grep -n 'set_threat_category("NORMAL")' src/zmq_handler.cpp
```

### Asimetría anotada (NO bloquea 1b-hoist, alinear en commit 2)
run_internal_head recibe label_l1 pero NO confidence_l1. El contador mide
"L1-benigno" = label_l1 != 1. Pero el else NORMAL se alcanza si label_l1 != 1 O
confidence_l1 < level1_attack. En el borde (L1 attack, confianza baja → NORMAL) el
contador lo ve como no-discrepancia. Para el paper (Camino A): o se anota como
definición consciente ("hueco = discrepancia de CLASE, no de confianza") o se pasa
confidence_l1 a run_internal_head en commit 2. NO meter la firma nueva en 1b-hoist.

### Tests de contorno OBLIGATORIOS en 1b-hoist (los 4)
1. Interno lateral/exfil, L1 BENIGN → internal_l1_discrepancies SUBE.
2. Ese mismo flujo → veredicto sigue NORMAL, final_threat_classification ≠
   SUSPICIOUS_INTERNAL. **FRONTERA conservador/agresivo — sin ella un sellado
   accidental pasa en verde.**
3. Interno L1-attack → sella SUSPICIOUS_INTERNAL, idéntico a extract (hot path intacto).
4. EXTERNO con features lateral/exfil → run_internal_head NO se llama, contador NO
   sube. **Blinda (a): si quitan el guard, se pone rojo.**

### WATCH-POINT EMECAS+++ para 1b-hoist (leer ANTES de los 79 min)
Al des-gatear, run_traffic_head corre en TODOS los flujos → el informe
TricapaMLAnalysis gana sección de traffic en flujos EXTERNOS y L1-BENIGN que hoy no
la tienen. Pega contra el adapter bronce→gold (DAY 199-208). Rojo probable en la
etapa de CIRCUITO, no en el detector. Corrección correcta: TOLERAR la sección en el
adapter (commit 2 con noisy-OR producirá informes aún más ricos), NO gatear el
registro dentro de run_traffic_head (hack + DEBT).
NOTA: este mismo watch-point aplica en menor grado a 1b-extract — con el extract
sólo los flujos internos-benignos ganan sección interna nueva; con el hoist se
extiende a externos. Si el EMECAS+++ de anoche (extract) salió rojo en circuito,
el hoist lo agravaría — resolver el adapter ANTES del hoist.

---

## DESPUÉS: commit 2 — noisy-OR (el que mata el monocapa)
Reemplazar el `if` de sellado por combinador: `P = 1 − ∏(1 − pᵢ)`,
`pᵢ = fiabilidad_i · score_crudo_i`.
- ransomware/ddos entran con fiabilidad ≈0 (features rotas auditadas): honesto, no
  envenenan. Reconectar post-FEDER = cambiar 1 peso de config.
- Tests OBLIGATORIOS: (a) una cabeza dispara; (b) dos corroboran; (c) cabeza
  fiabilidad-0 NO envenena.
- Aquí se alinea la asimetría label_l1/confidence_l1 (pasar confidence_l1 a las cabezas).
- Paper (Camino A): tricapa→monocapa como HUECO DE COBERTURA, nunca como
  divergencia predicha con Suricata/Zeek.

---

## HOUSEKEEPING PENDIENTE (al merge o cuando apetezca)
- SUMMARY de tests/CMakeLists.txt: verificado DAY 213, rótulos correctos
  (CSV pipeline / correlation_v1 golden / verdict multihead cada uno el suyo).
- `git rm` del proto_aligned con su DEBT (`git ls-files | grep proto_aligned`).
- Anexar DAY 212-213 al PLAN DE CAMPAÑA (fuente de verdad — Alonso, no regenerar).
- Al MERGE: docs/BACKLOG.md (marcar 1a/1b-extract en DEBT-VERDICT-MONOCAPA-001)
    + README.md DAY-STATUS.
- Los 19 duplicados históricos de BACKLOG.md → DEBT-DOCS-BACKLOG-DEDUP-002.
- Umbral level3_internal: cuando entre noisy-OR, revisar si el umbral duro encima
  del combinador distorsiona.
- "Tricapa" en protobuf::TricapaMLAnalysis sobrevive aunque el veredicto sea
  monocapa. Renombrar = terremoto post-FEDER. NO tocar.

---
## MÉTODO (confirmado DAY 213 — funcionó otra vez)
- ENTENDER primero, EXTRAER a función pura + test, y SÓLO ENTONCES mover. El
  extract es cambio con red (comportamiento idéntico verificable); el hoist es
  cambio real. Separarlos hace que los defectos salgan en terreno seguro. DAY 213:
  el doble contador, el guard estricto, y los tests fuera de CI salieron TODOS
  durante el extract, ninguno a mitad de cirugía. Más legible, más entendible,
  mejor ingeniería.
- Medir, no votar: grep de la función entera, balance de llaves antes de cortar,
  ver el bloque completo antes de tocar. Números de línea se DESPLAZAN — re-anclar
  con grep de texto.
- El test que no corre es PEOR que el que falla (el que falla se ve). Verificar con
  `ctest -N` que el test está REGISTRADO, no sólo que el fichero existe. El
  `|| echo "No tests configured"` de test-components traga fallos de registro.
- Reescribir limpio > operar lo malo. Cambios pequeños y verificables > cirugía grande.
- macOS BSD (no GNU). $ML_DETECTOR_BUILD_DIR no existe en shell remota — ruta literal.
- Editar tras `git add` desincroniza el índice — re-add + `git status --short`
  (columna derecha vacía) antes de commitear. Mordió 2 veces DAY 213.
- FEDER go/no-go ~August 1, 2026; deadline September 22, 2026.