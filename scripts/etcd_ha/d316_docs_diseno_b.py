#!/usr/bin/env python3
# d316_docs_diseno_b.py — diseño del commit B del paso 5 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY316), escrito antes del código.
# Añade al final de docs/ml-heads/day312_diseno.md la sección «Diseño del commit B (paso 5)» y al final de docs/BACKLOG.md
# su resumen y DEBT-SNIFFER-LIBPCAP-ETCD-001.
# Uso:  python3 d316_docs_diseno_b.py --check <raiz_repo>
#       python3 d316_docs_diseno_b.py --apply <raiz_repo>
# Todo o nada; idempotente (si las dos secciones ya están, no toca nada).
import hashlib, os, sys

DISENO = '\n## Diseño del commit B (paso 5) — DAY316, escrito ANTES de tocar código\n\nObjetivo (estado deseado de Alonso, DAY316): el pipeline arranca y sigue protegiendo aunque no responda ningún etcd-server;\ncuando uno vuelve, cada componente se registra y recoge su clave HMAC solo. Va en dos commits: **B1** (librería y arranque de\nlos tres) y **B2** (clave del firewall; cierra DEBT-FW-HMAC-KEY-ALARM-001).\n\n### Medido para este diseño (código tras `fe99a7e70`)\n\n- Librería: `get_hmac_key()`, `set/get`, `register_component()` y el resto devuelven fallo si `connected_` es falso, y\n  `connected_` solo se pone en `connect()`. Un componente que arranca sin etcd-server no vuelve a intentarlo nunca (y el\n  sondeo de clave del ml-detector no la recogería aunque el servidor vuelva).\n- El hilo de latidos arranca solo tras un registro bueno; un latido fallido deja un aviso y nada más. El servidor responde\n  404 a un latido de un componente no registrado (`latir` → `NoEncontrado`); el registro vive en el etcd real, así que tras\n  reiniciar el etcd-server el componente sigue registrado.\n- `register_component()` hace `unlock()`/`lock()` a mano sobre el mutex de un `lock_guard`.\n- Sniffer: sin etcd sale en `main.cpp:687` («etcd integration is REQUIRED»). Ese bloque lee `seed.bin` para pasárselo a\n  `RingBufferConsumer`, que lo ignora desde DAY98 (parámetro comentado; el cifrado lo hace `SeedClient`). El sniffer no\n  pide clave HMAC.\n- ml-detector: sale sin etcd-server o con fatales. El sondeo de clave ya existe (`bronze_key.check_interval_seconds`,\n  `[BRONCE-SIN-CLAVE]`, `-SIN-CONFIRMAR`, `-CONFIRMADA`, `-RECUPERADA`, `-CAMBIADA`); el proveedor llama a\n  `etcd->get_hmac_key()` sin mirar si `etcd` es nulo.\n- Firewall: pide la clave una vez (`zmq_subscriber.cpp:88`, ruta sacada de la respuesta de `/register`); sin clave no\n  escribe filas y no la vuelve a pedir. Escribe todo en un único `firewall_blocks.csv` en modo añadir: con un cambio de\n  clave quedarían filas de dos claves en el mismo fichero. Lo lee `scripts/parquet/generate_parquet.py` (ruta fija).\n- Los envoltorios suben su config con rutas escritas en el código (sniffer `/vagrant/sniffer/config/sniffer.json`,\n  firewall `../config/firewall.json`).\n- El sniffer libpcap (`main_libpcap.cpp`) no habla con etcd.\n\n### Decisiones de Alonso (DAY316)\n\n- **G1.** Un hilo «mantenedor» en la librería sustituye al de latidos, con **un solo ritmo**: `heartbeat_interval_seconds`\n  (Alonso: el latido es cada cuánto se pregunta por el etcd-server, también para reconectar). Sin campos nuevos.\n- **G2.** Ninguno de los tres sale nunca por etcd. Deja atrás la decisión F1 de DAY310 (argumento del impostor): el cifrado\n  de ZMQ sale de `seed.bin` y no del registro, y los componentes se autentican ante el etcd-server con mTLS.\n- **G3.** Al registrarse (y al volver a registrarse) la librería llama a una función del envoltorio que sube la config del\n  JSON con el que arrancó el proceso. Que quede claro en el log.\n- **G4.** El firewall pide su clave como el ml-detector (mismo comportamiento y etiquetas equivalentes); **a**: al cambiar\n  la clave cierra el CSV y abre otro.\n- **G5.** Fuera el bloque muerto de la semilla del sniffer.\n- **G6.** Dos commits, B1 y B2, cada uno con sus tests en ctest y su medida en el laboratorio.\n- **G7.** El sniffer libpcap sin etcd: deuda aparte (DEBT-SNIFFER-LIBPCAP-ETCD-001).\n\n### B1 — librería y arranque\n\n- **Estados del mantenedor:** `SIN_SERVICIO` → (conecta y registra) → `REGISTRADO`. Cada `heartbeat_interval_seconds`:\n  - `REGISTRADO`: latido. 2xx: nada. 404: vuelve a registrarse (y a subir la config). Sin respuesta o 5xx en todas las\n    direcciones: pasa a `SIN_SERVICIO`.\n  - `SIN_SERVICIO`: intenta `/health` + `/register`. Bien: `REGISTRADO`, sube la config y deja\n    `[ETCD-CLIENTE-REGISTRADO] <CN> en <dirección> tras <s> s sin servicio, <n> intentos; config subida: <ruta JSON> (<bytes>)`.\n    Mal: `[ETCD-CLIENTE-SIN-SERVICIO] <CN> sin etcd-server desde <hora> (<s> s, intento <n>): <dirección>: <error>; ...;\n    el componente sigue protegiendo; próximo intento en <s> s`.\n  - El primer intento es al arrancar, sin bloquear: el proceso sigue aunque falle.\n  - La parada es inmediata (espera interrumpible, como `[PARADA-INMEDIATA-D300]`); al parar, `/unregister` una sola vez si\n    estaba registrado.\n- **Llamadas sin `connected_`:** `get_hmac_key()` y el resto van directas al transporte; si no hay servicio fallan como\n  cualquier petición sin respuesta. `connect()`/`is_connected()` pasan a reflejar el estado del mantenedor.\n- **Función de registro (G3):** `EtcdClient::al_registrar(std::function<bool()>)`; los envoltorios la usan para el\n  `PUT /v1/config/<CN>` con el JSON leído al arrancar (ruta que reciben de `main`, la misma de `-c` o la del\n  config_loader). Si la subida falla: `[ETCD-CLIENTE-CONFIG-NO-SUBIDA]` y se reintenta en el siguiente latido.\n- **Fatales en el bloque (G2):** el proceso arranca sin etcd y repite `[ETCD-CLIENTE-FATAL] <CN>: bloque etcd con <n> campos\n  fatales (arriba, al arrancar); el componente sigue sin etcd` cada 30 s (el defecto de `heartbeat_interval_seconds`: el\n  campo del bloque roto no se puede leer con garantías).\n- **Arranque:** sniffer, ml-detector y firewall crean siempre el cliente si el bloque no tiene fatales y no salen nunca por\n  etcd. El proveedor de clave del ml-detector comprueba el puntero.\n- **Fuera (G5):** en el sniffer, el bloque de `main.cpp` 680-720, `leer_semilla_local()` y el parámetro `encryption_seed`\n  de `RingBufferConsumer`.\n- **`lock_guard`:** `register_component()` sin `unlock()`/`lock()` a mano.\n\n### B2 — clave del firewall\n\n- `hmac_key.check_interval_seconds` en `firewall.json`, entero [10, 3600], defecto 60, con `[CONFIG]`/`[CONFIG-DEFAULT]`.\n  Hilo propio; pide `/secrets/firewall-acl-agent` (no necesita registro, solo el certificado con ese CN).\n- Mismo comportamiento que el ml-detector: sin clave no escribe CSV y avisa en cada intento (`[FW-CSV-SIN-CLAVE]`, desde\n  cuándo y filas sin escribir); servidor caído con clave vigente: sigue firmando (`[FW-CSV-CLAVE-SIN-CONFIRMAR]`); vuelve\n  (`-CONFIRMADA`); clave nueva (`[FW-CSV-CLAVE-CAMBIADA]`, huella vieja → nueva); recuperada tras un hueco\n  (`-RECUPERADA`). En el log solo la huella.\n- CSV (G4 a): un fichero por clave, `firewall_blocks-<AAAAMMDDTHHMMSSZ>-<huella>.csv` en `output_dir`; al cambiar la clave\n  se cierra y se abre otro. `generate_parquet.py` lee todos los `firewall_blocks-*.csv`. La huella en el nombre adelanta\n  para el firewall el camino b de DEBT-BRONZE-KEY-ID-001 (el bronce del ml-detector sigue como está).\n\n### Pruebas y predicciones\n\n- **ctest B1** (servidor falso `httplib::SSLServer`, PKI desechable): sin servidor al arrancar → constructor y arranque no\n  fallan, `[ETCD-CLIENTE-SIN-SERVICIO]` en cada intervalo; el servidor aparece → registro en ≤ 1 intervalo, función de\n  registro llamada una vez; 404 en un latido → nuevo `/register` y nueva subida; el servidor cae → `SIN_SERVICIO` y vuelve;\n  `get_hmac_key()` funciona sin haber llamado a `connect()`; parada en < 1 s con un intervalo de 30 s. Contra el código\n  de `fe99a7e70`: los casos de reconexión fallan.\n- **ctest B2:** el CSV cambia de fichero con la clave; sin clave no se escribe; con el servidor caído se sigue firmando.\n- **Laboratorio B1:** etcd-server de la VM parado → `pipeline-start` arranca los tres (`RUNNING`) con\n  `[ETCD-CLIENTE-SIN-SERVICIO]` cada 30 s y `[BRONCE-SIN-CLAVE]` en el ml-detector; arrancar el etcd-server → los tres\n  `[ETCD-CLIENTE-REGISTRADO]` en ≤ 30 s y `[BRONCE-CLAVE-RECUPERADA]`; pararlo con el pipeline en marcha →\n  `SIN-SERVICIO` y `[BRONCE-CLAVE-SIN-CONFIRMAR]`; volver a arrancarlo → latidos sin nuevo registro (el registro sigue en\n  el etcd real) y `[BRONCE-CLAVE-CONFIRMADA]`. E2E y mitre-start como en el commit A.\n- **Laboratorio B2:** el firewall recibe su clave al volver el etcd-server; tras una rotación (`/secrets/rotate`, admin) →\n  `[FW-CSV-CLAVE-CAMBIADA]` y un CSV nuevo con la otra huella.\n'

BACKLOG = '\n### Diseño del commit B (DAY316) — `docs/ml-heads/day312_diseno.md`, «Diseño del commit B (paso 5)»\nDecisiones G1-G7 de Alonso: un hilo mantenedor en la librería con un solo ritmo (`heartbeat_interval_seconds`: latido si\nestá registrado, reconexión si no); ninguno de los tres sale por etcd (deja atrás F1 de DAY310); la config se sube al\nregistrarse y al volver a registrarse, desde el JSON con el que arrancó; el firewall pide su clave cada\n`hmac_key.check_interval_seconds` y abre un CSV por clave; fuera la semilla muerta del sniffer. B1 (librería y arranque) y\nB2 (clave del firewall, cierra DEBT-FW-HMAC-KEY-ALARM-001).\n\n### DEBT-SNIFFER-LIBPCAP-ETCD-001 — ABIERTA (nueva DAY316, G7)\nEl sniffer libpcap (variante B, `main_libpcap.cpp`, `sniffer-libpcap.json`) no habla con etcd: ni registro, ni latidos,\nni config subida, aunque su JSON ya trae el bloque `etcd` del commit A. Mismo comportamiento que la variante A cuando se\nretome (lector único y mantenedor de la librería).\n'

FICHEROS = [  # (ruta, sha256 previo, marca, texto que se añade)
    ('docs/ml-heads/day312_diseno.md', 'f896e8d5a50242f766377814e75f1b37705360432d7390d6d0ed8f6baf76266d',
     '## Diseño del commit B (paso 5) — DAY316', DISENO),
    ('docs/BACKLOG.md', '3ebe616f1923f1d1e684f889ae342ac8e837b125e7c8bc5f33a55b276dfded51',
     '### Diseño del commit B (DAY316)', BACKLOG),
]

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    contenidos, ya = {}, 0
    for ruta, previo, marca, _ in FICHEROS:
        f = os.path.join(raiz, ruta)
        if not os.path.isfile(f):
            print('FALLA: no existe %s; no se toca nada.' % f); return 1
        b = open(f, 'rb').read()
        contenidos[ruta] = b
        if marca.encode() in b:
            ya += 1
        elif sha(b) != previo:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (ruta, sha(b)[:16])); return 1
    if ya == len(FICHEROS):
        print('YA APLICADO: las dos secciones ya están; no se toca nada.'); return 0
    if ya:
        print('FALLA: una sección está y la otra no; no se toca nada.'); return 1
    nuevos = {}
    for ruta, previo, marca, texto in FICHEROS:
        t = texto
        assert '@@' not in t and t.count(marca) == 1
        nuevos[ruta] = contenidos[ruta] + t.encode()
    if modo == '--check':
        print('APLICABLE: 2 ficheros; se añaden %d y %d líneas.'
              % (FICHEROS[0][3].count('\n'), FICHEROS[1][3].count('\n'))); return 0
    for ruta, c in nuevos.items():
        f = os.path.join(raiz, ruta)
        t = f + '.d316tmp'
        with open(t, 'wb') as o: o.write(c)
        os.chmod(t, os.stat(f).st_mode & 0o7777); os.replace(t, f)
        print('  escrito  %s' % ruta)
    mal = [r for r, c in nuevos.items() if sha(open(os.path.join(raiz, r), 'rb').read()) != sha(c)]
    if mal:
        print('FALLA tras escribir: %s' % ', '.join(mal)); return 1
    print('APLICADO: 2 ficheros.'); return 0

if __name__ == '__main__':
    sys.exit(main())
