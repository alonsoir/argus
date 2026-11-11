#!/usr/bin/env python3
# d317_6c_status.py — paso 6c de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): pipeline-status enseña el estado real de la VM etcd
# (etcd-server, cada miembro etcd con líder y retraso, Vault de las claves HMAC). Requiere 6b aplicado.
# docs/ml-heads/day312_diseno.md, «Diseño del paso 6».
# Uso:  python3 d317_6c_status.py --check <raiz_repo>
#       python3 d317_6c_status.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si cada fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

MAKEFILE_PREVIO = '609094ff92b6d776e9d46d9f5c6d721d196aee51251dafdaf52c5052a6f341e0'
MAKEFILE_FINAL = 'c13e757ebdf4562482b1f9b68cd6ffa529dfecee393e0765261de4aaf114cbe0'
CAMBIOS = [('\t@vagrant ssh -c "( tmux has-session -t etcd-server 2>/dev/null || pgrep -x etcd-server >/dev/null 2>&1 ) && echo \'  ✅ etcd-server:   RUNNING\' || echo \'  ❌ etcd-server:   STOPPED\'"\n', '\t@# [ETCD-VM-D317] VM etcd: etcd-server (systemd + /health), cada miembro etcd (sano, líder, retraso) y Vault de las claves HMAC\n\t@vagrant ssh etcd -c "bash /vagrant/scripts/etcd_ha/etcd_vm_estado.sh" 2>/dev/null | grep -E \'^  (✅|❌|⚠️)|^       - \' || echo \'  ❌ etcd-server:   STOPPED [VM etcd parada o inalcanzable: vagrant up etcd]\'\n')]
NUEVOS = {}   # {ruta: contenido}: ficheros que se crean (0755)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    mk = os.path.join(raiz, 'Makefile')
    if not os.path.isfile(mk):
        print('FALLA: no existe %s; no se toca nada.' % mk); return 1
    b = open(mk, 'rb').read()
    nuevos_ya = all(os.path.isfile(os.path.join(raiz, r)) and open(os.path.join(raiz, r), 'rb').read() == c.encode()
                    for r, c in NUEVOS.items())
    if sha(b) == MAKEFILE_FINAL and nuevos_ya:
        print('YA APLICADO: no se toca nada.'); return 0
    if sha(b) != MAKEFILE_PREVIO:
        print('FALLA: Makefile no está en el estado esperado (sha256 %s); no se toca nada.' % sha(b)[:16]); return 1
    for r in NUEVOS:
        if os.path.exists(os.path.join(raiz, r)):
            print('FALLA: %s ya existe con otro contenido; no se toca nada.' % r); return 1
    t = b.decode('utf-8')
    for i, (v, n) in enumerate(CAMBIOS, 1):
        if t.count(v) != 1:
            print('FALLA: el cambio %d encuentra su texto %d veces (se exige 1); no se toca nada.' % (i, t.count(v))); return 1
        t = t.replace(v, n)
    nuevo = t.encode('utf-8')
    if sha(nuevo) != MAKEFILE_FINAL:
        print('FALLA: el Makefile resultante no da el sha256 final; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: Makefile (%d cambios)%s.' % (len(CAMBIOS), ''.join(' + %s nuevo' % r for r in NUEVOS))); return 0
    for r, c in NUEVOS.items():
        f = os.path.join(raiz, r); tmp = f + '.d317tmp'
        with open(tmp, 'wb') as o: o.write(c.encode('utf-8'))
        os.chmod(tmp, 0o755); os.replace(tmp, f); print('  creado   %s' % r)
    tmp = mk + '.d317tmp'
    with open(tmp, 'wb') as o: o.write(nuevo)
    os.chmod(tmp, os.stat(mk).st_mode & 0o7777); os.replace(tmp, mk); print('  escrito  Makefile')
    if sha(open(mk, 'rb').read()) != MAKEFILE_FINAL:
        print('FALLA tras escribir el Makefile'); return 1
    print('APLICADO: Makefile (sha256 %s)%s.' % (MAKEFILE_FINAL[:16], ''.join(' + %s' % r for r in NUEVOS))); return 0

if __name__ == '__main__':
    sys.exit(main())
