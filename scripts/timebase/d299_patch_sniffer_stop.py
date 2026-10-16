#!/usr/bin/env python3
"""DAY299: parada ORDENADA del sniffer. pipeline-stop hacia tmux kill-session (SIGHUP) y el sniffer solo
capturaba SIGINT/SIGTERM: moria sin limpieza ni volcado de parada (medido: 0 lineas [Cleanup]). Target
sniffer-stop (SIGTERM, espera SNIFFER_STOP_GRACE_S, SIGKILL con aviso), pipeline-stop lo usa, y el sniffer
trata SIGHUP como parada ordenada. --check | --apply desde la raiz del repo. Atomico."""
import os
import sys

M = "[SNIFFER-STOP-D299]"
MK = "Makefile"
MAIN = "sniffer/src/userspace/main.cpp"
BACK = "docs/BACKLOG.md"
T = "\t"

EDITS = [
    (MK,
     "# ── sniffer-libpcap-start — Variant B (libpcap) ──────────────────────────────\n",
     "# ── sniffer-stop — parada ORDENADA " + M + " ──────────────────────────────────\n"
     "# SIGTERM y espera; SIGKILL solo como ultimo recurso. tmux kill-session (SIGHUP) mataba el sniffer\n"
     "# sin limpieza ni volcado del estado por victima (medido DAY299: 0 lineas [Cleanup]).\n"
     "SNIFFER_STOP_GRACE_S ?= 15\n"
     "sniffer-stop:\n"
     + T + "@vagrant ssh defender -c \"if pgrep -x sniffer >/dev/null; then \\\n"
     + T + "    sudo pkill -TERM -x sniffer; \\\n"
     + T + "    for i in \\$$(seq 1 $(SNIFFER_STOP_GRACE_S)); do pgrep -x sniffer >/dev/null || break; sleep 1; done; \\\n"
     + T + "    if pgrep -x sniffer >/dev/null; then \\\n"
     + T + "      echo '⚠️  sniffer no paró en $(SNIFFER_STOP_GRACE_S) s: SIGKILL (sin volcado de parada)'; \\\n"
     + T + "      sudo pkill -KILL -x sniffer; \\\n"
     + T + "    else echo '✅ sniffer parado de forma ordenada'; fi; \\\n"
     + T + "  else echo '➖ sniffer no estaba en marcha'; fi; \\\n"
     + T + "  tmux kill-session -t sniffer 2>/dev/null || true\"\n"
     "\n"
     "# ── sniffer-libpcap-start — Variant B (libpcap) ──────────────────────────────\n"),
    (MK,
     "pipeline-stop:\n" + T + "@echo \"🛑 Stopping all pipeline components...\"\n",
     "pipeline-stop:\n" + T + "@echo \"🛑 Stopping all pipeline components...\"\n"
     + T + "@$(MAKE) --no-print-directory sniffer-stop  # " + M + " parada ordenada antes del resto\n"),
    (MAIN,
     "    sigaction(SIGTERM, &sa, nullptr);\n",
     "    sigaction(SIGTERM, &sa, nullptr);\n"
     "    sigaction(SIGHUP, &sa, nullptr);  // " + M + " tmux kill-session (SIGHUP) = parada ordenada\n"),
    (MAIN,
     "    std::cout << \"✅ Signal handlers configured (SIGINT, SIGTERM)\" << std::endl;\n",
     "    std::cout << \"✅ Signal handlers configured (SIGINT, SIGTERM, SIGHUP)\" << std::endl;\n"),
]

APPEND_BACK = """
### DEBT-PIPELINE-STOP-GRACEFUL-001 — ABIERTA (decisión de Alonso DAY299) """ + M + """
pipeline-stop hacía tmux kill-session de cada componente: SIGHUP, y ninguno lo trataba, así que morían sin su
parada ordenada (medido DAY299 en el sniffer: 0 líneas [Cleanup] en sniffer.log). Hecho DAY299 para el
sniffer: target sniffer-stop (SIGTERM, espera SNIFFER_STOP_GRACE_S, SIGKILL de último recurso con aviso),
pipeline-stop lo llama primero, y el sniffer trata SIGHUP como parada ordenada. Pendiente: lo mismo para
ml-detector, firewall-acl-agent y el resto (decisión de Alonso: los procesos deben hacer su parada ordenada
también ante SIGHUP). El firewall lo necesitará para volcar strike_states_ en la parada.
"""


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply")
        return 2
    files = sorted({p for p, _, _ in EDITS} | {BACK})
    t = {p: open(p, encoding="utf-8").read() for p in files}
    hechos = [new in t[p] for p, _, new in EDITS] + [APPEND_BACK.strip()[:50] in t[BACK]]
    if all(hechos):
        print("[YA-APLICADO]")
        return 0
    if any(hechos):
        print("[ABORTA] mezcla de aplicado y pendiente:", hechos)
        return 1
    for i, (p, old, _) in enumerate(EDITS):
        n = t[p].count(old)
        if n != 1:
            print(f"[ABORTA] edicion {i} en {p}: ancla {n} veces: {old.splitlines()[0][:90]}")
            return 1
    if sys.argv[1] == "--check":
        print(f"[CHECK-OK] {len(EDITS)} ediciones y 1 anexo pendientes en {len(files)} ficheros")
        return 0
    for p, old, new in EDITS:
        t[p] = t[p].replace(old, new, 1)
    t[BACK] = t[BACK].rstrip("\n") + "\n" + APPEND_BACK
    for p in files:
        tmp = p + ".d299tmp"
        open(tmp, "w", encoding="utf-8").write(t[p])
        os.replace(tmp, p)
    print(f"[APLICADO] {len(EDITS)} ediciones y 1 anexo en {len(files)} ficheros {M}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
