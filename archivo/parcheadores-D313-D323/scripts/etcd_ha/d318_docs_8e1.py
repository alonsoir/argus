#!/usr/bin/env python3
# d318_docs_8e1.py — DAY318, docs de los pasos 8e.1a y 8e.1b (ADR-060) [PROTEGIDOS-MANIFIESTO-D318]: el plan partido en
# 8e.1a y 8e.1b con sus commits, set_name de 1 a 29, los mensajes de log implementados, el límite del anti-rollback
# entre reinicios (8e.3), el hallazgo de libsodium en DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 y la sección de BACKLOG
# con lo medido en el banco y en el lab.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_docs_8e1.py --check|--apply <raíz>
# Todo o nada e idempotente; imprime el sha256 de cada fichero antes y después.
import hashlib
import os
import sys

ADR = "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md"
BL = "docs/BACKLOG.md"
CAMBIOS = {
    ADR: [
        ("plan 8e.1 partido en 8e.1a y 8e.1b",
         "- **8e.1** firewall-acl-agent: categoría `infraestructura`, manifiesto por hospital con sus plantas, carga desde la\n"
         "  caché y verificación (Ed25519 con libsodium, clave pública compilada en dos ranuras), versión monótona, límites de\n"
         "  prefijo, set `hash:net,iface` aplicado de forma atómica con `ipset swap`, candado (D6), último verificado y avisos\n"
         "  periódicos (D7), aviso si falta el plano de control, contadores por categoría. Fuera `ddos_protegidos`,\n"
         "  `ipsets.whitelist` y el defecto RFC 1918. Tests.\n",
         "- **8e.1** firewall-acl-agent, en dos commits (DAY318):\n"
         "  - **8e.1a** (hecho, 3af32373c) el verificador, sin cambiar el comportamiento del agente: categoría\n"
         "    `infraestructura`, manifiesto por hospital con sus plantas, verificación Ed25519 con libsodium y clave pública\n"
         "    compilada en dos ranuras, versión monótona, límites de prefijo, lo vigente seguro entre hilos (D7), caché en\n"
         "    disco, aviso si falta el plano de control (D-C). Tests.\n"
         "  - **8e.1b** (hecho, f9076a97c) el cableado: carga desde la caché al arrancar, set `hash:net,iface` sustituido de\n"
         "    forma atómica con `ipset swap` y regla `src,src`, candado (D6), barrera por IP con los rangos del vigente,\n"
         "    avisos periódicos (D6, D7, D-C), contadores por categoría. Fuera `ddos_protegidos`, `ipsets.whitelist` y el\n"
         "    defecto RFC 1918. Tests.\n"),
        ("set_name de 1 a 29",
         "| `protegidos.set_name` | lo que acepta `is_valid_set_name` (1 a 31, `[A-Za-z0-9_-]`) | `ml_defender_protegidos` | set `hash:net,iface` del kernel |\n",
         "| `protegidos.set_name` | `[A-Za-z0-9_-]`, de 1 a 29 (el temporal `<set>_n` del swap añade dos y tiene que caber en los 31 de `is_valid_set_name`) | `ml_defender_protegidos` | set `hash:net,iface` del kernel |\n"),
        ("mensajes de log implementados",
         "- `protegidos:` gana `infraestructura=N`.\n",
         "- `protegidos:` gana `infraestructura=N`.\n"
         "\n"
         "Implementados en 8e.1b, además: `[PROTEGIDOS-CLAVE]` (huellas de las dos ranuras compiladas: los 16 primeros hex\n"
         "del sha256 de la clave, no los de la clave), `[PROTEGIDOS-SET]`, `[PROTEGIDOS-KERNEL]` (entradas llevadas al set;\n"
         "las IPv6 solo en la barrera) y `[PROTEGIDOS-CACHE]` (la caché no se lee o ya no verifica: se conserva lo que hay en\n"
         "memoria). `[INFRA-CAMBIO]` llega con 8e.3, cuando el manifiesto cambia en caliente.\n"),
        ("anti-rollback entre reinicios",
         "(`consulta_sec`) va en 8e.3, con sus rutas.\n",
         "(`consulta_sec`) va en 8e.3, con sus rutas.\n"
         "\n"
         "**Límite de 8e.1 (medido DAY318).** La versión monótona protege mientras el agente está vivo: al arrancar no hay\n"
         "versión aplicada y se acepta cualquier manifiesto bien firmado de la caché, también uno más viejo. La caché solo la\n"
         "escribe root (O_NOFOLLOW, temporal y rename), pero el anti-rollback entre reinicios (la versión más alta vista,\n"
         "guardada aparte, o pedida al etcd-server antes de aplicar) se cierra en 8e.3.\n"),
    ],
    BL: [
        ("libsodium en el lab",
         "**Estimación:** 0.5 sesión (investigación).\n"
         "\n"
         "### DEBT-SEMGREP-CPP-HANG-001",
         "**Estimación:** 0.5 sesión (investigación).\n"
         "**Medido DAY318 (8e.1a, el firewall enlaza libsodium):** en el defender conviven la 1.0.18 de Debian\n"
         "(`libsodium23`) y la 1.0.19 compilada desde el código fuente en `/usr/local/lib`. La buena solo carga porque el FIX\n"
         "DAY107 de `tools/provision.sh` enlaza `/usr/local/lib/libsodium.so.23 -> .so.26` y porque las unidades systemd,\n"
         "`firewall-start`, `test-firewall` y el perfil del Vagrantfile ponen `LD_LIBRARY_PATH=/usr/local/lib`. Funciona,\n"
         "pero es frágil: un binario lanzado sin esa variable carga la 1.0.18. Hay que hacerlo bien (rpath o una sola\n"
         "versión instalada); lo ideal, que la 1.0.19 llegue con Debian (Alonso DAY318). El banco reproduce ya el enlace y la\n"
         "variable.\n"
         "\n"
         "### DEBT-SEMGREP-CPP-HANG-001"),
        ("8e.1a y 8e.1b hechos",
         "la ley de cada hospital.\n",
         "la ley de cada hospital.\n"
         "\n"
         "---\n"
         "\n"
         "## DAY318 — pasos 8e.1a y 8e.1b hechos [PROTEGIDOS-MANIFIESTO-D318]\n"
         "\n"
         "Commits: 3af32373c (8e.1a, el verificador, sin cambiar el comportamiento del agente) y f9076a97c (8e.1b, el\n"
         "cableado). Diseño: ADR-060, secciones 5 y 6.\n"
         "\n"
         "### Medido en el banco (Debian 12, GCC 12.2.0, opciones de production, dos pasadas)\n"
         "- 8e.1a y 8e.1b: 117/117 tests en cada pasada, los mismos que el control.\n"
         "- Mutaciones del verificador (8e.1a): todas detectadas, después de exigir `!ok` en cada rechazo (`rech()`) y de\n"
         "  añadir la caché con la misma versión y otro contenido.\n"
         "- Mutaciones del cableado (8e.1b), las 8 detectadas: candado siempre abierto, candado que ignora el nulo, rangos que\n"
         "  no se renuevan, sin `swap`, entradas malas aceptadas, temporal sin borrar, regla `src` en vez de `src,src`, tipo\n"
         "  del set mal leído. `test_argus_cadena_root` corre contra el kernel de verdad.\n"
         "\n"
         "### Medido en el lab (PROFILE=production)\n"
         "- `pipeline-build` rc 0. `test-firewall`: 94/94 (2 de rendimiento saltados, como antes). `test-firewall-e2e`: 23/23,\n"
         "  0 saltados en el gate; `test_argus_cadena_root` 58/58.\n"
         "- La huella compilada (52ba6180cf5e8e9a) es la del sha256 de `protegidos_pubkey_actual.hex`: la misma clave que\n"
         "  trajo `make protegidos-pubkey` de `protegidos-hospital-lab`.\n"
         "- Arranque: cinco `[CONFIG] protegidos.*` del JSON y ningún `ddos_protegidos`; `[PROTEGIDOS-SIN-MANIFIESTO]` (no hay\n"
         "  caché hasta 8e.3); regla `ml_defender_protegidos src,src RETURN`; rangos `NINGUNO`; resumen con\n"
         "  `infraestructura=0 manifiesto=ninguno`.\n"
         "\n"
         "### Hallazgos DAY318 (8e.1)\n"
         "- En `dry_run` el agente no crea ningún set: la whitelist vieja no ha existido nunca en el kernel del defender del\n"
         "  lab (medido: ningún set ni regla de aRGus). Los sets solo los crean los E2E que ponen `dry_run=false`.\n"
         "- La llamada al candado dentro de `zmq_subscriber` no tiene test unitario (el suscriptor no tiene ninguno); la\n"
         "  función `candado_cerrado` sí. La cubre el E2E de 8e.5.\n"
         "- libsodium del lab: ver DEBT-LIBSODIUM-SO-VERSION-CONFLICT-001 (medido DAY318).\n"
         "- `firewall-acl-agent/config/rules/` (`blacklist.json` y `whitelist.json`, vacíos) tampoco se usa; va con\n"
         "  `src/rules` en DEBT-REPO-RESIDUOS-001.\n"
         "\n"
         "### Pendiente\n"
         "- `lab-e2e-mitigacion` y `lab-e2e-protegidos` fallan hasta 8e.5: sin manifiesto el candado para la mitigación, y\n"
         "  `d303_veredicto_protegidos.sh` busca líneas de log que ya no existen (se reescribe en 8e.5 con P1–P6).\n"
         "- 8e.3: anti-rollback entre reinicios (ADR-060, sección 6), `[INFRA-CAMBIO]`, `consulta_sec`.\n"),
    ],
}
REESCRITOS = []



def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d318_docs_8e1.py --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores, hechos, pendientes = [], [], []
    escribir = {}
    for rel, viejo, esperado, contenido in REESCRITOS:
        b = contenido.encode("utf-8")
        if sha(b) != esperado:
            errores.append(f"{rel}: el contenido embebido no da su sha256 (parcheador dañado)")
            continue
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        actual = sha(open(p, "rb").read())
        print(f"sha256 previo  {rel}: {actual}")
        if actual == esperado:
            hechos.append(f"{rel}: reescrito")
        elif actual == viejo:
            pendientes.append(f"{rel}: reescribir")
            escribir[rel] = b
        else:
            errores.append(f"{rel}: sha256 {actual}, ni el viejo esperado ni el nuevo")
    orig, nuevo = {}, {}
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for nombre, viejo, nv in cambios:
            cv, cn = t.count(viejo), (t.count(nv) if nv else 0)
            if nv and viejo in nv:      # inserción: el texto viejo sigue dentro del nuevo
                aplicar, hecho = cv == 1 and cn == 0, cn == 1
            elif nv in viejo:           # borrado o recorte: el nuevo cabe dentro del viejo
                aplicar, hecho = cv == 1, cv == 0 and (not nv or cn >= 1)
            else:
                aplicar, hecho = cv == 1 and cn == 0, cv == 0 and cn == 1
            if aplicar:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: {nombre}")
            elif hecho:
                hechos.append(f"{rel}: {nombre}")
            else:
                errores.append(f"{rel}: {nombre}: texto viejo {cv} veces, nuevo {cn} veces")
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
        todo = dict(escribir)
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                todo[rel] = nuevo[rel]
        for rel, b in todo.items():
            p = os.path.join(raiz, rel)
            m = os.stat(p).st_mode
            with open(p + ".d318tmp", "wb") as f:
                f.write(b)
            os.chmod(p + ".d318tmp", m)
            os.replace(p + ".d318tmp", p)
    for rel, _, esperado, _ in REESCRITOS:
        print(f"sha256 final   {rel}: {esperado}")
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
