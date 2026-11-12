#!/usr/bin/env python3
# d323_jenkins_clave.py — (DAY323) [JENKINS-CLAVE-D323]: Jenkins desde pkg.jenkins.io con la clave comprobada por huella
# (repo_oficial, como Wazuh y Falco), en scripts/jenkins/jenkins_instalar.sh; si no se puede instalar, avisa, retira el
# repositorio y el up sigue (rc 3; decisión de Alonso DAY323). Medido DAY323: el keyserver de terceros no respondió, el
# bloque dijo «✅ Jenkins instalado» sin Jenkins y el repositorio roto tumbó el apt-get update de vault-install.
# Antes de este parcheador se escriben a mano (cat) y se verifican scripts/jenkins/jenkins_instalar.sh y
# provisioning/jenkins/CLAVE (nuevos); este comprueba sus sha256 y cambia el bloque de Jenkins del Vagrantfile.
# Requiere d323_reloj_lab.py aplicado (commit 6387cfd75).
# Uso:  python3 d323_jenkins_clave.py --check <raiz_repo>
#       python3 d323_jenkins_clave.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si CADA fichero está en el estado previo exacto y el resultado da su sha256 final.
import hashlib, os, sys

REQUISITOS = {'scripts/jenkins/jenkins_instalar.sh': '079934c47061f7662d7f28fe0bf7c288c034b98f7d68e94ac9f45a272a4eda1a', 'provisioning/jenkins/CLAVE': 'f68d76b0aa24439af9b0b3065e7add12efd6dd2a904c46fe106dcd5ced4c1353'}   # {ruta: sha256} que deben estar ya en su sitio
FICHEROS = {'Vagrantfile': ('d026e01d2120590f0b2f6a89fb84d48a513ddf3b691fe305b6144c59a58dabae', 'ca1afd00c6f68e828ad6228be42c1e8d6cb7b487e835eb38ab5acf695a55f5d1', [('      # ── Jenkins (DEBT-VAULT-PROVISION-PROD-001) ───────────────────────────\n      # Fix DAY 160: key via keyserver (jenkins.io-2023.key rotada — NO usar)\n      # Fix DAY 160: Jenkins 2.555+ requiere Java 21 — JAVA_HOME en defaults\n      # Fix DAY 160: Jenkins como root en dev (Java 21 en /root/.sdkman)\n      if ! command -v jenkins &>/dev/null && [ ! -f /etc/init.d/jenkins ]; then\n        echo "📦 Instalando Jenkins 2.555+..."\n        gpg --keyserver keyserver.ubuntu.com --recv-keys 7198F4B714ABFC68 2>/dev/null\n        gpg --export 7198F4B714ABFC68 \\\n          | tee /usr/share/keyrings/jenkins-keyring.gpg > /dev/null\n        echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.gpg] https://pkg.jenkins.io/debian-stable binary/" \\\n          | tee /etc/apt/sources.list.d/jenkins.list\n        apt-get update -qq\n        apt-get install -y jenkins\n        echo "JAVA_HOME=/root/.sdkman/candidates/java/21.0.7-tem" >> /etc/default/jenkins\n        echo "JAVA=/root/.sdkman/candidates/java/21.0.7-tem/bin/java" >> /etc/default/jenkins\n        sed -i \'s/^JENKINS_USER=.*/JENKINS_USER=root/\' /etc/default/jenkins\n        sed -i \'s/^JENKINS_GROUP=.*/JENKINS_GROUP=root/\' /etc/default/jenkins\n        mkdir -p /etc/systemd/system/jenkins.service.d\n        printf \'[Service]\\nUser=root\\nGroup=root\\nEnvironment="JAVA_HOME=/root/.sdkman/candidates/java/21.0.7-tem"\\nEnvironment="PATH=/root/.sdkman/candidates/java/21.0.7-tem/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\\n\' \\\n          > /etc/systemd/system/jenkins.service.d/java21.conf\n        systemctl daemon-reload\n        systemctl enable jenkins\n        systemctl start jenkins\n        echo "✅ Jenkins instalado (puerto 8080)"\n        echo "⚠️  Password inicial: sudo cat /var/lib/jenkins/secrets/initialAdminPassword"\n      else\n        echo "✅ Jenkins ya instalado — asegurando arranque..."\n        systemctl start jenkins 2>/dev/null || true\n      fi\n', '      # ── Jenkins (DEBT-VAULT-PROVISION-PROD-001) ───────────────────────────\n      # [JENKINS-CLAVE-D323] scripts/jenkins/jenkins_instalar.sh: el repositorio de pkg.jenkins.io con la clave comprobada\n      # por huella (provisioning/jenkins/CLAVE), como Wazuh y Falco; antes, un keyserver de terceros sin comprobar nada\n      # (medido DAY323: no respondió y el bloque dijo «✅ Jenkins instalado» sin Jenkins). rc 3 = Jenkins no instalado,\n      # avisado y con el repositorio retirado: el up sigue (decisión de Alonso DAY323: EMECAS no usa Jenkins). Otro rc\n      # distinto de 0 para el up.\n      bash /vagrant/scripts/jenkins/jenkins_instalar.sh; JK_RC=$?\n      [ "$JK_RC" = 0 ] || [ "$JK_RC" = 3 ] || { echo "❌ [JENKINS-INSTALAR] rc=$JK_RC"; exit 1; }\n', 1)])}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
    for ruta, esperado in REQUISITOS.items():
        if not os.path.isfile(p(ruta)) or sha(open(p(ruta), 'rb').read()) != esperado:
            print('FALLA: %s falta o no tiene el sha256 esperado (%s...); no se toca nada.' % (ruta, esperado[:16])); return 1
        if modo == '--apply' and ruta.endswith(('.py', '.sh')) and not os.access(p(ruta), os.X_OK) and ruta.endswith('.sh'):
            os.chmod(p(ruta), 0o755); print('  chmod 755 %s' % ruta)
    nuevos, ya = {}, []
    for ruta, (previo, final, cambios) in FICHEROS.items():
        if not os.path.isfile(p(ruta)):
            print('FALLA: no existe %s; no se toca nada.' % ruta); return 1
        b = open(p(ruta), 'rb').read()
        if sha(b) == final:
            ya.append(ruta); continue
        if sha(b) != previo:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (ruta, sha(b)[:16])); return 1
        t = b.decode('utf-8')
        for i, (v, n, k) in enumerate(cambios, 1):
            if t.count(v) != k:
                print('FALLA: %s, cambio %d: %d apariciones (se exigen %d); no se toca nada.' % (ruta, i, t.count(v), k)); return 1
            t = t.replace(v, n)
        if sha(t.encode('utf-8')) != final:
            print('FALLA: %s: el resultado no da el sha256 final; no se toca nada.' % ruta); return 1
        nuevos[ruta] = t.encode('utf-8')
    if not nuevos:
        print('YA APLICADO: no se toca nada.'); return 0
    if ya:
        print('FALLA: aplicado a medias (ya: %s); no se toca nada.' % ', '.join(ya)); return 1
    if modo == '--check':
        print('APLICABLE: %s.' % ', '.join('%s (%d cambios)' % (r, len(FICHEROS[r][2])) for r in nuevos)); return 0
    for ruta, nuevo in nuevos.items():
        tmp = p(ruta) + '.d323tmp'
        with open(tmp, 'wb') as o: o.write(nuevo)
        os.chmod(tmp, os.stat(p(ruta)).st_mode & 0o7777); os.replace(tmp, p(ruta))
        print('  escrito  %s (sha256 %s)' % (ruta, FICHEROS[ruta][1][:16]))
    print('APLICADO.'); return 0

if __name__ == '__main__':
    sys.exit(main())
