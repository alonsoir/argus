#!/bin/bash
# [KERNEL-HOMOGENEO-D329] (dentro de cada VM; lo envía kernel_homogeneo.sh por stdin) tres líneas clave=valor:
#   uname         kernel en marcha
#   fecha         marca de snapshot.debian.org de bookworm-security en /etc/apt/sources.list (vacía si no hay)
#   kernel_fecha  kernel que pide linux-image-amd64 instalado (el de la fecha tras debian-fecha)
set -u
echo "uname=$(uname -r)"
echo "fecha=$(sed -n 's#^deb .*snapshot\.debian\.org/archive/debian-security/\([0-9]\{8\}T[0-9]\{6\}Z\)/ bookworm-security .*#\1#p' /etc/apt/sources.list 2>/dev/null | head -n 1)"
echo "kernel_fecha=$(dpkg-query -W -f='${Depends}' linux-image-amd64 2>/dev/null | sed -n 's/.*linux-image-\([0-9][^ ,]*\).*/\1/p' | head -n 1)"
