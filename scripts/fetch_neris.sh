#!/usr/bin/env bash
# scripts/fetch_neris.sh — DAY 249. Descarga idempotente del pcap Neris (CTU-13 escenario 1,
# = CTU-Malware-Capture-Botnet-42 del Stratosphere Lab / MCFP, CVUT) a datasets/ctu13/.
# Cierra DEBT-DATASETS-FETCH-NOT-AUTOMATED-001: hace `make ctu-start` reproducible desde
# `vagrant destroy -f && up` (el pcap son 56MB, no va en git).
# Se ejecuta DENTRO del guest (client) para usar GNU sha256sum, no el shasum de macOS.
# Invocacion: vagrant ssh client -c "bash /vagrant/scripts/fetch_neris.sh"
set -uo pipefail

DIR="/vagrant/datasets/ctu13"
FILE="$DIR/botnet-capture-20110810-neris.pcap"
URL="https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-42/botnet-capture-20110810-neris.pcap"
# Pin de integridad. RELLENA con el sha256 de TU copia (medir, no votar):
#   vagrant ssh client -c "sha256sum /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap"
# y pega aqui el hash. Si Stratosphere sirviera algo distinto, la verificacion fallara adrede.
# vagrant ssh client -c "sha256sum /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap"
# b89cd5931f62d87ceff266568c97c6e36e56dd0330813cacadbc14a6c5576a36  /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap
SHA256="b89cd5931f62d87ceff266568c97c6e36e56dd0330813cacadbc14a6c5576a36"

mkdir -p "$DIR"

verify(){ echo "$SHA256  $FILE" | sha256sum -c - >/dev/null 2>&1; }

if [ "$SHA256" = "RELLENA_CON_SHA256_DE_TU_COPIA" ]; then
  echo "X sha256 sin fijar. Corre:"
  echo "   sha256sum $FILE"
  echo "   y pega el hash en SHA256= dentro de scripts/fetch_neris.sh"
  exit 1
fi

if [ -f "$FILE" ] && verify; then
  echo "OK Neris ya presente y verificado ($FILE)"
  exit 0
fi

echo "-- descargando Neris de Stratosphere/MCFP (~56MB) --"
curl -fSL --retry 3 -o "$FILE" "$URL" || { echo "X descarga fallo ($URL)"; exit 1; }
verify || { echo "X sha256 NO casa tras descargar -> borra $FILE y revisa el pin / la fuente"; exit 1; }
echo "OK Neris descargado y verificado ($FILE)"