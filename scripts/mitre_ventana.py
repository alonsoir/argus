#!/usr/bin/env python3
# mitre_ventana.py — DAY323 [MITRE-VENTANA-D323]: deja en un bronce correlation_v1 solo las filas de la ventana de la
# corrida MITRE, [T0, T1] con el reloj del defender (el de todo el lab, [LAB-NTP-SENSORES-D323]), y cuenta las del
# ataque (atacante <-> víctima, en los dos sentidos). La misma ventana para los tres sensores: el grafo del día no
# mezcla datos de otras corridas (medido DAY323: el eve.json de Suricata acumulaba de una corrida a otra; el 04-nov
# el veredicto pasó con alertas del 3-nov).
# Las filas se copian tal cual (byte a byte: el HMAC de cada fila sigue valiendo). Una pasada: lineal.
# Columnas (correlation_v1, bronze_to_gold_converter): 6 flow_start_sec, 7 flow_start_nano, 8 src_ip, 9 dst_ip;
# 19 campos; CSV con comillas como split_csv del correlation-engine.
# Uso: python3 -I scripts/mitre_ventana.py --sensor S --desde T0 --hasta T1 --atacante IP --victima IP ENTRADA SALIDA
# Salida: una línea «[MITRE-VENTANA] sensor=S filas=N dentro=D fuera=F malas=M ataque=K -> SALIDA».
# rc: 0 hay filas dentro; 3 ninguna fila dentro de la ventana; 2 uso; 4 no se puede leer o escribir.
import argparse
import csv
import sys

CAMPOS = 19


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--sensor', required=True)
    ap.add_argument('--desde', required=True, type=float, help='T0, epoch en segundos (reloj del defender)')
    ap.add_argument('--hasta', required=True, type=float, help='T1, epoch en segundos (reloj del defender)')
    ap.add_argument('--atacante', required=True)
    ap.add_argument('--victima', required=True)
    ap.add_argument('entrada')
    ap.add_argument('salida')
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    if a.hasta < a.desde:
        print('[MITRE-VENTANA] FALLA: T1 (%.3f) anterior a T0 (%.3f)' % (a.hasta, a.desde))
        return 2
    par = {a.atacante, a.victima}
    filas = dentro = fuera = malas = ataque = 0
    try:
        with open(a.entrada, encoding='utf-8', newline='') as ent, open(a.salida, 'w', encoding='utf-8', newline='') as sal:
            for linea in ent:
                if not linea.strip():
                    continue
                filas += 1
                try:
                    f = next(csv.reader([linea]))
                    t = int(f[5]) + int(f[6]) / 1e9
                except (StopIteration, IndexError, ValueError, csv.Error):
                    malas += 1
                    continue
                if len(f) != CAMPOS:
                    malas += 1
                    continue
                if a.desde <= t <= a.hasta:
                    dentro += 1
                    sal.write(linea if linea.endswith('\n') else linea + '\n')
                    if {f[7], f[8]} == par:
                        ataque += 1
                else:
                    fuera += 1
    except OSError as e:
        print('[MITRE-VENTANA] FALLA: sensor=%s: %s' % (a.sensor, e))
        return 4
    print('[MITRE-VENTANA] sensor=%s filas=%d dentro=%d fuera=%d malas=%d ataque=%d -> %s'
          % (a.sensor, filas, dentro, fuera, malas, ataque, a.salida))
    return 0 if dentro > 0 else 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
