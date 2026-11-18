#!/usr/bin/env python3
"""DAY330 [GRUB-DISCO-D330] DEBT-LAB-GRUB-INSTALL-DEVICES-001 (decisión de Alonso DAY330: su propio PR, antes del de Zeek).

Nuevos: scripts/emecas/grub_disco.sh (el disco de /boot como lo elige el postinst de grub-pc) y su test
scripts/emecas/test_grub_disco.sh. Vagrantfile: debian-fecha fija grub-pc/install_devices en debconf antes del
full-upgrade y comprueba después grub-pc configurado y el valor. Makefile: el test en test-kernel-homogeneo (ya en EMECAS).

Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d330_grub_disco.py [--apply]
Sin --apply solo comprueba. Con --apply escribe, y solo si TODO cuadra: sha256 de partida de cada fichero que modifica,
cada ancla exactamente las veces esperadas y ningún fichero nuevo ya existente. Si algo falla no escribe nada.
"""
import hashlib, os, sys

NUEVOS = {'scripts/emecas/grub_disco.sh': ('#!/usr/bin/env bash\n# scripts/emecas/grub_disco.sh — [GRUB-DISCO-D330] DEBT-LAB-GRUB-INSTALL-DEVICES-001: el disco donde grub-pc tiene que\n# instalarse, sacado de la propia VM (nunca escrito a mano). Lo usa el aprovisionador debian-fecha del Vagrantfile para\n# fijar grub-pc/install_devices en debconf ANTES del full-upgrade.\n# Por qué (medido DAY330): la caja debian/bookworm64 12.20240905.1 trae grub-pc/install_devices SIN valor. Con la lista\n# vacía, el postinst de grub-pc (2.06-13+deb12u2) pregunta, no puede preguntar (noninteractive) y para con "You must\n# correct your GRUB install devices": cayó así el defender en el EMECAS de DAY330, mientras que en el de DAY329, con la\n# misma caja, la misma fecha y el mismo paquete, las 8 VMs tenían un disco y grub-install fue bien en /dev/sda. De dónde\n# salió ese valor el DAY329 no está medido (ni grub-pc.config ni el postinst lo rellenan); sea cual sea, ya no se depende\n# de él.\n# Salida: el enlace de /dev/disk/by-id del disco de /boot, elegido como lo hace el propio postinst (device_to_id sobre\n# available_ids: los enlaces en orden, uno por destino), o el dispositivo tal cual si no tiene enlace. rc 1 si no hay\n# disco. La función grub_id_de_disco no toca el sistema (la prueba scripts/emecas/test_grub_disco.sh en el Mac).\nset -u\nLC_ALL=C; export LC_ALL\n\n# grub_id_de_disco DISCO_REAL < líneas "enlace destino_real" (en el orden del glob de /dev/disk/by-id)\ngrub_id_de_disco() {\n  local real=$1 id dest\n  [ -n "$real" ] || return 1\n  while read -r id dest; do\n    [ "$dest" = "$real" ] && { printf \'%s\\n\' "$id"; return 0; }\n  done < <(sort -k2 -s -u)\n  printf \'%s\\n\' "$real"\n}\n\nmain() {\n  local disco real p\n  disco=$(grub-probe -t disk /boot 2>/dev/null) || { echo "grub-probe -t disk /boot falla" >&2; return 1; }\n  real=$(readlink -f "$disco")\n  [ -b "$real" ] || { echo "grub-probe da \'$disco\', que no es un dispositivo de bloques" >&2; return 1; }\n  for p in /dev/disk/by-id/*; do\n    [ -e "$p" ] && printf \'%s %s\\n\' "$p" "$(readlink -f "$p")"\n  done | grub_id_de_disco "$real"\n}\n\nif [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi\n', 420), 'scripts/emecas/test_grub_disco.sh': ('#!/usr/bin/env bash\n# scripts/emecas/test_grub_disco.sh — [GRUB-DISCO-D330] tests de grub_id_de_disco (Mac, sin VMs). Los casos de valor\n# se vuelven a correr contra una versión que devuelve siempre el dispositivo tal cual (la que no traduce a by-id): tienen\n# que fallar ahí, para ver que el test distingue.\nset -u\nLC_ALL=C; export LC_ALL\n. "$(dirname "$0")/grub_disco.sh"\n\nDIA330=$\'/dev/disk/by-id/ata-VBOX_HARDDISK_VB981eec03-849363ff /dev/sda\\n/dev/disk/by-id/ata-VBOX_HARDDISK_VB981eec03-849363ff-part1 /dev/sda1\'\ncasos=0; fallos=0; traducen=0; traducen_vistos=0\n\nes() { local n=$1 esperado=$2 real=$3 entrada=$4 got\n  casos=$((casos + 1)); got=$(printf \'%s\\n\' "$entrada" | grub_id_de_disco "$real")\n  if [ "$got" = "$esperado" ]; then echo "✅ $n"; else echo "❌ $n: \'$got\', se esperaba \'$esperado\'"; fallos=$((fallos + 1)); fi; }\ntraduce() { traducen=$((traducen + 1)); local f=$fallos; es "$@"; [ "$fallos" = "$f" ] || traducen_vistos=$((traducen_vistos + 1)); }\nfalla() { local n=$1 real=$2 entrada=$3; casos=$((casos + 1))\n  if printf \'%s\\n\' "$entrada" | grub_id_de_disco "$real" >/dev/null; then echo "❌ $n"; fallos=$((fallos + 1)); else echo "✅ $n"; fi; }\n\nlos_casos() {\n  traduce "el disco medido DAY330 en el defender -> su by-id" /dev/disk/by-id/ata-VBOX_HARDDISK_VB981eec03-849363ff /dev/sda "$DIA330"\n  traduce "nunca la partición" /dev/disk/by-id/ata-X /dev/sda $\'/dev/disk/by-id/ata-X-part1 /dev/sda1\\n/dev/disk/by-id/ata-X /dev/sda\'\n  traduce "dos enlaces al mismo disco: el primero, como el postinst" /dev/disk/by-id/ata-A /dev/sda $\'/dev/disk/by-id/ata-A /dev/sda\\n/dev/disk/by-id/wwn-0x1 /dev/sda\'\n  traduce "dos discos: el de /boot" /dev/disk/by-id/ata-B /dev/sdb $\'/dev/disk/by-id/ata-A /dev/sda\\n/dev/disk/by-id/ata-B /dev/sdb\'\n  es "sin enlace by-id: el dispositivo tal cual" /dev/sda /dev/sda ""\n  es "enlaces de otros discos solamente: el dispositivo tal cual" /dev/vda /dev/vda "$DIA330"\n  falla "disco vacío -> rc 1" "" "$DIA330"\n}\n\nlos_casos\necho "$((casos - fallos))/$casos casos"\ntotal=$fallos\n\ngrub_id_de_disco() { cat >/dev/null; [ -n "$1" ] || return 1; printf \'%s\\n\' "$1"; }\nesperados=$traducen; casos=0; fallos=0; traducen=0; traducen_vistos=0\nlos_casos > /dev/null\nif [ "$traducen_vistos" = "$esperados" ]; then\n  echo "✅ contra una versión que no traduce a by-id fallan los $esperados casos que traducen"\nelse\n  echo "❌ contra una versión que no traduce a by-id fallan $traducen_vistos de los $esperados casos que traducen"; total=$((total + 1))\nfi\n[ "$total" = 0 ]\n', 420)}

MODIFICA = {'Vagrantfile': ('d6202d320b009632af1a52bad384e7b4c0a9a3ee450dac870d292e10e0e961b4', [('      echo "❌ debian-fecha: fuentes de Debian sin fijar a $TS: $OTRAS"; exit 1\n    fi\n    apt-get update -o Acquire::Retries=3\n', '      echo "❌ debian-fecha: fuentes de Debian sin fijar a $TS: $OTRAS"; exit 1\n    fi\n    # [GRUB-DISCO-D330] DEBT-LAB-GRUB-INSTALL-DEVICES-001: la caja trae grub-pc/install_devices sin valor y, sin disco y en\n    # noninteractive, el postinst de grub-pc para el full-upgrade (medido DAY330 en el defender; el DAY329 pasó en las 8\n    # VMs sin saber por qué). Se fija aquí al disco de /boot, sacado de la VM (scripts/emecas/grub_disco.sh), y se\n    # comprueba tras el full-upgrade. También si grub-pc quedó a medio configurar de una corrida anterior.\n    GD=\n    case "$(dpkg-query -W -f=\'${Status}\' grub-pc 2>/dev/null || true)" in\n      ""|*" not-installed"|*" config-files") echo "debian-fecha: sin grub-pc, nada que fijar" ;;\n      *)\n        GD=$(bash /vagrant/scripts/emecas/grub_disco.sh) || { echo "❌ debian-fecha: no se sabe en qué disco va grub-pc"; exit 1; }\n        echo "grub-pc grub-pc/install_devices multiselect $GD" | debconf-set-selections\n        echo "debian-fecha: grub-pc/install_devices=$GD (el disco de /boot)"\n        ;;\n    esac\n    apt-get update -o Acquire::Retries=3\n', 1), ('      echo "❌ debian-fecha: apt sigue viendo Debian fuera de $TS (líneas de arriba)"; exit 1\n    fi\n', '      echo "❌ debian-fecha: apt sigue viendo Debian fuera de $TS (líneas de arriba)"; exit 1\n    fi\n    if [ -n "$GD" ]; then\n      GS=$(dpkg-query -W -f=\'${Status}\' grub-pc)\n      GV=$(debconf-show grub-pc | sed -n \'s/^[* ] grub-pc\\/install_devices: //p\')\n      if [ "$GS" != "install ok installed" ] || [ "$GV" != "$GD" ]; then\n        echo "❌ debian-fecha: grub-pc \'$GS\', install_devices \'$GV\' (se fijó \'$GD\')"; exit 1\n      fi\n    fi\n', 1), ('    echo "✅ debian-fecha: Debian en $TS; kernel de la fecha $K (en marcha: $(uname -r); arranca tras reiniciar)"\n', '    echo "✅ debian-fecha: Debian en $TS; kernel de la fecha $K (en marcha: $(uname -r); arranca tras reiniciar); grub-pc en ${GD:-ninguno}"\n', 1)]), 'Makefile': ('34cf9516f64b5be9be67bb6ee9635a090030de7d328d011c5e5b74b37bd0b3ed', [('\t@bash scripts/emecas/test_kernel_homogeneo.sh\n', '\t@bash scripts/emecas/test_kernel_homogeneo.sh\n\t@bash scripts/emecas/test_grub_disco.sh\n', 1)])}

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
