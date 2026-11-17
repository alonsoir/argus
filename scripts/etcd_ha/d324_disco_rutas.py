#!/usr/bin/env python3
# d324_disco_rutas.py — DAY324 [DISCO-RUTAS-D324]: argus-disco con una lista de rutas (decisión de Alonso DAY324, opción
# B, estricto). Antes, en su sitio y con su sha256: scripts/vigilancia/argus_disco.py, scripts/vigilancia/test_argus_disco.py
# y provisioning/vigilancia/disco.json (bloques cat > ... <<'EOF'). Este parcheador cambia lo que lleva tabuladores o
# comentarios: provisioning/wazuh/argus/tests/casos_reglas.tsv (formato nuevo de las líneas de argus-disco y el caso de
# control-2 sin /var/log/vault) y el comentario del agent.conf de argus-control.
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_disco_rutas.py
import hashlib
import os
import sys

CASOS = "provisioning/wazuh/argus/tests/casos_reglas.tsv"
AGENT = "provisioning/wazuh/argus/shared/argus-control/agent.conf"
PARTIDA = {
    CASOS: "9ea124b496253185b97ce91c3f39261e25fcc7b4938e83cd9115679bed0e1c7c",
    AGENT: "5dca6a36f439fddd45d952e22507307028875badff80ba1a9fd5dcac4b258a6d",
}
NUEVOS = {
    "scripts/vigilancia/argus_disco.py": "7c1a086630d8207ef79457ff1c2e99e6a327c323891bd3fbb5aaaece543d3d19",
    "scripts/vigilancia/test_argus_disco.py": "688d48eaa77c0a046f14328c6d7bff97b1462c42d24b3474d7ce5aecba2a29dd",
    "provisioning/vigilancia/disco.json": "4b7cfacf79a9afc9d1933b749748dad122f3a8d4c309b8931dae6582546a6acd",
}
H = "Nov  9 09:00:00 argus-control-1 argus-disco[900]: "
CAMBIOS = {
    CASOS: [
        (H + "ARGUS-DISCO ruta=/var/log/vault uso=3 umbral=75 estado=OK\n",
         H + "ARGUS-DISCO ruta=/var/log/vault,/var/lib/etcd uso=3 umbral=75 estado=OK\n"),
        (H + "ARGUS-DISCO ruta=/var/log/vault uso=81 umbral=75 estado=ALTO\n",
         H + "ARGUS-DISCO ruta=/var/log/vault,/var/lib/etcd uso=81 umbral=75 estado=ALTO\n"),
        (H + "ARGUS-DISCO-ERROR ruta=/var/log/vault: [Errno 2] No such file or directory\n",
         H + "ARGUS-DISCO-ERROR ruta=/var/log/vault: [Errno 2] No such file or directory\n"
         "disco_error_sin_vault\t100542\t8\tNov  9 09:00:00 argus-control-2 argus-disco[900]: ARGUS-DISCO-ERROR "
         "ruta=/var/log/vault: [Errno 2] No such file or directory: '/var/log/vault'\n"
         "disco_ok_etcd_sin_alerta\t100540\t0\tNov  9 09:00:00 argus-control-2 argus-disco[900]: ARGUS-DISCO "
         "ruta=/var/lib/etcd uso=3 umbral=75 estado=OK\n"),
        (H + "ARGUS-DISCO-CONFIG ruta=/var/log/vault (fichero) umbral_pct=75 (fichero) periodo_s=60 (fichero)\n",
         H + "ARGUS-DISCO-CONFIG rutas=/var/log/vault,/var/lib/etcd (fichero) umbral_pct=75 (fichero) periodo_s=60 (fichero)\n"),
    ],
    AGENT: [
        ("  <!-- Disco del audit de Vault (argus-disco, umbral en /etc/argus-vigilancia/disco.json) -->\n",
         "  <!-- Discos del audit de Vault y de los datos de etcd (argus-disco: rutas y umbral en\n"
         "       /etc/argus-vigilancia/disco.json; una línea por partición) [DISCO-RUTAS-D324] -->\n"),
    ],
}


def falla(msg):
    print("[D324-DISCO-RUTAS] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    for ruta, esperado in NUEVOS.items():
        if not os.path.isfile(ruta):
            falla("antes, en su sitio: " + ruta)
        with open(ruta, "rb") as f:
            h = sha(f.read())
        if h != esperado:
            falla(ruta + " no es el entregado: sha256 " + h[:16] + " (esperado " + esperado[:16] + ")")
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
                falla("%s: '%s' aparece %d veces (esperada 1)" % (ruta, viejo.strip()[:70], k))
            t = t.replace(viejo, nuevo)
        nuevos.append((ruta, t))
    for ruta, t in nuevos:
        st = os.stat(ruta)
        tmp = ruta + ".d324tmp"
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-DISCO-RUTAS] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-DISCO-RUTAS] RESULTADO PASA: 2 ficheros (y los 3 nuevos verificados)")


if __name__ == "__main__":
    main()
