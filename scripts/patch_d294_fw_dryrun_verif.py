#!/usr/bin/env python3
"""DAY294 — patcher atómico (todo o nada) [FW-DRYRUN-VERIF-D294] sobre firewall-acl-agent/src/main.cpp.
Medido DAY294: con dry_run=true el firewall NO crea los ipsets ("[DRY-RUN] Would execute: ipset create"), pero la
verificación del Day 52 exigía que existieran en el kernel -> [FATAL] IPSet does not exist y el proceso moría.
Ayer no se vio porque los ipsets seguían en el kernel de corridas anteriores con dry_run=false; tras rearrancar la VM,
la sombra DDoS no llegaba a arrancar. Arreglo: en dry_run la verificación se omite con aviso visible y el arranque
sigue; en modo real, el mismo FATAL que antes.
Uso: --check | --apply. Idempotente por la marca. No commitea."""
import sys
from pathlib import Path

MARK = "[FW-DRYRUN-VERIF-D294]"
F = Path("/vagrant/firewall-acl-agent/src/main.cpp")

OLD = ("            if (!exists) {\n"
       "                FIREWALL_LOG_CRASH(\"IPSet verification failed\",\n")
NEW = ("            if (!exists && config.operation.dry_run) {  // [FW-DRYRUN-VERIF-D294] en dry_run no se crean: no es fallo\n"
       "                FIREWALL_LOG_INFO(\"IPSet verification skipped (dry-run: ipset not created)\",\n"
       "                    \"logical_name\", name,\n"
       "                    \"set_name\", ipset_cfg.set_name);\n"
       "                std::cout << \"[DRY-RUN] verificación de ipset omitida (no se crea en dry_run): \"\n"
       "                          << ipset_cfg.set_name << std::endl;\n"
       "            } else if (!exists) {\n"
       "                FIREWALL_LOG_CRASH(\"IPSet verification failed\",\n")


def fail(m):
    print("ABORTA:", m); sys.exit(1)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        fail("uso: --check | --apply")
    t = F.read_text(encoding="utf-8")
    if MARK in t:
        print("YA APLICADO (marca %s presente). Nada que hacer." % MARK); return
    c = t.count(OLD)
    if c != 1:
        fail("ancla encontrada %d veces" % c)
    n = t.replace(OLD, NEW)
    if sys.argv[1] == "--check":
        print("CHECK OK: ancla única; +%d líneas." % (n.count("\n") - t.count("\n"))); return
    tmp = F.with_name(F.name + ".d294tmp")
    tmp.write_text(n, encoding="utf-8")
    tmp.replace(F)
    print("APLICADO %s en %s" % (MARK, F))


if __name__ == "__main__":
    main()
