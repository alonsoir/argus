#!/usr/bin/env bash
# Regenera el artefacto DDoS de 9 features (sin geo) y verifica las puertas.
# Corre DENTRO de la VM defender (deps: numpy/sklearn/pandas del provisioning).
# No ensucia el repo: toda la cadena vive en un scratch temporal.
#
# Camino A (DAY256): puertas duras = censo GO + diff contra header trackeado.
# El sha se REPORTA, no aborta — la garantía viva es el censo, no el sha,
# hasta que se pinnee el entorno (DEUDA-DDOS-REPRO-PIN).
set -euo pipefail

DDOS_DIR=/vagrant/ml-training/scripts/ddos_detection
DDOS_HPP=/vagrant/ml-detector/include/ml_defender/ddos_trees_inline.hpp
DDOS_SHA=56f0c5ae8640cde93c213130cc26752500c4affa72a455f8d9b1fb468cf9bc68

scratch=$(mktemp -d /tmp/ddos-regen.XXXXXX)
trap 'rm -rf "$scratch"' EXIT
echo "[regen] scratch=$scratch"
cd "$scratch"

python3 "$DDOS_DIR/SyntheticDDOSGenerator.py"
python3 "$DDOS_DIR/DDosModelTrainer.py"
python3 "$DDOS_DIR/GenerateDDOSCPPForest.py" ddos_detection_model.pkl ddos_trees_inline.hpp

# Puerta 1 (dura, portable): invariante semántico. Imprime su tabla antes de fallar.
python3 "$DDOS_DIR/census_ddos_splits.py" ddos_trees_inline.hpp \
  --sentinel geographical_concentration

# Puerta 2 (aviso): bit-exactness contra el sha publicado. NO aborta en Camino A.
got=$(shasum -a 256 ddos_trees_inline.hpp | cut -d' ' -f1)
echo "[regen] sha=$got"
[ "$got" = "$DDOS_SHA" ] && echo "[regen] sha coincide con el publicado" \
                         || echo "[regen] sha DIVERGE del publicado — esperable si cambió el entorno; ver censo"

# Puerta 3 (dura): lo que hay en el repo == lo que produce la manivela.
diff -q ddos_trees_inline.hpp "$DDOS_HPP" \
  || { echo "[regen] header trackeado != regenerado — NO-GO"; exit 1; }

echo "[regen] GO — censo + diff-trackeado (sha informativo)"
