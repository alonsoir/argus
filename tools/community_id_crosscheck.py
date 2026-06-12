#!/usr/bin/env python3
# community_id_crosscheck.py — DAY 171 #1 · DAY 172: +delta inicio de flujo (Opción A)
# Verificador de paridad de community_id entre los tres sensores de red:
#   aRGus (nativo), Suricata, Zeek — sobre el MISMO trafico replayado.
#
# NO es un adapter AdapterSpec-compliant. Es un verificador de paridad
# standalone que valida el CIMIENTO del AdapterSpec (§10): que los tres
# motores emiten el mismo community_id sobre el mismo paquete. Lee las
# salidas crudas de cada motor, no el envelope SecurityEvent.
#
# Paridad por VALOR de community_id (el solomillo). La 5-tupla se conserva
# como ETIQUETA forense de la anomalia, NO como clave de comparacion
# (el cid ya encapsula la 5-tupla canonica del hash Corelight).
#
# DAY 172 — Opción A (delta de INICIO de flujo, sanity check temporal):
#   Lee el timestamp INTERNO de cada registro (inicio de flujo / primer paquete)
#   y reporta el spread entre sensores para los cids en 'agree'.
#   Esto NO es source_wait_timeout (eso es retardo de EMISION -> B,
#   DEBT-CORRELATION-TIMEOUT-CALIB-001). Es un sanity check: los tres ven
#   el mismo paquete casi a la vez -> spread esperado en MILISEGUNDOS.
#
#   HALLAZGO DAY 172: el TSV de aRGus estampa timestamp SINTETICO
#   (contador 1.7e18+N, no system_clock real — community_id_log.cpp corre
#   bajo reloj inyectado en el build de cross-check). Por eso el ts de aRGus
#   se IGNORA aqui (ts=0.0 forzado). aRGus entra en la medida cuando B le
#   de wall-clock de aparicion real en el host. Verificar tambien si el path
#   de PRODUCCION heredo el reloj inyectado (bug latente posible).
#
# Categorias de salida:
#   agree         — cids en la interseccion de los tres. Lo que importa.
#   expected_diff — cids que Suricata/Zeek emiten y aRGus difiere POR DISENO
#                   (ICMP/IPv6-ICMP/no-TCP-UDP -> compute_community_id = nullopt).
#   anomaly       — todo lo demas. NO se descarta: se vuelca a fichero para
#                   investigacion (bug propio | diferencia de capa | evasion).
#
# Ejecutar desde el HOST (macOS). Shell-ea a cada VM via vagrant ssh.
# Exit 0 si no hay anomalias; !=0 si las hay o si un sensor capturo 0 flujos.
#
# Rutas overridables por flag (default = rutas reales del entorno unificado):
#   --suricata-eve  (default /var/log/suricata/eve.json)
#   --zeek-conn     (default /vagrant/logs/lab/zeek/conn.log)
#   --argus-tsv     (default /vagrant/logs/lab/cid-xcheck-argus.tsv)
import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime

# Rutas reales por sensor (verificadas DAY 171, no de memoria)
SURICATA_VM   = "suricata"
SURICATA_EVE  = "/var/log/suricata/eve.json"
ZEEK_VM       = "zeek"
ZEEK_CONN     = "/vagrant/logs/lab/zeek/conn.log"
ARGUS_VM      = "defender"
ARGUS_TSV     = "/vagrant/logs/lab/cid-xcheck-argus.tsv"
ANOMALY_OUT   = "/vagrant/logs/lab/cid-xcheck-anomalies.tsv"

# Protocolos que aRGus procesa (TCP/UDP). El resto los difiere (nullopt).
ARGUS_PROTOS_TEXT = {"tcp", "udp"}
ARGUS_PROTOS_NUM  = {6, 17}


# --- Normalizacion de timestamp por sensor -> epoch-segundos-float ----------
# Todos devuelven 0.0 ante fallo/no-disponible. 0.0 == "ts no fiable, no usar".

def _parse_zeek_ts(raw: str) -> float:
    # Zeek: epoch float directo (campo 'ts' de conn.log)
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def _parse_suricata_ts(raw: str) -> float:
    # Suricata: ISO8601 con offset, p.ej. 2026-06-02T04:31:07.123456+0000.
    # datetime.fromisoformat soporta el offset sin ':' en Python 3.11+.
    try:
        return datetime.fromisoformat(raw).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _parse_argus_ts(raw: str) -> float:
    # HALLAZGO DAY 172: el TSV de aRGus estampa CONTADOR sintetico
    # (1.7e18+N), no system_clock real. Reloj inyectado en build de cross-check.
    # Se IGNORA hasta que B (DEBT-CORRELATION-TIMEOUT-CALIB-001) mida aRGus por
    # wall-clock de aparicion en el host. NO devolver el valor crudo: contaminaria
    # el spread con un delta falso de pinta valida.
    #   Cuando el reloj real este arreglado, sustituir el cuerpo por:
    #       return int(raw) / 1e9   # (confirmar unidad: ns/us/ms via tail+cut -f7)
    return 0.0


@dataclass(frozen=True)
class Record:
    cid: str
    saddr: str
    daddr: str
    sport: str
    dport: str
    proto_raw: str
    ts: float = 0.0          # epoch-segundos-float. 0.0 == no capturado / no fiable.

    def is_argus_protocol(self) -> bool:
        p = self.proto_raw.strip().lower()
        if p in ARGUS_PROTOS_TEXT:
            return True
        if p.isdigit() and int(p) in ARGUS_PROTOS_NUM:
            return True
        return False


@dataclass
class SensorData:
    name: str
    records: list = field(default_factory=list)

    @property
    def cids(self) -> set:
        return {r.cid for r in self.records}

    def record_for_cid(self, cid: str):
        for r in self.records:
            if r.cid == cid:
                return r
        return None


def _ssh(vm: str, cmd: str) -> str:
    full = ["vagrant", "ssh", vm, "-c", cmd]
    try:
        out = subprocess.run(full, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"[ERROR] timeout hablando con VM '{vm}'", file=sys.stderr)
        return ""
    if out.returncode != 0:
        print(f"[WARN] '{vm}' rc={out.returncode}: {out.stderr.strip()[:200]}",
              file=sys.stderr)
    return out.stdout


def read_suricata(eve_path: str = SURICATA_EVE) -> SensorData:
    jq = (r"""jq -r 'select(.community_id != null and .community_id != "") """
          r"""| [.community_id, .src_ip, .dest_ip, """
          r"""(.src_port // 0), (.dest_port // 0), .proto, .timestamp] | @tsv'""")
    raw = _ssh(SURICATA_VM, f"sudo {jq} {eve_path} 2>/dev/null")
    data = SensorData("suricata")
    for line in raw.splitlines():
        c = line.split("\t")
        if len(c) == 7 and c[0]:
            data.records.append(Record(c[0], c[1], c[2], c[3], c[4], c[5],
                                       _parse_suricata_ts(c[6])))
    return data


def read_zeek(conn_path: str = ZEEK_CONN) -> SensorData:
    # 'ts' al FINAL para no desplazar el reordenamiento orig/resp de zeek-cut.
    zc = ("zeek-cut community_id id.orig_h id.orig_p id.resp_h id.resp_p proto ts "
          f"< {conn_path}")
    raw = _ssh(ZEEK_VM, f"sudo bash -lc '{zc}' 2>/dev/null")
    data = SensorData("zeek")
    for line in raw.splitlines():
        c = line.split("\t")
        if len(c) == 7 and c[0] and c[0] != "-":
            data.records.append(Record(c[0], c[1], c[3], c[2], c[4], c[5],
                                       _parse_zeek_ts(c[6])))
    return data


def read_argus(tsv_path: str = ARGUS_TSV) -> SensorData:
    # El TSV de aRGus tiene 7 columnas; la 7a es el timestamp SINTETICO (ver
    # _parse_argus_ts / HALLAZGO DAY 172). Se lee para no romper el formato,
    # pero _parse_argus_ts lo neutraliza a 0.0.
    raw = _ssh(ARGUS_VM, f"sudo cat {tsv_path} 2>/dev/null")
    data = SensorData("argus")
    for line in raw.splitlines():
        c = line.split("\t")
        if len(c) == 7 and c[0]:
            data.records.append(Record(c[0], c[1], c[2], c[3], c[4], c[5],
                                       _parse_argus_ts(c[6])))
    return data


def guard_nonzero(sensors: list) -> bool:
    ok = True
    print("-- Guard N>0 (cada sensor debe ver el flujo) --")
    for s in sensors:
        n = len(s.records)
        mark = "OK " if n > 0 else "XX "
        print(f"  {mark} {s.name:10s}: {n} flujos con community_id")
        if n == 0:
            ok = False
    if not ok:
        print("\nGUARD FALLO: al menos un sensor capturo 0 flujos.")
        print("   Causas tipicas: eth1 sin promisc allow-all en el intnet,")
        print("   sensor no arrancado, o ruta de log incorrecta.")
        print("   NO se compara: 'tres vacios coinciden' es un falso verde.")
    return ok


def report_flow_start_delta(agree: set, suri, zeek, argus) -> None:
    # Opción A (DAY 172): spread del timestamp INTERNO (inicio de flujo) entre
    # sensores, para los cids en 'agree'. Sanity check temporal de la paridad:
    # los tres ven el mismo paquete casi a la vez -> spread en MILISEGUNDOS.
    # NO es source_wait_timeout (retardo de EMISION -> B).
    # Solo cuenta sensores con ts > 0.0 (aRGus hoy = 0.0, ver HALLAZGO DAY 172),
    # por eso hoy el spread es Suricata<->Zeek. aRGus entra cuando B le de ts real.
    print("\n-- Delta de INICIO de flujo (Opción A, sanity check) --")
    print("   [esperado: spread en ms. NO es source_wait_timeout -> ver DEBT-")
    print("    CORRELATION-TIMEOUT-CALIB-001. aRGus excluido: ts sintetico DAY 172]")

    spreads_ms = []
    sin_ts = 0
    for cid in sorted(agree):
        r_a = argus.record_for_cid(cid)
        r_s = suri.record_for_cid(cid)
        r_z = zeek.record_for_cid(cid)
        ts = {nm: r.ts for nm, r in
              (("argus", r_a), ("suri", r_s), ("zeek", r_z))
              if r and r.ts > 0.0}
        if len(ts) >= 2:
            spread = max(ts.values()) - min(ts.values())
            spreads_ms.append(spread * 1000.0)
            detalle = " ".join(f"{k}={v:.3f}" for k, v in ts.items())
            print(f"   {cid[:28]:28s} spread={spread*1000:8.1f}ms  {detalle}")
        else:
            sin_ts += 1

    if spreads_ms:
        n = len(spreads_ms)
        peor = max(spreads_ms)
        medio = sum(spreads_ms) / n
        print(f"\n   resumen: {n} cids con >=2 ts | "
              f"spread medio={medio:.1f}ms | peor={peor:.1f}ms")
        if peor > 1000.0:
            print("   [!!] spread > 1s: NO es inicio de flujo limpio. Posible ts")
            print("        anclado a fin-de-flujo, o un sensor midiendo emision.")
            print("        Investigar antes de fiarse de este numero.")
    if sin_ts:
        print(f"   ({sin_ts} cids sin >=2 ts fiables — esperado mientras aRGus=0.0)")


def crosscheck(suri: SensorData, zeek: SensorData, argus: SensorData) -> int:
    s_cids, z_cids, a_cids = suri.cids, zeek.cids, argus.cids

    agree = s_cids & z_cids & a_cids

    not_in_argus = (s_cids | z_cids) - a_cids
    expected_diff = set()
    anomaly = set()
    for cid in not_in_argus:
        rec = suri.record_for_cid(cid) or zeek.record_for_cid(cid)
        if rec and not rec.is_argus_protocol():
            expected_diff.add(cid)
        else:
            anomaly.add(cid)

    only_argus = a_cids - (s_cids | z_cids)
    anomaly |= only_argus

    print("\n=============================================================")
    print("  CROSS-CHECK community_id — DAY 171 #1")
    print("=============================================================")
    print(f"  Suricata: {len(s_cids):5d} cids unicos")
    print(f"  Zeek:     {len(z_cids):5d} cids unicos")
    print(f"  aRGus:    {len(a_cids):5d} cids unicos")
    print(f"\n  [OK]  agree (los tres, identico):        {len(agree):5d}")
    print(f"  [--]  expected_diff (aRGus difiere ICMP): {len(expected_diff):5d}")
    print(f"  [!!]  anomaly (a investigar):            {len(anomaly):5d}")

    if agree:
        report_flow_start_delta(agree, suri, zeek, argus)

    if anomaly:
        dump_anomalies(anomaly, suri, zeek, argus)
        print(f"\n  Anomalias volcadas a: {ANOMALY_OUT}")
        print("  (conservadas para investigacion: bug | capa | evasion)")

    return 0 if not anomaly else 2


def dump_anomalies(anomaly: set, suri, zeek, argus) -> None:
    lines = ["cid\tsensor\tsaddr\tdaddr\tsport\tdport\tproto"]
    for cid in sorted(anomaly):
        for s in (suri, zeek, argus):
            r = s.record_for_cid(cid)
            if r:
                lines.append(f"{cid}\t{s.name}\t{r.saddr}\t{r.daddr}"
                             f"\t{r.sport}\t{r.dport}\t{r.proto_raw}")
            else:
                lines.append(f"{cid}\t{s.name}\t-\t-\t-\t-\t-")
    payload = "\n".join(lines) + "\n"
    full = ["vagrant", "ssh", ARGUS_VM, "-c", f"cat > {ANOMALY_OUT}"]
    subprocess.run(full, input=payload, text=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Cross-check de community_id entre aRGus/Suricata/Zeek")
    ap.add_argument("--sensors", default="suricata,zeek,argus",
                    help="sensores a leer (coma-separado). Default: los tres.")
    ap.add_argument("--suricata-eve", default=SURICATA_EVE,
                    help=f"ruta eve.json en VM suricata (default {SURICATA_EVE})")
    ap.add_argument("--zeek-conn", default=ZEEK_CONN,
                    help=f"ruta conn.log en VM zeek (default {ZEEK_CONN})")
    ap.add_argument("--argus-tsv", default=ARGUS_TSV,
                    help=f"ruta tsv en VM defender (default {ARGUS_TSV})")
    args = ap.parse_args()
    want = {s.strip() for s in args.sensors.split(",")}

    suri  = read_suricata(args.suricata_eve) if "suricata" in want else SensorData("suricata")
    zeek  = read_zeek(args.zeek_conn)        if "zeek"     in want else SensorData("zeek")
    argus = read_argus(args.argus_tsv)       if "argus"    in want else SensorData("argus")

    active = [s for s in (suri, zeek, argus) if s.name in want]
    if not guard_nonzero(active):
        return 1

    if want != {"suricata", "zeek", "argus"}:
        print("\n[INFO] Subconjunto de sensores: solo guard N>0, sin paridad 3-way.")
        return 0
    return crosscheck(suri, zeek, argus)


if __name__ == "__main__":
    sys.exit(main())