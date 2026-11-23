#!/usr/bin/env python3
# d335_atomic_fuera_parche.py — [TERCEROS-ATOMIC-FUERA-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 (decisión de
# Alonso DAY335): el Vagrantfile deja de clonar Atomic Red Team en el client (sin commit fijado, 419 MB, y nada lo usa) y
# lo quita de la lista de herramientas. Va encima de la lente etcd-cpp-apiv3 (d335_etcdcpp_parche.py).
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_atomic_fuera_parche.py
# Comprueba el sha256 de partida, cada ancla las veces exactas, el sha256 de llegada, y no escribe nada si algo falla.
import hashlib, pathlib, sys

F = 'Vagrantfile'
PARTIDA = '2b6bcc6fc23f8ec199d4017e93d59a5f3f2389c83ad33e6d98136f7831052982'
LLEGADA = 'ac0869bc3e617356ac8cb8229303cb123b7c2a725160b3cf4bd1d2cda9616f6b'
CAMBIOS = [
    ('          # Atomic Red Team (ground truth reproducible — DEBT-ARGUSPP-MITRE-001)\n          if [ ! -d /opt/atomic-red-team ]; then\n            git clone --depth 1 \\\n              https://github.com/redcanaryco/atomic-red-team.git \\\n              /opt/atomic-red-team || \\\n              echo "⚠️  atomic-red-team clone failed — red team offline mode"\n          fi\n\n',
     '          # [TERCEROS-ATOMIC-FUERA-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001 (decisión de Alonso DAY335): aquí se\n          # clonaba Atomic Red Team (rama principal, --depth 1, sin commit fijado, 419 MB medidos DAY335) en\n          # /opt/atomic-red-team, y nada lo usaba (git grep: ni mitre-start ni ningún script). Entrará, con su commit\n          # fijado, cuando empiece RESEARCH-MITRE-ATTACK-RANSOMWARE-001.\n\n'),
    ('          echo "   Tools   : nmap hydra sqlmap tcpreplay atomic-red-team"\n', '          echo "   Tools   : nmap hydra sqlmap tcpreplay"\n'),
]

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    b = pathlib.Path(F).read_bytes()
    if sha(b) != PARTIDA:
        sys.exit(f'FALLA: {F} sha256 de partida {sha(b)}, se espera {PARTIDA}. Nada escrito.')
    t = b.decode()
    for viejo, nuevo in CAMBIOS:
        n = t.count(viejo)
        if n != 1:
            sys.exit(f'FALLA: {F}: el ancla aparece {n} veces, se espera 1:\n{viejo[:120]}\nNada escrito.')
        t = t.replace(viejo, nuevo)
    if sha(t.encode()) != LLEGADA:
        sys.exit(f'FALLA: {F} sha256 de llegada {sha(t.encode())}, se espera {LLEGADA}. Nada escrito.')
    pathlib.Path(F).write_bytes(t.encode())
    print(f'OK {F} {LLEGADA}')

if __name__ == '__main__':
    main()
