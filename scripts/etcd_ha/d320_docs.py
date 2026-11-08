#!/usr/bin/env python3
# [PROTEGIDOS-MANIFIESTO-D320] docs de 8e.3: ADR-060 (8e.3 hecho con sus commits, F-C con GET /v1/protegidos/v/{n},
# G-A..G-G, firmante corto, F-I con el alcance real de 8e.3e, nota de [INFRA-CAMBIO]) y BACKLOG (sección DAY320:
# medidas de 8e.3e, hallazgos y DEBT-ETCD-CLIENT-TEST-R2-CARRERA-001). Solo documentación.
#
# Uso, desde la raíz del repo:
#   python3 -I scripts/etcd_ha/d320_docs.py --check
#   python3 -I scripts/etcd_ha/d320_docs.py --apply
# Todo o nada: comprueba el sha256 de cada fichero antes de escribir ninguno. Idempotente: si los dos ficheros ya
# tienen el sha256 de después, no toca nada. Salidas: 0 aplicable/aplicado/ya aplicado, 1 no aplicable, 2 uso.
import hashlib, json, os, sys, tempfile

CAMBIOS = json.loads(r'''[
 {
  "ruta": "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md",
  "antes": "06778d9779092532d7dac2268b305bc94b13cff9c32a8a80417ee203763e1e92",
  "despues": "810debb5c61455e8e8f03783b39460c7bd56d417934b572a40081f94399e3bfd",
  "bloques": [
   {
    "viejo": "- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server. Diseño cerrado DAY318 (decisiones de Alonso\n  F-A..F-I):\n",
    "nuevo": "- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server. Diseño cerrado DAY318 (decisiones de Alonso\n  F-A..F-I). Hecho: 8e.3a a5a41ba4 (`libs/protegidos`), 8e.3b 465e6aa4 (etcd-server), 8e.3c 91981329 (consulta del\n  firewall), 8e.3d-0 a831c44b (historial en el etcd-server), 8e.3d 6b88a0c8 (`argus-infra`), 8e.3e e2f4bb79\n  (fuera la familia `/kv` del etcd-client):\n"
   },
   {
    "viejo": "    `argus_hospital_id`). Rutas sin segmento de hospital: `GET /v1/protegidos` (`ou:firewall-acl-agent`,\n    `ou:argus-infra`) y `PUT /v1/protegidos` (`ou:argus-infra`).\n",
    "nuevo": "    `argus_hospital_id`). Rutas sin segmento de hospital: `GET /v1/protegidos` (`ou:firewall-acl-agent`,\n    `ou:argus-infra`) y `PUT /v1/protegidos` (`ou:argus-infra`). Añadida DAY319 (G-C): `GET /v1/protegidos/v/{n}`\n    (solo `ou:argus-infra`), la versión n de `protegidos/v/<N>` tal cual, sin verificar (verifica quien la pide);\n    400 si n no es un decimal >= 1 sin ceros a la izquierda que quepa en 64 bits, 404 si no existe, 503 sin\n    `hospital_id` o con el almacén caído. El firewall no la puede leer.\n"
   },
   {
    "viejo": "    `verificar`, `deshacer N` (contenido de N como N+1 firmado). Firma y verifica con Vault transit; comprueba los\n    límites de D2 antes del PUT.\n",
    "nuevo": "    `verificar`, `deshacer N` (contenido de N como N+1 firmado). Firma y verifica con Vault transit; comprueba los\n    límites de D2 antes del PUT. Diseño fino DAY319 (decisiones de Alonso G-A..G-G):\n    - **G-A** Configuración `/etc/argus-infra/argus-infra.json` (lab: `tools/argus-infra/argus-infra.lab.json`):\n      hospital, plantas, límites, Vault, etcd-server y TLS sin defecto sano (sin ellos no firma); solo `timeout_s`\n      tiene defecto ([1, 120], 10, con aviso).\n    - **G-B** Plantilla sin firmar aparte (`tools/argus-infra/plantillas/hospital-lab.json`); los límites salen\n      siempre de la configuración, nunca de la plantilla ni de la versión anterior.\n    - **G-C** El historial se lee del etcd-server (`GET /v1/protegidos/v/{n}`, F-C), no de un archivo local: la\n      verdad en un solo sitio.\n    - **G-D** `firmante` = `<cn> entidad=<entity_id de Vault>`, como mucho 64 caracteres. Cambiado tras medir: el\n      etcd-server y el firewall registran el firmante con `saneado()`, que corta a 64, y con el formato largo el\n      entity_id se perdía.\n    - **G-E** Cada cambio: login en Vault; lo vigente se valida (reglas de `libs/protegidos` portadas a Python y\n      transit verify); N+1; diff; confirmación tecleando el número de versión (`--si` para el bootstrap); sign;\n      verify; PUT; GET final comparado byte a byte; revoke-self del token.\n    - **G-F** Órdenes `init --desde`, `list`, `add`, `del`, `diff`, `verificar` (también la cadena\n      `hash_anterior`), `deshacer N`. Salidas: 0 bien, 1 error, 2 uso, 3 rechazo del etcd-server.\n    - **G-G** Vive en `tools/argus-infra/`; lo instala el aprovisionador `argus-infra` de la VM etcd (run: always);\n      `make test-argus-infra`.\n"
   },
   {
    "viejo": "  - **F-I** `set/get/del/list_keys` del etcd-client piden `/kv/...`, rutas que el servidor no tiene: se borran en\n    un commit propio cuando 8e.3 funcione, tras comprobar con `git grep` que nadie los usa.\n",
    "nuevo": "  - **F-I** `set/get/del/list_keys` del etcd-client piden `/kv/...`, rutas que el servidor no tiene: se borran en\n    un commit propio cuando 8e.3 funcione, tras comprobar con `git grep` que nadie los usa. Hecho DAY320\n    (e2f4bb79): medido que borrar solo esos 4 rompe la librería, porque otros 6 métodos suyos los llaman\n    (`save_config_master`, `save_config_active`, `get_config_master`, `get_config_active`, `get_component_config`\n    y `rollback_config`). Decisión de Alonso: fuera los 10; se queda `put_config` (sí funciona).\n"
   },
   {
    "viejo": "  \"firmante\": \"<entidad de Vault del admin>\",\n",
    "nuevo": "  \"firmante\": \"<cn> entidad=<entity_id de Vault> (<= 64 caracteres; G-D)\",\n"
   },
   {
    "viejo": "memoria). `[INFRA-CAMBIO]` llega con 8e.3, cuando el manifiesto cambia en caliente.\n",
    "nuevo": "memoria). `[INFRA-CAMBIO]` llega con 8e.3, cuando el manifiesto cambia en caliente (medido DAY319: solo se\nescribe si ya había un vigente; con la primera versión sale solo `[PROTEGIDOS-MANIFIESTO]`).\n"
   }
  ]
 },
 {
  "ruta": "docs/BACKLOG.md",
  "antes": "42666ab58d216a8d748003bcd29866a474033b143361be507ab1012559e19af0",
  "despues": "401e4ed4c189ffc82cef9db77adeda9aee6a3029682759ef6a0b374b092fa070",
  "bloques": [
   {
    "viejo": "### Pendiente (por orden)\n8e.3e (borrar `set/get/del/list_keys` del etcd-client), docs de 8e.3 en ADR-060 (F-C con la ruta del historial, G-A..G-G,\nfirmante corto), 8e.4, 8e.5 (bootstrap con `argus-infra init --si`, P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ y\ncierre del PR1.\n",
    "nuevo": "### Pendiente (por orden)\n8e.3e (borrar `set/get/del/list_keys` del etcd-client), docs de 8e.3 en ADR-060 (F-C con la ruta del historial, G-A..G-G,\nfirmante corto), 8e.4, 8e.5 (bootstrap con `argus-infra init --si`, P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ y\ncierre del PR1.\n\n\n---\n\n## DAY320 — paso 8e.3e hecho y docs de 8e.3 [PROTEGIDOS-MANIFIESTO-D320]\n\nCommit e2f4bb79 (8e.3e). Fuera del etcd-client todo lo que pide `/kv/...` (rutas que el etcd-server no tiene): `set`,\n`get`, `del`, `list_keys` y los 6 que se apoyan en ellos, `save_config_master`, `save_config_active`, `get_config_master`,\n`get_config_active`, `get_component_config` y `rollback_config` (decisión de Alonso DAY320, tras medir que borrar solo los\n4 rompía la librería). Se quedan `put_config` (va por `put_config_impl`) y el `mutex_`. ADR-060 al día: 8e.3 hecho, F-C con\n`GET /v1/protegidos/v/{n}`, G-A..G-G y firmante corto, F-I con el alcance real.\n\n### Medido en el banco (Debian 12, GCC 12.2.0, CMake 3.25.1, libsodium 1.0.19, httplib v0.63.0; banco rehecho)\n- Base (2cc8c344) y parcheado, con Release (como `etcd-client-build`), native y skylake (opciones de production), dos\n  pasadas: 12/12 compilan sin avisos del código y ctest de etcd-client 5/5.\n- `nm -DC`: `EtcdClient` exporta 26 símbolos (antes 36); el diff son exactamente los 10, ninguno nuevo.\n- Mutación: una sonda que llama a los 10 métodos compila contra la base; contra el parcheado, 10 \"has no member named\".\n- Parcheador `d320_8e3e.py`: `--check`, `--apply`, idempotente; con un fichero alterado o en estado mezclado no escribe.\n\n### Medido en el lab (PROFILE=production)\n`pipeline-build` rc 0 (etcd-server, ml-detector, sniffer, firewall y tools recompilados contra la cabecera nueva);\n`make etcd-client-test` 5/5; en el defender, 0 símbolos de la familia en `/usr/local/lib/libetcd_client.so`.\n\n### Hallazgos DAY320\n- **Buscar usos por palabra, no por `objeto.metodo(`.** El primer `git grep` (`.set(`, `->set(`) daba 0 usos y se le\n  escaparon las llamadas sin calificar dentro de la propia clase; la compilación del banco lo cazó. Para borrar un\n  método: `git grep -w`.\n- `etcd-client-build` (y crypto-transport, seed-client, plugin-loader, vault-client) compila con\n  `-DCMAKE_BUILD_TYPE=Release` y sin los flags de `PROFILE` (`CXX Flags (from Makefile):` vacío); los consumidores sí van\n  con production. Anotado, sin decidir.\n- `common/EtcdServiceRegistry.{h,cpp}` (habla con la API v3 de etcd directamente) solo lo cita\n  `scripts/build_and_run.sh`, que exige `service1/`, `service2/` y `docker-compose.yaml`, que no existen en el repo: el\n  script siempre aborta. Es de la época de Docker. Candidato a borrar, sin decidir.\n- `EtcdClient::set_encryption_key` (no-op desde DAY98) y `has_encryption_key`: nadie los llama. Candidatos a borrar, sin\n  decidir.\n\n### DEBT-ETCD-CLIENT-TEST-R2-CARRERA-001 — ABIERTA (nueva DAY320, Alonso)\n`test_etcd_cliente_tls` (DAY316, mantenedor G1-G3) falla de vez en cuando en R2 (\"el etcd-server aparece: se registra\nen <= 1 latido y sube la config del JSON de arranque\"). Medido DAY320 en el banco, en el árbol base 2cc8c344 sin ningún\ncambio: 1 de 30 y 1 de 60 ejecuciones, más 1 en la matriz. Con R2 instrumentado en una copia aparte: en los 60 casos el\nservidor falso cuenta `register=1 config=1` y `reg=1`; en el que falla, las líneas `[ETCD-CLIENTE-REGISTRADO] sniffer` y\n`config subida: ...` aún no están en la salida capturada. Es una carrera del test (comprueba el log en cuanto el\nservidor cuenta la petición, antes de que el hilo mantenedor escriba su línea), no del cliente.\nArreglo: que R2 espere (`espera(...)`) también a las dos líneas del log antes de comprobar.\n**Test de cierre:** 200 ejecuciones seguidas de `test_etcd_cliente_tls` sin un fallo de R2; y con la espera del log\nquitada, vuelve a fallar alguna (el instrumento detecta).\n\n### Pendiente (por orden)\n8e.4 (vigilancia: kernel <-> manifiesto, antispoofing en raw PREROUTING, MAC, rp_filter, versión en latido y\npipeline-status, Falco/Wazuh, alarma de disco del audit de Vault al 75 %), 8e.5 (bootstrap con `argus-infra init --si`,\n`d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1.\n"
   }
  ]
 }
]''')

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d320_docs.py --check|--apply  (desde la raíz del repo)", file=sys.stderr); return 2
    aplicar = sys.argv[1] == "--apply"
    estados, nuevos = [], {}
    for c in CAMBIOS:
        if not os.path.isfile(c["ruta"]):
            print(f"[NO APLICABLE] no existe {c['ruta']} (¿estás en la raíz del repo?)"); return 1
        b = open(c["ruta"], "rb").read(); s = sha(b)
        if s == c["despues"]:
            estados.append("hecho"); print(f"[YA APLICADO] {c['ruta']} sha256={s}"); continue
        if s != c["antes"]:
            print(f"[NO APLICABLE] {c['ruta']} sha256={s}\n  esperado antes  ={c['antes']}\n  esperado después={c['despues']}")
            return 1
        t = b.decode("utf-8"); borradas = 0
        for i, bl in enumerate(c["bloques"], 1):
            v = bl["viejo"]
            if t.count(v) != 1:
                print(f"[NO APLICABLE] {c['ruta']}: el bloque {i} aparece {t.count(v)} veces"); return 1
            t = t.replace(v, bl["nuevo"]); borradas += v.count(chr(10)) - bl["nuevo"].count(chr(10))
        n = t.encode("utf-8")
        if sha(n) != c["despues"]:
            print(f"[NO APLICABLE] {c['ruta']}: el resultado no da el sha256 esperado"); return 1
        estados.append("pendiente"); nuevos[c["ruta"]] = n
        print(f"[APLICABLE] {c['ruta']} {s[:16]} -> {c['despues'][:16]} ({len(c['bloques'])} bloques, {abs(borradas)} líneas {'menos' if borradas >= 0 else 'más'})")
    if "hecho" in estados and "pendiente" in estados:
        print("[NO APLICABLE] estado mezclado: un fichero ya aplicado y otro no; no se toca nada"); return 1
    if not nuevos:
        print("[YA APLICADO] nada que hacer"); return 0
    if not aplicar:
        print("[CHECK] todo aplicable; nada escrito"); return 0
    for ruta, n in nuevos.items():
        modo = os.stat(ruta).st_mode & 0o7777
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta), prefix=".d320.")
        with os.fdopen(fd, "wb") as f: f.write(n); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, modo); os.replace(tmp, ruta)
    for c in CAMBIOS:
        s = sha(open(c["ruta"], "rb").read())
        if s != c["despues"]:
            print(f"[ERROR] {c['ruta']} quedó con sha256={s}"); return 1
        print(f"[APLICADO] {c['ruta']} sha256={s}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
