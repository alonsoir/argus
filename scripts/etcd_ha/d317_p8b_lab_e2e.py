#!/usr/bin/env python3
# d317_p8b_lab_e2e.py — paso 8 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): sexto E2E lab-e2e-reinicio-etcd (instrumento de reinicio de la VM
# etcd, veredicto PASA/FALLA) al final de lab-e2e, tras la restauración del pipeline. Requiere 8a.
# Uso:  python3 d317_p8b_lab_e2e.py --check <raiz_repo>
#       python3 d317_p8b_lab_e2e.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si el fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

RUTA = 'Makefile'
SHA_PREVIO = 'b747a9ba56f216f2e59ba796aa1e850612be231a37745e34a173cc1757ceee5a'
SHA_FINAL = '61c6ff18f3a2bba31f817d00c98645a72eccd4bad5637932e6f8ef58ca2bf4d3'
CAMBIOS = [('.PHONY: lab-e2e lab-e2e-prep lab-e2e-reinicio-antes lab-e2e-reinicio-ordenada lab-e2e-reinicio-kill9 lab-e2e-protegidos lab-e2e-mitigacion\n', '.PHONY: lab-e2e lab-e2e-prep lab-e2e-reinicio-antes lab-e2e-reinicio-ordenada lab-e2e-reinicio-kill9 lab-e2e-protegidos lab-e2e-mitigacion lab-e2e-reinicio-etcd\n', 1), ('lab-e2e:\n', '# [REINICIO-VM-D317] sexto E2E: reinicia el etcd-server de la VM etcd con el pipeline vivo (scripts/etcd_ha/d317_reinicio_vm.sh,\n# veredicto PASA/FALLA). Requiere el pipeline arrancado: va al final de lab-e2e, tras la restauración. El nombre de la\n# corrida lleva la fecha (el instrumento no reescribe una corrida y EMECAS se repite). ~10 min.\nlab-e2e-reinicio-etcd:\n\t@$(MAKE) lab-e2e-prep\n\tDIA=$(LAB_E2E_DIA) bash scripts/etcd_ha/d317_reinicio_vm.sh lab_reinicio_etcd_$$(date -u +%Y%m%dT%H%M%SZ)\n\nlab-e2e:\n', 1), ('\t@echo "[LAB-E2E] PASA los cinco E2E del lab $$(date \'+%F %T\')"\n', '\t$(MAKE) lab-e2e-reinicio-etcd\n\t@echo "[LAB-E2E] PASA los seis E2E del lab $$(date \'+%F %T\')"\n', 1), ('\t@echo "[LAB-E2E] inicio $$(date \'+%F %T\'): reinicio antes/ordenada/kill9, protegidos, mitigacion"\n', '\t@echo "[LAB-E2E] inicio $$(date \'+%F %T\'): reinicio antes/ordenada/kill9, protegidos, mitigacion, reinicio del etcd-server"\n', 1)]
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
