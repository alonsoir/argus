#!/bin/bash
# [PROVISION-WITH-D329] (Mac, raíz del repo) cada aprovisionador que el Makefile pide por nombre con --provision-with
# tiene que estar declarado CON nombre en el Vagrantfile: config.vm.provision "<nombre>", type: "shell", ... El
# name: de un aprovisionador shell es solo la etiqueta que se muestra, no su nombre: con él, vagrant up
# --provision-with responde "'<nombre>' is not a known provisioner" (medido DAY329: EMECAS caído en vagrant-up a los 3 s).
set -u
[ -f Makefile ] && [ -f Vagrantfile ] || { echo "❌ ejecutar desde la raíz del repo"; exit 1; }
nombres=$(grep -v '^[[:space:]]*@\?#' Makefile | grep -o -- '--provision-with [a-z0-9,_-]*' | sed 's/--provision-with //' | tr ',' '\n' | sort -u)
[ -n "$nombres" ] || { echo "❌ el Makefile no pide ningún aprovisionador por nombre (¿se ha movido el paso vagrant-up?)"; exit 1; }
fallos=0; n=0
for p in $nombres; do
  n=$((n + 1))
  if grep -qE "\.vm\.provision \"$p\", type: \"" Vagrantfile; then
    echo "✅ $p: declarado con nombre en el Vagrantfile"
  else
    echo "❌ $p: el Makefile lo pide con --provision-with y el Vagrantfile no lo declara con nombre (\"$p\", type: \"shell\")"
    fallos=$((fallos + 1))
  fi
done
echo "$((n - fallos))/$n aprovisionadores"
[ "$fallos" -eq 0 ]
