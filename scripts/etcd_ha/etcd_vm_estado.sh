#!/bin/bash
# etcd_vm_estado.sh — DAY317, paso 6b/6c de DEBT-ETCD-HA-TLS-RAFT-001: estado REAL de la VM etcd (no solo procesos).
# Se ejecuta EN LA VM etcd como vagrant (hace sudo dentro): vagrant ssh etcd -c "bash /vagrant/scripts/etcd_ha/etcd_vm_estado.sh"
#   - etcd-server: unidad systemd activa y GET /health por mTLS (certificado del propio etcd-server, regla «cualquiera»)
#   - etcd: por cada miembro (etcdctl member list: con el PR2 salen todos), sano o no, líder, term y retraso respecto al líder
#   - vault-hmac: por cada dirección de almacen_claves.vault_addrs, /v1/sys/health (200 activo, 429 en espera, 503 sellado)
# Direcciones y certificados salen del JSON del etcd-server (el que escribe Ansible): el JSON es la ley.
# Opciones: --estricto        rc 1 si algo no está sano (EMECAS); sin ella, rc 0 siempre (pipeline-status informa)
#           --esperar S       reintenta hasta S segundos a que todo esté sano, entero [0, 300], defecto 0
#           --retraso-max N   entradas de retraso respecto al líder que aún cuentan como sincronizado, entero [0, 1000000],
#                             defecto 1000
set -u
LC_ALL=C; export LC_ALL
JSON=/etc/ml-defender/etcd-server/etcd-server.json
UNIDAD=ml-defender-etcd-server.service
ESTRICTO=no; ESPERAR=""; RETRASO=""
while [ $# -gt 0 ]; do
  case "$1" in
    --estricto) ESTRICTO=si; shift;;
    --esperar) ESPERAR=${2:-}; shift 2 || shift;;
    --retraso-max) RETRASO=${2:-}; shift 2 || shift;;
    *) echo "[ETCD-VM-ESTADO] opción desconocida '$1' (--estricto | --esperar S | --retraso-max N)"; exit 2;;
  esac
done
entero() {  # nombre valor defecto min max -> deja VAL y ORIGEN (sin subshell)
  local n=$1 v=$2 d=$3 lo=$4 hi=$5
  if [ -z "$v" ]; then VAL=$d; ORIGEN="defecto: ausente"; return; fi
  if ! [[ "$v" =~ ^[0-9]+$ ]] || [ "$v" -lt "$lo" ] || [ "$v" -gt "$hi" ]; then
    VAL=$d; ORIGEN="defecto: '$v' mal formado, entero en [$lo, $hi]"; return
  fi
  VAL=$v; ORIGEN="argumento"
}
entero esperar "$ESPERAR" 0 0 300;            ESPERAR=$VAL;   O_ESP=$ORIGEN
entero retraso-max "$RETRASO" 1000 0 1000000; RETRASO_V=$VAL; O_RET=$ORIGEN
echo "[ETCD-VM-ESTADO] $(date -u +%FT%TZ) $(hostname) estricto=$ESTRICTO esperar_s=$ESPERAR ($O_ESP) retraso_max=$RETRASO_V ($O_RET)"

if ! sudo test -f "$JSON"; then
  echo "  ❌ etcd-server:   STOPPED [VM etcd: falta $JSON; despliegue: make etcd-vm-deploy desde el Mac]"
  [ "$ESTRICTO" = si ] && exit 1 || exit 0
fi
CFG=$(sudo python3 - "$JSON" <<'PY'
import json, sys
j = json.load(open(sys.argv[1]))
a, c, t, s = j["almacen"], j["almacen_claves"], j["tls"], j["server"]
print(",".join(a["endpoints"])); print(a["ca_file"]); print(a["cert_file"]); print(a["key_file"])
print(" ".join(c["vault_addrs"])); print(c["ca_file"]); print(c["cert_file"]); print(c["key_file"])
print(t["ca_file"]); print(t["cert_file"]); print(t["key_file"]); print(s["port"])
PY
) || { echo "  ❌ etcd-server:   STOPPED [VM etcd: $JSON ilegible o sin almacen/almacen_claves/tls/server]"; [ "$ESTRICTO" = si ] && exit 1 || exit 0; }
{ read -r A_EP; read -r A_CA; read -r A_CRT; read -r A_KEY; read -r V_ADDRS; read -r V_CA; read -r V_CRT; read -r V_KEY
  read -r T_CA; read -r T_CRT; read -r T_KEY; read -r PUERTO; } <<< "$CFG"

evaluar() {  # deja el informe en INFORME y SANO=si|no
  local ok=si l
  INFORME=""
  # etcd-server
  local act code
  act=$(systemctl is-active "$UNIDAD" 2>/dev/null)
  code=$(sudo curl -s -o /dev/null -w '%{http_code}' --max-time 3 --cacert "$T_CA" --cert "$T_CRT" --key "$T_KEY" \
         "https://127.0.0.1:$PUERTO/health" 2>/dev/null)
  if [ "$act" = active ] && [ "$code" = 200 ]; then
    INFORME+="  ✅ etcd-server:   RUNNING [VM etcd: systemd active, /health $code]"$'\n'
  elif [ "$act" = active ]; then
    INFORME+="  ⚠️  etcd-server:   RUNNING sin servicio [VM etcd: systemd active, /health ${code:-sin respuesta}]"$'\n'; ok=no
  else
    INFORME+="  ❌ etcd-server:   STOPPED [VM etcd: systemd ${act:-desconocido}, /health ${code:-sin respuesta}]"$'\n'; ok=no
  fi
  # etcd: miembros, salud, líder, retraso
  local E="sudo etcdctl --endpoints=$A_EP --cacert=$A_CA --cert=$A_CRT --key=$A_KEY --command-timeout=3s -w json"
  local ml st he
  ml=$($E member list 2>/dev/null); st=$($E endpoint status --cluster 2>/dev/null); he=$($E endpoint health --cluster 2>/dev/null)
  l=$(python3 - "$RETRASO_V" "$ml" "$st" "$he" <<'PY'
import json, sys
rmax = int(sys.argv[1])
def carga(x):
    try: return json.loads(x)
    except Exception: return None
ml, st, he = carga(sys.argv[2]), carga(sys.argv[3]), carga(sys.argv[4])
if not ml or "members" not in ml:
    print("NO"); print("  ❌ etcd:          sin respuesta a member list (etcd caído o certificado rechazado)"); sys.exit()
miembros = {str(m["ID"]): m for m in ml["members"]}
sanos = {h["endpoint"]: h.get("health", False) for h in (he or [])}
estados = {str(s["Status"]["header"]["member_id"]): s for s in (st or [])}
lideres = {str(s["Status"].get("leader", 0)) for s in estados.values()} - {"0"}
lider = next(iter(lideres)) if len(lideres) == 1 else None
idx_lider = estados[lider]["Status"]["raftIndex"] if lider in estados else None
lineas, n_sanos, rmax_visto, ok = [], 0, 0, True
for mid, m in sorted(miembros.items(), key=lambda kv: kv[1].get("name", "")):
    url = (m.get("clientURLs") or ["?"])[0]
    s = estados.get(mid)
    sano = bool(sanos.get(url)) and s is not None
    if sano: n_sanos += 1
    if s:
        S = s["Status"]; ap = S.get("raftAppliedIndex", S["raftIndex"])
        ret = (idx_lider - ap) if idx_lider is not None else None
        if ret is not None: rmax_visto = max(rmax_visto, ret)
        lineas.append("       - %s %s %s%s term=%s indice=%s aplicado=%s retraso=%s" % (
            m.get("name", "?"), url, "sano" if sano else "NO SANO", " lider" if mid == lider else "",
            S["raftTerm"], S["raftIndex"], ap, "?" if ret is None else ret))
    else:
        lineas.append("       - %s %s NO RESPONDE" % (m.get("name", "?"), url))
if lider is None or n_sanos != len(miembros) or rmax_visto > rmax: ok = False
nombre_lider = miembros[lider].get("name", "?") if lider in miembros else ("varios: %d" % len(lideres) if lideres else "ninguno")
term = estados[lider]["Status"]["raftTerm"] if lider in estados else "?"
print("SI" if ok else "NO")
print("  %s etcd:          %d/%d miembros sanos, líder %s (term %s), retraso máx %d entradas (límite %d)" % (
    "✅" if ok else "❌", n_sanos, len(miembros), nombre_lider, term, rmax_visto, rmax))
for x in lineas: print(x)
PY
)
  [ "$(printf '%s\n' "$l" | head -n 1)" = SI ] || ok=no
  INFORME+="$(printf '%s\n' "$l" | tail -n +2)"$'\n'
  # Vault (claves HMAC): cada dirección del JSON
  local a c nodos=0 activos=0 malos=0 det=""
  for a in $V_ADDRS; do
    nodos=$((nodos+1))
    c=$(sudo curl -s -o /dev/null -w '%{http_code}' --max-time 3 --cacert "$V_CA" --cert "$V_CRT" --key "$V_KEY" \
        "$a/v1/sys/health" 2>/dev/null)
    case "$c" in
      200) activos=$((activos+1)); det+=" $a activo ($c);";;
      429) det+=" $a en espera ($c);";;
      503) malos=$((malos+1)); det+=" $a SELLADO ($c);";;
      501) malos=$((malos+1)); det+=" $a SIN INICIALIZAR ($c);";;
      *)   malos=$((malos+1)); det+=" $a sin respuesta (${c:-000});";;
    esac
  done
  if [ "$activos" = 1 ] && [ "$malos" = 0 ]; then
    INFORME+="  ✅ vault-hmac:    $nodos nodos, 1 activo:$det"$'\n'
  else
    INFORME+="  ❌ vault-hmac:    $nodos nodos, $activos activos, $malos con problemas:$det"$'\n'; ok=no
  fi
  SANO=$ok
}

T0=$(date +%s)
while :; do
  evaluar
  [ "$SANO" = si ] && break
  [ $(( $(date +%s) - T0 )) -ge "$ESPERAR" ] && break
  sleep 2
done
printf '%s' "$INFORME"
if [ "$SANO" = si ]; then
  echo "[ETCD-VM-ESTADO] SANO tras $(( $(date +%s) - T0 )) s"
else
  echo "[ETCD-VM-ESTADO] NO SANO tras $(( $(date +%s) - T0 )) s: el pipeline sigue protegiendo, pero sin etcd-server/etcd/Vault sanos no se firma con HMAC"
fi
[ "$ESTRICTO" = si ] && [ "$SANO" != si ] && exit 1
exit 0
