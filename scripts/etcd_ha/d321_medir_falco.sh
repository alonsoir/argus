#!/usr/bin/env bash
# [VIGILANCIA-D321] DAY321, medida previa al diseño de 8e.4d: cuánto pesa Falco 0.43.1 (modern_ebpf, reglas de serie del
# paquete) en la VM etcd y en el defender, con el pipeline vivo. CAMBIA el lab de forma temporal: en cada VM instala
# dist/vendor/falco_*.deb (sha256 contra dist/vendor/CHECKSUMS, como vendor-download), arranca falco-modern-bpf, mide
# 60 s y lo PURGA (también desde el trap). Si Falco ya estaba instalado en una VM, no la toca. Sin falcoctl (no baja
# nada de internet). Se lanza desde el Mac, en la raíz del repo, con el pipeline arrancado.
# Uso: bash scripts/etcd_ha/d321_medir_falco.sh > /tmp/d321_falco.txt 2>&1; cat /tmp/d321_falco.txt
#
# Por VM: memoria disponible antes / con Falco / después de purgar; RSS de falco cada 5 s (máximo y último); CPU de
# falco en los 60 s (utime+stime de /proc/<pid>/stat, en % de un núcleo); eventos que escribe en el journal en esos
# 60 s (con las reglas de serie, sin las de aRGus: da una idea del ruido).
#
# PREDICCIÓN (escrita antes de medir; la referencia es lo publicado para modern_ebpf, no medido aquí):
#  RSS de falco entre 50 y 150 MB en cada VM y CPU por debajo del 5 % de un núcleo con el tráfico normal del lab. En la
#  VM etcd la memoria disponible baja en esa misma cantidad (de ~626 MB a ~500 MB) y vuelve al purgar. Tras purgar: sin
#  proceso falco ni paquete, y el pipeline sigue arriba.
set -u
LC_ALL=C; export LC_ALL
# [VIGILANCIA-D321] LC_ALL=C también DENTRO de cada orden remota: medido DAY321, la v1 escribió "0,7" en el defender
# (es_ES) porque el LC_ALL del Mac no llega a la VM
vm() { local out rc; out=$(vagrant ssh "$1" -c "export LC_ALL=C; $2" 2>/dev/null); rc=$?
       [ -n "$out" ] && printf '%s\n' "$out" | tr -d '\r' | grep -v '^\[argus\]'; return $rc; }
UNIDAD=falco-modern-bpf.service
INSTALADO=""   # VMs donde lo instaló este script (las que hay que purgar)
purgar() {
  local v=$1
  vm "$v" "sudo systemctl stop $UNIDAD 2>/dev/null; sudo DEBIAN_FRONTEND=noninteractive dpkg --purge falco >/dev/null 2>&1; \
    echo \"paquete: \$(dpkg-query -W -f='\${Status}' falco 2>/dev/null || echo ausente) proceso: \$(pgrep -x falco >/dev/null && echo SIGUE || echo ninguno)\"" \
    | sed "s/^/    $v purgado: /"
}
restaurar() {
  local v
  for v in $INSTALADO; do purgar "$v"; done
  INSTALADO=""
}
trap restaurar EXIT
trap 'exit 130' INT TERM

echo "=== [$(date +%T)] 0 comprobaciones"
DEB=$(ls dist/vendor/falco_*.deb 2>/dev/null | head -n 1)
[ -n "$DEB" ] || { echo "PARADA: no hay dist/vendor/falco_*.deb"; exit 1; }
H=$(shasum -a 256 "$DEB" | cut -d' ' -f1)
grep -q "$H" dist/vendor/CHECKSUMS 2>/dev/null || { echo "PARADA: el sha256 de $DEB no está en dist/vendor/CHECKSUMS"; exit 1; }
echo "    $DEB sha256=${H:0:16}… en CHECKSUMS"
make pipeline-status > /tmp/d321_falco_status0.txt 2>&1
grep -E '✅|❌' /tmp/d321_falco_status0.txt | grep -E 'ml-detector|sniffer|firewall|etcd-server' | sed 's/^/   /'

for V in etcd defender; do
  echo; echo "=== [$(date +%T)] $V"
  if vm "$V" "dpkg-query -W -f='\${Status}' falco 2>/dev/null | grep -q 'install ok installed'"; then
    echo "    Falco YA estaba instalado en $V: no se toca"; continue
  fi
  echo "    disponible antes: $(vm "$V" "free -m | awk 'NR==2 {print \$7}'") MB"
  INSTALADO="$INSTALADO $V"
  vm "$V" "sudo env FALCO_FRONTEND=noninteractive FALCO_DRIVER_CHOICE=modern_ebpf FALCOCTL_ENABLED=no DEBIAN_FRONTEND=noninteractive \
    dpkg -i /vagrant/$DEB > /tmp/d321_falco_dpkg.txt 2>&1; echo \"dpkg rc=\$?\"; \
    sudo systemctl disable --now falcoctl-artifact-follow.service >/dev/null 2>&1; \
    sudo systemctl restart $UNIDAD; sleep 5; echo \"$UNIDAD: \$(systemctl is-active $UNIDAD)\"; falco --version 2>/dev/null | head -n 1" \
    | sed 's/^/    /'
  vm "$V" "pgrep -x falco >/dev/null" || { echo "    FALLA: falco no arrancó en $V"; vm "$V" "sudo journalctl -u $UNIDAD -n 15 --no-pager; tail -n 5 /tmp/d321_falco_dpkg.txt" | sed 's/^/      /'; continue; }
  vm "$V" "T0=\$(date +%s); P=\$(pgrep -x falco | head -n 1); TCK=\$(getconf CLK_TCK); \
    c0=\$(awk '{print \$14+\$15}' /proc/\$P/stat); max=0; \
    for i in \$(seq 1 12); do r=\$(ps -o rss= -p \$P | tr -d ' '); [ \"\$r\" -gt \"\$max\" ] && max=\$r; sleep 5; done; \
    c1=\$(awk '{print \$14+\$15}' /proc/\$P/stat); \
    echo \"RSS de falco: máximo \$((max / 1024)) MB, último \$((r / 1024)) MB\"; \
    awk -v a=\$c0 -v b=\$c1 -v t=\$TCK 'BEGIN {printf \"CPU de falco en 60 s: %.1f %% de un núcleo\\n\", (b - a) / t / 60 * 100}'; \
    echo \"disponible con Falco: \$(free -m | awk 'NR==2 {print \$7}') MB\"; \
    echo \"eventos de falco en el journal en esos 60 s: \$(sudo journalctl -u $UNIDAD --since @\$T0 --no-pager -q | grep -c -E 'Warning|Notice|Critical|Error|Informational')\"; \
    sudo journalctl -u $UNIDAD --since @\$T0 --no-pager -q | grep -E 'Warning|Notice|Critical|Error' | sed -E 's/.*(Warning|Notice|Critical|Error) ([^(]{0,80}).*/\1 \2/' | sort | uniq -c | sort -rn | head -n 5" \
    | sed 's/^/    /'
  purgar "$V"; INSTALADO=$(echo "$INSTALADO" | sed "s/ $V//")
  echo "    disponible tras purgar: $(vm "$V" "free -m | awk 'NR==2 {print \$7}'") MB"
done

echo; echo "=== [$(date +%T)] pipeline tras la medida"
make pipeline-status > /tmp/d321_falco_status1.txt 2>&1
grep -E '✅|❌' /tmp/d321_falco_status1.txt | grep -E 'ml-detector|sniffer|firewall|etcd-server' | sed 's/^/   /'
echo "=== [$(date +%T)] fin"
