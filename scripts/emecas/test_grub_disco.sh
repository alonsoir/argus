#!/usr/bin/env bash
# scripts/emecas/test_grub_disco.sh — [GRUB-DISCO-D330] tests de grub_id_de_disco (Mac, sin VMs). Los casos de valor
# se vuelven a correr contra una versión que devuelve siempre el dispositivo tal cual (la que no traduce a by-id): tienen
# que fallar ahí, para ver que el test distingue.
set -u
LC_ALL=C; export LC_ALL
. "$(dirname "$0")/grub_disco.sh"

DIA330=$'/dev/disk/by-id/ata-VBOX_HARDDISK_VB981eec03-849363ff /dev/sda\n/dev/disk/by-id/ata-VBOX_HARDDISK_VB981eec03-849363ff-part1 /dev/sda1'
casos=0; fallos=0; traducen=0; traducen_vistos=0

es() { local n=$1 esperado=$2 real=$3 entrada=$4 got
  casos=$((casos + 1)); got=$(printf '%s\n' "$entrada" | grub_id_de_disco "$real")
  if [ "$got" = "$esperado" ]; then echo "✅ $n"; else echo "❌ $n: '$got', se esperaba '$esperado'"; fallos=$((fallos + 1)); fi; }
traduce() { traducen=$((traducen + 1)); local f=$fallos; es "$@"; [ "$fallos" = "$f" ] || traducen_vistos=$((traducen_vistos + 1)); }
falla() { local n=$1 real=$2 entrada=$3; casos=$((casos + 1))
  if printf '%s\n' "$entrada" | grub_id_de_disco "$real" >/dev/null; then echo "❌ $n"; fallos=$((fallos + 1)); else echo "✅ $n"; fi; }

los_casos() {
  traduce "el disco medido DAY330 en el defender -> su by-id" /dev/disk/by-id/ata-VBOX_HARDDISK_VB981eec03-849363ff /dev/sda "$DIA330"
  traduce "nunca la partición" /dev/disk/by-id/ata-X /dev/sda $'/dev/disk/by-id/ata-X-part1 /dev/sda1\n/dev/disk/by-id/ata-X /dev/sda'
  traduce "dos enlaces al mismo disco: el primero, como el postinst" /dev/disk/by-id/ata-A /dev/sda $'/dev/disk/by-id/ata-A /dev/sda\n/dev/disk/by-id/wwn-0x1 /dev/sda'
  traduce "dos discos: el de /boot" /dev/disk/by-id/ata-B /dev/sdb $'/dev/disk/by-id/ata-A /dev/sda\n/dev/disk/by-id/ata-B /dev/sdb'
  es "sin enlace by-id: el dispositivo tal cual" /dev/sda /dev/sda ""
  es "enlaces de otros discos solamente: el dispositivo tal cual" /dev/vda /dev/vda "$DIA330"
  falla "disco vacío -> rc 1" "" "$DIA330"
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

grub_id_de_disco() { cat >/dev/null; [ -n "$1" ] || return 1; printf '%s\n' "$1"; }
esperados=$traducen; casos=0; fallos=0; traducen=0; traducen_vistos=0
los_casos > /dev/null
if [ "$traducen_vistos" = "$esperados" ]; then
  echo "✅ contra una versión que no traduce a by-id fallan los $esperados casos que traducen"
else
  echo "❌ contra una versión que no traduce a by-id fallan $traducen_vistos de los $esperados casos que traducen"; total=$((total + 1))
fi
[ "$total" = 0 ]
