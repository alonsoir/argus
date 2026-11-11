#!/usr/bin/env bash
# test_mitre_ventana.sh — DAY323 [MITRE-VENTANA-D323]: prueba scripts/mitre_ventana.py y scripts/mitre_zeek_cosecha.sh
# con datos fabricados que reproducen lo medido DAY323 (Linux con GNU date: se lanza en la VM zeek con
# `make test-mitre-ventana`). No toca Zeek ni nada del lab: usa un directorio temporal y stubs de zeekctl y pgrep.
set -u
export LC_ALL=C
RAIZ=$(cd "$(dirname "$0")/.." && pwd)
V="python3 -I $RAIZ/scripts/mitre_ventana.py"
C="$RAIZ/scripts/mitre_zeek_cosecha.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
OK=0; KO=0
pasa() { echo "PASA  $1"; OK=$((OK + 1)); }
falla() { echo "FALLA $1"; KO=$((KO + 1)); }
espera() { # nombre rc_esperado rc_obtenido salida patron
  if [ "$2" = "$3" ] && echo "$4" | tr '\n' ' ' | grep -qE -- "$5"; then pasa "$1"; else falla "$1 (rc=$3, esperado $2): $4"; fi
}
fila() { # sensor sec src dst [firma]
  echo "1,$1,$1:id$RANDOM,cpp_sniffer_v33_day12,1:cid=,$2,500000000,$3,$4,44370,8080,TCP,\"${5:-ET SCAN, con coma}\",Web Application Attack,0.000000,0.000000,0.000000,$1,abcd$RANDOM"
}
A=192.168.100.50; VI=192.168.100.1; T0=1794391100; T1=1794391300

# --- mitre_ventana.py
# V1: eve acumulado de dos corridas (medido DAY323: 32 + 32 = 64): solo cuenta la de esta ventana
{ for i in 1 2 3; do fila suricata $((T0 - 3600 + i)) $A $VI; done
  for i in 1 2; do fila suricata $((T0 + 10 + i)) $A $VI; done
  fila suricata $((T0 + 20)) $VI $A
  fila suricata $((T0 + 30)) 192.168.100.1 192.168.100.20; } > "$T/b1.csv"
s=$($V --sensor suricata --desde $T0 --hasta $T1 --atacante $A --victima $VI "$T/b1.csv" "$T/o1.csv"); r=$?
espera "V1 dos corridas: solo la de la ventana; el ataque en los dos sentidos" 0 $r "$s" 'filas=7 dentro=4 fuera=3 malas=0 ataque=3'
[ "$(cat "$T/o1.csv" | wc -l | tr -d ' ')" = 4 ] && grep -qF "$(sed -n 4p "$T/b1.csv")" "$T/o1.csv" \
  && pasa "V2 las filas de dentro se copian byte a byte (el HMAC sigue valiendo)" || falla "V2 copia byte a byte"
# V3: los bordes T0 y T1 están dentro; T1 + 1 s fuera
{ echo "1,zeek,e,n,c,$T0,0,$A,$VI,1,2,tcp,,,0.000000,0.000000,0.000000,zeek,h"
  echo "1,zeek,e,n,c,$T1,0,$A,$VI,1,2,tcp,,,0.000000,0.000000,0.000000,zeek,h"
  echo "1,zeek,e,n,c,$((T1 + 1)),0,$A,$VI,1,2,tcp,,,0.000000,0.000000,0.000000,zeek,h"; } > "$T/b3.csv"
s=$($V --sensor zeek --desde $T0 --hasta $T1 --atacante $A --victima $VI "$T/b3.csv" "$T/o3.csv"); r=$?
espera "V3 T0 y T1 dentro, T1+1 s fuera" 0 $r "$s" 'dentro=2 fuera=1'
# V4: solo NTP y etcd en la ventana (lo que pasaba en falso DAY323): hay filas pero ataque=0
{ fila zeek $((T0 + 5)) 192.168.100.1 192.168.100.20; fila zeek $((T0 + 6)) $A $VI ntp | sed 's/,TCP,/,udp,/'; } > "$T/b4.csv"
sed -i '2s/,8080,/,123,/' "$T/b4.csv"
fila zeek $((T0 + 7)) 192.168.100.50 192.168.100.11 >> "$T/b4.csv"
s=$($V --sensor zeek --desde $T0 --hasta $T1 --atacante $A --victima 192.168.100.99 "$T/b4.csv" "$T/o4.csv"); r=$?
espera "V4 filas en la ventana sin el ataque: ataque=0 (lo decide el veredicto)" 0 $r "$s" 'dentro=3 .*ataque=0'
# V5: líneas rotas y vacías: se cuentan como malas, no paran
{ echo "basura sin comas"; echo ""; echo "1,zeek,e,n,c,no_numero,0,$A,$VI"; echo "1,zeek,e,n,c,$((T0+1)),0,$A,$VI,1,2"; fila zeek $((T0 + 9)) $A $VI; } > "$T/b5.csv"
s=$($V --sensor zeek --desde $T0 --hasta $T1 --atacante $A --victima $VI "$T/b5.csv" "$T/o5.csv"); r=$?
espera "V5 malas contadas (3) y la buena dentro" 0 $r "$s" 'filas=4 dentro=1 fuera=0 malas=3 ataque=1'
# V6: nada en la ventana -> rc 3
s=$($V --sensor suricata --desde 1 --hasta 2 --atacante $A --victima $VI "$T/b3.csv" "$T/o6.csv"); r=$?
espera "V6 ninguna fila dentro -> rc 3" 3 $r "$s" 'dentro=0'
# V7: T1 < T0 -> rc 2; entrada que no existe -> rc 4
s=$($V --sensor x --desde 10 --hasta 5 --atacante $A --victima $VI "$T/b3.csv" "$T/o7.csv"); r=$?
espera "V7 T1 anterior a T0 -> rc 2" 2 $r "$s" 'anterior a T0'
s=$($V --sensor x --desde 1 --hasta 5 --atacante $A --victima $VI "$T/no_existe.csv" "$T/o8.csv"); r=$?
espera "V8 entrada inexistente -> rc 4" 4 $r "$s" 'FALLA'

# --- mitre_zeek_cosecha.sh (stubs: zeekctl no hace nada; pgrep dice «archivando» las N primeras veces)
Z="$T/zeek"; mkdir -p "$Z/bin" "$Z/spool/tmp" "$T/stub"
printf '#!/usr/bin/env bash\necho "stopping zeek ..."\n' > "$Z/bin/zeekctl"
cat > "$T/stub/pgrep" <<'P'
#!/usr/bin/env bash
n=$(cat "$PGREP_CUENTA" 2>/dev/null || echo 0); echo $((n + 1)) > "$PGREP_CUENTA"
[ "$n" -lt "$PGREP_VECES" ] && { echo "123 bash archive-log conn.log"; exit 0; }; exit 1
P
printf '#!/usr/bin/env bash\n:\n' > "$T/stub/sleep"
chmod +x "$Z/bin/zeekctl" "$T/stub/"*
D=$(date -u -d "@$T0" +%F); mkdir -p "$Z/logs/$D"
cab='#separator \x09
#fields	ts	uid	id.orig_h	id.orig_p	id.resp_h	id.resp_p	proto'
# la rotación de las 10:00 de DAY323: el barrido en el archivado de 09:59:34-10:00:00, lo de después en el siguiente
{ echo "$cab"; for i in $(seq 1 1072); do printf '%s.1\tC%d\t%s\t%d\t%s\t%d\ttcp\n' $((T0 + 30)) $i $A $((40000 + i)) $VI $((i)); done; echo '#close	x'; } | gzip > "$Z/logs/$D/conn.09:59:34-10:00:00.log.gz"
{ echo "$cab"; for i in $(seq 1 8); do printf '%s.1\tE%d\t%s\t%d\t%s\t2379\ttcp\n' $((T0 + 70)) $i $VI $((38000 + i)) 192.168.100.20; done; echo '#close	x'; } | gzip > "$Z/logs/$D/conn.10:00:00-10:00:48.log.gz"
echo "$cab" | gzip > "$Z/logs/$D/conn-summary.10:00:00-10:00:48.log.gz"
corre() { PATH="$T/stub:$PATH" ZEEK_DIR="$Z" PGREP_CUENTA="$T/pgrep.n" PGREP_VECES=$1 bash "$C" "${@:2}" 2>&1; }
rm -f "$T/pgrep.n"; s=$(corre 5 $T0.25 $T1.75 "$T/conn.log" 300); r=$?
espera "Z1 rotación a mitad de la corrida: junta los dos archivados (1072 + 8 filas)" 0 $r "$s" 'archivado terminado en 5 s.*2 ficheros.* 1080 filas'
[ "$(grep -c '^#fields' "$T/conn.log")" = 2 ] && ! grep -q 'conn-summary' "$T/conn.log" \
  && pasa "Z2 #fields repetidos (el adapter los acepta) y sin conn-summary" || falla "Z2 cabeceras / conn-summary"
rm -f "$T/pgrep.n"; s=$(corre 1000 $T0 $T1 "$T/conn2.log" 3); r=$?
espera "Z3 el archivado no termina en el máximo -> rc 1" 1 $r "$s" 'sigue tras 3 s'
touch "$Z/spool/tmp/conn.log"; rm -f "$T/pgrep.n"; s=$(corre 0 $T0 $T1 "$T/conn3.log" 2); r=$?
espera "Z4 queda un conn* en spool/tmp (a medio mover) -> espera y rc 1" 1 $r "$s" 'sigue tras 2 s'
rm -f "$Z/spool/tmp/conn.log"
head -c 300 "$Z/logs/$D/conn.09:59:34-10:00:00.log.gz" > "$Z/logs/$D/conn.10:00:48-10:00:50.log.gz"
rm -f "$T/pgrep.n"; s=$(corre 0 $T0 $T1 "$T/conn4.log" 5); r=$?
espera "Z5 un .gz cortado -> rc 4" 4 $r "$s" 'no se puede descomprimir'
rm -f "$Z/logs/$D/conn.10:00:48-10:00:50.log.gz"
rm -f "$T/pgrep.n"; s=$(corre 0 $((T0 + 86400 * 3)) $((T1 + 86400 * 3)) "$T/conn5.log" 5); r=$?
espera "Z6 días sin ficheros conn -> rc 3" 3 $r "$s" 'ningún conn'
s=$(corre 0 abc $T1 "$T/conn6.log"); r=$?
espera "Z7 T0 mal formado -> rc 2" 2 $r "$s" 'uso'

echo "[TEST-MITRE-VENTANA] $OK PASA, $KO FALLA"
[ "$KO" -eq 0 ]
