#!/usr/bin/env python3
# d318_docs_cierre.py — DAY318, cierre del día: prompt de continuidad para DAY319 (empieza en 8e.3d) y BACKLOG con 8e.3a-8e.3c
# (medidas de banco y lab, hallazgos, DEBT-FW-TEST-IPSET-INJECTION-DEBIL-001).
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_docs_cierre.py --check|--apply <raíz>
# Todo o nada e idempotente: un fichero NUEVO se crea si no existe y se da por hecho si ya tiene su sha256; uno BORRADO
# se borra si tiene el sha256 esperado y se da por hecho si ya no está; cada CAMBIO se aplica si su texto viejo aparece
# una vez y se da por hecho si ya está el nuevo. Si algo no cuadra, no se escribe nada. Imprime los sha256.
import hashlib
import os
import sys

NUEVOS = []

BORRADOS = []

CAMBIOS = {
    'docs/continuity/PROMPT_CONTINUE_CLAUDE.md': [
        ('# Prompt de continuidad — DAY318 (tras DAY317, miércoles 2026-11-04)\n\nHola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama\n`feat/etcd-mtls-vault` (PR1, un nodo). Responde siempre en español. Lee, en este orden:\n`docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md` (entero: contexto medido, decisiones D1-D11, plan 8e.1-8e.5\ny el **diseño fino de 8e.1 con sus puntos abiertos**), el final de `docs/BACKLOG.md` (sección\n`[MANIFIESTO-PROTEGIDOS-D317]` y, antes, las de los pasos 6 y 7) y `docs/ml-heads/day312_diseno.md` (diseño y\nresultados de los pasos 6 y 7).\n\n**DAY318 empieza el desarrollo de 8e.** DAY317 terminó solo con documentación: no se escribió código de 8e.\n\n## Hecho DAY317\n\n| paso | qué | estado |\n|---|---|---|\n| 6a | `ml-defender-etcd-server.service` en la VM etcd (provisioner `etcd-server-unit`) | commit 430f12421 (y 8834cad88) |\n| 6b | Makefile: `etcd-vm-deploy`/`-estado`/`-check`/`-aviso`; `etcd-server-start/stop/status` actúan en la VM; `up`/`halt` incluyen etcd | commiteado |\n| 6c | `pipeline-status` mira el etcd-server, cada miembro etcd (líder, term, retraso) y Vault de la VM (`scripts/etcd_ha/etcd_vm_estado.sh`) | commiteado |\n| 6d | fuera del defender el etcd-server y su unidad; `etcd-server.json` = el de la VM; smoke enterprise con `etcd-server.smoke-enterprise.json` (DEBT-VAULT-ENTERPRISE-SMOKE-VM-001) | commiteado |\n| 7 | instrumento de reinicio `d317_reinicio_vm.sh` / `d317_reinicio_defender.sh` con veredicto: `reinicio_vm_2` PASA | commiteado |\n| 8d | provisioner global `apt-espera` (espera a unattended-upgrades, `DPkg::Lock::Timeout 600`) | commiteado |\n| 8a | el bootstrap hace `etcd-vm-deploy` en `[6c/8]`, antes de `[7/8]` | commiteado |\n| 8b | `lab-e2e-reinicio-etcd`: lab-e2e pasa a seis E2E | commiteado |\n| 8c | `emecas` levanta las 6 VMs; `emecas+++` gana el Acto IV (adapters desde cero, `mitre-check` con `mitre_veredicto.sh`, fases visibles con su hora) | **comprobar con `git log` que está commiteado** |\n\nHashes exactos: `git log --oneline -15`.\n\n## Resultado del EMECAS+++ DAY317 (paso 8): FALLA, y con razón\n\n`make emecas+++ PROFILE=production`: 2 h 20 min. Pasa todo hasta `lab-e2e-protegidos`, que **falla P2**:\n`origenes=192.168.100.50:10780,192.168.100.20:3`. El Acto IV no llegó a correr.\n\nMedido: .20 es la VM etcd. El episodio es UDP. Chrony de la VM etcd pregunta la hora al defender cada 64 s; 207 s /\n64 s = 3 peticiones NTP de cliente que `ddos_v2` marcó junto con la reflexión NTP. Con la mitigación real (hoy en\nsombra), la VM etcd quedaría una hora en el blacklist: **DoS autoinfligido del plano de control**. También medido: la\nwhitelist (`ml_defender_whitelist`, con `RETURN` antes del blacklist en iptables) exime de TODO bloqueo de aRGus, no\nsolo del de la cabeza DDoS.\n\nDecisión de Alonso: no se relaja EMECAS. Entra en este PR1 **DEBT-FW-MANIFIESTO-PROTEGIDOS-001** (ADR-060): un\nmanifiesto firmado por despliegue con categorías `infraestructura`/`intranet`/`dmz`/`externos_criticos`, que sustituye\na `ddos_protegidos` de cada `firewall.json`. Resumen de lo decidido (el detalle, en el ADR):\n- **Firma:** Ed25519; clave privada en Vault transit, una por hospital, no exportable; la pública, compilada en el\n  firewall-acl-agent en dos ranuras (patrón ADR-025).\n- **Entradas:** `{cidr, interfaz obligatoria, mac opcional, motivo}`; límites de prefijo por categoría desde la\n  plantilla de despliegue (`infraestructura` solo /32 y /128).\n- **Cambios:** versión monótona; deshacer firmado.\n- **Candado:** la mitigación real exige manifiesto verificado.\n- **Fallo en caliente:** conserva el último verificado y avisa periódicamente.\n- **Vigilancia:** comprobación continua kernel ↔ manifiesto; alertas de spoofing por interfaz y MAC; Falco, Wazuh y\n  audit de Vault.\n- **`argus-infra`:** solo en la máquina del admin. En el lab vive en la VM etcd por falta de RAM, y esa limitación\n  está escrita.\n- **Fuera de este PR:** regla de dos personas, no ahora (DEBT-FW-DOS-PERSONAS-001).\n\n## Plan DAY318\n\n1. **Comprobar el estado** (Mac, raíz del repo): `git status`, `git log --oneline -15`, que ADR-060 y la sección del\n   BACKLOG estén commiteados, y `make pipeline-status` si el lab está levantado.\n2. **Cerrar los cuatro puntos abiertos del diseño fino** (ADR-060, sección 6), midiendo antes de decidir:\n   1. el set del kernel: reutilizar `ml_defender_whitelist` (recomendado) o uno nuevo;\n   2. borrar el defecto RFC 1918 de DAY300, que el candado vuelve innecesario (lo decide Alonso);\n   3. cómo entra la clave pública en la compilación (opción de CMake que lee un fichero traído de Vault; sin él, la\n      compilación falla) y en qué orden en el bootstrap;\n   4. el nombre de la interfaz del defender hacia la LAN (`eth2` según el Vagrantfile; medirlo en la VM).\n\n   Antes, leer el código que se va a tocar: `firewall-acl-agent/include/firewall/ddos_protegidos.hpp`,\n   `src/core/config_loader.cpp` (lectura de `ddos_protegidos`), `src/main.cpp` (`[ARGUS-WHITELIST-D301]`),\n   `src/api/zmq_subscriber.cpp` (`ALERTA_PROTEGIDO`, contadores `protegidos:`), `src/core/iptables_wrapper.cpp`\n   (cadena con la whitelist), la verificación Ed25519 de ADR-025 (no reinventar) y\n   `scripts/timebase/d303_veredicto_protegidos.sh`.\n3. **8e.1** (firewall-acl-agent), con tests y probado en el banco antes de entregar el parcheador. Después\n   8e.2 → 8e.5 (ADR-060, sección 5), un commit por cambio lógico.\n4. **EMECAS+++ PROFILE=production** de nuevo. Criterio: rc 0; `lab-e2e-protegidos` P1-P6 PASA con .20 aprovisionado\n   por `argus-infra` en el bootstrap; Acto IV con `err_to_row=0` en el adapter de Suricata (eve.json nuevo).\n5. Después: docs del paso 8, merge de PR1 y PR2 (HA) en rama nueva.\n\n## Pendiente de decidir (Alonso), no bloquea 8e\n\n- **eve.json de Suricata.** Los dos `json ilegible` del adapter son huellas de apagados bruscos de la VM. Medido:\n  arranques sin `shutdown`, un registro cortado con otro pegado y 3024 bytes `\\0`. El adapter hizo lo correcto.\n  Propuesta:\n  - (c) `mitre_start` y `ctu_start` dan al adapter solo lo escrito desde T0;\n  - (b) `err_to_row=0` obligatorio;\n  - opcional: las dos líneas reales como casos de `test_to_row`.\n- **DEBT-DDOS-V2-NTP-CLIENTE-001.** El falso positivo del modelo con un cliente NTP. Va a `diag/ml-heads`.\n- **Hipótesis de Alonso, sin medir: el DDoS autoinfligido** (tráfico legítimo de aRGus en despliegue distribuido que\n  parezca un DDoS contra el plano de control). Se mide en PR2, sin adelantarse.\n\n## Requisitos de PR2 (HA), prometidos al BACKLOG en el paso 8\n\n- 3 nodos etcd, cada uno con su etcd-server, y Vault HA de 3 nodos raft. Antes, la decisión de RAM (VMs pequeñas o\n  `ip netns`).\n- Fallos:\n  - tirar un nodo (también el líder) y ver que otro toma el control;\n  - el estado de los componentes sigue sincronizado;\n  - medir el tiempo de sincronización tras la caída y tras la vuelta;\n  - partición 1+1+1.\n- Seguridad: TLS entre pares, `peer-cert-allowed-cn`, una CA por despliegue.\n- Despliegue:\n  - inventario por despliegue;\n  - Ansible genera `vault.hcl` y `etcd.conf.yml`;\n  - medir que `EtcdRegistryStore` pasa todas las direcciones.\n- Además: la hipótesis del DDoS autoinfligido y la categoría `infraestructura` del manifiesto con los 3 nodos.\n\n## Deudas abiertas que no bloquean (ninguna decidida aún)\n\n- DEBT-REPO-RESIDUOS-001: `__pycache__`, los `scripts/d31*_parche.py` y el patcher de 6d sin trackear (decisión de\n  Alonso: dejarlo sin trackear).\n- ggshield no reconoce la clave `paths_ignore`.\n- La regla `/secrets/valid/{c}` del converter deja leer las claves de cualquier componente (pregunta de mínimo\n  privilegio).\n- DEBT-VAULT-ENTERPRISE-SMOKE-VM-001.\n- DEBT-ETCD-VIGILANCIA-FALCO-WAZUH-001 (después de PR2).\n- Las de DAY316: DEBT-ETCD-CONFIG-SIZE-ENDIAN-001, DEBT-ETCD-CLIENT-MANUAL-TESTS-CTEST-001,\n  DEBT-SNIFFER-LIBPCAP-ETCD-001, DEBT-FW-CSV-SIN-FILAS-EN-GATE-001, DEBT-PKI-AT-REST-001,\n  DEBT-GRAPH-HUECO-SIN-CLAVE-001, DEBT-CONFIG-AT-REST-PROTECTION-001.\n\n## Herramientas de Claude (en su contenedor, no en el repo)\n\nBanco Debian 12 en `/srv/banco` (GCC 12.2.0, libsodium 1.0.19, httplib v0.63.0, etcd-cpp-apiv3 v0.15.3, libbpf v1.4.6,\nonnxruntime 1.17.1). `/root/banco_etcd.sh <árbol> <etiqueta>` compila seed-client, crypto-transport, common y\netcd-server con las opciones de production y pasa ctest; los tests se ejecutan DENTRO del chroot. Para 8e hará falta\nañadir al banco el firewall-acl-agent. Si el contenedor es nuevo, hay que rehacerlo.\n\n## Reglas\n\n- Medir, no votar. Predicción escrita antes de medir; si algo no da lo esperado, parar.\n- Todo lo que se compile se prueba antes en el banco con las opciones de production (g++-12, `-std=c++20 -Wall -Wextra\n  -Wpedantic -Werror -O3 -march=native -DNDEBUG -flto -fno-omit-frame-pointer`), dos veces seguidas y contra el\n  comportamiento viejo (mutaciones: tiene que fallar).\n- Parcheadores:\n  - `--check`/`--apply <raíz>`, todo o nada, idempotentes, con sha256 previo y final;\n  - se copian a `scripts/etcd_ha/` y se ejecutan desde allí;\n  - se entregan con su sha256;\n  - un sha por línea de constante, nunca diccionarios largos con hex: ggshield los toma por secretos.\n- Comandos:\n  - exactos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM etcd con `vagrant ssh etcd -c`);\n  - las salidas largas a un fichero, con `; cat` al final;\n  - búsquedas con `git grep`, nunca `grep -r`;\n  - sin emojis.\n- El JSON es la ley.\n- Lo deprecado se borra.\n- No romper la seguridad ni abrir un camino para romperla en producción.\n- El repo es de solo lectura para Claude: los commits los hace Alonso, uno por cambio lógico. **Claude propone siempre\n  el mensaje de cada commit** con el `git commit -m` listo.\n',
         '# Prompt de continuidad — DAY319 (tras DAY318, jueves 2026-11-05)\n\nHola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama\n`feat/etcd-mtls-vault` (PR1, un nodo) y, dentro de ella, con **DEBT-FW-MANIFIESTO-PROTEGIDOS-001** (ADR-060, paso 8e).\nResponde siempre en español. Lee, en este orden:\n`docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md` (entero: decisiones D1-D11, D-A..D-I, F-A..F-I, plan\n8e.1-8e.5 y diseño fino) y el final de `docs/BACKLOG.md` (secciones `[PROTEGIDOS-MANIFIESTO-D318]` y\n`[PROTEGIDOS-PUBKEY-D318]`).\n\n**DAY319 empieza en 8e.3d.** Comprueba antes con `git log --oneline -12` que HEAD es `919813290` (o posterior).\n\n## Hecho DAY318 (10 commits, 07:00-18:10)\n\n| commit | qué |\n|---|---|\n| addc844a | docs: diseño fino de 8e (D-A..D-I) |\n| 77077b47 | 8e.2 Vault transit: clave ed25519 `protegidos-<hospital>` no exportable, rol `argus-infra`, audit fichero + syslog, `make protegidos-pubkey` |\n| 9e9c58c6 | docs de 8e.2 |\n| 3af32373 | 8e.1a verificador del manifiesto (Ed25519 libsodium, JSON estricto, límites, versión, caché, clave compilada en dos ranuras) |\n| f9076a97 | 8e.1b cableado: set `hash:net,iface` con swap atómico, regla `src,src`, candado D6, barrera por IP, avisos D6/D7/D-C; fuera `ddos_protegidos` y la whitelist |\n| b8bf8a4a | docs de 8e.1 |\n| 7d2b58e1 | docs: diseño de 8e.3 (F-A..F-I) y DEBT-FW-ARGUS-INFRA-LLAVE-HW-001 |\n| a5a41ba4 | 8e.3a `libs/protegidos` (estática, `argus::protegidos`); validador de CIDR a `common/include/argus`; falso `stringop-overflow` de GCC 12 con `-march=skylake` |\n| 465e6aa4 | 8e.3b etcd-server: `GET/PUT /v1/protegidos` (authz por OU), `verificar_documento`, etcd `protegidos/vigente` + `protegidos/v/<N>`, `protegidos.hospital_id` (Ansible) |\n| 91981329 | 8e.3c firewall: `get_protegidos()` en etcd-client, consulta cada `consulta_sec`, `[INFRA-CAMBIO]`, anti-rollback con `<cache>.version` |\n\nMedido en el lab al cierre: huella de la clave `52ba6180cf5e8e9a` igual en el firewall y en el etcd-server de la VM;\nel firewall consulta y recibe 404 (no hay manifiesto publicado todavía); el lab está en `dry_run`.\n\n## Lo que queda, por orden\n\n1. **8e.3d** `argus-infra`: un fichero Python con la biblioteca estándar (Python 3.11.2 y OpenSSL 3.0.22 medidos en la\n   VM etcd), instalado por el Vagrantfile en la VM etcd. `init --desde PLANTILLA`, `list`, `add`, `del`, `diff`,\n   `verificar`, `deshacer N`. Login en Vault con `/etc/argus-pki/argus-infra.{crt,key}` (token 300 s, 127.0.0.1),\n   firma con `argus-transit/sign/protegidos-<hospital>`, comprueba los límites de D2 y hace `PUT /v1/protegidos` con\n   el mismo certificado. Plantilla `hospital-lab` en el repo: `.20` infraestructura por `eth2`, `.61` intranet.\n   **Primera prueba real de 8e.3c:** al publicar la versión 1, el firewall tiene que aplicarla sin reiniciar\n   (`[PROTEGIDOS-MANIFIESTO] verificado ... (etcd-server)`, caché y `.version` escritas).\n2. **8e.3e** borrar `set/get/del/list_keys` del etcd-client (`/kv/...`, rutas que el servidor no tiene) tras\n   comprobar con `git grep` que nadie los usa.\n3. **Docs de 8e.3** (ADR-060 y BACKLOG).\n4. **8e.4** vigilancia: kernel ↔ manifiesto, antispoofing `raw PREROUTING`, MAC, `rp_filter`, versión en el latido y en\n   `pipeline-status`, Falco y Wazuh (incluida la alarma de disco del audit de Vault al 75 %).\n5. **8e.5** bootstrap con `argus-infra` (`.20` y `.61`), reescribir `d303_veredicto_protegidos.sh` (P1-P6).\n6. **EMECAS+++ PROFILE=production**: rc 0, `lab-e2e-protegidos` P1-P6 PASA, Acto IV con `err_to_row=0`.\n\nHasta 8e.5, `lab-e2e-mitigacion` y `lab-e2e-protegidos` fallan (sin manifiesto el candado para la mitigación).\n\n## Herramientas de Claude (en su contenedor, no en el repo; si el contenedor es nuevo, hay que rehacerlas)\n\n- Banco Debian 12 en `/srv/banco`: GCC 12.2.0, libsodium 1.0.19, httplib v0.63.0, Vault 2.2.1, gRPC 1.51,\n  cpprest, etcd-cpp-apiv3 v0.15.3 (clonado fuera del chroot: dentro no hay CA del proxy).\n- `/root/banco_fw.sh ÁRBOL ETIQUETA`: compila las librerías, el firewall y su ctest. Variables: `PUBKEY_ACTUAL`,\n  `PUBKEY_SIGUIENTE`, `SOLO_FW=1` (solo el firewall; no sirve si cambia el etcd-client), `ES=1` (también el\n  etcd-server y su ctest), `MARCH=skylake` (la CPU del defender; compilar SIEMPRE también así).\n- `/root/vault_8e3b.sh` (Vault dev con la clave transit) y `/root/e2e_8e3b.sh` (etcd-server con mTLS + firma real +\n  curl por rol, 12 pruebas).\n- `/home/claude/gen/generar.py VIEJO NUEVO SALIDA "cabecera"` + `plantilla.py`: parcheador con ficheros nuevos,\n  borrados y trozos anclados a partir de dos árboles (lista de rutas en `gen/rutas.txt`).\n\n## Reglas\n\n- Medir, no votar. Predicción escrita antes de medir; si algo no da lo esperado, parar.\n- Todo lo que se compile se prueba antes en el banco con las opciones de production (g++-12, `-std=c++20 -Wall -Wextra\n  -Wpedantic -Werror -O3 -march=native -DNDEBUG -flto -fno-omit-frame-pointer`, y además con `-march=skylake`), dos\n  veces y contra el comportamiento viejo (mutaciones: tiene que fallar).\n- Compilar el pipeline completo (`make pipeline-build PROFILE=production`), no un componente suelto.\n- Parcheadores: `--check`/`--apply <raíz>`, todo o nada, idempotentes, con sha256 previo y final; se copian a\n  `scripts/etcd_ha/` y se ejecutan desde allí; se entregan con su sha256; un sha por línea, nunca diccionarios largos\n  con hex (ggshield); quedan sin trackear.\n- Comandos: exactos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM etcd); salidas largas a\n  un fichero con `; cat`; búsquedas con `git grep`; sin emojis.\n- El JSON es la ley. Lo deprecado se borra. No romper la seguridad ni abrir un camino para romperla en producción.\n- El repo es de solo lectura para Claude: los commits los hace Alonso, uno por cambio lógico; **Claude propone siempre\n  el `git commit -m`**. Push solo al cerrar un paso grande o el día: tras cada commit basta `git rev-parse HEAD`.\n'),
    ],
    'docs/BACKLOG.md': [
        ('audit.\n',
         'audit.\n\n---\n\n## DAY318 — pasos 8e.3a, 8e.3b y 8e.3c hechos [PROTEGIDOS-MANIFIESTO-D318]\n\nCommits: a5a41ba4 (8e.3a `libs/protegidos`), 465e6aa4 (8e.3b etcd-server), 91981329 (8e.3c consulta del firewall).\nDiseño: ADR-060, sección 5 (F-A..F-I).\n\n### Medido en el banco\n- 8e.3a: 117/117 con `native` y con `skylake`; una mutación en la librería la caza el ctest del firewall.\n- 8e.3b: firewall 117/117 y etcd-server 8/8 (antes 7) con `skylake` y `native`. Prueba de punta a punta con el\n  etcd-server real (mTLS), firma real de Vault 2.2.1 transit y `curl` por rol, 12/12 dos veces (404 sin manifiesto;\n  PUT con firewall-acl-agent o admin 403; PUT con argus-infra 201; GET devuelve los bytes exactos; sniffer 403;\n  repetida y rollback 409; alterada tras firmar 403). 6 mutaciones detectadas.\n- 8e.3c: 117/117 con `skylake` y `native`; `test_protegidos_manifiesto` 125 comprobaciones; 3 mutaciones (sin suelo,\n  sin bajas, fichero de versión ausente como error) detectadas. La consulta y el arranque de `main.cpp` no tienen test\n  unitario: la primera prueba real es 8e.3d (publicar la versión 1 y verla aplicada sin reiniciar).\n\n### Medido en el lab (PROFILE=production)\n- El etcd-server de la VM y el firewall tienen la misma huella de clave (`52ba6180cf5e8e9a`); reglas 14/15 y 15/15;\n  `[ETCD-PROTEGIDOS] protegidos.hospital_id=hospital-lab (JSON)`; `--check-config` sin defectos; `GET` con argus-infra\n  404 (aún no hay manifiesto).\n- El firewall: `consulta_sec=30`, `suelo=0` y `[PROTEGIDOS-CONSULTA] ... 404`: llega al etcd-server con su certificado y\n  authz le deja pasar.\n\n### Hallazgos DAY318 (8e.3)\n- **`-march=native` engaña al banco:** el defender es `skylake` y el banco otra CPU. Con LTO, GCC 12.2 dio en el lab un\n  falso `-Werror=stringop-overflow` (37 bytes en el búfer corto de 16 de `std::string`) en\n  `test_ipset_injection_integration` que en el banco no salía. Reproducido con `-march=skylake`; arreglado sin\n  desactivar el aviso (cadenas con `ostringstream`). Desde entonces el banco compila también con `-march=skylake`.\n- El despliegue del etcd-server a la VM copia `libsodium.so.23` como librería propia: es el enlace del FIX DAY107 a la\n  `.so.26` (1.0.19) copiado con `cp -L` (ver DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001).\n- La escritura del manifiesto en etcd no es una transacción (primero `protegidos/v/<N>`, después `protegidos/vigente`)\n  y un `PUT` a la vez lo asegura un mutex: con varios etcd-server (PR2) hace falta una transacción de etcd.\n\n### DEBT-FW-TEST-IPSET-INJECTION-DEBIL-001 — ABIERTA (nueva DAY318, Alonso)\n`test_ipset_injection_integration` pasa aunque el validador de CIDR lo acepte todo (medido DAY318 en el banco, también\nen el árbol de 8e.1b): lo más probable es que la línea inyectada (`add argus_h2_evil ...`) falle por sí sola porque ese\nset no existe. Arreglo: que el test cree antes el set víctima.\n**Test de cierre:** con el validador mutado (acepta todo), el test falla; con el bueno, pasa.\n'),
    ],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    nombre = os.path.basename(sys.argv[0])
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(f"uso: {nombre} --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores, hechos, pendientes = [], [], []
    crear, borrar = {}, []
    for rel, esperado, contenido in NUEVOS:
        b = contenido.encode("utf-8")
        if sha(b) != esperado:
            errores.append(f"{rel}: el contenido embebido no da su sha256 (parcheador dañado)")
            continue
        p = os.path.join(raiz, rel)
        if os.path.exists(p):
            a = sha(open(p, "rb").read())
            if a == esperado:
                hechos.append(f"{rel}: creado")
            else:
                errores.append(f"{rel}: ya existe con otro contenido (sha256 {a})")
        else:
            pendientes.append(f"{rel}: crear")
            crear[rel] = b
    for rel, esperado in BORRADOS:
        p = os.path.join(raiz, rel)
        if not os.path.exists(p):
            hechos.append(f"{rel}: borrado")
            continue
        a = sha(open(p, "rb").read())
        print(f"sha256 previo  {rel}: {a}")
        if a == esperado:
            pendientes.append(f"{rel}: borrar")
            borrar.append(rel)
        else:
            errores.append(f"{rel}: sha256 {a}, no el esperado para borrarlo")
    orig, nuevo = {}, {}
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for n, (viejo, nv) in enumerate(cambios, 1):
            cv, cn = t.count(viejo), (t.count(nv) if nv else 0)
            if nv and viejo in nv:
                aplicar, hecho = cv == 1 and cn == 0, cn == 1
            elif nv in viejo:
                aplicar, hecho = cv == 1, cv == 0 and (not nv or cn >= 1)
            else:
                aplicar, hecho = cv == 1 and cn == 0, cv == 0 and cn == 1
            if aplicar:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: cambio {n}")
            elif hecho:
                hechos.append(f"{rel}: cambio {n}")
            else:
                errores.append(f"{rel}: cambio {n}: texto viejo {cv} veces, nuevo {cn} veces")
        nuevo[rel] = t.encode("utf-8")
    print(f"ya aplicados ({len(hechos)})")
    for h in hechos:
        print(f"  = {h}")
    print(f"por aplicar  ({len(pendientes)})")
    for h in pendientes:
        print(f"  + {h}")
    if errores:
        for e in errores:
            print(f"FALLA: {e}")
        print("RESULTADO: FALLA (no se ha escrito nada)")
        return 1
    if modo == "--apply":
        for rel, b in crear.items():
            p = os.path.join(raiz, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p + ".d318tmp", "wb") as f:
                f.write(b)
            os.chmod(p + ".d318tmp", 0o644)
            os.replace(p + ".d318tmp", p)
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                p = os.path.join(raiz, rel)
                m = os.stat(p).st_mode
                with open(p + ".d318tmp", "wb") as f:
                    f.write(nuevo[rel])
                os.chmod(p + ".d318tmp", m)
                os.replace(p + ".d318tmp", p)
        for rel in borrar:
            os.remove(os.path.join(raiz, rel))
    for rel, esperado, _ in NUEVOS:
        print(f"sha256 nuevo   {rel}: {esperado}")
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
