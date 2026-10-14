#!/usr/bin/env python3
"""[TIMEBASE-D295:FLOWSTART] flow_start_time y time_window.window_start del evento de flujo pasan a epoch
derivado (mono + ancla), como event_timestamp. Medido DAY295: el bronce correlation_v1 de aRGus llevaba
flow_start_sec ~10427 (segundos desde el arranque) mientras Suricata/Zeek y los tests van en epoch;
flow_uid (ventana en micros epoch) y ADR-057 (comparacion con ingested_at) esperan epoch.
time_window.sequence_number sigue siendo event.timestamp (contador, no instante).
Atomico: las dos anclas deben aparecer exactamente una vez. Uso: --check | --apply"""
import os
import sys
from pathlib import Path

P = Path("sniffer/src/userspace/ring_consumer.cpp")
MARCA = "[TIMEBASE-D295:FLOWSTART]"
A_FST = ("    flow_start->set_seconds(event.timestamp / 1000000000ULL);\n"
         "    flow_start->set_nanos(event.timestamp % 1000000000ULL);\n")
N_FST = ("    // [TIMEBASE-D295:FLOWSTART] epoch derivado (mono + ancla), como event_timestamp: el bronce\n"
         "    // correlation_v1, flow_uid y ADR-057 esperan epoch. mono = epoch - time_context.wall_anchor_ns.\n"
         "    const uint64_t fst_epoch_ns = ::argus::timebase::epoch_ns(\n"
         "        event.timestamp, tb_anchor_ns_.load(std::memory_order_relaxed));\n"
         "    flow_start->set_seconds(static_cast<int64_t>(fst_epoch_ns / 1000000000ULL));\n"
         "    flow_start->set_nanos(static_cast<int32_t>(fst_epoch_ns % 1000000000ULL));\n")
A_WIN = ("    window_start->set_seconds(event.timestamp / 1000000000ULL);\n"
         "    window_start->set_nanos(event.timestamp % 1000000000ULL);\n")
N_WIN = ("    window_start->set_seconds(static_cast<int64_t>(fst_epoch_ns / 1000000000ULL));  // [TIMEBASE-D295:FLOWSTART]\n"
         "    window_start->set_nanos(static_cast<int32_t>(fst_epoch_ns % 1000000000ULL));\n")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(2)
    t = P.read_text(encoding="utf-8")
    if MARCA in t:
        print("YA APLICADO")
        sys.exit(0)
    n1, n2 = t.count(A_FST), t.count(A_WIN)
    if n1 != 1 or n2 != 1:
        print(f"ABORTA: anclas flow_start={n1} window_start={n2} (deben ser 1 y 1)")
        sys.exit(1)
    i1, i2 = t.index(A_FST), t.index(A_WIN)
    if not i1 < i2:
        print("ABORTA: window_start aparece antes que flow_start (fst_epoch_ns no estaria declarado)")
        sys.exit(1)
    nuevo = t.replace(A_FST, N_FST, 1).replace(A_WIN, N_WIN, 1)
    if sys.argv[1] == "--check":
        print("CHECK OK: anclas 1 y 1, en orden; flow_start_time y window_start pasarian a epoch derivado")
        return
    tmp = P.with_name(P.name + ".tmp_d295fs")
    tmp.write_text(nuevo, encoding="utf-8")
    os.replace(tmp, P)
    print(f"APLICADO: {P} ({len(t)} -> {len(nuevo)} bytes)")


if __name__ == "__main__":
    main()
