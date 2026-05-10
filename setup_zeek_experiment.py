#!/usr/bin/env python3
"""
setup_zeek_experiment.py — aRGus NDR DAY 147
Crea la infraestructura completa del experimento Zeek vs aRGus NDR,
equivalente al experimento Suricata (DAY 146).

Genera:
  experiments/zeek-comparative/Vagrantfile
  experiments/zeek-comparative/parse_results_zeek.py
  experiments/zeek-comparative/makefile_targets.mk  ← pegar en Makefile

Topología (simétrica a Suricata):
  zeek VM  : 192.168.56.22 (host-only) + 192.168.102.1 (zeek_experiment_lan)
  client VM: 192.168.102.50 (zeek_experiment_lan)
  Specs    : debian/bookworm64, 8192 MB, 6 vCPU, VirtIO — idéntico a Suricata

Uso:
    python3 setup_zeek_experiment.py [--base-dir PATH] [--dry-run]

Por defecto crea todo bajo ./experiments/zeek-comparative/
"""

import argparse
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# VAGRANTFILE
# ─────────────────────────────────────────────────────────────────────────────

VAGRANTFILE = r"""# ============================================================================
# aRGus NDR — Experiment Comparative: Zeek vs aRGus NDR
# Dataset: CTU-13 Neris (botnet-capture-20110810-neris.pcap)
# Hardware: identical to aRGus defender VM (8192MB, 6 vCPU, Debian bookworm64)
# Phase 1: default policy scripts (out-of-the-box, fair comparison)
# Speeds: 10, 50, 100 Mbps via tcpreplay
# Detection: notice.log (alerts) + conn.log (behavioral analysis)
# ============================================================================

Vagrant.configure("2") do |config|

  # ==========================================================================
  # VM 1: zeek — IDS node (mirrors aRGus defender VM exactly)
  # ==========================================================================
  config.vm.define "zeek", primary: true do |zeek|
    zeek.vm.box         = "debian/bookworm64"
    zeek.vm.box_version = "12.20240905.1"
    zeek.vm.hostname    = "zeek-ids"

    zeek.vm.provider "virtualbox" do |vb|
      vb.name   = "experiment-zeek-ids"
      vb.memory = "8192"
      vb.cpus   = 6
      vb.customize ["modifyvm", :id, "--nictype1", "virtio"]
      vb.customize ["modifyvm", :id, "--nictype2", "virtio"]
      vb.customize ["modifyvm", :id, "--nictype3", "virtio"]
      vb.customize ["modifyvm", :id, "--nicpromisc2", "allow-all"]
      vb.customize ["modifyvm", :id, "--ioapic", "on"]
      vb.customize ["modifyvm", :id, "--audio", "none"]
      vb.customize ["modifyvm", :id, "--usb", "off"]
      vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    end

    # eth1: host-only (management)  eth2: intnet (capture interface)
    zeek.vm.network "private_network", ip: "192.168.56.22"
    zeek.vm.network "private_network", ip: "192.168.102.1",
      virtualbox__intnet: "zeek_experiment_lan"

    zeek.vm.synced_folder "../..", "/vagrant", type: "virtualbox",
      mount_options: ["dmode=775,fmode=775,exec"]

    zeek.vm.provision "shell", name: "install-zeek", inline: <<-SHELL
      set -e
      export DEBIAN_FRONTEND=noninteractive
      echo "=== Installing Zeek + dependencies ==="
      apt-get update -qq
      apt-get install -y curl wget gnupg2 tcpreplay net-tools python3 procps jq ca-certificates

      # Add official Zeek repository for Debian 12 (bookworm)
      echo "--- Adding Zeek OBS repository ---"
      echo 'deb http://download.opensuse.org/repositories/security:/zeek/Debian_12/ /' \
        > /etc/apt/sources.list.d/zeek.list
      curl -fsSL https://download.opensuse.org/repositories/security:zeek/Debian_12/Release.key \
        | gpg --dearmor > /etc/apt/trusted.gpg.d/zeek.gpg
      apt-get update -qq
      apt-get install -y zeek

      # PATH permanently
      echo 'export PATH=/opt/zeek/bin:$PATH' > /etc/profile.d/zeek.sh
      chmod +x /etc/profile.d/zeek.sh
      export PATH=/opt/zeek/bin:$PATH

      zeek --version

      # Configure capture interface: eth2 receives tcpreplay traffic
      sed -i 's/interface=.*/interface=eth2/' /opt/zeek/etc/node.cfg

      # Promiscuous mode on eth2 (persistent)
      ip link set eth2 promisc on || true
      echo 'ip link set eth2 promisc on' >> /etc/rc.local
      chmod +x /etc/rc.local

      # Log output directory (shared with host via /vagrant)
      mkdir -p /vagrant/logs/experiment/zeek

      echo "=== Zeek ready (Phase 1: default policy scripts) ==="
      /opt/zeek/bin/zeek --version
    SHELL
  end

  # ==========================================================================
  # VM 2: client — tcpreplay (same as suricata experiment)
  # ==========================================================================
  config.vm.define "client", autostart: false do |client|
    client.vm.box         = "debian/bookworm64"
    client.vm.box_version = "12.20240905.1"
    client.vm.hostname    = "experiment-zeek-client"

    client.vm.provider "virtualbox" do |vb|
      vb.name   = "experiment-zeek-client"
      vb.memory = "1024"
      vb.cpus   = 2
      vb.customize ["modifyvm", :id, "--nictype1", "virtio"]
      vb.customize ["modifyvm", :id, "--nictype2", "virtio"]
    end

    client.vm.network "private_network", ip: "192.168.102.50",
      virtualbox__intnet: "zeek_experiment_lan"

    client.vm.synced_folder "../..", "/vagrant", type: "virtualbox",
      mount_options: ["dmode=775,fmode=775,exec"]

    client.vm.provision "shell", inline: <<-SHELL
      set -e
      apt-get update -qq
      apt-get install -y tcpreplay net-tools
      tcpreplay --version | head -1
      echo "=== Client ready ==="
    SHELL
  end

end
"""

# ─────────────────────────────────────────────────────────────────────────────
# PARSE_RESULTS_ZEEK.PY
# ─────────────────────────────────────────────────────────────────────────────

PARSE_RESULTS = '''#!/usr/bin/env python3
"""
parse_results_zeek.py — aRGus NDR DAY 147
Parsea notice.log y conn.log de Zeek para calcular TP/FP/FN/F1/Recall
contra el ground truth CTU-13 Neris (147.32.84.165, 646 flujos maliciosos).

Uso:
    python3 parse_results_zeek.py \\
        --notice /vagrant/logs/experiment/zeek/notice.log \\
        --conn   /vagrant/logs/experiment/zeek/conn.log \\
        --speed  50Mbps

Métricas:
    notice.log → TP/FP/FN/F1/Recall (detección primaria, equivalente a eve.json)
    conn.log   → análisis behavioral complementario del ground truth IP
"""

import argparse
import json
from pathlib import Path

MALICIOUS_IP  = "147.32.84.165"
GROUND_TRUTH  = 646          # flujos maliciosos conocidos
BENIGN_FLOWS  = 12075        # flujos benignos en el corpus Neris

# ─── Parser de logs Zeek (formato TSV con cabeceras #fields) ─────────────────

def parse_zeek_log(path: Path) -> list[dict]:
    """Lee un fichero de log Zeek TSV y devuelve lista de dicts."""
    if not path.exists():
        return []
    rows = []
    fields = []
    sep = "\\t"
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\\n")
            if line.startswith("#separator"):
                sep_hex = line.split()[-1]
                sep = bytes.fromhex(sep_hex.replace("\\\\x", "")).decode()
            elif line.startswith("#fields"):
                fields = line.split(sep)[1:]
            elif line.startswith("#"):
                continue
            elif fields:
                values = line.split(sep)
                rows.append(dict(zip(fields, values)))
    return rows

# ─── Análisis de notice.log ───────────────────────────────────────────────────

def analyse_notice(notice_path: Path) -> dict:
    rows = parse_zeek_log(notice_path)
    total_notices = len(rows)

    tp_rows, fp_rows = [], []
    for r in rows:
        src = r.get("src", r.get("id.orig_h", "-"))
        dst = r.get("dst", r.get("id.resp_h", "-"))
        if src == MALICIOUS_IP or dst == MALICIOUS_IP:
            tp_rows.append(r)
        else:
            fp_rows.append(r)

    tp = len(tp_rows)
    fp = len(fp_rows)
    fn = GROUND_TRUTH - tp  # malicious flows with no notice

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / GROUND_TRUTH
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    # Notice types breakdown
    note_counts = {}
    for r in rows:
        note = r.get("note", "Unknown")
        note_counts[note] = note_counts.get(note, 0) + 1

    return {
        "total_notices": total_notices,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "notice_types": note_counts,
        "tp_sample": [
            {"note": r.get("note"), "msg": r.get("msg", "")[:80]}
            for r in tp_rows[:5]
        ],
    }

# ─── Análisis de conn.log ─────────────────────────────────────────────────────

def analyse_conn(conn_path: Path) -> dict:
    rows = parse_zeek_log(conn_path)
    malicious_rows = [
        r for r in rows
        if r.get("id.orig_h") == MALICIOUS_IP or r.get("id.resp_h") == MALICIOUS_IP
    ]

    # Service breakdown
    services = {}
    for r in malicious_rows:
        svc = r.get("service", "-")
        services[svc] = services.get(svc, 0) + 1

    # Duration stats
    durations = []
    for r in malicious_rows:
        try:
            durations.append(float(r.get("duration", "0") or "0"))
        except ValueError:
            pass

    avg_dur = sum(durations) / len(durations) if durations else 0.0
    max_dur = max(durations) if durations else 0.0

    # Unique dest IPs
    dest_ips = {r.get("id.resp_h") for r in malicious_rows
                if r.get("id.orig_h") == MALICIOUS_IP}

    return {
        "total_flows_in_log": len(rows),
        "malicious_ip_flows": len(malicious_rows),
        "unique_dest_ips": len(dest_ips),
        "services": services,
        "avg_duration_s": round(avg_dur, 3),
        "max_duration_s": round(max_dur, 3),
    }

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Parse Zeek notice.log + conn.log → TP/FP/FN/F1 vs CTU-13 Neris"
    )
    parser.add_argument("--notice", required=True)
    parser.add_argument("--conn",   required=True)
    parser.add_argument("--speed",  default="unknown")
    parser.add_argument("--output", default=None,
                        help="Guardar JSON en fichero")
    args = parser.parse_args()

    notice_path = Path(args.notice)
    conn_path   = Path(args.conn)

    notice_stats = analyse_notice(notice_path)
    conn_stats   = analyse_conn(conn_path)

    result = {
        "speed":         args.speed,
        "ground_truth":  {"malicious_ip": MALICIOUS_IP,
                          "malicious_flows": GROUND_TRUTH,
                          "benign_flows": BENIGN_FLOWS},
        "notice_log":    notice_stats,
        "conn_log":      conn_stats,
        "zeek_phase":    "1-default-scripts",
    }

    print("=" * 60)
    print(f"Zeek experiment results — {args.speed}")
    print("=" * 60)
    print(f"\\n[notice.log — primary detection]")
    print(f"  Total notices : {notice_stats[\'total_notices\']}")
    print(f"  TP (malicious): {notice_stats[\'tp\']}")
    print(f"  FP (benign)   : {notice_stats[\'fp\']}")
    print(f"  FN (missed)   : {notice_stats[\'fn\']}")
    print(f"  Precision     : {notice_stats[\'precision\']:.4f}")
    print(f"  Recall        : {notice_stats[\'recall\']:.4f}")
    print(f"  F1            : {notice_stats[\'f1\']:.4f}")
    if notice_stats["notice_types"]:
        print(f"\\n  Notice types  :")
        for k, v in sorted(notice_stats["notice_types"].items(),
                            key=lambda x: -x[1]):
            print(f"    {k}: {v}")
    else:
        print("\\n  ⚠️  notice.log vacío — 0 alertas generadas")

    print(f"\\n[conn.log — behavioral analysis of {MALICIOUS_IP}]")
    print(f"  Total flows    : {conn_stats[\'total_flows_in_log\']}")
    print(f"  Malicious flows: {conn_stats[\'malicious_ip_flows\']}")
    print(f"  Unique dest IPs: {conn_stats[\'unique_dest_ips\']}")
    print(f"  Services       : {conn_stats[\'services\']}")
    print(f"  Avg duration   : {conn_stats[\'avg_duration_s\']}s")
    print(f"  Max duration   : {conn_stats[\'max_duration_s\']}s")
    print("=" * 60)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        print(f"\\n✅ JSON guardado en {out}")

    return result


if __name__ == "__main__":
    main()
'''

# ─────────────────────────────────────────────────────────────────────────────
# MAKEFILE TARGETS
# ─────────────────────────────────────────────────────────────────────────────

MAKEFILE_TARGETS = r"""
# ============================================================================
# Experiment Comparative: Zeek vs aRGus NDR (DAY 147)
# Phase 1: default policy scripts (out-of-the-box)
# Symmetric to Suricata experiment (DAY 146)
# Dataset: CTU-13 Neris — ground truth: 147.32.84.165 (646 flows)
# Detection: notice.log (primary) + conn.log (behavioral complement)
# Usage:
#   make experiment-zeek-up       # arrancar VMs
#   make experiment-zeek-run      # ejecutar 3 runs (10/50/100 Mbps)
#   make experiment-zeek-results  # parsear logs -> métricas
#   make experiment-zeek-down     # parar VMs
# ============================================================================

ZEEK_DIR     := experiments/zeek-comparative
ZEEK_LOGS    := /vagrant/logs/experiment/zeek
CTU13_NERIS  := /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap

.PHONY: experiment-zeek-up experiment-zeek-down experiment-zeek-run
.PHONY: experiment-zeek-replay-10 experiment-zeek-replay-50 experiment-zeek-replay-100
.PHONY: experiment-zeek-results experiment-zeek-status
.PHONY: up-zeek halt-zeek

up-zeek:
	@cd $(ZEEK_DIR) && vagrant up zeek

halt-zeek:
	@cd $(ZEEK_DIR) && vagrant halt

experiment-zeek-up:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🦓 Experiment Zeek — Arrancar VMs                        ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@cd $(ZEEK_DIR) && vagrant up zeek
	@cd $(ZEEK_DIR) && vagrant up client
	@echo "✅ VMs del experimento Zeek arrancadas"
	@cd $(ZEEK_DIR) && vagrant status

experiment-zeek-down:
	@echo "🛑 Parando VMs del experimento Zeek..."
	@cd $(ZEEK_DIR) && vagrant halt
	@echo "✅ VMs paradas"

experiment-zeek-status:
	@cd $(ZEEK_DIR) && vagrant status
	@cd $(ZEEK_DIR) && vagrant ssh zeek -c \
	  "export PATH=/opt/zeek/bin:\$$PATH && zeek --version" 2>/dev/null || true

experiment-zeek-replay-10:
	@echo "🦓 [Zeek Phase 1] Replay CTU-13 Neris — 10 Mbps..."
	@cd $(ZEEK_DIR) && vagrant ssh zeek -c " \
	  export PATH=/opt/zeek/bin:\$$PATH && \
	  pkill zeek 2>/dev/null || true && \
	  sleep 2 && \
	  rm -rf $(ZEEK_LOGS)/10mbps && \
	  mkdir -p $(ZEEK_LOGS)/10mbps && \
	  cd $(ZEEK_LOGS)/10mbps && \
	  nohup zeek -i eth2 local > zeek-stdout.log 2>&1 & \
	  sleep 5 && \
	  echo 'Zeek started, PID:' \$$(pgrep zeek)"
	@cd $(ZEEK_DIR) && vagrant ssh client -c " \
	  sudo tcpreplay -i eth1 --mbps=10 --stats=1 $(CTU13_NERIS) \
	    > /vagrant/logs/experiment/zeek/tcpreplay-zeek-10mbps.log 2>&1; \
	  echo \"exit=\$$?\" >> /vagrant/logs/experiment/zeek/tcpreplay-zeek-10mbps.log" || true
	@cd $(ZEEK_DIR) && vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/experiment/zeek/tcpreplay-zeek-10mbps.log 2>/dev/null | tail -6" || true
	@echo "⏳ Esperando drain Zeek (15s)..."
	@sleep 15
	@cd $(ZEEK_DIR) && vagrant ssh zeek -c \
	  "pkill zeek 2>/dev/null || true; sleep 2; \
	   echo 'Logs en $(ZEEK_LOGS)/10mbps:'; ls -lh $(ZEEK_LOGS)/10mbps/"

experiment-zeek-replay-50:
	@echo "🦓 [Zeek Phase 1] Replay CTU-13 Neris — 50 Mbps..."
	@cd $(ZEEK_DIR) && vagrant ssh zeek -c " \
	  export PATH=/opt/zeek/bin:\$$PATH && \
	  pkill zeek 2>/dev/null || true && \
	  sleep 2 && \
	  rm -rf $(ZEEK_LOGS)/50mbps && \
	  mkdir -p $(ZEEK_LOGS)/50mbps && \
	  cd $(ZEEK_LOGS)/50mbps && \
	  nohup zeek -i eth2 local > zeek-stdout.log 2>&1 & \
	  sleep 5 && \
	  echo 'Zeek started, PID:' \$$(pgrep zeek)"
	@cd $(ZEEK_DIR) && vagrant ssh client -c " \
	  sudo tcpreplay -i eth1 --mbps=50 --stats=1 $(CTU13_NERIS) \
	    > /vagrant/logs/experiment/zeek/tcpreplay-zeek-50mbps.log 2>&1; \
	  echo \"exit=\$$?\" >> /vagrant/logs/experiment/zeek/tcpreplay-zeek-50mbps.log" || true
	@cd $(ZEEK_DIR) && vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/experiment/zeek/tcpreplay-zeek-50mbps.log 2>/dev/null | tail -6" || true
	@echo "⏳ Esperando drain Zeek (15s)..."
	@sleep 15
	@cd $(ZEEK_DIR) && vagrant ssh zeek -c \
	  "pkill zeek 2>/dev/null || true; sleep 2; \
	   echo 'Logs en $(ZEEK_LOGS)/50mbps:'; ls -lh $(ZEEK_LOGS)/50mbps/"

experiment-zeek-replay-100:
	@echo "🦓 [Zeek Phase 1] Replay CTU-13 Neris — 100 Mbps..."
	@cd $(ZEEK_DIR) && vagrant ssh zeek -c " \
	  export PATH=/opt/zeek/bin:\$$PATH && \
	  pkill zeek 2>/dev/null || true && \
	  sleep 2 && \
	  rm -rf $(ZEEK_LOGS)/100mbps && \
	  mkdir -p $(ZEEK_LOGS)/100mbps && \
	  cd $(ZEEK_LOGS)/100mbps && \
	  nohup zeek -i eth2 local > zeek-stdout.log 2>&1 & \
	  sleep 5 && \
	  echo 'Zeek started, PID:' \$$(pgrep zeek)"
	@cd $(ZEEK_DIR) && vagrant ssh client -c " \
	  sudo tcpreplay -i eth1 --mbps=100 --stats=1 $(CTU13_NERIS) \
	    > /vagrant/logs/experiment/zeek/tcpreplay-zeek-100mbps.log 2>&1; \
	  echo \"exit=\$$?\" >> /vagrant/logs/experiment/zeek/tcpreplay-zeek-100mbps.log" || true
	@cd $(ZEEK_DIR) && vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/experiment/zeek/tcpreplay-zeek-100mbps.log 2>/dev/null | tail -6" || true
	@echo "⏳ Esperando drain Zeek (15s)..."
	@sleep 15
	@cd $(ZEEK_DIR) && vagrant ssh zeek -c \
	  "pkill zeek 2>/dev/null || true; sleep 2; \
	   echo 'Logs en $(ZEEK_LOGS)/100mbps:'; ls -lh $(ZEEK_LOGS)/100mbps/"

experiment-zeek-results:
	@echo "📊 Parseando resultados Zeek (notice.log + conn.log)..."
	@for SPEED in 10mbps 50mbps 100mbps; do \
	  echo ""; \
	  echo "── $$SPEED ────────────────────────────────────────────"; \
	  cd $(ZEEK_DIR) && vagrant ssh zeek -c " \
	    python3 /vagrant/experiments/zeek-comparative/parse_results_zeek.py \
	      --notice $(ZEEK_LOGS)/$$SPEED/notice.log \
	      --conn   $(ZEEK_LOGS)/$$SPEED/conn.log \
	      --speed  $$SPEED \
	      --output $(ZEEK_LOGS)/zeek_metrics_$$SPEED.json" 2>/dev/null || \
	  echo "  ⚠️  Logs no disponibles para $$SPEED"; \
	done
	@echo ""
	@echo "✅ Métricas en /vagrant/logs/experiment/zeek/zeek_metrics_*.json"

experiment-zeek-run: experiment-zeek-replay-10 experiment-zeek-replay-50 experiment-zeek-replay-100
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Experiment Zeek COMPLETADO — 3 runs (10/50/100)       ║"
	@echo "╠════════════════════════════════════════════════════════════╣"
	@echo "║  Phase 1: default policy scripts (out-of-the-box)        ║"
	@echo "║  Logs: logs/experiment/zeek/{10,50,100}mbps/             ║"
	@echo "║  notice.log → detección primaria (equivalente eve.json)  ║"
	@echo "║  conn.log   → análisis behavioral del ground truth IP    ║"
	@echo "║  Ground truth: 147.32.84.165 (646 flows maliciosos)      ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@$(MAKE) experiment-zeek-results
"""

# ─────────────────────────────────────────────────────────────────────────────
# SETUP SCRIPT
# ─────────────────────────────────────────────────────────────────────────────

def create_file(path: Path, content: str, dry_run: bool):
    if dry_run:
        print(f"  🔍 DRY-RUN — crearía: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  ✅ Creado: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Setup del experimento Zeek vs aRGus NDR (DAY 147)"
    )
    parser.add_argument("--base-dir", default="experiments/zeek-comparative",
                        help="Directorio base (default: experiments/zeek-comparative)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base = Path(args.base_dir)
    dry  = args.dry_run

    print(f"🦓 Setup experimento Zeek — {'DRY-RUN' if dry else 'ESCRITURA'}")
    print(f"   Directorio: {base.resolve()}\n")

    files = [
        (base / "Vagrantfile",           VAGRANTFILE),
        (base / "parse_results_zeek.py", PARSE_RESULTS),
        (base / "makefile_targets.mk",   MAKEFILE_TARGETS),
    ]

    for path, content in files:
        create_file(path, content, dry_run=dry)

    if not dry:
        # chmod +x en parse_results_zeek.py
        import os
        os.chmod(base / "parse_results_zeek.py", 0o755)

    print(f"""
{'─'*60}
{'DRY-RUN completado' if dry else '✅ Ficheros creados'}

Próximos pasos:
  1. Pega el contenido de makefile_targets.mk al final del Makefile
     (antes de la última sección de producción)

  2. Levanta las VMs del experimento:
       make experiment-zeek-up

  3. Ejecuta los 3 runs:
       make experiment-zeek-run

  4. Revisa métricas:
       make experiment-zeek-results
{'─'*60}
""")


if __name__ == "__main__":
    main()