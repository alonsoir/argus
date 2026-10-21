#!/usr/bin/env bash
# DAY302: 5.o inventario b2 (solo lectura): anclas del cableado en suscriptor, main y config. Mac, raiz del repo.
set -u
DIA=day302
OUT=logs/lab/$DIA/inv_b2_5.txt
mkdir -p logs/lab/$DIA
FW=firewall-acl-agent
I=$FW/include/firewall
S=$FW/src
sec() { printf '\n===== %s =====\n' "$1"; }
{
sec "U1 disparo del resumen de la sombra"
git grep -n -B 25 'resumen: habilitada=' -- "$S/api/zmq_subscriber.cpp"
sec "U1 inicio de la rama ddos_v2 en handle_message (ts_s, sombra)"
git grep -n -B 40 'evento DROP sin network_features' -- "$S/api/zmq_subscriber.cpp"
sec "U2 create_blocked_event_from_proto"
git grep -n -A 25 -E "BlockedEvent create_blocked_event_from_proto" -- "$S" "$I"
sec "U3 constructor del suscriptor"
git grep -n -A 20 "ZMQSubscriber::ZMQSubscriber" -- "$S/api/zmq_subscriber.cpp"
sec "U3 miembros del suscriptor (sombra y contadores)"
git grep -n -B 3 -A 12 "DdosShadowPolicy ddos_shadow_" -- "$I/zmq_subscriber.hpp"
git grep -n -E "prot_alertas_|prot_detalle_|sombra_primer_drop_|hmac_key_" -- "$I/zmq_subscriber.hpp"
sec "U3 main: dry_run, processor y suscriptor"
git grep -n -E "dry_run|ZMQSubscriber subscriber|ZMQSubscriber::Config|BatchProcessor processor" -- "$S/main.cpp"
sec "U3 main: tras set_recidivism_config"
git grep -n -A 30 "processor.set_recidivism_config(recidivism_config);" -- "$S/main.cpp"
sec "U4 config_loader: bloque ddos_mitigacion"
git grep -n -A 40 '"ddos_mitigacion"' -- "$S/core/config_loader.cpp"
sec "U4 firewall.json: bloque ddos_mitigacion"
git grep -n -A 20 '"ddos_mitigacion"' -- "$FW/config/firewall.json"
} > "$OUT" 2>&1
echo "inventario en $OUT ($(wc -l < "$OUT") lineas)"
