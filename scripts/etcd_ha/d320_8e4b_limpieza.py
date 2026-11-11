#!/usr/bin/env python3
# d320_8e4b_limpieza.py — DAY320, 8e.4b: los traps de los E2E con mitigación real retiran también la cadena raw
# del antispoofing y sus sets (medido: quedaban ARGUS_ANTISPOOF{,_IF,_MAC} en modo descarta y 4 sets en el defender).
# Ayudante único d320_limpia_kernel.sh (+ --contar), test 9/9, lab-test-limpia-kernel y lab-kernel-limpio en lab-e2e.
# d302: iptables.chain_name se lee del JSON (antes escrita en el script).
# Uso (raíz del repo, Mac): python3 scripts/etcd_ha/d320_8e4b_limpieza.py --check | --apply
#
# Uso, desde la raíz del repo:
#   python3 -I scripts/etcd_ha/d320_8e4b_limpieza.py --check
#   python3 -I scripts/etcd_ha/d320_8e4b_limpieza.py --apply
# Todo o nada: comprueba el sha256 de cada fichero (y que los nuevos no existan) antes de escribir ninguno.
# Idempotente: si todos tienen ya el sha256 de después, no toca nada. Salidas: 0 bien, 1 no aplicable, 2 uso.
import hashlib, json, os, sys, tempfile

CAMBIOS = json.loads(r"""[
 {
  "ruta": "Makefile",
  "antes": "3114dacbfb4d157d85fc8f349bd0053a1a25eca94de314e30a88c1290eba11a8",
  "despues": "645f2adef7075898f70b61189d3856d15fb80c5e706dbef8b2e6da8e6942048b",
  "bloques": [
   {
    "viejo": "# lab_corrida_defender.sh exige DIA con formato dayNNN (medido DAY303)\nLAB_E2E_DIA ?= day303\n.PHONY: lab-e2e lab-e2e-prep lab-e2e-reinicio-antes lab-e2e-reinicio-ordenada lab-e2e-reinicio-kill9 lab-e2e-protegidos lab-e2e-mitigacion lab-e2e-vigia lab-e2e-antispoof lab-e2e-reinicio-etcd\nlab-e2e-prep:\n\t@echo \"[LAB-E2E] client: alias 192.168.100.51 en eth1 y MAC de 192.168.100.1 en la tabla de vecinos\"\n",
    "nuevo": "# lab_corrida_defender.sh exige DIA con formato dayNNN (medido DAY303)\nLAB_E2E_DIA ?= day303\n.PHONY: lab-e2e lab-e2e-prep lab-e2e-reinicio-antes lab-e2e-reinicio-ordenada lab-e2e-reinicio-kill9 lab-e2e-protegidos lab-e2e-mitigacion lab-e2e-vigia lab-e2e-antispoof lab-e2e-reinicio-etcd lab-test-limpia-kernel lab-kernel-limpio\nlab-e2e-prep:\n\t@echo \"[LAB-E2E] client: alias 192.168.100.51 en eth1 y MAC de 192.168.100.1 en la tabla de vecinos\"\n"
   },
   {
    "viejo": "\tDIA=$(LAB_E2E_DIA) bash scripts/etcd_ha/d320_antispoof_e2e.sh lab_antispoof_$$(date -u +%Y%m%dT%H%M%SZ)\n\n# [REINICIO-VM-D317] sexto E2E: reinicia el etcd-server de la VM etcd con el pipeline vivo (scripts/etcd_ha/d317_reinicio_vm.sh,\n# veredicto PASA/FALLA). Requiere el pipeline arrancado: va al final de lab-e2e, tras la restauración. El nombre de la\n",
    "nuevo": "\tDIA=$(LAB_E2E_DIA) bash scripts/etcd_ha/d320_antispoof_e2e.sh lab_antispoof_$$(date -u +%Y%m%dT%H%M%SZ)\n\n# [PROTEGIDOS-LIMPIEZA-D320] los E2E con la mitigación real (mitigacion, vigia, antispoof) dejan el pipeline parado y\n# limpian el kernel en su trap con scripts/etcd_ha/d320_limpia_kernel.sh (cadena del filtro, cadena raw del antispoofing\n# y sus sets; medido DAY320: sin la raw quedaban sets=1). lab-test-limpia-kernel prueba el ayudante en el defender con\n# nombres propios (no toca los del pipeline); lab-kernel-limpio comprueba, sin tocar nada (--contar), que tras cada uno\n# no queda nada con los nombres de firewall.json. Pipeline parado: si está vivo, sus cadenas y sets son legítimos.\nlab-test-limpia-kernel:\n\t@vagrant ssh defender -c \"sudo bash /vagrant/scripts/etcd_ha/test_d320_limpia_kernel.sh\" 2>/dev/null | tr -d '\\r' | grep -v '^\\[argus\\]' > /tmp/argus_test_limpia.txt; cat /tmp/argus_test_limpia.txt; grep -qE '^([0-9]+)/\\1 PASA' /tmp/argus_test_limpia.txt || { echo \"[LAB-E2E] FALLA: test_d320_limpia_kernel\"; exit 1; }\n\nlab-kernel-limpio:\n\t@n=$$(python3 -c 'import json; d = json.load(open(\"firewall-acl-agent/config/firewall.json\")); p = d.get(\"protegidos\", {}); a = p.get(\"antispoof\", {}); print(d[\"iptables\"][\"chain_name\"], a.get(\"cadena\", \"ARGUS_ANTISPOOF\"), a.get(\"set_redes\", \"ml_defender_prot_redes\"), a.get(\"set_ips_mac\", \"ml_defender_prot_ipmac\"), a.get(\"set_mac\", \"ml_defender_prot_mac\"), d[\"ipsets\"][\"blacklist\"][\"set_name\"], p.get(\"set_name\", \"ml_defender_protegidos\"))') || { echo \"[LAB-E2E] FALLA: no leo firewall.json\"; exit 1; }; \\\n\tvagrant ssh defender -c \"sudo bash /vagrant/scripts/etcd_ha/d320_limpia_kernel.sh --contar $$n\" 2>/dev/null | tr -d '\\r' | grep -v '^\\[argus\\]' > /tmp/argus_kernel_limpio.txt; cat /tmp/argus_kernel_limpio.txt; \\\n\tgrep -qx '    quedan raw=0 filter=0 sets=0' /tmp/argus_kernel_limpio.txt && echo \"[LAB-E2E] kernel limpio ($$n)\" || { echo \"[LAB-E2E] FALLA: restos en el kernel del defender (sudo bash /vagrant/scripts/etcd_ha/d320_limpia_kernel.sh $$n)\"; exit 1; }\n\n# [REINICIO-VM-D317] sexto E2E: reinicia el etcd-server de la VM etcd con el pipeline vivo (scripts/etcd_ha/d317_reinicio_vm.sh,\n# veredicto PASA/FALLA). Requiere el pipeline arrancado: va al final de lab-e2e, tras la restauración. El nombre de la\n"
   },
   {
    "viejo": "lab-e2e:\n\t@echo \"[LAB-E2E] inicio $$(date '+%F %T'): reinicio antes/ordenada/kill9, protegidos, mitigacion, vigia, antispoof, reinicio del etcd-server\"\n\t$(MAKE) lab-e2e-reinicio-antes\n\t$(MAKE) lab-e2e-reinicio-ordenada\n",
    "nuevo": "lab-e2e:\n\t@echo \"[LAB-E2E] inicio $$(date '+%F %T'): reinicio antes/ordenada/kill9, protegidos, mitigacion, vigia, antispoof, reinicio del etcd-server\"\n\t$(MAKE) lab-test-limpia-kernel\n\t$(MAKE) lab-e2e-reinicio-antes\n\t$(MAKE) lab-e2e-reinicio-ordenada\n"
   },
   {
    "viejo": "\t$(MAKE) lab-e2e-protegidos\n\t$(MAKE) lab-e2e-mitigacion\n\t$(MAKE) lab-e2e-vigia\n\t$(MAKE) lab-e2e-antispoof\n\t@echo \"[LAB-E2E] [ARGUS-LAB-RESTORE-D303] los E2E paran el pipeline: se deja arrancado, como se encontro\"\n\t$(MAKE) pipeline-start > /tmp/argus_lab_e2e_restore.txt 2>&1 || { tail -n 20 /tmp/argus_lab_e2e_restore.txt; echo \"[LAB-E2E] FALLA: pipeline-start al restaurar\"; exit 1; }\n",
    "nuevo": "\t$(MAKE) lab-e2e-protegidos\n\t$(MAKE) lab-e2e-mitigacion\n\t$(MAKE) lab-kernel-limpio\n\t$(MAKE) lab-e2e-vigia\n\t$(MAKE) lab-kernel-limpio\n\t$(MAKE) lab-e2e-antispoof\n\t$(MAKE) lab-kernel-limpio\n\t@echo \"[LAB-E2E] [ARGUS-LAB-RESTORE-D303] los E2E paran el pipeline: se deja arrancado, como se encontro\"\n\t$(MAKE) pipeline-start > /tmp/argus_lab_e2e_restore.txt 2>&1 || { tail -n 20 /tmp/argus_lab_e2e_restore.txt; echo \"[LAB-E2E] FALLA: pipeline-start al restaurar\"; exit 1; }\n"
   }
  ],
  "modo": null
 },
 {
  "ruta": "scripts/timebase/d302_mitigacion_e2e.sh",
  "antes": "4369a0d22f1c25f925ae1d1790a22a36f3fbc6bd3a7b1fde9cecc134961d6226",
  "despues": "6e4938995402470cf8fa69c90bf68c7d5612c6e5855217928c55bc73bc5d3ec3",
  "bloques": [
   {
    "viejo": "JSON=firewall-acl-agent/config/firewall.json\nBAK=/tmp/$N.firewall.json.orig\nCHAIN=ML_DEFENDER_TEST\nF=logs/lab/firewall-agent.log\nBL=\"\"\n",
    "nuevo": "JSON=firewall-acl-agent/config/firewall.json\nBAK=/tmp/$N.firewall.json.orig\nCHAIN=\"\"   # [PROTEGIDOS-LIMPIEZA-D320] de iptables.chain_name (paso 1), antes escrita aquí\nF=logs/lab/firewall-agent.log\nBL=\"\"\n"
   },
   {
    "viejo": "  make pipeline-stop > \"/tmp/${N}_stop_trap.txt\" 2>&1\n  echo \"    pipeline-stop rc=$?\"\n  if [ -n \"$BL\" ]; then\n    vagrant ssh defender -c \"while sudo iptables -D INPUT -j $CHAIN 2>/dev/null; do :; done; sudo iptables -F $CHAIN 2>/dev/null; sudo iptables -X $CHAIN 2>/dev/null; sudo ipset destroy $BL 2>/dev/null; sudo ipset destroy $WL 2>/dev/null; echo \\\"    quedan reglas=\\$(sudo iptables -S | grep -c $CHAIN) sets=\\$(sudo ipset list -n | grep -c -x -e $BL -e $WL)\\\"\" 2>/dev/null | tr -d '\\r' | grep -v '^\\[argus\\]'\n  fi\n  if [ \"$JSON_TOCADO\" = 1 ] && [ -f \"$BAK\" ]; then\n",
    "nuevo": "  make pipeline-stop > \"/tmp/${N}_stop_trap.txt\" 2>&1\n  echo \"    pipeline-stop rc=$?\"\n  if [ -n \"$BL\" ] && [ -n \"$CHAIN\" ]; then\n    # [PROTEGIDOS-LIMPIEZA-D320] también la cadena raw del antispoofing y sus sets (usa el de protegidos: si no se\n    # quita antes, 'ipset destroy' de éste falla; medido DAY320, quedaban sets=1).\n    vagrant ssh defender -c \"sudo bash /vagrant/scripts/etcd_ha/d320_limpia_kernel.sh $CHAIN ${AS:--} $SR $SI $SM $BL $WL\" 2>/dev/null | tr -d '\\r' | grep -v '^\\[argus\\]'\n  fi\n  if [ \"$JSON_TOCADO\" = 1 ] && [ -f \"$BAK\" ]; then\n"
   },
   {
    "viejo": "BL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[\"ipsets\"][\"blacklist\"][\"set_name\"])' \"$JSON\") || falla \"no leo ipsets.blacklist.set_name\"\nWL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(\"protegidos\", {}).get(\"set_name\", \"ml_defender_protegidos\"))' \"$JSON\") || falla \"no leo protegidos.set_name\"  # [PROTEGIDOS-MANIFIESTO-D318]\necho \"    blacklist=$BL whitelist=$WL cadena=$CHAIN\"\n# [PROTEGIDOS-C7-D320] C7 (ADR-060, el escenario del DAY317): la VM etcd tiene que estar arriba, con su chrony\n# contra el defender durante el ataque NTP; sin ella la prueba de que .20 nunca entra en el blacklist no vale nada.\n",
    "nuevo": "BL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[\"ipsets\"][\"blacklist\"][\"set_name\"])' \"$JSON\") || falla \"no leo ipsets.blacklist.set_name\"\nWL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(\"protegidos\", {}).get(\"set_name\", \"ml_defender_protegidos\"))' \"$JSON\") || falla \"no leo protegidos.set_name\"  # [PROTEGIDOS-MANIFIESTO-D318]\nCHAIN=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[\"iptables\"][\"chain_name\"])' \"$JSON\") || falla \"no leo iptables.chain_name\"\n[ -n \"$CHAIN\" ] || falla \"iptables.chain_name vacío\"\n# [PROTEGIDOS-LIMPIEZA-D320] nombres del antispoofing (ADR-060 D8), con los mismos valores por defecto que el agente.\nread -r AS SR SI SM < <(python3 -c 'import json,sys; a = json.load(open(sys.argv[1])).get(\"protegidos\", {}).get(\"antispoof\", {}); print(a.get(\"cadena\", \"ARGUS_ANTISPOOF\"), a.get(\"set_redes\", \"ml_defender_prot_redes\"), a.get(\"set_ips_mac\", \"ml_defender_prot_ipmac\"), a.get(\"set_mac\", \"ml_defender_prot_mac\"))' \"$JSON\") || falla \"no leo protegidos.antispoof\"\necho \"    blacklist=$BL whitelist=$WL cadena=$CHAIN antispoof=$AS sets=$SR,$SI,$SM\"\n# [PROTEGIDOS-C7-D320] C7 (ADR-060, el escenario del DAY317): la VM etcd tiene que estar arriba, con su chrony\n# contra el defender durante el ataque NTP; sin ella la prueba de que .20 nunca entra en el blacklist no vale nada.\n"
   }
  ],
  "modo": null
 },
 {
  "ruta": "scripts/etcd_ha/d320_vigia_e2e.sh",
  "antes": "d063caabe6e9e37ba82b7c9c477979a8aa2b63ad66ed82cc8c8e3c26365c4784",
  "despues": "3715832da1e727704f87cc910f03c6b85e1335e6676f29d6b2851e5605f2f903",
  "bloques": [
   {
    "viejo": "BAK=/tmp/$N.firewall.json.orig\nF=logs/lab/firewall-agent.log\nWL=\"\"; CHAIN=\"\"; BL=\"\"; K=0\nJSON_TOCADO=0; RESTAURADO=0; FALLOS=0\npaso()  { echo; echo \"=== [$(date +%T)] $*\"; }\n",
    "nuevo": "BAK=/tmp/$N.firewall.json.orig\nF=logs/lab/firewall-agent.log\nWL=\"\"; CHAIN=\"\"; BL=\"\"; AS=\"\"; SR=\"\"; SI=\"\"; SM=\"\"; K=0\nJSON_TOCADO=0; RESTAURADO=0; FALLOS=0\npaso()  { echo; echo \"=== [$(date +%T)] $*\"; }\n"
   },
   {
    "viejo": "  def \"sudo iptables -D INPUT -m comment --comment d320-vigia-extra 2>/dev/null; true\" > /dev/null\n  if [ -n \"$WL\" ]; then\n    def \"while sudo iptables -D INPUT -j $CHAIN 2>/dev/null; do :; done; sudo iptables -F $CHAIN 2>/dev/null; sudo iptables -X $CHAIN 2>/dev/null; sudo ipset destroy $BL 2>/dev/null; sudo ipset destroy $WL 2>/dev/null; echo \\\"    quedan reglas=\\$(sudo iptables -S | grep -c -e $CHAIN -e d320-vigia-extra) sets=\\$(sudo ipset list -n | grep -c -x -e $BL -e $WL)\\\"\"\n  fi\n  if [ \"$JSON_TOCADO\" = 1 ] && [ -f \"$BAK\" ]; then\n",
    "nuevo": "  def \"sudo iptables -D INPUT -m comment --comment d320-vigia-extra 2>/dev/null; true\" > /dev/null\n  if [ -n \"$WL\" ]; then\n    # [PROTEGIDOS-LIMPIEZA-D320] también la cadena raw del antispoofing y sus sets (medido DAY320: quedaban sets=1).\n    def \"sudo bash /vagrant/scripts/etcd_ha/d320_limpia_kernel.sh $CHAIN $AS $SR $SI $SM $BL $WL; echo \\\"    quedan reglas d320-vigia-extra=\\$(sudo iptables -S | grep -c d320-vigia-extra)\\\"\"\n  fi\n  if [ \"$JSON_TOCADO\" = 1 ] && [ -f \"$BAK\" ]; then\n"
   },
   {
    "viejo": "paso \"1 JSON de serie, nombres y periodo del vigía\"\ngit diff --quiet -- \"$JSON\" || falla \"$JSON tiene cambios sin commit: no se toca\"\nread -r WL CHAIN BL K < <(python3 - \"$JSON\" <<'PYEOF'\nimport json, sys\nd = json.load(open(sys.argv[1], encoding=\"utf-8\"))\np = d.get(\"protegidos\", {})\nprint(p.get(\"set_name\", \"ml_defender_protegidos\"), d[\"iptables\"][\"chain_name\"], d[\"ipsets\"][\"blacklist\"][\"set_name\"],\n      p.get(\"comprobacion_kernel_sec\", 30))\nPYEOF\n) || falla \"no leo el JSON\"\n",
    "nuevo": "paso \"1 JSON de serie, nombres y periodo del vigía\"\ngit diff --quiet -- \"$JSON\" || falla \"$JSON tiene cambios sin commit: no se toca\"\nread -r WL CHAIN BL K AS SR SI SM < <(python3 - \"$JSON\" <<'PYEOF'\nimport json, sys\nd = json.load(open(sys.argv[1], encoding=\"utf-8\"))\np = d.get(\"protegidos\", {}); a = p.get(\"antispoof\", {})\nprint(p.get(\"set_name\", \"ml_defender_protegidos\"), d[\"iptables\"][\"chain_name\"], d[\"ipsets\"][\"blacklist\"][\"set_name\"],\n      p.get(\"comprobacion_kernel_sec\", 30), a.get(\"cadena\", \"ARGUS_ANTISPOOF\"), a.get(\"set_redes\", \"ml_defender_prot_redes\"),\n      a.get(\"set_ips_mac\", \"ml_defender_prot_ipmac\"), a.get(\"set_mac\", \"ml_defender_prot_mac\"))\nPYEOF\n) || falla \"no leo el JSON\"\n"
   }
  ],
  "modo": null
 },
 {
  "ruta": "scripts/etcd_ha/d320_antispoof_e2e.sh",
  "antes": "3066cc13bd9ccb330a2d9b5f2b117889ab190807ea541f101c1f830a0e45e36d",
  "despues": "c8e9f504385e602a57dec4d6f0645dbcae5188d862153be46c6dc94ba87ec260",
  "bloques": [
   {
    "viejo": "  vm defender \"sudo ip netns del $NS 2>/dev/null; sudo ip link del $VA 2>/dev/null; sudo iptables -w -t mangle -D PREROUTING -i eth2 -s $IP62 -m comment --comment d320as-62 2>/dev/null; sudo iptables -w -t mangle -D PREROUTING -i $VA -s 192.168.100.20 -m comment --comment d320as-20 2>/dev/null; true\" > /dev/null\n  if [ -n \"$AS\" ]; then\n    vm defender \"while sudo iptables -w -t raw -D PREROUTING -j $AS 2>/dev/null; do :; done; for c in $AS ${AS}_IF ${AS}_MAC; do sudo iptables -w -t raw -F \\$c 2>/dev/null; done; for c in $AS ${AS}_IF ${AS}_MAC; do sudo iptables -w -t raw -X \\$c 2>/dev/null; done; while sudo iptables -D INPUT -j $CHAIN 2>/dev/null; do :; done; sudo iptables -F $CHAIN 2>/dev/null; sudo iptables -X $CHAIN 2>/dev/null; for s in $SR $SI $SM $BL $WL; do sudo ipset destroy \\$s 2>/dev/null; done; echo \\\"    quedan raw=\\$(sudo iptables -w -t raw -S | grep -c $AS) filter=\\$(sudo iptables -S | grep -c $CHAIN) sets=\\$(sudo ipset list -n | grep -c -x -e $SR -e $SI -e $SM -e $BL -e $WL)\\\"\"\n  fi\n  if [ \"$JSON_TOCADO\" = 1 ] && [ -f \"$BAK\" ]; then\n",
    "nuevo": "  vm defender \"sudo ip netns del $NS 2>/dev/null; sudo ip link del $VA 2>/dev/null; sudo iptables -w -t mangle -D PREROUTING -i eth2 -s $IP62 -m comment --comment d320as-62 2>/dev/null; sudo iptables -w -t mangle -D PREROUTING -i $VA -s 192.168.100.20 -m comment --comment d320as-20 2>/dev/null; true\" > /dev/null\n  if [ -n \"$AS\" ]; then\n    vm defender \"sudo bash /vagrant/scripts/etcd_ha/d320_limpia_kernel.sh $CHAIN $AS $SR $SI $SM $BL $WL\"   # [PROTEGIDOS-LIMPIEZA-D320] un solo sitio\n  fi\n  if [ \"$JSON_TOCADO\" = 1 ] && [ -f \"$BAK\" ]; then\n"
   }
  ],
  "modo": null
 },
 {
  "ruta": "scripts/etcd_ha/d320_limpia_kernel.sh",
  "antes": null,
  "despues": "e28f57850635cfc6edd7f39c489a0cade170a5510d45d2ac1056182aa6593e1b",
  "nuevo_b64": null,
  "contenido": "#!/usr/bin/env bash\n# [PROTEGIDOS-LIMPIEZA-D320] DAY320. Retira del kernel lo que deja el firewall-acl-agent tras un E2E: el salto de INPUT,\n# la cadena del filtro, el salto de raw PREROUTING y las tres cadenas del antispoofing (ADR-060 D8, 8e.4b) y los sets.\n# Corre EN EL DEFENDER (como root). Los nombres NO van aquí: los pasa quien lo llama, leídos de firewall.json.\n#\n# Por qué existe (medido DAY320): los traps de d302_mitigacion_e2e.sh y d320_vigia_e2e.sh borraban la cadena del filtro\n# y los sets, pero no la cadena raw del antispoofing. Como ésta usa el set de protegidos, 'ipset destroy' fallaba en\n# silencio y quedaban en el defender ARGUS_ANTISPOOF{,_IF,_MAC} (en modo descarta) y los cuatro sets (quedan sets=1).\n# El orden importa: primero los saltos y las cadenas (raw y filter), después los sets, que ya nadie referencia.\n#\n# Uso:  sudo bash d320_limpia_kernel.sh [--contar] CADENA_FILTER CADENA_ANTISPOOF SET [SET...]\n#       (CADENA_ANTISPOOF puede ser '-' si no hay antispoofing que retirar; --contar solo cuenta, no toca nada:\n#        es la comprobación de lab-kernel-limpio al final de lab-e2e)\n# Salida: una línea \"quedan raw=N filter=N sets=N\"; código 0 si todo es 0, 1 si queda algo, 2 si el uso es malo.\nset -u\nCONTAR=0; [ \"${1:-}\" = \"--contar\" ] && { CONTAR=1; shift; }\nif [ \"$#\" -lt 3 ]; then echo \"uso: $0 CADENA_FILTER CADENA_ANTISPOOF SET [SET...]\" >&2; exit 2; fi\nCH=$1; AS=$2; shift 2\nfor n in \"$CH\" \"$AS\" \"$@\"; do\n  case \"$n\" in ''|*[!A-Za-z0-9_.-]*) echo \"nombre no válido: '$n'\" >&2; exit 2 ;; esac\ndone\n\nif [ \"$CONTAR\" = 0 ] && [ \"$AS\" != \"-\" ]; then\n  while iptables -w -t raw -D PREROUTING -j \"$AS\" 2>/dev/null; do :; done\n  for c in \"$AS\" \"${AS}_IF\" \"${AS}_MAC\"; do iptables -w -t raw -F \"$c\" 2>/dev/null; done\n  for c in \"$AS\" \"${AS}_IF\" \"${AS}_MAC\"; do iptables -w -t raw -X \"$c\" 2>/dev/null; done\nfi\nif [ \"$CONTAR\" = 0 ]; then\n  while iptables -w -D INPUT -j \"$CH\" 2>/dev/null; do :; done\n  iptables -w -F \"$CH\" 2>/dev/null\n  iptables -w -X \"$CH\" 2>/dev/null\n  for s in \"$@\"; do ipset destroy \"$s\" 2>/dev/null; done\nfi\n\nraw=0\n[ \"$AS\" != \"-\" ] && raw=$(iptables -w -t raw -S | grep -c -w -e \"$AS\" -e \"${AS}_IF\" -e \"${AS}_MAC\")\nfilter=$(iptables -w -S | grep -c -w -e \"$CH\")\npat=(); for s in \"$@\"; do pat+=(-e \"$s\"); done\nsets=$(ipset list -n | grep -c -x \"${pat[@]}\")\necho \"    quedan raw=$raw filter=$filter sets=$sets\"\n[ \"$raw\" = 0 ] && [ \"$filter\" = 0 ] && [ \"$sets\" = 0 ]\n",
  "modo": 493
 },
 {
  "ruta": "scripts/etcd_ha/test_d320_limpia_kernel.sh",
  "antes": null,
  "despues": "a68ec700fcc30bd4bbb807c712bfc29bc62b5608a16be55c10ffc59b59a69854",
  "nuevo_b64": null,
  "contenido": "#!/usr/bin/env bash\n# [PROTEGIDOS-LIMPIEZA-D320] Test de d320_limpia_kernel.sh. Necesita root, iptables e ipset. Usa nombres PROPIOS\n# (D320T_*, d320t_*), así que se puede correr en el defender sin tocar las cadenas ni los sets del pipeline.\n# Reproduce el estado medido en el defender el DAY320 (cadena raw del antispoofing que usa el set de protegidos) y\n# comprueba: que la limpieza antigua lo deja (el test discrimina), que la nueva lo quita entero, que no toca nombres\n# parecidos, idempotencia, saltos repetidos, sin antispoofing ('-'), uso malo, que avisa (rc 1) si algo ajeno\n# sigue usando un set y que --contar cuenta sin tocar.\n# Uso: sudo bash scripts/etcd_ha/test_d320_limpia_kernel.sh      Salida: N/M PASA; rc 0 si todo pasa, 77 sin root.\nset -u\nL=\"$(cd \"$(dirname \"$0\")\" && pwd)/d320_limpia_kernel.sh\"\n[ \"$(id -u)\" = 0 ] || { echo \"SKIP: necesita root\"; exit 77; }\ncommand -v ipset > /dev/null && command -v iptables > /dev/null || { echo \"SKIP: faltan iptables/ipset\"; exit 77; }\n\nCH=D320T_FILTER; AS=D320T_AS; WL=d320t_prot; BL=d320t_bl; SR=d320t_redes; SI=d320t_ipmac; SM=d320t_mac\nPARECIDOS_CAD=\"D320T_ASX D320T_FILTERX\"; PARECIDOS_SET=\"d320t_prot_x d320t_blx\"\nSETS=\"$SR $SI $SM $BL $WL\"\nOK=0; TOT=0\npasa() { OK=$((OK + 1)); TOT=$((TOT + 1)); echo \"PASA  $*\"; }\nmal()  { TOT=$((TOT + 1)); echo \"FALLA $*\"; }\nlimpia_todo() {\n  iptables -w -D INPUT -m set --match-set $WL src -m comment --comment d320t-ajeno -j ACCEPT 2>/dev/null\n  bash \"$L\" \"$CH\" \"$AS\" $SETS > /dev/null 2>&1 || true\n  for c in $PARECIDOS_CAD; do\n    iptables -w -t raw -F \"$c\" 2>/dev/null; iptables -w -t raw -X \"$c\" 2>/dev/null\n    iptables -w -F \"$c\" 2>/dev/null; iptables -w -X \"$c\" 2>/dev/null\n  done\n  for s in $PARECIDOS_SET; do ipset destroy \"$s\" 2>/dev/null; done\n}\ntrap limpia_todo EXIT\n\n# Tipo para el set de MAC: hash:ip,mac si el kernel lo tiene (defender), hash:ip si no (banco, medido DAY320).\nTMAC=hash:ip,mac\nipset create d320t_sonda hash:ip,mac 2>/dev/null && ipset destroy d320t_sonda || TMAC=hash:ip\n\nmonta() {   # el estado que dejó en el defender la última corrida de lab-e2e-antispoof (modo descarta)\n  ipset create $WL hash:net,iface -exist; ipset create $BL hash:ip -exist\n  ipset create $SR hash:net -exist; ipset create $SI hash:ip -exist; ipset create $SM $TMAC -exist\n  iptables -w -N $CH 2>/dev/null; iptables -w -I INPUT 1 -j $CH\n  iptables -w -A $CH -m set --match-set $WL src,src -j RETURN\n  iptables -w -A $CH -m set --match-set $BL src -j DROP\n  iptables -w -t raw -N $AS 2>/dev/null; iptables -w -t raw -N ${AS}_IF 2>/dev/null; iptables -w -t raw -N ${AS}_MAC 2>/dev/null\n  iptables -w -t raw -I PREROUTING 1 -j $AS\n  iptables -w -t raw -A $AS -i lo -j RETURN\n  iptables -w -t raw -A $AS -m set ! --match-set $SR src -j RETURN\n  iptables -w -t raw -A $AS -m set ! --match-set $WL src,src -g ${AS}_IF\n  iptables -w -t raw -A $AS -m set ! --match-set $SI src -j RETURN\n  iptables -w -t raw -A $AS -m set ! --match-set $SM src,src -g ${AS}_MAC\n  iptables -w -t raw -A $AS -j RETURN\n  iptables -w -t raw -A ${AS}_IF -m limit --limit 5/min -j LOG --log-prefix \"D320T-IF \"\n  iptables -w -t raw -A ${AS}_IF -j DROP\n  iptables -w -t raw -A ${AS}_MAC -m limit --limit 5/min -j LOG --log-prefix \"D320T-MAC \"\n  iptables -w -t raw -A ${AS}_MAC -j DROP\n}\ncuenta_sets() { local n=0 s; for s in $SETS; do ipset list -n | grep -qx \"$s\" && n=$((n + 1)); done; echo $n; }\ncuenta_raw()  { iptables -w -t raw -S | grep -c -w -e $AS -e ${AS}_IF -e ${AS}_MAC; }\n\nlimpia_todo\n# Nombres parecidos: no se pueden llevar por delante.\nfor c in $PARECIDOS_CAD; do iptables -w -t raw -N \"$c\"; iptables -w -N \"$c\"; done\nfor s in $PARECIDOS_SET; do ipset create \"$s\" hash:ip; done\n\n# T1: la limpieza ANTIGUA (la de los traps de d302 y del vigía) deja la cadena raw y el set de protegidos.\nmonta\nwhile iptables -w -D INPUT -j $CH 2>/dev/null; do :; done; iptables -w -F $CH; iptables -w -X $CH\nipset destroy $BL 2>/dev/null; ipset destroy $WL 2>/dev/null\nr=$(cuenta_raw); ipset list -n | grep -qx $WL && w=1 || w=0\n[ \"$r\" -gt 0 ] && [ \"$w\" = 1 ] && pasa \"T1 la limpieza antigua deja raw=$r y $WL (el defecto medido)\" || mal \"T1 raw=$r prot=$w\"\n\n# T2: la nueva lo quita todo, a partir de ese mismo estado.\nout=$(bash \"$L\" \"$CH\" \"$AS\" $SETS); rc=$?\n[ \"$rc\" = 0 ] && [ \"$out\" = \"    quedan raw=0 filter=0 sets=0\" ] && [ \"$(cuenta_sets)\" = 0 ] && [ \"$(cuenta_raw)\" = 0 ] \\\n  && pasa \"T2 desde los restos: rc=0 '$out'\" || mal \"T2 rc=$rc '$out' sets=$(cuenta_sets) raw=$(cuenta_raw)\"\n\n# T3: desde el estado completo (cadena del filtro incluida) y con el salto raw y el de INPUT repetidos.\nmonta; iptables -w -t raw -I PREROUTING 1 -j $AS; iptables -w -I INPUT 1 -j $CH\nout=$(bash \"$L\" \"$CH\" \"$AS\" $SETS); rc=$?\n[ \"$rc\" = 0 ] && [ \"$(cuenta_sets)\" = 0 ] && ! iptables -w -t raw -S PREROUTING | grep -qw $AS && ! iptables -w -S INPUT | grep -qw $CH \\\n  && pasa \"T3 estado completo con saltos dobles: rc=0 '$out'\" || mal \"T3 rc=$rc '$out'\"\n\n# T4: los nombres parecidos siguen ahí.\nf=0; for c in $PARECIDOS_CAD; do iptables -w -t raw -S \"$c\" > /dev/null 2>&1 && iptables -w -S \"$c\" > /dev/null 2>&1 || f=1; done\nfor s in $PARECIDOS_SET; do ipset list -n | grep -qx \"$s\" || f=1; done\n[ \"$f\" = 0 ] && pasa \"T4 no toca $PARECIDOS_CAD $PARECIDOS_SET\" || mal \"T4 se llevó algún nombre parecido\"\n\n# T5: idempotente.\nout=$(bash \"$L\" \"$CH\" \"$AS\" $SETS); rc=$?\n[ \"$rc\" = 0 ] && [ \"$out\" = \"    quedan raw=0 filter=0 sets=0\" ] && pasa \"T5 segunda pasada sin nada: rc=0\" || mal \"T5 rc=$rc '$out'\"\n\n# T6: sin antispoofing ('-').\nipset create $WL hash:net,iface; ipset create $BL hash:ip; iptables -w -N $CH; iptables -w -I INPUT 1 -j $CH\niptables -w -A $CH -m set --match-set $WL src,src -j RETURN\nout=$(bash \"$L\" \"$CH\" - $BL $WL); rc=$?\n[ \"$rc\" = 0 ] && [ \"$out\" = \"    quedan raw=0 filter=0 sets=0\" ] && pasa \"T6 con '-': rc=0\" || mal \"T6 rc=$rc '$out'\"\n\n# T7: algo ajeno sigue usando el set de protegidos: no se puede destruir y lo dice (rc 1, sets=1).\nmonta; iptables -w -A INPUT -m set --match-set $WL src -m comment --comment d320t-ajeno -j ACCEPT\nout=$(bash \"$L\" \"$CH\" \"$AS\" $SETS); rc=$?\n[ \"$rc\" = 1 ] && [ \"$out\" = \"    quedan raw=0 filter=0 sets=1\" ] && pasa \"T7 regla ajena: rc=1 '$out'\" || mal \"T7 rc=$rc '$out'\"\niptables -w -D INPUT -m set --match-set $WL src -m comment --comment d320t-ajeno -j ACCEPT\n\n# T9: --contar cuenta los restos sin tocarlos (rc 1 y los mismos números dos veces), y da 0 tras limpiar.\nmonta\no1=$(bash \"$L\" --contar \"$CH\" \"$AS\" $SETS); r1=$?\no2=$(bash \"$L\" --contar \"$CH\" \"$AS\" $SETS); r2=$?\nn1=$(cuenta_sets)\nbash \"$L\" \"$CH\" \"$AS\" $SETS > /dev/null\no3=$(bash \"$L\" --contar \"$CH\" \"$AS\" $SETS); r3=$?\n[ \"$r1\" = 1 ] && [ \"$o1\" = \"$o2\" ] && [ \"$r2\" = 1 ] && [ \"$n1\" = 5 ] && [ \"$o1\" = \"    quedan raw=14 filter=4 sets=5\" ] \\\n  && [ \"$r3\" = 0 ] && [ \"$o3\" = \"    quedan raw=0 filter=0 sets=0\" ] \\\n  && pasa \"T9 --contar: '$o1' rc=1 sin tocar; tras limpiar rc=0\" || mal \"T9 r=$r1/$r2/$r3 '$o1' '$o2' '$o3' sets=$n1\"\n\n# T8: uso malo.\nbash \"$L\" \"$CH\" \"$AS\" > /dev/null 2>&1; r1=$?\nbash \"$L\" \"$CH\" 'X;rm' $WL > /dev/null 2>&1; r2=$?\nbash \"$L\" \"\" \"$AS\" $WL > /dev/null 2>&1; r3=$?\nbash \"$L\" --contar \"$CH\" \"$AS\" > /dev/null 2>&1; r4=$?\n[ \"$r1\" = 2 ] && [ \"$r2\" = 2 ] && [ \"$r3\" = 2 ] && [ \"$r4\" = 2 ] && pasa \"T8 uso malo: rc 2 2 2 2\" || mal \"T8 rc $r1 $r2 $r3 $r4\"\n\necho \"$OK/$TOT PASA (set de MAC: $TMAC)\"\n[ \"$OK\" = \"$TOT\" ]\n",
  "modo": 493
 }
]""")

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d320_8e4b_limpieza.py --check|--apply  (desde la raíz del repo)", file=sys.stderr); return 2
    aplicar = sys.argv[1] == "--apply"
    hechos, nuevos = 0, {}
    for c in CAMBIOS:
        r = c["ruta"]
        existe = os.path.isfile(r)
        b = open(r, "rb").read() if existe else None
        if existe and sha(b) == c["despues"]:
            hechos += 1; print(f"[YA APLICADO] {r}"); continue
        if c["antes"] is None:
            if existe:
                print(f"[NO APLICABLE] {r} ya existe con otro contenido (sha256={sha(b)})"); return 1
            if not os.path.isdir(os.path.dirname(r) or "."):
                print(f"[NO APLICABLE] no existe el directorio de {r} (¿estás en la raíz del repo?)"); return 1
            n = c["contenido"].encode("utf-8")
            print(f"[APLICABLE] {r} (nuevo, {len(n)} B)")
        else:
            if not existe:
                print(f"[NO APLICABLE] no existe {r} (¿estás en la raíz del repo?)"); return 1
            if sha(b) != c["antes"]:
                print(f"[NO APLICABLE] {r} sha256={sha(b)}\n  esperado antes  ={c['antes']}\n  esperado después={c['despues']}"); return 1
            t = b.decode("utf-8")
            for i, bl in enumerate(c["bloques"], 1):
                if t.count(bl["viejo"]) != 1:
                    print(f"[NO APLICABLE] {r}: el bloque {i} aparece {t.count(bl['viejo'])} veces"); return 1
                t = t.replace(bl["viejo"], bl["nuevo"])
            n = t.encode("utf-8")
            print(f"[APLICABLE] {r} {c['antes'][:16]} -> {c['despues'][:16]} ({len(c['bloques'])} bloques)")
        if sha(n) != c["despues"]:
            print(f"[NO APLICABLE] {r}: el resultado no da el sha256 esperado"); return 1
        nuevos[r] = (n, c.get("modo"))
    if hechos and nuevos:
        print(f"[NO APLICABLE] estado mezclado: {hechos} ya aplicados y {len(nuevos)} no; no se toca nada"); return 1
    if not nuevos:
        print("[YA APLICADO] nada que hacer"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(nuevos)} ficheros); nada escrito"); return 0
    for r, (n, modo) in nuevos.items():
        d = os.path.dirname(r) or "."
        m = (os.stat(r).st_mode & 0o7777) if os.path.exists(r) else (modo or 0o644)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche.")
        with os.fdopen(fd, "wb") as f: f.write(n); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, m); os.replace(tmp, r)
    for c in CAMBIOS:
        s = sha(open(c["ruta"], "rb").read())
        if s != c["despues"]:
            print(f"[ERROR] {c['ruta']} quedó con sha256={s}"); return 1
        print(f"[APLICADO] {c['ruta']} sha256={s}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
