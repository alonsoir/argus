#!/usr/bin/env python3
# d318_8e3a_fix_stringop.py — DAY318, ADR-060 8e.3a, arreglo [PROTEGIDOS-MANIFIESTO-D318]: con -O3 -flto -march=skylake (la CPU del
# defender), GCC 12.2 da un falso -Werror=stringop-overflow en test_ipset_injection_integration al enlazar libs/protegidos
# (cambia el reparto LTO). Las dos cadenas de inyección se construyen con ostringstream: mismos bytes, sin desactivar el
# aviso. Va encima de d318_8e3a_libs_protegidos.py, en el mismo commit.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_8e3a_fix_stringop.py --check|--apply <raíz>
# Todo o nada e idempotente: un fichero NUEVO se crea si no existe y se da por hecho si ya tiene su sha256; uno BORRADO
# se borra si tiene el sha256 esperado y se da por hecho si ya no está; cada CAMBIO se aplica si su texto viejo aparece
# una vez y se da por hecho si ya está el nuevo. Si algo no cuadra, no se escribe nada. Imprime los sha256.
import hashlib
import os
import sys

NUEVOS = []

BORRADOS = []

CAMBIOS = {
    'firewall-acl-agent/tests/unit/test_ipset_injection_integration.cpp': [
        ('// get_entry_count (los PRIMARIOS) no dependen de eso y prueban el cierre por si solos.\n#include <gtest/gtest.h>\n',
         '// get_entry_count (los PRIMARIOS) no dependen de eso y prueban el cierre por si solos.\n#include <sstream>\n#include <gtest/gtest.h>\n'),
        ('constexpr const char* kEvilSet   = "argus_h2_evil";\n\n',
         'constexpr const char* kEvilSet   = "argus_h2_evil";\n// [PROTEGIDOS-MANIFIESTO-D318] "<ip>\\nadd <kEvilSet> <otra>" con ostringstream y no con una cadena de operator+ sobre\n// temporales: con -O3 -flto -march=skylake, GCC 12.2 daba un falso -Werror=stringop-overflow (37 bytes en el búfer\n// corto de 16 de std::string) al cambiar el reparto LTO al enlazar libs/protegidos. Mismos bytes que antes.\nstd::string inyeccion(const char* ip, const char* otra) {\n    std::ostringstream o;\n    o << ip << "\\nadd " << kEvilSet << " " << otra;\n    return o.str();\n}\n\n'),
        ('    // [H-2 DAY188 IPSetEntry ctor fix] IPSetEntry exige IP en el ctor (no default-construct).\n    IPSetEntry evil{std::string("1.2.3.4/24\\nadd ") + kEvilSet + " 6.6.6.6"};\n\n',
         '    // [H-2 DAY188 IPSetEntry ctor fix] IPSetEntry exige IP en el ctor (no default-construct).\n    IPSetEntry evil{inyeccion("1.2.3.4/24", "6.6.6.6")};\n\n'),
        ('    std::vector<std::string> ips = {\n        std::string("9.9.9.9/24\\nadd ") + kEvilSet + " 7.7.7.7"\n    };\n',
         '    std::vector<std::string> ips = {\n        inyeccion("9.9.9.9/24", "7.7.7.7")\n    };\n'),
    ],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    nombre = os.path.basename(sys.argv[0])
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print(f"uso: {nombre} --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores, hechos, pendientes = [], [], []
    crear, borrar = {}, []
    for rel, esperado, contenido in NUEVOS:
        b = contenido.encode("utf-8")
        if sha(b) != esperado:
            errores.append(f"{rel}: el contenido embebido no da su sha256 (parcheador dañado)")
            continue
        p = os.path.join(raiz, rel)
        if os.path.exists(p):
            a = sha(open(p, "rb").read())
            if a == esperado:
                hechos.append(f"{rel}: creado")
            else:
                errores.append(f"{rel}: ya existe con otro contenido (sha256 {a})")
        else:
            pendientes.append(f"{rel}: crear")
            crear[rel] = b
    for rel, esperado in BORRADOS:
        p = os.path.join(raiz, rel)
        if not os.path.exists(p):
            hechos.append(f"{rel}: borrado")
            continue
        a = sha(open(p, "rb").read())
        print(f"sha256 previo  {rel}: {a}")
        if a == esperado:
            pendientes.append(f"{rel}: borrar")
            borrar.append(rel)
        else:
            errores.append(f"{rel}: sha256 {a}, no el esperado para borrarlo")
    orig, nuevo = {}, {}
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for n, (viejo, nv) in enumerate(cambios, 1):
            cv, cn = t.count(viejo), (t.count(nv) if nv else 0)
            if nv and viejo in nv:
                aplicar, hecho = cv == 1 and cn == 0, cn == 1
            elif nv in viejo:
                aplicar, hecho = cv == 1, cv == 0 and (not nv or cn >= 1)
            else:
                aplicar, hecho = cv == 1 and cn == 0, cv == 0 and cn == 1
            if aplicar:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: cambio {n}")
            elif hecho:
                hechos.append(f"{rel}: cambio {n}")
            else:
                errores.append(f"{rel}: cambio {n}: texto viejo {cv} veces, nuevo {cn} veces")
        nuevo[rel] = t.encode("utf-8")
    print(f"ya aplicados ({len(hechos)})")
    for h in hechos:
        print(f"  = {h}")
    print(f"por aplicar  ({len(pendientes)})")
    for h in pendientes:
        print(f"  + {h}")
    if errores:
        for e in errores:
            print(f"FALLA: {e}")
        print("RESULTADO: FALLA (no se ha escrito nada)")
        return 1
    if modo == "--apply":
        for rel, b in crear.items():
            p = os.path.join(raiz, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p + ".d318tmp", "wb") as f:
                f.write(b)
            os.chmod(p + ".d318tmp", 0o644)
            os.replace(p + ".d318tmp", p)
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                p = os.path.join(raiz, rel)
                m = os.stat(p).st_mode
                with open(p + ".d318tmp", "wb") as f:
                    f.write(nuevo[rel])
                os.chmod(p + ".d318tmp", m)
                os.replace(p + ".d318tmp", p)
        for rel in borrar:
            os.remove(os.path.join(raiz, rel))
    for rel, esperado, _ in NUEVOS:
        print(f"sha256 nuevo   {rel}: {esperado}")
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
