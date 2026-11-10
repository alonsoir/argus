#!/usr/bin/env bash
# scripts/vigilancia/alertas_wazuh.sh — [VIGILANCIA-E2E-D322] ADR-060 8e.4d-3: alertas del alerts.json del manager para
# lab-e2e-vigilancia. EN LA VM wazuh como vagrant (hace sudo dentro). Salida legible por máquina: "E2E|<CLAVE>|<valor>".
#   posicion                                   tamaño en bytes e inodo de alerts.json (el punto de partida de un caso)
#   esperar DESDE INODO ESPERA_S AGENTE REGLA [TEXTO]
#                                              espera hasta ESPERA_S (entero [1, 600]) una alerta de REGLA (id) del
#                                              AGENTE (agent.name) escrita después del byte DESDE, con TEXTO en la línea
#   contar DESDE INODO AGENTE REGLA [TEXTO]    cuántas hay desde DESDE
# Lee solo lo nuevo (seek al byte DESDE): coste lineal en lo escrito desde el inicio del caso, no en el fichero entero.
# Si el inodo cambió (rotación de medianoche), lee el fichero nuevo desde el principio y lo dice.
set -u
LC_ALL=C; export LC_ALL
F=/var/ossec/logs/alerts/alerts.json
entero() { [[ "$1" =~ ^[0-9]+$ ]]; }
case "${1:-}" in
posicion)
  sudo test -f "$F" || { echo "E2E|FALLA|no existe $F (¿wazuh-manager en marcha?)"; exit 1; }
  echo "E2E|DESDE|$(sudo stat -c %s "$F")"; echo "E2E|INODO|$(sudo stat -c %i "$F")";;
esperar|contar)
  M=$1; shift
  if [ "$M" = esperar ]; then D=${1:-}; I=${2:-}; S=${3:-}; A=${4:-}; R=${5:-}; X=${6:-}
  else D=${1:-}; I=${2:-}; S=0; A=${3:-}; R=${4:-}; X=${5:-}; fi
  entero "$D" && entero "$I" && entero "$S" && [ -n "$A" ] && entero "$R" || { echo "E2E|FALLA|argumentos mal formados: $*"; exit 2; }
  [ "$M" = contar ] || { [ "$S" -ge 1 ] && [ "$S" -le 600 ]; } || { echo "E2E|FALLA|ESPERA_S '$S' fuera de [1, 600]"; exit 2; }
  sudo python3 - "$F" "$M" "$D" "$I" "$S" "$A" "$R" "$X" <<'PY'
import json, os, sys, time
f, modo, desde, inodo, espera, agente, regla, texto = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), \
    int(sys.argv[5]), sys.argv[6], sys.argv[7], sys.argv[8]
fin = time.time() + espera
def buscar():
    st = os.stat(f); d = desde
    if st.st_ino != inodo or st.st_size < desde:
        print("E2E|AVISO|alerts.json rotado desde el inicio del caso: se lee el nuevo desde el principio"); d = 0
    halladas = []
    with open(f, "rb") as fh:
        fh.seek(d)
        for linea in fh:
            t = linea.decode("utf-8", "replace")
            if texto and texto not in t: continue
            try: a = json.loads(t)
            except Exception: continue
            if str(a.get("rule", {}).get("id")) == regla and a.get("agent", {}).get("name") == agente:
                halladas.append(a)
    return halladas
while True:
    h = buscar()
    if modo == "contar":
        print("E2E|CUENTA|%d" % len(h)); break
    if h:
        a = h[0]; r = a.get("rule", {})
        det = (a.get("syscheck", {}) or {}).get("path") or (a.get("data", {}) or {}).get("output") or a.get("full_log", "")
        print("E2E|OK|regla %s nivel %s del agente %s a las %s: %s | %s" % (regla, r.get("level"), agente,
              a.get("timestamp", "?"), r.get("description", "?"), str(det)[:220]))
        break
    if time.time() >= fin:
        print("E2E|FALLA|ninguna alerta %s del agente %s%s en %d s" % (regla, agente, (" con '%s'" % texto) if texto else "", espera))
        break
    time.sleep(2)
PY
  ;;
*) echo "uso: $0 posicion | esperar DESDE INODO ESPERA_S AGENTE REGLA [TEXTO] | contar DESDE INODO AGENTE REGLA [TEXTO]"; exit 2;;
esac
