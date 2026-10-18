#!/usr/bin/env bash
# DAY301: inventario de solo lectura para el paso 3b (drop temporal real ddos_v2 -> ipset). Mac, raíz del repo.
set -u
DIA=day301
OUT=logs/lab/$DIA/inv_3b.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "git"; git status -sb; git log --oneline -6
sec "zmq_subscriber: referencias a batch/ipset/recidiva/dry_run"
git grep -n -E "batch_processor|add_detection|add_to_blacklist|ipset|BLOCKED|dry_run|penalty|strike" -- "$FW/src/api/zmq_subscriber.cpp"
sec "zmq_subscriber: desde add_drop (sombra) hasta los pasos 5-8"
git grep -n -A 110 "ddos_shadow_.add_drop" -- "$FW/src/api/zmq_subscriber.cpp"
sec "RECIDIVISM-D276: sitios"
git grep -n "RECIDIVISM-D276" -- "$FW"
sec "RECIDIVISM-D276: cálculo del timeout"
git grep -n -A 40 -E "compute_penalty_timeout[a-z_]*\(" -- "$FW/*.cpp" "$FW/*.hpp"
sec "batch_processor: timeout, volcado, whitelist, dry_run"
git grep -n -E "timeout|restore|flush|whitelist|dry_run|protegid|geteuid" -- "$FW/*batch_processor.cpp" "$FW/*batch_processor.hpp"
sec "reglas iptables / match-set / whitelist"
git grep -n -E "match-set|whitelist|ACCEPT|iptables -I|iptables -A" -- "$FW/*.cpp" "$FW/*.hpp"
sec "firewall.json: claves de primer nivel y bloques relevantes"
python3 - "$FW/config/firewall.json" <<'PYEOF'
import json, re, sys
d = json.load(open(sys.argv[1]))
print("claves:", list(d.keys()))
for k, v in d.items():
    if re.search(r"ipset|dry|recid|strike|penal|ddos_shadow|iptables|batch|whitelist|blacklist", k, re.I):
        print("--", k); print(json.dumps(v, indent=2, ensure_ascii=False)[:3000])
    elif isinstance(v, dict):
        for k2, v2 in v.items():
            if re.search(r"dry_run|recid|strike|penal", k2, re.I):
                print("--", k + "." + k2, "=", json.dumps(v2, ensure_ascii=False)[:1500])
PYEOF
sec "tests del ipset: saltos"
git grep -n -c "GTEST_SKIP" -- "$FW/tests"
git grep -n -B 2 -A 2 "GTEST_SKIP" -- "$FW/*ipset*"
sec "Makefile: objetivos de firewall/ipset"
git grep -n -E "^test-firewall|^firewall-|ipset" -- Makefile
sec "Vagrantfile: aprovisionamiento ipset"
git grep -n -E "ipset|xt_set|ip_set|modprobe" -- Vagrantfile
sec "conmutador de referencia (cabecera)"
head -30 scripts/timebase/d299_agg_conmutador.py
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") líneas)"
