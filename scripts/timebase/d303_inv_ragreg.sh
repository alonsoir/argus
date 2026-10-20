#!/usr/bin/env bash
# DAY303 K8: historial de registro de rag-security en etcd, y si otros componentes fallan el MAC
set -u
L=/vagrant/logs/lab/rag-security.log
echo "===== K8 rag-security.log: lineas y tamano ====="
wc -l "$L"
echo "===== K8 arranques, registros y fallos (numero de linea: texto) ====="
grep -n -E 'Failed to register|[Rr]egistered|registrad|Registro|MAC verification failed|Sistema listo' "$L" | cut -c1-120 | awk -F: '{k=$2; sub(/^[0-9]+:/,""); if (k!=prev) {print} prev=k}' | tail -40
echo "===== K8 primera y ultima fecha ts= del log ====="
grep -o -E 'ts=[0-9T:.-]+Z' "$L" | sed -n '1p;$p'
echo "===== K8 MAC verification failed por log (solo lineas con ts de hoy) ====="
for f in /vagrant/logs/lab/*.log; do
  c=$(grep 'ts=2026-10-20' "$f" 2>/dev/null | grep -c 'MAC verification failed')
  [ "$c" != "0" ] && echo "$c $f"
done
echo "(fin)"
