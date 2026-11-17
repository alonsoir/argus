#!/usr/bin/env python3
# d326_f2c_despliegue_falco.py — DAY326, F2c de DEBT-FALCO-RUIDO-ADMIN-001 [FALCO-RUIDO-D326] (PR2b de
# DEBT-ETCD-HA-TLS-RAFT-001). El despliegue del etcd-server (make etcd-vm-deploy) sin CRITICAL de Falco, con lo medido:
#   - provisioning/falco/argus_lab.yaml: macro argus_lab_despliegue_etcd_server dentro de la de administración (Notice):
#     sudo tar con la orden exacta del script, y sha256sum hijo de sudo, sobre seed.bin y private.pem del etcd-server.
#   - scripts/etcd_ha/d312_etcd_vm_deploy.sh: sudo sha256sum $(sudo find ...) en vez de sudo xargs sha256sum (padre sudo).
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d326_f2c_despliegue_falco.py --check | --apply
# Todo o nada: sha256 de partida, cada ancla exactamente una vez y sha256 del resultado antes de escribir. Idempotente.
import hashlib
import os
import sys

TAG = "[D326-F2C]"
FICHEROS = ('provisioning/falco/argus_lab.yaml', 'scripts/etcd_ha/d312_etcd_vm_deploy.sh')
INICIO = {'provisioning/falco/argus_lab.yaml': '48f125d88c384c7ff59243c3a64cb54001d4f1117fdd80b68363c5d23d8133ad', 'scripts/etcd_ha/d312_etcd_vm_deploy.sh': '6c0c25e1373aab9d32928a3f6d3761690781280b8254f0c953257c57a9139b24'}
FINAL = {'provisioning/falco/argus_lab.yaml': '1944c2541078fb898ee0c56d664d7b98af787b3f138db8b0b79c758bf5a87427', 'scripts/etcd_ha/d312_etcd_vm_deploy.sh': '06cb7ef74a5d95e578a7c5d829325cb90ec596f0da358e31e14f3e7a647be9cf'}
CAMBIOS = {
    'provisioning/falco/argus_lab.yaml': [('#             openssl desde bash (provision.sh verify, en pipeline-start) los private.pem; argus-infra con sudo la suya\n#             (medido DAY326: antispoof, latido, protegidos-pubkey).\n', '#             openssl desde bash (provision.sh verify, en pipeline-start) los private.pem; argus-infra con sudo la suya\n#             (medido DAY326: antispoof, latido, protegidos-pubkey); tar y sha256sum con sudo la semilla y el\n#             private.pem del etcd-server (d312_etcd_vm_deploy.sh, en etcd-vm-deploy; medido DAY326).\n'), ('     proc.cmdline startswith "argus-infra -I /usr/local/sbin/argus-infra " and\n     fd.name = /etc/argus-pki/argus-infra.key) or\n', '     proc.cmdline startswith "argus-infra -I /usr/local/sbin/argus-infra " and\n     fd.name = /etc/argus-pki/argus-infra.key) or\n    argus_lab_despliegue_etcd_server or\n'), ('# Herramientas de administración medidas (trazas de bajo nivel, no alertas)\n', '# [FALCO-RUIDO-D326] d312_etcd_vm_deploy.sh (make etcd-vm-deploy, en bootstrap) lleva el material del etcd-server del\n# defender a control-1 y lo compara fichero a fichero. Medido DAY326: sudo tar en el defender lee seed.bin y private.pem\n# (2 CRITICAL) y sha256sum los lee en las dos VMs (4 CRITICAL; padre xargs, que pasa a ser sudo). tar puede sacar el\n# contenido, así que solo con la orden exacta del script; sha256sum solo imprime la huella: basta padre sudo. El tar -x\n# de control-1 escribe, no lee: no da evento.\n- macro: argus_lab_despliegue_etcd_server\n  condition: >\n    fd.name in (/etc/ml-defender/etcd-server/seed.bin, /etc/ml-defender/etcd-server/private.pem) and\n    proc.pexepath = /usr/bin/sudo and\n    ((proc.exepath = /usr/bin/tar and\n      proc.cmdline = "tar -C /etc/ml-defender --exclude=etcd-server/etcd-server.json -cf - etcd-server") or\n     proc.exepath = /usr/bin/sha256sum)\n\n# Herramientas de administración medidas (trazas de bajo nivel, no alertas)\n')],
    'scripts/etcd_ha/d312_etcd_vm_deploy.sh': [('D=$(S defender "cd /etc/ml-defender/etcd-server && sudo find . -type f | sort | sudo xargs sha256sum" 2>/dev/null )\nE=$(S control-1 "cd /etc/ml-defender/etcd-server && sudo find . -type f | sort | sudo xargs sha256sum" 2>/dev/null )\n', '# [FALCO-RUIDO-D326] sha256sum hijo directo de sudo (antes de xargs): así lo reconoce Falco como administración\n# (provisioning/falco/argus_lab.yaml, argus_lab_despliegue_etcd_server). La lista la expande la VM, no el Mac.\nD=$(S defender "cd /etc/ml-defender/etcd-server && sudo sha256sum \\$(sudo find . -type f | sort)" 2>/dev/null )\nE=$(S control-1 "cd /etc/ml-defender/etcd-server && sudo sha256sum \\$(sudo find . -type f | sort)" 2>/dev/null )\n')],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(f"{TAG} uso: python3 -I scripts/etcd_ha/d326_f2c_despliegue_falco.py --check | --apply", file=sys.stderr)
        return 2
    if not (os.path.isfile("Vagrantfile") and os.path.isdir(".git")):
        print(f"{TAG} FALLA: ejecútalo desde la raíz del repo", file=sys.stderr)
        return 1
    nuevos, ya = {}, 0
    for p in FICHEROS:
        b = open(p, "rb").read()
        h = sha(b)
        if h == FINAL[p]:
            print(f"{TAG} {p}: ya aplicado")
            ya += 1
            continue
        if h != INICIO[p]:
            print(f"{TAG} FALLA: {p} sha256 {h} no es el de partida {INICIO[p]} ni el final {FINAL[p]}; nada escrito",
                  file=sys.stderr)
            return 1
        s = b.decode("utf-8")
        for i, (a, n) in enumerate(CAMBIOS[p]):
            c = s.count(a)
            if c != 1:
                print(f"{TAG} FALLA: {p} ancla {i} aparece {c} veces (se exige 1); nada escrito", file=sys.stderr)
                return 1
            s = s.replace(a, n)
        r = s.encode("utf-8")
        if sha(r) != FINAL[p]:
            print(f"{TAG} FALLA: {p} resultado {sha(r)} no es el esperado {FINAL[p]}; nada escrito", file=sys.stderr)
            return 1
        nuevos[p] = r
        print(f"{TAG} {p}: {len(CAMBIOS[p])} anclas, una vez cada una; resultado {FINAL[p][:16]}")
    if sys.argv[1] == "--check":
        print(f"{TAG} CHECK OK: {len(nuevos)} por aplicar, {ya} ya aplicados")
        return 0
    for p, r in nuevos.items():
        modo = os.stat(p).st_mode
        tmp = p + ".d326ctmp"
        with open(tmp, "wb") as f:
            f.write(r)
        os.chmod(tmp, modo)
        os.replace(tmp, p)
    print(f"{TAG} APLICADO: {len(nuevos)} escritos, {ya} ya estaban.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
