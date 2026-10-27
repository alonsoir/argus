#!/usr/bin/env python3
"""DAY309 compara dos corridas de la bateria B (resumen.json de d309_bateria_analisis.py): antes (main) y despues (rama).
Uso: d309_comparar.py DIR_ANTES DIR_DESPUES

Criterio fijado antes de medir: decisiones iguales dentro del ruido = mismo numero de INICIO y de FIN, y suma de ataque
y de bajo_presion del resumen [DDOS-V2] con diferencia relativa <= 5 % (ruido medido DAY309: 0,1-0,4 %). Los rasgos se
muestran lado a lado; la caducidad solo debia cambiar la base de la benigna (prediccion en d309_bateria_analisis.py).
rc 0 = decisiones iguales; rc 1 = distintas; rc 2 = faltan datos.
"""
import json
import sys
from pathlib import Path

TOL = 0.05


def rel(a, b):
    return 0.0 if a == b == 0 else abs(a - b) / max(abs(a), abs(b))


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    r = []
    for p in sys.argv[1:]:
        f = Path(p) / "resumen.json"
        if not f.is_file():
            print(f"FALTA {f}")
            return 2
        r.append(json.loads(f.read_text()))
    a, b = r
    print(f"antes:   {sys.argv[1]} tipo={a['tipo']} lado={a['lado']}")
    print(f"despues: {sys.argv[2]} tipo={b['tipo']} lado={b['lado']}")
    if a["tipo"] != b["tipo"]:
        print("TIPOS DISTINTOS: no se comparan")
        return 2
    if (a["lado"], b["lado"]) != ("main", "rama"):
        print(f"AVISO: se esperaba antes=main y despues=rama, hay {a['lado']} y {b['lado']}")
    print("\n== rasgos por grupo (antes | despues)")
    for g in sorted(set(a["grupos"]) | set(b["grupos"])):
        x, y = a["grupos"].get(g), b["grupos"].get(g)
        if not x or not y:
            print(f"  {g:10s} solo en {'antes' if x else 'despues'}")
            continue
        print(f"  {g:10s} n {x['n']} | {y['n']}  media_fpk {x['media_fpk']:.3f} | {y['media_fpk']:.3f}  "
              f"size {x['size']:.1f} | {y['size']:.1f}  entropia {x['entropia']:.4f} | {y['entropia']:.4f}  "
              f"ratio>=3 {x['ratio_ge3']:.3f} | {y['ratio_ge3']:.3f}")
    print("\n== prediccion de rasgos por lado")
    print(f"  antes {a['pred']}  despues {b['pred']}")
    da, db = a["decision"], b["decision"]
    print("\n== decisiones (criterio: INICIO y FIN iguales; ataque y bajo_presion a <= 5 %)")
    ok = True
    for k in ("inicio", "fin"):
        e = da[k] == db[k]
        ok &= e
        print(f"  {k:12s} {da[k]} | {db[k]}  {'IGUAL' if e else 'DISTINTO'}")
    for k in ("ataque", "bajo_presion"):
        d = rel(da[k], db[k])
        e = d <= TOL
        ok &= e
        print(f"  {k:12s} {da[k]} | {db[k]}  dif={100 * d:.2f} %  {'IGUAL' if e else 'DISTINTO'}")
    print(f"  drops en FIN {da['drops_fin']} | {db['drops_fin']}")
    print(f"  tabla de flujos (despues): {b['flow_table']}")
    print(f"\nRESULTADO: decisiones {'IGUALES' if ok else 'DISTINTAS'} dentro del ruido")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
