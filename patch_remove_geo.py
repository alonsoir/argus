#!/usr/bin/env python3
"""
patch_remove_geo.py — quita geographical_concentration del pipeline DDoS (DAY255, paso 3).
Cuatro sitios COORDINADOS: DDOSFeatures.py (entrada), SyntheticDDOSGenerator.py (dict normal 28,
dict http_flood 59, elif del default 100), GenerateDDOSCPPForest.py (docstring del contrato).
Idempotente. --check no escribe. Verifica que compila. NO commitea.
Uso: python patch_remove_geo.py [--check] [--base <dir>]
"""
import argparse, os, sys, py_compile, tempfile, re

FEAT = "DDOSFeatures.py"; GEN = "SyntheticDDOSGenerator.py"; HDR = "GenerateDDOSCPPForest.py"

EDITS = [
    (FEAT,
     '    "geographical_concentration",    # Geo-IP concentration\n',
     '', "DDOSFeatures: entrada de la lista"),
    (GEN,
     "            'geographical_concentration': np.random.beta(1, 9, self.n_samples),     # Muy baja concentración\n",
     '', "generador: dict NORMAL (28)"),
    (GEN,
     "            'geographical_concentration': np.random.beta(12, 2, n_per_attack),  # Alta concentración geográfica\n",
     '', "generador: dict http_flood (59)"),
    (GEN,
     "                    elif feature == 'geographical_concentration':\n"
     "                        data[feature].extend(np.random.beta(6, 3, n_per_attack))  # Concentración media\n",
     '', "generador: elif del default (100)"),
    (HDR,
     "/// @param features Array of 10 feature values in order:",
     "/// @param features Array of 9 feature values in order:", "header: contrato N=10 -> 9"),
    (HDR,
     "///   [7] geographical_concentration\n"
     "///   [8] traffic_escalation_rate\n"
     "///   [9] resource_saturation_score",
     "///   [7] traffic_escalation_rate\n"
     "///   [8] resource_saturation_score", "header: docstring quita [7], renumera"),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--base', default='ml-training/scripts/ddos_detection')
    args = ap.parse_args()

    files = {}
    for fn in (FEAT, GEN, HDR):
        p = os.path.join(args.base, fn)
        if not os.path.isfile(p):
            print(f"[ABORT] no existe: {p}"); sys.exit(2)
        files[fn] = open(p, encoding='utf-8').read()

    plan, already, ambiguous = [], [], []
    for fn, old, new, tag in EDITS:
        c = files[fn].count(old)
        if c == 1:   plan.append((fn, old, new, tag))
        elif c == 0: already.append(tag)
        else:        ambiguous.append((tag, c))

    if ambiguous:
        print("[ABORT] ancla no unica (el fichero no es el que espero):")
        for tag, c in ambiguous: print(f"   {tag}: {c} coincidencias")
        sys.exit(2)

    print("== patch_remove_geo ==")
    for tag in already: print(f"  [ya aplicado] {tag}")
    for _, _, _, tag in plan: print(f"  [se aplicaria] {tag}")
    if not plan:
        print("  nada que hacer (geo ya quitado en los 4 sitios)."); return
    if args.check:
        print(f"[CHECK] {len(plan)} ediciones pendientes. No se ha escrito nada."); return

    for fn, old, new, tag in plan:
        files[fn] = files[fn].replace(old, new, 1)

    for fn in (FEAT, GEN):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8')
        tmp.write(files[fn]); tmp.close()
        try:
            py_compile.compile(tmp.name, doraise=True)
        except py_compile.PyCompileError as e:
            print(f"[ABORT] {fn} NO compila tras el parche — no se escribe nada:\n{e}")
            os.unlink(tmp.name); sys.exit(2)
        os.unlink(tmp.name)

    for fn in {e[0] for e in plan}:
        open(os.path.join(args.base, fn), 'w', encoding='utf-8').write(files[fn])

    m = re.search(r'DDOS_FEATURES\s*=\s*\[(.*?)\]', files[FEAT], re.S)
    names = re.findall(r'"([^"]+)"', re.sub(r'#[^\n]*', '', m.group(1)))
    print(f"[OK] aplicado. DDOS_FEATURES -> {len(names)} features: {names}")
    if 'geographical_concentration' in names or 'geographical_concentration' in files[GEN]:
        print("[WARN] geo sigue presente?!"); sys.exit(2)
    print("      geo eliminado de lista, generador y contrato. Los .py compilan.")

if __name__ == '__main__':
    main()
