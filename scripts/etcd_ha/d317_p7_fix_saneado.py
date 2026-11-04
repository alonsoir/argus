#!/usr/bin/env python3
# d317_p7_fix_saneado.py — paso 7 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): arreglo del instrumento d317_reinicio_vm.sh.
# La corrida reinicio_vm_1 paró en la verificación: vagrant ssh antepone una línea vacía y T1 llegó como «\n<epoch>»,
# partiendo la orden del ayudante. Se sanea cada valor capturado (T1 solo dígitos; horas de la VM, la línea con fecha) y
# se para con mensaje claro si alguno sale vacío; el wc de macOS sin relleno de espacios.
# Uso:  python3 d317_p7_fix_saneado.py --check <raiz_repo>
#       python3 d317_p7_fix_saneado.py --apply <raiz_repo>
# Todo o nada; idempotente.
import hashlib, os, sys

RUTA = 'scripts/etcd_ha/d317_reinicio_vm.sh'
SHA_PREVIO = '270106c7f2cc464054a07c7fac7f06a2e804b1c0610bdebb4987d893d164793e'
SHA_FINAL = '0abf6ccd909d3b9468b10dfdd824926aec17556c19a4c44fd9e067b9fd0ce22e'
CAMBIOS = [('TV0=$(vme "date -u \'+%Y-%m-%d %H:%M:%S UTC\'"); [ -n "$TV0" ] || falla "no leo la hora de la VM etcd"', '# [REINICIO-VM-D317b] vagrant ssh antepone una línea vacía: cada valor capturado se sanea (reinicio_vm_1 paró por eso)\nTV0=$(vme "date -u \'+%Y-%m-%d %H:%M:%S UTC\'" | grep -E \'^[0-9]{4}-\' | tail -n 1); [ -n "$TV0" ] || falla "no leo la hora de la VM etcd"'), ('TV1=$(vme "date -u \'+%Y-%m-%d %H:%M:%S UTC\'")', 'TV1=$(vme "date -u \'+%Y-%m-%d %H:%M:%S UTC\'" | grep -E \'^[0-9]{4}-\' | tail -n 1); [ -n "$TV1" ] || falla "no leo la hora de la VM etcd (arranque)"'), ('T1=$(def "date +%s")', 'T1=$(def "date +%s" | tr -dc \'0-9\'); [ -n "$T1" ] || falla "no leo la hora del defender"'), ('echo "[$TAG] etcd-server.log: $(wc -l < "$L/etcd-server.log") líneas; etcd-server-tras.log: $(wc -l < "$L/etcd-server-tras.log")"', 'echo "[$TAG] etcd-server.log: $(wc -l < "$L/etcd-server.log" | tr -d \' \') líneas; etcd-server-tras.log: $(wc -l < "$L/etcd-server-tras.log" | tr -d \' \')"')]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    f = os.path.join(raiz, RUTA)
    if not os.path.isfile(f):
        print('FALLA: no existe %s; no se toca nada.' % RUTA); return 1
    b = open(f, 'rb').read()
    if sha(b) == SHA_FINAL:
        print('YA APLICADO: no se toca nada.'); return 0
    if sha(b) != SHA_PREVIO:
        print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (RUTA, sha(b)[:16])); return 1
    t = b.decode('utf-8')
    for i, (v, n) in enumerate(CAMBIOS, 1):
        if t.count(v) != 1:
            print('FALLA: cambio %d: %d apariciones; no se toca nada.' % (i, t.count(v))); return 1
        t = t.replace(v, n)
    nuevo = t.encode('utf-8')
    if sha(nuevo) != SHA_FINAL:
        print('FALLA: el resultado no da el sha256 final; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: %s (%d cambios).' % (RUTA, len(CAMBIOS))); return 0
    tmp = f + '.d317tmp'
    with open(tmp, 'wb') as o: o.write(nuevo)
    os.chmod(tmp, os.stat(f).st_mode & 0o7777); os.replace(tmp, f)
    print('APLICADO: %s (sha256 %s).' % (RUTA, SHA_FINAL[:16])); return 0

if __name__ == '__main__':
    sys.exit(main())
