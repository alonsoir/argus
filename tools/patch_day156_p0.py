#!/usr/bin/env python3
# patch_day156_p0.py — DEBT-AUTONOMY-CRYPTO-INTEGRATION-001
# Tres operaciones: etcd-server/main.cpp, firewall main.cpp, firewall.json
# Ejecutar: vagrant ssh -c "python3 /vagrant/tools/patch_day156_p0.py"

import json, re, sys, subprocess
from pathlib import Path

OK  = "✅"
ERR = "❌"
INF = "🔧"

def fail(msg):
    print(f"{ERR} {msg}", file=sys.stderr)
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────
# 1. PATCH etcd-server/src/main.cpp
# ─────────────────────────────────────────────────────────────────
ETCD_MAIN = Path("/vagrant/etcd-server/src/main.cpp")

ETCD_INCLUDE_ANCHOR = '#include <filesystem>'
ETCD_INCLUDE_INSERT = '''#include <filesystem>
#include <vault_client/autonomy_publisher.h>
#include <vault_client/crypto_autonomy.h>'''

ETCD_SM_ANCHOR = '        std::cout << std::endl;'  # primera línea tras STEP 0 block
ETCD_SM_INSERT = '''
        // ═══════════════════════════════════════════════════════════
        // STEP 0b: CryptoAutonomyStateMachine + AutonomyPublisher (DAY 156)
        // DEBT-AUTONOMY-CRYPTO-INTEGRATION-001
        // etcd-server es el único publisher de autonomía en el nodo (Q1 DAY 155).
        // ═══════════════════════════════════════════════════════════
        const std::string autonomy_endpoint = "ipc:///run/argus/autonomy.sock";
        ml_defender::common::AutonomyPublisher autonomy_pub(
            autonomy_endpoint, "etcd-server", 0
        );
        ml_defender::CryptoAutonomy autonomy_sm(
            "etcd-server",
            autonomy_pub.make_callback()
        );
        std::cout << "✅ AutonomyPublisher + CryptoAutonomySM inicializados" << std::endl;
        std::cout << "   endpoint: " << autonomy_endpoint << std::endl;

'''

ETCD_LOOP_OLD = '''        while (g_server->is_running()) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }'''

ETCD_LOOP_NEW = '''        // ── Health-check loop con SM de autonomía (DAY 156) ──────────────
        auto   last_vault_check = std::chrono::steady_clock::now();
        bool   was_vault_healthy = true;

        while (g_server->is_running()) {
            auto now     = std::chrono::steady_clock::now();
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                               now - last_vault_check).count();

            if (elapsed >= 5) {
                const bool healthy = crypto_provider->is_healthy();
                if (!healthy && was_vault_healthy) {
                    std::cout << "[autonomy] Vault KO → AUTONOMOUS" << std::endl;
                    autonomy_sm.on_vault_unreachable();
                } else if (healthy && !was_vault_healthy) {
                    std::cout << "[autonomy] Vault OK → RECONCILING" << std::endl;
                    autonomy_sm.on_vault_restored();
                    // on_reconciliation_ok() se llamará tras validar material
                    // DEBT-CRYPTO-RECONCILIATION-001
                    autonomy_sm.on_reconciliation_ok();
                }
                was_vault_healthy = healthy;
                last_vault_check  = now;
            }

            std::this_thread::sleep_for(std::chrono::seconds(1));
        }'''

def patch_etcd_main():
    src = ETCD_MAIN.read_text()

    # Guard: no re-parchear
    if 'autonomy_publisher.h' in src:
        print(f"{OK} etcd-server/main.cpp ya parcheado — skip")
        return

    # 1a. Includes
    if ETCD_INCLUDE_ANCHOR not in src:
        fail(f"etcd-server: anchor de includes no encontrado")
    src = src.replace(ETCD_INCLUDE_ANCHOR, ETCD_INCLUDE_INSERT, 1)

    # 1b. SM instantiation — insertar ANTES del primer std::cout tras STEP 0
    anchor = '        std::cout << std::endl;\n        std::cout << "═══'
    if anchor not in src:
        fail("etcd-server: anchor STEP 1 no encontrado")
    src = src.replace(anchor, ETCD_SM_INSERT + anchor, 1)

    # 1c. Main loop con health-check
    if ETCD_LOOP_OLD not in src:
        fail("etcd-server: main loop pattern no encontrado")
    src = src.replace(ETCD_LOOP_OLD, ETCD_LOOP_NEW, 1)

    ETCD_MAIN.write_text(src)
    print(f"{OK} etcd-server/src/main.cpp parcheado")

# ─────────────────────────────────────────────────────────────────
# 2. PATCH firewall-acl-agent/src/main.cpp
# ─────────────────────────────────────────────────────────────────
FW_MAIN = Path("/vagrant/firewall-acl-agent/src/main.cpp")

FW_INCLUDE_ANCHOR = '#include "firewall/etcd_client.hpp"'
FW_INCLUDE_INSERT = '''#include "firewall/etcd_client.hpp"
#include "firewall/autonomy_subscriber.hpp"
#include "firewall/autonomy_reactor.hpp"'''

FW_REACTOR_ANCHOR = '    FIREWALL_LOG_DEBUG("Configuration phase completed successfully");'
FW_REACTOR_INSERT = '''        FIREWALL_LOG_DEBUG("Configuration phase completed successfully");

        // ═══════════════════════════════════════════════════════════
        // AUTONOMY PLANE — FirewallAutonomyReactor + AutonomySubscriber
        // DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 (DAY 156)
        // ═══════════════════════════════════════════════════════════
    FIREWALL_LOG_INFO("Initializing autonomy plane",
        "zmq_endpoint", config.autonomy.zmq_endpoint,
        "reconcile_interval_sec", config.autonomy.reconcile_interval_sec);

    mldefender::firewall::FirewallAutonomyReactor autonomy_reactor(
        config.autonomy.whitelist_cidrs,
        config.operation.dry_run
    );

    // poll_callback: consultado por el reconciliador cada reconcile_interval_sec.
    auto poll_callback = [&etcd_client]() -> mldefender::firewall::FirewallAutonomyMode {
        if (etcd_client && etcd_client->isHealthy()) {
            return mldefender::firewall::FirewallAutonomyMode::NORMAL;
        }
        return mldefender::firewall::FirewallAutonomyMode::AUTONOMOUS;
    };

    auto autonomy_sub = std::make_unique<mldefender::firewall::AutonomySubscriber>(
        autonomy_reactor,
        poll_callback,
        config.autonomy.zmq_endpoint,
        config.autonomy.reconcile_interval_sec
    );
    autonomy_sub->start();
    FIREWALL_LOG_INFO("AutonomySubscriber started",
        "endpoint", config.autonomy.zmq_endpoint);

'''

FW_STOP_ANCHOR = '        // Export final metrics'
FW_STOP_INSERT = '''        // Detener AutonomySubscriber antes de shutdown
        if (autonomy_sub && autonomy_sub->is_running()) {
            autonomy_sub->stop();
            FIREWALL_LOG_INFO("AutonomySubscriber stopped");
        }

        // Export final metrics'''

def patch_firewall_main():
    src = FW_MAIN.read_text()

    if 'autonomy_subscriber.hpp' in src:
        print(f"{OK} firewall main.cpp ya parcheado — skip")
        return

    if FW_INCLUDE_ANCHOR not in src:
        fail("firewall: anchor de includes no encontrado")
    src = src.replace(FW_INCLUDE_ANCHOR, FW_INCLUDE_INSERT, 1)

    if FW_REACTOR_ANCHOR not in src:
        fail("firewall: anchor REACTOR no encontrado")
    src = src.replace(FW_REACTOR_ANCHOR, FW_REACTOR_INSERT, 1)

    if FW_STOP_ANCHOR not in src:
        fail("firewall: anchor STOP no encontrado")
    src = src.replace(FW_STOP_ANCHOR, FW_STOP_INSERT, 1)

    FW_MAIN.write_text(src)
    print(f"{OK} firewall-acl-agent/src/main.cpp parcheado")

# ─────────────────────────────────────────────────────────────────
# 3. PATCH firewall.json — añadir zmq_endpoint a autonomy
# ─────────────────────────────────────────────────────────────────
FW_JSON = Path("/vagrant/firewall-acl-agent/config/firewall.json")

def patch_firewall_json():
    cfg = json.loads(FW_JSON.read_text())

    if "autonomy" not in cfg:
        fail("firewall.json: sección 'autonomy' no encontrada")

    if "zmq_endpoint" in cfg["autonomy"]:
        print(f"{OK} firewall.json ya tiene zmq_endpoint — skip")
        return

    cfg["autonomy"]["zmq_endpoint"] = "ipc:///run/argus/autonomy.sock"

    FW_JSON.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"{OK} firewall.json parcheado — zmq_endpoint añadido")

# ─────────────────────────────────────────────────────────────────
# 4. VERIFICACIÓN FORMAL
# ─────────────────────────────────────────────────────────────────
def verify():
    errors = []

    # etcd-server
    etcd_src = ETCD_MAIN.read_text()
    checks_etcd = [
        ("include autonomy_publisher", "autonomy_publisher.h"),
        ("include crypto_autonomy",    "crypto_autonomy.h"),
        ("AutonomyPublisher instancia", "autonomy_pub("),
        ("CryptoAutonomy instancia",    "autonomy_sm("),
        ("on_vault_unreachable",        "on_vault_unreachable()"),
        ("on_vault_restored",           "on_vault_restored()"),
        ("on_reconciliation_ok",        "on_reconciliation_ok()"),
        ("health-check loop",           "was_vault_healthy"),
    ]
    for name, token in checks_etcd:
        if token not in etcd_src:
            errors.append(f"etcd-server: falta '{name}' ({token})")
        else:
            print(f"  {OK} etcd-server: {name}")

    # firewall main
    fw_src = FW_MAIN.read_text()
    checks_fw = [
        ("include autonomy_subscriber", "autonomy_subscriber.hpp"),
        ("include autonomy_reactor",    "autonomy_reactor.hpp"),
        ("FirewallAutonomyReactor",     "FirewallAutonomyReactor autonomy_reactor"),
        ("poll_callback lambda",        "poll_callback"),
        ("AutonomySubscriber instancia","autonomy_sub"),
        ("autonomy_sub->start()",       "autonomy_sub->start()"),
        ("autonomy_sub->stop()",        "autonomy_sub->stop()"),
    ]
    for name, token in checks_fw:
        if token not in fw_src:
            errors.append(f"firewall: falta '{name}' ({token})")
        else:
            print(f"  {OK} firewall: {name}")

    # firewall.json
    cfg = json.loads(FW_JSON.read_text())
    checks_json = [
        ("zmq_endpoint presente",     "zmq_endpoint" in cfg.get("autonomy", {})),
        ("zmq_endpoint correcto",      cfg.get("autonomy", {}).get("zmq_endpoint") == "ipc:///run/argus/autonomy.sock"),
        ("whitelist_cidrs presente",   "whitelist_cidrs" in cfg.get("autonomy", {})),
        ("reconcile_interval_sec",     "reconcile_interval_sec" in cfg.get("autonomy", {})),
    ]
    for name, ok in checks_json:
        if not ok:
            errors.append(f"firewall.json: {name} — FALLO")
        else:
            print(f"  {OK} firewall.json: {name}")

    if errors:
        print(f"\n{ERR} VERIFICACIÓN FALLIDA:")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)
    else:
        print(f"\n{OK} Verificación formal completa — 0 errores")

# ─────────────────────────────────────────────────────────────────
# 5. COMPILACIÓN
# ─────────────────────────────────────────────────────────────────
def compile_component(name, build_dir, flags):
    print(f"\n{INF} Compilando {name}...")
    r = subprocess.run(
        f"cd {build_dir} && cmake .. {flags} -DBUILD_TESTS=ON 2>&1 | tail -5 && make -j$(nproc) 2>&1 | tail -20",
        shell=True, capture_output=True, text=True
    )
    print(r.stdout)
    if r.returncode != 0:
        print(r.stderr)
        fail(f"{name} compilación fallida")
    print(f"{OK} {name} compilado")

# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 — DAY 156 P0")
    print("=" * 60)

    print("\n── Fase 1: Patches ──")
    patch_etcd_main()
    patch_firewall_main()
    patch_firewall_json()

    print("\n── Fase 2: Verificación formal ──")
    verify()

    print("\n── Fase 3: Compilación ──")
    dbg = "-DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS='-std=c++20 -Wall -Wextra -Wpedantic -Werror -g -O0 -fno-omit-frame-pointer -DDEBUG'"
    compile_component(
        "etcd-server",
        "/vagrant/etcd-server/build-debug",
        dbg
    )
    compile_component(
        "firewall-acl-agent",
        "/vagrant/firewall-acl-agent/build-debug",
        dbg
    )

    print("\n" + "=" * 60)
    print(f"{OK} P0 COMPLETO — DEBT-AUTONOMY-CRYPTO-INTEGRATION-001")
    print("Siguiente: make test-all → tests E2E autonomy")
    print("=" * 60)