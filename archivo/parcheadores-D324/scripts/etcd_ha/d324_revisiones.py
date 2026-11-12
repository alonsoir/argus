#!/usr/bin/env python3
# d324_revisiones.py — DAY324, PR2a de DEBT-ETCD-HA-TLS-RAFT-001 (medida y diseño). Un paso por commit:
#   epoca            README del etcd-server y _doc de almacen en etcd-server.json y etcd-server.smoke-enterprise.json:
#                    la clave <prefijo>epoca ya no existe ([ADR045-FUERA-D316], registro_componentes.hpp)
#   adr048 TEXTO     ADR-048: estado «En revisión (DAY324)» y la sección «Revisión DAY324» (TEXTO) al final
#   adr049 TEXTO     ADR-049: lo mismo
# Cada paso exige el sha256 de partida de cada fichero que toca (los de main en ba8c934) y el del TEXTO, cambia cada
# ancla exactamente una vez, comprueba el resultado (en los JSON: siguen siendo JSON y solo cambia ese _doc) y escribe
# el sha256 final. Si algo no cuadra, no escribe nada. Uso (Mac, raíz del repo):
#   python3 -I scripts/etcd_ha/d324_revisiones.py epoca
#   python3 -I scripts/etcd_ha/d324_revisiones.py adr048 /tmp/d324_adr048_rev.md
#   python3 -I scripts/etcd_ha/d324_revisiones.py adr049 /tmp/d324_adr049_rev.md
import hashlib
import json
import os
import sys

README = "etcd-server/README.md"
JSONS = ["etcd-server/config/etcd-server.json", "etcd-server/config/etcd-server.smoke-enterprise.json"]
ADR048 = "docs/adr/ADR-048-etcd-ha-raft.md"
ADR049 = "docs/adr/ADR-049-vault-ha-raft-autounseal.md"

PARTIDA = {
    README: "4a5e6c0350569a9288e79c5b64c2e1172ff448a00ce30ae4c30f114726bd6b17",
    JSONS[0]: "5af4946cf8b3e84b16767c993a091f8bacc7ca3e6cd39601b1a3e780d0ac60a8",
    JSONS[1]: "6e3a1f2110d1455b7159aa31306879e0212bdbb8ba8eec953e9336054e3a3ff1",
    ADR048: "b2c24d143bb925af9494ca8b5f36cf5b0b72b2147ab95ed5179e1e6a7105a43e",
    ADR049: "0bfd3ead5a23066d2b91e2b74d9e54d347ab55e545090162c83762b419975234",
}
TEXTO = {
    "adr048": "d351fa1818a3768c511b7b847e897d7d78ab31be0ab189070d0caf7229118e30",
    "adr049": "daa13febde52ccf65a2ae23d6948b747fe72c0803a1f73d731e061e15b52dce7",
}
ESTADO_VIEJO = "- **Estado:** En preparación (implementación post-FEDER)\n"
ESTADO_NUEVO = ("- **Estado:** En revisión (DAY324): se implementa en el PR2 de DEBT-ETCD-HA-TLS-RAFT-001; "
                "ver «Revisión DAY324» al final\n")
README_VIEJO = "  `<prefijo>registro/<CN>`, `<prefijo>latido/<CN>`, `<prefijo>epoca`.\n"
README_NUEVO = "  `<prefijo>registro/<CN>` y `<prefijo>latido/<CN>`.\n"
JSON_VIEJO = "Claves: <prefijo>registro/<CN>, <prefijo>latido/<CN>, <prefijo>epoca."
JSON_NUEVO = "Claves: <prefijo>registro/<CN> y <prefijo>latido/<CN>."


def falla(msg):
    print("[D324-REV] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def leer(ruta, esperado):
    if not os.path.isfile(ruta):
        falla(ruta + " no existe (¿raíz del repo?)")
    with open(ruta, "rb") as f:
        b = f.read()
    if esperado is not None and sha(b) != esperado:
        falla(ruta + " no es el de partida: sha256 " + sha(b)[:16] + " (esperado " + esperado[:16] + ")")
    return b.decode("utf-8")


def una_vez(texto, viejo, nuevo, ruta):
    n = texto.count(viejo)
    if n != 1:
        falla(ruta + ": el ancla aparece " + str(n) + " veces (esperada 1): " + viejo.strip()[:60])
    return texto.replace(viejo, nuevo)


def escribir(cambios):
    for ruta, texto in cambios:
        tmp = ruta + ".d324tmp"
        with open(tmp, "wb") as f:
            f.write(texto.encode("utf-8"))
        os.replace(tmp, ruta)
        print("[D324-REV] " + ruta + " sha256 " + sha(texto.encode("utf-8")))


def paso_epoca():
    cambios = []
    t = una_vez(leer(README, PARTIDA[README]), README_VIEJO, README_NUEVO, README)
    if "epoca" in t:
        falla(README + ": sigue mencionando epoca")
    cambios.append((README, t))
    for ruta in JSONS:
        viejo = leer(ruta, PARTIDA[ruta])
        nuevo = una_vez(viejo, JSON_VIEJO, JSON_NUEVO, ruta)
        a, b = json.loads(viejo), json.loads(nuevo)
        da = a["almacen"].pop("_doc")
        db = b["almacen"].pop("_doc")
        if a != b or "epoca" in db or da == db:
            falla(ruta + ": el cambio toca algo más que almacen._doc")
        cambios.append((ruta, nuevo))
    escribir(cambios)
    print("[D324-REV] RESULTADO PASA: epoca fuera del README y de los dos JSON (solo almacen._doc)")


def paso_adr(nombre, ruta, ruta_texto):
    if not ruta_texto:
        falla("falta la ruta del texto de la revisión")
    rev = leer(ruta_texto, None)
    if sha(rev.encode("utf-8")) != TEXTO[nombre]:
        falla(ruta_texto + ": sha256 " + sha(rev.encode("utf-8"))[:16] + " (esperado " + TEXTO[nombre][:16] + ")")
    t = leer(ruta, PARTIDA[ruta])
    if "## Revisión DAY324" in t:
        falla(ruta + ": ya tiene la revisión DAY324")
    if not t.endswith("\n"):
        falla(ruta + ": no acaba en salto de línea")
    t = una_vez(t, ESTADO_VIEJO, ESTADO_NUEVO, ruta) + rev
    if t.count("## Revisión DAY324") != 1:
        falla(ruta + ": la revisión no quedó una sola vez")
    escribir([(ruta, t)])
    print("[D324-REV] RESULTADO PASA: " + ruta + " con estado «En revisión (DAY324)» y su revisión al final")


if __name__ == "__main__":
    paso = sys.argv[1] if len(sys.argv) > 1 else ""
    if paso == "epoca":
        paso_epoca()
    elif paso == "adr048":
        paso_adr("adr048", ADR048, sys.argv[2] if len(sys.argv) > 2 else "")
    elif paso == "adr049":
        paso_adr("adr049", ADR049, sys.argv[2] if len(sys.argv) > 2 else "")
    else:
        falla("paso '" + paso + "' desconocido (epoca | adr048 TEXTO | adr049 TEXTO)")
