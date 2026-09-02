#!/usr/bin/env bash
#
# verify_seed_repro.sh — Paso 1 (semilla): PRUEBA de reproducibilidad del generador DDoS.
#
# Que hace (todo READ-ONLY sobre el repo; nunca toca el dataset trackeado):
#   1. Verifica que el parche de semilla esta presente en SyntheticDDOSGenerator.py.
#   2. Comprueba que el generador compila.
#   3. Regenera el dataset DOS veces, en procesos SEPARADOS, a un dir de evidencia.
#   4. Valida la estructura de cada salida (guarda contra "falso verde").
#   5. Compara shasum de las dos corridas.
#   6. Escribe un manifiesto con procedencia (rama, HEAD, sha del generador, versiones).
#   7. Informa GO / NO-GO. NO commitea: el commit lo decides tu.
#
# Uso:
#   ./verify_seed_repro.sh [GEN_DIR] [N]
#     GEN_DIR: dir con SyntheticDDOSGenerator.py
#              (def: ml-training/scripts/ddos_detection)
#     N:       n_samples de entrada para la prueba (def: 5000).
#              El determinismo es INDEPENDIENTE de N; se usa un N modesto para que sea rapido.
#
set -euo pipefail

GEN_DIR="${1:-ml-training/scripts/ddos_detection}"
N="${2:-5000}"
GEN_FILE="${GEN_DIR}/SyntheticDDOSGenerator.py"
EVID_DIR="${GEN_DIR}/evidence/seed-repro"

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
grn()  { printf '\033[32m%s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }

echo "== verify_seed_repro =="
info "generador: ${GEN_FILE}"
info "N (entrada): ${N}"

# -- 0) existencia
if [[ ! -f "${GEN_FILE}" ]]; then
  red "[NO-GO] No existe ${GEN_FILE}"; exit 2
fi

# -- 1) parche presente (scoped al fichero, salida corta)
if ! grep -q 'np.random.seed(42)' "${GEN_FILE}"; then
  red "[NO-GO] Falta 'np.random.seed(42)' en el generador. Aplica primero el parche."; exit 3
fi
if ! grep -q 'random_state=42' "${GEN_FILE}"; then
  red "[NO-GO] Falta 'random_state=42' en el shuffle. Aplica primero el parche."; exit 3
fi
grn "[1/5] Parche de semilla presente."

# -- 2) compila
if ! python3 -m py_compile "${GEN_FILE}"; then
  red "[NO-GO] El generador no compila."; exit 4
fi
grn "[2/5] Generador compila."

# -- procedencia
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'sin-git')"
GIT_HEAD="$(git rev-parse --short HEAD 2>/dev/null || echo 'sin-git')"
GEN_SHA="$(shasum -a 256 "${GEN_FILE}" | awk '{print $1}')"
GEN_SHA_SHORT="${GEN_SHA:0:12}"
TS="$(date +%Y%m%d_%H%M%S)"
VERS="$(python3 -c 'import numpy,pandas; print("numpy",numpy.__version__,"pandas",pandas.__version__)')"

mkdir -p "${EVID_DIR}"
OUT1="${EVID_DIR}/dataset_${GIT_HEAD}_${GEN_SHA_SHORT}_${TS}_run1.json"
OUT2="${EVID_DIR}/dataset_${GIT_HEAD}_${GEN_SHA_SHORT}_${TS}_run2.json"

# -- driver de generacion (importa la clase; no depende de un __main__ desconocido)
run_gen() {
  local out="$1"
  GEN_DIR_ABS="$(cd "${GEN_DIR}" && pwd)" OUT="${out}" N="${N}" python3 - << 'PYDRV'
import os, sys
gen_dir = os.environ["GEN_DIR_ABS"]; out = os.environ["OUT"]; n = int(os.environ["N"])
sys.path.insert(0, gen_dir)
from SyntheticDDOSGenerator import DDOSSyntheticGenerator
DDOSSyntheticGenerator(n_samples=n).save_dataset(out)
PYDRV
}

# -- 3) dos corridas en procesos separados
grn "[3/5] Regenerando (run1)..."; run_gen "${OUT1}"
grn "        Regenerando (run2)..."; run_gen "${OUT2}"

# -- 4) validacion estructural (anti falso-verde)
validate() {
  OUT="$1" python3 - << 'PYVAL'
import json, os, sys
p = os.environ["OUT"]
if os.path.getsize(p) == 0:
    print("vacio"); sys.exit(1)
d = json.load(open(p))
mi = d.get("model_info", {})
fn = mi.get("feature_names") or []
ds = d.get("dataset") or []
if not fn or not ds:
    print("estructura incompleta"); sys.exit(1)
if mi.get("n_features") != len(fn):
    print("n_features != len(feature_names)"); sys.exit(1)
print(f"ok {len(ds)} filas, {len(fn)} features")
PYVAL
}
V1="$(validate "${OUT1}")" || { red "[NO-GO] run1 malformado: ${V1}"; exit 5; }
V2="$(validate "${OUT2}")" || { red "[NO-GO] run2 malformado: ${V2}"; exit 5; }
grn "[4/5] Estructura valida (run1: ${V1} | run2: ${V2})."

# -- 5) comparacion de shasum
SHA1="$(shasum -a 256 "${OUT1}" | awk '{print $1}')"
SHA2="$(shasum -a 256 "${OUT2}" | awk '{print $1}')"

MANIFEST="${EVID_DIR}/manifest_${GIT_HEAD}_${TS}.txt"
{
  echo "verify_seed_repro — manifiesto de procedencia"
  echo "timestamp     : ${TS}"
  echo "git_branch    : ${GIT_BRANCH}"
  echo "git_head      : ${GIT_HEAD}"
  echo "generador     : ${GEN_FILE}"
  echo "generador_sha : ${GEN_SHA}"
  echo "n_samples_in  : ${N}"
  echo "versiones     : ${VERS}"
  echo "run1          : ${OUT1}"
  echo "run1_sha256   : ${SHA1}"
  echo "run2          : ${OUT2}"
  echo "run2_sha256   : ${SHA2}"
  echo "match         : $([[ "${SHA1}" == "${SHA2}" ]] && echo SI || echo NO)"
} > "${MANIFEST}"

echo
if [[ "${SHA1}" == "${SHA2}" ]]; then
  grn "[5/5] GO — regeneraciones IDENTICAS."
  info "sha256: ${SHA1}"
  info "manifiesto: ${MANIFEST}"
  echo
  grn "===================== GO ====================="
  info "Reproducibilidad conquistada. Siguiente (a mano):"
  info "  1) git add ${GEN_FILE}"
  info "  2) git commit -m \"fix(ddos): semilla fija en generador (reproducibilidad de artefacto, DAY255)\""
  info "  3) (opcional) commitear el manifiesto como evidencia: git add ${MANIFEST}"
  info "  Los dos dataset de evidencia son regenerables desde la semilla; no hace falta commitearlos."
  exit 0
else
  red  "[5/5] NO-GO — las dos regeneraciones DIFIEREN."
  info "sha1: ${SHA1}"
  info "sha2: ${SHA2}"
  info "Queda una fuente de aleatoriedad sin fijar. NO commitear. Cazarla antes de seguir."
  info "manifiesto: ${MANIFEST}"
  exit 6
fi