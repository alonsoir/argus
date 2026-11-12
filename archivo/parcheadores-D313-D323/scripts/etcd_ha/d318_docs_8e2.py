#!/usr/bin/env python3
# d318_docs_8e2.py — DAY318: documentación del paso 8e.2 de ADR-060 (resultados medidos, los dos roles de
# administración, hospital-lab, alarma de disco del audit en 8e.4, PUT del manifiesto con el certificado de argus-infra,
# lectura de la clave pública para el etcd-server en 8e.3) y DEBT-VAULT-GESTION-TRAS-INIT-001 en docs/BACKLOG.md.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_docs_8e2.py --check|--apply <raíz>
# Todo o nada e idempotente; imprime el sha256 de cada fichero antes y después.
import hashlib
import os
import sys

ADR = "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md"
BACKLOG = "docs/BACKLOG.md"
MARCA = "[PROTEGIDOS-PUBKEY-D318]"

CAMBIOS_ADR = [
    ("D9 roles",
     "código abierto como el resto de aRGus: la seguridad sale de la clave y de la vigilancia, no de ocultar el código\n"
     "(Kerckhoffs).\n",
     "código abierto como el resto de aRGus: la seguridad sale de la clave y de la vigilancia, no de ocultar el código\n"
     "(Kerckhoffs).\n"
     "\n"
     "**D9 bis. Dos roles de administración, separados a propósito (DAY318).**\n"
     "- `admin` (certificado OU=admin): operación diaria en el etcd-server (rotar claves HMAC, listar componentes,\n"
     "  `/info`). No puede firmar el manifiesto.\n"
     "- `argus-infra` (certificado OU=argus-infra; rol de Vault `argus-infra-admin`): solo firma, verifica y lee la clave\n"
     "  pública del manifiesto de su hospital, y solo publica el manifiesto en el etcd-server. Firmar da inmunidad frente a\n"
     "  todo bloqueo de aRGus: si se compromete el certificado de uso diario, el manifiesto sigue a salvo.\n"
     "- Medido DAY318 (banco y lab): `argus-infra` recibe 403 al leer `argus-hmac`, rotar, exportar o reconfigurar su\n"
     "  clave y firmar con otra; `etcd-server` recibe 403 al firmar. Token de `argus-infra`: 300 s, atado a 127.0.0.1.\n"),
    ("8e.3 PUT con argus-infra y lectura de la pública",
     "- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server (`GET`/`PUT`, PUT solo con certificado de admin,\n"
     "  verificación de firma, versión y hospital); el firewall lo pide cada `protegidos.consulta_sec`. Fichero de\n"
     "  despliegue del lab.\n",
     "- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server (`GET`/`PUT`, PUT solo con certificado\n"
     "  OU=argus-infra (D9 bis), verificación de firma, versión y hospital); el firewall lo pide cada\n"
     "  `protegidos.consulta_sec`. El etcd-server necesita leer la clave pública: medido DAY318, hoy su política de Vault\n"
     "  da 403 en `argus-transit/keys/...`. Fichero de despliegue del lab.\n"),
    ("8e.4 alarma de disco del audit",
     "  `pipeline-status`, reglas Falco (en la VM hardened-x86, `check-prod-falco`) y Wazuh.\n",
     "  `pipeline-status`, reglas Falco (en la VM hardened-x86, `check-prod-falco`) y Wazuh. Falco y Wazuh avisan también\n"
     "  cuando la partición del audit de Vault (`/var/log/vault`) pasa de un umbral (p. ej. 75 %), con prioridad en el log,\n"
     "  y cuando falla uno de los dos audit devices (Alonso DAY318: es su trabajo avisarnos).\n"),
    ("hospital-lab en el ejemplo",
     '  "hospital_id": "lab",\n',
     '  "hospital_id": "hospital-lab",\n'),
]

BACKLOG_NUEVO = """
---

## DAY318 — paso 8e.2 hecho [PROTEGIDOS-PUBKEY-D318]

Commit de código: «DAY318 paso 8e.2: Vault transit para el manifiesto de protegidos ...». Decisiones de Alonso DAY318:
E1 certificado nuevo `argus-infra` separado de `admin` (ADR-060, D9 bis); E2 dos audit devices (fichero + syslog) con
rotación; E3 `argus_hospital_id` en `group_vars` (lab: `hospital-lab`); E4 Vault en Ansible va con PR2; E5
DEBT-VAULT-GESTION-TRAS-INIT-001.

### Medido en el banco (Debian 12, Vault 2.2.1 real, dos pasadas idénticas)
- Desde cero y segunda pasada: rc 0; sonda: clave ed25519, `exportable=False`, `deletion_allowed=False`, los dos audit
  escriben.
- La firma de Vault transit se verifica con `crypto_sign_verify_detached` de libsodium 1.0.19; con un byte de la carga o
  un bit de la firma cambiados, no verifica (confirma D-E para 8e.1).
- Permisos: 7 de 7 con 403 (ver ADR-060, D9 bis).
- Mutaciones: Vault de DAY317 sin transit, otro hospital y syslog caído dan rc 1 con su mensaje. Con syslog caído Vault
  sigue respondiendo: el audit de fichero basta para no bloquearlo, y la sonda lo canta.
- Fallo del instrumento corregido antes de entregar: la primera sonda de syslog buscaba en los últimos 5 minutos y dio
  OK con líneas de una pasada anterior (en la VM habría pasado igual al reaprovisionar). Ahora cuenta antes y después.

### Medido en el lab
`vagrant destroy -f etcd && vagrant up etcd`: inicializado con audit de fichero + syslog, `protegidos-hospital-lab`
ed25519 no exportable versión 1, los dos audit escriben, ningún `❌`. `etcd-vm-deploy`: PASA, SANO.
`make protegidos-pubkey`: clave versión 1, huella 52ba6180cf5e8e9a, en el defender. `pipeline-start`: 8/8, los tres
componentes RUNNING. Se perdieron las claves HMAC de prueba del lab (previsto: DEBT-LAB-VAULT-CLAVES-PRUEBA-001).

### DEBT-VAULT-GESTION-TRAS-INIT-001 — ABIERTA (nueva DAY318, decisión E5 de Alonso)
El root de Vault se revoca tras el `init`: nadie puede rotar la clave transit del manifiesto (las dos ranuras de D3) ni
cambiar políticas o el CIDR autorizado sin rehacer Vault. Lo mismo para `argus-hmac/`. Hace falta una identidad de
gestión de Vault propia, con su certificado y su auditoría. Va con PR2 (Vault HA). Sin la regla de dos personas: en los
hospitales no suele haber tanta gente y uno puede no estar disponible (Alonso DAY318; DEBT-FW-DOS-PERSONAS-001 sigue
sin decidir).

### Para 8e.4 (Alonso DAY318)
Falco y Wazuh avisan cuando la partición del audit de Vault pasa de un umbral (p. ej. 75 %) y cuando falla uno de los
dos audit devices, con prioridad en el log. Retención del audit en el lab: 30 días (`logrotate`); en producción la fija
la ley de cada hospital.
"""


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d318_docs_8e2.py --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    rutas = {ADR: os.path.join(raiz, ADR), BACKLOG: os.path.join(raiz, BACKLOG)}
    orig = {}
    for k, p in rutas.items():
        if not os.path.isfile(p):
            print(f"FALLA: no existe {p}")
            return 1
        orig[k] = open(p, "rb").read()
        print(f"sha256 previo  {k}: {sha(orig[k])}")
    adr = orig[ADR].decode("utf-8")
    hechos, pendientes, errores = [], [], []
    for nombre, viejo, nuevo in CAMBIOS_ADR:
        cv, cn = adr.count(viejo), adr.count(nuevo)
        if cv == 1 and cn == 0:
            adr = adr.replace(viejo, nuevo)
            pendientes.append(nombre)
        elif cn == 1:
            hechos.append(nombre)
        else:
            errores.append(f"{nombre}: texto viejo {cv} veces, nuevo {cn} veces")
    bl = orig[BACKLOG].decode("utf-8")
    nm = bl.count(MARCA)
    if nm == 0:
        bl = bl + ("" if bl.endswith("\n") else "\n") + BACKLOG_NUEVO
        pendientes.append("BACKLOG")
    elif nm == 1 and bl.endswith(BACKLOG_NUEVO):
        hechos.append("BACKLOG")
    else:
        errores.append(f"BACKLOG: la marca {MARCA} aparece {nm} veces sin coincidir con la sección esperada")
    print(f"ya aplicados ({len(hechos)}): {', '.join(hechos) or '-'}")
    print(f"por aplicar  ({len(pendientes)}): {', '.join(pendientes) or '-'}")
    if errores:
        for e in errores:
            print(f"FALLA: {e}")
        print("RESULTADO: FALLA (no se ha escrito nada)")
        return 1
    nuevos = {ADR: adr.encode("utf-8"), BACKLOG: bl.encode("utf-8")}
    if modo == "--apply":
        for k, p in rutas.items():
            if nuevos[k] != orig[k]:
                with open(p + ".d318tmp", "wb") as f:
                    f.write(nuevos[k])
                os.replace(p + ".d318tmp", p)
    for k in rutas:
        estado = "igual" if nuevos[k] == orig[k] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {k}: {sha(nuevos[k])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
