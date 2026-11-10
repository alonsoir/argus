#!/usr/bin/env bash
# scripts/vigilancia/lab_e2e_vigilancia_etcd.sh — [VIGILANCIA-E2E-D322] ADR-060 8e.4d-3: acciones de lab-e2e-vigilancia
# EN LA VM etcd, como vagrant (hace sudo dentro). Cada acción tiene su deshacer y "restaurar" los deshace todos
# (idempotente: es lo que llama el trap del driver). Salida: "E2E|<CLAVE>|<valor>".
#   fim-crear | fim-borrar   C1 fichero de prueba en /etc/argus-pki (FIM en tiempo real; no es .key: Falco no lo mira)
#   disco-bajar | disco-restaurar
#                            C2 umbral_pct=1 en /etc/argus-vigilancia/disco.json (copia exacta en $BK; se restaura con cmp)
#   audit-romper | audit-restaurar
#                            C3 chattr +i en el audit de fichero de Vault y una petición auditada (login por certificado
#                            del etcd-server con sudo curl: traza NOTICE de Falco, como pipeline-status)
#   clave-copiar             C5 copia la clave del desellado fuera con sudo install (lectura ajena: Falco CRITICAL)
#   clave-intento            C6 lee la clave del desellado como nobody (EACCES: Falco WARNING, argus_lab_clave_intento_fallido)
#   etcd-parar | etcd-arrancar   C8 para y arranca etcd (el etcd-server sigue: última copia en memoria)
#   falco-lineas             nº de líneas de /var/log/falco/eventos.json
#   restaurar                todo lo anterior deshecho
set -u
LC_ALL=C; export LC_ALL
BK=/root/vigilancia_e2e_bk
PRUEBA=/etc/argus-pki/vigilancia-e2e.prueba
DISCO=/etc/argus-vigilancia/disco.json
AUDIT=/var/log/vault/audit.log
CLAVE=/etc/argus-pki/argus-vault-unseal.key
COPIA=/tmp/vigilancia-e2e.copia
EVENTOS=/var/log/falco/eventos.json
C="--cacert /etc/vault.d/tls/ca.crt --cert /etc/argus-pki/etcd-server.crt --key /etc/argus-pki/etcd-server.key"
ok() { echo "E2E|OK|$*"; }
mal() { echo "E2E|FALLA|$*"; }
login() { sudo curl -s -o /dev/null -w '%{http_code}' --max-time 5 $C -X POST -d '{"name":"etcd-server"}' \
            https://127.0.0.1:8200/v1/auth/cert/login; }
disco_restaurar() {
  sudo test -f "$BK/disco.json" || { ok "disco.json sin copia: nada que restaurar"; return 0; }
  sudo cp -p "$BK/disco.json" "$DISCO"
  if sudo cmp -s "$BK/disco.json" "$DISCO"; then sudo rm -f "$BK/disco.json"; ok "disco.json restaurado (cmp 0)"
  else mal "disco.json NO coincide con la copia $BK/disco.json"; return 1; fi
}
case "${1:-}" in
fim-crear)  echo "vigilancia-e2e $(date -u +%FT%TZ)" | sudo tee "$PRUEBA" > /dev/null && sudo chmod 0600 "$PRUEBA" \
              && ok "creado $PRUEBA" || mal "no se pudo crear $PRUEBA";;
fim-borrar) sudo rm -f "$PRUEBA" && ok "borrado $PRUEBA";;
disco-bajar)
  sudo test -f "$DISCO" || { mal "no existe $DISCO"; exit 1; }
  sudo install -d -m 0700 "$BK"
  sudo test -f "$BK/disco.json" || sudo cp -p "$DISCO" "$BK/disco.json"
  sudo python3 - "$DISCO" <<'PY' && ok "umbral_pct=1 en $DISCO (copia en $BK/disco.json)" || mal "no se pudo cambiar $DISCO"
import json, sys
p = sys.argv[1]; d = json.load(open(p)); d["umbral_pct"] = 1
open(p, "w").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
PY
  ;;
disco-restaurar) disco_restaurar;;
audit-romper)
  sudo chattr +i "$AUDIT" || { mal "chattr +i $AUDIT"; exit 1; }
  ok "$(sudo lsattr "$AUDIT" | cut -c1-40)"
  c=$(login); [ "$c" = 200 ] && ok "login auditado con el audit de fichero inmutable: HTTP $c (Vault sigue con el de syslog)" \
    || mal "login con el audit de fichero inmutable: HTTP $c (se esperaba 200)";;
audit-restaurar)
  sudo chattr -i "$AUDIT" 2>/dev/null; a=$(sudo lsattr "$AUDIT" | cut -c1-22)
  case "$a" in *i*) mal "$AUDIT sigue inmutable ($a)";; *) ok "$AUDIT escribible otra vez ($a)";; esac;;
clave-copiar)
  sudo install -m 0600 "$CLAVE" "$COPIA"; r=$?; sudo rm -f "$COPIA"
  [ "$r" = 0 ] && ok "copiada $CLAVE a $COPIA y borrada la copia" || mal "sudo install $CLAVE rc=$r";;
clave-intento)
  sudo -u nobody cat "$CLAVE" > /dev/null 2>&1; r=$?
  [ "$r" != 0 ] && ok "nobody no pudo leer $CLAVE (rc=$r, el intento queda para Falco)" || mal "nobody LEYÓ $CLAVE";;
etcd-parar)   sudo systemctl stop etcd && ok "etcd parado" || mal "systemctl stop etcd";;
etcd-arrancar)
  sudo systemctl start etcd && systemctl is-active --quiet etcd && ok "etcd en marcha" || mal "etcd no arranca";;
falco-lineas)  # wc con la ruta como argumento: con "sudo wc -l < f" la redirección la abre vagrant (medido DAY322)
  n=$(sudo wc -l "$EVENTOS" 2>/dev/null | awk '{print $1}')
  [[ "$n" =~ ^[0-9]+$ ]] && echo "E2E|LINEAS|$n" || mal "no leo el nº de líneas de $EVENTOS";;
restaurar)
  sudo rm -f "$PRUEBA" "$COPIA"
  sudo chattr -i "$AUDIT" 2>/dev/null
  disco_restaurar
  systemctl is-active --quiet etcd || sudo systemctl start etcd
  systemctl is-active --quiet vault.service && sudo systemctl start argus-vault-unseal.service
  ok "VM etcd restaurada: sin $PRUEBA ni $COPIA, audit escribible, disco.json original, etcd y Vault en marcha";;
*) echo "uso: $0 fim-crear|fim-borrar|disco-bajar|disco-restaurar|audit-romper|audit-restaurar|clave-copiar|clave-intento|etcd-parar|etcd-arrancar|falco-lineas|restaurar"; exit 2;;
esac
