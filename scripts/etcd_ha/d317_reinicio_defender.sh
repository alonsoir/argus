#!/usr/bin/env bash
# d317_reinicio_defender.sh — DAY317, paso 7 de DEBT-ETCD-HA-TLS-RAFT-001: ayudante del DEFENDER para d317_reinicio_vm.sh
# (instrumento de medida; sustituye a d311_etcd_defender.sh). Se ejecuta en el defender (sudo dentro).
# Las claves se piden por mTLS con la identidad del conversor (OU=CN=bronze-to-gold-converter; regla de /secrets/valid/{c})
# al etcd-server del bloque etcd de ml-detector, SOLO para comprobar huellas y verificar segmentos con el conversor real.
# Se guardan en un directorio solo-root fuera de /vagrant; por la salida solo sale la huella (8 hex del SHA-256 de la
# clave, la misma que escribe el ml-detector). 'borrar' las elimina.
# Uso: d317_reinicio_defender.sh clave A|B ml-detector|firewall-acl-agent | marcas | intervalos |
#      copiar DIR OFF_ML OFF_FW OFF_SN | verificar DIR T0 T1 | borrar
set -u
export LC_ALL=C
CLAVES=${CLAVES:-/tmp/d317_claves}
CORR=${CORR:-/vagrant/logs/correlation}
CONV=${CONV:-/vagrant/correlation-engine/build/bronze_to_gold_converter}
LAB=${LAB:-/vagrant/logs/lab}
PKI=${PKI:-/etc/argus-pki}
JSON_ML=${JSON_ML:-/etc/ml-defender/ml-detector/ml_detector_config.json}
ID=bronze-to-gold-converter
huella() { python3 -I -c 'import hashlib,sys; print(hashlib.sha256(bytes.fromhex(sys.stdin.read().strip())).hexdigest()[:8])'; }
case "${1:-}" in
  clave)
    X=${2:?A o B}; C=${3:?componente}
    case "$X" in A|B) ;; *) echo "[REINICIO-VM] FALLA: clave '$X' (A|B)"; exit 2;; esac
    case "$C" in ml-detector|firewall-acl-agent) ;; *) echo "[REINICIO-VM] FALLA: componente '$C'"; exit 2;; esac
    sudo mkdir -p "$CLAVES" && sudo chmod 700 "$CLAVES" || { echo "[REINICIO-VM] FALLA: no creo $CLAVES"; exit 1; }
    EP=$(sudo python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["etcd"]["endpoints"][0])' "$JSON_ML") \
      || { echo "[REINICIO-VM] FALLA: $JSON_ML sin etcd.endpoints[0]"; exit 1; }
    K=$(sudo curl -sS -f --max-time 10 --cacert "$PKI/ca.crt" --cert "$PKI/$ID.crt" --key "$PKI/$ID.key" "$EP/secrets/valid/$C" \
        | python3 -I -c '
import json, re, sys
d = json.load(sys.stdin)
a = [k.get("key", "") for k in d.get("keys", []) if k.get("is_active") is True]
print(a[0] if len(a) == 1 and re.fullmatch(r"[0-9a-f]{64}", a[0]) else "")') \
      || { echo "[REINICIO-VM] FALLA: GET $EP/secrets/valid/$C"; exit 1; }
    [ ${#K} -eq 64 ] || { echo "[REINICIO-VM] FALLA: /secrets/valid/$C sin una única clave activa de 64 hex"; exit 1; }
    printf '%s' "$K" | sudo tee "$CLAVES/$X-$C.hex" > /dev/null && sudo chmod 600 "$CLAVES/$X-$C.hex"
    echo "[REINICIO-VM] huella_${X}_${C}=$(printf '%s' "$K" | huella)"
    ;;
  marcas)
    for f in ml-detector firewall-agent sniffer; do printf '%s=%s ' "$f" "$(wc -l < "$LAB/$f.log" 2>/dev/null || echo 0)"; done
    echo "epoch=$(date +%s)"
    ;;
  intervalos)  # heartbeat_interval_seconds de cada componente (defecto 30 si falta: el de la librería)
    for p in sniffer:/vagrant/sniffer/config/sniffer.json ml-detector:/vagrant/ml-detector/config/ml_detector_config.json \
             firewall-acl-agent:/vagrant/firewall-acl-agent/config/firewall.json; do
      python3 -I -c 'import json,sys; c,f=sys.argv[1].split(":",1); v=json.load(open(f)).get("etcd",{}).get("heartbeat_interval_seconds",30); print("%s=%s" % (c, v if isinstance(v,int) and 5<=v<=300 else 30))' "$p"
    done | tr '\n' ' '; echo
    ;;
  copiar)
    D=${2:?dir}; mkdir -p "$D" || exit 1
    i=3
    for f in ml-detector firewall-agent sniffer; do
      off=${!i:-0}; i=$((i + 1))
      tail -n +"$((off + 1))" "$LAB/$f.log" > "$D/$f.log"
      echo "[REINICIO-VM] $f.log: $(wc -l < "$D/$f.log") líneas nuevas"
    done
    ;;
  verificar)  # cada segmento de bronce del intervalo, con la clave A y con la B del ml-detector
    D=${2:?dir}; T0=${3:?t0}; T1=${4:?t1}
    for X in A B; do sudo test -s "$CLAVES/$X-ml-detector.hex" || { echo "[REINICIO-VM] FALLA: falta la clave $X"; exit 1; }; done
    [ -x "$CONV" ] || { echo "[REINICIO-VM] FALLA: no existe el conversor $CONV"; exit 1; }
    W=$(mktemp -d); O="$D/verificacion.txt"
    echo "# segmento mtime lineas validas_A validas_B clase" > "$O"
    for s in $(ls "$CORR" | grep -E '^argus-.*\.csv$' | sort); do
      m=$(stat -c %Y "$CORR/$s")
      [ "$m" -ge "$T0" ] && [ "$m" -le "$T1" ] || continue
      n=$(wc -l < "$CORR/$s"); va=0; vb=0
      for X in A B; do
        v=$(sudo cat "$CLAVES/$X-ml-detector.hex" | { read -r k; ARGUS_BRONZE_HMAC_KEY_HEX="$k" "$CONV" "$CORR/$s" "$W/o.avro" "$W/o.parquet" 2>/dev/null; } |
            awk '/filas v/ { print $NF }')
        v=${v:-0}
        if [ "$X" = A ]; then va=$v; else vb=$v; fi
      done
      if   [ "$n" -eq 0 ]; then c=VACIO
      elif [ "$va" -eq "$n" ] && [ "$vb" -eq "$n" ]; then c=AB
      elif [ "$va" -eq "$n" ] && [ "$vb" -eq 0 ]; then c=A
      elif [ "$vb" -eq "$n" ] && [ "$va" -eq 0 ]; then c=B
      elif [ "$va" -eq 0 ] && [ "$vb" -eq 0 ]; then c=NINGUNA
      else c=MEZCLA; fi
      echo "$s $m $n $va $vb $c" >> "$O"
    done
    rm -rf "$W"
    awk '!/^#/ { n++; c[$6]++; l[$6] += $3 }
         END { printf "[REINICIO-VM] segmentos=%d AB=%d (filas %d) A=%d B=%d NINGUNA=%d MEZCLA=%d VACIO=%d\n",
               n, c["AB"], l["AB"], c["A"], c["B"], c["NINGUNA"], c["MEZCLA"], c["VACIO"] }' "$O"
    ;;
  borrar)
    sudo rm -rf "$CLAVES" && echo "[REINICIO-VM] claves borradas de $CLAVES"
    ;;
  *)
    echo "uso: $0 clave A|B ml-detector|firewall-acl-agent | marcas | intervalos | copiar DIR OFF_ML OFF_FW OFF_SN | verificar DIR T0 T1 | borrar"
    exit 2
    ;;
esac
