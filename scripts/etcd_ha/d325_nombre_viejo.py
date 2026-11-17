#!/usr/bin/env python3
# d325_nombre_viejo.py — DAY325, PR2b de DEBT-ETCD-HA-TLS-RAFT-001: restos del renombrado etcd -> control-1 (paso 1, 542e02b)
# que el C1 de test-plano-control no cazaba y que pararían lab-e2e (y con él el EMECAS):
#   - scripts/vigilancia/lab_e2e_vigilancia.sh: la VM en el bucle de comprobación y el agente de Wazuh (ahora control-1)
#     en el bucle de agentes, en los seis 'alerta' y en el 'contar' de C8.
#   - scripts/etcd_ha/d320_antispoof_e2e.sh y d321_latido_e2e.sh: vm etcd "..." y el bucle de vagrant status.
#   - scripts/etcd_ha/d321_medir_falco_hijos.sh (instrumento DAY321; vivo solo porque lo cita un comentario de las reglas
#     de Falco): lo mismo, para que C1 siga verde; si se borra o no se decide en F2.
#   - scripts/etcd_ha/test_plano_control.py: el detector caza también esas formas (7 muestras nuevas que debe cazar y
#     7 legítimas que debe dejar pasar).
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d325_nombre_viejo.py --check | --apply
# Todo o nada: sha256 de partida, cada ancla exactamente una vez y sha256 del resultado antes de escribir. Idempotente.
import hashlib, os, sys, tempfile

FICHEROS = [{'ruta': 'scripts/etcd_ha/test_plano_control.py',
  'antes': '78daa5befaa18e12330e911e0496b448e7796dc1c941562f513d37d4cbae150d',
  'despues': '4b7797f8b4af1de7d918b0d69c33d258a3899df54f482018a53db0f502c7c67a',
  'modo': None,
  'nuevo': None,
  'trozos': [("#   C1 (paso 1, renombrado etcd -> control-1): ningún fichero VIVO nombra todavía a la VM 'etcd' "
              '(vagrant ssh/up/halt/\n'
              '#      status/destroy/ssh-config etcd, S/V etcd "...", known_hosts_etcd, AGENT_NAME etcd, el grupo de '
              'Wazuh argus-etcd,\n'
              '#      la máquina "etcd" del Vagrantfile o del inventario). VIVO no es una lista escrita a mano: se '
              'parte del Makefile,\n'
              '#      el Vagrantfile, ansible/ y provisioning/, y se añade todo script de scripts/ o tools/ cuya '
              'ruta aparezca en un\n'
              '#      fichero vivo, hasta que no entra ninguno más. Un parcheador de un día que nadie llama no es '
              'vivo. Este test',
              "#   C1 (paso 1, renombrado etcd -> control-1): ningún fichero VIVO nombra todavía a la VM 'etcd' "
              '(vagrant ssh/up/halt/\n'
              '#      status/destroy/ssh-config etcd, S/V etcd "...", known_hosts_etcd, AGENT_NAME etcd, el grupo de '
              'Wazuh argus-etcd,\n'
              '#      la máquina "etcd" del Vagrantfile o del inventario; y, DAY325, las formas que se escaparon al '
              'renombrar: vm etcd\n'
              '#      "...", un bucle for sobre nombres de VM con etcd dentro, y el agente de Wazuh \'etcd\' como '
              'argumento de alerta y\n'
              '#      contar en el E2E de vigilancia). VIVO no es una lista escrita a mano: se parte del Makefile,\n'
              '#      el Vagrantfile, ansible/ y provisioning/, y se añade todo script de scripts/ o tools/ cuya '
              'ruta aparezca en un\n'
              '#      fichero vivo, hasta que no entra ninguno más. Un parcheador de un día que nadie llama no es '
              'vivo. Este test'),
             ('    r"vagrant (?:ssh|up|halt|provision|ssh-config|status|destroy|reload)(?: -f)?(?: '
              '(?:defender|client|suricata|zeek|wazuh))*"\n'
              '    r" etcd(?![\\w/.-])"\n'
              '    r"|(?:^|[\\s;(|&])[SV] etcd \\""\n'
              '    r"|known_hosts_etcd"\n'
              '    r"|argus-etcd(?![\\w-])"',
              '    r"vagrant (?:ssh|up|halt|provision|ssh-config|status|destroy|reload)(?: -f)?(?: '
              '(?:defender|client|suricata|zeek|wazuh))*"\n'
              '    r" etcd(?![\\w/.-])"\n'
              '    r"|(?:^|[\\s;(|&{])(?:[SV]|vm|vme) etcd \\""\n'
              '    r"|\\bfor \\w+ in '
              '(?=[^;]*\\b(?:defender|client|suricata|zeek|wazuh)\\b)[^;]*(?<![\\w/.$-])etcd(?![\\w/.-])"\n'
              '    r"|\\balerta etcd\\b|\\bcontar \\S+ \\S+ etcd\\b"\n'
              '    r"|known_hosts_etcd"\n'
              '    r"|argus-etcd(?![\\w-])"'),
             ("    '        etcd:',\n    'etcd\\targus-etcd',\n]\nDEBE_PASAR = [",
              "    '        etcd:',\n"
              "    'etcd\\targus-etcd',\n"
              '    \'infra() { vm etcd "sudo /usr/local/sbin/argus-infra $1"; }\',\n'
              '    \'INICIO=$(vm etcd "date +%s")\',\n'
              '    \'for v in client etcd; do vagrant status "$v" 2>/dev/null | grep -qE "^$v +running" || falla '
              '"x"; done\',\n'
              "    'for m in defender client etcd wazuh; do',\n"
              "    'for a in etcd defender; do',\n"
              '    \'marca; etcd fim-crear; alerta etcd "$ESPERA" 554 vigilancia-e2e.prueba\',\n'
              '    \'    V wazuh "bash $HW contar $D8 $I8 etcd 100553" > "$T"; W8=$(valor CUENTA)\',\n'
              ']\n'
              'DEBE_PASAR = ['),
             ('    \'vagrant ssh defender -c "ipset save" || falla "el manifiesto vigente no protege la VM etcd"\',\n'
              '    \'vagrant ssh control-1 -c "systemctl stop x; echo \\\\"etcd-server de la VM etcd: '
              'activo\\\\""\',\n'
              ']\n'
              'GV = "ansible/inventory/group_vars/argus_dev.yml"',
              '    \'vagrant ssh defender -c "ipset save" || falla "el manifiesto vigente no protege la VM etcd"\',\n'
              '    \'vagrant ssh control-1 -c "systemctl stop x; echo \\\\"etcd-server de la VM etcd: '
              'activo\\\\""\',\n'
              "    'for perfil in etcd vault etcd-server; do',\n"
              "    'for c in etcd-server ml-detector sniffer firewall-acl-agent; do',\n"
              "    'for m in defender client control-1 wazuh; do',\n"
              '    \'marca; etcd fim-crear; alerta control-1 "$ESPERA" 554 vigilancia-e2e.prueba\',\n'
              '    \'grep etcd "/tmp/${N}_status.txt"; }\',\n'
              "    'etcd etcd-parar',\n"
              '    \'infra() { vm control-1 "sudo /usr/local/sbin/argus-infra $1"; }\',\n'
              ']\n'
              'GV = "ansible/inventory/group_vars/argus_dev.yml"')]},
 {'ruta': 'scripts/vigilancia/lab_e2e_vigilancia.sh',
  'antes': '6b999d5244f98ae660f2e825789745a82e91d5ae119ec68d256ba82f999dc3fe',
  'despues': 'ff2679cf8b79a492d7c22ec09df67e2630faede46b1d9b3da9f45e5cd6f26ff0',
  'modo': None,
  'nuevo': None,
  'trozos': [('# del inicio del caso (scripts/vigilancia/alertas_wazuh.sh). Decisiones de Alonso: dentro de lab-e2e '
              '(DAY321); C4\n'
              '# provoca su propia divergencia y C8 solo mide en su primera corrida (DAY322).\n'
              '# Se ejecuta EN EL MAC, desde la raíz del repo, con las VMs defender, client, etcd y wazuh arriba:\n'
              '#   DIA=dayNNN bash scripts/vigilancia/lab_e2e_vigilancia.sh NOMBRE        (make lab-e2e-vigilancia)\n'
              '#\n'
              '# PREDICCIÓN (escrita antes de la primera corrida, DAY322):\n'
              '#   C1 FIM: crear un fichero en /etc/argus-pki da la 554 y borrarlo la 553 (agente etcd), cada una en '
              '< 30 s.\n'
              '#   C2 disco: umbral_pct=1 da la 100541 (estado=ALTO) en < periodo_s + 30 s; restaurado con cmp.\n'
              '#   C3 audit de Vault: chattr +i en audit.log y un login: HTTP 200 (sigue el device de syslog) y la '
              '100520 en < 30 s.',
              '# del inicio del caso (scripts/vigilancia/alertas_wazuh.sh). Decisiones de Alonso: dentro de lab-e2e '
              '(DAY321); C4\n'
              '# provoca su propia divergencia y C8 solo mide en su primera corrida (DAY322).\n'
              '# Se ejecuta EN EL MAC, desde la raíz del repo, con las VMs defender, client, control-1 y wazuh '
              'arriba:\n'
              '#   DIA=dayNNN bash scripts/vigilancia/lab_e2e_vigilancia.sh NOMBRE        (make lab-e2e-vigilancia)\n'
              '#\n'
              '# PREDICCIÓN (escrita antes de la primera corrida, DAY322):\n'
              '#   C1 FIM: crear un fichero en /etc/argus-pki da la 554 y borrarlo la 553 (agente control-1), cada '
              'una en < 30 s.\n'
              '#   C2 disco: umbral_pct=1 da la 100541 (estado=ALTO) en < periodo_s + 30 s; restaurado con cmp.\n'
              '#   C3 audit de Vault: chattr +i en audit.log y un login: HTTP 200 (sigue el device de syslog) y la '
              '100520 en < 30 s.'),
             ('\n'
              'log "0 VMs y manager"\n'
              'for m in defender client etcd wazuh; do\n'
              '  V "$m" "echo vivo" | grep -qx vivo || { log "❌ la VM $m no responde: vagrant up $m '
              '(lab-e2e-vigilancia la necesita)"; exit 1; }\n'
              'done\n'
              'V wazuh "systemctl is-active wazuh-manager; sudo /var/ossec/bin/agent_control -l" > "$T"\n'
              'grep -qx active "$T" || { cat "$T"; log "❌ wazuh-manager no está en marcha en la VM wazuh"; exit 1; '
              '}\n'
              'for a in etcd defender; do\n'
              '  grep -E "Name: $a, .*Active" "$T" > /dev/null || { cat "$T"; log "❌ el agente $a no está Active en '
              'el manager"; exit 1; }\n'
              'done\n'
              'log "   wazuh-manager en marcha; agentes etcd y defender Active"\n'
              '\n'
              'log "C1 FIM en /etc/argus-pki"\n'
              'marca; etcd fim-crear; alerta etcd "$ESPERA" 554 vigilancia-e2e.prueba\n'
              'marca; etcd fim-borrar; alerta etcd "$ESPERA" 553 vigilancia-e2e.prueba\n'
              '\n'
              'log "C2 umbral del disco bajado"\n'
              'marca; etcd disco-bajar; alerta etcd "$ESPERA_DISCO" 100541 \'estado=ALTO\'\n'
              'etcd disco-restaurar\n'
              '\n'
              'log "C3 audit de fichero de Vault inmutable"\n'
              'marca; etcd audit-romper; alerta etcd "$ESPERA" 100520\n'
              'etcd audit-restaurar\n'
              '\n'
              'log "C5 lectura ajena de una clave (Falco CRITICAL)"\n'
              'marca; etcd clave-copiar; alerta etcd "$ESPERA" 100551 argus_lab_clave_leida_ajeno\n'
              '\n'
              'log "C6 intento fallido de leer una clave (Falco WARNING)"\n'
              'marca; etcd clave-intento; alerta etcd "$ESPERA" 100552 argus_lab_clave_intento_fallido\n'
              '\n'
              'log "C8 trazas de un etcd-vm-check con etcd parado (máximo $C8_MAX, y todas en el manager)"',
              '\n'
              'log "0 VMs y manager"\n'
              'for m in defender client control-1 wazuh; do\n'
              '  V "$m" "echo vivo" | grep -qx vivo || { log "❌ la VM $m no responde: vagrant up $m '
              '(lab-e2e-vigilancia la necesita)"; exit 1; }\n'
              'done\n'
              'V wazuh "systemctl is-active wazuh-manager; sudo /var/ossec/bin/agent_control -l" > "$T"\n'
              'grep -qx active "$T" || { cat "$T"; log "❌ wazuh-manager no está en marcha en la VM wazuh"; exit 1; '
              '}\n'
              'for a in control-1 defender; do\n'
              '  grep -E "Name: $a, .*Active" "$T" > /dev/null || { cat "$T"; log "❌ el agente $a no está Active en '
              'el manager"; exit 1; }\n'
              'done\n'
              'log "   wazuh-manager en marcha; agentes control-1 y defender Active"\n'
              '\n'
              'log "C1 FIM en /etc/argus-pki"\n'
              'marca; etcd fim-crear; alerta control-1 "$ESPERA" 554 vigilancia-e2e.prueba\n'
              'marca; etcd fim-borrar; alerta control-1 "$ESPERA" 553 vigilancia-e2e.prueba\n'
              '\n'
              'log "C2 umbral del disco bajado"\n'
              'marca; etcd disco-bajar; alerta control-1 "$ESPERA_DISCO" 100541 \'estado=ALTO\'\n'
              'etcd disco-restaurar\n'
              '\n'
              'log "C3 audit de fichero de Vault inmutable"\n'
              'marca; etcd audit-romper; alerta control-1 "$ESPERA" 100520\n'
              'etcd audit-restaurar\n'
              '\n'
              'log "C5 lectura ajena de una clave (Falco CRITICAL)"\n'
              'marca; etcd clave-copiar; alerta control-1 "$ESPERA" 100551 argus_lab_clave_leida_ajeno\n'
              '\n'
              'log "C6 intento fallido de leer una clave (Falco WARNING)"\n'
              'marca; etcd clave-intento; alerta control-1 "$ESPERA" 100552 argus_lab_clave_intento_fallido\n'
              '\n'
              'log "C8 trazas de un etcd-vm-check con etcd parado (máximo $C8_MAX, y todas en el manager)"'),
             ('  W8=""; t0=$SECONDS   # que el agente mande lo último: hasta ESPERA s a que el manager tenga las F8\n'
              '  while :; do\n'
              '    V wazuh "bash $HW contar $D8 $I8 etcd 100553" > "$T"; W8=$(valor CUENTA)\n'
              '    [[ "$W8" =~ ^[0-9]+$ ]] && [ "$W8" -ge "$F8" ] && break\n'
              '    [ $(( SECONDS - t0 )) -ge "$ESPERA" ] && break',
              '  W8=""; t0=$SECONDS   # que el agente mande lo último: hasta ESPERA s a que el manager tenga las F8\n'
              '  while :; do\n'
              '    V wazuh "bash $HW contar $D8 $I8 control-1 100553" > "$T"; W8=$(valor CUENTA)\n'
              '    [[ "$W8" =~ ^[0-9]+$ ]] && [ "$W8" -ge "$F8" ] && break\n'
              '    [ $(( SECONDS - t0 )) -ge "$ESPERA" ] && break')]},
 {'ruta': 'scripts/etcd_ha/d320_antispoof_e2e.sh',
  'antes': 'b3173bbcdf356bb4b82c000d9920192a299f03e11a26519ea2a9d6a846ffe33a',
  'despues': 'b6ac71f4e5630b516fc05d762b2fee064ca46f265eb31a7dea464f26d8d9ee7e',
  'modo': None,
  'nuevo': None,
  'trozos': [('vm()    { local out rc; out=$(vagrant ssh "$1" -c "$2" 2>/dev/null); rc=$?\n'
              '          [ -n "$out" ] && printf \'%s\\n\' "$out" | tr -d \'\\r\' | grep -v \'^\\[argus\\]\'; return '
              '$rc; }\n'
              'infra() { vm etcd "sudo /usr/local/sbin/argus-infra $1"; }\n'
              'cuenta(){ vm defender "sudo iptables -w -t raw -L $1 -v -x -n 2>/dev/null | awk \'NR == 4 {print '
              '\\$1}\'"; }   # regla 2 = la de cuenta\n'
              'llegan(){ vm defender "sudo iptables -w -t mangle -L PREROUTING -v -x -n | awk \'/$1/ {print '
              '\\$1}\'"; }',
              'vm()    { local out rc; out=$(vagrant ssh "$1" -c "$2" 2>/dev/null); rc=$?\n'
              '          [ -n "$out" ] && printf \'%s\\n\' "$out" | tr -d \'\\r\' | grep -v \'^\\[argus\\]\'; return '
              '$rc; }\n'
              'infra() { vm control-1 "sudo /usr/local/sbin/argus-infra $1"; }\n'
              'cuenta(){ vm defender "sudo iptables -w -t raw -L $1 -v -x -n 2>/dev/null | awk \'NR == 4 {print '
              '\\$1}\'"; }   # regla 2 = la de cuenta\n'
              'llegan(){ vm defender "sudo iptables -w -t mangle -L PREROUTING -v -x -n | awk \'/$1/ {print '
              '\\$1}\'"; }'),
             ('paso "1 comprobaciones previas y nombres"\n'
              'git diff --quiet -- "$JSON" || falla "$JSON tiene cambios sin commit: no se toca"\n'
              'for v in client etcd; do vagrant status "$v" 2>/dev/null | grep -qE "^$v +running" || falla "la VM $v '
              'no está arriba (vagrant up $v)"; done\n'
              'read -r WL BL CHAIN AS SR SI SM K < <(python3 - "$JSON" <<\'PYEOF\'\n'
              'import json, sys',
              'paso "1 comprobaciones previas y nombres"\n'
              'git diff --quiet -- "$JSON" || falla "$JSON tiene cambios sin commit: no se toca"\n'
              'for v in client control-1; do vagrant status "$v" 2>/dev/null | grep -qE "^$v +running" || falla "la '
              'VM $v no está arriba (vagrant up $v)"; done\n'
              'read -r WL BL CHAIN AS SR SI SM K < <(python3 - "$JSON" <<\'PYEOF\'\n'
              'import json, sys')]},
 {'ruta': 'scripts/etcd_ha/d321_latido_e2e.sh',
  'antes': '4e4ba4b325fec88fb5a8e6a8bd2800394cda1582c06e85318d8538c02240e14e',
  'despues': 'f26803771d3adab9502aa86df18b51da7634cfe526601b822f0ce6ee986b6240',
  'modo': None,
  'nuevo': None,
  'trozos': [('vm()    { local out rc; out=$(vagrant ssh "$1" -c "$2" 2>/dev/null); rc=$?\n'
              '          [ -n "$out" ] && printf \'%s\\n\' "$out" | tr -d \'\\r\' | grep -v \'^\\[argus\\]\'; return '
              '$rc; }\n'
              'infra() { vm etcd "sudo /usr/local/sbin/argus-infra $1"; }\n'
              'estado(){ vm etcd "bash $EST" > "$DM/estado_$1.txt" 2>&1; grep -E \'^  (✅ |⚠️  |❌ '
              ')protegidos:|^       - [a-z].* v[0-9]+ \' "$DM/estado_$1.txt"; }\n'
              'veredicto() { grep -oE \'^\\[ETCD-VM-ESTADO\\] (SANO|NO SANO)\' "$DM/estado_$1.txt" | head -n 1; }\n'
              "publicada() { sed -nE 's/^  (✅ |⚠️  )protegidos:     v([0-9]+) publicada.*/\\2/p' "
              '"$DM/estado_$1.txt" | head -n 1; }',
              'vm()    { local out rc; out=$(vagrant ssh "$1" -c "$2" 2>/dev/null); rc=$?\n'
              '          [ -n "$out" ] && printf \'%s\\n\' "$out" | tr -d \'\\r\' | grep -v \'^\\[argus\\]\'; return '
              '$rc; }\n'
              'infra() { vm control-1 "sudo /usr/local/sbin/argus-infra $1"; }\n'
              'estado(){ vm control-1 "bash $EST" > "$DM/estado_$1.txt" 2>&1; grep -E \'^  (✅ |⚠️  |❌ '
              ')protegidos:|^       - [a-z].* v[0-9]+ \' "$DM/estado_$1.txt"; }\n'
              'veredicto() { grep -oE \'^\\[ETCD-VM-ESTADO\\] (SANO|NO SANO)\' "$DM/estado_$1.txt" | head -n 1; }\n'
              "publicada() { sed -nE 's/^  (✅ |⚠️  )protegidos:     v([0-9]+) publicada.*/\\2/p' "
              '"$DM/estado_$1.txt" | head -n 1; }'),
             (') || falla "no leo el JSON"\n'
              'LIM=$((HB + 15)); LIM3=$((CS + HB + 15))\n'
              'INICIO=$(vm etcd "date +%s")\n'
              '[[ "$INICIO" =~ ^[0-9]+$ ]] || falla "no leo la hora de la VM etcd"\n'
              'echo "    heartbeat_interval_seconds=$HB consulta_sec=$CS (límites: $LIM s y $LIM3 s); journal del '
              'etcd-server desde @$INICIO"',
              ') || falla "no leo el JSON"\n'
              'LIM=$((HB + 15)); LIM3=$((CS + HB + 15))\n'
              'INICIO=$(vm control-1 "date +%s")\n'
              '[[ "$INICIO" =~ ^[0-9]+$ ]] || falla "no leo la hora de la VM etcd"\n'
              'echo "    heartbeat_interval_seconds=$HB consulta_sec=$CS (límites: $LIM s y $LIM3 s); journal del '
              'etcd-server desde @$INICIO"'),
             ('paso "6 L4 sin rechazos de datos del latido"\n'
              'r1=$(grep -cE "\\[ETCD-CLIENTE-LATIDO-DATOS-RECHAZADOS\\]|no se guarda \\(datos del latido" "$F")\n'
              'r2=$(vm etcd "sudo journalctl -u $UNIDAD --since @$INICIO --no-pager | grep -c '
              '\'\\[ETCD-LATIDO-DATOS-RECHAZADOS\\]\'")\n'
              '[ "$r1" = 0 ] && pasa "L4 0 rechazos en el log del firewall" || mal "L4 $r1 rechazos en el log del '
              'firewall"\n'
              '[ "${r2:-x}" = 0 ] && pasa "L4 0 [ETCD-LATIDO-DATOS-RECHAZADOS] en el journal del etcd-server" || mal '
              '"L4 ${r2:-sin respuesta} rechazos en el journal del etcd-server"',
              'paso "6 L4 sin rechazos de datos del latido"\n'
              'r1=$(grep -cE "\\[ETCD-CLIENTE-LATIDO-DATOS-RECHAZADOS\\]|no se guarda \\(datos del latido" "$F")\n'
              'r2=$(vm control-1 "sudo journalctl -u $UNIDAD --since @$INICIO --no-pager | grep -c '
              '\'\\[ETCD-LATIDO-DATOS-RECHAZADOS\\]\'")\n'
              '[ "$r1" = 0 ] && pasa "L4 0 rechazos en el log del firewall" || mal "L4 $r1 rechazos en el log del '
              'firewall"\n'
              '[ "${r2:-x}" = 0 ] && pasa "L4 0 [ETCD-LATIDO-DATOS-RECHAZADOS] en el journal del etcd-server" || mal '
              '"L4 ${r2:-sin respuesta} rechazos en el journal del etcd-server"')]},
 {'ruta': 'scripts/etcd_ha/d321_medir_falco_hijos.sh',
  'antes': 'd035101e3359efd5f70b5fb6163888a40ff4b911f3172f04bb31e9eeadd599d9',
  'despues': 'fe26c1fe1b86d93e9f921473676898a5849262c57cee18ff9d4bc8d2f492edf1',
  'modo': None,
  'nuevo': None,
  'trozos': [('H=$(shasum -a 256 "$DEB" | cut -d\' \' -f1)\n'
              'grep -q "$H" dist/vendor/CHECKSUMS 2>/dev/null || { echo "PARADA: el sha256 de $DEB no está en '
              'dist/vendor/CHECKSUMS"; exit 1; }\n'
              'for v in client etcd; do vagrant status "$v" 2>/dev/null | grep -qE "^$v +running" || { echo "PARADA: '
              'la VM $v no está arriba"; exit 1; }; done\n'
              'git diff --quiet -- firewall-acl-agent/config/firewall.json || { echo "PARADA: firewall.json con '
              'cambios sin commit (lab-e2e-mitigacion no arrancaría)"; exit 1; }\n'
              'mkdir -p "$DM"',
              'H=$(shasum -a 256 "$DEB" | cut -d\' \' -f1)\n'
              'grep -q "$H" dist/vendor/CHECKSUMS 2>/dev/null || { echo "PARADA: el sha256 de $DEB no está en '
              'dist/vendor/CHECKSUMS"; exit 1; }\n'
              'for v in client control-1; do vagrant status "$v" 2>/dev/null | grep -qE "^$v +running" || { echo '
              '"PARADA: la VM $v no está arriba"; exit 1; }; done\n'
              'git diff --quiet -- firewall-acl-agent/config/firewall.json || { echo "PARADA: firewall.json con '
              'cambios sin commit (lab-e2e-mitigacion no arrancaría)"; exit 1; }\n'
              'mkdir -p "$DM"'),
             ("json_include_output_property: true'\n"
              '\n'
              'for V in etcd defender; do\n'
              '  echo; echo "=== [$(date +%T)] 1 Falco con las reglas de medida en $V"\n'
              '  if vm "$V" "dpkg-query -W -f=\'\\${Status}\' falco 2>/dev/null | grep -q \'install ok installed\'"; '
              'then',
              "json_include_output_property: true'\n"
              '\n'
              'for V in control-1 defender; do\n'
              '  echo; echo "=== [$(date +%T)] 1 Falco con las reglas de medida en $V"\n'
              '  if vm "$V" "dpkg-query -W -f=\'\\${Status}\' falco 2>/dev/null | grep -q \'install ok installed\'"; '
              'then'),
             ('  vm "$V" "pgrep -x falco > /dev/null" || { echo "PARADA: falco no arrancó en $V"; vm "$V" "sudo '
              'journalctl -u $UNIDAD -n 15 --no-pager"; exit 1; }\n'
              'done\n'
              'T0=$(vm etcd "date +%s"); T0D=$(vm defender "date +%s")\n'
              '\n'
              'echo; echo "=== [$(date +%T)] 2 carga de trabajo"',
              '  vm "$V" "pgrep -x falco > /dev/null" || { echo "PARADA: falco no arrancó en $V"; vm "$V" "sudo '
              'journalctl -u $UNIDAD -n 15 --no-pager"; exit 1; }\n'
              'done\n'
              'T0=$(vm control-1 "date +%s"); T0D=$(vm defender "date +%s")\n'
              '\n'
              'echo; echo "=== [$(date +%T)] 2 carga de trabajo"'),
             ('sleep 40\n'
              '\n'
              'for V in etcd defender; do\n'
              '  t=$T0; [ "$V" = defender ] && t=$T0D\n'
              '  echo; echo "=== [$(date +%T)] 3 resultado en $V"',
              'sleep 40\n'
              '\n'
              'for V in control-1 defender; do\n'
              '  t=$T0; [ "$V" = defender ] && t=$T0D\n'
              '  echo; echo "=== [$(date +%T)] 3 resultado en $V"')]}]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: python3 -I scripts/etcd_ha/d325_nombre_viejo.py --check | --apply"); return 2
    if not (os.path.isfile("Vagrantfile") and os.path.isdir(".git")):
        print("[D325-NOMBRE] PARADA: no estoy en la raíz del repo"); return 1
    plan, errores, ya = [], [], 0
    for f in FICHEROS:
        r = f["ruta"]
        actual = open(r, "rb").read() if os.path.isfile(r) else None
        if actual is not None and sha(actual) == f["despues"]:
            print("[D325-NOMBRE] YA-APLICADO  %s" % r); ya += 1; continue
        if f["nuevo"] is not None:
            if actual is not None:
                errores.append("%s existe con otro contenido (sha256 %s): no se pisa" % (r, sha(actual))); continue
            nuevo = f["nuevo"].encode("utf-8")
        else:
            if actual is None:
                errores.append("%s no existe" % r); continue
            if sha(actual) != f["antes"]:
                errores.append("%s: sha256 de partida %s, se exige %s" % (r, sha(actual), f["antes"])); continue
            t = actual.decode("utf-8")
            mal = False
            for i, (viejo, nuevo_t) in enumerate(f["trozos"], 1):
                c = t.count(viejo)
                if c != 1:
                    errores.append("%s: el ancla %d aparece %d veces (se exige 1)" % (r, i, c)); mal = True; break
                t = t.replace(viejo, nuevo_t)
            if mal: continue
            nuevo = t.encode("utf-8")
        if sha(nuevo) != f["despues"]:
            errores.append("%s: el resultado tendría sha256 %s, se exige %s" % (r, sha(nuevo), f["despues"])); continue
        plan.append((f, nuevo))
    if errores:
        for e in errores: print("[D325-NOMBRE] ERROR  " + e)
        print("[D325-NOMBRE] PARADA: no se escribe nada"); return 1
    if not plan:
        print("[D325-NOMBRE] todo aplicado ya (%d ficheros): nada que hacer" % ya); return 0
    for f, nuevo in plan:
        print("[D325-NOMBRE] %s  %s -> sha256 %s%s" % ("APLICA" if sys.argv[1] == "--apply" else "CHECK ", f["ruta"],
              f["despues"], " (nuevo)" if f["nuevo"] is not None else " (%d anclas)" % len(f["trozos"])))
    if sys.argv[1] == "--check":
        print("[D325-NOMBRE] --check: %d ficheros por cambiar, %d ya aplicados; nada escrito" % (len(plan), ya)); return 0
    for f, nuevo in plan:
        d = os.path.dirname(f["ruta"]) or "."
        modo = f["modo"] if f["modo"] is not None else (os.stat(f["ruta"]).st_mode & 0o777)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".d325_")
        with os.fdopen(fd, "wb") as h: h.write(nuevo)
        os.chmod(tmp, modo); os.replace(tmp, f["ruta"])
    print("[D325-NOMBRE] aplicado: %d ficheros" % len(plan)); return 0


if __name__ == "__main__":
    sys.exit(main())
