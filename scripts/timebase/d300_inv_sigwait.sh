#!/usr/bin/env bash
# DAY300: inventario para [SIGWAIT-D300] y para el E2E del reinicio (solo lectura).
sec() { printf '\n===== %s =====\n' "$1"; }
sec "main.cpp: includes"
git grep -n "#include" -- sniffer/src/userspace/main.cpp
sec "main.cpp: manejador y setup de senales"
git grep -n -A 20 "^void signal_handler(int signum)" -- sniffer/src/userspace/main.cpp
sec "main.cpp: comienzo de main hasta setup_signal_handlers()"
git grep -n -B 30 -A 2 "^    setup_signal_handlers();" -- sniffer/src/userspace/main.cpp
sec "globales con constructor en main.cpp (posibles hilos antes de main)"
git grep -n -e "^static " -e "^std::" -e "^[A-Za-z_:<>]* g_" -- sniffer/src/userspace/main.cpp
sec "lab_frio.sh: cabecera y uso"
head -n 60 scripts/timebase/lab_frio.sh
sec "gen_disjunto.py: uso y argumentos"
git grep -n -e "argparse" -e "add_argument" -e "^def " -e '"""' -- scripts/dataset_lab/gen_disjunto.py
