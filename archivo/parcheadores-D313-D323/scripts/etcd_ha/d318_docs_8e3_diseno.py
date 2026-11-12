#!/usr/bin/env python3
# d318_docs_8e3_diseno.py — DAY318, docs del diseño cerrado de 8e.3 (ADR-060, decisiones F-A..F-I de Alonso)
# [PROTEGIDOS-MANIFIESTO-D318]: clave pública compilada también en el etcd-server, verificador compartido, rutas, etcd,
# consulta, anti-rollback, argus-infra en Python, plantilla y código muerto del etcd-client; BACKLOG con la aclaración
# de las claves, DEBT-FW-ARGUS-INFRA-LLAVE-HW-001 y la nota de Vault caído en DEBT-VAULT-HA-001.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_docs_8e3_diseno.py --check|--apply <raíz>
# Todo o nada e idempotente; imprime el sha256 de cada fichero antes y después.
import hashlib
import os
import sys

ADR = "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md"
BL = "docs/BACKLOG.md"
CAMBIOS = {
    ADR: [
        ("8e.3 con el diseño cerrado",
         "- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server (`GET`/`PUT`, PUT solo con certificado\n"
         "  OU=argus-infra (D9 bis), verificación de firma, versión y hospital); el firewall lo pide cada\n"
         "  `protegidos.consulta_sec`. El etcd-server necesita leer la clave pública: medido DAY318, hoy su política de Vault\n"
         "  da 403 en `argus-transit/keys/...`. Fichero de despliegue del lab.\n",
         "- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server. Diseño cerrado DAY318 (decisiones de Alonso\n"
         "  F-A..F-I):\n"
         "  - **F-A** El etcd-server verifica con la clave pública **compilada**, la misma que el firewall (patrón ADR-025;\n"
         "    CMake lee el mismo `.hex`). No se le da permiso de lectura en Vault. Que REA vea la pública no importa (es\n"
         "    pública, D9); cambiarla exige cambiar el binario. Consecuencia: con Vault caído no se pueden firmar versiones\n"
         "    nuevas, pero verificar y proteger no depende de Vault.\n"
         "  - **F-B** Un solo verificador: el de 8e.1a pasa a una librería compartida (`libs/protegidos`, jsoncpp +\n"
         "    libsodium) que enlazan el firewall y el etcd-server, con modo \"documento entero, sin planta\" para el servidor.\n"
         "  - **F-C** Un etcd-server sirve a un hospital: `protegidos.hospital_id` en su JSON (Ansible, desde\n"
         "    `argus_hospital_id`). Rutas sin segmento de hospital: `GET /v1/protegidos` (`ou:firewall-acl-agent`,\n"
         "    `ou:argus-infra`) y `PUT /v1/protegidos` (`ou:argus-infra`).\n"
         "  - **F-D** En etcd, el sobre tal cual: `/argus/protegidos/vigente` y `/argus/protegidos/v/<N>` (inmutable). PUT\n"
         "    rechazado si versión <= vigente, firma u hospital no cuadran o se sale de los límites.\n"
         "  - **F-E** El firewall lo pide cada `protegidos.consulta_sec` ([5, 3600], 30) con un método nuevo del etcd-client.\n"
         "    Nueva y verificada: kernel, caché y `[INFRA-CAMBIO]` con altas y bajas. Igual: nada. Menor: rechazo\n"
         "    `motivo=version` (intento de rollback). Servidor caído o 404: sigue con lo vigente y avisa cada `aviso_sec`.\n"
         "  - **F-F** Anti-rollback entre reinicios: `protegidos.version` junto a la caché (versión más alta aplicada) y\n"
         "    consulta al etcd-server antes de aplicar la caché. Caché con versión menor que la del fichero: rechazo y alarma.\n"
         "  - **F-G** `argus-infra`: un fichero Python con la biblioteca estándar (medido en la VM etcd: Python 3.11.2,\n"
         "    OpenSSL 3.0.22), instalado por el Vagrantfile en la VM etcd. `init`, `list`, `add`, `del`, `diff`,\n"
         "    `verificar`, `deshacer N` (contenido de N como N+1 firmado). Firma y verifica con Vault transit; comprueba los\n"
         "    límites de D2 antes del PUT.\n"
         "  - **F-H** Plantilla de despliegue sin firmar en el repo (lab: `.20` infraestructura por eth2, `.61` intranet);\n"
         "    `argus-infra init --desde FICHERO` la rellena y firma la versión 1 solo si no hay ninguna. El bootstrap la usa\n"
         "    en 8e.5.\n"
         "  - **F-I** `set/get/del/list_keys` del etcd-client piden `/kv/...`, rutas que el servidor no tiene: se borran en\n"
         "    un commit propio cuando 8e.3 funcione, tras comprobar con `git grep` que nadie los usa.\n"),
    ],
    BL: [
        ("diseño de 8e.3 y llave hardware",
         "- 8e.3: anti-rollback entre reinicios (ADR-060, sección 6), `[INFRA-CAMBIO]`, `consulta_sec`.\n",
         "- 8e.3: anti-rollback entre reinicios (ADR-060, sección 6), `[INFRA-CAMBIO]`, `consulta_sec`.\n"
         "\n"
         "---\n"
         "\n"
         "## DAY318 — diseño de 8e.3 cerrado [PROTEGIDOS-MANIFIESTO-D318]\n"
         "\n"
         "Decisiones de Alonso F-A..F-I: ADR-060, sección 5 (8e.3). La más discutida, F-A: la clave pública va compilada\n"
         "también en el etcd-server, no se lee de Vault. Aclarado en la discusión (DAY318):\n"
         "- La **privada del manifiesto** no está en ningún disco: vive solo dentro de Vault transit (ed25519, no exportable,\n"
         "  sin borrado, 8e.2). Vault firma por dentro y devuelve la firma: hace de HSM.\n"
         "- La **pública** no es secreta (que REA la vea no da nada, D9). El riesgo es sustituirla, y eso exige cambiar el\n"
         "  binario (firma ADR-025, Falco y Wazuh).\n"
         "- El par **no se regenera** con cada build ni con cada EMECAS: es por hospital y de larga vida; solo cambia en una\n"
         "  rotación deliberada (dos ranuras, D3). Jenkins recibe la pública con `-D`. En el lab cambia cada vez que se\n"
         "  destruye la VM etcd (Vault nace de cero) y el bootstrap la vuelve a traer ([4b/8]).\n"
         "- Lo que sí está en disco es la **privada TLS de `argus-infra`** (`/etc/argus-pki/argus-infra.key`, VM etcd): da\n"
         "  derecho a pedir firmas (desde 127.0.0.1, token de 300 s). Es la que hay que proteger: DEBT-FW-ARGUS-INFRA-LLAVE-HW-001.\n"
         "- Vault puede caerse y hoy no está en HA (Alonso DAY318; DEBT-VAULT-HA-001, PR2). Con F-A, Vault caído solo impide\n"
         "  firmar versiones nuevas: el etcd-server y los firewalls verifican y protegen sin Vault.\n"
         "\n"
         "### DEBT-FW-ARGUS-INFRA-LLAVE-HW-001 — ABIERTA (nueva DAY318, Alonso)\n"
         "En producción la privada del certificado de `argus-infra` no puede estar en el disco de una máquina: va en una\n"
         "llave hardware (USB tipo YubiKey o smartcard PIV) de la que no se puede extraer, y firmar exige tenerla enchufada;\n"
         "Vault registra en su audit quién firmó, cuándo y desde dónde. En el lab queda en el disco de la VM etcd porque no hay\n"
         "VM admin (RAM) ni hardware. Va con DEBT-VAULT-GESTION-TRAS-INIT-001 y con la máquina del admin (ADR-060, D8).\n"
         "**Test de cierre:** sin la llave enchufada `argus-infra` no consigue token de Vault; con ella, firma y queda en el\n"
         "audit.\n"),
        ("Vault HA: la caída deja sin firmar",
         "**Test de cierre:** Vault HA 3 nodos. Kill del líder → failover < 5s → componentes siguen operativos.\n",
         "**Test de cierre:** Vault HA 3 nodos. Kill del líder → failover < 5s → componentes siguen operativos.\n"
         "**DAY318 (Alonso):** Vault puede caerse y aún no hemos hecho ni visto nada de Vault en HA. Hoy, con Vault caído, no\n"
         "se pueden firmar manifiestos de protegidos nuevos (la verificación no depende de Vault: ADR-060, F-A). Va con PR2.\n"),
    ],
}
REESCRITOS = []



def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d318_docs_8e3_diseno.py --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores, hechos, pendientes = [], [], []
    escribir = {}
    for rel, viejo, esperado, contenido in REESCRITOS:
        b = contenido.encode("utf-8")
        if sha(b) != esperado:
            errores.append(f"{rel}: el contenido embebido no da su sha256 (parcheador dañado)")
            continue
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        actual = sha(open(p, "rb").read())
        print(f"sha256 previo  {rel}: {actual}")
        if actual == esperado:
            hechos.append(f"{rel}: reescrito")
        elif actual == viejo:
            pendientes.append(f"{rel}: reescribir")
            escribir[rel] = b
        else:
            errores.append(f"{rel}: sha256 {actual}, ni el viejo esperado ni el nuevo")
    orig, nuevo = {}, {}
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for nombre, viejo, nv in cambios:
            cv, cn = t.count(viejo), (t.count(nv) if nv else 0)
            if nv and viejo in nv:      # inserción: el texto viejo sigue dentro del nuevo
                aplicar, hecho = cv == 1 and cn == 0, cn == 1
            elif nv in viejo:           # borrado o recorte: el nuevo cabe dentro del viejo
                aplicar, hecho = cv == 1, cv == 0 and (not nv or cn >= 1)
            else:
                aplicar, hecho = cv == 1 and cn == 0, cv == 0 and cn == 1
            if aplicar:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: {nombre}")
            elif hecho:
                hechos.append(f"{rel}: {nombre}")
            else:
                errores.append(f"{rel}: {nombre}: texto viejo {cv} veces, nuevo {cn} veces")
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
        todo = dict(escribir)
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                todo[rel] = nuevo[rel]
        for rel, b in todo.items():
            p = os.path.join(raiz, rel)
            m = os.stat(p).st_mode
            with open(p + ".d318tmp", "wb") as f:
                f.write(b)
            os.chmod(p + ".d318tmp", m)
            os.replace(p + ".d318tmp", p)
    for rel, _, esperado, _ in REESCRITOS:
        print(f"sha256 final   {rel}: {esperado}")
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
