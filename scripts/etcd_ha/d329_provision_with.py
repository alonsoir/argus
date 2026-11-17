#!/usr/bin/env python3
"""DAY329 [PROVISION-WITH-D329] apt-espera y debian-fecha declarados con nombre (config.vm.provision "<nombre>",
type: "shell"): el EMECAS de las 08:26 cayó en vagrant-up a los 3 s con "'apt-espera' is not a known provisioner",
porque el name: de un aprovisionador shell es solo su etiqueta. Test estático (scripts/emecas/test_provision_with.sh,
en make test-kernel-homogeneo): todo nombre pedido con --provision-with en el Makefile está declarado con nombre.

Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d329_provision_with.py [--apply]
Sin --apply solo comprueba. Con --apply escribe, y solo si TODO cuadra: sha256 de partida de cada fichero que modifica,
cada ancla exactamente las veces esperadas y ningún fichero nuevo ya existente. Si algo falla no escribe nada.
"""
import hashlib, os, sys

NUEVOS = {'scripts/emecas/test_provision_with.sh': ('#!/bin/bash\n# [PROVISION-WITH-D329] (Mac, raíz del repo) cada aprovisionador que el Makefile pide por nombre con --provision-with\n# tiene que estar declarado CON nombre en el Vagrantfile: config.vm.provision "<nombre>", type: "shell", ... El\n# name: de un aprovisionador shell es solo la etiqueta que se muestra, no su nombre: con él, vagrant up\n# --provision-with responde "\'<nombre>\' is not a known provisioner" (medido DAY329: EMECAS caído en vagrant-up a los 3 s).\nset -u\n[ -f Makefile ] && [ -f Vagrantfile ] || { echo "❌ ejecutar desde la raíz del repo"; exit 1; }\nnombres=$(grep -v \'^[[:space:]]*@\\?#\' Makefile | grep -o -- \'--provision-with [a-z0-9,_-]*\' | sed \'s/--provision-with //\' | tr \',\' \'\\n\' | sort -u)\n[ -n "$nombres" ] || { echo "❌ el Makefile no pide ningún aprovisionador por nombre (¿se ha movido el paso vagrant-up?)"; exit 1; }\nfallos=0; n=0\nfor p in $nombres; do\n  n=$((n + 1))\n  if grep -qE "\\.vm\\.provision \\"$p\\", type: \\"" Vagrantfile; then\n    echo "✅ $p: declarado con nombre en el Vagrantfile"\n  else\n    echo "❌ $p: el Makefile lo pide con --provision-with y el Vagrantfile no lo declara con nombre (\\"$p\\", type: \\"shell\\")"\n    fallos=$((fallos + 1))\n  fi\ndone\necho "$((n - fallos))/$n aprovisionadores"\n[ "$fallos" -eq 0 ]\n', 493)}

MODIFICA = {'Vagrantfile': ('154c92c0afd296b3c50c0e5d8a94013136730770b03753bcacbe3143d1d10643', [('  config.vm.provision "shell", name: "apt-espera", run: "always", inline:', '  # [PROVISION-WITH-D329] con nombre ("apt-espera", type: "shell"): EMECAS lo pide con --provision-with; el name: de\n  # shell solo es la etiqueta que se muestra (medido DAY329: "\'apt-espera\' is not a known provisioner")\n  config.vm.provision "apt-espera", type: "shell", name: "apt-espera", run: "always", inline:', 1), ('  config.vm.provision "shell", name: "debian-fecha", run: "always", args:', '  config.vm.provision "debian-fecha", type: "shell", name: "debian-fecha", run: "always", args:', 1)]), 'Makefile': ('768a65bd20e5ae6ac929b9b55818a6bdf29c0687807af259b3371b4e7a8782f3', [('\t@python3 -I scripts/emecas/test_con_limite.py\n', '\t@python3 -I scripts/emecas/test_con_limite.py\n\t@bash scripts/emecas/test_provision_with.sh\n', 1)])}

def main():
    aplicar = "--apply" in sys.argv[1:]
    if not os.path.isfile("Vagrantfile") or not os.path.isfile("Makefile"):
        sys.exit("❌ ejecutar desde la raíz del repo")
    errores, resultado = [], {}
    for ruta in NUEVOS:
        if os.path.exists(ruta):
            errores.append("ya existe " + ruta)
    for ruta, (sha_partida, cambios) in MODIFICA.items():
        datos = open(ruta, "rb").read()
        h = hashlib.sha256(datos).hexdigest()
        if h != sha_partida:
            errores.append("%s: sha256 de partida %s, esperado %s" % (ruta, h, sha_partida))
            continue
        texto = datos.decode("utf-8")
        for viejo, nuevo, veces in cambios:
            n = texto.count(viejo)
            if n != veces:
                errores.append("%s: ancla %d veces, esperadas %d: %r" % (ruta, n, veces, viejo[:90]))
            else:
                texto = texto.replace(viejo, nuevo)
        resultado[ruta] = texto
    if errores:
        print("❌ no se escribe nada:")
        for e in errores:
            print("   - " + e)
        sys.exit(1)
    if not aplicar:
        print("✅ todo cuadra (sin --apply no se escribe nada): %d nuevos, %d modificados" % (len(NUEVOS), len(resultado)))
        return
    for ruta, (contenido, modo) in NUEVOS.items():
        os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(contenido)
        os.chmod(ruta, modo)
        print("  + %s  sha256=%s" % (ruta, hashlib.sha256(contenido.encode()).hexdigest()))
    for ruta, texto in resultado.items():
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        print("  ~ %s  sha256=%s" % (ruta, hashlib.sha256(texto.encode()).hexdigest()))
    print("✅ aplicado")

if __name__ == "__main__":
    main()
