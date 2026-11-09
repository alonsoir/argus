#!/usr/bin/env bash
# [VIGILANCIA-D321] DAY321, medida previa al diseño de 8e.4d (Wazuh y Falco). Se lanza desde el Mac, en la raíz del repo.
# Mide, sin instalar nada:
#   M1 Mac: RAM física, presión de memoria y VMs arrancadas (para saber si cabe la VM wazuh con defender, etcd y client)
#   M2 defender y VM etcd: RAM libre, kernel, BTF (Falco modern_ebpf lo necesita), agente Wazuh instalado y su RSS
#   M3 VM etcd: en qué sistema de ficheros está /var/log/vault y cuánto ocupa (la alarma del 75 %)
#   M4 VM etcd: el texto EXACTO que escribe Vault cuando falla UN audit device. Se pone inmutable (chattr +i)
#      /var/log/vault/audit.log, se hace una petición auditada (login cert de argus-infra y revoke-self), se mira el
#      journal de vault.service y el audit de syslog, y se quita el inmutable. El trap lo quita pase lo que pase.
#   M5 Mac: si existe dist/vendor/falco_*.deb, su versión y si su sha256 está en dist/vendor/CHECKSUMS
# Uso: bash scripts/etcd_ha/d321_medir_vigilancia.sh > /tmp/d321_medir.txt 2>&1; cat /tmp/d321_medir.txt
#
# PREDICCIÓN (escrita antes de medir):
# v2 (DAY321, tras la primera corrida): sudo en la comprobación de Wazuh y en lsattr (/var/ossec y /var/log/vault no
#    los lee vagrant); en el fichero de audit solo cuentan los logins (antes contaba también peticiones del etcd-server).
#  M2 en las dos VMs: kernel 6.1 de Debian 12 y /sys/kernel/btf/vmlinux presente. Agente Wazuh en el defender con
#     RSS total de decenas de MB; en la VM etcd, NO hay agente.
#  M3 /var/log/vault en el sistema de ficheros raíz de la VM etcd (no hay partición propia).
#  M4 con el fichero bloqueado, la petición sigue dando 200 (Vault solo bloquea si fallan TODOS los audit devices y el
#     de syslog sigue escribiendo); en el journal de vault.service aparece una línea de error del audit de fichero y en
#     syslog (vault-audit) sí está la petición. Si el inmutable no impide escribir sobre el descriptor ya abierto, no hay
#     error: sería un hallazgo y se probaría otro método.
set -u
LC_ALL=C; export LC_ALL
vm() { local out rc; out=$(vagrant ssh "$1" -c "$2" 2>/dev/null); rc=$?
       [ -n "$out" ] && printf '%s\n' "$out" | tr -d '\r' | grep -v '^\[argus\]'; return $rc; }
BLOQUEADO=0
restaurar() {
  if [ "$BLOQUEADO" = 1 ]; then
    vm etcd "sudo chattr -i /var/log/vault/audit.log; sudo lsattr /var/log/vault/audit.log" | sed 's/^/    trap: /'
    BLOQUEADO=0
  fi
}
trap restaurar EXIT
trap 'exit 130' INT TERM

echo "=== [$(date +%T)] M1 Mac"
echo "    RAM física: $(( $(sysctl -n hw.memsize) / 1024 / 1024 )) MB"
memory_pressure 2>/dev/null | tail -n 1 | sed 's/^/    /'
VBoxManage list runningvms 2>/dev/null | sed 's/^/    VM arrancada: /'
for v in $(VBoxManage list runningvms 2>/dev/null | sed -E 's/^"([^"]+)".*/\1/'); do
  echo "    $v: $(VBoxManage showvminfo "$v" --machinereadable 2>/dev/null | grep '^memory=' | cut -d= -f2) MB asignados"
done

for V in defender etcd; do
  echo; echo "=== [$(date +%T)] M2 $V"
  vm "$V" "free -m | sed -n 1,2p; echo \"kernel \$(uname -r)\"; [ -r /sys/kernel/btf/vmlinux ] && echo 'BTF: /sys/kernel/btf/vmlinux presente' || echo 'BTF: AUSENTE'; \
    if sudo test -x /var/ossec/bin/wazuh-control; then echo \"wazuh-agent: \$(systemctl is-active wazuh-agent) \$(dpkg-query -W -f='\${Version}' wazuh-agent 2>/dev/null)\"; \
      ps -C wazuh-agentd,wazuh-execd,wazuh-modulesd,wazuh-syscheckd,wazuh-logcollector -o rss=,comm= | awk '{t+=\$1; printf \"  %-20s %6d KB\\n\", \$2, \$1} END {printf \"  total RSS wazuh       %6d KB\\n\", t}'; \
    else echo 'wazuh-agent: NO instalado'; fi" | sed 's/^/    /'
done

echo; echo "=== [$(date +%T)] M3 VM etcd: /var/log/vault"
vm etcd "findmnt -n -T /var/log/vault -o SOURCE,TARGET,FSTYPE,SIZE,USED,USE%; sudo du -sh /var/log/vault; sudo ls -la /var/log/vault | head -n 8" | sed 's/^/    /'

echo; echo "=== [$(date +%T)] M4 VM etcd: un audit device roto (fichero inmutable unos segundos)"
T0=$(vm etcd "date +%s")
[[ "$T0" =~ ^[0-9]+$ ]] || { echo "PARADA: no leo la hora de la VM etcd"; exit 1; }
vm etcd "sudo chattr +i /var/log/vault/audit.log && sudo lsattr /var/log/vault/audit.log" | sed 's/^/    /'
BLOQUEADO=1
vm etcd 'C="--cacert /etc/argus-pki/ca.crt --cert /etc/argus-pki/argus-infra.crt --key /etc/argus-pki/argus-infra.key"
  R=$(sudo curl -s -w "\n%{http_code}" $C -X POST -d "{\"name\":\"argus-infra\"}" https://127.0.0.1:8200/v1/auth/cert/login)
  CODE=$(printf "%s" "$R" | tail -n 1); echo "login cert argus-infra con el fichero bloqueado: HTTP $CODE"
  TOK=$(printf "%s" "$R" | head -n -1 | python3 -c "import sys,json; print(json.load(sys.stdin).get(\"auth\",{}).get(\"client_token\",\"\"))" 2>/dev/null)
  printf "%s" "$R" | head -n -1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(\"errores:\", d.get(\"errors\"))" 2>/dev/null
  if [ -n "$TOK" ]; then RV=$(sudo curl -s -o /dev/null -w "%{http_code}" $C -H "X-Vault-Token: $TOK" -X POST https://127.0.0.1:8200/v1/auth/token/revoke-self); echo "revoke-self: HTTP $RV"; fi' | sed 's/^/    /'
sleep 2
restaurar
echo "    journal de vault.service desde el bloqueo (las líneas con audit, error o fail):"
vm etcd "sudo journalctl -u vault.service --since @$T0 --no-pager -o short-iso | grep -iE 'audit|error|fail' | head -n 12" | sed 's/^/      /' | cut -c1-300
echo "    líneas de vault.service desde el bloqueo: $(vm etcd "sudo journalctl -u vault.service --since @$T0 --no-pager -q | wc -l")"
echo "    audit de syslog (vault-audit) desde el bloqueo: $(vm etcd "sudo journalctl -t vault-audit --since @$T0 --no-pager -q | grep -c 'auth/cert/login'") peticiones de login"
echo "    audit de fichero: logins (auth/cert/login) con fecha posterior al bloqueo: $(vm etcd "sudo python3 - $T0 <<'PY'
import json, sys, datetime
t0 = int(sys.argv[1]); n = 0
for l in open('/var/log/vault/audit.log'):
    try:
        j = json.loads(l)
        if j.get('request', {}).get('path') != 'auth/cert/login': continue
        t = datetime.datetime.strptime(j['time'][:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=datetime.timezone.utc)
        n += t.timestamp() >= t0
    except Exception:
        pass
print(n)
PY") (0 = el bloqueo impidió escribir el login en el fichero)"
vm etcd "sudo lsattr /var/log/vault/audit.log" | sed 's/^/    tras restaurar (sin la i): /'
echo "    Vault sigue sano: $(vm etcd "sudo curl -s -o /dev/null -w '%{http_code}' --cacert /etc/argus-pki/ca.crt --cert /etc/argus-pki/argus-infra.crt --key /etc/argus-pki/argus-infra.key https://127.0.0.1:8200/v1/sys/health") (/v1/sys/health)"

echo; echo "=== [$(date +%T)] M5 Mac: paquete de Falco"
if ls dist/vendor/falco_*.deb >/dev/null 2>&1; then
  for d in dist/vendor/falco_*.deb; do
    h=$(shasum -a 256 "$d" | cut -d' ' -f1)
    echo "    $d $(du -h "$d" | cut -f1) sha256=${h:0:16}… en CHECKSUMS: $(grep -c "$h" dist/vendor/CHECKSUMS 2>/dev/null || echo 0)"
  done
else
  echo "    dist/vendor/falco_*.deb NO existe (lo produce EMECAS dev; ver make vendor-download)"
fi
echo; echo "=== [$(date +%T)] fin"
