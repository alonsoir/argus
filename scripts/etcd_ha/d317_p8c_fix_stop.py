#!/usr/bin/env python3
# d317_p8c_fix_stop.py — paso 8 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): mitre-check para el pipeline antes de arrancarlo (pipeline-start no
# admite un pipeline ya arrancado: «duplicate session: ml-detector», medido DAY317). Requiere 8c.
# Uso:  python3 d317_p8c_fix_stop.py --check <raiz_repo>
#       python3 d317_p8c_fix_stop.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si el fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

RUTA = 'Makefile'
SHA_PREVIO = '472f73246823b16bb19808221916f793dcaba3ec878778549652bc29313371f0'
SHA_FINAL = '8f96a48b5b30191eeccde748e9b3e6fb77a5d43c9e064ad753814af4275307d3'
CAMBIOS = [('\t@$(MAKE) --no-print-directory pipeline-start > /tmp/argus_mitre_check_start.txt 2>&1 || ', '\t@# [EMECAS-TODO-D317] pipeline-start no admite un pipeline ya arrancado (duplicate session, medido DAY317): se para\n\t@# antes, como en los E2E del lab, y el Acto IV parte siempre de un pipeline limpio\n\t@$(MAKE) --no-print-directory pipeline-stop > /tmp/argus_mitre_check_stop.txt 2>&1 || { tail -n 20 /tmp/argus_mitre_check_stop.txt; echo "[MITRE-VEREDICTO] FALLA: pipeline-stop"; exit 1; }\n\t@$(MAKE) --no-print-directory pipeline-start > /tmp/argus_mitre_check_start.txt 2>&1 || ', 1)]
NUEVOS = {}   # {ruta: contenido} que se crean (0755)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
    if not os.path.isfile(p(RUTA)):
        print('FALLA: no existe %s; no se toca nada.' % RUTA); return 1
    b = open(p(RUTA), 'rb').read()
    nuevos_ya = all(os.path.isfile(p(r)) and open(p(r), 'rb').read() == c.encode() for r, c in NUEVOS.items())
    if sha(b) == SHA_FINAL and nuevos_ya:
        print('YA APLICADO: no se toca nada.'); return 0
    if sha(b) != SHA_PREVIO:
        print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (RUTA, sha(b)[:16])); return 1
    for r in NUEVOS:
        if os.path.exists(p(r)):
            print('FALLA: %s ya existe; no se toca nada.' % r); return 1
    t = b.decode('utf-8')
    for i, (v, n, k) in enumerate(CAMBIOS, 1):
        if t.count(v) != k:
            print('FALLA: cambio %d: %d apariciones (se exigen %d); no se toca nada.' % (i, t.count(v), k)); return 1
        t = t.replace(v, n)
    nuevo = t.encode('utf-8')
    if sha(nuevo) != SHA_FINAL:
        print('FALLA: el resultado no da el sha256 final; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: %s (%d cambios)%s.' % (RUTA, len(CAMBIOS), ''.join(' + %s nuevo' % r for r in NUEVOS))); return 0
    for r, c in NUEVOS.items():
        tmp = p(r) + '.d317tmp'
        with open(tmp, 'wb') as o: o.write(c.encode('utf-8'))
        os.chmod(tmp, 0o755); os.replace(tmp, p(r)); print('  creado   %s' % r)
    tmp = p(RUTA) + '.d317tmp'
    with open(tmp, 'wb') as o: o.write(nuevo)
    os.chmod(tmp, os.stat(p(RUTA)).st_mode & 0o7777); os.replace(tmp, p(RUTA))
    print('APLICADO: %s (sha256 %s)%s.' % (RUTA, SHA_FINAL[:16], ''.join(' + %s' % r for r in NUEVOS))); return 0

if __name__ == '__main__':
    sys.exit(main())
