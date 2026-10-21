#!/usr/bin/env bash
# DAY302: 3.er inventario b2 (solo lectura): disparo del flush, receive_loop, umbrales del lote, dry_run del wrapper. Mac, raiz del repo.
set -u
DIA=day302
OUT=logs/lab/$DIA/inv_b2_3.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
I=$FW/include/firewall
S=$FW/src
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "R1 should_flush"
git grep -n -A 25 "bool BatchProcessor::should_flush" -- "$S/core/batch_processor.cpp"
sec "R2 llamada a flush de la linea 73 (constructor/destructor)"
git grep -n -A 30 "^BatchProcessor::BatchProcessor" -- "$S/core/batch_processor.cpp"
sec "R3 receive_loop"
git grep -n -A 80 "void ZMQSubscriber::receive_loop" -- "$S/api/zmq_subscriber.cpp"
sec "R4 umbrales del lote: struct, JSON y main"
git grep -n -B 2 -A 30 "struct BatchProcessorConfig" -- "$I/batch_processor.hpp"
git grep -n -E "batch_size|batch_time|max_pending|flush" -- "$FW/config/firewall.json"
git grep -n -E "batch_config\.[a-z_]+ *=" -- "$S/main.cpp"
sec "R5 dry_run del wrapper"
git grep -n -E "dry_run" -- "$S/core/ipset_wrapper.cpp"
git grep -n -A 20 "bool IPSetWrapper::set_exists_unlocked" -- "$S/core/ipset_wrapper.cpp"
git grep -n -B 2 -A 20 "safe_exec_with_file_in({kIpsetBin" -- "$S/core/ipset_wrapper.cpp"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
