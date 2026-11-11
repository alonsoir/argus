#!/usr/bin/env python3
# d317_p8d_apt_espera.py — paso 8 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317): aprovisionador global apt-espera en el Vagrantfile
# (espera al unattended-upgrades del arranque y DPkg::Lock::Timeout=600: EMECAS no falla al azar por el bloqueo de dpkg).
# Uso:  python3 d317_p8d_apt_espera.py --check <raiz_repo>
#       python3 d317_p8d_apt_espera.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si el fichero está en el estado previo exacto y el resultado da el sha256 final.
import hashlib, os, sys

RUTA = 'Vagrantfile'
SHA_PREVIO = 'd2d634a32d1e6c6e026477ebcb97a6c00f7b8bb7114837cb226e85383f28935f'
SHA_FINAL = 'e4d7b23b3086a49ecde8b1d138a31189c92ddec584544357479f6d5371476309'
CAMBIOS = [('Vagrant.configure("2") do |config|\n\n', 'Vagrant.configure("2") do |config|\n\n  # [APT-ESPERA-D317] determinismo de EMECAS: en una VM recién arrancada, unattended-upgrades coge el bloqueo de dpkg y un\n  # apt-get/dpkg de cualquier aprovisionador falla al azar (medido DAY317 en client-setup y DAY315 en d312). Va a nivel de\n  # config (no por VM): Vagrant lo ejecuta el primero en cada VM y en cada up. Espera a que acabe el unattended-upgrades\n  # en curso (hasta 600 s; cubre también el dpkg -i del agente de Wazuh) y deja DPkg::Lock::Timeout para que todo apt-get\n  # posterior espere al bloqueo en vez de fallar. unattended-upgrades sigue activo (DEBT-DEBIAN-BASE-SECURITY-001).\n  config.vm.provision "shell", name: "apt-espera", run: "always", inline: <<-\'APT_ESPERA\'\n    set -u\n    C=/etc/apt/apt.conf.d/80argus-espera-dpkg\n    echo \'DPkg::Lock::Timeout "600";  // [APT-ESPERA-D317] generado por el Vagrantfile; no editar a mano\' > "$C"\n    T0=$(date +%s); n=0\n    while pgrep -f \'/usr/bin/unattended-upgrade|apt.systemd.daily\' > /dev/null && [ "$n" -lt 600 ]; do sleep 2; n=$((n + 2)); done\n    if pgrep -f \'/usr/bin/unattended-upgrade|apt.systemd.daily\' > /dev/null; then\n      echo "⚠️  apt-espera: unattended-upgrades sigue activo tras 600 s; los apt-get esperarán al bloqueo (DPkg::Lock::Timeout)"\n    else\n      echo "✅ apt-espera: dpkg libre tras $(( $(date +%s) - T0 )) s; DPkg::Lock::Timeout=600 en $C"\n    fi\n  APT_ESPERA\n\n', 1)]
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
        tmp = p(r) + '.d317tmp'
        with open(tmp, 'wb') as o: o.write(c.encode('utf-8'))
        os.chmod(tmp, 0o755); os.replace(tmp, p(r)); print('  creado   %s' % r)
    tmp = p(RUTA) + '.d317tmp'
    with open(tmp, 'wb') as o: o.write(nuevo)
    os.chmod(tmp, os.stat(p(RUTA)).st_mode & 0o7777); os.replace(tmp, p(RUTA))
    print('APLICADO: %s (sha256 %s)%s.' % (RUTA, SHA_FINAL[:16], ''.join(' + %s' % r for r in NUEVOS))); return 0

if __name__ == '__main__':
    sys.exit(main())
