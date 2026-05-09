#!/bin/bash
# ============================================================================
# aRGus NDR — Experiment Comparative: Suricata vs aRGus
# Replicates Tables 3, 7, 8, 11 from paper v19
# Dataset: CTU-13 Neris (botnet-capture-20110810-neris.pcap)
# Ground truth: 147.32.84.165 (646 malicious flows)
# ============================================================================
set -e

PCAP="/vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap"
EVE_LOG="/var/log/suricata/eve.json"
RESULTS_DIR="/vagrant/logs/experiment"
MALICIOUS_IP="147.32.84.165"
TOTAL_FLOWS=19135
GROUND_TRUTH_TP=646
GROUND_TRUTH_TN=12075

mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT="$RESULTS_DIR/suricata_results_${TIMESTAMP}.json"

echo "=============================================="
echo " aRGus NDR — Suricata Comparative Experiment"
echo " $(date)"
echo "=============================================="

# Verificar dependencias
if [ ! -f "$PCAP" ]; then
    echo "❌ PCAP no encontrado: $PCAP"
    exit 1
fi

suricata_version=$(suricata -V 2>&1 | head -1)
echo "✅ $suricata_version"
echo "✅ PCAP: $PCAP ($(du -h $PCAP | cut -f1))"
echo "✅ Ground truth: $MALICIOUS_IP ($GROUND_TRUTH_TP flows maliciosos)"
echo ""

# Función para medir recursos
measure_resources() {
    local pid=$1
    local label=$2
    local outfile=$3
    local interval=2
    echo "timestamp,cpu_pct,rss_mb,vsz_mb" > "$outfile"
    while kill -0 "$pid" 2>/dev/null; do
        local stats=$(ps -p "$pid" -o %cpu,rss,vsz --no-headers 2>/dev/null || echo "0 0 0")
        local cpu=$(echo $stats | awk '{print $1}')
        local rss=$(echo $stats | awk '{printf "%.1f", $2/1024}')
        local vsz=$(echo $stats | awk '{printf "%.1f", $3/1024}')
        echo "$(date +%s),$cpu,$rss,$vsz" >> "$outfile"
        sleep $interval
    done
}

# Función para parsear eve.json y calcular métricas
calculate_metrics() {
    local eve_file=$1
    local speed=$2

    if [ ! -f "$eve_file" ]; then
        echo "❌ eve.json no encontrado"
        return
    fi

    # Alertas por IP origen
    local total_alerts=$(grep '"event_type":"alert"' "$eve_file" | wc -l)
    local tp_alerts=$(grep '"event_type":"alert"' "$eve_file" | \
        grep "\"$MALICIOUS_IP\"" | wc -l)
    local fp_alerts=$((total_alerts - tp_alerts))

    # Flows únicos alertados
    local tp_flows=$(grep '"event_type":"alert"' "$eve_file" | \
        grep "\"$MALICIOUS_IP\"" | \
        python3 -c "
import sys, json
flows = set()
for line in sys.stdin:
    try:
        e = json.loads(line)
        key = (e.get('src_ip',''), e.get('dest_ip',''), e.get('src_port',0), e.get('dest_port',0), e.get('proto',''))
        flows.add(key)
    except: pass
print(len(flows))
" 2>/dev/null || echo "0")

    local fp_flows=$(grep '"event_type":"alert"' "$eve_file" | \
        grep -v "\"$MALICIOUS_IP\"" | \
        python3 -c "
import sys, json
flows = set()
for line in sys.stdin:
    try:
        e = json.loads(line)
        key = (e.get('src_ip',''), e.get('dest_ip',''), e.get('src_port',0), e.get('dest_port',0), e.get('proto',''))
        flows.add(key)
    except: pass
print(len(flows))
" 2>/dev/null || echo "0")

    # Métricas de detección
    local fn=$((GROUND_TRUTH_TP - tp_flows))
    local tn=$((GROUND_TRUTH_TN - fp_flows))
    [ $fn -lt 0 ] && fn=0
    [ $tn -lt 0 ] && tn=0

    local precision=0
    local recall=0
    local f1=0

    if [ $((tp_flows + fp_flows)) -gt 0 ]; then
        precision=$(python3 -c "print(f'{$tp_flows/($tp_flows+$fp_flows):.4f}')" 2>/dev/null || echo "0")
    fi
    if [ $GROUND_TRUTH_TP -gt 0 ]; then
        recall=$(python3 -c "print(f'{$tp_flows/$GROUND_TRUTH_TP:.4f}')" 2>/dev/null || echo "0")
    fi
    if [ "$precision" != "0" ] && [ "$recall" != "0" ]; then
        f1=$(python3 -c "
p=$precision; r=$recall
if p+r > 0: print(f'{2*p*r/(p+r):.4f}')
else: print('0')
" 2>/dev/null || echo "0")
    fi

    local fpr=0
    if [ $GROUND_TRUTH_TN -gt 0 ]; then
        fpr=$(python3 -c "print(f'{$fp_flows/$GROUND_TRUTH_TN:.6f}')" 2>/dev/null || echo "0")
    fi

    echo "  --- Métricas @${speed}Mbps ---"
    echo "  Total alertas:  $total_alerts"
    echo "  TP (flows):     $tp_flows / $GROUND_TRUTH_TP"
    echo "  FP (flows):     $fp_flows"
    echo "  FN:             $fn"
    echo "  Precision:      $precision"
    echo "  Recall:         $recall"
    echo "  F1:             $f1"
    echo "  FPR:            $fpr"

    # Guardar en JSON
    python3 -c "
import json
data = {
    'speed_mbps': '$speed',
    'total_alerts': $total_alerts,
    'tp_flows': $tp_flows,
    'fp_flows': $fp_flows,
    'fn': $fn,
    'tn': $tn,
    'precision': $precision,
    'recall': $recall,
    'f1': $f1,
    'fpr': $fpr,
    'ground_truth_tp': $GROUND_TRUTH_TP,
    'ground_truth_tn': $GROUND_TRUTH_TN
}
print(json.dumps(data, indent=2))
" >> "${RESULTS_DIR}/metrics_${speed}mbps_${TIMESTAMP}.json" 2>/dev/null || true
}

# ============================================================================
# EXPERIMENTO PRINCIPAL
# ============================================================================

run_replay() {
    local speed=$1
    echo ""
    echo "=========================================="
    echo " RUN: ${speed} Mbps"
    echo "=========================================="

    # Limpiar logs anteriores
    sudo systemctl stop suricata 2>/dev/null || true
    sudo rm -f "$EVE_LOG"
    sudo truncate -s 0 /var/log/suricata/suricata.log 2>/dev/null || true

    # Arrancar Suricata en modo AF_PACKET
    sudo suricata -c /etc/suricata/suricata.yaml \
        --af-packet=eth1 \
        -D \
        -l /var/log/suricata/ \
        2>/dev/null
    sleep 3

    # PID de Suricata
    local suricata_pid=$(pgrep -f "suricata" | head -1)
    echo "  Suricata PID: $suricata_pid"

    # Monitor de recursos en background
    local res_file="${RESULTS_DIR}/resources_${speed}mbps_${TIMESTAMP}.csv"
    measure_resources "$suricata_pid" "suricata" "$res_file" &
    local monitor_pid=$!

    # Replay desde la VM cliente — aquí simulamos con tcpreplay local
    # En producción: vagrant ssh client -c "sudo tcpreplay ..."
    echo "  🚀 Iniciando tcpreplay @ ${speed} Mbps..."
    local start_time=$(date +%s%N)

    sudo tcpreplay -i eth1 \
        --mbps=$speed \
        --stats=5 \
        "$PCAP" 2>&1 | tee "${RESULTS_DIR}/tcpreplay_${speed}mbps_${TIMESTAMP}.log"

    local exit_code=$?
    local end_time=$(date +%s%N)
    local duration=$(python3 -c "print(f'{($end_time-$start_time)/1e9:.2f}')")

    echo "  ✅ tcpreplay exit=$exit_code duration=${duration}s"

    # Esperar drain
    echo "  ⏳ Esperando drain (10s)..."
    sleep 10

    # Detener monitor
    kill $monitor_pid 2>/dev/null || true

    # Métricas de recursos
    if [ -f "$res_file" ]; then
        local avg_cpu=$(tail -n +2 "$res_file" | awk -F',' '{sum+=$2; n++} END {if(n>0) printf "%.1f", sum/n}')
        local max_rss=$(tail -n +2 "$res_file" | awk -F',' '{if($3>max) max=$3} END {printf "%.1f", max}')
        echo "  CPU promedio: ${avg_cpu}%"
        echo "  RAM máx:      ${max_rss} MB"
    fi

    # Parsear resultados
    sleep 2  # Asegurar flush de eve.json
    calculate_metrics "$EVE_LOG" "$speed"

    # Extraer estadísticas de tcpreplay
    local actual_mbps=$(grep -oP '[0-9.]+ Mbps' "${RESULTS_DIR}/tcpreplay_${speed}mbps_${TIMESTAMP}.log" | tail -1 | awk '{print $1}')
    local packets=$(grep -oP 'Actual: [0-9]+' "${RESULTS_DIR}/tcpreplay_${speed}mbps_${TIMESTAMP}.log" | tail -1 | awk '{print $2}')
    local failed=$(grep -oP 'Failed: [0-9]+' "${RESULTS_DIR}/tcpreplay_${speed}mbps_${TIMESTAMP}.log" | tail -1 | awk '{print $2}')

    echo "  Actual Mbps:  ${actual_mbps:-N/A}"
    echo "  Packets sent: ${packets:-N/A}"
    echo "  Failed:       ${failed:-0}"

    sudo systemctl stop suricata 2>/dev/null || true
    sleep 2
}

# Ejecutar los 3 runs (igual que aRGus DAY 145)
run_replay 10
run_replay 50
run_replay 100

echo ""
echo "=============================================="
echo " ✅ EXPERIMENTO COMPLETADO"
echo " Resultados en: $RESULTS_DIR"
echo "=============================================="

# Resumen final
echo ""
echo "=== TABLA COMPARATIVA (formato paper) ==="
echo "Variant | Target | Actual | PPS | Duration | Packets | Failed | exit"
echo "Suricata | 10 Mbps | ... | ... | ... | 320,524 | 2,630 | ..."
echo "Suricata | 50 Mbps | ... | ... | ... | 320,524 | 2,630 | ..."
echo "Suricata | 100 Mbps | ... | ... | ... | 320,524 | 2,630 | ..."
echo "(completar con logs en $RESULTS_DIR)"
