#!/usr/bin/env python3
"""
census_ddos_splits.py — Censo determinista de splits por feature en un .hpp de bosque DDoS.
Mide el ARTEFACTO (el .hpp que se compila y sirve), no el modelo en memoria. READ-ONLY.
Conteo por feature_idx (autoritativo); nombre por DDOSFeatures.DDOS_FEATURES, contrastado
con el comentario de cada nodo (salvaguarda anti-desalineacion .hpp<->lista).

Uso:
    python census_ddos_splits.py <ruta_al_hpp> [--features <DDOSFeatures.py>] [--sentinel NOMBRE ...]
"""
import re, sys, os, hashlib, argparse

NODE_RE   = re.compile(r'^\s*\{\s*(-?\d+)\s*,')
HDR_TREES = re.compile(r'^//\s*Trees:\s*(\d+)')
HDR_FEATS = re.compile(r'^//\s*Features:\s*(\d+)')

def load_feature_names(path):
    if not path or not os.path.isfile(path):
        return None
    txt = open(path, encoding='utf-8').read()
    m = re.search(r'DDOS_FEATURES\s*=\s*\[(.*?)\]', txt, re.S)
    if not m:
        return None
    body = re.sub(r'#[^\n]*', '', m.group(1))
    pairs = re.findall(r'"([^"]+)"|\'([^\']+)\'', body)
    return [a or b for a, b in pairs] or None

def name_from_comment(line):
    i = line.find('//')
    if i < 0:
        return None
    c = line[i+2:].strip()
    return c.split('<=')[0].strip() if '<=' in c else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('hpp')
    ap.add_argument('--features', default=None)
    ap.add_argument('--sentinel', action='append', default=[])
    args = ap.parse_args()

    if not os.path.isfile(args.hpp):
        print(f"[ABORT] no existe: {args.hpp}"); sys.exit(2)

    raw = open(args.hpp, 'rb').read()
    sha = hashlib.sha256(raw).hexdigest()
    lines = raw.decode('utf-8', 'replace').splitlines()

    feats_path = args.features or os.path.join(
        os.path.dirname(os.path.abspath(args.hpp)), 'DDOSFeatures.py')
    names = load_feature_names(feats_path)

    n_trees_hdr = n_feats_hdr = None
    counts, comment_name, mismatches = {}, {}, []
    leaves = internal = 0

    for ln in lines:
        mt = HDR_TREES.match(ln); mf = HDR_FEATS.match(ln)
        if mt: n_trees_hdr = int(mt.group(1)); continue
        if mf: n_feats_hdr = int(mf.group(1)); continue
        m = NODE_RE.match(ln)
        if not m:
            continue
        idx = int(m.group(1))
        if idx < 0:
            leaves += 1; continue
        internal += 1
        counts[idx] = counts.get(idx, 0) + 1
        cn = name_from_comment(ln)
        if cn:
            if idx in comment_name and comment_name[idx] != cn:
                mismatches.append((idx, comment_name[idx], cn))
            comment_name[idx] = cn

    if internal == 0:
        print("[ABORT] 0 nodos internos parseados — .hpp vacio/roto o formato inesperado (anti falso-verde)")
        sys.exit(2)

    def label(idx):
        if names and idx < len(names):
            return names[idx]
        return comment_name.get(idx, f"idx{idx}")

    print("== censo de splits por feature ==")
    print(f"  hpp: {args.hpp}")
    print(f"  sha256: {sha}")
    print(f"  header: Trees={n_trees_hdr}  Features={n_feats_hdr}")
    print(f"  lista features: {feats_path if names else '(no encontrada)'}"
          + (f"  ({len(names)} nombres)" if names else ""))
    print(f"  nodos internos: {internal}   hojas: {leaves}")
    print("  --- splits por feature (idx: nombre = cuenta) ---")
    for idx in sorted(counts):
        nm = label(idx)
        mark = "   <-- SENTINEL (deberia ser 0)" if nm in args.sentinel else ""
        print(f"   {idx:>2}: {nm:<30} = {counts[idx]}{mark}")
    if names:
        zero = [f"{i}:{n}" for i, n in enumerate(names) if counts.get(i, 0) == 0]
        if zero:
            print(f"  features con 0 splits: {', '.join(zero)}")
        bad = [(i, names[i], comment_name[i]) for i in comment_name
               if i < len(names) and comment_name[i] != names[i]]
        if bad:
            print("  [WARN] desalineacion .hpp<->DDOSFeatures.py:")
            for i, a, b in bad:
                print(f"         idx {i}: lista='{a}'  comentario='{b}'")
        else:
            print("  [OK] idx->nombre del .hpp casa con DDOSFeatures.py")
    if mismatches:
        print("  [WARN] un mismo idx con nombres de comentario distintos:", mismatches)

    if args.sentinel:
        viol = {label(i): c for i, c in counts.items() if label(i) in args.sentinel and c > 0}
        if viol:
            print(f"  ===== NO-GO ===== splits sobre centinela: {viol}"); sys.exit(1)
        print(f"  ===== GO ===== 0 splits sobre {args.sentinel}")

if __name__ == '__main__':
    main()
