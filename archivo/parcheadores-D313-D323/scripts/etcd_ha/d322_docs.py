#!/usr/bin/env python3
# d322_docs.py — DAY322 [VAULT-ARRANQUE-D322]: documentación del arranque de Vault destapado por Falco.
#   - ADR-060: plan de 8e.4d y párrafo «8e.4d, DAY322» en la sección 7 (qué pasaba, decisiones de Alonso, cómo queda).
#   - BACKLOG: sección DAY322 (decisiones, medido en lab y banco, hallazgos, DEBT-VAULT-SELLADO-ALERTA-001, pendiente).
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d322_docs.py --check | --apply
# Todo o nada: --check comprueba que cada fichero está en su estado de partida (sha256) o ya parcheado; --apply escribe
# todo solo si --check pasa. Idempotente: dos --apply dejan lo mismo.
import hashlib, json, os, sys, tempfile
D = json.loads(r'''{
"cambios": [
{
"ruta": "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md",
"sha_antes": "e0c523f57b35a99d7ecd65b19f718653b37962f90e8767ad73d4d44c536ce6ad",
"sha_despues": "827ec208158abd902cea59d452eba327aae723a3e410ab869dd5f794b1f0fd60",
"trozos": [
[
"    informado (H-F).\n  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J), en\n    tres commits: **8e.4d-1** (hecho, 464c733bc) el manager; **8e.4d-2** (hecho DAY321) los sensores; **8e.4d-3** el E2E.\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n\n## 6. Diseño fino de 8e.1 (cerrado DAY318)\n",
"    informado (H-F).\n  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J), en\n    tres commits: **8e.4d-1** (hecho, 464c733bc) el manager; **8e.4d-2** (hecho DAY321) los sensores; **8e.4d-3** el E2E.\n    Antes de 8e.4d-3, lo que la vigilancia destapó el DAY322: el arranque de Vault sin Vagrant (31ae20e62, 3cb29fee0;\n    ver «8e.4d, DAY322» en la sección 7).\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n\n## 6. Diseño fino de 8e.1 (cerrado DAY318)\n"
],
[
"con 9 mutaciones cazadas, los instaladores restauran con configuraciones rotas y `lib_apt_oficial.sh` rechaza claves\najenas. Lab: los cinco agentes en 4.14.10-1 desde el apt de Wazuh y conectados, etcd y defender en su grupo, Falco\n0.43.1 en las dos VMs con 3 reglas activas, argus-disco `uso=4 estado=OK`, `pipeline-status` en ✅.\n",
"con 9 mutaciones cazadas, los instaladores restauran con configuraciones rotas y `lib_apt_oficial.sh` rechaza claves\najenas. Lab: los cinco agentes en 4.14.10-1 desde el apt de Wazuh y conectados, etcd y defender en su grupo, Falco\n0.43.1 en las dos VMs con 3 reglas activas, argus-disco `uso=4 estado=OK`, `pipeline-status` en ✅.\n\n**8e.4d, DAY322: lo que la vigilancia destapó en el arranque de Vault [VAULT-ARRANQUE-D322].** Falco dio 7 CRITICAL\n`argus_lab_clave_leida_ajeno` en la VM etcd al arrancar el lab: `curl` desde `bash` leyendo `etcd-server.key`. Era el\ndesellado del lab, y midiendo por qué corría se vio que **Vault no volvía solo de un arranque**:\n`logrotate.timer` (`Persistent=true`) corre al arrancar tras una noche apagada, el `postrotate` del audit mandaba\nSIGHUP a un Vault que aún arrancaba (`Failed with result 'protocol'`), `Restart=on-failure` lo levantaba **sellado** y\nel desellado, ligado a `multi-user.target`, ya se había descartado («Dependency failed»). Solo lo desellaba, de\nrebote, el `systemctl start` del aprovisionador `etcd-server-unit` (con `Wants=` del desellado: un `start` de una\nunidad activa arranca sus `Wants=` inactivos). En un hospital, tras un corte de luz, Vault se habría quedado sellado y\nel etcd-server sin claves HMAC; y en 24x7, cada caída de Vault. Decisiones de Alonso:\n- **Identidad propia del desellado** (opción b): `CN=OU=argus-vault-unseal`, sin ninguna política en Vault\n  (`sys/seal-status` y `sys/unseal` no la piden; el listener exige certificado de cliente solo para el TLS). Descartada\n  (a), que Falco lo tratara como herramienta de administración: un desellado comprometido seguiría teniendo la\n  identidad que lee y escribe las claves HMAC.\n- **Las 17 trazas NOTICE por `pipeline-status` se aceptan** (2 `curl` + 15 `etcdctl`, padre `sudo`, constantes en\n  cuatro pasadas): dejan rastro de quién leyó la clave y cuándo. Se mide en 8e.4d-3 cuántas deja un `etcd-vm-check`\n  con etcd caído (reevalúa cada 2 s); si pasa de un límite, se agrupa en Wazuh.\n- **Regla aparte para los intentos fallidos de leer una clave** (EACCES/EPERM, WARNING), en 8e.4d-3 con su E2E.\n\nCómo queda: `provisioning/vault/` (script, unidad y logrotate) y `scripts/etcd_ha/vault_arranque_instalar.sh`\n(aprovisionador `vault-arranque`, `run: always`, antes de `vault-server`): el desellado va `WantedBy=vault.service`\n(cada arranque de Vault, también un `Restart`, lo dessella); el `postrotate` solo manda SIGHUP con Vault activo (si\narranca, espera hasta 60 s); la identidad se comprueba (CA, CN, OU, clave que casa) y no se reescribe si el\ncertificado no cambia. El etcd-server pasa a `After=` (no `Wants=`) del desellado. Falco: el desellado es dueño de su\nclave (`curl` hijo de `bash` hijo de pid 1) y la lectura de una clave cuenta solo si el `open` tuvo éxito\n(`fd.num>=0`, como `open_read` del reglamento oficial: GNU `install` hace `openat(destino, O_RDONLY|O_PATH|O_DIRECTORY)`,\nque falla sin leer). **Solo laboratorio**: en producción no hay clave de desellado en disco; ahí la protección es\navisar de Vault sellado (DEBT-VAULT-SELLADO-ALERTA-001).\n\nMedido DAY322 (detalle en BACKLOG, «DAY322»): banco con Vault 2.2.1 y Falco 0.43.1 oficiales (firma comprobada); lab,\n`d322_reinicio_vault.sh` R1-R6 en ✅ (`sudo systemctl reboot` sin Vagrant con una rotación pendiente: logrotate rota,\nVault arranca a la primera, lo dessella su unidad sin aprovisionadores; SIGKILL: vuelve desellado en 7 s; 0 CRITICAL);\ninstalar una clave en `/etc/argus-pki` no da evento y copiarla fuera da 1 CRITICAL.\n"
]
]
},
{
"ruta": "docs/BACKLOG.md",
"sha_antes": "bd2f959af74893c32529198bc0115f421880b6a94dff0cef7316effef2133c87",
"sha_despues": "779c91890e65b9a026f944d57ae208cb10b9cb2bad1fb6118b3baa85336457fb",
"trozos": [
[
"--si`, `d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del\nPR1. Sin orden decidido: DEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001, DEBT-LAB-ZONA-HORARIA-001,\nDEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001, DEBT-HARDENED-FALCO-RUTAS-001.\n",
"--si`, `d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del\nPR1. Sin orden decidido: DEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001, DEBT-LAB-ZONA-HORARIA-001,\nDEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001, DEBT-HARDENED-FALCO-RUTAS-001.\n\n## DAY322 — el arranque de Vault sin Vagrant, destapado por Falco [VAULT-ARRANQUE-D322]\n\nCommits: `886515c78` (medidor de eventos de Falco, `scripts/etcd_ha/d322_medir_falco_admin.sh`), `31ae20e62` (Vault\narranca y se dessella sin Vagrant; desellado con identidad propia), `3cb29fee0` (Falco solo cuenta lecturas con éxito;\n`vault-arranque` no reinstala una identidad sin cambios) y este de documentación. Diseño y decisiones en ADR-060,\nsección 7 («8e.4d, DAY322»).\n\n### Decisiones de Alonso (DAY322)\n- Las 17 trazas NOTICE `argus_lab_clave_leida_admin` por cada `pipeline-status` se aceptan; se mide en 8e.4d-3 cuántas\n  deja un `etcd-vm-check` con etcd caído y, si pasa de un límite, se agrupan en Wazuh.\n- El desellado del lab tiene identidad propia (opción b): `CN=OU=argus-vault-unseal`, sin políticas en Vault.\n- El test del reinicio de Vault entra en `lab-e2e-vigilancia`.\n- Regla de Falco aparte para los intentos fallidos de leer una clave (EACCES/EPERM, WARNING), en 8e.4d-3 con su E2E.\n\n### Medido en el lab (horas UTC)\n- Falco en la VM etcd: 17 eventos por `pipeline-status` (2 `curl` + 15 `etcdctl`, padre `/usr/bin/sudo`,\n  `etcd-server.key`) en las cuatro pasadas medidas (DAY321 12:03, 12:57 y 13:00; DAY322 06:30). Y 7 CRITICAL a las\n  06:26 y 06:28: `curl` con padre `bash` y `etcd-server.key`, de `argus-vault-unseal`.\n- Arranque del DAY322 (06:25:57): `logrotate.service` 06:25:59-06:26:00 rota `audit.log`; su `postrotate` manda SIGHUP a\n  Vault (PID 459) en arranque: `Failed with result 'protocol'`; `argus-vault-unseal`: «Dependency failed»;\n  `Restart=on-failure` levanta Vault a las 06:26:07, sellado. El etcd-server (PID 540, sin reinicio) avisa\n  `[ETCD-VAULT-NO-DISPONIBLE]` y `[ETCD-VAULT-RECUPERADO]` a los 16 s, cuando el `systemctl start` del aprovisionador\n  `etcd-server-unit` de `make up` arrastra el desellado por `Wants=` (06:26:13; otra vez con `vagrant up etcd`, 06:28:46).\n- Tras el arreglo, `d322_reinicio_vault.sh`: R1 logrotate rota en el arranque, R2 Vault a la primera (NRestarts=0),\n  R3 desellado por su unidad sin aprovisionadores, R4 Vault y etcd-server sanos, R5 tras SIGKILL vuelve desellado en\n  7 s (NRestarts 0 -> 1), R6 0 CRITICAL (34 NOTICE de los `etcd_vm_estado.sh` del propio test). VM de vuelta en 40 s.\n- `install` de una clave en `/etc/argus-pki`: 0 eventos; `install` de `argus-vault-unseal.key` a `/tmp`: 1 CRITICAL\n  (`proc=/usr/bin/install padre=/usr/bin/sudo`).\n\n### Medido en el banco\n- Vault 2.2.1 (releases.hashicorp.com, SHA256SUMS con firma de HashiCorp) con el listener del lab (mTLS obligatorio):\n  el desellado nuevo en 6 casos (sin inicializar rc 0; sellado; ya desellado; sin `unseal.key`; certificado de otra\n  CA, curl rc 56; Vault parado, curl rc 7). Sin certificado de cliente, `sys/seal-status` no responde (rc 56): la\n  identidad hace falta.\n- Falco 0.43.1 (tarball oficial, firma con la huella de `provisioning/falco/CLAVE`): `--dry-run` con las reglas nuevas,\n  3 activas. En el contenedor no hay eBPF: el linaje (`proc.apid[2] = 1`) se midió en el lab (R5 + R6).\n- `vault_arranque_instalar.sh` con `systemctl` simulado: otra CA, CN ajeno, clave que no casa y sin PKI fallan; bueno,\n  idempotente, rotación e identidad sin cambios (no reescribe la clave). `postrotate` con estados simulados: activo,\n  arrancando->activo, parado, fallido, arrancando siempre (60 esperas). `logrotate -d` acepta el fichero.\n  `d312_pki.sh init` (9 hojas) y `cliente` sobre una PKI vieja. `d322_reinicio_vault.sh` con `vagrant` simulado: pasa,\n  falla un criterio, falla la previa y la VM no vuelve (el trap deshace la rotación pendiente).\n- `strace` de GNU install 9.4: `openat(destino, O_RDONLY|O_PATH|O_DIRECTORY)` antes de crear el destino.\n\n### Hallazgos DAY322\n- Dos predicciones fallidas, y las dos se pararon a medir: la caída de Vault no era la red (la unidad ya tiene\n  `After=network-online.target`) sino el SIGHUP de logrotate; y quien desellaba no era un reinicio del etcd-server sino\n  el `start` de su unidad activa, que arranca sus `Wants=` inactivos.\n- La macro de lectura de Falco contaba `open` fallidos: el sondeo `O_PATH|O_DIRECTORY` de `install` daba un CRITICAL\n  en cada `vagrant up` (los aprovisionadores `file` de la identidad son `run: always`).\n- Las unidades que escribía `vault-server` con `umask 077` salían 0600 («marked world-inaccessible» en el journal); las\n  de `vault-arranque` van 0644.\n- Por vigilar: el aprovisionador `vault-server` (solo al crear la VM) usa `vault status` con la clave del etcd-server;\n  si alguna vez corre con Falco instalado, dará CRITICAL. En un lab desde cero Falco se instala después.\n- Sin probar en el lab: el camino desde cero (`vault-arranque` antes de `vault-server`, Vault sin inicializar: el\n  desellado da rc 0 en el banco). Lo cubre el EMECAS+++.\n\n### DEBT-VAULT-SELLADO-ALERTA-001 — ABIERTA (nueva DAY322, propuesta de Claude, por decidir)\nEn producción no hay clave de desellado en disco: tras un reinicio o una caída, Vault queda sellado hasta que alguien\nlo desselle (procedimiento manual, o auto-unseal con HSM/KMS). El etcd-server sigue (`[ETCD-VAULT-NO-DISPONIBLE]`,\núltima ventana conocida; sin ella `/secrets` da 503) y el pipeline sigue protegiendo sin firmar. Falta que Wazuh lo\nconvierta en una alerta que el admin vea, y el procedimiento de desellado documentado.\n**Test de cierre:** con Vault sellado a mano, el `alerts.json` del manager tiene la alerta en menos de un minuto y el\nprocedimiento lo deja desellado.\n\n### Pendiente (por orden)\n8e.4d-3 (`lab-e2e-vigilancia` dentro de `lab-e2e`: FIM en `/etc/argus-pki`, umbral del disco bajado, audit de Vault\nroto con `chattr`, divergencia del vigía, lectura ajena de una clave, intento fallido de leer una clave (regla nueva),\nel reinicio de Vault de `d322_reinicio_vault.sh` y las trazas de un `etcd-vm-check` con etcd caído, comprobados en el\n`alerts.json` del manager), sus docs, 8e.5 (bootstrap con `argus-infra init --si`, `d303_veredicto_protegidos.sh`\nP1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1. Sin orden decidido:\nDEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001, DEBT-LAB-ZONA-HORARIA-001, DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001,\nDEBT-HARDENED-FALCO-RUTAS-001, DEBT-VAULT-SELLADO-ALERTA-001.\n"
]
]
}
],
"nuevos": []
}''')
def sha(t): return hashlib.sha256(t.encode()).hexdigest()
def leer(p):
    try: return open(p, encoding="utf-8").read()
    except FileNotFoundError: return None
def plan():
    acciones, errores = [], []
    for c in D["cambios"]:
        t = leer(c["ruta"])
        if t is None: errores.append(f"{c['ruta']}: no existe"); continue
        h = sha(t)
        if h == c["sha_despues"]: print(f"  ya parcheado  {c['ruta']}"); continue
        if h != c["sha_antes"]:
            errores.append(f"{c['ruta']}: sha256 {h[:16]} no es el de partida ({c['sha_antes'][:16]}) ni el parcheado"); continue
        for o, n in c["trozos"]: t = t.replace(o, n, 1)
        assert sha(t) == c["sha_despues"]
        acciones.append((c["ruta"], t, None)); print(f"  se parchea    {c['ruta']} ({len(c['trozos'])} trozos)")
    for n in D["nuevos"]:
        t = leer(n["ruta"])
        if t == n["contenido"]: print(f"  ya está       {n['ruta']}"); continue
        if t is not None: errores.append(f"{n['ruta']}: existe con otro contenido"); continue
        acciones.append((n["ruta"], n["contenido"], n["modo"])); print(f"  se crea       {n['ruta']}")
    return acciones, errores
def escribir(ruta, texto, modo):
    d = os.path.dirname(ruta) or "."
    os.makedirs(d, exist_ok=True)
    m = modo if modo is not None else (os.stat(ruta).st_mode & 0o777)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".d322_")
    with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(texto)
    os.chmod(tmp, m); os.replace(tmp, ruta)
if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: python3 scripts/etcd_ha/d322_docs.py --check | --apply"); sys.exit(2)
    if not os.path.isfile("Vagrantfile") or not os.path.isdir("scripts/etcd_ha"):
        print("[D322] FALLA: hay que lanzarlo desde la raíz del repo"); sys.exit(2)
    acciones, errores = plan()
    if errores:
        print("[D322] FALLA, no se toca nada:"); [print("  - " + e) for e in errores]; sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"[D322] check OK: {len(acciones)} fichero(s) por escribir"); sys.exit(0)
    for r, t, m in acciones: escribir(r, t, m)
    print(f"[D322] apply OK: {len(acciones)} fichero(s) escrito(s)")
