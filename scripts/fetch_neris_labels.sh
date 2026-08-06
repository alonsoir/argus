#!/usr/bin/env bash
# scripts/fetch_neris_labels.sh — DAY 250. Descarga idempotente del binetflow del Neris
# (CTU-13 escenario 1 = CTU-Malware-Capture-Botnet-42, Stratosphere Lab / MCFP, CVUT) a datasets/ctu13/.
# Hermano de fetch_neris.sh: cierra la mitad de LABELS de DEBT-DATASETS-FETCH-NOT-AUTOMATED-001 y
# hace `make bias-report` reproducible desde `vagrant destroy -f && up` (386MB, no va en git).
# Es el argus NetFlow BIDIRECCIONAL con labels Botnet/Normal/Background del paper (Capture 1).
# Se ejecuta DENTRO del guest (client) para usar GNU sha256sum, no el shasum de macOS.
# Invocacion: vagrant ssh client -c "bash /vagrant/scripts/fetch_neris_labels.sh"
set -uo pipefail
DIR="/vagrant/datasets/ctu13"
FILE="$DIR/capture20110810.binetflow"
URL="https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-42/capture20110810.binetflow"
# Pin de integridad. RELLENA con el sha256 de TU copia (medir, no votar):
#   vagrant ssh client -c "sha256sum /vagrant/datasets/ctu13/capture20110810.binetflow"
# y pega aqui el hash. Si Stratosphere sirviera algo distinto, la verificacion fallara adrede.
# sha256sum datasets/ctu13/capture20110810.binetflow
# be09f7f6a06beef0134152dc88bff85f0027db4affe07b3fbe956bbb49be5430  datasets/ctu13/capture20110810.binetflow
SHA256="be09f7f6a06beef0134152dc88bff85f0027db4affe07b3fbe956bbb49be5430"
mkdir -p "$DIR"
verify(){ echo "$SHA256  $FILE" | sha256sum -c - >/dev/null 2>&1; }
if [ "$SHA256" = "RELLENA_CON_SHA256_DE_TU_COPIA" ]; then
  echo "X sha256 sin fijar. Corre:"
  echo "   sha256sum $FILE"
  echo "   y pega el hash en SHA256= dentro de scripts/fetch_neris_labels.sh"
  exit 1
fi
if [ -f "$FILE" ] && verify; then
  echo "OK binetflow ya presente y verificado ($FILE)"
  exit 0
fi
echo "-- descargando binetflow de Stratosphere/MCFP (~386MB) --"
curl -fSL --retry 3 -o "$FILE" "$URL" || { echo "X descarga fallo ($URL)"; exit 1; }
verify || { echo "X sha256 NO casa tras descargar -> borra $FILE y revisa el pin / la fuente"; exit 1; }
echo "OK binetflow descargado y verificado ($FILE)"