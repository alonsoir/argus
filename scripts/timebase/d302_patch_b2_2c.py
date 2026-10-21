#!/usr/bin/env python3
# DAY302 tanda b2-2c [DDOS-MITIGACION-B2C-D302]: decision de Alonso DAY302 -> en dry_run el registro de eventos
# tambien guarda los RENOVAR (DRY_RUN_RENEW). Activo: BLOCKED / BLOCK_RENEWED. Uso: --check | --apply
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "firewall-acl-agent/src/api/zmq_subscriber.cpp"
MARCA = "[DDOS-MITIGACION-B2C-D302]"

OLD = r'''                    if (bloquear || !config_.dry_run) {  // D1+D2: en dry_run solo BLOQUEAR (una vez por origen y episodio)
                        const std::string accion_reg =
                            config_.dry_run ? "DRY_RUN_BLOCK" : (bloquear ? "BLOCKED" : "BLOCK_RENEWED");
'''
NEW = r'''                    {  // [DDOS-MITIGACION-B2C-D302] D1: se registra TODA accion (Alonso DAY302: tambien RENOVAR en dry_run)
                        const std::string accion_reg = config_.dry_run
                            ? (bloquear ? "DRY_RUN_BLOCK" : "DRY_RUN_RENEW")
                            : (bloquear ? "BLOCKED" : "BLOCK_RENEWED");
'''


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d302_patch_b2_2c.py --check | --apply")
        return 2
    txt = P.read_text(encoding="utf-8")
    if MARCA in txt:
        print("YA APLICADO")
        return 1
    n = txt.count(OLD)
    print(f"ancla: {n} coincidencia(s) en {P.relative_to(ROOT)}")
    if n != 1:
        print("CHECK FALLA")
        return 1
    if sys.argv[1] == "--check":
        print("CHECK OK: nada escrito")
        return 0
    P.write_text(txt.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"escrito {P}\nAPPLY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
