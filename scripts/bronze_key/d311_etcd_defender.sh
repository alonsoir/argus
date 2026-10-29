#!/usr/bin/env bash
# DAY311 [ETCD-REINICIO-D311] ayudante del DEFENDER para d311_reinicio_etcd.sh (instrumento de medida, se commitea).
# Las claves HMAC del bronce se leen del etcd-server SOLO para verificar segmentos con el conversor real; se guardan en
# un directorio solo-root fuera de /vagrant y en la salida solo aparece la huella (8 hex del SHA-256 de la clave, la
# misma que escribe el ml-detector). 'borrar' las elimina.
# Uso: d311_etcd_defender.sh clave A|B | puerto | marcas | copiar DIR OFF_ML OFF_FW OFF_SN OFF_ET |
#      verificar DIR T0 T1 | borrar
set -u
export LC_ALL=C
CLAVES=${CLAVES:-/tmp/d311_claves}
CORR=${CORR:-/vagrant/logs/correlation}
CONV=${CONV:-/vagrant/correlation-engine/build/bronze_to_gold_converter}
LAB=${LAB:-/vagrant/logs/lab}
ETCD=${ETCD:-http://127.0.0.1:2379}
huella() { python3 -I -c 'import hashlib,sys; print(hashlib.sha256(bytes.fromhex(sys.stdin.read().strip())).hexdigest()[:8])'; }
case "${1:-}" in
  clave)
    X=${2:?A o B}
    sudo mkdir -p "$CLAVES" && sudo chmod 700 "$CLAVES" || { echo "[ETCD-D311] FALLA: no creo $CLAVES"; exit 1; }
    J=$(curl -s -m 3 "$ETCD/secrets/ml-detector") || { echo "[ETCD-D311] FALLA: el etcd-server no contesta"; exit 1; }
    K=$(printf '%s' "$J" | python3 -I -c 'import json,sys; print(json.load(sys.stdin).get("key",""))' 2>/dev/null)
    if ! printf '%s' "$K" | grep -q -E '^[0-9a-fA-F]{64}$'; then echo "[ETCD-D311] FALLA: respuesta sin clave de 64 hex"; exit 1; fi
    printf '%s' "$K" | sudo tee "$CLAVES/$X.hex" > /dev/null && sudo chmod 600 "$CLAVES/$X.hex"
    echo "[ETCD-D311] huella_$X=$(printf '%s' "$K" | huella)"
    ;;
  puerto)
    n=$(sudo ss -ltn 2>/dev/null | awk '$4 ~ /:2379$/' | wc -l)
    echo "[ETCD-D311] escuchando_2379=$n"
    ;;
  marcas)
    for f in ml-detector firewall-agent sniffer etcd-server; do
      printf '%s=%s ' "$f" "$(wc -l < "$LAB/$f.log" 2>/dev/null || echo 0)"
    done
    echo "epoch=$(date +%s)"
    ;;
  copiar)
    D=${2:?dir}; mkdir -p "$D" || exit 1
    i=3
    for f in ml-detector firewall-agent sniffer etcd-server; do
      off=${!i:-0}; i=$((i + 1))
      tail -n +"$((off + 1))" "$LAB/$f.log" > "$D/$f.log"
      echo "[ETCD-D311] $f.log: $(wc -l < "$D/$f.log") lineas nuevas"
    done
    ;;
  verificar)
    D=${2:?dir}; T0=${3:?t0}; T1=${4:?t1}
    for X in A B; do sudo test -s "$CLAVES/$X.hex" || { echo "[ETCD-D311] FALLA: falta la clave $X"; exit 1; }; done
    [ -x "$CONV" ] || { echo "[ETCD-D311] FALLA: no existe el conversor $CONV"; exit 1; }
    W=$(mktemp -d)
    O="$D/verificacion.txt"
    echo "# segmento mtime lineas validas_A validas_B clase" > "$O"
    for s in $(ls "$CORR" | grep -E '^argus-.*\.csv$' | sort); do
      m=$(stat -c %Y "$CORR/$s")
      [ "$m" -ge "$T0" ] && [ "$m" -le "$T1" ] || continue
      n=$(wc -l < "$CORR/$s")
      va=0; vb=0
      for X in A B; do
        v=$(sudo cat "$CLAVES/$X.hex" | { read -r k; ARGUS_BRONZE_HMAC_KEY_HEX="$k" "$CONV" "$CORR/$s" "$W/o.avro" "$W/o.parquet" 2>/dev/null; } |
            awk '/filas v/ { print $NF }')
        v=${v:-0}
        if [ "$X" = A ]; then va=$v; else vb=$v; fi
      done
      if [ "$va" -eq "$n" ] && [ "$vb" -eq 0 ]; then c=A
      elif [ "$vb" -eq "$n" ] && [ "$va" -eq 0 ]; then c=B
      else c=MEZCLA; fi
      echo "$s $m $n $va $vb $c" >> "$O"
    done
    rm -rf "$W"
    awk '!/^#/ { n++; c[$6]++; l[$6] += $3
                 if ($6 == "A" && $2 > amax) amax = $2; if ($6 == "B" && (bmin == 0 || $2 < bmin)) bmin = $2 }
         END { printf "[ETCD-D311] segmentos=%d A=%d (filas %d) B=%d (filas %d) MEZCLA=%d (filas %d) orden_A_antes_que_B=%s\n",
               n, c["A"], l["A"], c["B"], l["B"], c["MEZCLA"], l["MEZCLA"],
               (c["A"] > 0 && c["B"] > 0 ? (amax <= bmin ? "si" : "NO") : "n/a") }' "$O"
    ;;
  borrar)
    sudo rm -rf "$CLAVES" && echo "[ETCD-D311] claves borradas de $CLAVES"
    ;;
  *)
    echo "uso: $0 clave A|B | puerto | marcas | copiar DIR OFF_ML OFF_FW OFF_SN OFF_ET | verificar DIR T0 T1 | borrar"
    exit 2
    ;;
esac
