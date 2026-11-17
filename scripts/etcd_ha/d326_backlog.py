#!/usr/bin/env python3
# d326_backlog.py — DAY326: añade al final de docs/BACKLOG.md las secciones DAY325 y DAY326 (hecho, hallazgos, decisiones
# de Alonso y deudas). Solo añade: el resto del fichero no cambia.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d326_backlog.py --check | --apply
import hashlib
import os
import sys

TAG = "[D326-BACKLOG]"
INICIO = {'docs/BACKLOG.md': 'ff995de830c1bd5871d55ee7f2ec025fdec37462c35b96eca50f852de7eb2eba'}
FINAL = {'docs/BACKLOG.md': 'bd32b2595617bbdaaea300db54ea0cf237ca2c226a8ae2250581327b5708163a'}
CAMBIOS = {'docs/BACKLOG.md': [('- Ramas viejas en el remoto: `chore/cleanup-temp-scripts` (14-may-2026) y `chore/preserve-scratch-scripts`.\n', '- Ramas viejas en el remoto: `chore/cleanup-temp-scripts` (14-may-2026) y `chore/preserve-scratch-scripts`.\n\n## DAY325 — reinicio de uno en uno del clúster etcd, restos del renombrado y un lab-e2e rojo que venía del anfitrión [ETCD-REINICIO-D325] [PLANO-CONTROL-D324]\n\n### Hecho\n- `d207ce9b0` **F1**: `etcd_cluster.yml` sin CRITICAL de Falco (etcdctl con sudo; stat sin leer las claves; salud tras\n  reinicio desde control-1, sin curl) y reinicio de uno en uno (`serial: 1`, salud de TODOS antes del siguiente).\n  `make test-etcd-reinicio` (R0-R6). Medido: PASA; 0 CRITICAL; 1 escritura de 147 fallida a la primera (propuesta en\n  vuelo al ceder el liderazgo; el reintento entra).\n- `627885d5e` restos del renombrado etcd → control-1 en tres E2E de lab-e2e y en `d321_medir_falco_hijos.sh`; el\n  detector de C1 de `test-plano-control` caza también `vm etcd "…"`, bucles sobre nombres de VM y el agente `etcd`.\n\n### Hallazgos DAY325\n- lab-e2e-protegidos rojo (1.ª corrida): **rehacer Vault sin rehacer el defender deja al firewall sin manifiesto**: el\n  Vault nuevo empieza en la versión 1 con otra clave y el defender conserva el suelo anti-retroceso (versión 5) y la caché\n  vieja. Apartando los dos, el firewall acepta la v1. Un EMECAS desde cero no lo ve (destruye también el defender).\n- lab-e2e-protegidos rojo (2.ª corrida): el Mac ahogado por una compilación ajena (carga 46, swap 5,3 de 6,1 GB):\n  `slow fdatasync` de 5-13 s en etcd, reelecciones continuas (término 164 → 216), 18 714 alertas de infraestructura (Raft\n  25-36 veces la línea base) y ningún DROP del ataque. Corrida no válida como prueba; sí como experimento de estrés.\n- Al reiniciar al líder, una escritura en vuelo puede perderse y el cliente solo lo ve por el plazo (5 s).\n\n### Decisiones de Alonso (DAY325)\n- Reinicio del clúster: se deja el orden de la lista de nodos en el PR2b; para el PR2e, seguidores primero y líder al final.\n- F2 (DEBT-FALCO-RUIDO-ADMIN-001): tar y sha256sum del despliegue como traza Notice; la clave pública del manifiesto por\n  `argus-infra clave-publica`, sin curl; test de silencio de Falco en EMECAS desde la creación de las VMs hasta justo\n  antes de lab-e2e. Borrar los instrumentos d321 que ya no hacen falta.\n- Comprobación de recursos del anfitrión al empezar lab-e2e y EMECAS (DEBT-LAB-RECURSOS-ANFITRION-001).\n\n## DAY326 — lab-e2e entero en verde con 3 nodos y Falco sin ruido de administración [CLAVE-PUBLICA-D326] [FALCO-RUIDO-D326] [CLAVE-BRONCE-D326] [DESELLADO-PY-D326]\n\n### Hecho\n- **`make lab-e2e` entero en VERDE** (04:55-06:42Z, Mac a carga ~6), primera vez con el plano de control de 3 nodos y\n  tras el renombrado: reinicios del sniffer, protegidos P1-P6, mitigación C1-C7, vigía, antispoof S1-S4, latido L0-L4,\n  vigilancia C1-C8 (C8: 16 trazas ≤ 60; C7: Vault arranca y se dessella solo) y reinicio del etcd-server.\n- `f409059ca` `argus-infra clave-publica` (cliente de Vault de la herramienta; solo Ed25519 de 32 bytes; 25 tests);\n  `protegidos_pubkey.sh` la usa; se borra `protegidos_pubkey_vm.sh` (curl). Huella `a1b73e22cf85899a`, la misma.\n- `1ac905740` Falco: `iptables-restore` del firewall permitido por su nombre cortado (`iptables-restor`; la lista lo\n  tenía con 16 caracteres y nunca casaba: 4 CRITICAL en lab-e2e) y argus-infra con sudo leyendo su clave = Notice.\n- `b6c8dcfe7` saca `scripts/local_checks.sh`, que entró vacío y por error en `1ac905740`; el prototipo queda en la rama\n  `proto/local-checks`.\n- `151109ec4` `etcd-vm-deploy` sin CRITICAL: `tar` con sudo (solo la orden exacta del script) y `sha256sum` hijo de sudo\n  sobre semilla y private.pem del etcd-server = Notice; `d312_etcd_vm_deploy.sh` usa `sudo sha256sum $(sudo find …)`.\n- `51f4ebd29` `scripts/bronze_key/clave_bronce.py`: la clave HMAC activa por mTLS con la identidad del conversor, en\n  Python estándar (bloque etcd del JSON del ml-detector; 8 tests; `make test-clave-bronce`, paso en emecas). La usan\n  mitre/ctu/custom-start y las claves A y B del E2E del etcd-server; se borra `clave_bronce_ml_detector.sh`.\n- `[DESELLADO-PY-D326]` desellado del Vault del lab en Python estándar (8 tests; `make test-vault-unseal`, paso en\n  emecas); Falco vigila `/etc/vault.d/unseal.key` (antes no) y reconoce al desellado por binario, `proc.args` y\n  fichero, no por el árbol de procesos.\n- Cada regla nueva con su prueba que debe fallar, medida: `python3`, `cat` y `tar` cualesquiera sobre las mismas claves\n  siguen dando CRITICAL.\n\n### Hallazgos DAY326\n- Las CRITICAL de lab-e2e no venían de C5 (que las provoca a propósito) sino de herramientas legítimas que Falco no\n  conocía: argus-infra (14), curl del desellado al arrancar (1), curl de las claves A/B (4), iptables-restore (4).\n- **Carrera del desellado**: al arrancar la VM, Falco abrió la fuente de syscalls 1,7 s antes del desellado y aún no\n  conocía al proceso (padre=<NA>); la regla vieja pedía padre bash y abuelo pid 1. En el reinicio de C7 (2,07 s) no pasó.\n  En una VM recién creada no aparece (Falco ya corre cuando el aprovisionador dessella): EMECAS no lo habría visto.\n- Falco en control-2/3 activo y con las reglas cargadas (provocado: `sudo head -c 0 /etc/etcd/tls/etcd.key` = 1 CRITICAL).\n- El kernel corta proc.name a 15 caracteres; GNU tar no lee si la salida es /dev/null; `vagrant ssh -c` añade `\\r`.\n- `vault operator unseal` solo acepta la clave como argumento (visible en el proceso) o por el aviso interactivo.\n\n### Decisiones de Alonso (DAY326)\n- Desellado en Python estándar (no `vault` oficial: no lee la clave por stdin); vigilar `unseal.key` con el desellado\n  como único lector; claves A/B con una orden propia sin curl; iptables-restore como hijo permitido del firewall.\n- Las recomendaciones al admin sobre dónde guardar la clave de desellado en producción van a ADR-060 sección 7 y al\n  procedimiento de DEBT-VAULT-SELLADO-ALERTA-001 (pendiente de escribir).\n\n### DEBT-FALCO-RUIDO-ADMIN-001 — casi cerrada DAY326\nHecho (arriba). Queda: el test de silencio en EMECAS (0 CRITICAL `argus_*` en defender y control-1..3 desde la creación\nde las VMs hasta justo antes de lab-e2e) y su primera corrida desde cero.\n\n### DEBT-VAULT-SELLADO-ALERTA-001 — ampliada DAY326\nAdemás del aviso de Vault sellado y el procedimiento de desellado, escribir para el admin dónde guardar la clave de\ndesellado en producción: Shamir con `-pgp-keys` y la clave PGP privada en YubiKey (umbral 1 por las guardias), HSM\n(solo Vault Enterprise), KMS de nube (confianza en el proveedor; depende de Internet), transit desde el Vault de la VM\nadmin del hospital; nunca en claro en disco. Comprobar contra la documentación de Vault 2.2.1 antes de fijarlo.\n\n### DEBT-LAB-RECURSOS-ANFITRION-001 — ABIERTA (nueva DAY325, Alonso)\nlab-e2e y EMECAS comprueban al empezar la carga de CPU, la RAM disponible, el swap y el disco del Mac; si falta algo no\narrancan y dicen qué recurso, cuánto hay y cuánto se exige. Umbrales en configuración, con rango y defecto avisado; test\nque pruebe que falla cuando debe. Datos: DAY325 (rojo) carga 46 y swap 5,3/6,1 GB con la presión de memoria en verde (la\nmemoria sola no lo habría detectado); DAY326 (verde) carga ~6 en lab-e2e, 4,65 recién arrancado, swap 0, 170 GB libres.\n\n### DEBT-PROTEGIDOS-SUELO-REVAULT-001 — ABIERTA (nueva DAY325)\nTras rehacer Vault, el suelo anti-retroceso y la caché del firewall son del linaje anterior y el firewall se queda sin\nmanifiesto. Decidir: (a) paso manual del runbook (retirar suelo y caché en cada firewall), o (b) el firewall ata el suelo\na la huella de la clave compilada y lo reinicia con aviso cuando cambia (toca el modelo de seguridad de ADR-060). Medir\nsi el etcd-server tiene un estado equivalente. En el defender, `/var/lib/ml-defender/firewall-linaje-anterior/` (borrar\nal cerrarla).\n\n### DEBT-CURL-FUERA-PRODUCCION-001 — ABIERTA (nueva DAY326)\nQuedan usos de curl en las VMs del lab: `etcd-vm-check` lee `/health` del etcd-server con `sudo curl` (Notice en Falco)\ny otros por inventariar (`git grep -n curl -- scripts Makefile Vagrantfile`). Ninguno nuevo; en producción no puede\nexistir curl. Sustituirlos por herramientas propias en Python estándar, como `clave_bronce.py` y el desellado.\n\n### Para el PR2e (anotado DAY325)\n- Reinicio del clúster etcd: seguidores primero y líder al final (hoy el reinicio persigue al líder y una escritura en\n  vuelo puede perderse).\n', 1)]}
NUEVOS = {}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(f"{TAG} uso: python3 -I scripts/etcd_ha/d326_backlog.py --check | --apply", file=sys.stderr)
        return 2
    if not (os.path.isfile("Vagrantfile") and os.path.isdir(".git")):
        print(f"{TAG} FALLA: ejecútalo desde la raíz del repo", file=sys.stderr)
        return 1
    nuevos, ya = {}, 0
    for p in sorted(FINAL):
        existe = os.path.exists(p)
        if existe and sha(open(p, "rb").read()) == FINAL[p]:
            print(f"{TAG} {p}: ya aplicado")
            ya += 1
            continue
        if p in NUEVOS:
            if existe:
                print(f"{TAG} FALLA: {p} ya existe y no es el esperado; nada escrito", file=sys.stderr)
                return 1
            r = NUEVOS[p].encode("utf-8")
            que = "nuevo"
        else:
            if not existe:
                print(f"{TAG} FALLA: falta {p}; nada escrito", file=sys.stderr)
                return 1
            b = open(p, "rb").read()
            if sha(b) != INICIO[p]:
                print(f"{TAG} FALLA: {p} sha256 {sha(b)} no es el de partida {INICIO[p]} ni el final; nada escrito",
                      file=sys.stderr)
                return 1
            s = b.decode("utf-8")
            for i, (a, n, veces) in enumerate(CAMBIOS[p]):
                c = s.count(a)
                if c != veces:
                    print(f"{TAG} FALLA: {p} ancla {i} aparece {c} veces (se exigen {veces}); nada escrito",
                          file=sys.stderr)
                    return 1
                s = s.replace(a, n)
            r = s.encode("utf-8")
            que = f"{len(CAMBIOS[p])} anclas con sus veces exactas"
        if sha(r) != FINAL[p]:
            print(f"{TAG} FALLA: {p} resultado {sha(r)} no es el esperado {FINAL[p]}; nada escrito", file=sys.stderr)
            return 1
        nuevos[p] = r
        print(f"{TAG} {p}: {que}; resultado {FINAL[p][:16]}")
    if sys.argv[1] == "--check":
        print(f"{TAG} CHECK OK: {len(nuevos)} por aplicar, {ya} ya aplicados")
        return 0
    for p, r in nuevos.items():
        modo = os.stat(p).st_mode if os.path.exists(p) else 0o100644
        tmp = p + ".d326btmp"
        with open(tmp, "wb") as f:
            f.write(r)
        os.chmod(tmp, modo & 0o7777)
        os.replace(tmp, p)
    print(f"{TAG} APLICADO: {len(nuevos)} escritos, {ya} ya estaban.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
