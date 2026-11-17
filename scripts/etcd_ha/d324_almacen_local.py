#!/usr/bin/env python3
# d324_almacen_local.py — DAY324, PR2b paso 4 (corrección) [ETCD-CLUSTER-D324]: el etcd-server vuelve a hablar con UN
# endpoint, el miembro local del clúster (https://127.0.0.1:2381; 127.0.0.1 va en el SAN de cada etcd-<nodo>, medido en
# test-etcd-cluster T3/T4). Medido DAY324: con los tres endpoints, etcd-cpp-apiv3 v0.15.3 abre un solo canal gRPC con la
# lista entera como nombre TLS del par y falla ("Peer name 192.168.100.20:2381,192.168.100.21:2381,... is not in peer
# certificate"): escrituras 503. Varias direcciones en los componentes es el PR2d. Toca solo group_vars/argus_dev.yml.
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_almacen_local.py
import hashlib
import os
import sys

GV = "ansible/inventory/group_vars/argus_dev.yml"
PARTIDA = "f159fd6a824161f025400cf05987383f45ef0f3d61501d0723357b53c7370300"
VIEJO = ("# Lab [ETCD-CLUSTER-D324]: los miembros salen de argus_control_nodos (abajo), no de una lista escrita a mano.\n"
         "etcd_almacen_endpoints: \"{{ argus_control_nodos | map(attribute='ip') | map('regex_replace', '^(.*)$', "
         "'https://\\\\1:2381') | list }}\"\n")
NUEVO = ("# Lab [ETCD-CLUSTER-D324]: el etcd-server habla con el miembro local del clúster (127.0.0.1 va en el SAN de cada\n"
         "# etcd-<nodo>). Con varios endpoints etcd-cpp-apiv3 v0.15.3 usa la lista entera como nombre TLS del par y falla\n"
         "# (\"Peer name ... is not in peer certificate\", medido DAY324): varias direcciones en los componentes, PR2d.\n"
         "etcd_almacen_endpoints:\n"
         "  - \"https://127.0.0.1:2381\"\n")


def falla(msg):
    print("[D324-ALMACEN-LOCAL] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def main():
    if not os.path.isfile(GV):
        falla(GV + " no existe (¿raíz del repo?)")
    with open(GV, "rb") as f:
        b = f.read()
    h = hashlib.sha256(b).hexdigest()
    if h != PARTIDA:
        falla(GV + " no es el de partida: sha256 " + h[:16] + " (esperado " + PARTIDA[:16] + ")")
    t = b.decode("utf-8")
    k = t.count(VIEJO)
    if k != 1:
        falla("la línea derivada de etcd_almacen_endpoints aparece %d veces (esperada 1)" % k)
    t = t.replace(VIEJO, NUEVO)
    if t.count("etcd_almacen_endpoints:") != 1:
        falla("etcd_almacen_endpoints no queda definido exactamente una vez")
    st = os.stat(GV)
    tmp = GV + ".d324tmp"
    with open(tmp, "wb") as f:
        f.write(t.encode("utf-8"))
    os.chmod(tmp, st.st_mode & 0o7777)
    os.replace(tmp, GV)
    print("[D324-ALMACEN-LOCAL] %s sha256 %s" % (GV, hashlib.sha256(t.encode("utf-8")).hexdigest()))
    print("[D324-ALMACEN-LOCAL] RESULTADO PASA: etcd_almacen_endpoints = [https://127.0.0.1:2381]")


if __name__ == "__main__":
    main()
