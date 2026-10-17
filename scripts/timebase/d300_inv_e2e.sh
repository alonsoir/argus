#!/usr/bin/env bash
# DAY300: inventario para el E2E del reinicio (solo lectura).
sec() { printf '\n===== %s =====\n' "$1"; }
sec "gen_disjunto.py: cabecera"
head -n 40 scripts/dataset_lab/gen_disjunto.py
sec "d298_etapa1_resumen.sh: cabecera"
head -n 30 scripts/timebase/d298_etapa1_resumen.sh
sec "lab_frio.sh: final (pasos 12+)"
tail -n 25 scripts/timebase/lab_frio.sh
sec "lab_corrida_defender.sh: subcomandos"
git grep -n -e "^  [a-z_]*)" -- scripts/timebase/lab_corrida_defender.sh
sec "commits que mencionan el pcap del A5 (gen_disjunto)"
git log --oneline --all -i --grep="disjunt" -n 8
