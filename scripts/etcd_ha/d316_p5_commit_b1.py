#!/usr/bin/env python3
# d316_p5_commit_b1.py — DEBT-ETCD-HA-TLS-RAFT-001 paso 5, commit B1 ([ETCD-CLIENTE-B1-D316]).
# Mantenedor en la librería (un ritmo: heartbeat_interval_seconds; registro, latido, reconexión y subida de la config del
# JSON de arranque), AvisoBloqueFatal, ningún componente sale ni espera por etcd (G1-G3), fuera la semilla muerta del
# sniffer (G5), clave del firewall por /secrets/<CN>; tests R1-R8.
# Uso:  python3 d316_p5_commit_b1.py --check <raiz_repo>
#       python3 d316_p5_commit_b1.py --apply <raiz_repo>
# Todo o nada: comprueba el sha256 previo de cada fichero, aplica el diff en memoria, comprueba el sha256 final de
# cada uno y solo entonces escribe (fichero temporal + rename). Idempotente: si todo está ya en su estado final, no toca nada.
import base64, gzip, hashlib, json, os, re, sys

TABLA = [  # (ruta, sha256 antes ('' = no existe), sha256 después ('' = se borra))
    ('etcd-client/include/etcd_client/etcd_client.hpp', '715ef5cd9f594718d4c47c795b8925c5fd0e73a30d9d341adb2f8e5e1670b67f', '43ecf1a99469c31fa181fa6c3b674ec83915292e4a91e643ee070e7e516aea13'),
    ('etcd-client/src/etcd_client.cpp', 'f1b79e20ca1f27e1c1d0bc377510b4cfcc7e95d64dc2ba94f56b7c576242c027', '8d575efba9bb9787249cd59a6df4a141088fae140eb68e9502493176aca1038f'),
    ('etcd-client/src/http_client.cpp', 'b399b49f462356141309a33511e1afb88f87d33c112cc638ebb6feb376be147e', '6b8358118d51d6911366f7b50c9511da9d2e0b325700d387d634f28f52ba9fc8'),
    ('etcd-client/src/transporte.hpp', '7be94ff6d15d493ec19618186c25cf127dd5c85bac49b474b2f116046f8b741a', 'eb55f0e923d212671594d2b26eefb049334d89ea7954550da20e81651491bfcd'),
    ('etcd-client/tests/test_etcd_cliente_tls.cpp', 'a37a03f15cccbcc497c03a84678291eff80e6e1ec0aabd0e51d74b0c15ec2f23', '46716d183fc78e41dfcce101e6ff24aea62d1cffbf7c9d6fed1897e8d8467e5a'),
    ('firewall-acl-agent/include/firewall/etcd_client.hpp', '8f7cb1d613ce2a0eaf0e458ea29d87cd02e0b7a9888aadc44263fe8d42b759a9', 'f376210323ac08c9c0d75511e654b50be0bdd4237392e9f82c42ca8bd00095f4'),
    ('firewall-acl-agent/src/api/zmq_subscriber.cpp', 'f19e978faef2894e4494f587463337ee26fd5277036fc0f62ae58975f89119f6', '8749f1f13741b5727087fd5d1985d79f15cd1e93272dbbc05eee08596cc5ec04'),
    ('firewall-acl-agent/src/core/etcd_client.cpp', '2e56f7eff5fc928146ba4cbeb703b4d3be31a9d8f94116585404425e97b7892d', '2a4f78ee15601e339e37213e1c522e974b418c989fa5fc9071cd150886a4c315'),
    ('firewall-acl-agent/src/main.cpp', '5fae4c923c36064f74ab3d69ae505cd1dd00086e222e6046e2f3931387bd8369', '8fa571782cb9438d933b4aec111362b8e3f95e4b932ea9a7aeb2fe8e7d94b540'),
    ('ml-detector/include/etcd_client.hpp', '67be995047e1084aaad062c578484e21ba9895011533ace74cf4d8ddee8bc1f7', '4d62ea6dc8197550f834e4863a9b118941972615b30a05ac3aed38afeca1b998'),
    ('ml-detector/src/etcd_client.cpp', '063f461ab1227cf7eac43ad907ef14b7da7753f388e1dcb1a6c552ff21220e2e', 'e7cf8b3324386852f43839c7f3892b69d601b126711a4d4854f51dfd188b247d'),
    ('ml-detector/src/main.cpp', '01e7def41db3decaa503c00c7bfb9916133c9bc6f054ac41c1f0e47c884e25aa', '79ab809b01a39cd7446dfe0e9f700c4da68f28b93d0ddb8126cf29dd9d15b536'),
    ('sniffer/include/etcd_client.hpp', '8c98cccab4419c12585264ea833ce55b6d187e48af0583492c16e5231d953fb5', '467eca557f17992d06cffcae4eacc981aef8575df290e3e383a9fcbc8e15eef4'),
    ('sniffer/include/ring_consumer.hpp', '3c1a2e9169fd5ef2d99ebbc67aa322be72ac1f6495b7af1046f8176fb3918067', 'b4d0e5ea97f125447945e0eb3ca7734558dc81aaec3d7402bedd0cae03de6912'),
    ('sniffer/src/userspace/etcd_client.cpp', '6083d1ad606037e676d01be158851fa02c6f84b5f347a8604e9bb1f756a004f2', '5694d3f0523ae782ddfd4b8f504bf184930bdbf80149375c67ccb663eb23e3fe'),
    ('sniffer/src/userspace/main.cpp', 'c9afde749e21d1f24481e6095ca8b9a7187776ed1a4a2a3dccaf25eb052906f0', 'ba6e0e3342e664ba5a5e1ffd2f710dcb49ec854009e05bb69f43b036663f7f00'),
    ('sniffer/src/userspace/ring_consumer.cpp', '33e1c4533081e14dbd05e0757cc0a395cef1549af49c79756a06625d093345af', '3fd163970c70a73096c4517a7d503b785fbfb49aed66e7d7ee3d4371c5ef96b5'),
]
BLOB = """
H4sIAAAAAAAC/+19bXMbSXLmX6mRY+TGEAAJvugFkLhLkdQMbb3QpDQba0mBaAINsiUAjUUDHHFkbvjL3Yc7x5193ouNuLDDtxG+
Dw7HxsXFfrmwv63+yfyB259wmVlVXS9d1d0gQY13vNpZiQS66yUrKysr88nMD7eiWa/f6A3jaDxbjce94bwfreJnXfGZ9nPzbDK5
1Wa3Go0GC1cXfPH1eGVlhZ0s/tqPf8wa99bqd9gK/L2+xn7849djtrrKDk7n4bDO+lHaj1g0ZLPo/Sxhf3L8/Bl8NmQnw+Rn84gF
k3AasmGSsl4ymiRjaDZKGX4zjKIxS+f8jV4yZm/TZNybTGrQ/JOoN5tPw0e8DXhy2uXtdXF4ATydzlg667fb6Wwaj09vi+662Ead
f5PAV1E4ug2dn9Y60ChQAIb9av/F7l5j98nB/rMX+41HrcbeRuvOG/blepvNx3LU2AuNqRfCoFM2CGfhEMY9ThjNB+Y3mSa9KE2a
7CmSahqm7Dw+h2/SWcSSk7cR0CKN2DSaxLOI99wL+yGLYf7T83CYdFP22382B/N458XOkzfswe6z7XZuJA/G2/Zoms1mB4eiKMvS
+HSOf4/pxd/+a5N3TWvFgN64EEAWYzXwmd4wTFO2cx6nCSf6Y+yDfYCvJvOTYdxrw08M/tiPBNoqaI3CGsTfRt2ZHGsdJ25M/iHb
WMNloVZ/nms2+yr3DV98++PbNWgR+C6aRb43b7NkEk3DWTJ9WK2RyRRWdBbJqcMk570ZOxhNhp3sI5j8fBwj601m0wf43TabyEcu
8S++W56GsCb7sCa7tLUYERy+4oTXvgCSs4zkuPdaa636fbbSam3VW3f57sM/0OZuMh7DRomBO56G4/A0GkED6uuHS/rDt45o1LN9
enwoQQ13UUiMME1Owl788TdjoChbPYvC4eyMBRchbiJ4vB/3YODwG+yKWpPFaVe0EfWxlWl0GgPBw36i+r5gw3AGROrDruvHqdan
3JSjEDhsHPWTaVPQ4SRJhmp0Hf1Ts0tGLCEfOE/ivtFHp5QEX7YaX26wYG/np/ArjCmcTsNxj4Z1Fg8TbWwwkfN5NDyH3T1Oo9N5
3A+bbBfooPoAck1nJ1E468o9000jpFqqk6ZOBOknHdrxKTyHRKW9BpwQZk9OQRIFCfwajuf9cIpD4i/Ce/CL6la8QKIL6QEtfvwN
rM7+mEsv9f38hIS+EPdsOp+FSM1BfMoC+Bw+ovmjCOsraUlUVt115QCRh5uzi0kE+28WT2B9nySnMFWT1E934O9n+3vPj97UWeNo
/8uD4xdHO3vP4Zfjg2eN4/2jrw92D57TdzvPXu7hV6oz+cLzxuH+0d4Bvbb7/Nnjgy8bz543jl8+OtjbgY8e7fzJDgtCnAJu+Bho
VycypbPwJNSIX2uKtolX4jGQPpy6jiaNNnXm+B4nLA6oG9i6osU/jS4aX4dDWI7nJASB4CB+btWZoYCk056hAPR8CofjQZeC4XyM
hNomKhTw930u0f5IqCLsQcqP7W3jwziB3RNPzA9Bko/iHny2oj7rnU2TcWJ9NotHkfnRQHUCtNnZO2qstTbY4Vc7x/tsnX33l79g
sI3Z/Xtttju9mMySF8DK6SSZzuCQD9lxFElpHaTzdBbP5heReJIL4mmNt7y3f3i0v7vzYn9PNEht9+jJ7og/ilpWW03r9S3x9Uz2
uZp//vUtk2YwIKm/aT/jk9uc3pvr9dYaW9ncqosjBP4T55k6e9ptPLjoBMI/u3w7c87tAoM2BC+5ZxWNaZzAWN130UWXCcqglIFZ
6ERbsamqmta1CatBOQBdosNUQWIMwmEaya9HsNtOhhFvCX6J3jP6uysluP8BPgKSonCch7OztAuiGhWseIA7HqVaGg5jFNRyX/l5
RzxjqwijYbcfDeAQi6bttiLKNlN/tCXsdjzN2EzSbls03WYzmjOu/tZGvdViK/DPesvQIPbCC7Z1vw2LQ5PmJ955NL1gNH02mCYj
0iQbSJZoKt4Ujx/SMybB5HizcUQsG2MkSGxKdTo9FQd8JU8+NjuDPdoX39D8+Sfa4cg/yFiDHuJi4QGyybb26HQ+HgNXdT8Qt1wa
r3AuODvpjmbEBsYfHPDhDpwzO42DZ0/39w5AS4dBr629gTMBZSlXa6fz0SRGvsLjLutW74WUHmLn83AaEw9Cl71z6tHfS6nioRQL
usKgslHHH6bxbJSwwK9K1EFngcP9KDvS2kItaLLjWDumpWLRXkyxuMB7nzg3UYfItAA2npNixKk3jnFTRSQk4GEY8Zfr2dlKhJtG
vfk0jc+jLl8oeKo7ytYJBoh90PbUNcAO9j5Pw3GmgV2IcUfT1flY/tjNLi16lwYTqTNf456VTBZpX2PnqRJJcnhDfQ/hsGbz80R7
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
"""

def sha(b):
    return hashlib.sha256(b).hexdigest()

def leer(raiz, p):
    f = os.path.join(raiz, p)
    return open(f, 'rb').read() if os.path.isfile(f) else None

def lineas(s):  # solo '\n' separa líneas (str.splitlines corta también en \r, \x0c, \u2028...)
    return re.findall(r'[^\n]*\n|[^\n]+$', s)

def parches():
    d = json.loads(gzip.decompress(base64.b64decode(''.join(BLOB.split()))).decode())
    return {p: lineas(txt)[2:] for p, txt in d.items()}  # sin la cabecera ---/+++

def aplicar(antes, ls):
    viejo = lineas(antes.decode()) if antes is not None else []
    nuevo, pos, i = [], 0, 0
    while i < len(ls):
        m = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', ls[i]); i += 1
        ini = int(m.group(1)); cnt = int(m.group(2) or 1)
        ini0 = ini - 1 if cnt > 0 else ini
        nuevo.extend(viejo[pos:ini0]); pos = ini0
        while i < len(ls) and not ls[i].startswith('@@'):
            l = ls[i]
            if l[0] == ' ':
                assert viejo[pos].rstrip('\n') == l[1:].rstrip('\n'); nuevo.append(viejo[pos]); pos += 1
            elif l[0] == '-':
                assert viejo[pos].rstrip('\n') == l[1:].rstrip('\n'); pos += 1
            elif l[0] == '+':
                nuevo.append(l[1:])
            elif l[0] == '\\':
                prev = ls[i - 1][0]
                if prev in ' +' and nuevo and nuevo[-1].endswith('\n'):
                    nuevo[-1] = nuevo[-1][:-1]
            i += 1
    nuevo.extend(viejo[pos:])
    return ''.join(nuevo).encode()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    if not os.path.isfile(os.path.join(raiz, 'etcd-client/src/http_client.cpp')):
        sys.exit('FALLA: %s no parece la raíz del repo' % raiz)
    previos, finales, otros = [], [], []
    for p, a, d in TABLA:
        b = leer(raiz, p)
        h = sha(b) if b is not None else ''
        if h == d: finales.append(p)
        if h == a: previos.append(p)
        if h != a and h != d: otros.append((p, h))
    if len(finales) == len(TABLA):
        print('YA APLICADO: los %d ficheros están en su estado final; no se toca nada.' % len(TABLA)); return 0
    if otros or len(previos) != len(TABLA):
        print('FALLA: el árbol no está en el estado esperado; no se toca nada.')
        for p, h in otros:
            print('  inesperado: %s (sha256 %s)' % (p, h[:16] or 'no existe'))
        for p in finales:
            if p not in previos: print('  ya en estado final (mezcla): %s' % p)
        return 1
    ps = parches()
    nuevos = {}
    for p, a, d in TABLA:
        try:
            c = aplicar(leer(raiz, p), ps[p]) if d else None
        except Exception as e:
            print('FALLA: no se pudo aplicar el diff a %s (%s); no se toca nada.' % (p, e)); return 1
        if (sha(c) if c is not None else '') != d:
            print('FALLA: el resultado de %s no da el sha256 esperado; no se toca nada.' % p); return 1
        nuevos[p] = c
    cambian = sum(1 for p, a, d in TABLA if a and d)
    crea = sum(1 for p, a, d in TABLA if not a)
    borra = sum(1 for p, a, d in TABLA if not d)
    if modo == '--check':
        print('APLICABLE: %d ficheros (%d cambian, %d nuevos, %d se borran); sha256 previos y finales verificados en memoria.'
              % (len(TABLA), cambian, crea, borra)); return 0
    for p, c in nuevos.items():
        f = os.path.join(raiz, p)
        if c is None:
            os.remove(f)
            dd = os.path.dirname(f)
            if os.path.isdir(dd) and not os.listdir(dd): os.rmdir(dd)
            print('  borrado  %s' % p); continue
        os.makedirs(os.path.dirname(f), exist_ok=True)
        modo_f = os.stat(f).st_mode & 0o7777 if os.path.exists(f) else 0o644
        t = f + '.d316tmp'
        with open(t, 'wb') as o: o.write(c)
        os.chmod(t, modo_f); os.replace(t, f)
        print('  %s %s' % ('escrito ' if os.path.exists(f) else 'creado  ', p))
    mal = [p for p, a, d in TABLA if (sha(leer(raiz, p)) if leer(raiz, p) is not None else '') != d]
    if mal:
        print('FALLA tras escribir: %s' % ', '.join(mal)); return 1
    print('APLICADO: %d ficheros en su estado final (sha256 verificados).' % len(TABLA)); return 0

if __name__ == '__main__':
    sys.exit(main())
