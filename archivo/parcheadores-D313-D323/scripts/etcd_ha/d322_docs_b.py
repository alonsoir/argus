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
"sha_antes": "827ec208158abd902cea59d452eba327aae723a3e410ab869dd5f794b1f0fd60",
"sha_despues": "4e0a7fc6bca4beebd5acbf2594f4cd35f497c58028be04d47c1da3ba3b22972b",
"trozos": [
[
"  - **8e.4c** (hecho, 1818f4ec) versión del manifiesto en el latido y en `pipeline-status` (H-H) y `rp_filter`\n    informado (H-F).\n  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J), en\n    tres commits: **8e.4d-1** (hecho, 464c733bc) el manager; **8e.4d-2** (hecho DAY321) los sensores; **8e.4d-3** el E2E.\n    Antes de 8e.4d-3, lo que la vigilancia destapó el DAY322: el arranque de Vault sin Vagrant (31ae20e62, 3cb29fee0;\n    ver «8e.4d, DAY322» en la sección 7).\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n",
"  - **8e.4c** (hecho, 1818f4ec) versión del manifiesto en el latido y en `pipeline-status` (H-H) y `rp_filter`\n    informado (H-F).\n  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J), en\n    tres commits: **8e.4d-1** (hecho, 464c733bc) el manager; **8e.4d-2** (hecho DAY321) los sensores; **8e.4d-3** (hecho DAY322, 9aea549ba) el E2E.\n    Antes de 8e.4d-3, lo que la vigilancia destapó el DAY322: el arranque de Vault sin Vagrant (31ae20e62, 3cb29fee0;\n    ver «8e.4d, DAY322» en la sección 7).\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n"
],
[
"raw y filtro; después los sets; los nombres, del JSON), y `lab-e2e` comprueba con `make lab-kernel-limpio` (solo\ncuenta) que tras cada uno no queda nada.\n\n**8e.4d, la vigilancia con Wazuh y Falco (8e.4d-1 y 8e.4d-2 hechos DAY321; 8e.4d-3, el E2E, pendiente).** Decisiones\nde Alonso (DAY321):\n- **Cada sensor en la máquina que vigila**: Falco ve las syscalls del kernel donde corre, y el FIM y el journal son\n  locales. Falco en la VM etcd y en el defender; agente de Wazuh en las dos; el manager sigue en la VM wazuh. La VM\n",
"raw y filtro; después los sets; los nombres, del JSON), y `lab-e2e` comprueba con `make lab-kernel-limpio` (solo\ncuenta) que tras cada uno no queda nada.\n\n**8e.4d, la vigilancia con Wazuh y Falco (8e.4d-1 y 8e.4d-2 hechos DAY321; 8e.4d-3, el E2E, hecho DAY322).** Decisiones\nde Alonso (DAY321):\n- **Cada sensor en la máquina que vigila**: Falco ve las syscalls del kernel donde corre, y el FIM y el journal son\n  locales. Falco en la VM etcd y en el defender; agente de Wazuh en las dos; el manager sigue en la VM wazuh. La VM\n"
],
[
"`d322_reinicio_vault.sh` R1-R6 en ✅ (`sudo systemctl reboot` sin Vagrant con una rotación pendiente: logrotate rota,\nVault arranca a la primera, lo dessella su unidad sin aprovisionadores; SIGKILL: vuelve desellado en 7 s; 0 CRITICAL);\ninstalar una clave en `/etc/argus-pki` no da evento y copiarla fuera da 1 CRITICAL.\n",
"`d322_reinicio_vault.sh` R1-R6 en ✅ (`sudo systemctl reboot` sin Vagrant con una rotación pendiente: logrotate rota,\nVault arranca a la primera, lo dessella su unidad sin aprovisionadores; SIGKILL: vuelve desellado en 7 s; 0 CRITICAL);\ninstalar una clave en `/etc/argus-pki` no da evento y copiarla fuera da 1 CRITICAL.\n\n**8e.4d-3, DAY322: `lab-e2e-vigilancia` [VIGILANCIA-E2E-D322].** Cada caso provoca algo en el lab y exige su alerta en\nel `alerts.json` del manager de Wazuh, escrita después del inicio del caso (`scripts/vigilancia/alertas_wazuh.sh` lee\nsolo lo nuevo, por byte, y detecta la rotación): C1 FIM en `/etc/argus-pki` (554 y 553), C2 umbral del disco bajado\n(100541), C3 audit de fichero de Vault con `chattr +i` (100520; Vault reabre el fichero, ese `open` falla y sigue con el\ndevice de syslog), C5 lectura ajena de una clave (100551), C6 intento fallido de leerla (100552, regla nueva\n`argus_lab_clave_intento_fallido`, EACCES/EPERM; con `fd.num=-1`, `fd.name` es la ruta pedida), C8 trazas de un\n`etcd-vm-check` con etcd parado, C7 el reinicio de Vault sin Vagrant (`d322_reinicio_vault.sh`) y C4 una divergencia del\nvigía (`d320_vigia_e2e.sh` con `D320_EVENTOS=E1`; 100511 y 100512). Dentro de `lab-e2e`, tras `lab-e2e-latido`. Decisiones\nde Alonso: C4 provoca su propia divergencia; C8 midió primero y después es criterio: trazas de Falco <=\n`VIG_C8_MAX_TRAZAS` (defecto 60, parámetro porque otro despliegue puede necesitar más) y todas llegan al manager.\nMedido: 14 trazas y 14 alertas (se predijeron ~255: cada `etcdctl` espera su timeout y en 36 s caben un par de vueltas),\nmenos que un `pipeline-status` sano (17): no hace falta agruparlas. Dos corridas en PASA.\n"
]
]
},
{
"ruta": "docs/BACKLOG.md",
"sha_antes": "779c91890e65b9a026f944d57ae208cb10b9cb2bad1fb6118b3baa85336457fb",
"sha_despues": "1e4f77c7de60aba59311daa74546669affaf26b0eabb4a7b77d84a40f00907bc",
"trozos": [
[
"- Sin probar en el lab: el camino desde cero (`vault-arranque` antes de `vault-server`, Vault sin inicializar: el\n  desellado da rc 0 en el banco). Lo cubre el EMECAS+++.\n\n### DEBT-VAULT-SELLADO-ALERTA-001 — ABIERTA (nueva DAY322, propuesta de Claude, por decidir)\nEn producción no hay clave de desellado en disco: tras un reinicio o una caída, Vault queda sellado hasta que alguien\nlo desselle (procedimiento manual, o auto-unseal con HSM/KMS). El etcd-server sigue (`[ETCD-VAULT-NO-DISPONIBLE]`,\núltima ventana conocida; sin ella `/secrets` da 503) y el pipeline sigue protegiendo sin firmar. Falta que Wazuh lo\nconvierta en una alerta que el admin vea, y el procedimiento de desellado documentado.\n**Test de cierre:** con Vault sellado a mano, el `alerts.json` del manager tiene la alerta en menos de un minuto y el\nprocedimiento lo deja desellado.\n\n",
"- Sin probar en el lab: el camino desde cero (`vault-arranque` antes de `vault-server`, Vault sin inicializar: el\n  desellado da rc 0 en el banco). Lo cubre el EMECAS+++.\n\n### DEBT-VAULT-SELLADO-ALERTA-001 — ABIERTA (nueva DAY322, aceptada por Alonso)\nEn producción no hay clave de desellado en disco: tras un reinicio o una caída, Vault queda sellado hasta que alguien\nlo desselle (procedimiento manual, o auto-unseal con HSM/KMS). El etcd-server sigue (`[ETCD-VAULT-NO-DISPONIBLE]`,\núltima ventana conocida; sin ella `/secrets` da 503) y el pipeline sigue protegiendo sin firmar. Falta que Wazuh lo\nconvierta en una alerta que el admin vea, y el procedimiento de desellado escrito y disponible para el admin (Alonso:\n«con el tiempo se lo aprenderá de memoria»).\n**Test de cierre:** con Vault sellado a mano, el `alerts.json` del manager tiene la alerta en menos de un minuto y el\nprocedimiento lo deja desellado.\n\n"
],
[
"P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1. Sin orden decidido:\nDEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001, DEBT-LAB-ZONA-HORARIA-001, DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001,\nDEBT-HARDENED-FALCO-RUTAS-001, DEBT-VAULT-SELLADO-ALERTA-001.\n",
"P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1. Sin orden decidido:\nDEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001, DEBT-LAB-ZONA-HORARIA-001, DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001,\nDEBT-HARDENED-FALCO-RUTAS-001, DEBT-VAULT-SELLADO-ALERTA-001.\n\n## DAY322 — paso 8e.4d-3 hecho: `lab-e2e-vigilancia` [VIGILANCIA-E2E-D322]\n\nCommit `9aea549ba` y este de documentación. Diseño en ADR-060, sección 7 («8e.4d-3, DAY322»).\n\n### Decisiones de Alonso (DAY322)\n- C4 (divergencia del vigía) la provoca el propio test: `d320_vigia_e2e.sh` con `D320_EVENTOS=E1`.\n- C8 midió primero (sin PASA ni FALLA) y, con el dato, es criterio con `VIG_C8_MAX_TRAZAS` = 60 por defecto, como\n  parámetro: otro despliegue puede necesitar un número mayor.\n- Regla de Falco para los intentos fallidos de leer una clave (EACCES/EPERM, WARNING).\n- DEBT-VAULT-SELLADO-ALERTA-001 aceptada.\n\n### Medido en el lab (horas UTC; suricata y zeek apagadas: 32 GB en el Mac, las seis VMs ocupaban 19,2 GB de RSS)\n- Sonda de C3 (08:35): con `audit.log` en `chattr +i`, el login da HTTP 200, Vault escribe dos `[ERROR] audit: log …\n  underlying pipeline error` (petición y respuesta: reabre el fichero y ese `open` falla) y la 100520 llega al manager\n  en 1 s.\n- Falco con la regla nueva: 4 reglas activas en la VM etcd y en el defender (las mismas 5 syscalls).\n- Corrida 1 (08:41-08:49) y corrida 2 (09:06-09:14), las dos PASA: C1 554 en 8-12 s y 553 en 11-12 s; C2 100541 en\n  45-69 s; C3 100520 en 10 s; C5 100551 en 10 s; C6 100552 en 10 s (`usuario=nobody res=EACCES`, `fichero=` la ruta\n  pedida); C8 14 trazas en Falco (4 `curl` + 10 `etcdctl`) y 14 alertas 100553, `etcd-vm-check` de 36 s; C7 R1-R6;\n  C4 E1 reconciliado en 3-11 s y la 100511 y la 100512 del defender con 3 ms de diferencia.\n\n### Medido en el banco\n- `alertas_wazuh.sh` con un `alerts.json` falso (espera, agente, texto, argumentos mal formados); copia y restauración\n  de `disco.json` (una segunda bajada no pisa la copia); `--dry-run` de Falco con 4 reglas; el driver con `vagrant`\n  falso: todo bien, una alerta que falta, C8 con trazas de más, con alertas de menos y sin línea de partida.\n\n### Hallazgos DAY322 (8e.4d-3)\n- C8: predicción fallida, de ~255 a 14 trazas: el bucle de 2 s de `etcd_vm_estado.sh` lo frena el timeout de cada\n  `etcdctl` con etcd parado. Menos ruido que un `pipeline-status` sano: no se agrupa.\n- Dos errores míos cazados antes de dar nada por bueno: `alerta()` cruzaba agente y espera (lo vio el ensayo con\n  `vagrant` falso) y `sudo wc -l < fichero` (la redirección la abre `vagrant`: salía vacío; lo vio la primera corrida,\n  donde C8 resumió el fichero entero).\n- Wazuh no agrupa ni descarta las trazas NOTICE de Falco: 14 en el agente, 14 en el manager.\n\n### Pendiente (por orden)\n8e.5 (bootstrap con `argus-infra init --si`, `d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS),\nEMECAS+++ PROFILE=production (cubre el lab desde cero: `vault-arranque` antes de `vault-server`) y cierre del PR1\n(README del etcd-server, push, PR). Sin orden decidido: DEBT-ARGUS-INFRA-MOD-001, DEBT-SNIFFER-SYSTEM-SYSCTL-001,\nDEBT-LAB-ZONA-HORARIA-001, DEBT-SUPPLY-CHAIN-ORIGEN-OFICIAL-001, DEBT-HARDENED-FALCO-RUTAS-001,\nDEBT-VAULT-SELLADO-ALERTA-001.\n"
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
