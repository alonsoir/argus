#!/usr/bin/env bash
# DAY302: 2.o inventario b2 (solo lectura): flush, DdosMitigacion, protegidos por defecto, registro BLOCKED. Mac, raiz del repo.
set -u
DIA=day302
OUT=logs/lab/$DIA/inv_b2_2.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
I=$FW/include/firewall
S=$FW/src
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "Q1 cola de add_ip / add_detection (tras pending_ips_max)"
git grep -n -A 28 "metrics_.pending_ips_max.load" -- "$S/core/batch_processor.cpp"
sec "Q1 quien llama a flush / should_flush / flush_internal"
git grep -n -E "flush\(\)|should_flush\(\)|flush_internal\(\)" -- "$S" "$I"
sec "Q2 flush_internal tras el add_batch"
git grep -n -A 50 "if (flush_success) {" -- "$S/core/batch_processor.cpp"
sec "Q2 BatchProcessor: miembros privados"
git grep -n -A 60 "IPSetWrapper& ipset_;" -- "$I/batch_processor.hpp"
sec "Q2 BatchProcessorMetrics"
git grep -n -A 40 "struct BatchProcessorMetrics" -- "$I/batch_processor.hpp"
sec "Q6 DdosMitigacionParams"
git grep -n -A 8 "struct DdosMitigacionParams" -- "$I/ddos_mitigacion.hpp"
sec "Q3 class DdosMitigacion"
git grep -n -A 80 "^class DdosMitigacion" -- "$I/ddos_mitigacion.hpp"
sec "Q4 RangosProtegidos"
git grep -n -A 40 "^struct RangosProtegidos" -- "$I/ddos_protegidos.hpp"
sec "Q5 registro BLOCKED en el suscriptor"
git grep -n -B 14 -A 8 '"BLOCKED",' -- "$S/api/zmq_subscriber.cpp"
sec "Q5 logger del suscriptor"
git grep -n -E "logger_|Logger|log_blocked" -- "$I/zmq_subscriber.hpp"
sec "Q1 hilos del suscriptor y del main"
git grep -n -E "void ZMQSubscriber::|std::thread" -- "$S/api/zmq_subscriber.cpp"
git grep -n -E "processor\.(flush|should_flush)|BatchProcessor processor|std::thread" -- "$S/main.cpp"
sec "tests: fuentes de firewall_tests"
git grep -n -A 22 "set(TEST_SOURCES" -- "$FW/CMakeLists.txt"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
