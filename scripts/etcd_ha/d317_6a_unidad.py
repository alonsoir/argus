#!/usr/bin/env python3
# d317_6a_unidad.py — paso 6a de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): aprovisionador etcd-server-unit en la VM etcd del
# Vagrantfile (ml-defender-etcd-server.service: el etcd-server de la VM como servicio systemd). docs/ml-heads/day312_diseno.md
# Uso:  python3 d317_6a_unidad.py --check <raiz_repo>
#       python3 d317_6a_unidad.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si el Vagrantfile está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

RUTA = 'Vagrantfile'
SHA_PREVIO = '28abbe30b9ed1c368be76a5b4475b39252c96722bfe3b474df9eb6983542c6ce'
SHA_FINAL = 'd2d634a32d1e6c6e026477ebcb97a6c00f7b8bb7114837cb226e85383f28935f'
MARCA = '[ETCD-SERVER-UNIT-D317]'
ANCLA = '  end  # End etcd VM\n'
BLOQUE = '    # [ETCD-SERVER-UNIT-D317] DEBT-ETCD-HA-TLS-RAFT-001 paso 6a (decisión 5 de Alonso, DAY317): el etcd-server corre aquí como\n    # servicio systemd, junto a etcd y Vault. El binario y el JSON NO los pone Vagrant (el binario se compila en el defender\n    # tras bootstrap): los dejan d312_etcd_vm_deploy.sh y make deploy-configs. Sin ellos la unidad queda habilitada pero\n    # no arranca (ConditionPathExists): un up desde cero no falla antes del despliegue. run: always: la unidad sigue al\n    # Vagrantfile; si cambia, daemon-reload y reinicio solo si estaba activa. docs/ml-heads/day312_diseno.md, paso 6\n    etcd.vm.provision "shell", name: "etcd-server-unit", run: "always", inline: <<-\'ETCD_SERVER_UNIT\'\n      set -e\n      U=ml-defender-etcd-server.service\n      BIN=/opt/argus/etcd-server/bin/etcd-server\n      JSON=/etc/ml-defender/etcd-server/etcd-server.json\n      echo "=== etcd VM: etcd-server como servicio systemd [ETCD-SERVER-UNIT-D317] ==="\n      NUEVA=$(mktemp --suffix=.service)\n      cat > "$NUEVA" <<\'UNIT\'\n# [ETCD-SERVER-UNIT-D317] generado por el Vagrantfile; no editar a mano. docs/ml-heads/day312_diseno.md, paso 6\n[Unit]\nDescription=aRGus etcd-server (fachada HTTPS + mTLS; registro en etcd, claves HMAC en Vault) [ETCD-SERVER-UNIT-D317]\nAfter=network-online.target etcd.service vault.service argus-vault-unseal.service\nWants=network-online.target etcd.service vault.service argus-vault-unseal.service\nConditionPathExists=/opt/argus/etcd-server/bin/etcd-server\nConditionPathExists=/etc/ml-defender/etcd-server/etcd-server.json\n# Nunca se rinde: el pipeline necesita su etcd-server en cuanto pueda volver (sin límite de reinicios)\nStartLimitIntervalSec=0\n[Service]\nType=simple\nUser=root\nGroup=root\nEnvironment=LD_PRELOAD=\nEnvironment=LD_LIBRARY_PATH=/opt/argus/etcd-server/lib\nExecStart=/opt/argus/etcd-server/bin/etcd-server -c /etc/ml-defender/etcd-server/etcd-server.json\nRestart=always\nRestartSec=5s\nTimeoutStopSec=30s\nKillSignal=SIGTERM\nStandardOutput=journal\nStandardError=journal\nSyslogIdentifier=ml-defender-etcd-server\n[Install]\nWantedBy=multi-user.target\nUNIT\n      # systemd-analyze verify da rc 0 con directivas mal escritas: se decide por la salida (sin binario aún, se tolera solo eso)\n      VER=$(systemd-analyze verify "$NUEVA" 2>&1 | grep -v -E "Command $BIN is not executable" || true)\n      [ -z "$VER" ] || { echo "$VER"; rm -f "$NUEVA"; echo "❌ etcd-server-unit: systemd-analyze verify (arriba)"; exit 1; }\n      CAMBIA=1\n      if [ -f "/etc/systemd/system/$U" ] && cmp -s "$NUEVA" "/etc/systemd/system/$U"; then CAMBIA=0; fi\n      install -m 0644 -o root -g root "$NUEVA" "/etc/systemd/system/$U"; rm -f "$NUEVA"\n      systemctl daemon-reload\n      systemctl enable "$U" > /dev/null 2>&1\n      systemctl is-enabled "$U" | grep -qx enabled || { echo "❌ etcd-server-unit: $U no quedó habilitada"; exit 1; }\n      if [ ! -x "$BIN" ] || [ ! -f "$JSON" ]; then\n        echo "✅ etcd-server-unit: $U instalada y habilitada; sin arrancar: falta $([ -x "$BIN" ] || echo "$BIN ")$([ -f "$JSON" ] || echo "$JSON ")(despliegue: make etcd-vm-deploy desde el Mac)"\n        exit 0\n      fi\n      # Otro proceso en el 2379 (p. ej. uno lanzado a mano con d313_es_vm.sh) haría fallar la unidad en bucle: se para aquí\n      if ! systemctl is-active --quiet "$U" && ss -ltnH \'sport = :2379\' | grep -q .; then\n        ss -ltnpH \'sport = :2379\'\n        echo "❌ etcd-server-unit: el 2379 lo ocupa otro proceso (arriba). Si es el de d313_es_vm.sh: bash /vagrant/scripts/etcd_ha/d313_es_vm.sh parar"\n        exit 1\n      fi\n      if [ "$CAMBIA" = 1 ] && systemctl is-active --quiet "$U"; then\n        systemctl restart "$U"; echo "etcd-server-unit: la unidad cambió; reiniciada"\n      else\n        systemctl start "$U"\n      fi\n      ok=0; for i in $(seq 1 30); do\n        if systemctl is-active --quiet "$U" && ss -ltnpH \'sport = :2379\' | grep -q \'"etcd-server"\'; then ok=1; break; fi\n        sleep 1\n      done\n      [ "$ok" = 1 ] || { journalctl -u "$U" -n 20 --no-pager; echo "❌ etcd-server-unit: $U no escucha en 2379 a los 30 s (arriba el journal)"; exit 1; }\n      echo "✅ etcd-server-unit: $U activa, pid $(systemctl show -p MainPID --value "$U"), escucha $(ss -ltnH \'sport = :2379\' | awk \'{print $4}\' | tr \'\\n\' \' \')"\n    ETCD_SERVER_UNIT\n\n'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    f = os.path.join(raiz, RUTA)
    if not os.path.isfile(f):
        print('FALLA: no existe %s; no se toca nada.' % f); return 1
    b = open(f, 'rb').read()
    if sha(b) == SHA_FINAL:
        print('YA APLICADO: %s ya tiene el aprovisionador etcd-server-unit; no se toca nada.' % RUTA); return 0
    if MARCA.encode() in b:
        print('FALLA: %s tiene la marca %s pero no el contenido esperado; no se toca nada.' % (RUTA, MARCA)); return 1
    if sha(b) != SHA_PREVIO:
        print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (RUTA, sha(b)[:16])); return 1
    t = b.decode('utf-8')
    if t.count(ANCLA) != 1:
        print('FALLA: el ancla aparece %d veces; no se toca nada.' % t.count(ANCLA)); return 1
    nuevo = t.replace(ANCLA, BLOQUE + ANCLA).encode('utf-8')
    if sha(nuevo) != SHA_FINAL:
        print('FALLA: el resultado no da el sha256 final; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: %s, se añaden %d líneas antes del final de la VM etcd.' % (RUTA, BLOQUE.count('\n'))); return 0
    tmp = f + '.d317tmp'
    with open(tmp, 'wb') as o: o.write(nuevo)
    os.chmod(tmp, os.stat(f).st_mode & 0o7777); os.replace(tmp, f)
    if sha(open(f, 'rb').read()) != SHA_FINAL:
        print('FALLA tras escribir %s' % RUTA); return 1
    print('APLICADO: %s (sha256 %s).' % (RUTA, SHA_FINAL[:16])); return 0

if __name__ == '__main__':
    sys.exit(main())
