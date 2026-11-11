# scripts/vigilancia/lib_apt_oficial.sh — [VIGILANCIA-D321] repositorio apt firmado del mantenedor oficial, con su clave
# comprobada por huella. Se carga con `source` (wazuh_agente_instalar.sh, falco_instalar.sh, aprovisionador
# install-wazuh del Vagrantfile). Todo el software de terceros sale de su mantenedor: apt comprueba la firma de cada
# paquete con esta clave, y la clave solo se instala si TODAS sus claves principales están en el fichero de huellas
# del repo (provisioning/<producto>/CLAVE). Una clave que no está, o una descarga que no es una clave, para la
# instalación: nunca se instala "lo que venga".
#
# repo_oficial NOMBRE URL_CLAVE FICHERO_HUELLAS URL_REPO "SUITE COMPONENTES"
#   deja /usr/share/keyrings/NOMBRE.gpg y /etc/apt/sources.list.d/NOMBRE.list (deb [signed-by=...] URL_REPO SUITE ...)
#   y devuelve 0; con cualquier fallo, devuelve 1 sin tocar lo que hubiera. Otra entrada de sources.list.d que apunte
#   al mismo URL_REPO (otro signed-by daría "Conflicting values set for option Signed-By" a apt) también es fallo:
#   se avisa con su nombre, no se borra.
repo_oficial() {
  local nombre=$1 url_clave=$2 huellas=$3 url_repo=$4 suite=$5
  local anillo=/usr/share/keyrings/$nombre.gpg lista=/etc/apt/sources.list.d/$nombre.list
  local tmp f tengo quiero otros
  [[ "$nombre" =~ ^[a-z0-9-]{1,64}$ ]] || { echo "[APT-OFICIAL] FALLA: nombre '$nombre' mal formado"; return 1; }
  [ -r "$huellas" ] || { echo "[APT-OFICIAL] FALLA: no leo $huellas"; return 1; }
  quiero=$(grep -v '^#' "$huellas" | tr -d ' \t' | grep -E '^[0-9A-F]{40}$' | sort -u)
  [ -n "$quiero" ] || { echo "[APT-OFICIAL] FALLA: $huellas sin huellas (40 hexadecimales en mayúscula, una por línea)"; return 1; }
  for c in curl gpg; do
    command -v "$c" >/dev/null || { apt-get update -qq && apt-get install -y curl gnupg >/dev/null; break; }
  done
  otros=$(grep -lsF "$url_repo" /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources 2>/dev/null | grep -vxF "$lista")
  [ -z "$otros" ] || { echo "[APT-OFICIAL] FALLA: $url_repo ya está en $otros (revisarlo a mano; no se borra)"; return 1; }
  tmp=$(mktemp -d)
  if ! curl -fsSL --proto '=https' --tlsv1.2 -m 60 "$url_clave" -o "$tmp/clave"; then
    rm -rf "$tmp"; echo "[APT-OFICIAL] FALLA: no se pudo descargar $url_clave"; return 1
  fi
  tengo=$(gpg --show-keys --with-colons "$tmp/clave" 2>/dev/null \
            | awk -F: '$1 == "pub" {p = 1; next} p && $1 == "fpr" {print $10; p = 0}' | sort -u)
  if [ -z "$tengo" ]; then rm -rf "$tmp"; echo "[APT-OFICIAL] FALLA: $url_clave no contiene ninguna clave"; return 1; fi
  for f in $tengo; do
    if ! grep -qxF "$f" <<< "$quiero"; then
      rm -rf "$tmp"; echo "[APT-OFICIAL] FALLA: $url_clave trae la clave $f, que no está en $huellas"; return 1
    fi
  done
  gpg --dearmor < "$tmp/clave" > "$tmp/anillo" || { rm -rf "$tmp"; echo "[APT-OFICIAL] FALLA: gpg --dearmor"; return 1; }
  echo "deb [signed-by=$anillo] $url_repo $suite" > "$tmp/lista"
  cmp -s "$tmp/anillo" "$anillo" || install -m 0644 -o root -g root "$tmp/anillo" "$anillo"
  cmp -s "$tmp/lista" "$lista" || install -m 0644 -o root -g root "$tmp/lista" "$lista"
  rm -rf "$tmp"
  echo "[APT-OFICIAL] $nombre: clave $(echo $tengo) (en $huellas) -> $anillo; $(cat "$lista")"
}

# instalar_fijado PAQUETE VERSION — instala exactamente esa versión desde los repos configurados y la deja en hold.
# Devuelve 0 si al final está esa versión; 1 si no. Las variables de entorno del paquete (WAZUH_MANAGER, FALCO_*) las
# pone quien llama.
instalar_fijado() {
  local paquete=$1 version=$2 got
  apt-mark unhold "$paquete" >/dev/null 2>&1 || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y --allow-downgrades "$paquete=$version" \
    || { echo "[APT-OFICIAL] FALLA: apt-get install $paquete=$version"; return 1; }
  apt-mark hold "$paquete" >/dev/null
  got=$(dpkg-query -W -f='${Version}' "$paquete" 2>/dev/null)
  [ "$got" = "$version" ] || { echo "[APT-OFICIAL] FALLA: instalado $paquete '$got', se exige '$version'"; return 1; }
  echo "[APT-OFICIAL] $paquete $got instalado y fijado (apt-mark hold)"
}
