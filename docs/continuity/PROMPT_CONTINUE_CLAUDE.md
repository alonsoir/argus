# PROMPT DE CONTINUIDAD — DAY 215 → 216
## Rama `fix/verdict-multihead-honest` · commit 2 (noisy-OR) EN STASH

> Memoria de sesión. Claude no recuerda entre ventanas. Fuente de verdad del PLAN
> sigue siendo el PLAN, no este fichero — aquí sólo el estado operativo de la rama.

---

## ⚠️ AL ABRIR — LO PRIMERO

**DAY 215 NO cerró commit 2. Cerró algo más grande: un P0 que llevaba ~200 días vivo.**

Rama LIMPIA y VERDE en `8e03a264` (pusheado). Sanity antes de tocar nada:
```
git -C ml-detector log --oneline -3        # 8e03a264 (config P0) sobre 12ae89f7 (1b-hoist)
git -C ml-detector status --short          # árbol limpio
git -C ml-detector stash list              # DEBE aparecer stash@{0}: commit2-noisy-or WIP
make test-all                              # 15/15
```

**🔴 EL STASH ES EL PUNTO DE RETOMADA. NO LO PIERDAS.**
`stash@{0}: On master: commit2-noisy-or WIP` contiene DOS ficheros ya escritos y
validados con `g++ -std=c++20 -Wall -Wextra -Werror` (todos los checks verdes):
- `ml-detector/include/ml_defender/verdict_decision_logic.hpp` — con `HeadSignal`,
  `combine_noisy_or`, `L3VerdictInputs` reescrito (P + umbral en vez de bool), y
  `SUSPICIOUS_INTERNAL_LABEL` + `[[nodiscard]]` conservados.
- `ml-detector/tests/unit/test_verdict_decision_logic.cpp` — contornos de 1b-hoist
  REEXPRESADOS + checks del combinador (incluido el CRÍTICO: fiabilidad-0 no envenena).

**PRIMER COMANDO DEL DÍA:**
```
git -C ml-detector stash pop
make ml-detector          # ROMPERÁ en zmq_handler.cpp:828 — ES LO ESPERADO
```
Ese error ES el punto de retomada: `process_event` todavía construye
`L3VerdictInputs` con el campo `internal_is_suspicious`, que ya no existe.

---

## 🔥 EL HALLAZGO DE DAY 215 — DEBT-CONFIG-L3-THRESHOLDS-UNPARSED-001 (P0, CERRADO)

**`config_loader.cpp` parseaba 4 de los 6 umbrales.** `level3_web` y `level3_internal`
estaban en el struct y en el JSON, pero NUNCA se leían del disco. Con
`DetectorConfig config;` (default-init, floats sin NSDMI) quedaban INDETERMINADOS.

**MEDIDO EN EJECUCIÓN REAL:**
```
level3_web      = 0
level3_internal = 1.09486e+27
```

Consecuencias, durante ~200 días:
- `is_internal(0.0f)` → SIEMPRE true. Guard de traffic abierto: TODO flujo era "interno".
- `is_suspicious(1.09e27)` → NUNCA true. Ninguna probabilidad ∈ [0,1] lo supera.
- **`SUSPICIOUS_INTERNAL` no se selló JAMÁS en la historia del proyecto.**
- Basura de pila ⟹ **no reproducible** entre ejecuciones. El detector no era determinista.

Sobrevivió a 13 tests y a EMECAS+++ porque **ningún test verificaba que el config
llegara del disco al struct**. Esa era la pieza que faltaba desde el principio.

**Fix (commit `8e03a264`):** los 2 `get_required` + `DetectorConfig config{}` +
`print_config` + **test #15 `test_config_thresholds`** (test de PROPIEDAD, no espejo:
toda clave del JSON debe llegar al struct y coincidir; umbral fuera de [0,1] = rojo).
RED→GREEN verificado: JSON sin la clave → `exit=134`; JSON con 0.42 → PASSED.

---

## 🩸 TRES DEUDAS NUEVAS ABIERTAS POR ESTE HALLAZGO

**1. DEBT-VERDICT-WEIGHTS-CALIBRATION-001 — la auditoría de señal NO VALE.**
Traffic 4/10 e Internal 8/10 se midieron con `level3_web=0` (guard abierto) y
`level3_internal=1.09e27` (umbral inalcanzable). Esos números miden cabezas rotas,
no la calidad de los modelos. **Los pesos de fiabilidad del noisy-OR NO pueden
derivarse de ellos.** Arrancar con pesos PROVISIONALES documentados como tales y
recalibrar cuando las cabezas hayan corrido con umbrales reales.

**2. EMECAS+++ es VERDE NO INFORMATIVO para el veredicto.**
Tras el fix: EMECAS verde y `correlation_v1_golden.tsv` SIN MOVERSE. No es
confirmación. El bronce (`correlation_writer_->write_record`) se escribe **ANTES**
del gate L1, luego el veredicto L3 nunca cruza a `correlation_v1`. Medido tres veces
independientes: (a) contrato de 19 columnas, (b) orden de `process_event`,
(c) columna 14 `threat_category` = `RAW_CAPTURE` 4/4 (valor que pone el sniffer).
⟹ **Si tocas el veredicto, el golden NO te va a avisar. La única red es el unit test.**
Reordenar la escritura del bronce = COMMIT PROPIO (el golden se moverá, legítimamente).

**3. `SUSPICIOUS_INTERNAL` = 0 sellados TRAS el fix. SIN EXPLICAR.**
Puede ser correcto (el set sintético quizá no tiene tráfico interno sospechoso) o
puede seguir roto. **No lo sabemos.** Falta un contador que lo haga observable.

---

## PRÓXIMO: commit 2 — noisy-OR. Lo que queda, en orden

### PASO 1 — `reliability` + `l3_combined_seal` al config
Los pesos NO son umbrales: sección **hermana** de `thresholds` (criterio Alonso:
*"cada umbral leído para su trabajo específico"*).
```json
"thresholds": { ..., "l3_combined_seal": 0.65 },
"reliability": { "traffic": ?, "internal": ?, "ddos": 0.0, "ransomware": 0.0 }
```
- `ddos`/`ransomware` a **0.0**: features rotas (DEBT-RANSOMWARE-ML-HEAD-INERT-001).
  Entran HONESTAS y no envenenan: `1 − 0·score = 1` = factor neutro. Reconectarlas
  post-FEDER = cambiar UN peso, sin tocar código.
- `traffic`/`internal`: **DECISIÓN PENDIENTE** (ver deuda 1 — los 4/10 y 8/10 no valen).
- `l3_combined_seal` con **nombre propio**: reutilizar `level3_internal` como umbral
  del combinador es incorrecto — ese umbral ya se aplica ARRIBA, dentro de
  `run_internal_head` (`zmq_handler.cpp:408`), sobre la señal de UNA cabeza. Aplicarlo
  otra vez sobre una P combinada es el MISMO número haciendo DOS trabajos en escalas
  distintas.
- **⚠️ El struct `thresholds` NO tiene inicializadores por defecto.** Añadir campos sin
  añadir el `get_required` = el bug de hoy otra vez. **AHORA hay red:** el test #15
  detecta la clave huérfana. Extiéndelo con las claves nuevas.

### PASO 2 — el corte en `process_event:828`
```cpp
const bool traffic_internal = traffic_result &&
    traffic_result->is_internal(config_.ml.thresholds.level3_web);

const std::array<ml_defender::HeadSignal, 2> heads{{
    {w_traffic,  traffic_result ? traffic_result->probability    : 0.0f},
    {w_internal, internal_pred  ? internal_pred->suspicious_prob : 0.0f},
}};
const float p = ml_defender::combine_noisy_or(heads);

const auto l3_decision = ml_defender::decide_l3_verdict({
    .l1_gate_open         = true,
    .traffic_is_internal  = traffic_internal,
    .internal_ran         = internal_pred.has_value(),
    .combined_probability = p,
    .seal_threshold       = config_.ml.thresholds.l3_combined_seal,
});
```
- **VERIFICAR los nombres reales** de los campos de `Prediction` (`probability`,
  `suspicious_prob`) — no están confirmados con `file:line`.
- **ddos/ransomware NO se izan hoy.** `ddos_result` (:720) y `ransomware_result` (:789)
  viven dentro de su `try`/`else` dentro del gate: NO son visibles en :828. Con
  fiabilidad 0 su score da igual. Cuando se reconecten: **izado primero (con red,
  comportamiento idéntico), combinador después. NUNCA en el mismo commit.**

### INVARIANTE DE DISEÑO (ya en el header, no romper)
**La P gobierna la FUERZA de la evidencia, NUNCA la ETIQUETA.** `traffic_is_internal`
sigue siendo condición NECESARIA para sellar `SUSPICIOUS_INTERNAL`: un flujo externo
con P alta NO puede auto-etiquetarse como interno. Hay un check dedicado a esto.

### ALCANCE — lo que NO entra en commit 2
- **L1 sigue siendo GATE, no cabeza.** Meter `p_L1` en el producto mientras L1 cierra
  la puerta = **L1 vota dos veces** (portero y votante), infla P sistemáticamente.
- **PERO** (posición Alonso, DAY 215, y es sólida): el gate es una **optimización
  prematura**. Sólo se justifica si L1 es excepcional, y eso **se gana con datos**.
  Argumento demoledor descubierto hoy: **1b-hoist ya sacó traffic e internal fuera del
  gate.** Lo único que queda DETRÁS del gate es ddos/ransomware — las cabezas rotas
  cuyo score se descarta. **El gate ya no ahorra nada. Es un vestigio.**
  ⟹ Retirar el gate + unificar todas las cabezas a escalar = **ADR + Consejo**, no commit.
- **`confidence_l1`:** decisión CONGELADA — el hueco es discrepancia de **CLASE**
  (`label_l1 != 1`), no de confianza. Anotado en el header. Para el paper (Camino A).
- **`correlation_v2`** (telemetría por cabeza al grafo): ver abajo.

---

## 🎯 VISIÓN ALONSO (DAY 215) — TRANSPARENCIA ABSOLUTA. Post-commit-2.

Toda la telemetría conjunta debe llegar al grafo: score + etiqueta de CADA cabeza
(incluido fast-path), no sólo el veredicto. *"Mejor saber para poder reconstruir."*
El admin del hospital no se fía: **recalcula**.

**El invariante que esto regala (más fuerte que un golden — no compara, REDERIVA):**
> Dada la telemetría del grafo, recalcular `combine_noisy_or` debe reproducir la P
> almacenada, bit a bit. Si no cuadra: falta una señal, o el peso escrito no es el
> que se usó, o alguien tocó el combinador sin tocar el bronce.

Es también **reproducibilidad del paper**: *"nuestros datos permiten rederivar cada
decisión del detector"* es una afirmación científica falsable. Hospital y revisor de
Cornell quieren lo mismo. No hay tensión entre rigor y decencia — es el mismo eje.

**⚠️ SIN VERSIONADO DE PESOS, EL INVARIANTE ES FALSO.** Los pesos viven en config y
los admins pueden cambiarlos. El día que `ransomware.reliability` pase de 0.0 a 0.6
(el plan post-FEDER), **todas las filas históricas se recalcularían mal**. Decisión
Alonso: **viaja `config_version` / `model_set_id` en la fila**, y los pesos se resuelven
por versión desde un **registro INMUTABLE**.
⚠️ etcd es el registro **VIVO** (mutable, con rotación de epochs). Puede distribuir el
config y sellar el `config_version`, pero **el archivo inmutable histórico es OTRA COSA**
(se parece al golden set versionado de ADR-040). **NO fundir ambos en el ADR.**

**LA VENTANA NO EXISTE — hay que decirlo.** `MLContext` tiene
`window_start = now-30s`, `window_end = now`, **`events_in_window = 1` hardcoded**.
La noisy-OR de hoy combina **las cabezas de UN evento**, no eventos entre sí. El
recálculo POR EVENTO es viable y es un test real. El recálculo POR VENTANA requiere
definir qué es una ventana y cómo se agregan eventos (¿noisy-OR? ¿max? ¿decay?).
**No existe. ADR aparte, post-FEDER.** Si se intenta meter en v2, v2 no llega a agosto.

**Coste real de `correlation_v2`:** contrato nuevo (19 columnas planas hoy) + migración
de `bronze_to_gold_converter` + golden regenerado + vocabulario unificado de etiquetas.
Es la pieza que puede comerse el margen antes del **1 de agosto**.

---

## 📄 PAPER — decisión DAY 215

**El hallazgo del config SE CUENTA.** Decisión Alonso: *"es mejor ser honesto que no
serlo; el paper cuenta cómo estamos construyendo esto tratando de ser buenos científicos"*.
- No es "llevamos un año con un bug". Es: **dos defectos independientes producían el
  mismo síntoma** (veredicto sellado antes de tiempo POR ARQUITECTURA + umbral L3
  indeterminado POR CONFIG), y se encontraron **midiendo, no votando**.
- Contar sólo la causa arquitectónica y callar la del config sería dar **una causa de
  dos**, con el commit `8e03a264` público en el repo. La omisión dolería más.
- Encaja con §6 (gate RED→GREEN, libFuzzer 2.4M runs): es el caso de estudio de por qué
  el testing convencional no basta — un umbral silencioso que sobrevive 200 días de verde.

---

## HOUSEKEEPING PENDIENTE
- `print_config` imprime los umbrales L3 **dentro de `if (verbose)`**, y el arranque real
  usa `verbose=false` ⟹ **siguen sin verse**. La defensa real es el TEST, no el print.
  Sacarlos fuera del `if` = commit propio (decisión de UX de arranque).
- `config_loader.hpp.backup` (Nov 2025): **NO trackeado**. Basura local, `rm` a secas.
- `git rm` del `proto_aligned` con su DEBT (`git ls-files | grep proto_aligned`).
- Anexar DAY 215 al PLAN DE CAMPAÑA (fuente de verdad — Alonso, no regenerar).
- Al MERGE: `docs/BACKLOG.md` (1a/1b-extract/1b-hoist/config-P0 en
  DEBT-VERDICT-MONOCAPA-001) + `README.md` DAY-STATUS.
- Los 19 duplicados de BACKLOG.md → DEBT-DOCS-BACKLOG-DEDUP-002.
- `protobuf::TricapaMLAnalysis` mantiene "Tricapa" aunque el veredicto sea monocapa.
  Renombrar = terremoto post-FEDER. NO tocar.
- **Falsable, sin medir:** ¿`OnnxModel::predict` (`onnx_model.hpp:16`,
  `std::pair<int64_t,float>`) devuelve la probabilidad de la clase GANADORA o siempre la
  de clase 1? Si es lo segundo, `label=ATTACK && confidence<0.5` es posible y es un bug.
  Está en el `.cpp`, no en la firma. No bloquea.

---
## MÉTODO (DAY 215 — cuatro días seguidos, y hoy pagó a lo grande)
- **ENTENDER primero, medir con `file:line`, y SÓLO ENTONCES mover.** DAY 215: el noisy-OR
  no se cerró porque al ir a leer el umbral de sellado, el rastro del parseo NO EXISTÍA.
  Construirlo encima habría dado una P que parece correcta, con tests verdes, sobre
  cabezas que nunca supieron dónde estaba su frontera. **Mismo patrón que el ransomware
  inerte: el pipeline funcionando, produciendo números, sin significado.**
- **El verde hay que interrogarlo, no celebrarlo.** EMECAS+++ pasó verde tras cambiar el
  comportamiento de dos cabezas. Ese verde NO significaba "no rompiste nada": significaba
  "el golden no mira donde tocaste". Preguntar SIEMPRE: *¿qué mediría este verde si el
  cambio fuera malo?*
- **El test que nunca ha estado ROJO es una hipótesis, no una red.** Test #15 se validó
  rompiendo el JSON a propósito (`exit=134`) y cambiando el valor a 0.42 (PASSED, sigue
  al fichero y no a un literal). RED→GREEN o no vale.
- **Test de PROPIEDAD > test de ESPEJO.** `level3_web == 0.6f` se rompe al cambiar el
  valor y no caza nada. *"Toda clave del JSON llega al struct"* caza la clase entera.
- **La función pura paga tres veces:** `decide_l3_verdict` hizo el hoist verificable,
  hace commit 2 localizado, y `combine_noisy_or` se validó con `g++` suelto en el Mac
  sin montar medio sistema.
- **Ausencia de evidencia ≠ evidencia de ausencia.** `grep level3_internal` en `src/`
  devolvía USOS, no asignaciones. Ahí estaba el bug, a la vista, durante 200 días.
- **CUANDO EL CONSEJO DA CÓDIGO, EXIGIRLE EL `file:line` DE LO QUE DICE HABER LEÍDO.**
  DAY 215, Claude cometió dos errores: (a) afirmó haber compilado un test que no había
  ejecutado; (b) reescribió `verdict_decision_logic.hpp` **sin haberlo leído nunca**,
  destruyendo `SUSPICIOUS_INTERNAL_LABEL` y `[[nodiscard]]`. **Los cazó el compilador,
  no Claude.** El Consejo alucina con confianza: verificar SIEMPRE.
- **zsh, no bash.** `ml-detector/*.cpp` sin matches ⟹ **aborta el comando ENTERO** (el
  `grep` nunca corrió y pareció "no hay resultados"). macOS es **BSD**: `cat -A` no existe
  (usar `cat -e`). Nunca `sed -i` sin `-e ''`; Python3 heredoc para editar.
- **`#` NO es comentario para git.** `git status --short   # comentario` → el comentario
  entra como argumento y el output miente.
- **`ctest -N` confirma REGISTRO, no EXISTENCIA** ("Could not find executable" es normal
  antes de compilar). Y **CMake hay que reconfigurar** (`cmake .`) para que un test nuevo
  aparezca. El `|| echo "No tests configured"` de test-components traga fallos de alta.
- NO hacer `make` entre ediciones encadenadas con estado transitorio. Aplicar el juego
  completo y ENTONCES compilar.
- Editar tras `git add` desincroniza el índice (AM) — re-add + columna derecha vacía.
- Commits limpios: código y docs de continuidad en commits SEPARADOS.
- heredoc entrecomillado (`<<'EOF'`) para mensajes de commit con símbolos (→ ∧ ⟹).
- FEDER go/no-go ~1 agosto 2026; deadline 22 septiembre 2026.