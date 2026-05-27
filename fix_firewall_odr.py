#!/usr/bin/env python3
"""
DEBT-FIREWALL-HTTPLIB-ODR-001
Fix: AlertClient como miembro directo en batch_processor.hpp incluye httplib.h
en todas las translation units → ODR violation con libetcd_client.so → SIGSEGV.
Solución: pimpl mínimo con unique_ptr<AlertClient>.
"""
import sys
import shutil
from pathlib import Path

HPP = Path("firewall-acl-agent/include/firewall/batch_processor.hpp")
CPP = Path("firewall-acl-agent/src/core/batch_processor.cpp")

def check_files():
    for f in [HPP, CPP]:
        if not f.exists():
            print(f"ERROR: no se encuentra {f}")
            sys.exit(1)
    print("✅ Ficheros encontrados")

def backup(path):
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    print(f"   backup → {bak}")

def fix_hpp():
    text = HPP.read_text()

    # 1. Eliminar #define CPPHTTPLIB_OPENSSL_SUPPORT y #include "alert_client.hpp"
    old = '#define CPPHTTPLIB_OPENSSL_SUPPORT\n#include "alert_client.hpp"'
    new = '// alert_client.hpp movido al .cpp (DEBT-FIREWALL-HTTPLIB-ODR-001 — pimpl)\n#include <memory>'
    if old not in text:
        print("   WARN: bloque CPPHTTPLIB+alert_client no encontrado, buscando solo include...")
        old = '#include "alert_client.hpp"'
        new = '// alert_client.hpp movido al .cpp (DEBT-FIREWALL-HTTPLIB-ODR-001 — pimpl)\n#include <memory>'
    assert old in text, "ERROR: no se encontró el include de alert_client.hpp en .hpp"
    text = text.replace(old, new, 1)

    # 2. Añadir forward declaration justo antes de namespace mldefender
    fwd = '// Forward declaration — evita incluir httplib.h en este header (ODR)\nnamespace argus { class AlertClient; }\n\n'
    marker = 'namespace mldefender::firewall {'
    assert marker in text, "ERROR: no se encontró namespace mldefender::firewall"
    text = text.replace(marker, fwd + marker, 1)

    # 3. Cambiar miembro directo a unique_ptr
    old_member = '    argus::AlertClient   alert_client_{nlohmann::json{{"alerting", {{"enabled", false}}}}};  ///< SOS alerting'
    new_member = '    std::unique_ptr<argus::AlertClient> alert_client_;  ///< SOS alerting (pimpl — ODR fix)'
    assert old_member in text, "ERROR: no se encontró la declaración del miembro alert_client_"
    text = text.replace(old_member, new_member, 1)

    HPP.write_text(text)
    print("✅ batch_processor.hpp parcheado")

def fix_cpp():
    text = CPP.read_text()

    # 1. Añadir include de alert_client.hpp al principio del .cpp
    marker = '#include "firewall/batch_processor.hpp"'
    assert marker in text, "ERROR: no se encontró #include batch_processor.hpp en .cpp"
    new_include = '#include "firewall/batch_processor.hpp"\n#include "alert_client.hpp"  // DEBT-FIREWALL-HTTPLIB-ODR-001: include aquí, no en header'
    text = text.replace(marker, new_include, 1)

    # 2. Cambiar inicialización en constructor
    old_init = '    , alert_client_(config.alerting_json)'
    new_init = '    , alert_client_(std::make_unique<argus::AlertClient>(config.alerting_json))'
    assert old_init in text, "ERROR: no se encontró la inicialización de alert_client_ en constructor"
    text = text.replace(old_init, new_init, 1)

    # 3. Cambiar llamada de . a ->
    old_call = '    alert_client_.send_sos({'
    new_call = '    alert_client_->send_sos({'
    assert old_call in text, "ERROR: no se encontró alert_client_.send_sos"
    text = text.replace(old_call, new_call, 1)

    CPP.write_text(text)
    print("✅ batch_processor.cpp parcheado")

def verify():
    hpp = HPP.read_text()
    cpp = CPP.read_text()

    checks = [
        ("hpp NO tiene httplib.h directo",       'httplib' not in hpp),
        ("hpp NO tiene alert_client.hpp directo", '#include "alert_client.hpp"' not in hpp),
        ("hpp tiene forward declaration argus",   'namespace argus { class AlertClient; }' in hpp),
        ("hpp tiene unique_ptr<AlertClient>",     'unique_ptr<argus::AlertClient>' in hpp),
        ("cpp tiene #include alert_client.hpp",   '#include "alert_client.hpp"' in cpp),
        ("cpp tiene make_unique",                 'make_unique<argus::AlertClient>' in cpp),
        ("cpp usa -> en send_sos",                'alert_client_->send_sos' in cpp),
    ]

    all_ok = True
    for desc, result in checks:
        icon = "✅" if result else "❌"
        print(f"   {icon} {desc}")
        if not result:
            all_ok = False

    return all_ok

def main():
    print("=" * 60)
    print("DEBT-FIREWALL-HTTPLIB-ODR-001 — pimpl fix")
    print("=" * 60)

    check_files()

    print("\n📦 Creando backups...")
    backup(HPP)
    backup(CPP)

    print("\n🔧 Aplicando fix en .hpp...")
    fix_hpp()

    print("\n🔧 Aplicando fix en .cpp...")
    fix_cpp()

    print("\n🔍 Verificando resultado...")
    ok = verify()

    print()
    if ok:
        print("✅ FIX APLICADO CORRECTAMENTE")
        print()
        print("Siguiente paso:")
        print("  vagrant ssh -c 'cd /vagrant && make firewall-build'")
        print("  vagrant ssh -c 'cd /vagrant && make pipeline-start'")
        print("  vagrant ssh -c 'pgrep -a firewall-acl-agent'")
    else:
        print("❌ VERIFICACIÓN FALLIDA — revisa los errores arriba")
        print("   Los backups .bak están disponibles para revertir")
        sys.exit(1)

if __name__ == "__main__":
    main()