#!/usr/bin/env python3
# d332_xgboost_retirar.py — DEBT-XGBOOST-RETIRAR-001 (DAY332)
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d332_xgboost_retirar.py {vagrantfile|makefile|resto}
# Partida: cada fichero tocado debe ser idéntico a su versión en HEAD (sha256 de partida = el de HEAD).
# Cada ancla, las veces exactas. Si algo falla, no se escribe nada.
import hashlib, subprocess, sys

def sha(b): return hashlib.sha256(b).hexdigest()

def cargar(ruta):
    with open(ruta, 'rb') as f: actual = f.read()
    head = subprocess.run(['git', 'show', f'HEAD:{ruta}'], capture_output=True, check=True).stdout
    if sha(actual) != sha(head):
        sys.exit(f'❌ {ruta}: no coincide con HEAD (sha256 {sha(actual)} != {sha(head)}); nada escrito')
    print(f'  partida {ruta}: {sha(actual)}')
    return actual.decode('utf-8')

def reemplazar(txt, viejo, nuevo, n, ruta):
    c = txt.count(viejo)
    if c != n: raise ValueError(f'{ruta}: ancla {viejo!r} aparece {c} veces (esperadas {n})')
    return txt.replace(viejo, nuevo)

def quitar_lineas_con(txt, sub, n, ruta):
    ls = txt.splitlines(keepends=True)
    hits = [l for l in ls if sub in l]
    if len(hits) != n: raise ValueError(f'{ruta}: {sub!r} en {len(hits)} líneas (esperadas {n})')
    return ''.join(l for l in ls if sub not in l)

def quitar_lineas_exactas(txt, linea, n, ruta):
    ls = txt.splitlines(keepends=True)
    c = sum(1 for l in ls if l.rstrip('\n') == linea)
    if c != n: raise ValueError(f'{ruta}: línea {linea!r} aparece {c} veces (esperadas {n})')
    return ''.join(l for l in ls if l.rstrip('\n') != linea)

def quitar_bloque(txt, inicio, fin, nlineas, ruta):
    # Borra desde la línea 'inicio' hasta la línea 'fin' (incluida) y la línea en blanco que la sigue.
    ls = txt.splitlines(keepends=True)
    ini = [i for i, l in enumerate(ls) if l.rstrip('\n') == inicio]
    if len(ini) != 1: raise ValueError(f'{ruta}: inicio {inicio!r} aparece {len(ini)} veces (esperada 1)')
    i = ini[0]
    fins = [j for j in range(i, len(ls)) if ls[j].rstrip('\n') == fin]
    if not fins: raise ValueError(f'{ruta}: fin {fin!r} no aparece tras el inicio')
    j = fins[0]
    if j + 1 < len(ls) and ls[j + 1].strip() == '': j += 1
    if j - i + 1 != nlineas:
        raise ValueError(f'{ruta}: bloque {inicio!r} mide {j - i + 1} líneas (esperadas {nlineas})')
    return ''.join(ls[:i] + ls[j + 1:])

def vagrantfile():
    r = 'Vagrantfile'; t = cargar(r)
    t = quitar_bloque(t, '      # XGBoost 3.2.0 (C API + Python) - ADR-026 Track 1',
                      '      fi', 40, r)
    t = quitar_bloque(t, '      # plugin_xgboost (ADR-026 Track 1) — build + deploy',
                      '      fi', 12, r)
    t = reemplazar(t, '(RF DDoS + train xgboost).', '(RF DDoS).', 1, r)
    t = reemplazar(t, 'igual que xgboost/pandas/jinja2', 'igual que pandas/jinja2', 1, r)
    if 'xgboost' in t.lower(): raise ValueError(f'{r}: queda alguna mención de xgboost')
    q = 'ml-training/requirements-ddos-pinned.txt'; u = cargar(q)
    u = reemplazar(u, '(RF DDoS + train xgboost comparten pandas/sklearn).', '(RF DDoS: pandas/sklearn).', 1, q)
    if 'xgboost' in u.lower(): raise ValueError(f'{q}: queda alguna mención de xgboost')
    return {r: t, q: u}

def makefile():
    r = 'Makefile'; t = cargar(r)
    t = quitar_lineas_con(t, 'check-xgboost-version.sh', 1, r)
    t = quitar_lineas_con(t, 'test -f /usr/local/lib/libxgboost.so', 1, r)
    t = quitar_lineas_con(t, 'libplugin_xgboost.so missing', 1, r)
    t = quitar_lineas_exactas(t, '\t@echo "[6/8] Desplegando modelos ML..."', 2, r)
    t = quitar_lineas_exactas(t, '\t@$(MAKE) deploy-models', 2, r)
    t = quitar_bloque(t, 'deploy-models:', '\t@echo "✅ Modelos ML desplegados en /etc/ml-defender/models/"', 7, r)
    fin = [l for l in t.splitlines() if 'echo TEST-INTEG-XGBOOST-1 FAILED' in l]
    if len(fin) != 1: raise ValueError(f'{r}: línea final de test-integ-xgboost-1 aparece {len(fin)} veces')
    t = quitar_bloque(t, 'test-integ-xgboost-1:', fin[0], 4, r)
    t = quitar_bloque(t, 'sign-models:', '\t@echo "  ✅ 3 modelo(s) firmado(s) correctamente"', 7, r)
    for s in ('xgboost', 'deploy-models', 'sign-models'):
        if s in t.lower(): raise ValueError(f'{r}: queda {s!r}')
    return {r: t}

def resto():
    out = {}
    r = 'Jenkinsfile.dev'; t = cargar(r)
    ls = t.splitlines(keepends=True)
    i = [k for k, l in enumerate(ls) if 'test -f /usr/lib/ml-defender/plugins/libplugin_xgboost.so' in l]
    if len(i) != 1 or 'libplugin_xgboost.so missing' not in ls[i[0] + 1]:
        raise ValueError(f'{r}: par de líneas del plugin no encontrado exactamente una vez')
    t = ''.join(ls[:i[0]] + ls[i[0] + 2:]); out[r] = t
    r = 'tools/prod/build-x86.sh'; t = cargar(r)
    t = quitar_bloque(t, 'PLUGIN_SRC="${VAGRANT}/plugins/xgboost/build/libplugin_xgboost.so"', 'fi', 8, r); out[r] = t
    r = 'tools/prod/collect-libs.sh'; t = cargar(r)
    t = reemplazar(t, '    libonnxruntime.so.1.17.1 \\\n    libxgboost.so; do\n',
                   '    libonnxruntime.so.1.17.1; do\n', 1, r); out[r] = t
    r = 'security/apparmor/argus.ml-detector'; t = cargar(r)
    t = quitar_lineas_con(t, '/usr/local/lib/libxgboost.so', 1, r); out[r] = t
    for k, v in out.items():
        if 'xgboost' in v.lower(): raise ValueError(f'{k}: queda alguna mención de xgboost')
    return out

def main():
    pasos = {'vagrantfile': vagrantfile, 'makefile': makefile, 'resto': resto}
    if len(sys.argv) != 2 or sys.argv[1] not in pasos:
        sys.exit('uso: d332_xgboost_retirar.py {vagrantfile|makefile|resto}')
    try:
        nuevos = pasos[sys.argv[1]]()
    except (ValueError, subprocess.CalledProcessError) as e:
        sys.exit(f'❌ {e}; nada escrito')
    for ruta, txt in nuevos.items():
        with open(ruta, 'w', encoding='utf-8') as f: f.write(txt)
        print(f'  ✅ {ruta}: {sha(txt.encode("utf-8"))}')

if __name__ == '__main__':
    main()
