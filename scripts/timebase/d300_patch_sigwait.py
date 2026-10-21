#!/usr/bin/env python3
"""DAY300 DEBT-SNIFFER-MAIN-LOOP-POLL-001: el hilo principal esperaba la parada sondeando g_running con
sleep_for(1 s) fijo (hasta 1 s de retraso en cada parada, medido 337-1086 ms). Ahora SIGINT/SIGTERM/SIGHUP
se bloquean en todos los hilos (mascara heredada, antes de crear ninguno) y el hilo principal las espera con
sigwait(): sin sondeo ni numero fijo. --check | --apply desde la raiz del repo. Atomico."""
import os
import sys

M = "[SIGWAIT-D300]"
MAIN = "sniffer/src/userspace/main.cpp"

OLD_SIG = (
    "void signal_handler(int signum) {\n"
    "    // async-signal-safe: write() only (DEBT-SIGNAL-001)\n"
    "    static const char msg[] = \"\\n[Signal] Shutdown signal received\\n\";\n"
    "    write(STDERR_FILENO, msg, sizeof(msg) - 1);\n"
    "    (void)signum;\n"
    "    g_running = false;\n"
    "}\n"
    "\n"
    "void setup_signal_handlers() {\n"
    "    struct sigaction sa;\n"
    "    sa.sa_handler = signal_handler;\n"
    "    sigemptyset(&sa.sa_mask);\n"
    "    sa.sa_flags = 0;\n"
    "\n"
    "    sigaction(SIGINT, &sa, nullptr);\n"
    "    sigaction(SIGTERM, &sa, nullptr);\n"
    "    sigaction(SIGHUP, &sa, nullptr);  // [SNIFFER-STOP-D299] tmux kill-session (SIGHUP) = parada ordenada\n"
    "\n"
    "    std::cout << \"✅ Signal handlers configured (SIGINT, SIGTERM, SIGHUP)\" << std::endl;\n"
    "}\n"
)

NEW_SIG = (
    "// " + M + " Senales de parada: se BLOQUEAN en el hilo principal antes de crear ningun hilo (la mascara\n"
    "// se hereda, asi que ningun hilo las recibe) y el hilo principal las espera con sigwait() en lugar de\n"
    "// sondear g_running. Sin manejador asincrono: el mensaje se escribe desde el hilo principal.\n"
    "// SIGHUP = parada ordenada [SNIFFER-STOP-D299] (tmux kill-session).\n"
    "sigset_t g_senales_parada;\n"
    "\n"
    "void setup_signal_handlers() {\n"
    "    sigemptyset(&g_senales_parada);\n"
    "    sigaddset(&g_senales_parada, SIGINT);\n"
    "    sigaddset(&g_senales_parada, SIGTERM);\n"
    "    sigaddset(&g_senales_parada, SIGHUP);\n"
    "    const int rc = pthread_sigmask(SIG_BLOCK, &g_senales_parada, nullptr);\n"
    "    if (rc != 0) {\n"
    "        std::cerr << \"[SIGWAIT] ERROR pthread_sigmask=\" << rc << \" (\" << std::strerror(rc)\n"
    "                  << \"): las senales de parada no quedan bloqueadas\" << std::endl;\n"
    "        return;\n"
    "    }\n"
    "    std::cout << \"✅ Senales de parada (SIGINT, SIGTERM, SIGHUP) bloqueadas en todos los hilos; \"\n"
    "                 \"el hilo principal las espera con sigwait\" << std::endl;\n"
    "}\n"
)

OLD_LOOP = (
    "        while (g_running) {\n"
    "            std::this_thread::sleep_for(std::chrono::seconds(1));\n"
    "        }\n"
)

NEW_LOOP = (
    "        {   // " + M + " espera la senal de parada sin sondeo\n"
    "            int sig = 0;\n"
    "            const int rc = sigwait(&g_senales_parada, &sig);\n"
    "            if (rc == 0) {\n"
    "                std::cout << \"\\n[Signal] \" << strsignal(sig) << \" (\" << sig\n"
    "                          << \") recibida: parada ordenada\" << std::endl;\n"
    "            } else {\n"
    "                std::cerr << \"\\n[Signal] sigwait fallo (\" << rc << \", \" << std::strerror(rc)\n"
    "                          << \"): parada ordenada\" << std::endl;\n"
    "            }\n"
    "            g_running = false;\n"
    "        }\n"
)

EDITS = [
    (MAIN, "#include <csignal>\n",
     "#include <csignal>\n#include <pthread.h>  // " + M + "\n#include <cstring>    // " + M + " strsignal, strerror\n"),
    (MAIN, OLD_SIG, NEW_SIG),
    (MAIN, OLD_LOOP, NEW_LOOP),
]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d300_patch_sigwait.py --check | --apply")
        return 2
    with open(MAIN, encoding="utf-8") as fh:
        t = fh.read()
    if M in t:
        print(MAIN + ": ya contiene " + M + " (ya aplicado)")
        return 1
    errores = []
    for i, (_, old, new) in enumerate(EDITS, 1):
        n = t.count(old)
        if n != 1:
            errores.append("edicion %d: el ancla aparece %d veces (se esperaba 1)" % (i, n))
            continue
        t = t.replace(old, new, 1)
    if errores:
        print("\n".join(errores))
        print("NADA aplicado")
        return 1
    if sys.argv[1] == "--check":
        print("OK --check: %d ediciones en %s, todas las anclas unicas" % (len(EDITS), MAIN))
        return 0
    tmp = MAIN + ".tmp_d300"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(t)
    os.chmod(tmp, os.stat(MAIN).st_mode)
    os.replace(tmp, MAIN)
    print("OK --apply: %d ediciones en %s con marca %s" % (len(EDITS), MAIN, M))
    return 0


if __name__ == "__main__":
    sys.exit(main())
