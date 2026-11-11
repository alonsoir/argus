#!/usr/bin/env bash
# [VIGILANCIA-D321] DAY321, 8e.4d-2: comprobación de los sensores en el lab, después de aplicarlos. SOLO LEE (no cambia
# nada). Se lanza desde el Mac, en la raíz del repo, con el pipeline, la VM etcd y la VM wazuh arrancados.
# Uso: bash scripts/etcd_ha/d321_comprobar_sensores.sh > /tmp/d321_sensores.txt 2>&1; cat /tmp/d321_sensores.txt
#
# PREDICCIÓN (escrita antes de medir):
#  etcd y defender: falco 0.43.1 en hold, falco-modern-bpf active, falcoctl-artifact-follow masked, una sola lista de apt
#    para download.falco.org con signed-by=/usr/share/keyrings/falcosecurity.gpg, /var/log/falco/eventos.json presente
#    (0600 root; vacío o casi: las reglas de aRGus no deberían saltar con el lab en marcha normal), RSS de falco entre
#    100 y 160 MB (DAY321: 114-149 MB con las reglas de serie; con 3 reglas, quizá algo menos).
#  etcd, defender (y client/suricata/zeek si están arrancadas): wazuh-agent 4.14.10-1 en hold, status='connected'.
#  etcd: MemTotal ~1.5 GB; argus-disco active con su última línea "ARGUS-DISCO ruta=/var/log/vault uso=N umbral=75
#    estado=OK" (N de un solo dígito: el disco de la VM está casi vacío); el ejecutable de vault es /usr/bin/vault (lo
#    supone provisioning/falco/argus_lab.yaml: si sale otro, hay que corregir la macro).
#  Agentes: el ossec.log del agente dice que analiza /var/log/falco/eventos.json y journald, sin ERROR 1103 desde el
#    último arranque; el agent.conf que recibió lleva lo de su grupo (etcd: argus-disco; defender: firewall-agent.log).
#    No se compara el sha256 con el del grupo: con dos grupos (default + el de aRGus) el manager envía los dos fundidos
#    (medido DAY321, v1 de este script: los sha256 no coinciden por eso).
# v2 DAY321: wc y journalctl con sudo (como vagrant daban "Permission denied" y nada), grep -a en ossec.log (tiene
#    bytes no imprimibles: "binary file matches"), errores del agente con su hora, y el fichero que deja falcoctl en
#    config.d.
#  Manager: etcd en argus-etcd y defender en argus-defender, los dos Active y con versión v4.14.10.
#  pipeline-status: ml-detector, sniffer, firewall y etcd-server en ✅ (como antes).
set -u
LC_ALL=C; export LC_ALL
vm() { local out rc; out=$(vagrant ssh "$1" -c "export LC_ALL=C; $2" 2>/dev/null); rc=$?
       [ -n "$out" ] && printf '%s\n' "$out" | tr -d '\r' | grep -v '^\[argus\]'; return $rc; }
arrancada() { vagrant status "$1" 2>/dev/null | grep -qE "^$1 +running"; }

echo "=== [$(date +%T) Mac] 0 VMs"
for v in defender etcd wazuh client suricata zeek; do
  if arrancada "$v"; then echo "    $v: running"; else echo "    $v: parada"; fi
done

for V in etcd defender; do
  echo; echo "=== [$(date +%T) Mac] Falco en $V (hora de la VM en UTC)"
  vm "$V" "echo \"paquete: \$(dpkg-query -W -f='\${Version}' falco 2>/dev/null || echo ausente); hold: \$(apt-mark showhold falco)\"; \
    echo \"falco-modern-bpf: \$(systemctl is-active falco-modern-bpf.service); falcoctl-artifact-follow: \$(systemctl is-enabled falcoctl-artifact-follow.service 2>/dev/null)\"; \
    for u in falco-kmod falco-bpf falco-custom; do echo \"\$u: \$(systemctl is-active \$u.service 2>/dev/null)\"; done; \
    echo \"listas de apt con download.falco.org:\"; grep -lsF download.falco.org /etc/apt/sources.list /etc/apt/sources.list.d/* | while read f; do echo \"  \$f: \$(cat \$f)\"; done; \
    P=\$(pgrep -x falco | head -n 1); [ -n \"\$P\" ] && echo \"RSS de falco: \$(( \$(ps -o rss= -p \$P) / 1024 )) MB\"; \
    sudo ls -l /var/log/falco/eventos.json; echo \"líneas en eventos.json: \$(sudo wc -l /var/log/falco/eventos.json | cut -d' ' -f1)\"; \
    sudo grep -o '\"rule\":\"[^\"]*\"' /var/log/falco/eventos.json | sort | uniq -c | head -n 5; \
    echo \"reglas: \$(ls /etc/falco/rules.d/) config.d: \$(ls /etc/falco/config.d/ | tr '\n' ' ')\"; \
    echo \"engine-kind-falcoctl.yaml (lo escribe falcoctl driver config en el postinst):\"; \
    grep -v '^ *#' /etc/falco/config.d/engine-kind-falcoctl.yaml 2>/dev/null | sed 's/^/  /'" | sed 's/^/    /'
done

echo; echo "=== [$(date +%T) Mac] agentes de Wazuh"
for V in etcd defender client suricata zeek; do
  arrancada "$V" || { echo "    $V: parada, no se mira"; continue; }
  vm "$V" "echo \"$V: wazuh-agent \$(dpkg-query -W -f='\${Version}' wazuh-agent 2>/dev/null || echo ausente), hold: \$(apt-mark showhold wazuh-agent), \
\$(sudo grep '^status=' /var/ossec/var/run/wazuh-agentd.state 2>/dev/null), listas: \$(grep -lsF packages.wazuh.com /etc/apt/sources.list.d/* | tr '\n' ' ')\"" \
    | sed 's/^/    /'
done
for V in etcd defender; do
  case $V in etcd) M=argus-disco ;; *) M=firewall-agent.log ;; esac
  vm "$V" "L=/var/ossec/logs/ossec.log; B=\$(sudo grep -an 'Started (pid' \$L | tail -n 1 | cut -d: -f1); B=\${B:-1}; \
    echo \"$V ossec.log desde el último arranque, línea \$B: \$(sudo sed -n \"\${B}p\" \$L | cut -c1-19) UTC\"; \
    sudo tail -n +\$B \$L | grep -aE 'Analyzing|journald' | sed -E 's/^[0-9\/ :]+//' | sort | uniq -c | head -n 12; \
    echo \"  errores desde ese arranque: \$(sudo tail -n +\$B \$L | grep -ac 'ERROR')\"; \
    sudo tail -n +\$B \$L | grep -a 'ERROR' | sed -E 's/^([0-9\/]+ [0-9:]+) (.{0,110}).*/\1 \2/' | sed -n '1p;\$p' | sed 's/^/    primero y último: /'; \
    echo \"  agent.conf recibido: \$(sudo sha256sum /var/ossec/etc/shared/agent.conf 2>/dev/null | cut -c1-16), con $M: \$(sudo grep -c '$M' /var/ossec/etc/shared/agent.conf 2>/dev/null) líneas\"" | sed 's/^/    /'
done

echo; echo "=== [$(date +%T) Mac] VM etcd: memoria, argus-disco y el ejecutable de vault"
vm etcd "echo \"MemTotal: \$(awk '/MemTotal/ {print int(\$2/1024)}' /proc/meminfo) MB; disponible: \$(free -m | awk 'NR==2 {print \$7}') MB\"; \
  echo \"argus-disco: \$(systemctl is-active argus-disco.service)\"; sudo journalctl -t argus-disco -n 3 -o short-iso --no-pager; \
  P=\$(pgrep -x vault | head -n 1); echo \"vault: pid \$P exe \$(sudo readlink -f /proc/\$P/exe)\"; \
  P=\$(pgrep -x etcd | head -n 1); echo \"etcd: exe \$(sudo readlink -f /proc/\$P/exe)\"" | sed 's/^/    /'
vm defender "P=\$(pgrep -x vault | head -n 1); [ -n \"\$P\" ] && echo \"defender vault: exe \$(sudo readlink -f /proc/\$P/exe)\" || echo 'defender: vault sin proceso'" | sed 's/^/    /'

echo; echo "=== [$(date +%T) Mac] manager"
vm wazuh "sudo /var/ossec/bin/agent_control -l 2>/dev/null | grep -E 'ID:' ; \
  for g in argus-etcd argus-defender; do echo \"\$g: \$(sudo /var/ossec/bin/agent_groups -l -g \$g 2>/dev/null | grep -E '^ *[0-9]+|ID' | tr '\n' ' ')\"; \
  echo \"  agent.conf del manager: \$(sudo sha256sum /var/ossec/etc/shared/\$g/agent.conf | cut -c1-16)\"; done; \
  sudo /var/ossec/framework/python/bin/python3 -c \"import sqlite3; c=sqlite3.connect('file:/var/ossec/queue/db/global.db?mode=ro', uri=True); [print('  ', *r) for r in c.execute('select id,name,version,\\\"group\\\",connection_status from agent order by id')]\" 2>/dev/null" \
  | sed 's/^/    /'

echo; echo "=== [$(date +%T) Mac] pipeline-status"
make pipeline-status > /tmp/d321_sensores_status.txt 2>&1
grep -E '✅|❌' /tmp/d321_sensores_status.txt | grep -E 'ml-detector|sniffer|firewall|etcd-server' | sed 's/^/   /'
echo; echo "=== [$(date +%T) Mac] fin"
