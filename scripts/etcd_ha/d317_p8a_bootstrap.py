#!/usr/bin/env python3
# d317_p8a_bootstrap.py — paso 8 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): bootstrap (eBPF y libpcap) despliega el etcd-server en la VM etcd
# antes de test-provision-1 y pipeline-start ([6c/8]); fuera la línea de emecas que lo hacía después.
# Uso:  python3 d317_p8a_bootstrap.py --check <raiz_repo>
#       python3 d317_p8a_bootstrap.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si el fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

RUTA = 'Makefile'
SHA_PREVIO = '9967e05fa845f61298a0330e2f8c5498c0fa2b7ca0c948c32fa73bb3024ce895'
SHA_FINAL = 'b747a9ba56f216f2e59ba796aa1e850612be231a37745e34a173cc1757ceee5a'
CAMBIOS = [('\t@$(MAKE) sign-plugins\n\t@echo "[7/8] Verificando provisioning..."\n', '\t@$(MAKE) sign-plugins\n\t@echo "[6c/8] Desplegando el etcd-server en la VM etcd (binario, configuración, servicio)..."\n\t@$(MAKE) etcd-vm-deploy  # [ETCD-VM-D317] antes de pipeline-start: los componentes encuentran el etcd-server sano\n\t@echo "[7/8] Verificando provisioning..."\n', 2), ('\t$(MAKE) etcd-vm-deploy  # [ETCD-VM-D317] binario + config + servicio en la VM etcd; falla si no queda sano\n', '', 1)]
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
