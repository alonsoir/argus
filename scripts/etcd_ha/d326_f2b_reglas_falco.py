#!/usr/bin/env python3
# d326_f2b_reglas_falco.py — DAY326, F2b de DEBT-FALCO-RUIDO-ADMIN-001 [FALCO-RUIDO-D326] (PR2b de
# DEBT-ETCD-HA-TLS-RAFT-001). Dos arreglos de provisioning/falco/argus_lab.yaml, con lo medido en lab-e2e DAY326:
#   - iptables-restore del firewall: estaba permitido por proc.name, que el kernel corta a 15 caracteres
#     (iptables-restor); nunca casaba y daba argus_lab_hijo_inesperado CRITICAL (4 en el defender).
#   - argus-infra con sudo leyendo su propia clave TLS: traza Notice (argus_lab_lectura_admin) en vez de CRITICAL
#     (14 en antispoof y latido, 2 en protegidos-pubkey), con los campos exactos medidos.
# Wazuh no cambia: 100551/100553 se deciden por la prioridad de Falco.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d326_f2b_reglas_falco.py --check | --apply
# Todo o nada: sha256 de partida, cada ancla exactamente una vez y sha256 del resultado antes de escribir. Idempotente.
import hashlib
import os
import sys

TAG = "[D326-F2B]"
FICHEROS = ('provisioning/falco/argus_lab.yaml',)
INICIO = {'provisioning/falco/argus_lab.yaml': '794d207995ca58bbd39918e2dfa6f25ab75d6f934ed935e5f5fc1ec18599eb21'}
FINAL = {'provisioning/falco/argus_lab.yaml': '48f125d88c384c7ff59243c3a64cb54001d4f1117fdd80b68363c5d23d8133ad'}
CAMBIOS = {
    'provisioning/falco/argus_lab.yaml': [('#   lecturas: cada servidor sus claves y su semilla; etcdctl y curl con sudo (pipeline-status) la del etcd-server;\n#             openssl desde bash (provision.sh verify, en pipeline-start) los private.pem.\n', '#   lecturas: cada servidor sus claves y su semilla; etcdctl y curl con sudo (pipeline-status) la del etcd-server;\n#             openssl desde bash (provision.sh verify, en pipeline-start) los private.pem; argus-infra con sudo la suya\n#             (medido DAY326: antispoof, latido, protegidos-pubkey).\n'), ('    (proc.pexepath glob "/vagrant/firewall-acl-agent/build-*/firewall-acl-agent" and\n      (proc.exepath in (/usr/sbin/ipset, /usr/bin/ip) or\n       (proc.exepath = /usr/sbin/xtables-nft-multi and proc.name in (iptables, iptables-save, iptables-restore)))) or\n', '    (proc.pexepath glob "/vagrant/firewall-acl-agent/build-*/firewall-acl-agent" and\n      (proc.exepath in (/usr/sbin/ipset, /usr/bin/ip) or\n       (proc.exepath = /usr/sbin/xtables-nft-multi and proc.name in (iptables, iptables-save, iptables-restor)))) or\n'), ('# ── 1. Hijo inesperado de un proceso vigilado ──────────────────────────────────────────────────────────────────────\n', '# ── 1. Hijo inesperado de un proceso vigilado ──────────────────────────────────────────────────────────────────────\n# [FALCO-RUIDO-D326] xtables-nft-multi es un binario de varias órdenes: lo que lo distingue es argv[0], y proc.name es\n# ese nombre CORTADO a 15 caracteres por el kernel: iptables-restore (16) llega como iptables-restor. Medido DAY326:\n# 4 CRITICAL en lab-e2e (cmd=iptables-restor -w --noflush) con iptables-restore en la lista; nunca casaba.\n'), ('# Herramientas de administración medidas (trazas de bajo nivel, no alertas)\n- macro: argus_lab_lectura_admin\n  condition: >\n    (proc.exepath in (/usr/local/bin/etcdctl, /usr/bin/curl) and proc.pname = sudo and\n     fd.name = /etc/argus-pki/etcd-server.key) or\n', '# Herramientas de administración medidas (trazas de bajo nivel, no alertas)\n# [FALCO-RUIDO-D326] argus-infra (#!/usr/bin/python3 -I) con sudo leyendo SU clave TLS, nada más. Medido DAY326 en\n# control-1: proc.exepath=/usr/bin/python3.11, proc.pexepath=/usr/bin/sudo, proc.cmdline="argus-infra -I\n# /usr/local/sbin/argus-infra <orden> ...", dos lecturas por orden (un contexto TLS para Vault y otro para el\n# etcd-server). Python de Debian 12: al pasar a Debian 13 (python3.13) esto vuelve a dar CRITICAL, que es lo deseado:\n# se mide y se cambia. proc.cmdline lo fija quien lanza el proceso, pero para eso ya hace falta ser root.\n- macro: argus_lab_lectura_admin\n  condition: >\n    (proc.exepath in (/usr/local/bin/etcdctl, /usr/bin/curl) and proc.pname = sudo and\n     fd.name = /etc/argus-pki/etcd-server.key) or\n    (proc.exepath = /usr/bin/python3.11 and proc.pexepath = /usr/bin/sudo and\n     proc.cmdline startswith "argus-infra -I /usr/local/sbin/argus-infra " and\n     fd.name = /etc/argus-pki/argus-infra.key) or\n'), ('  desc: Traza - una herramienta de administración lee una clave (pipeline-status, provision.sh verify)\n', '  desc: Traza - una herramienta de administración lee una clave (pipeline-status, provision.sh verify, argus-infra)\n')],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(f"{TAG} uso: python3 -I scripts/etcd_ha/d326_f2b_reglas_falco.py --check | --apply", file=sys.stderr)
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
        tmp = p + ".d326btmp"
        with open(tmp, "wb") as f:
            f.write(r)
        os.chmod(tmp, modo)
        os.replace(tmp, p)
    print(f"{TAG} APLICADO: {len(nuevos)} escritos, {ya} ya estaban.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
