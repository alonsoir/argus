#!/usr/bin/env bash
# DAY302: inventario b2 (solo lectura): anclas del cableado ddos_v2 -> batch_processor -> ipset. Mac, raiz del repo.
set -u
DIA=day302
OUT=logs/lab/$DIA/inv_b2.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
I=$FW/include/firewall
S=$FW/src
T=$FW/tests/unit
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "rama y HEAD"
git rev-parse --abbrev-ref HEAD
git log --oneline -6
git status --short
sec "P1 BatchProcessor: clase completa (API y miembros)"
git grep -n -A 120 "^class BatchProcessor" -- "$I/batch_processor.hpp"
sec "P1 StrikeState"
git grep -n -B 2 -A 12 "struct StrikeState" -- "$I" "$S"
sec "P1 add_ip"
git grep -n -A 40 -E "BatchProcessor::add_ip\(" -- "$S/core/batch_processor.cpp"
sec "P1/P2 flush_internal completa"
git grep -n -A 90 "size_t BatchProcessor::flush_internal" -- "$S/core/batch_processor.cpp"
sec "P2 compute_penalty_timeout completa"
git grep -n -A 50 -E "BatchProcessor::compute_penalty_timeout\(" -- "$S/core/batch_processor.cpp"
sec "P2 set_recidivism_config"
git grep -n -A 50 "BatchProcessor::set_recidivism_config" -- "$S/core/batch_processor.cpp"
sec "P3 add_batch / restore -exist"
git grep -n -B 3 -A 30 -E "add_batch\(" -- "$S/core/ipset_wrapper.cpp"
sec "P4 DdosMitigacion: API"
git grep -n -E "enum class|struct |class |decidir|purgar|escalones_cortos|Accion|BLOQUEAR|RENOVAR" -- "$I/ddos_mitigacion.hpp"
sec "P4 en_episodio"
git grep -n -A 12 "en_episodio" -- "$I/ddos_shadow_policy.hpp"
sec "P4 protegidos: API"
git grep -n -E "categoria_de|es_protegido|struct |class |namespace detalle" -- "$I/ddos_protegidos.hpp"
sec "P5 zmq_subscriber.cpp: add_drop, return de la sombra y pasos 5-8"
git grep -n -B 30 -A 40 "add_drop(" -- "$S/api/zmq_subscriber.cpp"
sec "P5 zmq_subscriber.cpp: BLOCKED, timeout_sec, set fijo, processor_"
git grep -n -E "BLOCKED|timeout_sec|ml_defender_blacklist_test|processor_" -- "$S/api/zmq_subscriber.cpp"
sec "P5 zmq_subscriber.cpp: resumen de la sombra"
git grep -n -A 30 'resumen: habilitada=' -- "$S/api/zmq_subscriber.cpp"
sec "P6 zmq_subscriber.hpp: Config y miembros"
git grep -n -A 40 "struct Config" -- "$I/zmq_subscriber.hpp"
git grep -n -E "ddos_|processor_|std::mutex|std::thread" -- "$I/zmq_subscriber.hpp"
sec "P6 config: struct de ddos_mitigacion (b1) y usos"
git grep -n -B 2 -A 25 -E "struct DdosMitigacion[A-Za-z]*Config" -- "$I"
git grep -n -E "ddos_mitigacion" -- "$I/config_loader.hpp" "$S/main.cpp"
sec "P6 main: copia ddos al suscriptor y reincidencia"
git grep -n -B 2 -A 30 "zmq_config.ddos_shadow = config.ddos_shadow;" -- "$S/main.cpp"
git grep -n -A 32 "Recidivism config (RECIDIVISM-D276)" -- "$S/main.cpp"
sec "P7 tests de reincidencia: fixture y target"
git grep -n -A 40 "class RecidivismTest" -- "$T/test_batch_processor_recidivism.cpp"
git grep -n -B 2 -A 12 "test_batch_processor_recidivism" -- "$FW/CMakeLists.txt"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
