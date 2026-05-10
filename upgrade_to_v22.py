#!/usr/bin/env python3
"""
upgrade_to_v22.py — aRGus NDR DAY 147
Aplica cambios v21 → v22 sobre docs/latex/main.tex:

  1. Cabecera: Draft v21 → v22
  2. \\date{}: Draft v21 → v22
  3. Abstract: añade párrafo Zeek (tres paradigmas) tras el bloque Suricata
  4. §8.14 NEW: Three Paradigms (insertar tras §8.13, antes de §9)
  5. Conclusion: añade párrafo tres paradigmas
  6. §13 Reproducibility: añade comandos Zeek

Uso:
    python3 upgrade_to_v22.py [--tex PATH] [--dry-run]
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime

# ─── 1. Cabecera ─────────────────────────────────────────────────────────────

OLD_HEADER = "% Draft v21 --- DAY 147 --- 10 May 2026"
NEW_HEADER = "% Draft v22 --- DAY 147 --- 10 May 2026"

# ─── 2. \date{} ──────────────────────────────────────────────────────────────

OLD_DATE = r"\date{Draft v21 --- May 2026}"
NEW_DATE = r"\date{Draft v22 --- May 2026}"

# ─── 3. Abstract: añadir párrafo Zeek ────────────────────────────────────────
# Insertar justo antes del cierre del bloque DAY 146 en el abstract

OLD_ABSTRACT_ANCHOR = r"""        % ─────────────────────────────────────────────────────────────────────────

        ML Defender is released under the MIT license."""

NEW_ABSTRACT_ANCHOR = r"""        % ── NEW DAY 147 ──────────────────────────────────────────────────────────
        We extend this head-to-head to a \emph{three-paradigm comparison} by adding
        Zeek~8.1.2 with default policy scripts (DAY~147,
        \S\ref{sec:eval:threeparadigms}): Zeek generates 14~correct detections
        (\texttt{SSL::Invalid\_Server\_Cert}, Precision$=1.0000$, F1$=0.0424$) while
        fully observing the botnet behavioral profile in structured logs
        (\texttt{weird.log}, \texttt{http.log}, \texttt{smtp.log}) without generating
        further alerts under default configuration --- placing scripted behavioral
        detection precisely between signature-based and ML-based approaches on the
        Recall axis (F1$=0.042$ vs F1$=0.9985$).
        % ─────────────────────────────────────────────────────────────────────────

        ML Defender is released under the MIT license."""

# ─── 4. §8.14 nueva subsección ───────────────────────────────────────────────
# Insertar después del cierre de §8.13 y antes de §9

OLD_SECTION9_ANCHOR = r"""    % ─────────────────────────────────────────────────────────────────────────

% ============================================================
    \section{Performance Model and Throughput Analysis}"""

NEW_SECTION9_ANCHOR = r"""    % ─────────────────────────────────────────────────────────────────────────

    % ── §8.14 NEW — DAY 147 ──────────────────────────────────────────────────
    \subsection{Three Paradigms: Signature, Scripted Behavioral, and ML Behavioral Detection}
    \label{sec:eval:threeparadigms}

    To complete the paradigm comparison initiated in \S\ref{sec:eval:suricata}, we
    extended the direct experimental comparison to include Zeek~8.1.2 with default
    policy scripts (DAY~147). The three systems represent distinct detection philosophies
    evaluated under identical conditions on the same corpus.

    \paragraph{Experimental protocol.}
    Zeek~8.1.2 was provisioned on a dedicated VM with the same specification as the
    Suricata and aRGus evaluations: \texttt{debian/bookworm64} v\texttt{12.20240905.1},
    8,192~MB RAM, 6~vCPUs, VirtIO NIC, VirtualBox~7.2. Zeek was evaluated in
    \emph{offline mode} (\texttt{zeek -r neris.pcap local}), reading the CTU-13 Neris
    pcap directly without live capture. This mode processes 100\% of the 320,524 packets
    deterministically, eliminating throughput-dependent packet loss as a confounding
    variable. The experiment executed three times at nominal 10, 50, and 100~Mbps; all
    three runs produced byte-identical results, confirming deterministic behavior. Default
    Zeek policy scripts were loaded without modification (\texttt{local.zeek}),
    equivalent to evaluating Suricata with the ET~Open ruleset without custom tuning.

    \begin{table}[h]
        \centering
        \caption{Three-paradigm detection comparison on CTU-13 Neris (DAY~147).
            Identical hardware, dataset, and corpus for all three systems.
            Ground truth: 147.32.84.165 (646 malicious flows, 12,075 benign flows).
            Zeek metrics exclude \texttt{CaptureLoss} infrastructure notices (6 entries,
            not detections). $^{\dagger}$~Zeek Precision$=1.0000$: every alert correctly
            identifies the malicious host; low F1 reflects the structural Recall
            limitation of scripted behavioral detection, not a system deficiency.}
        \label{tab:threeparadigms}
        \begin{tabular}{llrrrrrrr}
            \toprule
            \textbf{System} & \textbf{Paradigm} & \textbf{TP} & \textbf{FP} &
            \textbf{FN} & \textbf{Prec.} & \textbf{Recall} & \textbf{F1} \\
            \midrule
            Suricata~6.0.10      & Signature (ET Open)  & 0   & 0 & 646
                                 & ---    & 0.0000 & 0.0000 \\
            Zeek~8.1.2 (default) & Scripted behavioral  & 14  & 0 & 632
                                 & \textbf{1.0000}$^{\dagger}$ & 0.0217 & 0.0424 \\
            \textbf{aRGus NDR}   & ML behavioral        & \textbf{646} & 2 & 0
                                 & 0.9969 & \textbf{1.0000} & \textbf{0.9985} \\
            \bottomrule
        \end{tabular}
    \end{table}

    \paragraph{Zeek detection detail.}
    Zeek generates 20 raw notices: 6 are \texttt{CaptureLoss} infrastructure metadata
    (excluded from metrics) and 14 are genuine \texttt{SSL::Invalid\_Server\_Cert}
    detections, all originating from the ground truth IP~(147.32.84.165). The bot
    connected to servers with untrusted certificate chains --- Microsoft Update
    infrastructure (65.55.196.251, 65.55.16.187) and Google services
    (74.125.224.242) --- which Zeek's TLS dissector flags regardless of whether the
    connecting host is known to be malicious. This is structural detection: Zeek
    validates certificate chains as part of protocol analysis, not as a behavioral
    heuristic.

    \begin{table}[h]
        \centering
        \caption{Zeek~8.1.2 behavioral visibility on CTU-13 Neris --- observations
            recorded in structured logs without generating \texttt{notice.log} alerts
            under default policy scripts. Zeek observes the complete behavioral
            profile of the botnet; the gap between visibility and detection is the
            core finding of this comparison.}
        \label{tab:zeek_visibility}
        \begin{tabular}{llr}
            \toprule
            \textbf{Log} & \textbf{Observation} & \textbf{Count} \\
            \midrule
            \texttt{conn.log}
                & Flows from/to malicious host       & 31,736 \\
                & Unique destination IPs              & 4,199  \\
                & DNS flows                           & 8,896  \\
                & HTTP flows (C2 + click fraud)       & 1,236  \\
                & SMTP flows (spam)                   & 63     \\
                & SSL flows                           & 63     \\
            \midrule
            \texttt{weird.log}
                & \texttt{unknown\_dce\_rpc\_auth\_type} (SMB lateral movement) & 33 \\
                & \texttt{bad\_HTTP\_request} (malformed C2 beaconing)          & 31 \\
                & \texttt{empty\_http\_request} (beaconing)                     & 31 \\
                & \texttt{irc\_invalid\_command} (IRC C2 present)               & 30 \\
                & \texttt{premature\_connection\_reuse}                          & 28 \\
            \midrule
            \texttt{http.log}
                & Total HTTP requests (GET + POST)    & 1,377 \\
                & Top C2 host: \texttt{1.95622.com}   & 300   \\
                & Top C2 host: \texttt{www.lddwj.com} & 136   \\
            \midrule
            \texttt{smtp.log}
                & Spam sessions (forged AOL identities) & 82 \\
            \midrule
            \texttt{ssl.log}
                & SSL flows from malicious host       & 63 \\
                & Invalid certificates ($\to$ notices) & 47 \\
            \bottomrule
        \end{tabular}
    \end{table}

    \paragraph{The three-paradigm spectrum.}
    These results define three structurally distinct detection philosophies:

    \begin{itemize}[noitemsep]
        \item \textbf{Suricata (signature-based):} requires prior knowledge of the
        exact threat identity. F1$=0.000$ on 15-year-old traffic not because the engine
        fails, but because no matching rule exists for a retired threat family. Correct
        behavior of a correct system operating as designed.

        \item \textbf{Zeek (scripted behavioral):} detects structural anomalies with
        Precision$=1.000$ --- every alert correctly identifies the malicious host.
        However, Recall$=0.022$ reflects a fundamental design property: default
        policy scripts alert on specific structural violations (invalid certificates,
        malformed protocol fields), not on behavioral flow patterns. Table~\ref{tab:zeek_visibility}
        demonstrates that Zeek \emph{observes} the complete behavioral profile of the
        botnet --- IRC commands, HTTP beaconing to 4,199 unique destinations, SMB
        lateral movement, 82 spam sessions --- but does not convert these observations
        to alerts under default configuration. Zeek is a high-fidelity network
        observability platform with selective detection capability.

        \item \textbf{aRGus NDR (ML behavioral):} classifies the behavioral footprint
        of the malware --- how many hosts it contacts, what protocols it abuses, the
        statistical structure of its flows --- without requiring prior knowledge of the
        threat's identity or any structural protocol violation. Recall$=1.000$ and
        F1$=0.9985$ on traffic the classifier had never seen during training.
    \end{itemize}

    \paragraph{Scientific significance.}
    This three-way comparison yields a finding that no two-system comparison could
    produce: \emph{Precision and Recall are not in fundamental tension for ML behavioral
    detection --- they are in structural tension for scripted behavioral detection.}
    Zeek achieves perfect Precision at the cost of near-zero Recall; aRGus achieves
    both simultaneously. This is not a deficiency of Zeek: it is the structural
    consequence of the architectural difference between \emph{detecting structural
    anomalies} and \emph{classifying behavioral patterns}.

    A secondary finding emerges from \texttt{weird.log}: the entry
    \texttt{irc\_invalid\_command:~30} confirms the presence of IRC traffic in the
    CTU-13 Neris capture, partially refuting the scenario README which describes only
    HTTP C2. The behavioral reality is more complex --- the bot exhibited both IRC and
    HTTP C2 patterns --- reinforcing the argument that any single-modality detector
    (signature-based or structurally-anomaly-based) is incomplete against multi-protocol
    botnet behavior~\cite{asad2023perspective}.

    % ─────────────────────────────────────────────────────────────────────────

% ============================================================
    \section{Performance Model and Throughput Analysis}"""

# ─── 5. Conclusion: añadir párrafo tres paradigmas ───────────────────────────

OLD_CONCLUSION_ANCHOR = r"""    % ── NEW DAY 146 ──────────────────────────────────────────────────────────
    The first direct experimental comparison of aRGus NDR and Suricata~6.0.10 on the same
    dataset, hardware, and topology (DAY~146, \S\ref{sec:eval:suricata}) yields a result that
    is both clear and scientifically meaningful: Suricata with 50,010 current ET~Open rules
    generates zero alerts on CTU-13 Neris 2011; aRGus achieves F1$=0.9985$ on the same traffic.
    The zero-alert result is not a failure of Suricata --- it is the expected behavior of a
    signature-based IDS when no matching rule exists for a 15-year-old threat family. The
    finding provides direct empirical support for the architectural thesis of this paper:
    \emph{behavioral ML detects what the traffic does; signatures detect what the traffic is
    known to be.}
    % ─────────────────────────────────────────────────────────────────────────"""

NEW_CONCLUSION_ANCHOR = r"""    % ── NEW DAY 146 ──────────────────────────────────────────────────────────
    The first direct experimental comparison of aRGus NDR and Suricata~6.0.10 on the same
    dataset, hardware, and topology (DAY~146, \S\ref{sec:eval:suricata}) yields a result that
    is both clear and scientifically meaningful: Suricata with 50,010 current ET~Open rules
    generates zero alerts on CTU-13 Neris 2011; aRGus achieves F1$=0.9985$ on the same traffic.
    The zero-alert result is not a failure of Suricata --- it is the expected behavior of a
    signature-based IDS when no matching rule exists for a 15-year-old threat family. The
    finding provides direct empirical support for the architectural thesis of this paper:
    \emph{behavioral ML detects what the traffic does; signatures detect what the traffic is
    known to be.}
    % ─────────────────────────────────────────────────────────────────────────

    % ── NEW DAY 147 ──────────────────────────────────────────────────────────
    The extension to a \emph{three-paradigm comparison} (DAY~147,
    \S\ref{sec:eval:threeparadigms}) adds Zeek~8.1.2 as the critical intermediate
    data point: scripted behavioral detection achieves Precision$=1.0000$ but
    Recall$=0.0217$, correctly identifying the malicious host in every alert while
    missing 97.8\% of malicious flows. The \texttt{weird.log} reveals that Zeek
    \emph{observes} the complete behavioral profile of the botnet --- IRC commands,
    HTTP beaconing to 4,199 unique destinations, SMB lateral movement, 82 spam
    sessions --- without converting these observations to alerts under default
    policy scripts. This distinction between \emph{network observability} and
    \emph{behavioral detection} is the core scientific finding of the three-paradigm
    comparison. The result could only emerge from a three-way experiment: with two
    systems, the distinction between ``cannot detect'' and ``chooses not to alert''
    is invisible.
    % ─────────────────────────────────────────────────────────────────────────"""

# ─── 6. §13 Reproducibility: añadir bloque Zeek ──────────────────────────────

OLD_REPRO_ANCHOR = r"""    \paragraph{Stress Test.}
    \begin{lstlisting}[language=bash]
vagrant ssh client -c "sudo tcpreplay -i eth1 --mbps=100 --loop=3 \
  /vagrant/datasets/ctu13/bigFlows.pcap"
    \end{lstlisting}"""

NEW_REPRO_ANCHOR = r"""    % ── NEW DAY 147 ──────────────────────────────────────────────────────────
    \paragraph{Zeek Three-Paradigm Experiment (DAY~147).}
    \begin{lstlisting}[language=bash]
# Provision Zeek VM (debian/bookworm64, 8GB RAM, 6 vCPU -- identical to aRGus)
make experiment-zeek-up

# Offline analysis: zeek -r neris.pcap local (x3 runs, deterministic)
make experiment-zeek-run
# Raw logs: logs/experiment/zeek/{10,50,100}mbps/{notice,conn,weird,http,smtp,ssl}.log

# Parse corrected metrics (CaptureLoss excluded)
cd experiments/zeek-comparative && vagrant ssh zeek -c "
  python3 /vagrant/experiments/zeek-comparative/parse_results_zeek_v2.py \
    --logdir /vagrant/logs/experiment/zeek/10mbps \
    --output /vagrant/logs/experiment/zeek/zeek_metrics_v2_10mbps.json"
    \end{lstlisting}
    % ─────────────────────────────────────────────────────────────────────────

    \paragraph{Stress Test.}
    \begin{lstlisting}[language=bash]
vagrant ssh client -c "sudo tcpreplay -i eth1 --mbps=100 --loop=3 \
  /vagrant/datasets/ctu13/bigFlows.pcap"
    \end{lstlisting}"""

# ─────────────────────────────────────────────────────────────────────────────

CHANGES = [
    ("Cabecera (v21→v22)",              OLD_HEADER,            NEW_HEADER),
    (r"\date{} (v21→v22)",              OLD_DATE,              NEW_DATE),
    ("Abstract: párrafo Zeek",          OLD_ABSTRACT_ANCHOR,   NEW_ABSTRACT_ANCHOR),
    ("§8.14 Three Paradigms",           OLD_SECTION9_ANCHOR,   NEW_SECTION9_ANCHOR),
    ("Conclusion: párrafo v22",         OLD_CONCLUSION_ANCHOR, NEW_CONCLUSION_ANCHOR),
    ("§13 Reproducibility: Zeek",       OLD_REPRO_ANCHOR,      NEW_REPRO_ANCHOR),
]

VERIFY = [
    ("Draft v22",                       "v22 en cabecera"),
    ("sec:eval:threeparadigms",         "§8.14 label"),
    ("tab:threeparadigms",              "tabla tres paradigmas"),
    ("tab:zeek_visibility",             "tabla visibilidad Zeek"),
    ("Three Paradigms",                 "título §8.14"),
    ("irc_invalid_command",             "hallazgo IRC en weird.log"),
    ("experiment-zeek-up",              "Zeek en §13"),
    ("three-paradigm comparison",       "párrafo conclusión v22"),
]


def main():
    parser = argparse.ArgumentParser(
        description="Actualiza main.tex v21 → v22 (DAY 147: §8.14 tres paradigmas)"
    )
    parser.add_argument("--tex", default="docs/latex/main.tex")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tex = Path(args.tex)
    if not tex.exists():
        print(f"❌ No se encuentra: {tex}")
        sys.exit(1)

    content = tex.read_text(encoding="utf-8")
    print(f"📄 TEX : {tex.resolve()}")
    print(f"{'🔍 DRY-RUN' if args.dry_run else '✏️  Escritura'}\n")

    ok = True
    for label, old, new in CHANGES:
        if old not in content:
            print(f"  ❌ NO ENCONTRADO — {label}")
            ok = False
        elif args.dry_run:
            print(f"  🔍 OK — {label}")
        else:
            content = content.replace(old, new, 1)
            print(f"  ✅ Aplicado — {label}")

    if args.dry_run:
        print("\n✅ Dry-run OK" if ok else "\n❌ Hay cambios no encontrados")
        return

    if not ok:
        print("\n❌ Cambios no encontrados — no se escribe en disco.")
        sys.exit(1)

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = tex.with_suffix(f".bak_{ts}.tex")
    shutil.copy2(tex, bak)
    print(f"\n📦 Backup: {bak.name}")

    tex.write_text(content, encoding="utf-8")

    # Verificación
    print("\n── Verificación ─────────────────────────────────────────────")
    final = tex.read_text(encoding="utf-8")
    all_ok = True
    for needle, label in VERIFY:
        if needle in final:
            print(f"  ✅ {label}")
        else:
            print(f"  ❌ FALTA: {label}")
            all_ok = False

    if all_ok:
        print("""
╔════════════════════════════════════════════════════════════╗
║  ✅ v22 aplicado — 6/6 cambios, 8/8 verificaciones       ║
╚════════════════════════════════════════════════════════════╝""")
    else:
        print("\n⚠️  Verificación incompleta.")
        sys.exit(1)


if __name__ == "__main__":
    main()