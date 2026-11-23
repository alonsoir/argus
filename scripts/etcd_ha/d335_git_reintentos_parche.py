#!/usr/bin/env python3
# d335_git_reintentos_parche.py — [TERCEROS-GIT-REINTENTOS-D335] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, pieza 1b
# (decisión de Alonso DAY335): gf_clonar reintenta el clon hasta GF_INTENTOS veces (3, como el `wget -t 3` de los demás
# instaladores), con GF_ESPERA_S segundos entre intentos; si el tag apunta a otro commit, para sin reintentar. Va
# encima de la pieza 1 (d335_git_fijado_parche.py).
# Uso, desde la raíz del repo: python3 scripts/etcd_ha/d335_git_reintentos_parche.py
# Comprueba el sha256 de partida, cada ancla las veces exactas, el sha256 de llegada, y no escribe nada si algo falla.
import hashlib, pathlib, sys

PARTIDA = {
    'scripts/terceros/lib_git_fijado.sh': '5a73da77d3c826ea991229e8c1cb86623db4b19cfa18046ff2f5b89c92828a7b',
    'scripts/terceros/test_lib_git_fijado.sh': '7197ad7d4d9206f3d1b3766ee653acb7c74d93dab6a47ddb4e5300d509b5a5e4',
}
LLEGADA = {
    'scripts/terceros/lib_git_fijado.sh': 'b53dd80cb7298c153071dbae03e5d89afe59d39a118126d21d5be003f30e61e3',
    'scripts/terceros/test_lib_git_fijado.sh': '7a6cbec227153fce6b178fb6f27fd97bd5d65608dc25ffeaec6e1f6a128ca4c3',
}

CAMBIOS = {
    'scripts/terceros/lib_git_fijado.sh': [
        ('''# Se carga con `.` desde cada instalador; no toca el sistema (lo prueba scripts/terceros/test_lib_git_fijado.sh en el
# Mac, sin red: con un repositorio git hecho allí).
''', '''# Se carga con `.` desde cada instalador; no toca el sistema (lo prueba scripts/terceros/test_lib_git_fijado.sh en el
# Mac, sin red: con un repositorio git hecho allí).
# [TERCEROS-GIT-REINTENTOS-D335] (decisión de Alonso DAY335) un fallo de red pasajero no debe costar un EMECAS: el clon
# se reintenta hasta GF_INTENTOS veces, como el `wget -t 3` de los demás instaladores de scripts/terceros/; agotados,
# para y lo dice. Que el tag apunte a otro commit no es un fallo pasajero: para al primero, sin reintentar.

GF_INTENTOS=3     # intentos de clonar, en total (1..10)
GF_ESPERA_S=10    # segundos entre un intento fallido y el siguiente (0..300)
''', 1),
        ('''# gf_clonar URL TAG DESTINO COMMIT -> clona TAG (solo ese, profundidad 1) en DESTINO y rc 0 si HEAD es COMMIT; si no,
# rc 1 y el motivo por la salida. No compila nada.
gf_clonar() {
  local h
  git -c advice.detachedHead=false clone -q --depth 1 --branch "$2" "$1" "$3" >/dev/null 2>&1 \\
    || { echo "no se pudo clonar el tag $2 de $1"; return 1; }
  h=$(git -C "$3" rev-parse HEAD 2>/dev/null)
''', '''# gf_clonar URL TAG DESTINO COMMIT -> clona TAG (solo ese, profundidad 1) en DESTINO y rc 0 si HEAD es COMMIT; si no,
# rc 1 y el motivo por la salida. Hasta GF_INTENTOS intentos de clonar, avisando de cada fallo por stderr; la
# comprobación del commit, una vez. No compila nada.
gf_clonar() {
  local h i=1
  until git -c advice.detachedHead=false clone -q --depth 1 --branch "$2" "$1" "$3" >/dev/null 2>&1; do
    rm -rf "$3"
    [ "$i" -lt "$GF_INTENTOS" ] || { echo "no se pudo clonar el tag $2 de $1 ($GF_INTENTOS intentos)"; return 1; }
    echo "[GIT-FIJADO] intento $i/$GF_INTENTOS de clonar el tag $2 de $1 fallido; otro en $GF_ESPERA_S s" >&2
    i=$((i + 1)); sleep "$GF_ESPERA_S"
  done
  h=$(git -C "$3" rev-parse HEAD 2>/dev/null)
''', 1),
    ],
    'scripts/terceros/test_lib_git_fijado.sh': [
        ('''# Casos sacados DAY335 de test_libbpf_instalar.sh. Cada caso de rechazo se vuelve a correr contra funciones que lo
# aceptan todo, y tiene que fallar ahí: así se ve que el test distingue.
''', '''# Casos sacados DAY335 de test_libbpf_instalar.sh. Cada caso de rechazo se vuelve a correr contra funciones que lo
# aceptan todo, y tiene que fallar ahí: así se ve que el test distingue. Los reintentos ([TERCEROS-GIT-REINTENTOS-D335]),
# con un `git` falso delante en el PATH que falla los N primeros `clone` y cuenta cuántos hubo.
''', 1),
        ('''. "$aqui/lib_git_fijado.sh"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
''', '''. "$aqui/lib_git_fijado.sh"

T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
# los valores de la biblioteca, comprobados antes de cambiar la espera para que el test no duerma
INTENTOS_LIB=$GF_INTENTOS; ESPERA_LIB=$GF_ESPERA_S
GF_ESPERA_S=0
''', 1),
        ('''UP="file://$T/up"; MOVIDO="file://$T/movido.git"
''', '''UP="file://$T/up"; MOVIDO="file://$T/movido.git"

# git falso: los FALLOS_RED primeros `clone` salen con 128 (como sin red); todos se cuentan en $T/cuenta
GIT_REAL=$(command -v git)
mkdir -p "$T/bin"
cat > "$T/bin/git" <<FALSO
#!/usr/bin/env bash
for a in "\\$@"; do
  if [ "\\$a" = clone ]; then
    n=\\$(( \\$(cat "$T/cuenta" 2>/dev/null || echo 0) + 1 )); echo "\\$n" > "$T/cuenta"
    [ "\\$n" -le "\\$(cat "$T/fallos_red")" ] && exit 128
    break
  fi
done
exec "$GIT_REAL" "\\$@"
FALSO
chmod +x "$T/bin/git"
# clona_red N NOMBRE URL TAG COMMIT -> gf_clonar con una red que falla los N primeros clones
clona_red() { echo "$1" > "$T/fallos_red"; rm -f "$T/cuenta"; PATH="$T/bin:$PATH" clona "${@:2}"; }
cuenta_es() { [ "$(cat "$T/cuenta" 2>/dev/null)" = "$1" ]; }
''', 1),
        ('''  rechaza "repositorio que no existe" clona nada "file://$T/no_existe" v1.2.3 "$C1"
}
''', '''  rechaza "repositorio que no existe" clona nada "file://$T/no_existe" v1.2.3 "$C1"
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
''', 1),
    ],
}

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    raiz = pathlib.Path('.')
    nuevos = {}
    for f, esperado in PARTIDA.items():
        b = (raiz / f).read_bytes()
        if sha(b) != esperado:
            sys.exit(f'FALLA: {f} sha256 de partida {sha(b)}, se espera {esperado} (¿pieza 1 aplicada?). Nada escrito.')
        t = b.decode()
        for viejo, nuevo, veces in CAMBIOS[f]:
            n = t.count(viejo)
            if n != veces:
                sys.exit(f'FALLA: {f}: el ancla aparece {n} veces, se esperan {veces}:\n{viejo[:120]}\nNada escrito.')
            t = t.replace(viejo, nuevo)
        nuevos[f] = t.encode()
        if sha(nuevos[f]) != LLEGADA[f]:
            sys.exit(f'FALLA: {f} sha256 de llegada {sha(nuevos[f])}, se espera {LLEGADA[f]}. Nada escrito.')
    for f, b in nuevos.items():
        (raiz / f).write_bytes(b)
        print(f'OK {f} {sha(b)}')

if __name__ == '__main__':
    main()
