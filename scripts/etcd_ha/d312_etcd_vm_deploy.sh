#!/bin/bash
# d312_etcd_vm_deploy.sh — DAY312, paso 4a del PR1 de DEBT-ETCD-HA-TLS-RAFT-001.
# Despliega el etcd-server compilado en el defender a la VM etcd, que NO tiene compilador (BSR, ADR-039).
#   1. defender: copia el binario y las librerías que resuelve en /usr/local/lib a dist/etcd-vm/ (fuera de git),
#      con manifiesto sha256, y la lista de paquetes Debian de las demás (dpkg -S), sin listas escritas a mano.
#   2. material /etc/ml-defender/etcd-server/ (semilla, claves): defender -> VM etcd con tar encadenado por dos
#      ssh -T (ver Transporte); pasa solo por la memoria del Mac, nunca por su disco ni por /vagrant. Se verifica fichero a
#      fichero con sha256 en las dos VMs; solo se imprime cuántos coinciden.
#   3. VM etcd: instala los paquetes, copia a /opt/argus/etcd-server/{bin,lib}, verifica el manifiesto y que el
#      binario no tenga librerías sin resolver.
# Uso (Mac, raíz del repo):  bash scripts/etcd_ha/d312_etcd_vm_deploy.sh [PROFILE]   (defecto production)
# Transporte: ssh -T con la configuración de 'vagrant ssh-config'. 'vagrant ssh --no-tty' sigue dando terminal al
# comando remoto (medido DAY312, Vagrant 2.4.9: tar se niega a escribir en el terminal, llegan 127 bytes de 348160).
set -euo pipefail
PROFILE=${1:-production}
[[ "$PROFILE" =~ ^(production|debug|tsan|asan)$ ]] || { echo "[ETCD-DEPLOY] FALLA: PROFILE '$PROFILE' (production|debug|tsan|asan)"; exit 1; }
[ -f Vagrantfile ] && [ -d .git ] || { echo "[ETCD-DEPLOY] FALLA: no estoy en la raíz del repo"; exit 1; }
BIN=/vagrant/etcd-server/build-$PROFILE/etcd-server
STAGE=/vagrant/dist/etcd-vm
CFG=$(mktemp -t d312sshcfg.XXXXXX); trap 'rm -f "$CFG"' EXIT
vagrant ssh-config defender > "$CFG" 2>/dev/null && vagrant ssh-config etcd >> "$CFG" 2>/dev/null \
  || { echo "[ETCD-DEPLOY] FALLA: vagrant ssh-config (¿defender y etcd levantadas?)"; exit 1; }
S() { local h=$1; shift; ssh -F "$CFG" -T -o LogLevel=ERROR "$h" "$@"; }
echo "[ETCD-DEPLOY] PROFILE=$PROFILE ($([ -n "${1:-}" ] && echo argumento || echo 'defecto: ausente')) $(date -u +%FT%TZ)"

# ── 1. defender: binario + librerías propias + paquetes ──────────────────────
S defender "set -euo pipefail
  [ -x '$BIN' ] || { echo '[ETCD-DEPLOY] FALLA: no existe $BIN (make pipeline-build PROFILE=$PROFILE)'; exit 1; }
  ldd '$BIN' | grep -q 'not found' && { echo '[ETCD-DEPLOY] FALLA: el binario tiene librerías sin resolver en el defender'; exit 1; }
  rm -rf '$STAGE' && mkdir -p '$STAGE/bin' '$STAGE/lib'
  cp -p '$BIN' '$STAGE/bin/etcd-server'
  ldd '$BIN' | awk '\$3 ~ /^\\/usr\\/local\\/lib\\// {print \$3}' | sort -u > '$STAGE/locales.txt'
  while read -r L; do cp -L \"\$L\" '$STAGE/lib/'; done < '$STAGE/locales.txt'
  ldd '$BIN' | awk '\$3 ~ /^\\// && \$3 !~ /^\\/usr\\/local\\// {print \$3}' | sort -u \\
    | while read -r L; do dpkg -S \"\$(readlink -f \"\$L\")\" 2>/dev/null || dpkg -S \"\$L\"; done \\
    | cut -d: -f1 | sort -u > '$STAGE/paquetes.txt'
  (cd '$STAGE' && find bin lib -type f | sort | xargs sha256sum) > '$STAGE/MANIFIESTO.sha256'
  echo \"[ETCD-DEPLOY] defender \$(hostname): binario + \$(wc -l < '$STAGE/locales.txt') librerías propias + \$(wc -l < '$STAGE/paquetes.txt') paquetes Debian\"
  echo \"[ETCD-DEPLOY] librerías propias: \$(xargs -n1 basename < '$STAGE/locales.txt' | tr '\\n' ' ')\"
  echo \"[ETCD-DEPLOY] paquetes: \$(tr '\\n' ' ' < '$STAGE/paquetes.txt')\""

# ── 2a. prueba del tubo con datos públicos: si no llega idéntico, no se manda el material ──
PA=$(S defender "tar -C /usr/share/doc -cf - bash | sha256sum" | cut -c1-64)
PB=$(S defender "tar -C /usr/share/doc -cf - bash" | S etcd "sha256sum" | cut -c1-64)
[ -n "$PA" ] && [ "$PA" = "$PB" ] || { echo "[ETCD-DEPLOY] FALLA: el tubo defender->etcd altera los datos (${PA:0:16} != ${PB:0:16}); no se manda el material"; exit 1; }
echo "[ETCD-DEPLOY] tubo defender->etcd verificado con datos públicos (sha256 ${PA:0:16} igual a los dos lados)"

# ── 2. material del etcd-server: defender -> etcd, sin disco intermedio ──────
S defender "sudo tar -C /etc/ml-defender -cf - etcd-server" \
  | S etcd "sudo install -d -m 0755 -o root -g root /etc/ml-defender && sudo tar -C /etc/ml-defender -xpf -"
D=$(S defender "cd /etc/ml-defender/etcd-server && sudo find . -type f | sort | sudo xargs sha256sum" 2>/dev/null )
E=$(S etcd "cd /etc/ml-defender/etcd-server && sudo find . -type f | sort | sudo xargs sha256sum" 2>/dev/null )
ND=$(printf '%s\n' "$D" | grep -c .); IG=$(comm -12 <(printf '%s\n' "$D" | sort) <(printf '%s\n' "$E" | sort) | grep -c . || true)
[ "$ND" -gt 0 ] && [ "$ND" = "$IG" ] || { echo "[ETCD-DEPLOY] FALLA: material: $IG de $ND ficheros iguales"; exit 1; }
L=$(S etcd "readlink /etc/ml-defender/etcd-server/etcd-server.json" )
echo "[ETCD-DEPLOY] material: $IG de $ND ficheros iguales en defender y etcd; etcd-server.json -> $L"

# ── 3. VM etcd: paquetes + instalación + verificación ────────────────────────
S etcd "set -euo pipefail
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \$(cat '$STAGE/paquetes.txt') > /dev/null
  # /run/argus: el etcd-server crea ahí ipc:///run/argus/autonomy.sock al arrancar (medido DAY312: sin él, 'No such file
  # or directory'). Mismo mecanismo que tools/provision.sh en el defender: tmpfiles.d, que lo recrea en cada arranque.
  printf 'd /run/argus 0755 root root -\\n' | sudo tee /etc/tmpfiles.d/argus-etcd-server.conf > /dev/null
  sudo systemd-tmpfiles --create /etc/tmpfiles.d/argus-etcd-server.conf
  [ -d /run/argus ] || { echo '[ETCD-DEPLOY] FALLA: /run/argus no existe tras systemd-tmpfiles'; exit 1; }
  sudo rm -rf /opt/argus/etcd-server.nuevo && sudo mkdir -p /opt/argus/etcd-server.nuevo
  sudo cp -rp '$STAGE/bin' '$STAGE/lib' /opt/argus/etcd-server.nuevo/
  (cd /opt/argus/etcd-server.nuevo && sha256sum -c --quiet '$STAGE/MANIFIESTO.sha256') || { echo '[ETCD-DEPLOY] FALLA: manifiesto sha256 no cuadra en la VM etcd'; exit 1; }
  NF=\$(LD_LIBRARY_PATH=/opt/argus/etcd-server.nuevo/lib ldd /opt/argus/etcd-server.nuevo/bin/etcd-server | grep -c 'not found' || true)
  [ \"\$NF\" = 0 ] || { LD_LIBRARY_PATH=/opt/argus/etcd-server.nuevo/lib ldd /opt/argus/etcd-server.nuevo/bin/etcd-server | grep 'not found'; echo \"[ETCD-DEPLOY] FALLA: \$NF librerías sin resolver en la VM etcd\"; exit 1; }
  sudo rm -rf /opt/argus/etcd-server && sudo mv /opt/argus/etcd-server.nuevo /opt/argus/etcd-server
  echo \"[ETCD-DEPLOY] etcd \$(hostname): /opt/argus/etcd-server instalado, manifiesto OK, 0 librerías sin resolver, /run/argus por tmpfiles.d\"
  echo \"[ETCD-DEPLOY] binario sha256 \$(sha256sum /opt/argus/etcd-server/bin/etcd-server | cut -c1-16)\""
echo "[ETCD-DEPLOY] RESULTADO PASA"
