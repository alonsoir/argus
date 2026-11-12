#!/usr/bin/env python3
# d323_suricata_arranque.py — DEBT-ETCD-HA-TLS-RAFT-001, PR1 (DAY323) [SURICATA-ARRANQUE-D323]: la provisión de Suricata
# lo reinicia cuando ya están las reglas y el yaml, y comprueba en el log del proceso nuevo que captura en eth1 con
# firmas > 0 (si no, la provisión falla); suricata-update con 3 intentos en vez de `|| true`. Medido DAY323: en una VM
# nueva Suricata corría con la configuración de fábrica (eth0, 0 firmas) y mitre-check dio 0 alertas.
# Uso:  python3 d323_suricata_arranque.py --check <raiz_repo>
#       python3 d323_suricata_arranque.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si el fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

RUTA = 'Vagrantfile'
SHA_PREVIO = '9b3ce21a65c049ce1a999a8d6c5832c4227f0974a8a437ab9def6eab4b344c03'
SHA_FINAL = '4d7dac75bbaa271e0ca36250a8136f025c0cbc139b24e1c4bc2c2d7ad25de8cc'
CAMBIOS = [('      suricata-update --no-reload || true\n      echo "Rules: $(find /var/lib/suricata/rules -name \'*.rules\' 2>/dev/null | head -1)"\n', '      # [SURICATA-ARRANQUE-D323] reglas ET Open: hasta 3 intentos; sin reglas la provisión FALLA. Antes era `|| true` y\n      # un fallo de descarga habría pasado en silencio, con Suricata vivo y ciego (0 firmas, medido DAY323).\n      REGLAS=/var/lib/suricata/rules/suricata.rules\n      for intento in 1 2 3; do\n        suricata-update --no-reload && [ -s "$REGLAS" ] && break\n        echo "⚠️  [SURICATA-ARRANQUE] suricata-update, intento $intento: sin reglas; reintento en 10 s"; sleep 10\n      done\n      [ -s "$REGLAS" ] || { echo "❌ [SURICATA-ARRANQUE] sin reglas tras 3 intentos de suricata-update"; exit 1; }\n      echo "Rules: $REGLAS ($(wc -l < "$REGLAS") líneas)"\n', 1), ('      mkdir -p /var/log/suricata\n      chown -R suricata:suricata /var/log/suricata 2>/dev/null || true\n\n      echo "=== Suricata ready ==="\n', '      mkdir -p /var/log/suricata\n      chown -R suricata:suricata /var/log/suricata 2>/dev/null || true\n\n      # [SURICATA-ARRANQUE-D323] apt-get install arranca Suricata con la configuración de fábrica (eth0, 0 firmas) y las\n      # reglas y los sed de arriba solo valen al reiniciarlo. Medido DAY323 en una VM nueva: proceso de las 06:11:50,\n      # reglas de las 06:12:15, yaml de las 06:12:58, ningún reinicio -> capturaba en eth0 con 0 firmas y mitre-check\n      # dio 0 alertas. Se reinicia y se comprueba en el log del proceso NUEVO (líneas con su pid): eth1 y firmas > 0.\n      systemctl restart suricata\n      SURI_ESPERA_S=180   # cargar 53 345 firmas tardó 28 s (DAY323); margen para un Mac cargado\n      SURI_LOG=/var/log/suricata/suricata.log\n      PID=0; OK=""\n      for i in $(seq 1 $SURI_ESPERA_S); do\n        PID=$(systemctl show -p MainPID --value suricata)\n        if [ "$PID" != "0" ] && grep -F "[$PID - " "$SURI_LOG" 2>/dev/null | grep -q \'Engine started\'; then OK=1; break; fi\n        sleep 1\n      done\n      [ -n "$OK" ] || { echo "❌ [SURICATA-ARRANQUE] Suricata (pid $PID) sin \'Engine started\' en $SURI_ESPERA_S s"; tail -n 20 "$SURI_LOG"; exit 1; }\n      LINEAS=$(grep -F "[$PID - " "$SURI_LOG")\n      FIRMAS=$(echo "$LINEAS" | grep -o \'[0-9]* signatures processed\' | tail -n 1 | cut -d\' \' -f1)\n      echo "$LINEAS" | grep -q \'eth1: creating\' || { echo "❌ [SURICATA-ARRANQUE] pid $PID no captura en eth1:"; echo "$LINEAS" | grep -i \'creating\'; exit 1; }\n      [ "${FIRMAS:-0}" -gt 0 ] || { echo "❌ [SURICATA-ARRANQUE] pid $PID con ${FIRMAS:-0} firmas"; exit 1; }\n      echo "✅ [SURICATA-ARRANQUE] pid $PID captura en eth1 con $FIRMAS firmas"\n\n      echo "=== Suricata ready ==="\n', 1)]
NUEVOS = {}   # {ruta: contenido} que se crean (0755)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
    if not os.path.isfile(p(RUTA)):
        print('FALLA: no existe %s; no se toca nada.' % RUTA); return 1
    b = open(p(RUTA), 'rb').read()
    nuevos_ya = all(os.path.isfile(p(r)) and open(p(r), 'rb').read() == c.encode() for r, c in NUEVOS.items())
    if sha(b) == SHA_FINAL and nuevos_ya:
        print('YA APLICADO: no se toca nada.'); return 0
    if sha(b) != SHA_PREVIO:
        print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (RUTA, sha(b)[:16])); return 1
    for r in NUEVOS:
        if os.path.exists(p(r)):
            print('FALLA: %s ya existe; no se toca nada.' % r); return 1
    t = b.decode('utf-8')
    for i, (v, n, k) in enumerate(CAMBIOS, 1):
        if t.count(v) != k:
            print('FALLA: cambio %d: %d apariciones (se exigen %d); no se toca nada.' % (i, t.count(v), k)); return 1
        t = t.replace(v, n)
    nuevo = t.encode('utf-8')
    if sha(nuevo) != SHA_FINAL:
        print('FALLA: el resultado no da el sha256 final; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: %s (%d cambios)%s.' % (RUTA, len(CAMBIOS), ''.join(' + %s nuevo' % r for r in NUEVOS))); return 0
    for r, c in NUEVOS.items():
        tmp = p(r) + '.d323tmp'
        with open(tmp, 'wb') as o: o.write(c.encode('utf-8'))
        os.chmod(tmp, 0o755); os.replace(tmp, p(r)); print('  creado   %s' % r)
    tmp = p(RUTA) + '.d323tmp'
    with open(tmp, 'wb') as o: o.write(nuevo)
    os.chmod(tmp, os.stat(p(RUTA)).st_mode & 0o7777); os.replace(tmp, p(RUTA))
    print('APLICADO: %s (sha256 %s)%s.' % (RUTA, SHA_FINAL[:16], ''.join(' + %s' % r for r in NUEVOS))); return 0

if __name__ == '__main__':
    sys.exit(main())
