#!/usr/bin/env python3
"""
fix_zeek_makefile.py — aRGus NDR DAY 147
Parchea dos bugs en los targets de Zeek del Makefile:

  Bug 1: zeek -i eth2 necesita sudo (pcap raw socket permission)
  Bug 2: cd $(ZEEK_DIR) dentro del for loop acumula path en iteraciones 2 y 3

Uso:
    python3 fix_zeek_makefile.py [--makefile PATH] [--dry-run]
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime

# ─── Bug 1: sudo en los tres replay targets ───────────────────────────────────
# El mismo patrón aparece tres veces (10/50/100 Mbps)

OLD_ZEEK_CMD = "nohup zeek -i eth2 local > zeek-stdout.log 2>&1 & \\"
NEW_ZEEK_CMD = "nohup sudo /opt/zeek/bin/zeek -i eth2 local > zeek-stdout.log 2>&1 & \\"

# ─── Bug 2: cd sin subshell en experiment-zeek-results ───────────────────────

OLD_CD = "  cd $(ZEEK_DIR) && vagrant ssh zeek -c \\"
NEW_CD = "  (cd $(ZEEK_DIR) && vagrant ssh zeek -c \\"

# La clausura del subshell va al final del bloque || — necesitamos cerrar el )
# El bloque completo original:
OLD_RESULTS_BLOCK = """\
	  cd $(ZEEK_DIR) && vagrant ssh zeek -c " \\
	    python3 /vagrant/experiments/zeek-comparative/parse_results_zeek.py \\
	      --notice $(ZEEK_LOGS)/$$SPEED/notice.log \\
	      --conn   $(ZEEK_LOGS)/$$SPEED/conn.log \\
	      --speed  $$SPEED \\
	      --output $(ZEEK_LOGS)/zeek_metrics_$$SPEED.json" 2>/dev/null || \\
	  echo "  ⚠️  Logs no disponibles para $$SPEED"; \\"""

NEW_RESULTS_BLOCK = """\
	  (cd $(ZEEK_DIR) && vagrant ssh zeek -c " \\
	    python3 /vagrant/experiments/zeek-comparative/parse_results_zeek.py \\
	      --notice $(ZEEK_LOGS)/$$SPEED/notice.log \\
	      --conn   $(ZEEK_LOGS)/$$SPEED/conn.log \\
	      --speed  $$SPEED \\
	      --output $(ZEEK_LOGS)/zeek_metrics_$$SPEED.json") 2>/dev/null || \\
	  echo "  ⚠️  Logs no disponibles para $$SPEED"; \\"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--makefile", default="Makefile")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    makefile = Path(args.makefile)
    if not makefile.exists():
        print(f"❌ No se encuentra: {makefile}")
        sys.exit(1)

    content = makefile.read_text(encoding="utf-8")

    # Contar ocurrencias antes
    n_sudo   = content.count(OLD_ZEEK_CMD)
    n_cd     = content.count(OLD_RESULTS_BLOCK)

    print(f"📄 Makefile: {makefile.resolve()}")
    print(f"   Bug 1 (sudo zeek): {n_sudo} ocurrencias encontradas (esperadas: 3)")
    print(f"   Bug 2 (cd subshell): {n_cd} ocurrencias encontradas (esperada: 1)")

    if n_sudo == 0 and n_cd == 0:
        print("\n✅ Nada que parchear — ya está aplicado o los targets no están presentes.")
        return

    if args.dry_run:
        print("\n🔍 DRY-RUN — sin cambios en disco.")
        if n_sudo:
            print(f"   Reemplazaría '{OLD_ZEEK_CMD}' → '{NEW_ZEEK_CMD}' ({n_sudo}×)")
        if n_cd:
            print(f"   Reemplazaría bloque cd → subshell (cd ...) (1×)")
        return

    # Backup
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = makefile.with_suffix(f".bak_{ts}")
    shutil.copy2(makefile, bak)
    print(f"\n📦 Backup: {bak.name}")

    # Aplicar Bug 1 (todas las ocurrencias)
    new_content = content.replace(OLD_ZEEK_CMD, NEW_ZEEK_CMD)
    applied_sudo = new_content.count(NEW_ZEEK_CMD)
    print(f"✅ Bug 1 (sudo): {applied_sudo} ocurrencias parcheadas")

    # Aplicar Bug 2 (una ocurrencia)
    new_content = new_content.replace(OLD_RESULTS_BLOCK, NEW_RESULTS_BLOCK, 1)
    applied_cd = 1 if OLD_RESULTS_BLOCK not in new_content else 0
    print(f"{'✅' if applied_cd else '❌'} Bug 2 (cd subshell): "
          f"{'parcheado' if applied_cd else 'NO parcheado — revisa manualmente'}")

    makefile.write_text(new_content, encoding="utf-8")

    # Verificación
    final = makefile.read_text(encoding="utf-8")
    ok = (
            "sudo /opt/zeek/bin/zeek" in final
            and "(cd $(ZEEK_DIR)" in final
            and OLD_ZEEK_CMD not in final
            and OLD_RESULTS_BLOCK not in final
    )
    if ok:
        print("\n✅ Parche verificado — listo para relanzar experiment-zeek-run")
    else:
        print("\n⚠️  Verificación parcial — revisa el Makefile manualmente")


if __name__ == "__main__":
    main()