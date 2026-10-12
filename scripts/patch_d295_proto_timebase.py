#!/usr/bin/env python3
"""[TIMEBASE-D295:PROTO] Contrato temporal v1 en el proto (docs/timebase/contrato_temporal_day295.md, C2).
Anade enum ClockState, message TimeContext y NetworkSecurityEvent.time_context = 38.
Atomico: o casan las dos anclas exactamente una vez y se aplica todo, o no se toca nada.
Uso: python3 scripts/patch_d295_proto_timebase.py --check | --apply"""
import os
import sys
from pathlib import Path

P = Path("protobuf/network_security.proto")
MARCA = "[TIMEBASE-D295:PROTO]"

ANCLA_MSG = "message NetworkSecurityEvent {\n"
BLOQUE_MSG = """// [TIMEBASE-D295:PROTO] Contrato temporal v1 (docs/timebase/contrato_temporal_day295.md).
// Base interna unica: CLOCK_MONOTONIC (bpf_ktime_get_ns en el kernel, steady_clock en espacio de usuario).
// Duraciones y orden SOLO con *_mono_ns y solo entre eventos con el mismo boot_id.
// Epoch = mono_ns + wall_anchor_ns (= event_timestamp desde el contrato v1).
enum ClockState {
  CLOCK_STATE_OK      = 0;  // sin salto reciente ni correccion gradual detectada
  CLOCK_STATE_SLEWING = 1;  // MONOTONIC se aparta de MONOTONIC_RAW mas que slew_ppm_threshold
  CLOCK_STATE_STEPPED = 2;  // salto del reloj de pared hace menos de stepped_recent_s
}

message TimeContext {
  uint64 mono_ns                = 1;   // instante del evento, CLOCK_MONOTONIC
  string boot_id                = 2;   // /proc/sys/kernel/random/boot_id del nodo productor
  uint64 producer_start_mono_ns = 3;   // arranque del proceso productor (CLOCK_MONOTONIC)
  uint64 producer_seq           = 4;   // +1 por evento; (node, boot_id, start, seq) es unica
  int64  wall_anchor_ns         = 5;   // REALTIME - MONOTONIC vigente al emitir
  ClockState clock_state        = 6;
  uint32 time_contract_version  = 7;   // 1
  uint64 sniffer_send_mono_ns   = 8;   // D17: retraso por salto (mismo nodo y boot_id)
  uint64 mld_recv_mono_ns       = 9;
  uint64 mld_send_mono_ns       = 10;
}

"""
ANCLA_CAMPO = "  EventKind event_kind = 37;\n}\n"
NUEVO_CAMPO = ("  EventKind event_kind = 37;\n"
               "  // [TIMEBASE-D295:PROTO] contrato temporal v1\n"
               "  TimeContext time_context = 38;\n"
               "}\n")


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(__doc__)
        sys.exit(2)
    t = P.read_text(encoding="utf-8")
    if MARCA in t:
        print("YA APLICADO: la marca esta en el proto")
        sys.exit(0)
    for nombre in ("TimeContext", "ClockState", "time_context"):
        if nombre in t:
            print(f"ABORTA: '{nombre}' ya existe en el proto sin la marca")
            sys.exit(1)
    n_msg, n_campo = t.count(ANCLA_MSG), t.count(ANCLA_CAMPO)
    if n_msg != 1 or n_campo != 1:
        print(f"ABORTA: anclas ANCLA_MSG={n_msg} ANCLA_CAMPO={n_campo} (deben ser 1 y 1)")
        sys.exit(1)
    nuevo = t.replace(ANCLA_MSG, BLOQUE_MSG + ANCLA_MSG, 1).replace(ANCLA_CAMPO, NUEVO_CAMPO, 1)
    if nuevo.count(MARCA) != 2:
        print(f"ABORTA: marcas tras aplicar = {nuevo.count(MARCA)} (deben ser 2)")
        sys.exit(1)
    if sys.argv[1] == "--check":
        print("CHECK OK: anclas 1 y 1; se anadirian enum ClockState, message TimeContext y time_context = 38")
        return
    tmp = P.with_suffix(".proto.tmp")
    tmp.write_text(nuevo, encoding="utf-8")
    os.replace(tmp, P)
    print(f"APLICADO: {P} ({len(t)} -> {len(nuevo)} bytes)")


if __name__ == "__main__":
    main()
