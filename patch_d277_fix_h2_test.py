#!/usr/bin/env python3
"""patch_d277_fix_h2_test.py -- DAY277: el test H2 asumia que flush() vacia pending_ips_.
MEDIDO: un flush fallido CONSERVA la cola (batch_processor.cpp, rama 'Flush failed -
keep IPs in pending set'). Se encolan las 3 IPs y se hace UN flush: el bucle de
flush_internal (donde vivia H2) recorre todas las IPs antes de add_batch."""
import pathlib, sys
F = pathlib.Path("firewall-acl-agent/tests/unit/test_batch_processor_recidivism.cpp")
MARKER = "DAY277-H2-TEST-FIX"
OLD = """    for (const char* ip : {"198.51.100.1", "198.51.100.2", "198.51.100.3"}) {
        processor_->add_ip(ip);
        ASSERT_EQ(processor_->get_pending_count(), 1u)
            << "add_ip no encolo " << ip << " -- el test no estaria probando nada";
        processor_->flush();
    }
"""
NEW = """    // DAY277-H2-TEST-FIX: un flush fallido conserva pending_ips_ (medido), asi
    // que no se asume nada sobre su exito. El bucle de flush_internal (donde
    // vivia H2) recorre todas las IPs pendientes ANTES de llamar a add_batch.
    for (const char* ip : {"198.51.100.1", "198.51.100.2", "198.51.100.3"}) {
        processor_->add_ip(ip);
    }
    ASSERT_EQ(processor_->get_pending_count(), 3u)
        << "add_ip no encolo las 3 IPs -- el test no estaria probando nada";
    processor_->flush();
"""
if not F.exists(): sys.exit(f"no existe {F} (¿raiz del repo?)")
t = F.read_text()
if MARKER in t: sys.exit(f"{MARKER} ya aplicado. Nada que hacer.")
n = t.count(OLD)
if n != 1: sys.exit(f"ABORTADO: ancla encontrada {n} veces (se esperaba 1). No se escribe nada.")
bak = F.with_name(F.name + ".orig_d277b")
if not bak.exists(): bak.write_text(t)
F.write_text(t.replace(OLD, NEW, 1))
print(f"parcheado: {F} (backup: {bak.name})")
