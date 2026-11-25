# scripts/parquet/filas_ts.py — [PARQUET-SIN-NUMPY-D337] comprobación de timestamp_utc_ns en TODAS las filas de una
# columna de Parquet ([PARQUET-ALLROWS-D296], DEBT-PARQUET-VALIDATOR-FIRST-ROW-001), solo con pyarrow.compute.
# Antes (hasta DAY336): to_numpy() y np.argmax, que obligaban a tener numpy en la base del defender solo para esto.
# Medido DAY337: pyarrow 26.0.1 no depende de numpy (requires_dist vacío en PyPI) y to_numpy() sin numpy da
# ImportError. Sin numpy, el gate solo depende de pyarrow (DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente pip B).
# Complejidad lineal: cada comparación recorre la columna una vez; pc.index para en el primer true.
import pyarrow.compute as pc

TS_MIN_NS = 1_700_000_000_000_000_000   # 2023-11-14; por debajo = reloj monotonico u otro error (DAY294, DAY296)
TS_FUTURE_MARGIN_NS = 300 * 10**9      # ninguna fila puede venir mas de 300 s del futuro
NS_POR_MS = 1_000_000


def _primera(a, mascara):
    """(cuántas, índice de la primera, su valor) de las filas de a donde mascara es true; None si ninguna."""
    n = pc.sum(mascara).as_py() or 0
    if n == 0:
        return None
    i = pc.index(mascara, True).as_py()
    return n, i, a[i].as_py()


def fallos_ts(nombre, col, ahora_ns, ms_multiple=False):
    """Lista de mensajes de fallo de la columna col (int64, Array o ChunkedArray); vacía si todo está bien.
    El índice de la primera fila es el de la columna sin nulos, como antes de DAY337."""
    fallos = []
    n = len(col)
    nul = col.null_count
    if nul != 0:
        fallos.append(f"{nombre}: {nul} de {n} filas con timestamp_utc_ns nulo")
    a = pc.drop_null(col)
    if len(a) == 0:
        return fallos
    hi = ahora_ns + TS_FUTURE_MARGIN_NS
    for mascara, que in ((pc.less(a, TS_MIN_NS), f"< {TS_MIN_NS} (reloj monotonico?)"),
                         (pc.greater(a, hi), "del futuro (> ahora + 300 s)")):
        r = _primera(a, mascara)
        if r:
            fallos.append(f"{nombre}: {r[0]} de {n} filas con timestamp_utc_ns {que}; primera: fila {r[1]} = {r[2]}")
    if ms_multiple:
        # a % 1e6 != 0 sin módulo: a != trunc(a / 1e6) * 1e6 (la división entera de pyarrow trunca hacia cero; el
        # producto no desborda porque su valor absoluto no pasa del de a).
        r = _primera(a, pc.not_equal(a, pc.multiply(pc.divide(a, NS_POR_MS), NS_POR_MS)))
        if r:
            fallos.append(f"{nombre}: {r[0]} de {n} filas no son multiplo de 1_000_000 (ms->ns fallida); "
                          f"primera: fila {r[1]} = {r[2]}")
    return fallos
