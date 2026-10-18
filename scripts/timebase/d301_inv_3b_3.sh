#!/usr/bin/env bash
# DAY301: 3.er inventario 3b (solo lectura): sombra por víctima, should_block, defectos de reincidencia,
# protegidos, tipos de ipset y víctima del E2E. Mac, raíz del repo.
set -u
DIA=day301
OUT=logs/lab/$DIA/inv_3b_3.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
I=$FW/include/firewall
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "Q1 ddos_shadow_policy: estructura"
git grep -n -E "struct |class |bool |std::(set|unordered_set|map|unordered_map)|INICIO|FIN|advance|add_drop" -- "$I/ddos_shadow_policy.hpp"
sec "Q1 ddos_shadow_policy: add_drop y advance"
git grep -n -A 45 -E "(void|auto|std::vector<[A-Za-z_:]+>) +(add_drop|advance)\(" -- "$I/ddos_shadow_policy.hpp"
sec "Q2 should_block"
git grep -n -A 25 "BatchProcessor::should_block" -- "$FW/src/core/batch_processor.cpp"
sec "Q3 add_detections, segundo paso"
git grep -n -A 30 "size_t dedup_count = 0;" -- "$FW/src/core/batch_processor.cpp"
sec "Q4 RecidivismConfigNew y RecidivismConfig"
git grep -n -A 22 "struct RecidivismConfigNew" -- "$I/config_loader.hpp"
git grep -n -A 22 "struct RecidivismConfig" -- "$I/batch_processor.hpp"
sec "Q5 ALERTA_PROTEGIDO en el suscriptor"
git grep -n -B 4 -A 22 "ALERTA_PROTEGIDO" -- "$FW/src/api/zmq_subscriber.cpp"
sec "Q5 firmas de ddos_protegidos.hpp"
git grep -n -E "inline|struct|enum" -- "$I/ddos_protegidos.hpp"
sec "Q6 IPSetType"
git grep -n -A 12 "enum class IPSetType" -- "$I/ipset_wrapper.hpp"
sec "Q6 creación de sets en main"
git grep -n -A 25 "ipset_config.type = IPSetType::HASH_IP;" -- "$FW/src/main.cpp"
sec "firewall.json ddos_protegidos"
python3 - "$FW/config/firewall.json" <<'PYEOF'
import json, sys
print(json.dumps(json.load(open(sys.argv[1]))["ddos_protegidos"], indent=2, ensure_ascii=False))
PYEOF
sec "Q7 víctima del E2E DAY300"
git grep -n -E "VICTIMA|VICTIM|DST|192\.168\.100\." -- scripts/timebase/d300_protegidos_e2e.sh
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") líneas)"
