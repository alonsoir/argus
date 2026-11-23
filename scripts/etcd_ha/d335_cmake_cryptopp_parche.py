#!/usr/bin/env python3
# d335_cmake_cryptopp_parche.py — [TERCEROS-CMAKE-CRYPTOPP-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001: el
# Vagrantfile deja de bajar con wget, sin hash, el instalador de CMake 3.25.0 y el zip de Crypto++ 8.7.0 (ramas que no
# se ejecutaban: medido DAY335). Quedan la comprobación de cmake >= 3.20 y el apt-get de Crypto++, que paran si fallan.
# Va encima de terceros/d335-kuzu (63f588f).
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_cmake_cryptopp_parche.py
# Comprueba el sha256 de partida, cada ancla las veces exactas, el sha256 de llegada, y no escribe nada si algo falla.
import hashlib, pathlib, sys

F = 'Vagrantfile'
PARTIDA = '1770af4dd8044d84b282b71e0d1a8f087568a8d3db9a837fa26e522a84768556'
LLEGADA = '01783dec16c7620bcff037340c44b25315b642ec517529de7b54caf3d0e3d13d'
CAMBIOS = [
    ('      # CMake 3.25+\n      CMAKE_VERSION=$(cmake --version 2>/dev/null | head -1 | awk \'{print $3}\')\n      if [ -z "$CMAKE_VERSION" ] || [ "$(printf \'%s\\n\' "3.20" "$CMAKE_VERSION" | sort -V | head -n1)" != "3.20" ]; then\n        cd /tmp\n        wget -q https://github.com/Kitware/CMake/releases/download/v3.25.0/cmake-3.25.0-linux-x86_64.sh\n        sh cmake-3.25.0-linux-x86_64.sh --prefix=/usr/local --skip-license\n        rm cmake-3.25.0-linux-x86_64.sh\n      fi\n',
     '      # [TERCEROS-CMAKE-CRYPTOPP-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001: CMake viene de apt (en la lista\n      # de arriba; bookworm trae la 3.25.1). Antes, si faltaba o era < 3.20, se bajaba con wget el instalador 3.25.0 de\n      # GitHub, sin hash, y se ejecutaba como root. Medido DAY335: esa rama no se ejecutaba nunca (cmake 3.25.1 en\n      # /usr/bin, nada en /usr/local/bin). Queda la comprobación: sin cmake >= 3.20, para aquí.\n      CMAKE_VERSION=$(cmake --version 2>/dev/null | head -1 | awk \'{print $3}\')\n      if [ -z "$CMAKE_VERSION" ] || [ "$(printf \'%s\\n\' "3.20" "$CMAKE_VERSION" | sort -V | head -n1)" != "3.20" ]; then\n        echo "❌ cmake de apt: \'$CMAKE_VERSION\', se necesita >= 3.20"; exit 1\n      fi\n'),
    ('      # Crypto++\n      if [ ! -f /usr/include/cryptopp/cryptlib.h ] && [ ! -f /usr/local/include/cryptopp/cryptlib.h ]; then\n        apt-get install -y libcrypto++-dev libcrypto++-doc libcrypto++-utils || {\n          cd /tmp\n          wget https://www.cryptopp.com/cryptopp870.zip\n          unzip cryptopp870.zip -d cryptopp\n          cd cryptopp && make -j4 && make install\n        }\n      fi\n',
     '      # [TERCEROS-CMAKE-CRYPTOPP-D335] Crypto++ de apt (libcrypto++-dev; bookworm trae la 8.7.0). Antes, si apt\n      # fallaba, se bajaba con wget cryptopp870.zip de cryptopp.com, sin hash, y se compilaba e instalaba como root.\n      # Medido DAY335: esa rama no se ejecutaba (libcrypto++-dev en ii, nada en /usr/local/include/cryptopp). Si apt\n      # falla, para aquí.\n      if [ ! -f /usr/include/cryptopp/cryptlib.h ] && [ ! -f /usr/local/include/cryptopp/cryptlib.h ]; then\n        apt-get install -y libcrypto++-dev libcrypto++-doc libcrypto++-utils || { echo "❌ Crypto++ de apt"; exit 1; }\n      fi\n'),
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
