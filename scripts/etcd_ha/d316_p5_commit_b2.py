#!/usr/bin/env python3
# d316_p5_commit_b2.py — DEBT-ETCD-HA-TLS-RAFT-001 paso 5, commit B2 ([FW-CSV-CLAVE-B2-D316]).
# Cierra DEBT-FW-HMAC-KEY-ALARM-001 (G4): el firewall pide su clave HMAC del CSV cada hmac_key.check_interval_seconds
# (ClaveCsv, hilo propio) y escribe un CSV por clave (firewall_blocks-<fecha>-<huella>.csv); generate_parquet.py los lee
# todos (sin ninguno: [PARQUET-SIN-CSV] / [PARQUET-SIN-DATOS], rc 0, decisión H1 b); la librería registra la ruta absoluta
# del JSON de arranque.
# Uso:  python3 d316_p5_commit_b2.py --check <raiz_repo>
#       python3 d316_p5_commit_b2.py --apply <raiz_repo>
# Todo o nada: comprueba el sha256 previo de cada fichero, aplica el diff en memoria, comprueba el sha256 final de
# cada uno y solo entonces escribe (fichero temporal + rename). Idempotente: si todo está ya en su estado final, no toca nada.
import base64, gzip, hashlib, json, os, re, sys

TABLA = [  # (ruta, sha256 antes ('' = no existe), sha256 después ('' = se borra))
    ('etcd-client/src/etcd_client.cpp', '8d575efba9bb9787249cd59a6df4a141088fae140eb68e9502493176aca1038f', '1e46570c6c089df4bf96949e72c9b51e31a85efc270a39a19823d922c368746d'),
    ('firewall-acl-agent/CMakeLists.txt', '613c14dfde8c66bac625395f4530ef294e9097ad3dcd49b34a4d023d60f70ef8', '0ed5c214914c9987ddfe832be1adca727d0ca6f51ea3c64e2552c3b2d190de5f'),
    ('firewall-acl-agent/config/firewall.json', '38fc5ff4b849635e1a0437ce01339248258daa1b001f30ed86ee74ddba353b28', 'dd707ba81b3fbe32026718769cc607dea8b26168fb4df10afb6e4fa31513e5ad'),
    ('firewall-acl-agent/include/firewall/clave_csv.hpp', '', '8c8aa0bd7fe245d3f7f253bccac4d1392a6682d2b9baad0c59e0727fcaceeaa2'),
    ('firewall-acl-agent/include/firewall/config_loader.hpp', '36dd9fffa32d2f5e2912260564dcc06e1e4e7675243305bf6692d5ed32ee0e33', '18506e7406b2b4ccfcb62e38749054a1f064297ea3f7ebde0fa58ccede80336b'),
    ('firewall-acl-agent/include/firewall/logger.hpp', 'f196d9655dd090fe836fd69d47b477416cbc2bdb7ff038659f7b4e430ebb94d0', 'a4994ae819454732a72338f08e215d866821165ed2656e2ff19e08b155b1cf6e'),
    ('firewall-acl-agent/include/firewall/zmq_subscriber.hpp', '18d8bfba8b35dfa5977b1f5db5ed6adde84724ce436c08a8d595a7a48475bca5', 'e7a32394075f6cc7266475665813d1bf9eb0996ec6edaaf61468714b2d1f2717'),
    ('firewall-acl-agent/src/api/zmq_subscriber.cpp', '8749f1f13741b5727087fd5d1985d79f15cd1e93272dbbc05eee08596cc5ec04', 'f755f895496cf9f6fcda9376e9e44f1995fdce7d5cac8c87f2aebf85038449b4'),
    ('firewall-acl-agent/src/core/clave_csv.cpp', '', '15f94e93c30565539bb11109c4d62007a08a8193f759fb56663d4f83eb4d61a2'),
    ('firewall-acl-agent/src/core/config_loader.cpp', '1bd13010f84b0bda86cccbba48d9cf72f2ecbfc2aca6ec6c58da28f477ff68cb', '37adca63780f1f1ae7ff3bdfc9c513734bd39d2a2c1173bc0fe870a1f5aa9d33'),
    ('firewall-acl-agent/src/core/logger.cpp', '5a12fba284343c0bf7889fc65a24b13d80a2916e008239363ba0fbdd6e6c6bf1', 'c34f863e2903cef443653f6fbaf7ab499b05fcca880f1684646826920cbbad36'),
    ('firewall-acl-agent/src/main.cpp', '8fa571782cb9438d933b4aec111362b8e3f95e4b932ea9a7aeb2fe8e7d94b540', '794be18791252bf6658c56a4f7067bd90ef72da10005a4a3a21ce7f7227fc633'),
    ('firewall-acl-agent/tests/unit/test_clave_csv.cpp', '', '07a551866199cf354968237a3e5b4edf9c2193074c3e4da20e83420bdbaa873a'),
    ('scripts/parquet/generate_parquet.py', 'fc214434a2422363498b07236e92ea3f4fab06e7184b5b59ffb741832510012f', '50916fd5e71dd4ba2a2c05df317be1cdcda013f0c243cf8c39ad688ca8c46c90'),
    ('scripts/parquet/validate_roundtrip.py', '59454058bf5b33fb54b71ad8dc65b3f98ff099e780bea0f53c414c29770aff5a', '98db6b4a3e1d1f73494b4e932614ade9e08117329bd7ba83a43f7b634b959459'),
]
BLOB = """
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
pwRQGUmCkqa8lpX7/w8LWiTPV5UAAA==
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
