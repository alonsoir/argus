#!/usr/bin/env python3
"""
fix_pipeline_status.py — DAY 147 aRGus NDR
Parchea el target pipeline-status del Makefile añadiendo pgrep como fallback
a tmux has-session para todos los componentes.

Bug: proceso sniffer (y cualquier otro) puede sobrevivir como huérfano fuera
de tmux → pipeline-health lo ve RUNNING, pipeline-status lo ve STOPPED.

Fix (Opción A — OR lógico): tmux has-session OR pgrep. Si el proceso corre
fuera de tmux, lo marca RUNNING igualmente.

Uso:
    python3 fix_pipeline_status.py [--makefile PATH] [--dry-run]

Por defecto busca ./Makefile en el directorio actual.
"""

import re
import shutil
import argparse
import sys
from pathlib import Path
from datetime import datetime

# ── Bloque antiguo (exactamente como está en el Makefile) ────────────────────
OLD_BLOCK = r"""pipeline-status:
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║  📊 ML Defender Pipeline Status (via TMUX)                ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@vagrant ssh -c "tmux has-session -t etcd-server 2>/dev/null && echo '  ✅ etcd-server:   RUNNING' || echo '  ❌ etcd-server:   STOPPED'"
	@vagrant ssh -c "tmux has-session -t rag-security 2>/dev/null && echo '  ✅ rag-security:  RUNNING' || echo '  ❌ rag-security:  STOPPED'"
	@vagrant ssh -c "tmux has-session -t rag-ingester 2>/dev/null && echo '  ✅ rag-ingester:  RUNNING' || echo '  ❌ rag-ingester:  STOPPED'"
	@vagrant ssh -c "tmux has-session -t ml-detector 2>/dev/null && echo '  ✅ ml-detector:   RUNNING' || echo '  ❌ ml-detector:   STOPPED'"
	@vagrant ssh -c " \
	  EBPF=$$(tmux has-session -t sniffer        2>/dev/null && echo 1 || echo 0); \
	  PCAP=$$(tmux has-session -t sniffer-libpcap 2>/dev/null && echo 1 || echo 0); \
	  if   [ \$$EBPF -eq 1 ] && [ \$$PCAP -eq 0 ]; then \
	    echo '  ✅ sniffer:       RUNNING [Variant A — eBPF]'; \
	  elif [ \$$EBPF -eq 0 ] && [ \$$PCAP -eq 1 ]; then \
	    echo '  ✅ sniffer:       RUNNING [Variant B — libpcap]'; \
	  elif [ \$$EBPF -eq 1 ] && [ \$$PCAP -eq 1 ]; then \
	    echo '  🚨 sniffer:       INVARIANT VIOLATION — eBPF + libpcap SIMULTANEOUS'; \
	  else \
	    echo '  ❌ sniffer:       STOPPED'; \
	  fi"
	@vagrant ssh -c "tmux has-session -t firewall 2>/dev/null && echo '  ✅ firewall:      RUNNING' || echo '  ❌ firewall:      STOPPED'"
	@echo "╚════════════════════════════════════════════════════════════╝"
"""

# ── Bloque nuevo (tmux OR pgrep para todos los componentes) ─────────────────
# Nota: los tabuladores son tabuladores reales (\t), no espacios.
# firewall-acl-agent es el nombre real del binario (≠ nombre sesión tmux).
NEW_BLOCK = """pipeline-status:
\t@echo ""
\t@echo "╔════════════════════════════════════════════════════════════╗"
\t@echo "║  📊 ML Defender Pipeline Status (via TMUX + pgrep)        ║"
\t@echo "╚════════════════════════════════════════════════════════════╝"
\t@vagrant ssh -c "( tmux has-session -t etcd-server 2>/dev/null || pgrep -x etcd-server >/dev/null 2>&1 ) && echo '  ✅ etcd-server:   RUNNING' || echo '  ❌ etcd-server:   STOPPED'"
\t@vagrant ssh -c "( tmux has-session -t rag-security 2>/dev/null || pgrep -x rag-security >/dev/null 2>&1 ) && echo '  ✅ rag-security:  RUNNING' || echo '  ❌ rag-security:  STOPPED'"
\t@vagrant ssh -c "( tmux has-session -t rag-ingester 2>/dev/null || pgrep -x rag-ingester >/dev/null 2>&1 ) && echo '  ✅ rag-ingester:  RUNNING' || echo '  ❌ rag-ingester:  STOPPED'"
\t@vagrant ssh -c "( tmux has-session -t ml-detector 2>/dev/null || pgrep -x ml-detector >/dev/null 2>&1 ) && echo '  ✅ ml-detector:   RUNNING' || echo '  ❌ ml-detector:   STOPPED'"
\t@vagrant ssh -c " \\
\t  EBPF=0; PCAP=0; \\
\t  tmux has-session -t sniffer         2>/dev/null && EBPF=1; \\
\t  tmux has-session -t sniffer-libpcap 2>/dev/null && PCAP=1; \\
\t  pgrep -x sniffer         >/dev/null 2>&1 && EBPF=1; \\
\t  pgrep -x sniffer-libpcap >/dev/null 2>&1 && PCAP=1; \\
\t  if   [ \\$$EBPF -eq 1 ] && [ \\$$PCAP -eq 0 ]; then \\
\t    echo '  ✅ sniffer:       RUNNING [Variant A — eBPF]'; \\
\t  elif [ \\$$EBPF -eq 0 ] && [ \\$$PCAP -eq 1 ]; then \\
\t    echo '  ✅ sniffer:       RUNNING [Variant B — libpcap]'; \\
\t  elif [ \\$$EBPF -eq 1 ] && [ \\$$PCAP -eq 1 ]; then \\
\t    echo '  🚨 sniffer:       INVARIANT VIOLATION — eBPF + libpcap SIMULTANEOUS'; \\
\t  else \\
\t    echo '  ❌ sniffer:       STOPPED'; \\
\t  fi"
\t@vagrant ssh -c "( tmux has-session -t firewall 2>/dev/null || pgrep -x firewall-acl-agent >/dev/null 2>&1 ) && echo '  ✅ firewall:      RUNNING' || echo '  ❌ firewall:      STOPPED'"
\t@echo "╚════════════════════════════════════════════════════════════╝"
"""


def patch_makefile(makefile_path: Path, dry_run: bool = False) -> bool:
    content = makefile_path.read_text(encoding="utf-8")

    if OLD_BLOCK not in content:
        # Intento alternativo: buscar por regex en caso de diferencias de espacio
        print("⚠️  Bloque exacto no encontrado — intentando búsqueda por regex...")
        pattern = re.compile(
            r"^pipeline-status:\n"
            r"(\t@.*\n)*",
            re.MULTILINE,
        )
        match = pattern.search(content)
        if match:
            print(f"   Encontrado por regex en posición {match.start()}–{match.end()}")
            print("   Mostrando bloque detectado:\n")
            print(repr(match.group()))
            print("\n❌ El bloque no coincide exactamente con el esperado.")
            print("   Edita OLD_BLOCK en el script para que coincida y vuelve a ejecutar.")
            return False
        else:
            print("❌ No se encontró ningún target pipeline-status: en el Makefile.")
            return False

    if dry_run:
        print("🔍 DRY-RUN — cambios que se aplicarían:\n")
        print("── OLD ──────────────────────────────────────────")
        print(OLD_BLOCK)
        print("── NEW ──────────────────────────────────────────")
        print(NEW_BLOCK)
        print("─────────────────────────────────────────────────")
        print("✅ Dry-run OK — sin cambios en disco.")
        return True

    # Backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = makefile_path.with_suffix(f".bak_{ts}")
    shutil.copy2(makefile_path, backup_path)
    print(f"📦 Backup: {backup_path}")

    new_content = content.replace(OLD_BLOCK, NEW_BLOCK, 1)

    if new_content == content:
        print("❌ replace() no produjo cambios — algo fue mal.")
        return False

    makefile_path.write_text(new_content, encoding="utf-8")
    print(f"✅ Makefile parcheado: {makefile_path}")
    return True


def verify_patch(makefile_path: Path) -> bool:
    content = makefile_path.read_text(encoding="utf-8")
    checks = [
        ("pgrep -x etcd-server",         "etcd-server fallback"),
        ("pgrep -x rag-security",         "rag-security fallback"),
        ("pgrep -x rag-ingester",         "rag-ingester fallback"),
        ("pgrep -x ml-detector",          "ml-detector fallback"),
        ("pgrep -x sniffer",              "sniffer eBPF fallback"),
        ("pgrep -x sniffer-libpcap",      "sniffer libpcap fallback"),
        ("pgrep -x firewall-acl-agent",   "firewall fallback"),
        ("via TMUX + pgrep",              "título actualizado"),
    ]
    print("\n🔍 Verificando parche aplicado:")
    all_ok = True
    for needle, label in checks:
        if needle in content:
            print(f"  ✅ {label}")
        else:
            print(f"  ❌ FALTA: {label}  ({needle!r})")
            all_ok = False
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Parchea pipeline-status en el Makefile de aRGus NDR (DAY 147)"
    )
    parser.add_argument(
        "--makefile",
        default="Makefile",
        help="Ruta al Makefile (por defecto: ./Makefile)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra los cambios sin escribir en disco",
    )
    args = parser.parse_args()

    makefile_path = Path(args.makefile)
    if not makefile_path.exists():
        print(f"❌ No se encuentra: {makefile_path}")
        sys.exit(1)

    print(f"📄 Makefile: {makefile_path.resolve()}")
    print(f"   Tamaño: {makefile_path.stat().st_size:,} bytes\n")

    ok = patch_makefile(makefile_path, dry_run=args.dry_run)
    if not ok:
        sys.exit(1)

    if not args.dry_run:
        if not verify_patch(makefile_path):
            print("\n❌ Verificación fallida — revisa el Makefile manualmente.")
            sys.exit(1)
        print("\n✅ Parche aplicado y verificado.")
        print("   Siguiente: make pipeline-status")


if __name__ == "__main__":
    main()