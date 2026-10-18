#!/usr/bin/env bash
# DAY301: 4.o inventario 3b (solo lectura): anclas para el cableado de la tanda 3b-b. Mac, raiz del repo.
set -u
DIA=day301
OUT=logs/lab/$DIA/inv_3b_4.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
I=$FW/include/firewall
S=$FW/src
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "R1 config_loader: bloque ddos_shadow"
git grep -n -A 45 '"ddos_shadow"' -- "$S/core/config_loader.cpp"
sec "R1 config_loader: bloque ddos_protegidos"
git grep -n -A 30 '"ddos_protegidos"' -- "$S/core/config_loader.cpp"
sec "R1 FirewallAgentConfig: miembros ddos"
git grep -n -B 2 -A 3 -E "ddos_shadow;|ddos_protegidos;" -- "$I/config_loader.hpp"
sec "R2 parse_recidivism"
git grep -n -A 45 "ConfigLoader::parse_recidivism" -- "$S/core/config_loader.cpp"
sec "R2 set_recidivism_config"
git grep -n -A 50 "BatchProcessor::set_recidivism_config" -- "$S/core/batch_processor.cpp"
sec "R3 flush_internal (inicio)"
git grep -n -A 45 "size_t BatchProcessor::flush_internal" -- "$S/core/batch_processor.cpp"
sec "R3 compute_penalty_timeout (final)"
git grep -n -A 15 "size_t idx = std::min<size_t>(state.strikes - 1" -- "$S/core/batch_processor.cpp"
sec "R3 BatchProcessor: API publica y miembros"
git grep -n -A 75 "^class BatchProcessor" -- "$I/batch_processor.hpp"
sec "R4 IPSetConfigNew"
git grep -n -A 16 "struct IPSetConfigNew" -- "$I/config_loader.hpp"
sec "R5 usos de la whitelist"
git grep -n -E "whitelist_ipset|ipsets.at\(\"whitelist\"\)" -- "$S"
sec "R6 is_valid_ip y add individual"
git grep -n -A 25 "bool is_valid_ip" -- "$S/core/ipset_wrapper.cpp"
git grep -n -E "IPSetResult<[a-z]+> (add|add_ip|add_entry|test)\(" -- "$I/ipset_wrapper.hpp"
sec "R7 resumen de la sombra"
git grep -n -A 30 'resumen: habilitada=' -- "$S/api/zmq_subscriber.cpp"
sec "zmq_subscriber.hpp: Config y miembros ddos"
git grep -n -E "struct Config|ddos_shadow|ddos_protegidos|processor_|prot_alertas_" -- "$I/zmq_subscriber.hpp"
sec "main: copia de la config ddos al suscriptor"
git grep -n -B 2 -A 25 "zmq_config.ddos_shadow = config.ddos_shadow;" -- "$S/main.cpp"
sec "main: bloque de reincidencia"
git grep -n -A 32 "Recidivism config (RECIDIVISM-D276)" -- "$S/main.cpp"
sec "tests: fixture de reincidencia (cabecera)"
git grep -n -A 30 "class RecidivismTest" -- "$FW/tests/unit/test_batch_processor_recidivism.cpp"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
