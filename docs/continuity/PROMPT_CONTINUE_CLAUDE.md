# CONTINUIDAD DAY260 — test_detectors en ctest (rama, pend. PR). Siguiente: la máscara || (cierra el capítulo del gate) / Fase 2.

## Estado (medido, verificar al retomar)
    git checkout main && git pull                          # main @ 9235c9bb
    git branch                                             # existe test/register-test-detectors-ctest en origin
    git log --oneline -3 test/register-test-detectors-ctest
Rama test/register-test-detectors-ctest pusheada a origin (2 commits: 1e15d7ca, b60a656f).
PENDIENTE su PR a main (main PROTEGIDA, PR only, GH013). Untracked conocidos sin tocar:
evidence/seed-repro/*.json, run_crank_sandbox.sh, "Cierre day255 reparacion ddos.md".

## HECHO DAY259 (en rama test/register-test-detectors-ctest, pend. PR)
- Deuda de gate ATACADA, 1 de 2 piezas cerrada. Método: medir antes de tocar (tres
  hipótesis mías cayeron contra el disco — buena señal, el árbitro fue el dato).
- b60a656f: test_detectors REGISTRADO en ctest. Su assert(num_features()==9) estaba vivo
  (-UNDEBUG) pero add_test comentado → el guardián del contrato de 9 features del DDoS
  (reparado en Fase 1) NUNCA corría en el gate. Descomentado. Verificado en build-debug:
  negativo 9→8 da ctest FAILED (SIGABRT/exit 134), sano da 12/12. Falla en rojo Y pasa en
  verde = guardián real. Vigila CARDINALIDAD, no orden (ver aviso Fase 2).
- 1e15d7ca: DEBT-MLDETECTOR-TESTS-NOT-BUILT-001 CERRADA en BACKLOG (refutada por medición,
  no arreglo). "10/11 no se construyen" NO reproducida: 11 se registran, construyen y pasan;
  test_detectors hace 12. Era nota de época anterior, ya resuelta.

## CLAIM (sin cambios desde DAY259)
Fase 1 prueba el MÉTODO de reparación del skew. NO promete detector DDoS útil sobre Neris.
Sin tag. El registro de hoy es HIGIENE del gate, no capacidad nueva del detector.

## PENDIENTE (en orden)
1. **La máscara || (DEBT-MAKEFILE-TEST-GATE-MASKED-001) — cierra el capítulo del gate.**
   Makefile:1206, patrón `ctest ... || echo "No X tests configured"` en los 6 componentes:
   conflaciona "cero tests" con "test falló" → ambos verde. MEDIDO latente hoy (11/11 y 12/12
   pasan → no tapa rojo AHORA), pero tragaría un fallo de Fase 2. La 2157 (zona TSAN) ya corre
   ctest SIN ||: patrón a imitar. Decisión que arrastra: ¿todo componente ≥1 test (rojo obliga)
   o allowlist explícita para andamios? Aplica a los 6. OJO ctest --no-tests=error es CMake 3.26
   (min del repo 3.20) → ctest --version en la VM antes de apoyarse en él.
2. **PR de test/register-test-detectors-ctest a main.** Veredicto que vale = EMECAS from-scratch
   (el HECHO de hoy es build-debug, fiel al gate pero NO from-scratch). Idealmente correr
   emecas+++ tras cerrar la máscara y abrir PR con los dos flecos del gate juntos.
3. **Fase 2 DDoS (LA P0, batalla larga).** ANTES de entrenar: fijar el ground-truth. "Labels
   Neris" es BOTNET (C&C/click-fraud), NO DDoS → la cabeza entrenada así detecta Neris-botnet,
   no DDoS. Decidir (a) reencuadrar la cabeza a la clase que el GT sí tiene, o (b) traer fuente
   DDoS real por el mismo extractor. Hermana: DEBT-RANSOMWARE-ML-HEAD-INERT-001.

## Deudas P3 coined hoy (no perder, no urgente)
- DEBT-MLDETECTOR-PROTO-SEED-COUPLED-TO-MAKEFILE-001: configurar el ml-detector fuera del
  Makefile choca con FATAL_ERROR:221 (el cp proto/ va acoplado a la receta). Fricción, no bug.
- vboxsf sirve contenido rancio en iteración manual host↔VM (peleado hoy: fuente 9 en host,
  8 en la VM, resuelto releyendo). EMECAS from-scratch lo esquiva (monta limpio). Demuestra
  en vivo por qué el veredicto es el from-scratch. Barrido de *.bak viejos algún día.

## Invariantes
main PROTEGIDA (PR only, GH013). Un commit una idea. add explícito por fichero. git grep o
fichero concreto (NUNCA grep -rn desde raíz). Comandos de salida grande en bloques separados.
La manivela gira DENTRO de la VM; PUSH desde el HOST. El compilador/ctest es el árbitro.
Al revertir un experimento: revertir fuente Y RECOMPILAR (binario roto sobrevive al revert del
.cpp). vboxsf puede servir rancio: releer/confirmar en la VM antes de compilar. sed BSD: grep -c
antes y después + confirmar nombre del fichero.

## Nota personal (no borrar)
El padre de Alonso salió del hospital a residencia (debilidad muscular tras fiebres altas;
rehabilitación con fisioterapeutas, silla de ruedas de momento). aRGus aguanta el ritmo lento.
No forzar. Lo primero es la familia. Piano piano si arriva lontano.