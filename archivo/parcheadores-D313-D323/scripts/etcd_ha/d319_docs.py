#!/usr/bin/env python3
# d319_docs.py — DAY319 docs: prompt de continuidad para DAY320 y BACKLOG de 8e.3d-0/8e.3d [PROTEGIDOS-MANIFIESTO-D319].
# Uso: python3 ESTE.py --check RAIZ | --apply RAIZ   (todo o nada, idempotente, sha256 previo y final)
import hashlib, os, sys
OPS = []
# mod docs/continuity/PROMPT_CONTINUE_CLAUDE.md
_s0 = '31d90a6478492ba4592edaac4fb27d892cfcfeb7dfc641118c69c20892f2e187'
_s1 = 'ca22a6e7247082e80611631565d9a778e1fe19b3512eaa048385e5c4feae1bcb'
_t = []
_t.append(('# Prompt de continuidad — DAY319 (tras DAY318, jueves 2026-11-05)\n\nHola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama\n`feat/etcd-mtls-vault` (PR1, un nodo) y, dentro de ella, con **DEBT-FW-MANIFIESTO-PROTEGIDOS-001** (ADR-060, paso 8e).\nResponde siempre en español. Lee, en este orden:\n`docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md` (entero: decisiones D1-D11, D-A..D-I, F-A..F-I, plan\n8e.1-8e.5 y diseño fino) y el final de `docs/BACKLOG.md` (secciones `[PROTEGIDOS-MANIFIESTO-D318]` y\n`[PROTEGIDOS-PUBKEY-D318]`).\n\n**DAY319 empieza en 8e.3d.** Comprueba antes con `git log --oneline -12` que HEAD es `919813290` (o posterior).\n\n## Hecho DAY318 (10 commits, 07:00-18:10)\n\n| commit | qué |\n|---|---|\n| addc844a | docs: diseño fino de 8e (D-A..D-I) |\n| 77077b47 | 8e.2 Vault transit: clave ed25519 `protegidos-<hospital>` no exportable, rol `argus-infra`, audit fichero + syslog, `make protegidos-pubkey` |\n| 9e9c58c6 | docs de 8e.2 |\n| 3af32373 | 8e.1a verificador del manifiesto (Ed25519 libsodium, JSON estricto, límites, versión, caché, clave compilada en dos ranuras) |\n| f9076a97 | 8e.1b cableado: set `hash:net,iface` con swap atómico, regla `src,src`, candado D6, barrera por IP, avisos D6/D7/D-C; fuera `ddos_protegidos` y la whitelist |\n| b8bf8a4a | docs de 8e.1 |\n| 7d2b58e1 | docs: diseño de 8e.3 (F-A..F-I) y DEBT-FW-ARGUS-INFRA-LLAVE-HW-001 |\n| a5a41ba4 | 8e.3a `libs/protegidos` (estática, `argus::protegidos`); validador de CIDR a `common/include/argus`; falso `stringop-overflow` de GCC 12 con `-march=skylake` |\n| 465e6aa4 | 8e.3b etcd-server: `GET/PUT /v1/protegidos` (authz por OU), `verificar_documento`, etcd `protegidos/vigente` + `protegidos/v/<N>`, `protegidos.hospital_id` (Ansible) |\n| 91981329 | 8e.3c firewall: `get_protegidos()` en etcd-client, consulta cada `consulta_sec`, `[INFRA-CAMBIO]`, anti-rollback con `<cache>.version` |\n\nMedido en el lab al cierre: huella de la clave `52ba6180cf5e8e9a` igual en el firewall y en el etcd-server de la VM;\nel firewall consulta y recibe 404 (no hay manifiesto publicado todavía); el lab está en `dry_run`.\n\n## Lo que queda, por orden\n\n1. **8e.3d** `argus-infra`: un fichero Python con la biblioteca estándar (Python 3.11.2 y OpenSSL 3.0.22 medidos en la\n   VM etcd), instalado por el Vagrantfile en la VM etcd. `init --desde PLANTILLA`, `list`, `add`, `del`, `diff`,\n   `verificar`, `deshacer N`. Login en Vault con `/etc/argus-pki/argus-infra.{crt,key}` (token 300 s, 127.0.0.1),\n   firma con `argus-transit/sign/protegidos-<hospital>`, comprueba los límites de D2 y hace `PUT /v1/protegidos` con\n   el mismo certificado. Plantilla `hospital-lab` en el repo: `.20` infraestructura por `eth2`, `.61` intranet.\n   **Primera prueba real de 8e.3c:** al publicar la versión 1, el firewall tiene que aplicarla sin reiniciar\n   (`[PROTEGIDOS-MANIFIESTO] verificado ... (etcd-server)`, caché y `.version` escritas).\n2. **8e.3e** borrar `set/get/del/list_keys` del etcd-client (`/kv/...`, rutas que el servidor no tiene) tras\n   comprobar con `git grep` que nadie los usa.\n3. **Docs de 8e.3** (ADR-060 y BACKLOG).\n4. **8e.4** vigilancia: kernel ↔ manifiesto, antispoofing `raw PREROUTING`, MAC, `rp_filter`, versión en el latido y en\n   `pipeline-status`, Falco y Wazuh (incluida la alarma de disco del audit de Vault al 75 %).\n5. **8e.5** bootstrap con `argus-infra` (`.20` y `.61`), reescribir `d303_veredicto_protegidos.sh` (P1-P6).\n6. **EMECAS+++ PROFILE=production**: rc 0, `lab-e2e-protegidos` P1-P6 PASA, Acto IV con `err_to_row=0`.\n\nHasta 8e.5, `lab-e2e-mitigacion` y `lab-e2e-protegidos` fallan (sin manifiesto el candado para la mitigación).\n\n## Herramientas de Claude (en su contenedor, no en el repo; si el contenedor es nuevo, hay que rehacerlas)\n\n- Banco Debian 12 en `/srv/banco`: GCC 12.2.0, libsodium 1.0.19, httplib v0.63.0, Vault 2.2.1, gRPC 1.51,\n  cpprest, etcd-cpp-apiv3 v0.15.3 (clonado fuera del chroot: dentro no hay CA del proxy).\n- `/root/banco_fw.sh ÁRBOL ETIQUETA`: compila las librerías, el firewall y su ctest. Variables: `PUBKEY_ACTUAL`,\n  `PUBKEY_SIGUIENTE`, `SOLO_FW=1` (solo el firewall; no sirve si cambia el etcd-client), `ES=1` (también el\n  etcd-server y su ctest), `MARCH=skylake` (la CPU del defender; compilar SIEMPRE también así).\n- `/root/vault_8e3b.sh` (Vault dev con la clave transit) y `/root/e2e_8e3b.sh` (etcd-server con mTLS + firma real +\n  curl por rol, 12 pruebas).\n- `/home/claude/gen/generar.py VIEJO NUEVO SALIDA "cabecera"` + `plantilla.py`: parcheador con ficheros nuevos,\n  borrados y trozos anclados a partir de dos árboles (lista de rutas en `gen/rutas.txt`).\n\n## Reglas\n\n- Medir, no votar. Predicción escrita antes de medir; si algo no da lo esperado, parar.\n- Todo lo que se compile se prueba antes en el banco con las opciones de production (g++-12, `-std=c++20 -Wall -Wextra\n  -Wpedantic -Werror -O3 -march=native -DNDEBUG -flto -fno-omit-frame-pointer`, y además con `-march=skylake`), dos\n  veces y contra el comportamiento viejo (mutaciones: tiene que fallar).\n- Compilar el pipeline completo (`make pipeline-build PROFILE=production`), no un componente suelto.\n- Parcheadores: `--check`/`--apply <raíz>`, todo o nada, idempotentes, con sha256 previo y final; se copian a\n  `scripts/etcd_ha/` y se ejecutan desde allí; se entregan con su sha256; un sha por línea, nunca diccionarios largos\n  con hex (ggshield); quedan sin trackear.\n- Comandos: exactos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM etcd); salidas largas a\n  un fichero con `; cat`; búsquedas con `git grep`; sin emojis.\n- El JSON es la ley. Lo deprecado se borra. No romper la seguridad ni abrir un camino para romperla en producción.\n- El repo es de solo lectura para Claude: los commits los hace Alonso, uno por cambio lógico; **Claude propone siempre\n  el `git commit -m`**. Push solo al cerrar un paso grande o el día: tras cada commit basta `git rev-parse HEAD`.\n',
           '# Prompt de continuidad — DAY320 (tras DAY319, viernes 2026-11-06)\n\nHola, Claude. Soy Alonso (aRGus NDR). Seguimos con DEBT-ETCD-HA-TLS-RAFT-001, rama `feat/etcd-mtls-vault`, y dentro con\nDEBT-FW-MANIFIESTO-PROTEGIDOS-001 (ADR-060). Responde en español. Lee ADR-060 entero y el final de `docs/BACKLOG.md`.\nComprueba con `git log --oneline -5` que HEAD es el commit de docs de DAY319 (posterior a `6b88a0c84`). **DAY320 empieza en 8e.3e.**\n\n## Hecho DAY319 (3 commits, 05:37-07:30)\n| commit | qué |\n|---|---|\n| a831c44b0 | 8e.3d-0 etcd-server: `GET /v1/protegidos/v/{n}` (solo ou:argus-infra; 400/404/503), 16 reglas authz |\n| 6b88a0c84 | 8e.3d `tools/argus-infra/` (Python 3.11 stdlib): init/list/add/del/diff/verificar/deshacer; `argus-infra.lab.json`, `plantillas/hospital-lab.json`, tests unittest, aprovisionador `argus-infra` de la VM etcd (run: always), `make test-argus-infra` |\n\nDecisiones de Alonso DAY319 (G-A..G-G): configuración `/etc/argus-infra/argus-infra.json` sin defecto sano para la\nidentidad (solo `timeout_s` [1,120] 10); plantilla separada (límites siempre de la configuración); historial por ruta nueva\ndel etcd-server (G-C); confirmación tecleando el número de versión (`--si` para bootstrap); orden de cada cambio: login\nVault, vigente validado (reglas portadas + transit verify), N+1, diff, confirmar, sign, verify, PUT, GET byte a byte,\nrevoke-self. Salidas 0/1/2/3 (3 = rechazo del etcd-server).\n\nCambio sobre G-D, medido: `firmante` = `<cn> entidad=<entity_id de Vault>` (<= 64 caracteres) porque el etcd-server y el\nfirewall cortan a 64 con `saneado()`; con el formato largo el entity_id se perdía.\n\n## Medido\n- Banco: etcd-server 8/8 (native y skylake), 4 mutaciones; unittest 19/19; diferencial C++ (libs/protegidos) vs Python con\n  8000 cargas, 0 discrepancias (mutación detectada: 94); E2E 43/43 x3; 12 mutaciones de argus-infra detectadas.\n- Lab: `pipeline-build` rc 0; etcd-server ctest 8/8; `etcd-vm-deploy` SANO; `regla 16/16`; huella 52ba6180cf5e8e9a en\n  argus-infra, etcd-server y firewall; `make test-argus-infra` 19 OK; publicadas v1..v4. Firewall: al arrancar\n  `[PROTEGIDOS-MANIFIESTO] verificado version=3 ... entradas=2 (infraestructura=1 intranet=1 ...) (etcd-server)`, caché\n  1036 B y `.version`=3; en vivo `[INFRA-CAMBIO] version 3 -> 4 ... altas=[intranet 192.168.100.62/32 eth2] bajas=[]`.\n  Primera prueba real de 8e.3c: PASA. Al cierre: `deshacer 1` firmó la v5 (contenido de la plantilla) y el firewall\n  registró `[INFRA-CAMBIO] version 4 -> 5 ... bajas=[intranet 192.168.100.62/32 eth2]`. Lab vigente: v5.\n- Notas: `[INFRA-CAMBIO]` solo sale si había vigente (con la v1 no). La VM etcd es `autostart: false`: `vagrant up etcd`\n  antes de `etcd-vm-deploy`. `pgrep` sin `-f` no casa nombres de más de 15 caracteres.\n\n## Lo que queda, por orden\n1. **8e.3e** borrar `set/get/del/list_keys` del etcd-client (`/kv/...`) tras `git grep` de usos.\n2. **Docs de 8e.3** (ADR-060: F-C con la ruta del historial, G-A..G-G, firmante corto; BACKLOG con las medidas de arriba).\n3. **8e.4** vigilancia (kernel <-> manifiesto, antispoofing raw PREROUTING, MAC, rp_filter, versión en latido y\n   pipeline-status, Falco/Wazuh, alarma de disco del audit de Vault 75 %).\n4. **8e.5** bootstrap con `argus-infra init --si` (.20 y .61), reescribir `d303_veredicto_protegidos.sh` (P1-P6),\n   meter `test-argus-infra` en EMECAS.\n5. **EMECAS+++ PROFILE=production**: rc 0, `lab-e2e-protegidos` P1-P6 PASA, Acto IV con `err_to_row=0`.\n6. **Cierre del PR1**: comprobar que el arranque del lab levanta la VM etcd (DAY319: `vagrant up` a secas no, es\n   `autostart: false`; el plan de DAY316 pedía `make up` con la VM etcd), README del etcd-server (DAY311), push y PR.\n   Lo demás (HA de 3 nodos, Vault HA, Ansible de Vault, transacción de etcd en el PUT) es PR2.\n\n## Banco de Claude (contenedor; si es nuevo, rehacer)\nChroot Debian 12 en `/srv/banco` (debootstrap minbase + `gcc g++` de Debian para el plugin LTO de `ar`, `cppzmq-dev`),\nlibsodium 1.0.19, httplib v0.63.0, etcd-cpp-apiv3 v0.15.3, Vault 2.2.1, etcd 3.6.16, PKI con `d312_pki.sh init`, identidad\ndel etcd-server (seed.bin 32 B + par ed25519). Scripts: `/root/banco_plano.sh arrancar hospital-lab` (etcd + Vault como\nla VM), `/root/banco_es.sh ARBOL ETIQUETA` (MARCH, LIBS=1), `/root/e2e_8e3d.sh`, `/root/mut_8e3d.py`, `/root/mut_es.sh`,\n`/root/dif/{arnes.cpp,dif.py,verifica_sobre.cpp}`. Generador de parcheadores `/home/claude/gen/generar.py VIEJO NUEVO\nSALIDA "cabecera" RUTAS...` (funde trozos solapados).\n\n## Reglas\nLas de siempre: medir, no votar; predicción escrita antes; si no da, parar. Banco con opciones de production, native y\nskylake, dos veces, mutaciones. Pipeline completo. Parcheadores `--check`/`--apply`, todo o nada, idempotentes, sha256, a\n`scripts/etcd_ha/`. Comandos exactos, uno por bloque, diciendo dónde. Repo de solo lectura para Claude; Claude propone\nel `git commit -m`.\n'))
OPS.append(('mod', 'docs/continuity/PROMPT_CONTINUE_CLAUDE.md', _s0, _s1, _t, 0o775))
# mod docs/BACKLOG.md
_s0 = '47ef2e5c04b94cd5fa96f8e639216db87d39b7fff7bf3f3066057d5fbb5ca04e'
_s1 = '42666ab58d216a8d748003bcd29866a474033b143361be507ab1012559e19af0'
_t = []
_t.append(('**Test de cierre:** con el validador mutado (acepta todo), el test falla; con el bueno, pasa.\n',
           '**Test de cierre:** con el validador mutado (acepta todo), el test falla; con el bueno, pasa.\n\n\n---\n\n## DAY319 — pasos 8e.3d-0 y 8e.3d hechos [PROTEGIDOS-MANIFIESTO-D319]\n\nCommits: a831c44b0 (8e.3d-0, `GET /v1/protegidos/v/{n}` en el etcd-server) y 6b88a0c84 (8e.3d, `tools/argus-infra/`).\nDiseño fino G-A..G-G (decisiones de Alonso DAY319):\n- G-A configuración `/etc/argus-infra/argus-infra.json` (lab: `tools/argus-infra/argus-infra.lab.json`): hospital,\n  plantas, límites, Vault, etcd-server y TLS sin defecto sano (no firma); `timeout_s` [1, 120], 10, con aviso.\n- G-B plantilla sin firmar separada (`tools/argus-infra/plantillas/hospital-lab.json`); los límites salen siempre de la\n  configuración, nunca de la plantilla ni de la versión anterior.\n- G-C el historial se lee del etcd-server (ruta nueva, solo `ou:argus-infra`), no de un archivo local.\n- G-D firmante desde la identidad de Vault. Cambiado tras medir: `<cn> entidad=<entity_id>` (<= 64 caracteres), porque el\n  etcd-server y el firewall registran el firmante con `saneado()`, que corta a 64, y el entity_id salía cortado.\n- G-E cada cambio: login, vigente validado (reglas portadas de libs/protegidos + transit verify), N+1, diff, confirmación\n  tecleando el número de versión (`--si` para el bootstrap), sign, verify, PUT, GET byte a byte, revoke-self.\n- G-F órdenes init, list, add, del, diff, verificar (con la cadena `hash_anterior`), deshacer N. Salidas 0/1/2/3.\n- G-G `tools/argus-infra/`, instalado por el aprovisionador `argus-infra` de la VM etcd (run: always); `make test-argus-infra`.\n\n### Medido en el banco (Debian 12, GCC 12.2, Python 3.11.2, Vault 2.2.1, etcd 3.6.16)\n- etcd-server 8/8 con native y skylake; mutaciones (ceros a la izquierda, devolver la vigente, el firewall lee el\n  histórico, tabla por defecto sin la regla): 4/4 detectadas.\n- argus-infra: unittest 19/19; prueba diferencial C++ (libs/protegidos) contra el porte en Python con 8000 cargas al azar,\n  0 discrepancias de motivo (con `repetidas` mutada, 94: el instrumento detecta); E2E contra el etcd-server real 43/43 en\n  tres pasadas (native x2, skylake); 12/12 mutaciones detectadas (dos sobrevivían a los unitarios, base64 sucio y clave\n  duplicada con el mismo valor: casos añadidos tras medir que libs/protegidos los rechaza).\n- Fallos de predicción (no del código): un segundo `15u` en test_etcd_server_authz; en el chroot faltaba el plugin LTO de\n  `ar` (`/usr/lib/bfd-plugins`).\n\n### Medido en el lab (PROFILE=production)\n`pipeline-build` rc 0; ctest del etcd-server 8/8; `etcd-vm-deploy` SANO; `regla 16/16`; aprovisionador `argus-infra` OK\n(Python 3.11.2); `make test-argus-infra` 19 OK; huella 52ba6180cf5e8e9a en argus-infra, etcd-server y firewall.\nPublicadas v1..v5. El firewall, al arrancar, aplica la vigente desde el etcd-server (`[PROTEGIDOS-MANIFIESTO] verificado\nversion=3 ... entradas=2 (infraestructura=1 intranet=1 dmz=0 externos_criticos=0) (etcd-server)`, caché y `.version`=3) y,\nsin reiniciar, `[INFRA-CAMBIO] version 3 -> 4 ... altas=[intranet 192.168.100.62/32 eth2]` y `4 -> 5 ... bajas=[...]`.\nPrimera prueba real de 8e.3c: PASA. Lab vigente al cierre: v5 (contenido de la plantilla).\n\n### Hallazgos DAY319\n- `[INFRA-CAMBIO]` solo se escribe si ya había vigente (con la primera versión, solo `[PROTEGIDOS-MANIFIESTO]`).\n- La VM etcd es `autostart: false`: `vagrant up` a secas no la levanta y `etcd-vm-deploy` falla con "vagrant ssh-config".\n  Para el cierre del PR1 hay que comprobar el arranque del lab con la VM etcd (plan de DAY316).\n- Los ficheros nuevos de `tools/argus-infra` quedaron 100644 en git (el parcheador aplica el modo, pero git en el Mac no lo\n  registró): no afecta (el Vagrantfile instala con `install -m 0750` y los tests se lanzan con `python3 -I`).\n\n### Pendiente (por orden)\n8e.3e (borrar `set/get/del/list_keys` del etcd-client), docs de 8e.3 en ADR-060 (F-C con la ruta del historial, G-A..G-G,\nfirmante corto), 8e.4, 8e.5 (bootstrap con `argus-infra init --si`, P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ y\ncierre del PR1.\n'))
OPS.append(('mod', 'docs/BACKLOG.md', _s0, _s1, _t, 0o775))


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def leer(p):
    with open(p, "rb") as f:
        return f.read().decode("utf-8")


def plan(raiz):
    """Devuelve [(ruta, contenido nuevo o None para borrar, modo, estado)] sin tocar nada; falla si algo no cuadra."""
    out, errores = [], []
    for tipo, r, s0, s1, dato, modo in OPS:
        p = os.path.join(raiz, r)
        hay = os.path.exists(p)
        actual = leer(p) if hay else None
        if tipo == "del":
            if not hay:
                out.append((r, None, 0, "ya aplicado"))
            elif sha(actual) == s0:
                out.append((r, None, 0, "borrar"))
            else:
                errores.append(f"{r}: sha256 {sha(actual)} (se espera {s0})")
            continue
        if hay and sha(actual) == s1:
            out.append((r, actual, modo, "ya aplicado"))
            continue
        if tipo == "new":
            if hay:
                errores.append(f"{r}: ya existe con otro contenido (sha256 {sha(actual)})")
            else:
                out.append((r, dato, modo, "crear"))
            continue
        if not hay:
            errores.append(f"{r}: no existe")
            continue
        if sha(actual) != s0:
            errores.append(f"{r}: sha256 {sha(actual)} (se espera {s0} antes o {s1} después)")
            continue
        t, pos = actual, 0
        for anc, nue in dato:
            if actual.count(anc) != 1:
                errores.append(f"{r}: un ancla aparece {actual.count(anc)} veces")
                break
            k = t.find(anc, pos)
            if k < 0:
                errores.append(f"{r}: ancla fuera de orden")
                break
            t = t[:k] + nue + t[k + len(anc):]
            pos = k + len(nue)
        else:
            if sha(t) != s1:
                errores.append(f"{r}: el resultado no da el sha256 esperado")
            else:
                out.append((r, t, None, "modificar"))
    if errores:
        for e in errores:
            print("[PARCHE] FALLA " + e)
        sys.exit(1)
    return out


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check RAIZ | --apply RAIZ")
        sys.exit(2)
    raiz = sys.argv[2]
    if not os.path.isfile(os.path.join(raiz, "Makefile")) or not os.path.isdir(os.path.join(raiz, ".git")):
        print(f"[PARCHE] FALLA {raiz} no parece la raíz del repo (sin Makefile o sin .git)")
        sys.exit(1)
    for _, r, s0, s1, _, _ in OPS:
        q = os.path.join(raiz, r)
        print(f"[PARCHE] {r}: sha256 previo {sha(leer(q)) if os.path.exists(q) else '(no existe)'}")
    p = plan(raiz)
    for r, _, _, estado in p:
        print(f"[PARCHE] {estado:12s} {r}")
    if sys.argv[1] == "--check":
        print("[PARCHE] --check OK: " + ("todo ya aplicado" if all(e == "ya aplicado" for *_, e in p) else
                                         "se puede aplicar"))
        return
    for r, t, modo, estado in p:
        if estado == "ya aplicado":
            continue
        q = os.path.join(raiz, r)
        if t is None:
            os.unlink(q)
            continue
        os.makedirs(os.path.dirname(q), exist_ok=True)
        tmp = q + ".parche.tmp"
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        if modo is not None:
            os.chmod(tmp, modo)
        else:
            os.chmod(tmp, os.stat(q).st_mode & 0o777)
        os.replace(tmp, q)
    for tipo, r, s0, s1, _, _ in OPS:
        q = os.path.join(raiz, r)
        if tipo == "del":
            print(f"[PARCHE] {r}: {'borrado' if not os.path.exists(q) else 'FALLA sigue ahí'}")
        else:
            final = sha(leer(q))
            print(f"[PARCHE] {r}")
            print(f"[PARCHE]   sha256 final  {final} {'OK' if final == s1 else 'FALLA'}")
    print("[PARCHE] --apply HECHO")


if __name__ == "__main__":
    main()
