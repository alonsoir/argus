#!/usr/bin/env python3
# d324_manifiesto_nodos.py — DAY324, PR2b paso 5 de DEBT-ETCD-HA-TLS-RAFT-001 [PLANO-CONTROL-D324]: los nodos control-2
# (.21) y control-3 (.22) entran en el manifiesto de protegidos del lab como infraestructura con su MAC (antispoofing
# H-G, como .20). Cambia: tools/argus-infra/plantillas/hospital-lab.json (dos entradas; .20 deja de llamarse "VM etcd"),
# tools/argus-infra/test_argus_infra.py (5 -> 7 entradas), scripts/etcd_ha/test_plano_control.py (C3: cada nodo de
# argus_control_nodos está en la plantilla con su IP/32 y su MAC; y tiene que fallar con copias estropeadas) y el
# comentario de protegidos-bootstrap en el Makefile. Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_manifiesto_nodos.py
import hashlib
import os
import sys

PL = "tools/argus-infra/plantillas/hospital-lab.json"
TAI = "tools/argus-infra/test_argus_infra.py"
TPC = "scripts/etcd_ha/test_plano_control.py"
MK = "Makefile"
PARTIDA = {
    PL: "136ab3734e322284212892d5df42eeedb96d588229cfce1fa14db461be74ad82",
    TAI: "03d58a843dfbb6c709b5489babf5993a1a444ab2f4591dcc48674dc20a52a474",
    TPC: "2754ae3e2a083abd39ea40764ce4d537b858e871cb4c4d3288357e5bac1fd97a",
    MK: "45092349bb422199870487417bc8e9055f5ccd6ac11422fb7f40674edef554f6",
}


def entrada(ip, mac, motivo):
    return ('      { "categoria": "infraestructura", "cidr": "%s/32", "interfaz": "eth2", "mac": "%s", "motivo": "%s" },\n'
            % (ip, mac, motivo))


C3 = '''

def mac_plantilla(mac):  # 080027A20021 -> 08:00:27:a2:00:21 (el formato del manifiesto: minúsculas con dos puntos)
    m = mac.lower()
    return ":".join(m[i:i + 2] for i in range(0, 12, 2))


def errores_c3(pl, nodos):
    """Lista de errores: cada nodo tiene que estar exactamente una vez como infraestructura, con su IP/32, su MAC y la
    misma interfaz que los demás nodos. Lineal en nodos x entradas (ambos acotados: 7 y MAX_ENTRADAS)."""
    entradas = list(pl.get("comun") or [])
    for v in (pl.get("plantas") or {}).values():
        entradas += list(v or [])
    errores, interfaces = [], set()
    for nombre, ip, mac in nodos:
        suyas = [e for e in entradas if isinstance(e, dict) and e.get("cidr") == ip + "/32"]
        if len(suyas) != 1:
            errores.append("%s (%s/32) aparece %d veces en la plantilla (esperada 1)" % (nombre, ip, len(suyas)))
            continue
        e = suyas[0]
        if e.get("categoria") != "infraestructura":
            errores.append("%s: categoria '%s', esperada infraestructura" % (nombre, e.get("categoria")))
        if e.get("mac") != mac_plantilla(mac):
            errores.append("%s: mac '%s', esperada '%s' (la de argus_control_nodos)" % (nombre, e.get("mac"), mac_plantilla(mac)))
        interfaces.add(e.get("interfaz"))
    if len(interfaces) > 1:
        errores.append("los nodos entran por interfaces distintas: %s" % sorted(map(str, interfaces)))
    return errores


def c3():
    import copy
    import json
    rc, out = ruby("nodos", GV, "Vagrantfile")
    if rc != 0:
        falla("C3: el group_vars real no pasa la validación:\\n" + out)
    nodos = [tuple(l.split("\\t")[1:4]) for l in out.splitlines() if l.startswith("nodo\\t")]
    with open(PLANTILLA, encoding="utf-8") as f:
        pl = json.load(f)
    e = errores_c3(pl, nodos)
    if e:
        falla("C3: la plantilla del manifiesto (%s) no lleva los nodos del plano de control: %s" % (PLANTILLA, "; ".join(e)))
    ultimo, ip_u = nodos[-1][0], nodos[-1][1]

    def con(f):
        c = copy.deepcopy(pl)
        for v in c["plantas"].values():
            for x in list(v):
                if x.get("cidr") == ip_u + "/32":
                    f(v, x)
        return c
    estropeadas = [
        ("MAC de %s cambiada" % ultimo, con(lambda v, x: x.update(mac="08:00:27:a2:00:99")), "mac '08:00:27:a2:00:99'"),
        ("sin %s" % ultimo, con(lambda v, x: v.remove(x)), "aparece 0 veces"),
        ("%s en intranet" % ultimo, con(lambda v, x: x.update(categoria="intranet")), "categoria 'intranet'"),
        ("%s dos veces" % ultimo, con(lambda v, x: v.append(dict(x))), "aparece 2 veces"),
    ]
    for nombre, c, esperado in estropeadas:
        e = errores_c3(c, nodos)
        if not any(esperado in x for x in e):
            falla("C3: la copia '%s' debía fallar diciendo '%s'; errores: %s" % (nombre, esperado, e))
    print("[PLANO-CONTROL] C3 PASA: %d nodos (%s) en el manifiesto con su IP/32 y su MAC; %d copias estropeadas rechazadas"
          % (len(nodos), ", ".join(n for n, _, _ in nodos), len(estropeadas)))
'''

CAMBIOS = {
    PL: [
        (entrada("192.168.100.20", "08:00:27:a2:00:20", "VM etcd: etcd, etcd-server, Vault"),
         entrada("192.168.100.20", "08:00:27:a2:00:20", "nodo control-1: etcd, etcd-server, Vault")
         + entrada("192.168.100.21", "08:00:27:a2:00:21", "nodo control-2: etcd")
         + entrada("192.168.100.22", "08:00:27:a2:00:22", "nodo control-3: etcd")),
        ("[PROTEGIDOS-ANTISPOOF-D320] La MAC de .20 es la fija de la VM etcd en el Vagrantfile (H-G): si se cambia allí, "
         "cambiarla aquí.",
         "[PROTEGIDOS-ANTISPOOF-D320] [PLANO-CONTROL-D324] .20, .21 y .22 son los nodos del plano de control "
         "(argus_control_nodos del group_vars, que el Vagrantfile fija en cada VM) con su MAC (H-G): make "
         "test-plano-control (C3) exige que coincidan."),
    ],
    TAI: [
        ('[("infraestructura", "192.168.100.20/32", "eth2"), ("infraestructura", "192.168.100.10/32", "eth2"),\n',
         '[("infraestructura", "192.168.100.20/32", "eth2"), ("infraestructura", "192.168.100.21/32", "eth2"),\n'
         '                          ("infraestructura", "192.168.100.22/32", "eth2"), ("infraestructura", "192.168.100.10/32", "eth2"),\n'),
        ('["192.168.100.20/32", "192.168.100.10/32", "192.168.100.11/32", "192.168.100.12/32",\n',
         '["192.168.100.20/32", "192.168.100.21/32", "192.168.100.22/32", "192.168.100.10/32",\n'
         '                          "192.168.100.11/32", "192.168.100.12/32",\n'),
        ('self.assertEqual(len(p["plantas"]["lab-vagrant"]), 5)   # .20 + los sensores .10 .11 .12 [PROTEGIDOS-SENSORES-D323] + .61',
         'self.assertEqual(len(p["plantas"]["lab-vagrant"]), 7)   # los nodos .20 .21 .22 [PLANO-CONTROL-D324] + los sensores .10 .11 .12 [PROTEGIDOS-SENSORES-D323] + .61'),
    ],
    TPC: [
        ("#      ausente. Necesita ruby (el del sistema vale: solo usa la biblioteca estándar).\n",
         "#      ausente. Necesita ruby (el del sistema vale: solo usa la biblioteca estándar).\n"
         "#   C3 (paso 5, manifiesto): cada nodo de argus_control_nodos está en la plantilla del manifiesto de protegidos\n"
         "#      (tools/argus-infra/plantillas/hospital-lab.json) exactamente una vez, como infraestructura, con su IP/32 y\n"
         "#      su MAC (antispoofing H-G). Y tiene que FALLAR contra copias estropeadas: MAC cambiada, nodo ausente, nodo\n"
         "#      en otra categoría y nodo repetido.\n"),
        ('NODOS_RB = "scripts/etcd_ha/nodos_control.rb"\n',
         'NODOS_RB = "scripts/etcd_ha/nodos_control.rb"\nPLANTILLA = "tools/argus-infra/plantillas/hospital-lab.json"\n'),
        ('          % (len(nodos), ", ".join(n for n, _ in nodos), len(estropeadas)))\n\n\nif __name__',
         '          % (len(nodos), ", ".join(n for n, _ in nodos), len(estropeadas)))\n' + C3 + '\n\nif __name__'),
        ("    c2()\n    print(", "    c2()\n    c3()\n    print("),
    ],
    MK: [
        ("# hospital-lab.json: .20 en infraestructura con su MAC, .61 en intranet).",
         "# hospital-lab.json: los nodos del plano de control .20-.22 en infraestructura con su MAC, .61 en intranet)."),
    ],
}


def falla(msg):
    print("[D324-MANIFIESTO-NODOS] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    nuevos = []
    for ruta, pares in CAMBIOS.items():
        if not os.path.isfile(ruta):
            falla(ruta + " no existe (¿raíz del repo?)")
        with open(ruta, "rb") as f:
            b = f.read()
        if sha(b) != PARTIDA[ruta]:
            falla(ruta + " no es el de partida: sha256 " + sha(b)[:16] + " (esperado " + PARTIDA[ruta][:16] + ")")
        t = b.decode("utf-8")
        for viejo, nuevo in pares:
            k = t.count(viejo)
            if k != 1:
                falla("%s: '%s' aparece %d veces (esperada 1)" % (ruta, viejo.strip()[:60], k))
            t = t.replace(viejo, nuevo)
        nuevos.append((ruta, t))
    import json
    try:
        json.loads(dict(nuevos)[PL])
    except Exception as e:
        falla(PL + " no queda como JSON válido: %s" % e)
    for ruta, t in nuevos:
        st = os.stat(ruta)
        tmp = ruta + ".d324tmp"
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-MANIFIESTO-NODOS] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-MANIFIESTO-NODOS] RESULTADO PASA: %d ficheros; ahora: make test-plano-control" % len(nuevos))


if __name__ == "__main__":
    main()
