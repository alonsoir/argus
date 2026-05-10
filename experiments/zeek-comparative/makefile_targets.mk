
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
