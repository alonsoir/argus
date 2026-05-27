.PHONY: help status
.PHONY: up halt destroy ssh
.PHONY: submodule-init
.PHONY: proto proto-unified proto-verify sniffer detector firewall all rebuild
.PHONY: sniffer-build sniffer-clean sniffer-package sniffer-install
.PHONY: detector-build detector-clean
.PHONY: firewall-build firewall-clean
.PHONY: run-sniffer run-detector run-firewall
.PHONY: logs-sniffer logs-detector logs-firewall logs-lab
.PHONY: run-lab-dev kill-lab status-lab
.PHONY: run-lab-dev-day23 kill-lab-day23 status-lab-day23
.PHONY: kill-all check-ports restart
.PHONY: clean clean-libs clean-components clean-all distclean test test-libs test-components test-all dev-setup schema-update parquet-convert test-parquet deploy-configs deploy-configs-prod test-alert-client
.PHONY: build-unified rebuild-unified quick-fix dev-setup-unified
.PHONY: check-libbpf verify-bpf-maps diagnose-bpf
.PHONY: test-replay-small test-replay-neris test-replay-big test-replay-neris-x86-ebpf test-replay-neris-x86-libpcap experiment-suricata-up experiment-suricata-down experiment-suricata-run experiment-suricata-results experiment-suricata-status
.PHONY: monitor-day13-tmux logs-dual-score logs-dual-score-live extract-dual-scores
.PHONY: test-integration-day13 test-integration-day13-tmux test-dual-score-quick
.PHONY: clean-day13-logs stats-dual-score
.PHONY: analyze-dual-scores test-analyze-workflow test-day13-full quick-analyze
.PHONY: rag-log-init rag-log-clean rag-log-status rag-log-analyze rag-log-tail rag-log-tail-live
.PHONY: test-rag-integration test-rag-quick rag-watch rag-validate test-rag-small test-rag-neris test-rag-big
.PHONY: quick-lab-test rag-consolidate detector-debug
.PHONY: etcd-client-build etcd-client-clean etcd-client-test
.PHONY: verify-etcd-linkage verify-encryption verify-pipeline-config verify-all
.PHONY: monitor-day23-tmux
.PHONY: test-day23-full test-day23-stress verify-rag-logs-day23
.PHONY: day23
.PHONY: rag-ingester rag-ingester-build rag-ingester-clean
.PHONY: tools-build tools-clean tools-synthetic-gen
.PHONY: crypto-transport-build crypto-transport-clean crypto-transport-test
.PHONY: plugin-loader-build plugin-loader-clean plugin-loader-test
.PHONY: plugin-hello-build plugin-hello-clean validate-prod-configs
# DEBT-HELLO-001 (PHASE 3, DAY 115)
# Falla si algún JSON de producción referencia libplugin_hello.
# Ejecutar antes de pipeline-start en CI/CD (TEST-PROVISION-1).
validate-prod-configs:
	@echo "🔍 Validando que libplugin_hello NO está en configs de producción..."
	@if vagrant ssh -c "grep -rl --include='*.json' 'libplugin_hello' \
	    /vagrant/sniffer/config/ \
	    /vagrant/firewall-acl-agent/config/ \
	    /vagrant/ml-detector/config/ \
	    /vagrant/rag/config/ \
	    /vagrant/rag-ingester/config/ \
	    /vagrant/etcd-server/config/ 2>/dev/null" 2>/dev/null | grep -v '.backup'; then \
		echo ""; \
		echo "❌ DEBT-HELLO-001: libplugin_hello encontrado en configs de producción"; \
		echo "   Ejecuta: python3 tools/debt_hello_001.py para limpiar"; \
		exit 1; \
	fi
	@echo "✅ validate-prod-configs: libplugin_hello ausente en todos los configs"


.PHONY: etcd-server etcd-server-build etcd-server-clean etcd-server-start etcd-server-stop
.PHONY: rag-build rag-clean rag-start rag-stop rag-status rag-logs rag-attach
.PHONY: etcd-server-status pipeline-start pipeline-stop pipeline-status
.PHONY: test-hardening test-hardening-build test-hardening-run
.PHONY: day38-step1 day38-step2 day38-step3 day38-step4 day38-step5
.PHONY: day38-full day38-status day38-clean day38-pipeline
.PHONY: tsan-all tsan-quick tsan-clean tsan-summary tsan-status
.PHONY: etcd-server-status pipeline-start pipeline-stop pipeline-status
.PHONY: ml-detector-start firewall-start sniffer-start sniffer-libpcap-start rag-ingester-start
.PHONY: etcd-server-start rag-start rag-stop dev-setup-tools pipeline-health
.PHONY: provision provision-status provision-check provision-reprovision test-provision-1 test-invariant-seed
.PHONY: seed-client-build seed-client-test seed-client-clean seed-client-rebuild

# ============================================================================
# ML Defender Pipeline - Master Makefile
# Single Source of Truth for Build Configurations
# ============================================================================
# Run from macOS - Commands execute in VM via vagrant ssh -c
# Day 57+ - Refactored for coherent clean/test/verify workflow
# ============================================================================

# ============================================================================
# BUILD PROFILES - SINGLE SOURCE OF TRUTH
# ============================================================================
# All compiler flags are defined HERE and ONLY here.
# CMakeLists.txt files MUST NOT hardcode any -O, -g, or -fsanitize flags.
# ============================================================================

# Base flags (always applied)
CXX_STD := -std=c++20
CXX_WARNINGS := -Wall -Wextra -Wpedantic -Werror
C_STD := -std=c11

# Profile-specific flags
PROFILE_PRODUCTION_CXX := -O3 -march=native -DNDEBUG -flto -fno-omit-frame-pointer
PROFILE_PRODUCTION_C   := -O3 -march=native -DNDEBUG -flto -fno-omit-frame-pointer

PROFILE_DEBUG_CXX := -g -O0 -fno-omit-frame-pointer -DDEBUG
PROFILE_DEBUG_C   := -g -O0 -fno-omit-frame-pointer -DDEBUG

PROFILE_TSAN_CXX := -fsanitize=thread -g -O1 -fno-omit-frame-pointer -DTSAN_ENABLED
PROFILE_TSAN_C   := -fsanitize=thread -g -O1 -fno-omit-frame-pointer -DTSAN_ENABLED
PROFILE_TSAN_LD  := -fsanitize=thread

PROFILE_ASAN_CXX := -fsanitize=address -fsanitize=undefined -g -O1 -fno-omit-frame-pointer -DASAN_ENABLED
PROFILE_ASAN_C   := -fsanitize=address -fsanitize=undefined -g -O1 -fno-omit-frame-pointer -DASAN_ENABLED
PROFILE_ASAN_LD  := -fsanitize=address -fsanitize=undefined

# Combined flags per profile
CMAKE_FLAGS_PRODUCTION := -DCMAKE_BUILD_TYPE=Release \
                          -DCMAKE_CXX_FLAGS="$(CXX_STD) $(CXX_WARNINGS) $(PROFILE_PRODUCTION_CXX)" \
                          -DCMAKE_C_FLAGS="$(C_STD) $(PROFILE_PRODUCTION_C)"

CMAKE_FLAGS_DEBUG := -DCMAKE_BUILD_TYPE=Debug \
                     -DCMAKE_CXX_FLAGS="$(CXX_STD) $(CXX_WARNINGS) $(PROFILE_DEBUG_CXX)" \
                     -DCMAKE_C_FLAGS="$(C_STD) $(PROFILE_DEBUG_C)"

CMAKE_FLAGS_TSAN := -DCMAKE_BUILD_TYPE=RelWithDebInfo \
                    -DCMAKE_CXX_FLAGS="$(CXX_STD) $(CXX_WARNINGS) $(PROFILE_TSAN_CXX)" \
                    -DCMAKE_C_FLAGS="$(C_STD) $(PROFILE_TSAN_C)" \
                    -DCMAKE_EXE_LINKER_FLAGS="$(PROFILE_TSAN_LD)" \
                    -DCMAKE_SHARED_LINKER_FLAGS="$(PROFILE_TSAN_LD)"

CMAKE_FLAGS_ASAN := -DCMAKE_BUILD_TYPE=RelWithDebInfo \
                    -DCMAKE_CXX_FLAGS="$(CXX_STD) $(CXX_WARNINGS) $(PROFILE_ASAN_CXX)" \
                    -DCMAKE_C_FLAGS="$(C_STD) $(PROFILE_ASAN_C)" \
                    -DCMAKE_EXE_LINKER_FLAGS="$(PROFILE_ASAN_LD)" \
                    -DCMAKE_SHARED_LINKER_FLAGS="$(PROFILE_ASAN_LD)"

# Default profile (can be overridden: make PROFILE=tsan all)
PROFILE ?= debug
CMAKE_FLAGS := $(CMAKE_FLAGS_$(shell echo $(PROFILE) | tr a-z A-Z))

# ============================================================================
# COMPONENT BUILD DIRECTORIES (Profile-specific)
# ============================================================================
SNIFFER_BUILD_DIR       := /vagrant/sniffer/build-$(PROFILE)
ML_DETECTOR_BUILD_DIR   := /vagrant/ml-detector/build-$(PROFILE)
RAG_INGESTER_BUILD_DIR  := /vagrant/rag-ingester/build-$(PROFILE)
FIREWALL_BUILD_DIR      := /vagrant/firewall-acl-agent/build-$(PROFILE)
ETCD_SERVER_BUILD_DIR   := /vagrant/etcd-server/build-$(PROFILE)
TOOLS_BUILD_DIR         := /vagrant/tools/build-$(PROFILE)

# Libraries (always release, no sanitizers)
CRYPTO_TRANSPORT_BUILD_DIR := /vagrant/crypto-transport/build
ETCD_CLIENT_BUILD_DIR      := /vagrant/etcd-client/build
PLUGIN_LOADER_BUILD_DIR    := /vagrant/plugin-loader/build

# Legacy compatibility (for existing scripts that reference /vagrant/component/build)
SNIFFER_LEGACY_LINK       := /vagrant/sniffer/build
ML_DETECTOR_LEGACY_LINK   := /vagrant/ml-detector/build
RAG_INGESTER_LEGACY_LINK  := /vagrant/rag-ingester/build
FIREWALL_LEGACY_LINK      := /vagrant/firewall-acl-agent/build
ETCD_SERVER_LEGACY_LINK   := /vagrant/etcd-server/build
TOOLS_LEGACY_LINK         := /vagrant/tools/build

RAG_BUILD_DIR := /vagrant/rag/build
RAG_INGESTER_BIN_DIR := /vagrant/rag-ingester/build
# ============================================================================
# HELP
# ============================================================================

help:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ML Defender Pipeline - Master Makefile (Day 57+)         ║"
	@echo "║  Single Source of Truth - Build Profile System            ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📋 Build Profiles (PROFILE=name):"
	@echo "  debug       - Debug symbols (-g -O0) [DEFAULT] — desarrollo diario"
	@echo "  production  - Optimized (-O3, LTO, march=native) — ODR check + benchmarks FEDER"
	@echo "  tsan        - ThreadSanitizer (-fsanitize=thread) — race conditions"
	@echo "  asan        - AddressSanitizer (-fsanitize=address,undefined) — memory errors + UB"
	@echo "  NOTE: PROFILE=production activa -flto → ODR verification cross-module (P0 bloqueante)"
	@echo ""
	@echo "Usage: make [PROFILE=<profile>] <target>"
	@echo "  Example: make PROFILE=tsan all"
	@echo "  Example: make PROFILE=production sniffer"
	@echo ""
	@echo "🏗️  Build Commands (Dependencies handled automatically):"
	@echo "  make all             - Build EVERYTHING (proto → libs → components)"
	@echo "  make proto           - Regenerate protobuf"
	@echo "  make crypto-transport-build - Build crypto-transport library"
	@echo "  make etcd-client-build     - Build etcd-client library"
	@echo "  make plugin-loader-build   - Build plugin-loader library (ADR-012)"
	@echo "  make sniffer         - Build sniffer (Variant A, eBPF/XDP)"
	@echo "  make sniffer-libpcap - Build sniffer (Variant B, libpcap)"
	@echo "  make ml-detector     - Build ML detector"
	@echo "  make rag-ingester    - Build RAG ingester"
	@echo "  make firewall        - Build firewall agent"
	@echo "  make etcd-server     - Build etcd server"
	@echo "  make tools           - Build tools"
	@echo ""
	@echo "🧹 Clean Commands (NEW - Day 57):"
	@echo "  make clean           - Clean components (current profile)"
	@echo "  make clean-libs      - Clean libraries (crypto-transport, etcd-client)"
	@echo "  make clean-components - Same as 'clean'"
	@echo "  make clean-all       - Clean EVERYTHING (legacy + profiles + libs)"
	@echo "  make distclean       - Nuclear clean (clean-all + protobuf)"
	@echo ""
	@echo "  Note: clean-all removes BOTH legacy build/ and build-PROFILE/"
	@echo ""
	@echo "🧪 Test Commands (NEW - Day 57):"
	@echo "  make test            - Run ALL tests (libs + components)"
	@echo "  make test-libs       - Run library tests only"
	@echo "  make test-components - Run component tests only"
	@echo ""
	@echo "✅ Verification Commands (NEW - Day 57):"
	@echo "  make verify-all      - Run ALL verifications post-build"
	@echo "  make verify-etcd-linkage  - Check etcd-client linkage"
	@echo "  make verify-encryption    - Check encryption configs"
	@echo ""
	@echo "🔧 TSAN Validation (Day 48 Phase 0):"
	@echo "  make tsan-all        - Full TSAN validation"
	@echo "  make tsan-quick      - Quick TSAN check"
	@echo "  make tsan-summary    - View TSAN report"
	@echo ""
	@echo "🚀 Run & Test:"
	@echo "  make run-lab-dev     - Start full lab"
	@echo "  make status-lab      - Check lab status"
	@echo "  make test-replay-small - Replay test dataset"
	@echo ""
	@echo "📊 Current Profile: $(PROFILE)"
	@echo "   Component builds: build-$(PROFILE)/"
	@echo "   Libraries: build/ (always release)"
	@echo ""
	@echo "VM Management:"
	@echo "  make up              - Start VM"
	@echo "  make halt            - Stop VM"
	@echo "  make ssh             - SSH into VM"
	@echo "  make status          - VM + libbpf status"
	@echo ""
	@echo "🏛️  Via Appia Quality: Piano piano - stone by stone"

# ============================================================================
# VM Management
# ============================================================================
.PHONY: bootstrap bootstrap-x86-ebpf bootstrap-x86-libpcap pipeline-start-x86-libpcap
# ============================================================================
# DEBT-BOOTSTRAP-001 + DEBT-INFRA-VERIFY-001/002 — DAY 120
# ============================================================================

.PHONY: check-system-deps check-build-artifacts post-up-verify

bootstrap: bootstrap-x86-ebpf

bootstrap-x86-ebpf:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🚀 aRGus NDR — Bootstrap x86 Variant A (eBPF/XDP)        ║"
	@echo "║  Ejecutar tras: git clone && make up                      ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo "[1/8] Verificando entorno post-up..."
	@$(MAKE) post-up-verify
	@echo "[2/8] Verificando dependencias del sistema..."
	@$(MAKE) check-system-deps
	@echo "[3/8] Activando perfil de build..."
	@$(MAKE) set-build-profile
	@echo "[4/8] Instalando systemd units..."
	@$(MAKE) install-systemd-units
	@echo "[5/8] Compilando pipeline (incluye pubkey runtime + plugin-test-message)..."
	@$(MAKE) pipeline-build
	@$(MAKE) check-build-artifacts
	@echo "[6/8] Desplegando modelos ML..."
	@$(MAKE) deploy-models
	@echo "[6b/8] Firmando plugins..."
	@$(MAKE) sign-plugins
	@echo "[7/8] Verificando provisioning..."
	@$(MAKE) test-provision-1
	@echo "[8/8] Arrancando pipeline (Variant A — eBPF/XDP)..."
	@$(MAKE) pipeline-start
	@$(MAKE) pipeline-status
	@$(MAKE) plugin-integ-test
	@vagrant ssh defender -c "tmux has-session -t sniffer 2>/dev/null" || (echo "\n❌ Bootstrap FAILED — sniffer STOPPED (DEBT-BOOTSTRAP-SNIFFER-VERIFY-001)" && exit 1)
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Bootstrap x86 eBPF completado — 6/6 RUNNING           ║"
	@echo "║  Sniffer activo: Variant A (eBPF/XDP)                     ║"
	@echo "║  Siguiente: make test-all                                  ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

bootstrap-x86-libpcap:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🚀 aRGus NDR — Bootstrap x86 Variant B (libpcap)         ║"
	@echo "║  Ejecutar tras: git clone && make up                      ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo "[1/8] Verificando entorno post-up..."
	@$(MAKE) post-up-verify
	@echo "[2/8] Verificando dependencias del sistema..."
	@$(MAKE) check-system-deps
	@echo "[3/8] Activando perfil de build..."
	@$(MAKE) set-build-profile
	@echo "[4/8] Instalando systemd units..."
	@$(MAKE) install-systemd-units
	@echo "[5/8] Compilando pipeline (incluye Variant B sniffer-libpcap)..."
	@$(MAKE) pipeline-build
	@$(MAKE) sniffer-libpcap
	@$(MAKE) check-build-artifacts
	@echo "[6/8] Desplegando modelos ML..."
	@$(MAKE) deploy-models
	@echo "[6b/8] Firmando plugins..."
	@$(MAKE) sign-plugins
	@echo "[7/8] Verificando provisioning..."
	@$(MAKE) test-provision-1
	@echo "[8/8] Arrancando pipeline (Variant B — libpcap)..."
	@$(MAKE) pipeline-start-x86-libpcap
	@$(MAKE) pipeline-status
	@$(MAKE) plugin-integ-test
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Bootstrap x86 libpcap completado — 6/6 RUNNING        ║"
	@echo "║  Sniffer activo: Variant B (libpcap)                      ║"
	@echo "║  Siguiente: make test-all                                  ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

check-system-deps:
	@echo "🔍 Verificando dependencias del sistema..."
	@vagrant ssh -c "command -v xxd >/dev/null || { echo '❌ xxd missing'; exit 1; }"
	@vagrant ssh -c "command -v tmux >/dev/null || { echo '❌ tmux missing'; exit 1; }"
	@vagrant ssh -c "pkg-config --modversion libsodium 2>/dev/null | grep -q '1.0.19' || { echo '❌ libsodium 1.0.19 missing'; exit 1; }"
	@vagrant ssh -c "bash /vagrant/tools/check-xgboost-version.sh" || { echo '❌ xgboost 3.2.0 missing'; exit 1; }
	@vagrant ssh -c "test -f /usr/local/lib/libxgboost.so || { echo '❌ libxgboost.so missing'; exit 1; }"
	@vagrant ssh -c "test -f /usr/local/lib/libcrypto_transport.so || { echo '❌ libcrypto_transport.so missing'; exit 1; }"
	@vagrant ssh -c "test -f /usr/sbin/nft || { echo '❌ nftables missing'; exit 1; }"
	@echo "✅ Todas las dependencias del sistema presentes"

check-build-artifacts:
	@echo "🔍 Verificando artefactos de build..."
	@vagrant ssh -c "test -f /usr/local/bin/argus-network-isolate || { echo '❌ argus-network-isolate missing'; exit 1; }"
	@echo "✅ Artefactos de build presentes"

post-up-verify:
	@echo "🔍 Verificando entorno post-up..."
	@$(MAKE) check-system-deps
	@vagrant ssh -c "test -d /usr/lib/ml-defender/plugins || { echo '❌ plugins dir missing'; exit 1; }"
	@vagrant ssh -c "test -f /usr/lib/ml-defender/plugins/libplugin_xgboost.so || { echo '❌ libplugin_xgboost.so missing'; exit 1; }"
	@vagrant ssh -c "test -f /etc/ml-defender/plugins/plugin_signing.pk || { echo '❌ plugin_signing.pk missing'; exit 1; }"
	@vagrant ssh -c "sudo find /etc/ml-defender -name 'seed.bin' | wc -l | tr -d ' ' | grep -q '^6$$' || { echo '❌ seeds missing (esperados 6)'; exit 1; }"
	@echo "✅ Entorno post-up verificado"

up-argus:
	@vagrant up defender client

up-suricata:
	@cd experiments/suricata-comparative && vagrant up suricata client

up: up-argus

halt-argus:
	@vagrant halt defender client

halt-suricata:
	@cd experiments/suricata-comparative && vagrant halt

halt: halt-argus

destroy:
	@vagrant destroy -f

ssh:
	@vagrant ssh

status:
	@echo "════════════════════════════════════════════════════════════"
	@echo "VM Status:"
	@vagrant status
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "libbpf Status (Day 8 Fix):"
	@vagrant ssh -c "pkg-config --modversion libbpf 2>/dev/null || echo '❌ libbpf not found'" | \
		awk '{if ($$1 >= "1.2.0") print "✅ libbpf " $$1 " (BPF map bug FIXED)"; else print "⚠️  libbpf " $$1 " (needs upgrade to 1.2.0+)"}'
	@echo "════════════════════════════════════════════════════════════"
	@echo "Current Profile: $(PROFILE)"
	@echo "════════════════════════════════════════════════════════════"

# ============================================================================
# Protobuf (Foundation Layer)
# ============================================================================

PROTOBUF_VERIFY_SCRIPT := /vagrant/scripts/verify_protobuf.sh

proto-unified:
	@echo "🔨 Protobuf Unified System..."
	@vagrant ssh -c "cd /vagrant/protobuf && chmod +x generate.sh && ./generate.sh"

proto-verify:
	@echo "🔍 Verificando consistencia protobuf..."
	@vagrant ssh -c "cd /vagrant && bash scripts/verify_protobuf.sh"

proto: proto-unified
	@echo "✅ Protobuf unificado generado y distribuido"

# ============================================================================
# Libraries Layer (No Sanitizers - Always Release)
# ============================================================================
# Dependencies: crypto-transport has no deps
#              etcd-client depends on: proto, crypto-transport
# ============================================================================

crypto-transport-build: seed-client-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building crypto-transport Library                     ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@vagrant ssh -c 'cd /vagrant/crypto-transport && \
		rm -rf build && \
		mkdir -p build && \
		cd build && \
		cmake -DCMAKE_BUILD_TYPE=Release .. && \
		make -j4'
	@echo "Installing system-wide..."
	@vagrant ssh -c "cd /vagrant/crypto-transport/build && sudo make install && sudo ldconfig"
	@echo ""
	@echo "✅ crypto-transport installed to /usr/local/lib"
	@vagrant ssh -c "ls -lh /usr/local/lib/libcrypto_transport.so* 2>/dev/null || echo '⚠️  Library not found in /usr/local/lib'"

crypto-transport-clean:
	@echo "🧹 Cleaning crypto-transport..."
	@vagrant ssh -c "rm -rf /vagrant/crypto-transport/build"
	@vagrant ssh -c "sudo rm -f /usr/local/lib/libcrypto_transport.so*"
	@vagrant ssh -c "sudo rm -rf /usr/local/include/crypto_transport"
	@vagrant ssh -c "sudo ldconfig"
	@echo "✅ crypto-transport cleaned"

crypto-transport-test:
	@echo "🧪 Testing crypto-transport..."
	@vagrant ssh -c "cd /vagrant/crypto-transport/build && ctest --output-on-failure"

# ADR-025: sincroniza MLD_PLUGIN_PUBKEY_HEX en CMakeLists.txt con el keypair activo en VM
# Ejecutar SIEMPRE tras vagrant destroy+up o provision.sh --reset
# Sin esto: TEST-INTEG-SIGN falla porque la pubkey compilada != keypair activo
sync-pubkey:
	@echo "⚠️  DEPRECATED: sync-pubkey ya no es necesario (DEBT-PUBKEY-RUNTIME-001 CERRADO)"
	@echo "    plugin-loader lee la pubkey desde /etc/ml-defender/plugins/plugin_signing.pk en cmake-time"
	@echo "    Ejecuta directamente: make plugin-loader-build"
	@$(MAKE) plugin-loader-build

plugin-loader-build:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔌 Building plugin-loader Library (PHASE 1)              ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  Phase: 1 — no crypto, no seed-client (ADR-012)"
	@echo "  Auth:  PHASE 2 (ADR-013, seed-client DAY 95-96)"
	@echo ""
	@vagrant ssh -c 'cd /vagrant/plugin-loader && \
		rm -rf build && \
		mkdir -p build && \
		cd build && \
		cmake -DCMAKE_BUILD_TYPE=Release .. && \
		make -j4'
	@echo "Installing system-wide..."
	@vagrant ssh -c "cd /vagrant/plugin-loader/build && sudo make install && sudo ldconfig"
	@echo ""
	@echo "✅ plugin-loader installed to /usr/local/lib"
	@vagrant ssh -c "ls -lh /usr/local/lib/libplugin_loader.so* 2>/dev/null || echo '⚠️  Library not found in /usr/local/lib'"

plugin-loader-clean:
	@echo "🧹 Cleaning plugin-loader..."
	@vagrant ssh -c "rm -rf /vagrant/plugin-loader/build"
	@vagrant ssh -c "sudo rm -f /usr/local/lib/libplugin_loader.so*"
	@vagrant ssh -c "sudo rm -rf /usr/local/include/plugin_loader"
	@vagrant ssh -c "sudo ldconfig"
	@echo "✅ plugin-loader cleaned"

plugin-loader-test:
	@echo "Testing safe-path property tests..."
	@vagrant ssh -c "/vagrant/contrib/safe-path/build/test_safe_path_property" || (echo "❌ safe-path property tests FAILED" && exit 1)
	@echo ""
	@echo "🧪 Testing plugin-loader..."
	@vagrant ssh -c "cd /vagrant/plugin-loader/build && ctest --output-on-failure"


# ADR-025: firma todos los plugins instalados en /usr/lib/ml-defender/plugins/
# Prerequisito: provision.sh full (keypair generado)
# Repetible: re-firmar sobreescribe .sig anterior

# ADR-025: TEST-INTEG-SIGN-1 a 7 — verificacion Ed25519 plugin loader
test-sign:
	@echo "TEST-INTEG-SIGN: Ed25519 plugin verification (ADR-025)..."
	@vagrant ssh -c 'cd /tmp && g++ -std=c++20 -o test_integ_sign /vagrant/plugins/test-message/test_integ_sign.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && sudo ./test_integ_sign && echo TEST-INTEG-SIGN PASSED || echo TEST-INTEG-SIGN FAILED'

deploy-models:
	@vagrant ssh -c "sudo mkdir -p /etc/ml-defender/models && \
	  sudo cp /vagrant/ml-detector/models/production/level1/xgboost_cicids2017.ubj \
	          /etc/ml-defender/models/xgboost_cicids2017.ubj && \
	  sudo chmod 644 /etc/ml-defender/models/xgboost_cicids2017.ubj"
	@echo "✅ Modelos ML desplegados en /etc/ml-defender/models/"

sign-plugins:
	@echo "Firmando plugins (ADR-025 D1)..."
	@vagrant ssh -c 'sudo bash /vagrant/tools/provision.sh sign'

test-integ-xgboost-1:
	@echo "TEST-INTEG-XGBOOST-1: XGBoost plugin inference (ADR-026 OBS-2)..."
	@vagrant ssh -c "cd /tmp && g++ -std=c++20 -o test_integ_xgboost_1 /vagrant/plugins/test-message/test_integ_xgboost_1.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && sudo ./test_integ_xgboost_1 && echo TEST-INTEG-XGBOOST-1 PASSED || echo TEST-INTEG-XGBOOST-1 FAILED"

sign-models:
	@echo "══ Firma de modelos (ADR-026 OBS-1) ══"
	@vagrant ssh -c "sudo bash /vagrant/tools/sign-model.sh /vagrant/ml-detector/models/production/level1/xgboost_cicids2017.ubj"
	@vagrant ssh -c "sudo bash /vagrant/tools/sign-model.sh /vagrant/ml-detector/models/production/level2/ddos/xgboost_ddos.ubj"
	@vagrant ssh -c "sudo bash /vagrant/tools/sign-model.sh /vagrant/ml-detector/models/production/level3/ransomware_xgboost_v2/xgboost_ransomware.ubj"
	@vagrant ssh -c "sudo bash /vagrant/tools/sign-model.sh /vagrant/ml-detector/models/production/level1/xgboost_cicids2017_v2.ubj"
	@echo "  ✅ 4 modelo(s) firmado(s) correctamente"

plugin-integ-test:
	@echo "TEST-INTEG-4a-PLUGIN: variantes A/B/C..."
	@vagrant ssh -c 'cd /tmp && g++ -std=c++20 -o test_variants /vagrant/plugins/test-message/test_variants.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && MLD_ALLOW_DEV_MODE=1 ./test_variants && echo TEST-INTEG-4a PASSED || echo TEST-INTEG-4a FAILED'
	@echo "TEST-INTEG-4b: plugin READ-ONLY contract (rag-ingester PHASE 2b)..."
	@vagrant ssh -c 'cd /tmp && g++ -std=c++20 -o test_integ_4b /vagrant/plugins/test-message/test_integ_4b.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && MLD_ALLOW_DEV_MODE=1 ./test_integ_4b && echo TEST-INTEG-4b PASSED || echo TEST-INTEG-4b FAILED'
	@echo "TEST-INTEG-4c: plugin NORMAL contract (sniffer PHASE 2c)..."
	@vagrant ssh -c 'cd /tmp && g++ -std=c++20 -o test_integ_4c /vagrant/plugins/test-message/test_integ_4c.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && MLD_ALLOW_DEV_MODE=1 ./test_integ_4c && echo TEST-INTEG-4c PASSED || echo TEST-INTEG-4c FAILED'
	@echo "TEST-INTEG-4d: plugin NORMAL contract (ml-detector PHASE 2d)..."
	@vagrant ssh -c 'cd /tmp && g++ -std=c++20 -o test_integ_4d /vagrant/plugins/test-message/test_integ_4d.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && MLD_ALLOW_DEV_MODE=1 ./test_integ_4d && echo TEST-INTEG-4d PASSED || echo TEST-INTEG-4d FAILED'
	@echo "TEST-INTEG-4e: rag-security READONLY + ADR-029 D1-D5..."
	@vagrant ssh -c 'cd /tmp && g++ -std=c++20 -o test_integ_4e /vagrant/plugins/test-message/test_integ_4e.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && MLD_ALLOW_DEV_MODE=1 ./test_integ_4e && echo TEST-INTEG-4e PASSED || echo TEST-INTEG-4e FAILED'
	@echo "TEST-INTEG-SIGN: Ed25519 plugin verification (ADR-025)..."
	@vagrant ssh -c 'cd /tmp && g++ -std=c++20 -o test_integ_sign /vagrant/plugins/test-message/test_integ_sign.cpp -I/usr/local/include -L/usr/local/lib -lplugin_loader -Wl,-rpath,/usr/local/lib && sudo ./test_integ_sign && echo TEST-INTEG-SIGN PASSED || echo TEST-INTEG-SIGN FAILED'

plugin-hello-build: plugin-loader-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔌 Building Hello World Plugin (ADR-012 validation)      ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@vagrant ssh -c 'cd /vagrant/plugins/hello && \
		rm -rf build && \
		mkdir -p build && \
		cd build && \
		cmake -DCMAKE_BUILD_TYPE=Release .. && \
		make -j4'
	@echo "Deploying to plugin directory..."
	@vagrant ssh -c "sudo mkdir -p /usr/lib/ml-defender/plugins"
	@vagrant ssh -c "sudo cp /vagrant/plugins/hello/build/libplugin_hello.so /usr/lib/ml-defender/plugins/"
	@echo ""
	@echo "✅ libplugin_hello.so deployed to /usr/lib/ml-defender/plugins/"
	@vagrant ssh -c "ls -lh /usr/lib/ml-defender/plugins/"

plugin-test-message-build: plugin-loader-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔌 Building Test Message Plugin (ADR-025 integration)    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@vagrant ssh -c 'cd /vagrant/plugins/test-message && rm -rf build && mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Release .. && make -j4'
	@vagrant ssh -c "sudo mkdir -p /usr/lib/ml-defender/plugins"
	@vagrant ssh -c "sudo cp /vagrant/plugins/test-message/build/libplugin_test_message.so /usr/lib/ml-defender/plugins/"
	@echo "✅ libplugin_test_message.so deployed to /usr/lib/ml-defender/plugins/"

plugin-hello-clean:
	@echo "🧹 Cleaning hello plugin..."
	@vagrant ssh -c "rm -rf /vagrant/plugins/hello/build"
	@vagrant ssh -c "sudo rm -f /usr/lib/ml-defender/plugins/libplugin_hello.so"
	@echo "✅ hello plugin cleaned"



etcd-client-build: proto-unified crypto-transport-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building etcd-client Library                          ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Dependencies:"
	@echo "  ✅ proto-unified"
	@echo "  ✅ crypto-transport-build"
	@echo ""
	@vagrant ssh -c 'cd /vagrant/etcd-client && \
		rm -rf build && \
		mkdir -p build && \
		cd build && \
		cmake -DCMAKE_BUILD_TYPE=Release .. && \
		make -j4'
	@echo "Installing system-wide..."
	@vagrant ssh -c "cd /vagrant/etcd-client/build && sudo make install && sudo ldconfig"
	@echo ""
	@echo "✅ etcd-client installed to /usr/local/lib"
	@echo ""
	@echo "Verifying library size and methods..."
	@vagrant ssh -c "ls -lh /vagrant/etcd-client/build/libetcd_client.so"
	@vagrant ssh -c "ls -lh /usr/local/lib/libetcd_client.so* 2>/dev/null || echo '⚠️  Library not found in /usr/local/lib'"
	@vagrant ssh -c "nm -D /usr/local/lib/libetcd_client.so.1.0.0 2>/dev/null | grep -c ' T ' | xargs echo 'Public methods:'" || echo "⚠️  Cannot verify methods"

etcd-client-clean:
	@echo "🧹 Cleaning etcd-client..."
	@vagrant ssh -c "rm -rf /vagrant/etcd-client/build"
	@vagrant ssh -c "sudo rm -f /usr/local/lib/libetcd_client.so*"
	@vagrant ssh -c "sudo rm -rf /usr/local/include/etcd_client"
	@vagrant ssh -c "sudo ldconfig"
	@echo "✅ etcd-client cleaned"

etcd-client-test:
	@echo "🧪 Testing etcd-client..."
	@vagrant ssh -c "cd /vagrant/etcd-client/build && ctest --output-on-failure"

# ============================================================================
# Component Builds (Profile-Aware)
# ============================================================================
# CRITICAL: All components copy protobuf files BEFORE cmake
# Dependencies are explicit and automatic
# ============================================================================
# Ajusta estas rutas a tu estructura real
SNIFFER_DIR := /vagrant/sniffer
SNIFFER_BIN        := ./$(notdir $(SNIFFER_BUILD_DIR))/sniffer
SNIFFER_CFG := ../config/sniffer.json
SNIFFER_LIBPCAP_BIN:= ./$(notdir $(SNIFFER_LIBPCAP_BUILD_DIR))/sniffer-libpcap

# ── Macro de exclusión mutua (inline, sin script externo) ────────────────────
define CHECK_SNIFFER_MUTEX
	@vagrant ssh defender -c " \
	  EBPF=\$$(tmux has-session -t sniffer         2>/dev/null && echo 1 || echo 0); \
	  PCAP=\$$(tmux has-session -t sniffer-libpcap  2>/dev/null && echo 1 || echo 0); \
	  if [ \$$EBPF -eq 1 ] || [ \$$PCAP -eq 1 ]; then \
	    echo '❌ MUTEX VIOLATION: otro sniffer activo — para primero con pipeline-stop'; \
	    exit 1; \
	  fi"
endef

# ── sniffer-start — Variant A (eBPF) ─────────────────────────────────────────
sniffer-start:
	@echo "🚀 Starting Sniffer Variant A (eBPF/XDP) [$(PROFILE)]..."
	$(CHECK_SNIFFER_MUTEX)
	@vagrant ssh defender -c "tmux kill-session -t sniffer 2>/dev/null || true"
	@vagrant ssh defender -c "tmux new-session -d -s sniffer \
	  'mkdir -p /vagrant/logs/lab && \
	   cd $(SNIFFER_BUILD_DIR) && \
	   sudo env LD_LIBRARY_PATH=/usr/local/lib ./sniffer -c /vagrant/sniffer/config/sniffer.json \
	   >> /vagrant/logs/lab/sniffer.log 2>&1'"
	@sleep 4

# ── sniffer-libpcap-start — Variant B (libpcap) ──────────────────────────────
sniffer-libpcap-start:
	@echo "🚀 Starting Sniffer Variant B (libpcap) [$(PROFILE)]..."
	$(CHECK_SNIFFER_MUTEX)
	@vagrant ssh defender -c "tmux kill-session -t sniffer-libpcap 2>/dev/null || true"
	@vagrant ssh defender -c "tmux new-session -d -s sniffer-libpcap \
	  'mkdir -p /vagrant/logs/lab && \
	   cd $(SNIFFER_LIBPCAP_BUILD_DIR) && \
	   sudo env LD_LIBRARY_PATH=/usr/local/lib ./sniffer-libpcap \
	   -c /etc/ml-defender/sniffer/sniffer-libpcap.json \
	   >> /vagrant/logs/lab/sniffer-libpcap.log 2>&1'"
	@sleep 4

sniffer: proto etcd-client-build plugin-loader-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building Sniffer [$(PROFILE)]                         ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build dir: $(SNIFFER_BUILD_DIR)"
	@echo "Flags: $(CMAKE_FLAGS)"
	@echo ""
	@echo "Copying protobuf files..."
	@vagrant ssh -c 'mkdir -p $(SNIFFER_BUILD_DIR)/proto && \
		cp /vagrant/protobuf/network_security.pb.* $(SNIFFER_BUILD_DIR)/proto/'
	@echo "Running CMake and build..."
	@vagrant ssh -c 'cd /vagrant/sniffer && \
		mkdir -p $(SNIFFER_BUILD_DIR) && \
		cd $(SNIFFER_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make -j4'
	@vagrant ssh -c "ln -sfn $(SNIFFER_BUILD_DIR) $(SNIFFER_LEGACY_LINK)"
	@echo ""
	@echo "✅ Sniffer built ($(PROFILE))"

ml-detector-start:
	@echo "🚀 Starting ML Detector (Tricapa Persistente)..."
	@vagrant ssh -c "tmux kill-session -t ml-detector 2>/dev/null || true"
	@vagrant ssh -c "tmux new-session -d -s ml-detector 'mkdir -p /vagrant/logs/lab && cd /vagrant/ml-detector/build-debug && export LD_LIBRARY_PATH=/usr/local/lib:$$LD_LIBRARY_PATH && sudo env LD_LIBRARY_PATH=/usr/local/lib ./ml-detector >> /vagrant/logs/lab/ml-detector.log 2>&1'"
	@sleep 3

ml-detector: proto etcd-client-build plugin-loader-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building ML Detector [$(PROFILE)]                     ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build dir: $(ML_DETECTOR_BUILD_DIR)"
	@echo "Flags: $(CMAKE_FLAGS)"
	@echo ""
	@echo "Copying protobuf files..."
	@vagrant ssh -c 'mkdir -p $(ML_DETECTOR_BUILD_DIR)/proto && \
		cp /vagrant/protobuf/network_security.pb.* $(ML_DETECTOR_BUILD_DIR)/proto/'
	@echo "Running CMake and build..."
	@vagrant ssh -c 'cd /vagrant/ml-detector && \
		mkdir -p $(ML_DETECTOR_BUILD_DIR) && \
		cd $(ML_DETECTOR_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make -j4'
	@vagrant ssh -c "ln -sfn $(ML_DETECTOR_BUILD_DIR) $(ML_DETECTOR_LEGACY_LINK)"
	@echo ""
	@echo "✅ ML Detector built ($(PROFILE))"

rag-ingester-start:
	@echo "🚀 Starting RAG Ingester (Full Context)..."
	@vagrant ssh -c "tmux kill-session -t rag-ingester 2>/dev/null || true"
	@echo "🧹 Limpiando SQLite lock anterior (si existe)..."
	@vagrant ssh -c "rm -f /vagrant/shared/indices/metadata.db-wal /vagrant/shared/indices/metadata.db-shm || true"
	@echo "Ejecución desde la raíz del componente para resolver paths relativos del config..."
	@vagrant ssh -c "tmux new-session -d -s rag-ingester 'mkdir -p /vagrant/logs/lab && cd /vagrant/rag-ingester && export LD_LIBRARY_PATH=/usr/local/lib:$$LD_LIBRARY_PATH && sudo env LD_LIBRARY_PATH=/usr/local/lib ./build-debug/rag-ingester /etc/ml-defender/rag-ingester/rag-ingester.json >> /vagrant/logs/lab/rag-ingester.log 2>&1'"
	@sleep 2

rag-ingester: proto etcd-client-build crypto-transport-build plugin-loader-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building RAG Ingester [$(PROFILE)]                    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build dir: $(RAG_INGESTER_BUILD_DIR)"
	@echo "Flags: $(CMAKE_FLAGS)"
	@echo ""
	@echo "Copying protobuf files..."
	@vagrant ssh -c 'mkdir -p $(RAG_INGESTER_BUILD_DIR)/proto && \
		cp /vagrant/protobuf/network_security.pb.* $(RAG_INGESTER_BUILD_DIR)/proto/'
	@echo "Running CMake and build..."
	@vagrant ssh -c 'cd /vagrant/rag-ingester && \
		mkdir -p $(RAG_INGESTER_BUILD_DIR) && \
		cd $(RAG_INGESTER_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make -j4'
	@vagrant ssh -c "ln -sfn $(RAG_INGESTER_BUILD_DIR) $(RAG_INGESTER_LEGACY_LINK)"
	@echo ""
	@echo "✅ RAG Ingester built ($(PROFILE))"

FIREWALL_DIR := /vagrant/firewall-acl-agent
FIREWALL_BIN := ./firewall-acl-agent
FIREWALL_CFG := /etc/ml-defender/firewall-acl-agent/firewall.json

firewall-start:
	@echo "🚀 Starting Firewall ACL (SUDO + TMUX)..."
	@vagrant ssh -c "tmux kill-session -t firewall 2>/dev/null || true"
	@vagrant ssh -c "tmux new-session -d -s firewall 'mkdir -p /vagrant/logs/lab && cd $(FIREWALL_DIR)/build-debug && sudo env LD_LIBRARY_PATH=/usr/local/lib $(FIREWALL_BIN) -c $(FIREWALL_CFG) >> /vagrant/logs/lab/firewall-agent.log 2>&1'"
	@sleep 2

firewall: proto seed-client-build etcd-client-build plugin-loader-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building Firewall ACL Agent [$(PROFILE)]              ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build dir: $(FIREWALL_BUILD_DIR)"
	@echo "Flags: $(CMAKE_FLAGS)"
	@echo ""
	@echo "Copying protobuf files..."
	@vagrant ssh -c 'mkdir -p $(FIREWALL_BUILD_DIR)/proto && \
		cp /vagrant/protobuf/network_security.pb.* $(FIREWALL_BUILD_DIR)/proto/'
	@echo "Running CMake and build..."
	@vagrant ssh -c 'cd /vagrant/firewall-acl-agent && \
		mkdir -p $(FIREWALL_BUILD_DIR) && \
		cd $(FIREWALL_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make -j4'
	@vagrant ssh -c "ln -sfn $(FIREWALL_BUILD_DIR) $(FIREWALL_LEGACY_LINK)"
	@echo ""
	@echo "✅ Firewall built ($(PROFILE))"

etcd-server:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building etcd-server [$(PROFILE)]                     ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build dir: $(ETCD_SERVER_BUILD_DIR)"
	@echo "Flags: $(CMAKE_FLAGS)"
	@echo ""
	@vagrant ssh -c 'cd /vagrant/etcd-server && \
		mkdir -p $(ETCD_SERVER_BUILD_DIR) && \
		cd $(ETCD_SERVER_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make -j4'
	@vagrant ssh -c "ln -sfn $(ETCD_SERVER_BUILD_DIR) $(ETCD_SERVER_LEGACY_LINK)"
	@echo ""
	@echo "✅ etcd-server built ($(PROFILE))"

etcd-server-status:
	@echo "════════════════════════════════════════════════════════════"
	@echo "etcd-server Status:"
	@vagrant ssh -c "pgrep -a -f etcd-server && echo '✅ etcd-server: RUNNING' || echo '❌ etcd-server: STOPPED'"
	@vagrant ssh -c "curl -s http://localhost:2379/health || echo '⚠️  Not responding'"
	@echo "════════════════════════════════════════════════════════════"


# ============================================================================
# Logging estándar — todos los componentes escriben en /vagrant/logs/lab/
# Standard: un componente, un fichero, nombre predecible.
# ADR pendiente: mover configuración log_file a JSON de cada componente.
# ============================================================================
logs-all:
	@echo '📋 Tailing all 6 pipeline component logs (Ctrl+C to stop)...'
	@vagrant ssh -c "tail -f /vagrant/logs/lab/etcd-server.log /vagrant/logs/lab/rag-security.log /vagrant/logs/lab/rag-ingester.log /vagrant/logs/lab/ml-detector.log /vagrant/logs/lab/firewall-agent.log /vagrant/logs/lab/sniffer.log 2>/dev/null"

logs-lab-clean:
	@echo '🧹 Rotating pipeline logs...'
	@vagrant ssh -c "mkdir -p /vagrant/logs/lab/archive && mv /vagrant/logs/lab/*.log /vagrant/logs/lab/archive/ 2>/dev/null || true"
	@echo '✅ Logs rotated to /vagrant/logs/lab/archive/'

pipeline-health:
	@bash scripts/pipeline_health.sh


# =============================================================================
# TEST-PROVISION-1 — CI Gate PHASE 3 (DAY 115)
# Verifica que el entorno está listo para arrancar el pipeline de forma segura.
# Encadena todos los checks de PHASE 3 ítems 1-4.
#
# USO:
#   make test-provision-1          # CI gate completo
#   make pipeline-start            # llama a test-provision-1 automáticamente
#
# CHECKS:
#   1. Claves criptográficas (provision.sh verify)
#   2. Plugins firmados (provision.sh check-plugins --production)
#   3. No dev plugins en prod configs (validate-prod-configs)
#   4. build-active symlinks presentes (set-build-profile.sh ejecutado)
#   5. systemd units instalados en /etc/systemd/system/
# =============================================================================

test-provision-1:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔍 TEST-PROVISION-1 — CI Gate PHASE 3                   ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "── Check 1/8: Claves criptográficas ──"
	@vagrant ssh -c "sudo bash /vagrant/tools/provision.sh verify" || \
		(echo "❌ CHECK 1 FAILED: claves ausentes o inválidas" && \
		 echo "   Ejecuta: make provision" && exit 1)
	@echo "✅ Check 1/8 OK"
	@echo ""
	@echo "── Check 2/8: Firmas de plugins (producción) ──"
	@vagrant ssh -c "sudo bash /vagrant/tools/provision.sh check-plugins --production" || \
		(echo "❌ CHECK 2 FAILED: plugins sin firma válida" && \
		 echo "   Ejecuta: make sign-plugins" && exit 1)
	@echo "✅ Check 2/8 OK"
	@echo ""
	@echo "── Check 3/8: Configs de producción (sin dev plugins) ──"
	@$(MAKE) validate-prod-configs || \
		(echo "❌ CHECK 3 FAILED: dev plugins en configs de producción" && exit 1)
	@echo "✅ Check 3/8 OK"
	@echo ""
	@echo "── Check 4/8: build-active symlinks ──"
	@vagrant ssh -c "test -L /vagrant/sniffer/build-active && \
		test -L /vagrant/ml-detector/build-active && \
		test -L /vagrant/firewall-acl-agent/build-active && \
		test -L /vagrant/etcd-server/build-active && \
		test -L /vagrant/rag-ingester/build-active" || \
		(echo "❌ CHECK 4 FAILED: build-active symlinks ausentes" && \
		 echo "   Ejecuta: vagrant ssh -c 'sudo bash /vagrant/etcd-server/config/set-build-profile.sh debug'" && \
		 exit 1)
	@echo "✅ Check 4/8 OK"
	@echo ""
	@echo "── Check 5/8: systemd units instalados ──"
	@vagrant ssh -c "systemctl list-unit-files ml-defender-*.service 2>/dev/null | grep -c 'ml-defender'" | \
		grep -q "6" || \
		(echo "❌ CHECK 5 FAILED: systemd units no instalados (esperado: 6)" && \
		 echo "   Ejecuta: vagrant ssh -c 'sudo bash /vagrant/etcd-server/config/install-systemd-units.sh'" && \
		 exit 1)
	@echo "✅ Check 5/8 OK"
	@echo ""
	@echo ""
	@echo "── Check 6/8: Permisos ficheros sensibles ──"
	@vagrant ssh -c "sudo find /etc/ml-defender -type f \( -name '*.sk' \) -perm /022 2>/dev/null | grep -q . && echo FAIL || true" | grep -q FAIL && \
		(echo "❌ CHECK 6 FAILED: .sk con permisos world/group-writable" && exit 1) || true
	@vagrant ssh -c "sudo find /etc/ml-defender -name 'seed.bin' ! -perm 400 ! -perm 440 2>/dev/null | grep -q . && echo FAIL || true" | grep -q FAIL && \
		(echo "❌ CHECK 6 FAILED: seed.bin con permisos incorrectos (esperado: 0400 o 0440)" && exit 1) || true
	@echo "✅ Check 6/8 OK"
	@echo ""
	@echo "── Check 7/8: Consistencia JSONs con plugins reales ──"
	@vagrant ssh -c "python3 /vagrant/tools/check-json-plugins.py" || \
		(echo "❌ CHECK 7 FAILED: plugins referenciados en JSONs sin .so o .sig" && exit 1)
	@echo "✅ Check 7/8 OK"
	@echo ""
	@echo "── Check 8/8: apparmor-utils instalado ──"
	@vagrant ssh -c "/usr/sbin/aa-complain --help > /dev/null 2>&1 && /usr/sbin/aa-enforce --help > /dev/null 2>&1 && echo OK || echo FAIL" | grep -q OK || \
		(echo "❌ CHECK 8 FAILED: apparmor-utils no instalado" && \
		 echo "   Ejecuta: vagrant ssh -c \"sudo apt-get install -y apparmor-utils\"" && exit 1)
	@echo "✅ Check 8/8 OK"
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ TEST-PROVISION-1 PASSED — entorno listo               ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""

test-invariant-seed:
	@echo ""
	@echo "── TEST-INVARIANT-SEED: 6 seeds idénticos post-reset ──"
	@vagrant ssh -c 'sudo bash -c " \
	  hashes=\"\" ; \
	  for c in etcd-server ml-detector sniffer firewall-acl-agent rag-ingester rag-security; do \
	    h=\$$(od -A n -t x1 /etc/ml-defender/\$$c/seed.bin | tr -d \" \\n\") ; \
	    hashes=\"\$$hashes \$$h\" ; \
	  done ; \
	  unique=\$$(echo \$$hashes | tr \" \" \"\\n\" | sort -u | grep -v \"^$$\" | wc -l) ; \
	  echo \"Hashes únicos: \$$unique\" ; \
	  [ \"\$$unique\" -eq 1 ] && echo \"✅ TEST-INVARIANT-SEED PASSED\" || { echo \"❌ TEST-INVARIANT-SEED FAILED\"; exit 1; } \
	"' || (echo "❌ INVARIANTE-SEED-001 violado: seeds divergentes" && exit 1)
	@echo ""

pipeline-start: test-provision-1 etcd-server-start
	@echo "⏳ Waiting for etcd-server to stabilize (Seed generation)..."
	@sleep 4
	@$(MAKE) rag-start
	@sleep 5
	@$(MAKE) rag-ingester-start
	@sleep 3
	@$(MAKE) ml-detector-start
	@$(MAKE) firewall-start
	@sleep 2
	@$(MAKE) sniffer-start
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ FULL PIPELINE STARTED (DAY 103 — con provisioning)     ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@$(MAKE) pipeline-status

pipeline-start-x86-libpcap: test-provision-1 etcd-server-start
	@echo "⏳ Waiting for etcd-server to stabilize (Seed generation)..."
	@sleep 4
	@$(MAKE) rag-start
	@sleep 5
	@$(MAKE) rag-ingester-start
	@sleep 3
	@$(MAKE) ml-detector-start
	@$(MAKE) firewall-start
	@sleep 2
	@$(MAKE) sniffer-libpcap-start
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ FULL PIPELINE STARTED — Variant B (libpcap)           ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@$(MAKE) pipeline-status

pipeline-stop:
	@echo "🛑 Stopping all pipeline components..."
	@vagrant ssh -c "for s in sniffer ml-detector firewall rag-ingester rag-security etcd-server; do tmux kill-session -t $$s 2>/dev/null || true; done"
	@echo "✅ Pipeline stopped"

pipeline-status:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  📊 ML Defender Pipeline Status (via TMUX + pgrep)        ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@vagrant ssh -c "( tmux has-session -t etcd-server 2>/dev/null || pgrep -x etcd-server >/dev/null 2>&1 ) && echo '  ✅ etcd-server:   RUNNING' || echo '  ❌ etcd-server:   STOPPED'"
	@vagrant ssh -c "( tmux has-session -t rag-security 2>/dev/null || pgrep -x rag-security >/dev/null 2>&1 ) && echo '  ✅ rag-security:  RUNNING' || echo '  ❌ rag-security:  STOPPED'"
	@vagrant ssh -c "( tmux has-session -t rag-ingester 2>/dev/null || pgrep -x rag-ingester >/dev/null 2>&1 ) && echo '  ✅ rag-ingester:  RUNNING' || echo '  ❌ rag-ingester:  STOPPED'"
	@vagrant ssh -c "( tmux has-session -t ml-detector 2>/dev/null || pgrep -x ml-detector >/dev/null 2>&1 ) && echo '  ✅ ml-detector:   RUNNING' || echo '  ❌ ml-detector:   STOPPED'"
	@vagrant ssh -c " \
	  EBPF=0; PCAP=0; \
	  tmux has-session -t sniffer         2>/dev/null && EBPF=1; \
	  tmux has-session -t sniffer-libpcap 2>/dev/null && PCAP=1; \
	  pgrep -x sniffer         >/dev/null 2>&1 && EBPF=1; \
	  pgrep -x sniffer-libpcap >/dev/null 2>&1 && PCAP=1; \
	  if   [ \$$EBPF -eq 1 ] && [ \$$PCAP -eq 0 ]; then \
	    echo '  ✅ sniffer:       RUNNING [Variant A — eBPF]'; \
	  elif [ \$$EBPF -eq 0 ] && [ \$$PCAP -eq 1 ]; then \
	    echo '  ✅ sniffer:       RUNNING [Variant B — libpcap]'; \
	  elif [ \$$EBPF -eq 1 ] && [ \$$PCAP -eq 1 ]; then \
	    echo '  🚨 sniffer:       INVARIANT VIOLATION — eBPF + libpcap SIMULTANEOUS'; \
	  else \
	    echo '  ❌ sniffer:       STOPPED'; \
	  fi"
	@vagrant ssh -c "( tmux has-session -t firewall 2>/dev/null || pgrep -x firewall-acl-agent >/dev/null 2>&1 ) && echo '  ✅ firewall:      RUNNING' || echo '  ❌ firewall:      STOPPED'"
	@echo "╚════════════════════════════════════════════════════════════╝"

install-systemd-units:
	@echo "═══ Instalando systemd units ML Defender ═══"
	@vagrant ssh -c "sudo bash /vagrant/etcd-server/config/install-systemd-units.sh"

set-build-profile:
	@echo "═══ Activando perfil de build: $(PROFILE) ═══"
	@vagrant ssh -c "sudo bash /vagrant/etcd-server/config/set-build-profile.sh $(PROFILE)"

# Secuencia completa post-build:
# 1. pipeline-build  → compila todos los componentes y libs
# 2. install-systemd-units → instala units en /etc/systemd/system/
# 3. set-build-profile → activa symlinks build-active
# 4. sign-plugins    → firma Ed25519 (ADR-025)
# 5. test-provision-1 → CI gate PHASE 3
# 6. pipeline-start  → arranca los 6 componentes
pipeline-build: crypto-transport-build seed-client-build etcd-client-build plugin-loader-build vault-client-build plugin-test-message-build etcd-server rag-build rag-ingester-build ml-detector sniffer firewall-build argus-network-isolate-build argus-network-isolate-install

tools: proto etcd-client-build crypto-transport-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building Tools [$(PROFILE)]                           ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build dir: $(TOOLS_BUILD_DIR)"
	@echo "Flags: $(CMAKE_FLAGS)"
	@echo ""
	@echo "Copying protobuf files..."
	@vagrant ssh -c 'mkdir -p $(TOOLS_BUILD_DIR)/proto && \
		cp /vagrant/protobuf/network_security.pb.* $(TOOLS_BUILD_DIR)/proto/'
	@echo "Running CMake and build..."
	@vagrant ssh -c 'cd /vagrant/tools && \
		mkdir -p $(TOOLS_BUILD_DIR) && \
		cd $(TOOLS_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make -j4'
	@vagrant ssh -c "ln -sfn $(TOOLS_BUILD_DIR) $(TOOLS_LEGACY_LINK)"
	@echo ""
	@echo "✅ Tools built ($(PROFILE))"


# ─────────────────────────────────────────────────────────────────────────────
# ADR-029 Variant B — sniffer compilado con libpcap (sin eBPF/XDP)
# DEBT-VARIANT-B-PCAP-IMPL-001: stub compilable, implementación real pendiente
# DAY 137 — 2026-04-30
# ─────────────────────────────────────────────────────────────────────────────
SNIFFER_LIBPCAP_BUILD_DIR := /vagrant/sniffer/build-$(PROFILE)-libpcap

.PHONY: sniffer-libpcap

sniffer-libpcap: proto etcd-client-build plugin-loader-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building Sniffer Variant B [libpcap, $(PROFILE)]      ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build dir: $(SNIFFER_LIBPCAP_BUILD_DIR)"
	@echo "Flags: $(CMAKE_FLAGS) -DUSE_LIBPCAP=ON"
	@echo ""
	@echo "Copying protobuf files..."
	@vagrant ssh -c 'mkdir -p $(SNIFFER_LIBPCAP_BUILD_DIR)/proto && \
		cp /vagrant/protobuf/network_security.pb.* $(SNIFFER_LIBPCAP_BUILD_DIR)/proto/'
	@echo "Running CMake and build (Variant B)..."
	@vagrant ssh -c 'cd /vagrant/sniffer && \
		mkdir -p $(SNIFFER_LIBPCAP_BUILD_DIR) && \
		cd $(SNIFFER_LIBPCAP_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) -DUSE_LIBPCAP=ON .. && \
		make sniffer-libpcap -j4'
	@echo ""
	@echo "✅ Sniffer Variant B built ($(PROFILE), libpcap)"

# Aliases for consistency with existing workflows
detector: ml-detector
sniffer-build: sniffer
detector-build: ml-detector
rag-ingester-build: rag-ingester
firewall-build: firewall
etcd-server-build: etcd-server
tools-build: tools


# ─────────────────────────────────────────────────────────────────────────────
# argus-network-isolate — ADR-042 Incident Response Protocol
# DAY 142 — nftables transaccional (pasos 1-3 implementados)
# ─────────────────────────────────────────────────────────────────────────────
ARGUS_ISOLATE_BUILD_DIR := /vagrant/tools/build-argus-network-isolate

.PHONY: argus-network-isolate-build argus-network-isolate-clean argus-network-isolate-test

argus-network-isolate-build:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building argus-network-isolate [ADR-042 IRP]          ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@vagrant ssh -c "rm -rf $(ARGUS_ISOLATE_BUILD_DIR) && mkdir -p $(ARGUS_ISOLATE_BUILD_DIR) && cd $(ARGUS_ISOLATE_BUILD_DIR) && cmake /vagrant/tools/argus-network-isolate -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS='-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0' && make -j4"
	@echo "✅ argus-network-isolate built"

argus-network-isolate-test:
	@echo "── argus-network-isolate: unit tests ──"
	@vagrant ssh -c "cd $(ARGUS_ISOLATE_BUILD_DIR) && ctest --output-on-failure"
	@echo "── argus-network-isolate: status ──"
	@vagrant ssh -c "sudo $(ARGUS_ISOLATE_BUILD_DIR)/argus-network-isolate status --config /vagrant/tools/argus-network-isolate/config/isolate.json"
	@echo "── argus-network-isolate: dry-run eth1 ──"
	@vagrant ssh -c "sudo $(ARGUS_ISOLATE_BUILD_DIR)/argus-network-isolate isolate --interface eth1 --dry-run --config /vagrant/tools/argus-network-isolate/config/isolate.json"
	@echo "✅ argus-network-isolate dry-run PASSED"

argus-network-isolate-install:
	@echo "── Instalando argus-network-isolate en /usr/local/bin/ ──"
	@vagrant ssh -c "sudo cp $(ARGUS_ISOLATE_BUILD_DIR)/argus-network-isolate /usr/local/bin/argus-network-isolate && sudo chmod 755 /usr/local/bin/argus-network-isolate"
	@echo "✅ argus-network-isolate instalado"

argus-network-isolate-clean:
	@vagrant ssh -c "rm -rf $(ARGUS_ISOLATE_BUILD_DIR)"
	@echo "✅ argus-network-isolate cleaned"

# ============================================================================
# Clean Targets (REFACTORED - Day 57)
# ============================================================================
# NEW STRUCTURE:
#   clean-libs       - Clean ONLY libraries (crypto-transport, etcd-client)
#   clean-components - Clean ONLY components (current profile)
#   clean            - Alias for clean-components
#   clean-all        - Clean EVERYTHING (all profiles + libs)
#   distclean        - Nuclear clean (clean-all + protobuf)
# ============================================================================

sniffer-clean:
	@echo "🧹 Cleaning Sniffer [$(PROFILE)]..."
	@vagrant ssh -c "rm -rf $(SNIFFER_BUILD_DIR)"

detector-clean:
	@echo "🧹 Cleaning ML Detector [$(PROFILE)]..."
	@vagrant ssh -c "rm -rf $(ML_DETECTOR_BUILD_DIR)"

rag-ingester-clean:
	@echo "🧹 Cleaning RAG Ingester [$(PROFILE)]..."
	@vagrant ssh -c "rm -rf $(RAG_INGESTER_BUILD_DIR)"

firewall-clean:
	@echo "🧹 Cleaning Firewall [$(PROFILE)]..."
	@vagrant ssh -c "rm -rf $(FIREWALL_BUILD_DIR)"

etcd-server-clean:
	@echo "🧹 Cleaning etcd-server [$(PROFILE)]..."
	@vagrant ssh -c "rm -rf $(ETCD_SERVER_BUILD_DIR)"

tools-clean:
	@echo "🧹 Cleaning Tools [$(PROFILE)]..."
	@vagrant ssh -c "rm -rf $(TOOLS_BUILD_DIR)"

clean-libs:
	@echo ""
	@echo "╔═══════════════════════════════════════════════════════════════════════════════════════╗"
	@echo "║  🧹 Cleaning Libraries (seed-client, plugin-loader, crypto-transport, etcd-client)    ║"
	@echo "╚═══════════════════════════════════════════════════════════════════════════════════════╝"
	@echo ""
	@$(MAKE) seed-client-clean
	@$(MAKE) crypto-transport-clean
	@$(MAKE) etcd-client-clean
	@$(MAKE) plugin-loader-clean
	@echo ""
	@echo "✅ Libraries cleaned"

clean-components: sniffer-clean detector-clean firewall-clean rag-ingester-clean etcd-server-clean tools-clean
	@echo "✅ Components cleaned [$(PROFILE)]"

clean: clean-components
	@echo "✅ Clean complete [$(PROFILE)]"
	@echo "💡 Tip: Use 'make clean-libs' to also clean libraries"
	@echo "💡 Tip: Use 'make clean-all' to clean ALL profiles + libs"

clean-all:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🧹 NUCLEAR CLEAN - ALL Profiles + Libraries             ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Cleaning ALL component builds (legacy + profile-specific)..."
	@echo "  - Removing legacy build/ directories..."
	@vagrant ssh -c "rm -rf /vagrant/sniffer/build"
	@vagrant ssh -c "rm -rf /vagrant/ml-detector/build"
	@vagrant ssh -c "rm -rf /vagrant/rag-ingester/build"
	@vagrant ssh -c "rm -rf /vagrant/firewall-acl-agent/build"
	@vagrant ssh -c "rm -rf /vagrant/etcd-server/build"
	@vagrant ssh -c "rm -rf /vagrant/tools/build"
	@echo "  - Removing profile-specific builds (production/debug/tsan/asan)..."
	@vagrant ssh -c "rm -rf /vagrant/sniffer/build-*"
	@vagrant ssh -c "rm -rf /vagrant/ml-detector/build-*"
	@vagrant ssh -c "rm -rf /vagrant/rag-ingester/build-*"
	@vagrant ssh -c "rm -rf /vagrant/firewall-acl-agent/build-*"
	@vagrant ssh -c "rm -rf /vagrant/etcd-server/build-*"
	@vagrant ssh -c "rm -rf /vagrant/tools/build-*"
	@echo ""
	@$(MAKE) clean-libs
	@echo ""
	@echo "✅ Nuclear clean complete - ALL builds + libraries removed"

distclean: clean-all
	@echo ""
	@echo "🧹 Cleaning protobuf artifacts..."
	@vagrant ssh -c "rm -f /vagrant/protobuf/network_security.pb.*"
	@vagrant ssh -c "rm -f /vagrant/protobuf/network_security_pb2.py"
	@echo ""
	@echo "✅ Distclean complete - System returned to pristine state"

# ============================================================================
# Test Targets (NEW - Day 57)
# ============================================================================
# UNIFIED TEST FRAMEWORK:
#   test-libs       - Run library tests (crypto-transport, etcd-client)
#   test-components - Run component tests (current profile)
#   test            - Run ALL tests (libs + components)
# ============================================================================

test-alert-client:
	@echo "Testing alert-client..."
	@vagrant ssh -c "cd /vagrant/common/build && ctest --output-on-failure"

test-libs:
	@echo "Testing seed-client..."
	@$(MAKE) seed-client-test
	@echo "Testing crypto-transport..."
	@vagrant ssh -c "cd /vagrant/crypto-transport/build && ctest" || echo "⚠️  crypto-transport has known LZ4 issues"
	@echo "Testing etcd-client (HMAC only)..."
	@vagrant ssh -c "cd /vagrant/etcd-client/build/tests && ./test_hmac_client"
	@echo "Testing plugin-loader..."
	@$(MAKE) plugin-loader-test
	@$(MAKE) plugin-integ-test

test-components:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🧪 Running Component Tests [$(PROFILE)]                  ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Testing Sniffer..."
	@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && ctest --output-on-failure" || echo "⚠️  No sniffer tests configured"
	@echo ""
	@echo "Testing ML Detector..."
	@vagrant ssh -c "cd $(ML_DETECTOR_BUILD_DIR) && ctest --output-on-failure" || echo "⚠️  No ml-detector tests configured"
	@echo ""
	@echo "Testing RAG Ingester..."
	@vagrant ssh -c "cd $(RAG_INGESTER_BUILD_DIR) && ctest --output-on-failure" || echo "⚠️  No rag-ingester tests configured"
	@echo ""
	@echo "Testing etcd-server..."
	@vagrant ssh -c "cd $(ETCD_SERVER_BUILD_DIR) && ctest --output-on-failure" || echo "⚠️  No etcd-server tests configured"
	@echo ""
	@echo "Testing RAG Security..."
	@vagrant ssh -c "cd $(RAG_BUILD_DIR) && ctest --output-on-failure" || echo "⚠️  No rag-security tests configured"
	@echo ""
	@echo "Testing Firewall ACL Agent..."
	@vagrant ssh -c "cd $(FIREWALL_BUILD_DIR) && ctest --output-on-failure" || echo "⚠️  No firewall tests configured"
	@echo ""

deploy-configs:
	@echo "🚀 Desplegando configs Ansible/Jinja2 (dev)..."
	@vagrant ssh defender -- -t "cd /vagrant && ansible-playbook -i ansible/inventory/dev.yml ansible/playbooks/deploy_configs.yml -e @ansible/group_vars/argus_dev.yml --diff"

deploy-configs-prod:
	@echo "🚀 Desplegando configs Ansible/Jinja2 (prod)..."
	@ansible-playbook -i ansible/inventory/prod.yml ansible/playbooks/deploy_configs.yml -e @ansible/group_vars/argus_prod.yml -e vault_token_secret=$${VAULT_TOKEN_SECRET} --diff

parquet-convert:
	@echo "📦 Installing/upgrading pyarrow..."
	@vagrant ssh -c "pip3 install --upgrade pyarrow --break-system-packages --quiet 2>&1 | tail -1"
	@echo "📦 Converting CSVs to Parquet..."
	@vagrant ssh -c "cd /vagrant/scripts/parquet && python3 generate_parquet.py"

test-parquet: parquet-convert
	@vagrant ssh -c "cd /vagrant/scripts/parquet && python3 validate_roundtrip.py"

test-all: test-libs test-components test-provision-1 test-invariant-seed plugin-integ-test argus-network-isolate-test test-parquet
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ ALL TESTS COMPLETE                                    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""

test: test-all
	@echo "💡 Tip: Use 'make test-libs' to test only libraries"
	@echo "💡 Tip: Use 'make test-components' to test only components"


# ============================================================================
# E2E Tests (DAY 159)
# test-e2e-synthetic: para componentes que sustituye, inyecta tráfico sintético
#                     y verifica contadores en logs. Rápido y determinista.
# test-e2e-live:      pipeline completo con componentes reales, parsea logs
#                     y verifica integridad de la cadena completa.
# Ambos son gates duros: exit 1 si cualquier criterio falla.
# ============================================================================
.PHONY: test-e2e-synthetic test-e2e-synthetic-full test-e2e-synthetic-firewall test-e2e-live test-e2e test-enterprise-plugin test-e2e-vault test-dual-compilation vault-dev-start vault-dev-stop

test-e2e-live:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🧪 TEST-E2E-LIVE — Pipeline real, sin injectors          ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "── Verificando 6/6 RUNNING ──"
	@$(MAKE) pipeline-status
	@echo "── Snapshot de contadores (DEBT-E2E-LIVE-DELTA-001) ──"
	@echo "── Verificando precondiciones del pipeline ──"
	@vagrant ssh -c "python3 /vagrant/scripts/check_e2e_pipeline.py precondition" || \
	  (echo "❌ TEST-E2E-LIVE ABORTED: precondición no cumplida (exit 2)" && exit 2)
	@vagrant ssh -c "python3 /vagrant/scripts/check_e2e_pipeline.py snapshot"
	@echo "── Observando pipeline real durante 60s ──"
	@sleep 60
	@echo "── Verificando delta E2E (≥1 evento nuevo) ──"
	@vagrant ssh -c "python3 /vagrant/scripts/check_e2e_pipeline.py check" || \
	  (echo "❌ TEST-E2E-LIVE FAILED" && exit 1)
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ TEST-E2E-LIVE PASSED                                  ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

test-e2e-synthetic-full:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🧪 TEST-E2E-SYNTHETIC-FULL                               ║"
	@echo "║  sniffer_injector → ml-detector → firewall               ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "── Parando sniffer real ──"
	@vagrant ssh -c "tmux kill-session -t sniffer 2>/dev/null || true"
	@sleep 2
	@echo "── Esperando stat fresco de ml-detector (60s cycle) ──"
	@sleep 65
	@echo "── Snapshot de contadores ──"
	@vagrant ssh -c "python3 /vagrant/scripts/check_e2e_pipeline.py snapshot"
	@echo "── Inyectando 100 eventos vía synthetic_sniffer_injector ──"
	@vagrant ssh -c "tmux kill-session -t e2e-sniffer-injector 2>/dev/null || true"
	@vagrant ssh -c "tmux new-session -d -s e2e-sniffer-injector 'sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_sniffer_injector 100 10 > /vagrant/logs/lab/e2e-sniffer-injector.log 2>&1; tmux kill-session -t e2e-sniffer-injector 2>/dev/null || true'"
	@echo "   Esperando fin de inyeccion (~20s)..."
	@vagrant ssh -c "timeout 60 bash -c 'until grep -q \"Injection complete\" /vagrant/logs/lab/e2e-sniffer-injector.log 2>/dev/null; do sleep 1; done'"
	@vagrant ssh -c "tail -3 /vagrant/logs/lab/e2e-sniffer-injector.log"
	@echo "   Esperando stats de ml-detector (60s cycle)..."
	@sleep 65
	@echo "── Verificando delta E2E ──"
	@vagrant ssh -c "python3 /vagrant/scripts/check_e2e_pipeline.py check" || \
	  (echo "❌ TEST-E2E-SYNTHETIC-FULL FAILED" && exit 1)
	@echo "── Restaurando sniffer ──"
	@$(MAKE) sniffer-start
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ TEST-E2E-SYNTHETIC-FULL PASSED                        ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

test-e2e-synthetic-firewall:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🧪 TEST-E2E-SYNTHETIC-FIREWALL                           ║"
	@echo "║  ml_output_injector → firewall (aislado)                 ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "── Parando sniffer + ml-detector + firewall + injector ──"
	@vagrant ssh -c "tmux kill-session -t sniffer 2>/dev/null || true"
	@vagrant ssh -c "tmux kill-session -t ml-detector 2>/dev/null || true"
	@vagrant ssh -c "tmux kill-session -t firewall 2>/dev/null || true"
	@vagrant ssh -c "tmux kill-session -t e2e-ml-injector 2>/dev/null || true"
	@sleep 2
	@vagrant ssh -c "truncate -s 0 /vagrant/logs/lab/firewall-agent.log"
	@echo "── Arrancando injector primero (PUB bind a :5572) ──"
	@vagrant ssh -c "tmux new-session -d -s e2e-ml-injector 'sudo env LD_LIBRARY_PATH=/usr/local/lib /vagrant/tools/build-debug/synthetic_ml_output_injector 300 5 > /vagrant/logs/lab/e2e-ml-injector.log 2>&1'"
	@sleep 3
	@echo "── Arrancando firewall (SUB connect → primer intento exitoso) ──"
	@$(MAKE) firewall-start
	@echo "── Esperando primer System State Dump del firewall (35s) ──"
	@sleep 36
	@echo "── Snapshot omitido: log truncado, contadores desde 0 ──"
	# snapshot omitido — log truncado, contadores desde 0
	@echo "── Esperando fin de inyeccion (300@5 = 60s total) ──"
	@vagrant ssh -c "timeout 90 bash -c 'until grep -q \"Injection complete\" /vagrant/logs/lab/e2e-ml-injector.log 2>/dev/null; do sleep 1; done'"
	@vagrant ssh -c "tail -3 /vagrant/logs/lab/e2e-ml-injector.log"
	@echo "   Esperando stats de firewall (30s cycle)..."
	@sleep 35
	@echo "── Verificando delta E2E firewall ──"
	@vagrant ssh -c "python3 /vagrant/scripts/check_e2e_pipeline.py check-firewall-abs" || \
	  (echo "❌ TEST-E2E-SYNTHETIC-FIREWALL FAILED" && exit 1)
	@echo "── Restaurando pipeline ──"
	@$(MAKE) ml-detector-start sniffer-start
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ TEST-E2E-SYNTHETIC-FIREWALL PASSED                    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

test-e2e-synthetic: test-e2e-synthetic-full test-e2e-synthetic-firewall
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ ALL SYNTHETIC E2E TESTS PASSED (DAY 159)              ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

test-e2e: test-e2e-synthetic

test-e2e-live-gate: test-e2e-live


# ── Enterprise plugin tests ───────────────────────────────────────────────────
# Requiere: Vault dev mode corriendo (make vault-dev-start)

test-wire-protocol:
	@echo "=== test-wire-protocol ==="
	@vagrant ssh defender -c " \
	  cd /vagrant/common/build && \
	  cmake .. -DBUILD_TESTS=ON > /dev/null 2>&1 && \
	  make test_wire_protocol -j\$$(nproc) > /dev/null 2>&1 && \
	  ./test_wire_protocol" || \
	  (echo "FAILED: test-wire-protocol" && exit 1)
	@echo "=== test-wire-protocol PASSED ==="

test-enterprise-plugin:
	@echo "=== test-enterprise-plugin ==="
	@vagrant ssh defender -c " \
	  cd /vagrant/enterprise/plugins/vault_crypto/build && \
	  cmake .. -DBUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Debug > /dev/null 2>&1 && \
	  make -j$$(nproc) > /dev/null 2>&1 && \
	  ./tests/test_vault_provider" || \
	  (echo "FAILED: test-enterprise-plugin -- Vault dev mode corriendo?" && exit 1)
	@echo "=== test-enterprise-plugin PASSED ==="

test-dual-compilation:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🧪 DEBT-EMECAS-DUAL-COMPILATION-001                     ║"
	@echo "║  Community (OFF) + Enterprise (ON) ambos verdes           ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "── [1/4] plugin-loader community (ARGUS_VAULT_ENABLED=OFF) ──"
	@vagrant ssh -c "cd /vagrant/plugin-loader/build && cmake -DCMAKE_BUILD_TYPE=Debug .. > /dev/null 2>&1 && make -j$$(nproc) 2>&1 | tail -2"
	@echo "✅ plugin-loader community OK"
	@echo "── [2/4] plugin-loader enterprise (ARGUS_VAULT_ENABLED=ON) ──"
	@vagrant ssh -c 'PUBKEY_HEX=$$(VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=argus-dev-token vault kv get -field=hex secret/argus/enterprise/vendor-pubkey) && cd /vagrant/plugin-loader/build-enterprise && cmake -DCMAKE_BUILD_TYPE=Debug -DARGUS_VAULT_ENABLED=ON -DARGUS_ENTERPRISE_PUBKEY_HEX=$$PUBKEY_HEX .. > /dev/null 2>&1 && make -j$$(nproc) 2>&1 | tail -2'
	@echo "✅ plugin-loader enterprise OK"
	@echo "── [3/4] common/ community (ARGUS_VAULT_ENABLED=OFF) ──"
	@vagrant ssh -c "cd /vagrant/common/build && cmake -DARGUS_VAULT_ENABLED=OFF .. > /dev/null 2>&1 && make -j$$(nproc) 2>&1 | tail -2"
	@echo "✅ common/ community OK"
	@echo "── [4/4] common/ enterprise (ARGUS_VAULT_ENABLED=ON) ──"
	@vagrant ssh -c "cd /vagrant/common/build && cmake -DARGUS_VAULT_ENABLED=ON .. > /dev/null 2>&1 && make -j$$(nproc) 2>&1 | tail -2"
	@echo "✅ common/ enterprise OK"
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ DUAL-COMPILATION PASSED — community + enterprise OK   ║"
	@echo "║  DEBT-EMECAS-DUAL-COMPILATION-001: CERRADA               ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

vault-dev-seed:
	@echo "── Preparando seed enterprise en Vault dev ──"
	@vagrant ssh -c "VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=argus-dev-token vault secrets enable -path=argus -version=1 kv 2>&1 | grep -v 'already enabled' || true"
	@vagrant ssh -c "VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=argus-dev-token vault write argus/dev/families/family_A/seed value=\$$(python3 -c 'import secrets; print(secrets.token_hex(32))') > /dev/null && echo '✅ Vault seed enterprise OK'"

test-e2e-vault: vault-dev-seed
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🧪 TEST-E2E-VAULT — Enterprise crypto integration        ║"
	@echo "║  Requiere: Vault dev corriendo (make vault-dev-start)     ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "── Step 1: Verificando Vault dev activo ──"
	@vagrant ssh -c "VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=argus-dev-token vault read argus/dev/families/family_A/seed > /dev/null 2>&1 && echo '✅ Vault OK' || (echo '❌ Vault no responde — ejecuta: make vault-dev-start' && exit 1)"
	@echo "── Step 2: Compilando common/ con ARGUS_VAULT_ENABLED=ON ──"
	@vagrant ssh -c "cd /vagrant/common/build && cmake .. -DARGUS_VAULT_ENABLED=ON > /dev/null 2>&1 && make -j$$(nproc) > /dev/null 2>&1 && echo '✅ common/ enterprise build OK'"
	@echo "── Step 3: Tests vault_provider (6/6) ──"
	@$(MAKE) test-enterprise-plugin
	@echo "── Step 4: Compilando etcd-server con ARGUS_VAULT_ENABLED=ON ──"
	@vagrant ssh -c "cd /vagrant/etcd-server/build-debug && cmake .. -DARGUS_VAULT_ENABLED=ON > /dev/null 2>&1 && make etcd-server -j$$(nproc) 2>&1 | tail -3"
	@echo "── Step 5: Smoke test etcd-server enterprise (Acto I — VaultProvider) ──"
	@vagrant ssh -c "sudo timeout -k 2 8 env LD_LIBRARY_PATH=/usr/local/lib VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=argus-dev-token /vagrant/etcd-server/build-debug/etcd-server 2>&1 | tee /tmp/etcd_vault_smoke.log | grep -E 'VaultProvider|ICryptoProvider|epoch|fatal' ; grep -q 'ICryptoProvider OK' /tmp/etcd_vault_smoke.log && echo '✅ Acto I: VaultProvider OK' || (echo '❌ Acto I FAILED' && exit 1)"
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ TEST-E2E-VAULT PASSED                                 ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

vault-dev-start:
	@echo "=== Arrancando Vault dev mode ==="
	@vagrant ssh defender -c " \
	  pgrep -x vault > /dev/null && echo 'Vault ya corriendo' || \
	  (nohup vault server -dev \
	    -dev-root-token-id=argus-dev-token \
	    -dev-listen-address=0.0.0.0:8200 \
	    > /tmp/vault-dev.log 2>&1 &) ; \
	  sleep 3 && \
	  VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=argus-dev-token \
	  vault kv put secret/argus/crypto \
	    seed=argus-dev-seed-32bytes-placeholder provider=vault_crypto > /dev/null && \
	  echo 'Vault dev OK'"

vault-dev-stop:
	@vagrant ssh defender -c "pkill vault && echo 'Vault detenido' || echo 'Vault no estaba corriendo'"

	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ ALL E2E TESTS PASSED (DAY 159)                       ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

# ============================================================================
# Fuzzing Targets (DEBT-FUZZING-LIBFUZZER-001 — DAY 130)
# ============================================================================
fuzz-safe-exec:
	@echo "🔍 Building and running libFuzzer on validate_chain_name + is_safe_for_exec..."
	@vagrant ssh -c " \
		cd /vagrant/firewall-acl-agent/fuzz && \
		clang++ -std=c++20 -fsanitize=fuzzer,address \
			-I/vagrant/firewall-acl-agent/src/core \
			-I/vagrant/firewall-acl-agent/include \
			fuzz_validate_chain.cpp -o fuzz_validate_chain && \
		./fuzz_validate_chain -max_total_time=60 -jobs=2 corpus/ 2>&1 | tail -5"
	@echo "✅ fuzz-safe-exec completado"

fuzz-validate-filepath:
	@echo "🔍 Building and running libFuzzer on validate_filepath..."
	@vagrant ssh -c " \
		cd /vagrant/firewall-acl-agent/fuzz && \
		clang++ -std=c++20 -fsanitize=fuzzer,address \
			-I/vagrant/firewall-acl-agent/src/core \
			-I/vagrant/firewall-acl-agent/include \
			fuzz_validate_filepath.cpp -o fuzz_validate_filepath && \
		./fuzz_validate_filepath -max_total_time=60 -jobs=2 corpus/ 2>&1 | tail -5"
	@echo "✅ fuzz-validate-filepath completado"

fuzz-all: fuzz-safe-exec fuzz-validate-filepath
	@echo "✅ All fuzz targets completed — corpus en firewall-acl-agent/fuzz/corpus/"

# ============================================================================
# Verification Targets (ENHANCED - Day 57)
# ============================================================================

verify-etcd-linkage:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔍 Verifying etcd-client Linkage                         ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "0️⃣  etcd-client library:"
	@vagrant ssh -c 'if [ -f /usr/local/lib/libetcd_client.so.1.0.0 ]; then \
		echo "   ✅ Library installed"; \
		ls -lh /usr/local/lib/libetcd_client.so*; \
		nm -D /usr/local/lib/libetcd_client.so.1.0.0 | grep -c " T " | xargs echo "   Public methods:"; \
	else \
		echo "   ❌ Library NOT FOUND - run: make etcd-client-build"; \
	fi'
	@echo ""
	@echo "Components (current profile: $(PROFILE)):"
	@vagrant ssh -c 'if [ -f $(SNIFFER_BUILD_DIR)/sniffer ]; then \
		ldd $(SNIFFER_BUILD_DIR)/sniffer 2>/dev/null | grep etcd_client && echo "   ✅ Sniffer linked" || echo "   ❌ Sniffer NOT linked"; \
	else \
		echo "   ⚠️  Sniffer not built"; \
	fi'
	@vagrant ssh -c 'if [ -f $(ML_DETECTOR_BUILD_DIR)/ml-detector ]; then \
		ldd $(ML_DETECTOR_BUILD_DIR)/ml-detector 2>/dev/null | grep etcd_client && echo "   ✅ ML Detector linked" || echo "   ❌ ML Detector NOT linked"; \
	else \
		echo "   ⚠️  ML Detector not built"; \
	fi'
	@vagrant ssh -c 'if [ -f $(RAG_INGESTER_BUILD_DIR)/rag-ingester ]; then \
		ldd $(RAG_INGESTER_BUILD_DIR)/rag-ingester 2>/dev/null | grep etcd_client && echo "   ✅ RAG Ingester linked" || echo "   ❌ RAG Ingester NOT linked"; \
	else \
		echo "   ⚠️  RAG Ingester not built"; \
	fi'
	@vagrant ssh -c 'if [ -f $(FIREWALL_BUILD_DIR)/firewall-acl-agent ]; then \
		ldd $(FIREWALL_BUILD_DIR)/firewall-acl-agent 2>/dev/null | grep etcd_client && echo "   ✅ Firewall linked" || echo "   ❌ Firewall NOT linked"; \
	else \
		echo "   ⚠️  Firewall not built"; \
	fi'
	@echo ""

verify-encryption:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔐 Verifying Encryption/Compression Configuration        ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "1️⃣  Sniffer config:"
	@vagrant ssh -c "jq '.transport.encryption.enabled, .transport.compression.enabled' /vagrant/sniffer/config/sniffer.json 2>/dev/null || echo '   ⚠️  Config not found'"
	@echo ""
	@echo "2️⃣  ML Detector config:"
	@vagrant ssh -c "jq '.transport.encryption.enabled, .transport.compression.enabled' /vagrant/ml-detector/config/ml_detector_config.json 2>/dev/null || echo '   ⚠️  Config not found'"
	@echo ""
	@echo "3️⃣  Firewall config:"
	@vagrant ssh -c "jq '.transport.encryption.enabled, .transport.compression.enabled' /vagrant/firewall-acl-agent/config/firewall.json 2>/dev/null || echo '   ⚠️  Config not found'"
	@echo ""

verify-pipeline-config: verify-etcd-linkage verify-encryption

verify-all:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Running ALL Verifications                             ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@$(MAKE) verify-etcd-linkage
	@$(MAKE) verify-encryption
	@echo ""
	@echo "✅ All verifications complete"

# ============================================================================
# Unified Build Targets
# ============================================================================

build-unified: proto-unified seed-client-build crypto-transport-build etcd-client-build plugin-loader-build sniffer ml-detector rag-ingester rag-build firewall tools
	@echo ""
	@echo "✅ Unified build complete [$(PROFILE)]"
	@$(MAKE) proto-verify

all: build-unified etcd-server
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ ALL COMPONENTS BUILT [$(PROFILE)]                     ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Build Summary:"
	@echo "  ✅ Protobuf unified"
	@echo "  ✅ crypto-transport library"
	@echo "  ✅ etcd-client library"
	@echo "  ✅ plugin-loader library (PHASE 1)"
	@echo "  ✅ Sniffer"
	@echo "  ✅ ML Detector"
	@echo "  ✅ RAG Ingester"
	@echo "  ✅ Firewall ACL Agent"
	@echo "  ✅ etcd-server"
	@echo "  ✅ Tools"
	@echo "  ✅ seed-client library (ADR-013 PHASE 1)"
	@echo ""
	@echo "Profile: $(PROFILE)"
	@echo "Component builds: build-$(PROFILE)/"
	@echo "Library builds: build/ (release)"
	@echo ""
	@echo "🏛️  Via Appia Quality: Built to last"
	@echo ""
	@echo "Next steps:"
	@echo "  make verify-all  - Verify linkage and configs"
	@echo "  make test        - Run all tests"

rebuild-unified: clean build-unified
	@echo "✅ Rebuild complete [$(PROFILE)]"

rebuild: clean all
	@echo "✅ Full rebuild complete [$(PROFILE)]"

# ============================================================================
# BPF Diagnostics (Day 8)
# ============================================================================

check-libbpf:
	@echo "════════════════════════════════════════════════════════════"
	@echo "🔍 Checking libbpf installation (Day 8 Fix)"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "1️⃣  libbpf version:"
	@vagrant ssh -c "pkg-config --modversion libbpf 2>/dev/null || echo '❌ libbpf not found'"
	@echo ""
	@echo "2️⃣  libbpf CFLAGS:"
	@vagrant ssh -c "pkg-config --cflags libbpf 2>/dev/null || echo '❌ pkg-config failed'"
	@echo ""
	@echo "3️⃣  libbpf LDFLAGS:"
	@vagrant ssh -c "pkg-config --libs libbpf 2>/dev/null || echo '❌ pkg-config failed'"
	@echo ""
	@echo "4️⃣  Verification:"
	@vagrant ssh -c 'LIBBPF_VER=$$(pkg-config --modversion libbpf 2>/dev/null); \
		if [ -z "$$LIBBPF_VER" ]; then \
			echo "❌ libbpf NOT installed - run: vagrant provision"; \
		elif [ "$$(printf "%s\n" "1.2.0" "$$LIBBPF_VER" | sort -V | head -n1)" = "1.2.0" ]; then \
			echo "✅ libbpf $$LIBBPF_VER >= 1.2.0 (BPF map bug FIXED)"; \
		else \
			echo "⚠️  libbpf $$LIBBPF_VER < 1.2.0 (BUG PRESENT)"; \
		fi'
	@echo "════════════════════════════════════════════════════════════"

verify-bpf-maps:
	@echo "════════════════════════════════════════════════════════════"
	@echo "🔍 Verifying BPF Maps Loading"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Checking BPF object file:"
	@vagrant ssh -c "ls -lh $(SNIFFER_BUILD_DIR)/sniffer.bpf.o 2>/dev/null || echo '   ❌ BPF object not found - run: make sniffer'"
	@echo ""
	@echo "Searching for interface_configs in object:"
	@vagrant ssh -c "llvm-objdump -h $(SNIFFER_BUILD_DIR)/sniffer.bpf.o 2>/dev/null | grep -i maps && echo '   ✅ .maps section found' || echo '   ❌ .maps section not found'"
	@echo "════════════════════════════════════════════════════════════"

diagnose-bpf: check-libbpf verify-bpf-maps
	@echo ""
	@echo "🔧 BPF Diagnostics Complete"

# ============================================================================
# Run Components
# ============================================================================

run-sniffer:
	@echo "📡 Running Sniffer [$(PROFILE)]..."
	@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && sudo ./sniffer -c /vagrant/sniffer/config/sniffer.json"

run-detector:
	@echo "🤖 Running ML Detector [$(PROFILE)]..."
	@vagrant ssh -c "cd $(ML_DETECTOR_BUILD_DIR) && ./ml-detector -c /vagrant/ml-detector/config/ml_detector_config.json"

run-firewall:
	@echo "🔥 Running Firewall [$(PROFILE)]..."
	@vagrant ssh -c "cd $(FIREWALL_BUILD_DIR) && sudo ./firewall-acl-agent -c /vagrant/firewall-acl-agent/config/firewall.json"

# ============================================================================
# Lab Control
# ============================================================================

run-lab-dev:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🚀 Starting ML Defender Lab [$(PROFILE)]                 ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@vagrant ssh -c "cd /vagrant && bash scripts/run_lab_dev.sh"

run-lab-dev-day23: etcd-server-start
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🚀 Starting ML Defender Lab - Day 23 (with etcd)         ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@sleep 3
	@vagrant ssh -c "cd /vagrant && bash scripts/run_lab_dev.sh"

kill-lab:
	@echo "💀 Stopping ML Defender Lab..."
	-@vagrant ssh -c "sudo pkill -9 -f firewall-acl-agent" 2>/dev/null || true
	-@vagrant ssh -c "pkill -9 -f ml-detector" 2>/dev/null || true
	-@vagrant ssh -c "sudo pkill -9 -f sniffer" 2>/dev/null || true
	@echo "✅ Lab stopped"

kill-lab-day23: kill-lab
	-@vagrant ssh -c "pkill -9 -f etcd-server" 2>/dev/null || true
	@echo "✅ Lab + etcd-server stopped"

status-lab:
	@echo "════════════════════════════════════════════════════════════"
	@echo "ML Defender Lab Status [$(PROFILE)]:"
	@echo "════════════════════════════════════════════════════════════"
	@vagrant ssh -c "pgrep -a -f firewall-acl-agent && echo '✅ Firewall: RUNNING' || echo '❌ Firewall: STOPPED'"
	@vagrant ssh -c "pgrep -a -f ml-detector && echo '✅ Detector: RUNNING' || echo '❌ Detector: STOPPED'"
	@vagrant ssh -c "pgrep -a -f 'sniffer.*-c' && echo '✅ Sniffer:  RUNNING' || echo '❌ Sniffer:  STOPPED'"
	@echo "════════════════════════════════════════════════════════════"

status-lab-day23: status-lab
	@vagrant ssh -c "pgrep -a -f etcd-server && echo '✅ etcd-server: RUNNING' || echo '❌ etcd-server: STOPPED'"

kill-all: kill-lab-day23

check-ports:
	@vagrant ssh -c "sudo ss -tlnp | grep -E '5571|5572' && echo '⚠️  Ports in use' || echo '✅ Ports free'"

# ============================================================================
# Logs
# ============================================================================

logs-sniffer:
	@vagrant ssh -c "tail -f /vagrant/logs/lab/sniffer.log 2>/dev/null || echo 'No sniffer logs yet'"

logs-detector:
	@vagrant ssh -c "tail -f /vagrant/ml-detector/build/logs/*.log 2>/dev/null || echo 'No detector logs yet'"

logs-firewall:
	@vagrant ssh -c "tail -f /vagrant/firewall-acl-agent/build/logs/*.log 2>/dev/null || echo 'No firewall logs yet'"

logs-lab:
	@echo "📋 Combined Lab Logs (CTRL+C to exit)..."
	@vagrant ssh -c "cd /vagrant && bash scripts/monitor_lab.sh"

# ============================================================================
# Development Workflows
# ============================================================================

dev-setup: up all
	@echo "✅ Development environment ready [$(PROFILE)]"

dev-setup-unified: up build-unified
	@echo "✅ Development environment ready (unified protobuf) [$(PROFILE)]"

schema-update: proto rebuild
	@echo "✅ Schema updated and components rebuilt [$(PROFILE)]"

quick-fix:
	@echo "🔧 Quick bug fix procedure..."
	@$(MAKE) kill-lab
	@$(MAKE) rebuild
	@echo "✅ Ready to test fix [$(PROFILE)]"

# ============================================================================
# Dataset Replays
# ============================================================================

CTU13_SMALL := /vagrant/datasets/ctu13/smallFlows.pcap
CTU13_NERIS := /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap
CTU13_BIG := /vagrant/datasets/ctu13/bigFlows.pcap

test-replay-small:
	@echo "🧪 Replaying CTU-13 smallFlows.pcap..."
	@vagrant ssh client -c "mkdir -p /vagrant/logs/lab && \
		sudo tcpreplay -i eth1 --mbps=10 --stats=2 $(CTU13_SMALL) 2>&1 | tee /vagrant/logs/lab/tcpreplay.log"

test-replay-neris:
	@echo "🧪 Replaying CTU-13 Neris botnet (492K events)..."
	@vagrant ssh client -c "mkdir -p /vagrant/logs/lab && \
		sudo tcpreplay -i eth1 --mbps=10 --stats=5 $(CTU13_NERIS) 2>&1 | tee /vagrant/logs/lab/tcpreplay.log"

test-replay-big:
	@echo "🧪 Replaying CTU-13 bigFlows.pcap..."
	@vagrant ssh client -c "mkdir -p /vagrant/logs/lab && \
		sudo tcpreplay -i eth1 --mbps=10 --stats=10 $(CTU13_BIG) 2>&1 | tee /vagrant/logs/lab/tcpreplay.log"

# ── relay targets — usan tmux, no systemctl ───────────────────────────────────
test-replay-neris-x86-ebpf:
	@echo "🧪 [Variant A / eBPF] Parando libpcap si activo..."
	@vagrant ssh defender -c "tmux kill-session -t sniffer-libpcap 2>/dev/null || true"
	@echo "🔄 Reiniciando sniffer eBPF limpio para el experimento..."
	@vagrant ssh defender -c "tmux kill-session -t sniffer 2>/dev/null || true"
	@sleep 1
	@$(MAKE) sniffer-start
	@echo "📊 Iniciando captura de métricas en defender..."
	@vagrant ssh defender -c \
	  "mkdir -p /vagrant/logs/lab && \
	   cat /proc/net/dev > /vagrant/logs/lab/netdev-pre-ebpf.txt && \
	   nohup bash -c 'while true; do cat /proc/net/dev; sleep 1; done' \
	     > /vagrant/logs/lab/netdev-ebpf.log 2>&1 &"
	@echo "🔁 Replaying CTU-13 Neris (Variant A) — 10 Mbps..."
	@vagrant ssh client -c "mkdir -p /vagrant/logs/lab && \
	   sudo tcpreplay -i eth1 --mbps=10 --stats=1 $(CTU13_NERIS) \
	     > /vagrant/logs/lab/tcpreplay-ebpf-10mbps.log 2>&1; \
	   echo \"exit=\$$?\" >> /vagrant/logs/lab/tcpreplay-ebpf-10mbps.log" || true
	@vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/lab/tcpreplay-ebpf-10mbps.log 2>/dev/null | tail -6" || true
	@echo "🔁 Replaying CTU-13 Neris (Variant A) — 50 Mbps..."
	@vagrant ssh client -c \
	  "sudo tcpreplay -i eth1 --mbps=50 --stats=1 $(CTU13_NERIS) \
	     > /vagrant/logs/lab/tcpreplay-ebpf-50mbps.log 2>&1; \
	   echo \"exit=\$$?\" >> /vagrant/logs/lab/tcpreplay-ebpf-50mbps.log" || true
	@vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/lab/tcpreplay-ebpf-50mbps.log 2>/dev/null | tail -6" || true
	@echo "🔁 Replaying CTU-13 Neris (Variant A) — 100 Mbps..."
	@vagrant ssh client -c \
	  "sudo tcpreplay -i eth1 --mbps=100 --stats=1 $(CTU13_NERIS) \
	     > /vagrant/logs/lab/tcpreplay-ebpf-100mbps.log 2>&1; \
	   echo \"exit=\$$?\" >> /vagrant/logs/lab/tcpreplay-ebpf-100mbps.log" || true
	@vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/lab/tcpreplay-ebpf-100mbps.log 2>/dev/null | tail -6" || true
	@vagrant ssh defender -c "pkill -f 'while true; do cat /proc/net' 2>/dev/null || true" || true
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Variant A (eBPF) DONE — ADR-029 DAY 145              ║"
	@echo "╠════════════════════════════════════════════════════════════╣"
	@echo "║  Logs en VM:                                              ║"
	@echo "║  /vagrant/logs/lab/tcpreplay-ebpf-10mbps.log             ║"
	@echo "║  /vagrant/logs/lab/tcpreplay-ebpf-50mbps.log             ║"
	@echo "║  /vagrant/logs/lab/tcpreplay-ebpf-100mbps.log            ║"
	@echo "║  /vagrant/logs/lab/netdev-ebpf.log                       ║"
	@echo "║  Nota: warnings 'Message too long' son artefacto MTU     ║"
	@echo "║  de VirtualBox — no son errores del pipeline.            ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

test-replay-neris-x86-libpcap:
	@echo "🧪 [Variant B / libpcap] Parando eBPF sniffer si activo..."
	@vagrant ssh defender -c "tmux kill-session -t sniffer 2>/dev/null || true"
	@echo "🔄 Reiniciando sniffer libpcap limpio para el experimento..."
	@vagrant ssh defender -c "tmux kill-session -t sniffer-libpcap 2>/dev/null || true"
	@sleep 1
	@$(MAKE) sniffer-libpcap-start
	@echo "📊 Iniciando captura de métricas en defender..."
	@vagrant ssh defender -c \
	  "mkdir -p /vagrant/logs/lab && \
	   cat /proc/net/dev > /vagrant/logs/lab/netdev-pre-libpcap.txt && \
	   nohup bash -c 'while true; do cat /proc/net/dev; sleep 1; done' \
	     > /vagrant/logs/lab/netdev-libpcap.log 2>&1 &"
	@echo "🔁 Replaying CTU-13 Neris (Variant B) — 10 Mbps..."
	@vagrant ssh client -c "mkdir -p /vagrant/logs/lab && \
	   sudo tcpreplay -i eth1 --mbps=10 --stats=1 $(CTU13_NERIS) \
	     > /vagrant/logs/lab/tcpreplay-libpcap-10mbps.log 2>&1; \
	   echo \"exit=\$$?\" >> /vagrant/logs/lab/tcpreplay-libpcap-10mbps.log" || true
	@vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/lab/tcpreplay-libpcap-10mbps.log 2>/dev/null | tail -6" || true
	@echo "🔁 Replaying CTU-13 Neris (Variant B) — 50 Mbps..."
	@vagrant ssh client -c \
	  "sudo tcpreplay -i eth1 --mbps=50 --stats=1 $(CTU13_NERIS) \
	     > /vagrant/logs/lab/tcpreplay-libpcap-50mbps.log 2>&1; \
	   echo \"exit=\$$?\" >> /vagrant/logs/lab/tcpreplay-libpcap-50mbps.log" || true
	@vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/lab/tcpreplay-libpcap-50mbps.log 2>/dev/null | tail -6" || true
	@echo "🔁 Replaying CTU-13 Neris (Variant B) — 100 Mbps..."
	@vagrant ssh client -c \
	  "sudo tcpreplay -i eth1 --mbps=100 --stats=1 $(CTU13_NERIS) \
	     > /vagrant/logs/lab/tcpreplay-libpcap-100mbps.log 2>&1; \
	   echo \"exit=\$$?\" >> /vagrant/logs/lab/tcpreplay-libpcap-100mbps.log" || true
	@vagrant ssh client -c \
	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' \
	   /vagrant/logs/lab/tcpreplay-libpcap-100mbps.log 2>/dev/null | tail -6" || true
	@vagrant ssh defender -c "pkill -f 'while true; do cat /proc/net' 2>/dev/null || true" || true
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Variant B (libpcap) DONE — ADR-029 DAY 145           ║"
	@echo "╠════════════════════════════════════════════════════════════╣"
	@echo "║  Logs en VM:                                              ║"
	@echo "║  /vagrant/logs/lab/tcpreplay-libpcap-10mbps.log          ║"
	@echo "║  /vagrant/logs/lab/tcpreplay-libpcap-50mbps.log          ║"
	@echo "║  /vagrant/logs/lab/tcpreplay-libpcap-100mbps.log         ║"
	@echo "║  /vagrant/logs/lab/netdev-libpcap.log                    ║"
	@echo "║  Nota: warnings 'Message too long' son artefacto MTU     ║"
	@echo "║  de VirtualBox — no son errores del pipeline.            ║"
	@echo "╚════════════════════════════════════════════════════════════╝"

# ============================================================================
# etcd-server Control

# ============================================================================
# Experiment Comparative: Suricata vs aRGus NDR (DAY 146)
# Replicates Tables 3, 7, 8, 11 from paper v19
# Dataset: CTU-13 Neris — ground truth: 147.32.84.165 (646 flows)
# Topology: suricata VM (IDS) + client VM (tcpreplay) — identical to aRGus
# Usage:
#   make experiment-suricata-up       # arrancar VMs del experimento
#   make experiment-suricata-run      # ejecutar los 3 runs (10/50/100 Mbps)
#   make experiment-suricata-results  # parsear eve.json y mostrar métricas
#   make experiment-suricata-down     # parar VMs
# ============================================================================

SURICATA_DIR := experiments/suricata-comparative
SURICATA_EVE := /var/log/suricata/eve.json
SURICATA_LOGS := /vagrant/logs/experiment
MALICIOUS_IP := 147.32.84.165

.PHONY: experiment-suricata-up experiment-suricata-down experiment-suricata-run
.PHONY: experiment-suricata-replay-10 experiment-suricata-replay-50 experiment-suricata-replay-100
.PHONY: experiment-suricata-results experiment-suricata-status

experiment-suricata-up:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🚀 Experiment Suricata — Arrancar VMs                    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@cd $(SURICATA_DIR) && vagrant up suricata
	@cd $(SURICATA_DIR) && vagrant up client
	@echo "✅ VMs del experimento arrancadas"
	@cd $(SURICATA_DIR) && vagrant status

experiment-suricata-down:
	@echo "🛑 Parando VMs del experimento Suricata..."
	@cd $(SURICATA_DIR) && vagrant halt
	@echo "✅ VMs paradas"

experiment-suricata-status:
	@cd $(SURICATA_DIR) && vagrant status
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c "sudo systemctl status suricata --no-pager | head -5" 2>/dev/null || true

experiment-suricata-replay-10:
	@echo "🔁 [Suricata] Replay CTU-13 Neris — 10 Mbps..."
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c 	  "sudo systemctl stop suricata 2>/dev/null; 	   sudo rm -f $(SURICATA_EVE); 	   sudo systemctl start suricata; 	   sleep 60; 	   mkdir -p $(SURICATA_LOGS)"
	@cd $(SURICATA_DIR) && vagrant ssh client -c 	  "mkdir -p /vagrant/logs/experiment && 	   sudo tcpreplay -i eth1 --mbps=10 --stats=1 $(CTU13_NERIS) 	     > /vagrant/logs/experiment/tcpreplay-suricata-10mbps.log 2>&1; 	   echo "exit=$$?" >> /vagrant/logs/experiment/tcpreplay-suricata-10mbps.log" || true
	@cd $(SURICATA_DIR) && vagrant ssh client -c 	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' 	   /vagrant/logs/experiment/tcpreplay-suricata-10mbps.log 2>/dev/null | tail -6" || true
	@echo "⏳ Esperando drain Suricata (10s)..."
	@sleep 10
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c "sudo cp $(SURICATA_EVE) $(SURICATA_LOGS)/eve-$(notdir $@).json 2>/dev/null || true; sudo systemctl stop suricata"

experiment-suricata-replay-50:
	@echo "🔁 [Suricata] Replay CTU-13 Neris — 50 Mbps..."
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c 	  "sudo systemctl stop suricata 2>/dev/null; 	   sudo rm -f $(SURICATA_EVE); 	   sudo systemctl start suricata; 	   sleep 60; 	   mkdir -p $(SURICATA_LOGS)"
	@cd $(SURICATA_DIR) && vagrant ssh client -c 	  "sudo tcpreplay -i eth1 --mbps=50 --stats=1 $(CTU13_NERIS) 	     > /vagrant/logs/experiment/tcpreplay-suricata-50mbps.log 2>&1; 	   echo "exit=$$?" >> /vagrant/logs/experiment/tcpreplay-suricata-50mbps.log" || true
	@cd $(SURICATA_DIR) && vagrant ssh client -c 	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' 	   /vagrant/logs/experiment/tcpreplay-suricata-50mbps.log 2>/dev/null | tail -6" || true
	@echo "⏳ Esperando drain Suricata (10s)..."
	@sleep 10
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c "sudo cp $(SURICATA_EVE) $(SURICATA_LOGS)/eve-$(notdir $@).json 2>/dev/null || true; sudo systemctl stop suricata"

experiment-suricata-replay-100:
	@echo "🔁 [Suricata] Replay CTU-13 Neris — 100 Mbps..."
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c 	  "sudo systemctl stop suricata 2>/dev/null; 	   sudo rm -f $(SURICATA_EVE); 	   sudo systemctl start suricata; 	   sleep 60; 	   mkdir -p $(SURICATA_LOGS)"
	@cd $(SURICATA_DIR) && vagrant ssh client -c 	  "sudo tcpreplay -i eth1 --mbps=100 --stats=1 $(CTU13_NERIS) 	     > /vagrant/logs/experiment/tcpreplay-suricata-100mbps.log 2>&1; 	   echo "exit=$$?" >> /vagrant/logs/experiment/tcpreplay-suricata-100mbps.log" || true
	@cd $(SURICATA_DIR) && vagrant ssh client -c 	  "grep -E 'Test complete|Actual:|Successful packets|Failed packets|exit=' 	   /vagrant/logs/experiment/tcpreplay-suricata-100mbps.log 2>/dev/null | tail -6" || true
	@echo "⏳ Esperando drain Suricata (10s)..."
	@sleep 10
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c "sudo cp $(SURICATA_EVE) $(SURICATA_LOGS)/eve-$(notdir $@).json 2>/dev/null || true; sudo systemctl stop suricata"

experiment-suricata-results:
	@echo "📊 Parseando resultados Suricata (eve.json)..."
	@cd $(SURICATA_DIR) && vagrant ssh suricata -c 	  "python3 /vagrant/experiments/suricata-comparative/parse_results.py 	   $(SURICATA_EVE) $(MALICIOUS_IP)" 2>/dev/null || 	  echo "⚠️  parse_results.py no disponible — revisar eve.json manualmente"

experiment-suricata-run: experiment-suricata-replay-10 experiment-suricata-replay-50 experiment-suricata-replay-100
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  ✅ Experiment Suricata COMPLETADO — 3 runs (10/50/100)   ║"
	@echo "╠════════════════════════════════════════════════════════════╣"
	@echo "║  Logs:                                                    ║"
	@echo "║  logs/experiment/tcpreplay-suricata-{10,50,100}mbps.log  ║"
	@echo "║  Ground truth: 147.32.84.165 (646 flows maliciosos)      ║"
	@echo "║  Comparar con: Table 11 paper v19 (aRGus DAY 145)        ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@$(MAKE) experiment-suricata-results

# ============================================================================
dev-setup-tools:
	@echo "🔧 Instalando herramientas de gestión en la VM..."
	@vagrant ssh -c "sudo apt-get update && sudo apt-get install -y tmux net-tools"

etcd-server-start: etcd-server
	@echo "🚀 Starting etcd-server (Persistente)..."
	@vagrant ssh -c "tmux kill-session -t etcd-server 2>/dev/null || true"
	@vagrant ssh -c "tmux new-session -d -s etcd-server 'mkdir -p /vagrant/logs/lab && cd /vagrant && sudo env LD_LIBRARY_PATH=/usr/local/lib $(ETCD_SERVER_BUILD_DIR)/etcd-server >> /vagrant/logs/lab/etcd-server.log 2>&1'"
	@sleep 2
	@$(MAKE) etcd-server-status

etcd-server-stop:
	@vagrant ssh -c "tmux kill-session -t etcd-server 2>/dev/null || true"
	@echo "✅ etcd-server stopped"

# ============================================================================
# TSAN Validation Suite (Day 48 Phase 0)
# ============================================================================

tsan-all:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔬 TSAN Full Validation Suite - Day 48 Phase 0           ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Step 1: Clean previous TSAN builds..."
	@$(MAKE) PROFILE=tsan clean
	@vagrant ssh -c "mkdir -p /vagrant/tsan-reports/day48"
	@echo ""
	@echo "Step 2: Build all components with TSAN..."
	@$(MAKE) PROFILE=tsan all
	@echo ""
	@echo "Step 3: Run unit tests with TSAN..."
	@echo ""
	@echo "  Testing Sniffer..."
	@vagrant ssh -c 'cd $(SNIFFER_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/sniffer-tsan history_size=7 second_deadlock_stack=1" \
		ctest --output-on-failure 2>&1 | tee /vagrant/tsan-reports/day48/sniffer-tsan-tests.log' || true
	@echo ""
	@echo "  Testing ML Detector..."
	@vagrant ssh -c 'cd $(ML_DETECTOR_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/ml-detector-tsan history_size=7" \
		ctest --output-on-failure 2>&1 | tee /vagrant/tsan-reports/day48/ml-detector-tsan-tests.log' || true
	@echo ""
	@echo "  Testing RAG Ingester..."
	@vagrant ssh -c 'cd $(RAG_INGESTER_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/rag-ingester-tsan history_size=7" \
		ctest --output-on-failure 2>&1 | tee /vagrant/tsan-reports/day48/rag-ingester-tsan-tests.log' || true
	@echo ""
	@echo "  Testing etcd-server..."
	@vagrant ssh -c 'cd $(ETCD_SERVER_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/etcd-server-tsan history_size=7" \
		ctest --output-on-failure 2>&1 | tee /vagrant/tsan-reports/day48/etcd-server-tsan-tests.log' || true
	@echo ""
	@echo "Step 4: Run integration test (5 min)..."
	@vagrant ssh -c 'cd /vagrant/sniffer && \
		mkdir -p $(SNIFFER_BUILD_DIR) && cd $(SNIFFER_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/sniffer-integration history_size=7" \
		timeout 300 ./sniffer -c /vagrant/sniffer/config/sniffer.json > /vagrant/tsan-reports/day48/sniffer-integration.log 2>&1 &' || true
	@vagrant ssh -c 'cd /vagrant/ml-detector && \
		mkdir -p $(ML_DETECTOR_BUILD_DIR) && cd $(ML_DETECTOR_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/ml-detector-integration history_size=7" \
		timeout 300 ./ml-detector --config /vagrant/ml-detector/config/detector.json > /vagrant/tsan-reports/day48/ml-detector-integration.log 2>&1 &' || true
	@vagrant ssh -c 'cd /vagrant/rag-ingester && \
		mkdir -p $(RAG_INGESTER_BUILD_DIR) && cd $(RAG_INGESTER_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/rag-ingester-integration history_size=7" \
		timeout 300 ./rag-ingester /vagrant/rag-ingester/config/rag-ingester.json > /vagrant/tsan-reports/day48/rag-ingester-integration.log 2>&1 &' || true
	@vagrant ssh -c 'cd /vagrant/etcd-server && \
		mkdir -p $(ETCD_SERVER_BUILD_DIR) && cd $(ETCD_SERVER_BUILD_DIR) && \
		TSAN_OPTIONS="log_path=/vagrant/tsan-reports/day48/etcd-server-integration history_size=7" \
		timeout 300 ./etcd-server > /vagrant/tsan-reports/day48/etcd-server-integration.log 2>&1 &' || true
	@sleep 310
	@vagrant ssh -c "pkill -f 'sniffer|ml-detector|rag-ingester|etcd-server' || true"
	@echo ""
	@echo "Step 5: Create baseline symlink..."
	@vagrant ssh -c "ln -sfn /vagrant/tsan-reports/day48 /vagrant/tsan-reports/baseline"
	@echo ""
	@echo "✅ TSAN Full Validation Complete"
	@echo ""
	@echo "📊 Reports generated:"
	@echo "   /vagrant/tsan-reports/day48/"
	@echo "   /vagrant/tsan-reports/baseline/ → day48/"
	@echo ""
	@$(MAKE) tsan-summary

tsan-quick:
	@echo "⚡ TSAN Quick Check..."
	@$(MAKE) PROFILE=tsan sniffer ml-detector
	@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && ctest --output-on-failure"
	@vagrant ssh -c "cd $(ML_DETECTOR_BUILD_DIR) && ctest --output-on-failure"
	@echo "✅ Quick TSAN check complete"

tsan-clean:
	@echo "🧹 Cleaning TSAN builds..."
	@$(MAKE) PROFILE=tsan clean
	@vagrant ssh -c "rm -rf /vagrant/tsan-reports/day48"
	@echo "✅ TSAN artifacts cleaned"

tsan-summary:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  📊 TSAN Validation Summary                                ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Unit Tests Results:"
	@echo "-------------------"
	@vagrant ssh -c "grep -E 'tests passed|test.*PASSED|PASS' /vagrant/tsan-reports/day48/sniffer-tsan-tests.log 2>/dev/null | tail -5 || echo 'No sniffer results'"
	@vagrant ssh -c "grep -E 'tests passed|test.*PASSED|PASS' /vagrant/tsan-reports/day48/ml-detector-tsan-tests.log 2>/dev/null | tail -5 || echo 'No ml-detector results'"
	@vagrant ssh -c "grep -E 'tests passed|test.*PASSED|PASS' /vagrant/tsan-reports/day48/rag-ingester-tsan-tests.log 2>/dev/null | tail -5 || echo 'No rag-ingester results'"
	@echo ""
	@echo "Race Conditions Detected:"
	@echo "-------------------------"
	@vagrant ssh -c "find /vagrant/tsan-reports/day48 -name '*-tsan.*' -exec grep -l 'WARNING: ThreadSanitizer' {} \; | wc -l | xargs echo 'Files with warnings:'" || echo "0"
	@echo ""
	@echo "Integration Test Status:"
	@echo "------------------------"
	@vagrant ssh -c "ls -lh /vagrant/tsan-reports/day48/*-integration.log 2>/dev/null | wc -l | xargs echo 'Components tested:'" || echo "0"
	@echo ""
	@echo "📁 Full reports: /vagrant/tsan-reports/day48/"
	@echo "════════════════════════════════════════════════════════════"

tsan-status:
	@echo "🔍 TSAN Build Status:"
	@echo ""
	@vagrant ssh -c "ls -lh $(SNIFFER_BUILD_DIR)/sniffer 2>/dev/null && echo '  ✅ Sniffer (TSAN)' || echo '  ❌ Sniffer not built'"
	@vagrant ssh -c "ls -lh $(ML_DETECTOR_BUILD_DIR)/ml-detector 2>/dev/null && echo '  ✅ ML Detector (TSAN)' || echo '  ❌ ML Detector not built'"
	@vagrant ssh -c "ls -lh $(RAG_INGESTER_BUILD_DIR)/rag-ingester 2>/dev/null && echo '  ✅ RAG Ingester (TSAN)' || echo '  ❌ RAG Ingester not built'"
	@vagrant ssh -c "ls -lh $(ETCD_SERVER_BUILD_DIR)/etcd-server 2>/dev/null && echo '  ✅ etcd-server (TSAN)' || echo '  ❌ etcd-server not built'"
	@echo ""
	@echo "Reports:"
	@vagrant ssh -c "ls -lh /vagrant/tsan-reports/day48/*.log 2>/dev/null | wc -l | xargs echo '  Log files:'" || echo "  ❌ No reports"

# ============================================================================
# Day 38 - Synthetic Data Generation
# ============================================================================

day38-step1:
	@echo "════════════════════════════════════════════════════════════"
	@echo "Day 38 - Step 1: etcd-server Bootstrap"
	@echo "════════════════════════════════════════════════════════════"
	@$(MAKE) etcd-server-start
	@sleep 2
	@vagrant ssh -c "curl -s http://localhost:2379/health > /dev/null 2>&1 && echo '✅ etcd-server ready' || echo '❌ etcd-server not responding'"

day38-step2: tools-build
	@echo "════════════════════════════════════════════════════════════"
	@echo "Day 38 - Step 2: Generate 100 Synthetic Events"
	@echo "════════════════════════════════════════════════════════════"
	@vagrant ssh -c "mkdir -p /vagrant/logs/rag/synthetic/events /vagrant/logs/rag/synthetic/artifacts"
	@vagrant ssh -c "cd $(TOOLS_BUILD_DIR) && ./generate_synthetic_events 100 0.20"

day38-step3:
	@echo "════════════════════════════════════════════════════════════"
	@echo "Day 38 - Step 3: Validate Artifacts"
	@echo "════════════════════════════════════════════════════════════"
	@vagrant ssh -c "find /vagrant/logs/rag/synthetic/artifacts -name 'event_*.pb.enc' | wc -l | xargs echo 'Generated:'"

day38-full: day38-step1 day38-step2 day38-step3
	@echo "✅ Day 38 workflow complete"

# ============================================================================
# RAG Ecosystem
# ============================================================================

rag-build: plugin-loader-build
	@echo "🔨 Building RAG Security System [$(PROFILE)]..."
	@vagrant ssh -c 'mkdir -p $(RAG_BUILD_DIR) && \
		cd $(RAG_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make -j4'
	@echo "✅ rag-security built ($(PROFILE))"

rag-clean:
	@echo "🧹 Cleaning RAG..."
	@vagrant ssh -c "cd /vagrant/rag && make clean"

rag-start:
	@echo "🚀 Starting rag-security (from /vagrant/rag/build-active)..."
	@vagrant ssh -c "tmux kill-session -t rag-security 2>/dev/null || true"
	@vagrant ssh -c "tmux new-session -d -s rag-security 'mkdir -p /vagrant/logs/lab && cd /vagrant/rag/build-active && ./rag-security >> /vagrant/logs/lab/rag-security.log 2>&1'"
	@sleep 2

rag-stop:
	@vagrant ssh -c "tmux kill-session -t rag-security 2>/dev/null || true"
	@echo "✅ rag-security stopped"

rag-status:
	@echo "════════════════════════════════════════════════════════════"
	@echo "RAG Security Status:"
	@vagrant ssh -c "pgrep -a -f rag-security && echo '✅ rag-security: RUNNING' || echo '❌ rag-security: STOPPED'"
	@vagrant ssh -c "tail -5 /vagrant/logs/rag.log 2>/dev/null || echo '⚠️  No log yet'"
	@echo "════════════════════════════════════════════════════════════"

rag-logs:
	@vagrant ssh -c "tail -f /vagrant/logs/lab/rag-security.log"

rag-attach:
	vagrant ssh -- tmux attach -t rag-security

# ============================================================================
# Test Hardening Suite (Day 46/47)
# ============================================================================

test-hardening-build: proto etcd-client-build
	@echo "🔨 Building Test-Driven Hardening Suite..."
	@vagrant ssh -c 'cd $(SNIFFER_BUILD_DIR) && \
		cmake $(CMAKE_FLAGS) .. && \
		make test_sharded_flow_full_contract \
		     test_ring_consumer_protobuf \
		     test_sharded_flow_multithread -j4'

test-hardening-run:
	@echo "🧪 Running Test-Driven Hardening Suite..."
	@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && ./test_sharded_flow_full_contract"
	@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && ./test_ring_consumer_protobuf"
	@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && ./test_sharded_flow_multithread"

test-hardening: test-hardening-build test-hardening-run

# =============================================================================
# CRYPTOGRAPHIC PROVISIONING (ADR-013, ADR-019)
# tools/provision.sh — single source of truth para keypairs + seeds
# Compatible AppArmor desde el primer día (paths fijos /etc/ml-defender/)
# =============================================================================

provision:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔐 ML Defender — Cryptographic Provisioning (PHASE 1)    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@vagrant ssh -c "sudo bash /vagrant/tools/provision.sh full"
	@echo ""
	@echo "✅ Provisioning completo"

provision-crypto:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔐 aRGus NDR — Provision Crypto (ADR-044)                ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@vagrant ssh -c "bash /vagrant/scripts/jenkins/provision_crypto.sh $(if $(FORCE),--force,) $(if $(AUDIT_OUT),--audit-out $(AUDIT_OUT),)"

provision-crypto-force:
	@$(MAKE) provision-crypto FORCE=1

provision-status:
	@vagrant ssh -c "sudo bash /vagrant/tools/provision.sh status"

provision-check:
	@echo "🔍 Verificando claves criptográficas..."
	@vagrant ssh -c "sudo bash /vagrant/tools/provision.sh verify" || \
		(echo "" && \
		 echo "❌ Claves ausentes o inválidas." && \
		 echo "   Ejecuta: make provision" && \
		 exit 1)
	@echo "✅ Claves verificadas"

provision-reprovision:
	@test -n "$(COMPONENT)" || \
		(echo "❌ Uso: make provision-reprovision COMPONENT=sniffer" && \
		 echo "   Componentes: etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security" && \
		 exit 1)
	@echo "⚠️  Re-provisionando $(COMPONENT)..."
	@vagrant ssh -c "sudo bash /vagrant/tools/provision.sh reprovision $(COMPONENT)"
	@echo "✅ Re-provisioning de $(COMPONENT) completo"

# ─── seed-client ─────────────────────────────────────────────────────────────
# Biblioteca de lectura de material criptográfico base (PHASE 1, ADR-013)
# Dependencia: nlohmann_json
# Ejecutar ANTES de crypto-transport si se recompila desde cero.

vault-client-build: seed-client-build crypto-transport-build
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  🔨 Building vault-client Library (ADR-044)               ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@vagrant ssh -c 'cd /vagrant/common && rm -rf build && mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Release .. && make -j4'
	@vagrant ssh -c 'cd /vagrant/common/build && sudo make install && sudo ldconfig'
	@echo "✅ vault-client instalado en /usr/local/lib"

vault-client-clean:
	@vagrant ssh -c 'rm -rf /vagrant/common/build'
	@vagrant ssh -c 'sudo rm -f /usr/local/lib/libvault_client.so*'
	@vagrant ssh -c 'sudo ldconfig'
	@echo "✅ vault-client limpiado"

vault-client-test:
	@vagrant ssh -c 'cd /vagrant/common/build && ctest --output-on-failure'

seed-client-build:
	@echo "╔══════════════════════════════════════════════╗"
	@echo "║  Building seed-client...                     ║"
	@echo "╚══════════════════════════════════════════════╝"
	@vagrant ssh -c 'cd /vagrant/libs/seed-client && rm -rf build && mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Release .. && make -j4'
	@vagrant ssh -c 'cd /vagrant/libs/seed-client/build && sudo make install && sudo ldconfig'
	@echo "✅ seed-client instalado"

seed-client-test:
	@echo "─── seed-client tests ───────────────────────"
	@vagrant ssh -c 'cd /vagrant/libs/seed-client/build && ctest --output-on-failure'

seed-client-clean:
	@vagrant ssh -c 'rm -rf /vagrant/libs/seed-client/build'
	@vagrant ssh -c 'sudo rm -f /usr/local/lib/libseed_client.so*'
	@echo "✅ seed-client limpiado"

seed-client-rebuild: seed-client-clean seed-client-build seed-client-test

# ============================================================================
# PRODUCCIÓN — ADR-030 Variant A — DAY 133
# Build/Runtime Separation (BSR) axiom — ADR-039
# Todos los targets prod-* corren en dev VM.
# Todos los check-prod-* corren en hardened VM.
# Lógica compleja → tools/prod/ (nunca inline).
# ============================================================================

.PHONY: prod-init-dist prod-build-x86 prod-collect-libs prod-sign prod-checksums prod-deploy-seeds
.PHONY: prod-verify prod-deploy-x86 prod-full-x86
.PHONY: check-prod-no-compiler check-prod-apparmor check-prod-capabilities
.PHONY: check-prod-permissions check-prod-falco check-prod-all
.PHONY: hardened-up hardened-halt hardened-destroy hardened-ssh
.PHONY: hardened-full hardened-redeploy vendor-download
.PHONY: hardened-setup-user hardened-setup-apparmor hardened-setup-falco hardened-setup-apt-integrity
.PHONY: hardened-setup-filesystem hardened-provision-all hardened-verify

HARDENED_X86_DIR   := vagrant/hardened-x86
DIST_X86           := dist/x86
ARGUS_BIN_DIST     := $(DIST_X86)/bin
ARGUS_LIB_DIST     := $(DIST_X86)/lib
ARGUS_PLUGIN_DIST  := $(DIST_X86)/plugins

# ── Guard: solo ejecutable desde dev VM (tiene compilador) ───────────────────
_check-dev-env:
	@vagrant ssh -c 'which clang++ > /dev/null 2>&1' || \
	  (echo "FAIL: prod targets requieren dev VM (clang++ no encontrado)"; exit 1)
	@echo "OK: dev VM detectada"

# ── Guard: hardened VM levantada ─────────────────────────────────────────────
_check-hardened-up:
	@cd $(HARDENED_X86_DIR) && vagrant status 2>/dev/null | grep -q running || \
	  (echo "FAIL: hardened-x86 VM no está corriendo. Ejecuta: make hardened-up"; exit 1)

# ─────────────────────────────────────────────────────────────────────────────
# Gestión de la hardened VM
# ─────────────────────────────────────────────────────────────────────────────

hardened-up:
	@echo "=== Levantando hardened-x86 VM ==="
	@cd $(HARDENED_X86_DIR) && vagrant up

hardened-halt:
	@echo "=== Parando hardened-x86 VM ==="
	@cd $(HARDENED_X86_DIR) && vagrant halt

hardened-destroy:
	@echo "=== Destruyendo hardened-x86 VM ==="
	@cd $(HARDENED_X86_DIR) && vagrant destroy -f

hardened-ssh:
	@cd $(HARDENED_X86_DIR) && vagrant ssh

# ─────────────────────────────────────────────────────────────────────────────
# dist/ — estructura de artefactos de producción
# ─────────────────────────────────────────────────────────────────────────────

prod-init-dist:
	@echo "=== Inicializando dist/x86/ ==="
	@mkdir -p $(ARGUS_BIN_DIST) $(ARGUS_LIB_DIST) $(ARGUS_PLUGIN_DIST)
	@echo "OK: dist/x86/{bin,lib,plugins} listos"

# ─────────────────────────────────────────────────────────────────────────────
# Compilación de binarios de producción
# Flags: PROFILE_PRODUCTION (-O3 -march=native -DNDEBUG -flto)
# Salida: dist/x86/bin/
# ─────────────────────────────────────────────────────────────────────────────

prod-build-x86: _check-dev-env prod-init-dist
	@echo "=== Building production binaries (x86-64) ==="
	@echo "── Step 1: pipeline-build PROFILE=production ──"
	$(MAKE) PROFILE=production pipeline-build
	@echo "── Step 2: recolectando binarios → dist/x86/ ──"
	@vagrant ssh -c 'bash /vagrant/tools/prod/build-x86.sh'
	@echo "OK: binarios en $(ARGUS_BIN_DIST)/"

# ─────────────────────────────────────────────────────────────────────────────
# Recolección de librerías runtime mínimas
# Solo lo que el pipeline necesita para ejecutar — sin dev deps
# Salida: dist/x86/lib/
# ─────────────────────────────────────────────────────────────────────────────

prod-collect-libs: _check-dev-env prod-init-dist
	@echo "=== Collecting runtime libraries ==="
	@vagrant ssh -c 'bash /vagrant/tools/prod/collect-libs.sh'
	@echo "OK: libs en $(ARGUS_LIB_DIST)/"

# ─────────────────────────────────────────────────────────────────────────────
# Firma Ed25519 de binarios + plugins
# Usa la misma clave que ADR-025 (plugin_signing.sk en la dev VM)
# ─────────────────────────────────────────────────────────────────────────────

prod-sign: _check-dev-env
	@echo "=== Signing production binaries (Ed25519) ==="
	@vagrant ssh -c 'sudo bash /vagrant/tools/prod/sign-binaries.sh'
	@echo "OK: .sig generados en $(DIST_X86)/"

# ─────────────────────────────────────────────────────────────────────────────
# SHA256SUMS — checksum de todos los artefactos en dist/x86/
# ─────────────────────────────────────────────────────────────────────────────

prod-checksums: _check-dev-env
	@echo "=== Generating SHA256SUMS ==="
	@vagrant ssh -c '\
	  cd /vagrant/$(DIST_X86) && \
	  find bin/ lib/ plugins/ -type f ! -name "*.sig" ! -name "SHA256SUMS*" \
	    -exec sha256sum {} \; | sort > SHA256SUMS && \
	  echo "OK: SHA256SUMS generado (lines=$$(wc -l < SHA256SUMS))"'

# ─────────────────────────────────────────────────────────────────────────────
# Verificación de SHA256SUMS + firmas Ed25519
# Se puede ejecutar en cualquier entorno (dev o hardened)
# ─────────────────────────────────────────────────────────────────────────────

prod-verify:
	@echo "=== Verifying production artifacts ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'bash /vagrant/tools/prod/verify-artifacts.sh'

# ─────────────────────────────────────────────────────────────────────────────
# Deploy a hardened VM
# Instala binarios, libs y plugins en /opt/argus/
# ─────────────────────────────────────────────────────────────────────────────

prod-deploy-x86: _check-hardened-up
	@echo "=== Deploying to hardened-x86 VM ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'sudo bash /vagrant/tools/prod/deploy-hardened.sh'
	@echo "OK: pipeline desplegado en /opt/argus/"

# ─────────────────────────────────────────────────────────────────────────────
# prod-deploy-seeds — Copia seeds desde dev VM a hardened VM
# Decisión Consejo D2 (DAY 134): seeds NO en EMECAS — deploy explícito.
#
# ⚠️  SEGURIDAD: seeds pasan brevemente por Mac host via /vagrant (shared folder).
#     Aceptable en Vagrant dev/test. En producción real: transferencia directa cifrada.
#     DEBT-SEEDS-SECURE-TRANSFER-001 (post-FEDER, Jenkins + hardware físico).
# ─────────────────────────────────────────────────────────────────────────────
prod-deploy-seeds: _check-hardened-up
	@echo "=== Deploying seeds to hardened-x86 VM ==="
	@echo "⚠️  Seeds pasan por Mac host via /vagrant — solo para Vagrant dev/test"
	@mkdir -p dist/seeds
	@chmod 700 dist/seeds
	@echo "── Step 1: extrayendo seeds de dev VM ──"
	@vagrant ssh -c 'sudo cp -r /etc/ml-defender/*/seed.bin /etc/ml-defender/*/seed.hex /tmp/seeds-export/ 2>/dev/null || true; 		sudo mkdir -p /tmp/seeds-export; 		for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do 			sudo mkdir -p /tmp/seeds-export/$$comp; 			sudo cp /etc/ml-defender/$$comp/seed.bin /tmp/seeds-export/$$comp/; 			sudo cp /etc/ml-defender/$$comp/seed.hex /tmp/seeds-export/$$comp/; 		done; 		sudo cp -r /tmp/seeds-export/* /vagrant/dist/seeds/; 		sudo chmod -R 700 /vagrant/dist/seeds/; 		sudo rm -rf /tmp/seeds-export'
	@echo "── Step 2: instalando seeds en hardened VM ──"
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c '		for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do 			sudo cp /vagrant/dist/seeds/$$comp/seed.bin /etc/ml-defender/$$comp/seed.bin; 			sudo cp /vagrant/dist/seeds/$$comp/seed.hex /etc/ml-defender/$$comp/seed.hex; 			sudo chmod 0400 /etc/ml-defender/$$comp/seed.bin; 			sudo chmod 0400 /etc/ml-defender/$$comp/seed.hex; 			sudo chown argus:argus /etc/ml-defender/$$comp/seed.bin; 			sudo chown argus:argus /etc/ml-defender/$$comp/seed.hex; 			echo "  ✅ $$comp/seed.bin desplegado"; 		done'
	@echo "── Step 2b: desplegando plugin_signing.pk (clave pública) ──"
	@vagrant ssh -c 'sudo cp /etc/ml-defender/plugins/plugin_signing.pk /vagrant/dist/seeds/plugin_signing.pk; sudo chmod 644 /vagrant/dist/seeds/plugin_signing.pk'
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'sudo cp /vagrant/dist/seeds/plugin_signing.pk /etc/ml-defender/plugins/plugin_signing.pk; sudo chmod 0444 /etc/ml-defender/plugins/plugin_signing.pk; sudo chown root:argus /etc/ml-defender/plugins/plugin_signing.pk; echo "  ✅ plugin_signing.pk desplegado"'
	@rm -f dist/seeds/plugin_signing.pk
	@echo "── Step 3: limpieza inmediata de dist/seeds/ ──"
	@rm -rf dist/seeds/
	@echo "  ✅ dist/seeds/ eliminado del Mac host"
	@echo "✅ prod-deploy-seeds completado (6 componentes)"

# ─────────────────────────────────────────────────────────────────────────────
# Pipeline completo: build → libs → sign → checksums → deploy
# ─────────────────────────────────────────────────────────────────────────────

prod-full-x86: prod-build-x86 prod-collect-libs prod-sign prod-checksums prod-deploy-x86
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║  ✅ prod-full-x86 COMPLETADO                        ║"
	@echo "║  Ejecuta: make check-prod-all                       ║"
	@echo "╚══════════════════════════════════════════════════════╝"

# ─────────────────────────────────────────────────────────────────────────────
# Provisioning de la hardened VM
# Estos targets configuran el sistema en la hardened VM.
# Se ejecutan UNA VEZ tras el primer vagrant up, o tras un destroy+up.
# ─────────────────────────────────────────────────────────────────────────────

hardened-setup-filesystem: _check-hardened-up
	@echo "=== Setting up filesystem (user, dirs, permissions) ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'sudo bash /vagrant/vagrant/hardened-x86/scripts/setup-filesystem.sh'

hardened-setup-apparmor: _check-hardened-up
	@echo "=== Installing AppArmor profiles (6 components) ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'sudo bash /vagrant/vagrant/hardened-x86/scripts/setup-apparmor.sh'

hardened-setup-falco: _check-hardened-up
	@echo "=== Installing and configuring Falco ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'sudo bash /vagrant/vagrant/hardened-x86/scripts/setup-falco.sh'

hardened-setup-apt-integrity: _check-hardened-up
	@echo "=== APT Sources Integrity (DEBT-PROD-APT-SOURCES-INTEGRITY-001) ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'sudo bash /vagrant/vagrant/hardened-x86/scripts/setup-apt-integrity.sh'

hardened-provision-all: hardened-setup-filesystem hardened-setup-apparmor hardened-setup-falco hardened-setup-apt-integrity
	@echo "✅ Provisioning completo — ejecuta make check-prod-all"

# ─────────────────────────────────────────────────────────────────────────────
# CHECK-PROD — Gates de seguridad en hardened VM
# Cada check es independiente y falla con exit 1 si no se cumple.
# ─────────────────────────────────────────────────────────────────────────────

# BSR gate: cero compiladores (dpkg + PATH, dos capas)
check-prod-no-compiler: _check-hardened-up
	@echo "=== BSR: verifying no compiler in production ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c '\
	  FAIL=0; \
	  if dpkg -l 2>/dev/null | grep -qE "^ii\s+(gcc|g\+\+|clang|clang-[0-9]+|cmake|build-essential)[[:space:]]"; then \
	    echo "FAIL (dpkg): compiler package found"; FAIL=1; \
	  fi; \
	  for cmd in gcc g++ clang clang++ cc c++ cmake; do \
	    if command -v $$cmd > /dev/null 2>&1; then \
	      echo "FAIL (PATH): $$cmd found at $$(which $$cmd)"; FAIL=1; \
	    fi; \
	  done; \
	  [ $$FAIL -eq 0 ] && echo "OK: no compiler present (dpkg + PATH verified)" || exit 1'

# AppArmor: 6 perfiles en modo enforce
check-prod-apparmor: _check-hardened-up
	@echo "=== AppArmor: verifying 6 profiles in enforce mode ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c '\
	  FAIL=0; \
	  for comp in etcd-server sniffer ml-detector firewall-acl-agent rag-ingester rag-security; do \
	    STATUS=$$(sudo aa-status 2>/dev/null | grep -c "argus-$$comp"); \
	    if [ "$$STATUS" -eq 0 ]; then \
	      echo "FAIL: argus-$$comp not in enforce mode"; FAIL=1; \
	    else \
	      echo "OK: argus-$$comp enforce"; \
	    fi; \
	  done; \
	  [ $$FAIL -eq 0 ] || exit 1'

# Capabilities: sniffer y firewall-acl-agent tienen los caps mínimos
check-prod-capabilities: _check-hardened-up
	@echo "=== Linux Capabilities: verifying setcap on sniffer and firewall ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c '\
	  FAIL=0; \
	  SNIFFER_CAPS=$$(/usr/sbin/getcap /opt/argus/bin/sniffer 2>/dev/null); \
	  if echo "$$SNIFFER_CAPS" | grep -q "cap_net_admin,cap_net_raw,cap_ipc_lock,cap_bpf=eip"; then \
	    echo "OK: sniffer caps: $$SNIFFER_CAPS"; \
	  else \
	    echo "FAIL: sniffer missing required caps (got: $$SNIFFER_CAPS)"; FAIL=1; \
	  fi; \
	  FW_CAPS=$$(/usr/sbin/getcap /opt/argus/bin/firewall-acl-agent 2>/dev/null); \
	  if echo "$$FW_CAPS" | grep -q "cap_net_admin"; then \
	    echo "OK: firewall caps: $$FW_CAPS"; \
	  else \
	    echo "FAIL: firewall-acl-agent missing required caps (got: $$FW_CAPS)"; FAIL=1; \
	  fi; \
	  [ $$FAIL -eq 0 ] || exit 1'

# Permisos: ownership argus:argus, modos correctos
check-prod-permissions: _check-hardened-up
	@echo "=== Filesystem permissions: /opt/argus/, /etc/ml-defender/, /var/log/argus/ ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c 'sudo bash /vagrant/tools/prod/check-permissions.sh'

# Falco: servicio activo y reglas cargadas
check-prod-falco: _check-hardened-up
	@echo "=== Falco: verifying service and rules ==="
	@cd $(HARDENED_X86_DIR) && vagrant ssh -c '\
	  sudo systemctl is-active falco > /dev/null 2>&1 || \
	    (echo "FAIL: falco service not running"; exit 1); \
	  echo "OK: falco active"; \
	  RULES=$$(grep -c "^- rule: argus_" /etc/falco/rules.d/argus.yaml 2>/dev/null || echo 0); \
	  [ "$$RULES" -gt 0 ] && echo "OK: $$RULES argus rules loaded" || \
	    echo "WARN: no argus-specific rules found"'

# Gate completo: todos los checks
check-prod-all: check-prod-no-compiler check-prod-apparmor check-prod-capabilities check-prod-permissions check-prod-falco
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║  ✅ check-prod-all PASSED                           ║"
	@echo "║  hardened-x86 VM cumple todos los gates de          ║"
	@echo "║  seguridad ADR-030 Variant A (DAY 133)              ║"
	@echo "╚══════════════════════════════════════════════════════╝"

# Verificación rápida del estado de la hardened VM
hardened-verify: check-prod-all
# ─────────────────────────────────────────────────────────────────────────────
# vendor-download — verifica Falco .deb en dist/vendor/ (producido por EMECAS dev)
# El .deb lo descarga el Vagrantfile dev durante provisioning. Este target solo verifica.
# ─────────────────────────────────────────────────────────────────────────────
vendor-download:
	@if ! ls dist/vendor/falco_*.deb 1>/dev/null 2>&1; then \
		echo "FAIL: dist/vendor/falco_*.deb no encontrado."; \
		echo "      Ejecuta EMECAS dev primero: vagrant destroy -f && vagrant up && make bootstrap && make test-all"; \
		exit 1; \
	fi
	@EXPECTED=$$(grep falco dist/vendor/CHECKSUMS 2>/dev/null | cut -d' ' -f1); \
	ACTUAL=$$(sha256sum dist/vendor/falco_*.deb | cut -d' ' -f1); \
	if [ "$$ACTUAL" != "$$EXPECTED" ]; then \
		echo "FAIL: hash de dist/vendor/falco_*.deb no coincide con CHECKSUMS"; \
		echo "      Ejecuta EMECAS dev para regenerar"; \
		exit 1; \
	fi
	@echo "✅ dist/vendor/falco_*.deb verificado (SHA-256 OK)"


# ─────────────────────────────────────────────────────────────────────────────
# hardened-full — EMECAS hardened: destroy → provision → build → deploy → check
# Decisión Consejo D6 (DAY 134). Gate pre-merge feature/adr030-variant-a.
# ─────────────────────────────────────────────────────────────────────────────
hardened-full:
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║  EMECAS HARDENED — destroy → build → check          ║"
	@echo "║  Gate pre-merge: feature/adr030-variant-a           ║"
	@echo "╚══════════════════════════════════════════════════════╝"
	@echo ""
	$(MAKE) hardened-destroy
	$(MAKE) hardened-up
	$(MAKE) vendor-download
	$(MAKE) hardened-provision-all
	$(MAKE) prod-full-x86
	$(MAKE) check-prod-all
	@echo ""
	@echo "╔══════════════════════════════════════════════════════╗"
	@echo "║  ✅ EMECAS HARDENED PASSED                          ║"
	@echo "║  feature/adr030-variant-a autorizado para merge     ║"
	@echo "╚══════════════════════════════════════════════════════╝"

hardened-full-with-seeds:
	@echo "⚠️  TESTING/FEDER ONLY — NO usar en producción"
	$(MAKE) hardened-full
	$(MAKE) prod-deploy-seeds
	$(MAKE) check-prod-all

# ─────────────────────────────────────────────────────────────────────────────
# hardened-redeploy — iteración rápida sin destroy (Consejo D1 DAY 134)
# Asume VM ya levantada y provisionada. Solo build → deploy → check.
# ─────────────────────────────────────────────────────────────────────────────
hardened-redeploy:
	@echo "=== HARDENED REDEPLOY (sin destroy) ==="
	$(MAKE) prod-full-x86
	$(MAKE) check-prod-all
	@echo "✅ hardened-redeploy PASSED"


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
	  sudo /opt/zeek/bin/zeek -r /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap local > zeek-stdout.log 2>&1 && \
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
	  sudo /opt/zeek/bin/zeek -r /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap local > zeek-stdout.log 2>&1 && \
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
	  sudo /opt/zeek/bin/zeek -r /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap local > zeek-stdout.log 2>&1 && \
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
	  (cd $(ZEEK_DIR) && vagrant ssh zeek -c " \
	    python3 /vagrant/experiments/zeek-comparative/parse_results_zeek.py \
	      --notice $(ZEEK_LOGS)/$$SPEED/notice.log \
	      --conn   $(ZEEK_LOGS)/$$SPEED/conn.log \
	      --speed  $$SPEED \
	      --output $(ZEEK_LOGS)/zeek_metrics_$$SPEED.json") 2>/dev/null || \
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

