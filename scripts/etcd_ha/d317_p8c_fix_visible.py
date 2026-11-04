#!/usr/bin/env python3
# d317_p8c_fix_visible.py — paso 8 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): mitre-check anuncia cada fase con su hora y su log,
# y mitre_veredicto.sh saca la salida de mitre_start.sh por pantalla y a su fichero a la vez (tee, rc por PIPESTATUS).
# Medido DAY317: en silencio unos 6 min, mitre-check parecía colgado. Requiere 8c y d317_p8c_fix_stop.py aplicados.
# Uso:  python3 d317_p8c_fix_visible.py --check <raiz_repo>
#       python3 d317_p8c_fix_visible.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si cada fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

MAKEFILE_RUTA = 'Makefile'
MAKEFILE_PREVIO = '8f96a48b5b30191eeccde748e9b3e6fb77a5d43c9e064ad753814af4275307d3'
MAKEFILE_FINAL = 'f39638048903ca34b71025975f1075631fad59903e09c9ba510a7a15f1cde6e5'
MAKEFILE_CAMBIOS = [('mitre-check:\n\t@# [EMECAS-TODO-D317] pipeline-start no admite', 'mitre-check:\n\t@echo "[MITRE-CHECK] $$(date \'+%T\') 1/3 parando el pipeline (log: /tmp/argus_mitre_check_stop.txt)"\n\t@# [EMECAS-TODO-D317] pipeline-start no admite', 1), ('\t@$(MAKE) --no-print-directory pipeline-start > /tmp/argus_mitre_check_start.txt', '\t@echo "[MITRE-CHECK] $$(date \'+%T\') 2/3 arrancando el pipeline (log: /tmp/argus_mitre_check_start.txt)"\n\t@$(MAKE) --no-print-directory pipeline-start > /tmp/argus_mitre_check_start.txt', 1), ('\t@bash scripts/mitre_veredicto.sh\n', '\t@echo "[MITRE-CHECK] $$(date \'+%T\') 3/3 mitre_start.sh y veredicto (la salida sale aquí y en logs/lab/mitre-veredicto-*.txt)"\n\t@bash scripts/mitre_veredicto.sh\n', 1)]
VEREDICTO_RUTA = 'scripts/mitre_veredicto.sh'
VEREDICTO_PREVIO = 'fa6fcc57ad1d7dffc567f7bc22db5642d526c37d75bc138dbb28b4514dcef8e0'
VEREDICTO_FINAL = '4d4bdeeba294c9e096c7833b0620410cc428c08cd0ba4ace92e3d79cfc45a411'
VEREDICTO_CAMBIOS = [('  bash scripts/mitre_start.sh > "$F" 2>&1; RC=$?\n', '  # [MITRE-VEREDICTO-D317b] por pantalla y al fichero a la vez (DAY317: en silencio, mitre-check parecía colgado)\n  bash scripts/mitre_start.sh 2>&1 | tee "$F"; RC=${PIPESTATUS[0]}\n', 1)]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    F = [(MAKEFILE_RUTA, MAKEFILE_PREVIO, MAKEFILE_FINAL, MAKEFILE_CAMBIOS), (VEREDICTO_RUTA, VEREDICTO_PREVIO, VEREDICTO_FINAL, VEREDICTO_CAMBIOS)]
    lee = lambda r: open(os.path.join(raiz, r), 'rb').read()
    for r, _, _, _ in F:
        if not os.path.isfile(os.path.join(raiz, r)):
            print('FALLA: no existe %s; no se toca nada.' % r); return 1
    if all(sha(lee(r)) == fin for r, _, fin, _ in F):
        print('YA APLICADO: no se toca nada.'); return 0
    nuevos = {}
    for r, prev, fin, cs in F:
        b = lee(r)
        if sha(b) != prev:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (r, sha(b)[:16])); return 1
        t = b.decode('utf-8')
        for i, (v, n, k) in enumerate(cs, 1):
            if t.count(v) != k:
                print('FALLA: %s cambio %d: %d apariciones; no se toca nada.' % (r, i, t.count(v))); return 1
            t = t.replace(v, n)
        if sha(t.encode('utf-8')) != fin:
            print('FALLA: %s no da el sha256 final; no se toca nada.' % r); return 1
        nuevos[r] = t.encode('utf-8')
    if modo == '--check':
        print('APLICABLE: %s (%d cambios) y %s (%d cambio).' % (MAKEFILE_RUTA, len(MAKEFILE_CAMBIOS), VEREDICTO_RUTA, len(VEREDICTO_CAMBIOS))); return 0
    for r, c in nuevos.items():
        f = os.path.join(raiz, r); tmp = f + '.d317tmp'
        with open(tmp, 'wb') as o: o.write(c)
        os.chmod(tmp, os.stat(f).st_mode & 0o7777); os.replace(tmp, f); print('  escrito  %s' % r)
    print('APLICADO: 2 ficheros.'); return 0

if __name__ == '__main__':
    sys.exit(main())
