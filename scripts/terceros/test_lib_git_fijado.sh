#!/usr/bin/env bash
# scripts/terceros/test_lib_git_fijado.sh — [TERCEROS-GIT-FIJADO-D335] tests de las funciones gf_* de lib_git_fijado.sh
# (Mac, sin VMs ni red: un repositorio git de juguete hecho aquí, con un tag ligero como los de libbpf o etcd-cpp-apiv3).
# Casos sacados DAY335 de test_libbpf_instalar.sh. Cada caso de rechazo se vuelve a correr contra funciones que lo
# aceptan todo, y tiene que fallar ahí: así se ve que el test distingue. Los reintentos ([TERCEROS-GIT-REINTENTOS-D335]),
# con un `git` falso delante en el PATH que falla los N primeros `clone` y cuenta cuántos hubo.
set -u
LC_ALL=C; export LC_ALL
aqui=$(dirname "$0")
. "$aqui/lib_git_fijado.sh"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
# los valores de la biblioteca, comprobados antes de cambiar la espera para que el test no duerma
INTENTOS_LIB=$GF_INTENTOS; ESPERA_LIB=$GF_ESPERA_S
GF_ESPERA_S=0
casos=0; fallos=0; rechazos=0; rechazos_vistos=0
acepta() { local n=$1; shift; casos=$((casos + 1)); if "$@" >/dev/null 2>&1; then echo "✅ $n"; else echo "❌ $n"; fallos=$((fallos + 1)); fi; }
rechaza() { local n=$1; shift; casos=$((casos + 1)); rechazos=$((rechazos + 1)); if "$@" >/dev/null 2>&1; then echo "❌ $n"; fallos=$((fallos + 1)); rechazos_vistos=$((rechazos_vistos + 1)); else echo "✅ $n"; fi; }

# repositorio de juguete: dos commits; v1.2.3 (tag ligero) en el primero, y una copia donde el tag se ha movido al segundo
g() { git -C "$1" -c user.name=t -c user.email=t@t -c commit.gpgsign=false "${@:2}" >/dev/null 2>&1; }
mkdir -p "$T/up" && git init -q "$T/up" && echo uno > "$T/up/f" && g "$T/up" add f && g "$T/up" commit -q -m uno
g "$T/up" tag v1.2.3; C1=$(git -C "$T/up" rev-parse HEAD)
echo dos > "$T/up/f" && g "$T/up" commit -q -am dos; C2=$(git -C "$T/up" rev-parse HEAD)
git clone -q --bare "$T/up" "$T/movido.git" >/dev/null 2>&1 && g "$T/movido.git" tag -f v1.2.3 "$C2"
UP="file://$T/up"; MOVIDO="file://$T/movido.git"

# git falso: los FALLOS_RED primeros `clone` salen con 128 (como sin red); todos se cuentan en $T/cuenta
GIT_REAL=$(command -v git)
mkdir -p "$T/bin"
cat > "$T/bin/git" <<FALSO
#!/usr/bin/env bash
for a in "\$@"; do
  if [ "\$a" = clone ]; then
    n=\$(( \$(cat "$T/cuenta" 2>/dev/null || echo 0) + 1 )); echo "\$n" > "$T/cuenta"
    [ "\$n" -le "\$(cat "$T/fallos_red")" ] && exit 128
    break
  fi
done
exec "$GIT_REAL" "\$@"
FALSO
chmod +x "$T/bin/git"
# clona_red N NOMBRE URL TAG COMMIT -> gf_clonar con una red que falla los N primeros clones
clona_red() { echo "$1" > "$T/fallos_red"; rm -f "$T/cuenta"; PATH="$T/bin:$PATH" clona "${@:2}"; }
cuenta_es() { [ "$(cat "$T/cuenta" 2>/dev/null)" = "$1" ]; }

printf '# comentario\n%s\n' "$C1" > "$T/c_bien"
printf '%s\n%s\n' "$C1" "$C2" > "$T/c_dos"
printf '%s\n' "${C1%?}" > "$T/c_corto"
printf '%s\n' "$(printf '%s' "$C1" | tr 'a-f' 'A-F')" > "$T/c_mayus"
printf '# solo comentarios\n' > "$T/c_vacio"

clona() { rm -rf "$T/d_$1"; gf_clonar "$2" "$3" "$T/d_$1" "$4"; }
commit_lee() { [ "$(gf_commit_de_fichero "$1")" = "$2" ]; }
# el clon bueno deja en DESTINO el árbol del commit fijado, no el del otro
contenido_es() { [ "$(cat "$T/d_$1/f" 2>/dev/null)" = "$2" ]; }

los_casos() {
  acepta "versión 1.2.3" gf_version_valida 1.2.3
  acepta "versión 0.67.0" gf_version_valida 0.67.0
  rechaza "versión v1.2.3 (con v)" gf_version_valida v1.2.3
  rechaza "versión 1.2 (sin parche)" gf_version_valida 1.2
  rechaza "versión latest (por nombre)" gf_version_valida latest
  rechaza "versión vacía" gf_version_valida ""
  rechaza "dos versiones en dos líneas" gf_version_valida $'1.2.3\n1.2.4'
  acepta "fichero COMMIT con comentario" commit_lee "$T/c_bien" "$C1"
  rechaza "fichero COMMIT con dos líneas" gf_commit_de_fichero "$T/c_dos"
  rechaza "fichero COMMIT corto" gf_commit_de_fichero "$T/c_corto"
  rechaza "fichero COMMIT en mayúscula" gf_commit_de_fichero "$T/c_mayus"
  rechaza "fichero COMMIT sin valor" gf_commit_de_fichero "$T/c_vacio"
  rechaza "fichero COMMIT que no existe" gf_commit_de_fichero "$T/no_existe"
  acepta "tag v1.2.3 que apunta al commit fijado" clona bien "$UP" v1.2.3 "$C1"
  acepta "el clon del tag v1.2.3 trae el árbol del commit fijado" contenido_es bien uno
  rechaza "tag v1.2.3 que apunta a otro commit" clona otro "$UP" v1.2.3 "$C2"
  rechaza "tag v1.2.3 movido a otro commit en el repositorio" clona movido "$MOVIDO" v1.2.3 "$C1"
  rechaza "tag que no existe (v9.9.9)" clona falta "$UP" v9.9.9 "$C1"
  rechaza "repositorio que no existe" clona nada "file://$T/no_existe" v1.2.3 "$C1"
  acepta "la biblioteca da 3 intentos" test "$INTENTOS_LIB" = 3
  acepta "la biblioteca espera 10 s entre intentos" test "$ESPERA_LIB" = 10
  acepta "red que falla 2 veces: clona a la tercera" clona_red 2 red2 "$UP" v1.2.3 "$C1"
  acepta "red que falla 2 veces: hubo 3 intentos" cuenta_es 3
  acepta "red que falla 2 veces: el árbol es el del commit fijado" contenido_es red2 uno
  rechaza "red que falla 3 veces: para" clona_red 3 red3 "$UP" v1.2.3 "$C1"
  acepta "red que falla 3 veces: 3 intentos, ni uno más" cuenta_es 3
  rechaza "tag que apunta a otro commit, con red sana" clona_red 0 otro2 "$UP" v1.2.3 "$C2"
  acepta "tag que apunta a otro commit: un intento, sin reintentar" cuenta_es 1
}

los_casos
echo "$((casos - fallos))/$casos casos"
total=$fallos

# Contra funciones que lo aceptan todo, cada rechazo tiene que dar ❌.
gf_version_valida() { return 0; }
gf_commit_de_fichero() { echo x; }
gf_clonar() { mkdir -p "$3"; return 0; }
esperados=$rechazos; casos=0; fallos=0; rechazos=0; rechazos_vistos=0
los_casos > /dev/null
if [ "$rechazos_vistos" = "$esperados" ]; then
  echo "✅ contra funciones que lo aceptan todo fallan los $esperados casos de rechazo"
else
  echo "❌ contra funciones que lo aceptan todo fallan $rechazos_vistos de los $esperados casos de rechazo"; total=$((total + 1))
fi
[ "$total" = 0 ] && echo "✅ test-lib-git-fijado" || { echo "❌ test-lib-git-fijado: $total fallos"; exit 1; }
