#!/usr/bin/env bash
# scripts/emecas/grub_disco.sh — [GRUB-DISCO-D330] DEBT-LAB-GRUB-INSTALL-DEVICES-001: el disco donde grub-pc tiene que
# instalarse, sacado de la propia VM (nunca escrito a mano). Lo usa el aprovisionador debian-fecha del Vagrantfile para
# fijar grub-pc/install_devices en debconf ANTES del full-upgrade.
# Por qué (medido DAY330): la caja debian/bookworm64 12.20240905.1 trae grub-pc/install_devices SIN valor. Con la lista
# vacía, el postinst de grub-pc (2.06-13+deb12u2) pregunta, no puede preguntar (noninteractive) y para con "You must
# correct your GRUB install devices": cayó así el defender en el EMECAS de DAY330, mientras que en el de DAY329, con la
# misma caja, la misma fecha y el mismo paquete, las 8 VMs tenían un disco y grub-install fue bien en /dev/sda. De dónde
# salió ese valor el DAY329 no está medido (ni grub-pc.config ni el postinst lo rellenan); sea cual sea, ya no se depende
# de él.
# Salida: el enlace de /dev/disk/by-id del disco de /boot, elegido como lo hace el propio postinst (device_to_id sobre
# available_ids: los enlaces en orden, uno por destino), o el dispositivo tal cual si no tiene enlace. rc 1 si no hay
# disco. La función grub_id_de_disco no toca el sistema (la prueba scripts/emecas/test_grub_disco.sh en el Mac).
set -u
LC_ALL=C; export LC_ALL

# grub_id_de_disco DISCO_REAL < líneas "enlace destino_real" (en el orden del glob de /dev/disk/by-id)
grub_id_de_disco() {
  local real=$1 id dest
  [ -n "$real" ] || return 1
  while read -r id dest; do
    [ "$dest" = "$real" ] && { printf '%s\n' "$id"; return 0; }
  done < <(sort -k2 -s -u)
  printf '%s\n' "$real"
}

main() {
  local disco real p
  disco=$(grub-probe -t disk /boot 2>/dev/null) || { echo "grub-probe -t disk /boot falla" >&2; return 1; }
  real=$(readlink -f "$disco")
  [ -b "$real" ] || { echo "grub-probe da '$disco', que no es un dispositivo de bloques" >&2; return 1; }
  for p in /dev/disk/by-id/*; do
    [ -e "$p" ] && printf '%s %s\n' "$p" "$(readlink -f "$p")"
  done | grub_id_de_disco "$real"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
