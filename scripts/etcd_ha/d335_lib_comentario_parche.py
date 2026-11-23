#!/usr/bin/env python3
# d335_lib_comentario_parche.py — [TERCEROS-ATOMIC-FUERA-D335] la cabecera de lib_git_fijado.sh nombraba atomic-red-team
# como usuario futuro; tras sacarlo del lab (066c252), ya no lo es.
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_lib_comentario_parche.py
import hashlib, pathlib, sys

F = 'scripts/terceros/lib_git_fijado.sh'
PARTIDA = 'b53dd80cb7298c153071dbae03e5d89afe59d39a118126d21d5be003f30e61e3'
LLEGADA = '86241f725fc77c196dadfa4b4322c25fcc0df4e5dda9e951b3984bcfc3d712dd'
VIEJO = '# a los instaladores que traen código fuente de terceros por git (libbpf; después cpp-httplib, etcd-cpp-apiv3 y\n# atomic-red-team). Un tag ligero no lleva firma y se puede mover (lección DAY334): se fija el commit al que apunta y se\n'
NUEVO = '# a los instaladores que traen código fuente de terceros por git (libbpf, cpp-httplib y etcd-cpp-apiv3). Un tag ligero\n# no lleva firma y se puede mover (lección DAY334): se fija el commit al que apunta y se\n'

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    b = pathlib.Path(F).read_bytes()
    if sha(b) != PARTIDA:
        sys.exit(f'FALLA: {F} sha256 de partida {sha(b)}, se espera {PARTIDA}. Nada escrito.')
    t = b.decode()
    if t.count(VIEJO) != 1:
        sys.exit(f'FALLA: {F}: el ancla aparece {t.count(VIEJO)} veces, se espera 1. Nada escrito.')
    t = t.replace(VIEJO, NUEVO)
    if sha(t.encode()) != LLEGADA:
        sys.exit(f'FALLA: {F} sha256 de llegada {sha(t.encode())}, se espera {LLEGADA}. Nada escrito.')
    pathlib.Path(F).write_bytes(t.encode())
    print(f'OK {F} {LLEGADA}')

if __name__ == '__main__':
    main()
