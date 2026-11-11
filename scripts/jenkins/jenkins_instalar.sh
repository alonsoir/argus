#!/usr/bin/env bash
# scripts/jenkins/jenkins_instalar.sh — [JENKINS-CLAVE-D323] Jenkins en el defender desde el repositorio apt de su
# mantenedor (pkg.jenkins.io), con la clave comprobada por huella (provisioning/jenkins/CLAVE, repo_oficial de
# scripts/vigilancia/lib_apt_oficial.sh), como Wazuh y Falco. Lo llama el aprovisionador all-dependencies del defender.
# Medido DAY323: la clave se pedía a un keyserver de terceros con los errores a /dev/null; no respondió, el anillo quedó
# vacío, apt rechazó el repositorio (NO_PUBKEY 7198F4B714ABFC68), el bloque dijo «✅ Jenkins instalado» sin Jenkins y el
# repositorio roto tumbó el apt-get update de vault-install (EMECAS parado en vagrant-up).
# Decisión de Alonso DAY323: si Jenkins no se puede instalar, se avisa en alto y el lab sigue sin él (EMECAS no usa
# Jenkins), pero SIN dejar configurado un repositorio que rompa los apt-get update siguientes.
# Uso (defender, root): bash /vagrant/scripts/jenkins/jenkins_instalar.sh   (JENKINS_CLAVE=fichero: otras huellas)
# rc: 0 Jenkins instalado (o ya estaba); 3 NO instalado, avisado y con el repositorio retirado; 1 instalado pero sin
#     poder configurarlo o arrancarlo.
set -u
RAIZ=$(cd "$(dirname "$0")/../.." && pwd)
CLAVE=${JENKINS_CLAVE:-$RAIZ/provisioning/jenkins/CLAVE}
URL_CLAVE=https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key
URL_REPO=https://pkg.jenkins.io/debian-stable
JAVA_DIR=/root/.sdkman/candidates/java/21.0.7-tem   # Fix DAY 160: Jenkins 2.555+ requiere Java 21 (SDKMAN + Temurin)
TAG="[JENKINS-INSTALAR]"
instalado() { dpkg-query -W -f='${Status}' jenkins 2>/dev/null | grep -q 'install ok installed'; }
retirar() {
  rm -f /etc/apt/sources.list.d/jenkins.list /usr/share/keyrings/jenkins.gpg /usr/share/keyrings/jenkins-keyring.gpg
  echo "❌ $TAG Jenkins NO instalado: $1. El lab sigue sin Jenkins (EMECAS no lo usa); repositorio retirado para no romper los apt-get update siguientes."
  exit 3
}

if instalado; then
  echo "✅ $TAG Jenkins ya instalado ($(dpkg-query -W -f='${Version}' jenkins)) — asegurando arranque..."
  systemctl start jenkins 2>/dev/null || true
  exit 0
fi
echo "📦 $TAG instalando Jenkins 2.555+ desde $URL_REPO (clave por huella: $CLAVE)"
rm -f /usr/share/keyrings/jenkins-keyring.gpg   # anillo del keyserver de antes de DAY323
# Sin el paquete instalado, un /etc/default/jenkins solo puede ser resto de un intento anterior. Medido DAY323: el
# bloque viejo del Vagrantfile lo escribía aunque Jenkins no se instalara, y al instalar después dpkg se quedó
# preguntando qué hacer con él (pregunta interactiva en un aprovisionamiento: colgado). Fuera.
rm -f /etc/default/jenkins
# shellcheck source=../vigilancia/lib_apt_oficial.sh
. "$RAIZ/scripts/vigilancia/lib_apt_oficial.sh"
repo_oficial jenkins "$URL_CLAVE" "$CLAVE" "$URL_REPO" "binary/" || retirar "la clave de $URL_CLAVE no se pudo comprobar con $CLAVE"
apt-get update -qq || retirar "apt-get update falló con el repositorio de Jenkins"
# Nunca una pregunta de dpkg (DEBIAN_FRONTEND solo cubre debconf): confdef/confold y sin terminal
DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold \
  jenkins < /dev/null || retirar "apt-get install jenkins falló"
instalado || retirar "dpkg no lo da por instalado"

# Fix DAY 160: Jenkins como root en dev, con Java 21 de /root/.sdkman
{ echo "JAVA_HOME=$JAVA_DIR"; echo "JAVA=$JAVA_DIR/bin/java"; } >> /etc/default/jenkins || { echo "❌ $TAG /etc/default/jenkins"; exit 1; }
sed -i 's/^JENKINS_USER=.*/JENKINS_USER=root/; s/^JENKINS_GROUP=.*/JENKINS_GROUP=root/' /etc/default/jenkins
mkdir -p /etc/systemd/system/jenkins.service.d
printf '[Service]\nUser=root\nGroup=root\nEnvironment="JAVA_HOME=%s"\nEnvironment="PATH=%s/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n' \
  "$JAVA_DIR" "$JAVA_DIR" > /etc/systemd/system/jenkins.service.d/java21.conf
systemctl daemon-reload
systemctl enable jenkins || { echo "❌ $TAG systemctl enable jenkins"; exit 1; }
systemctl start jenkins || { echo "❌ $TAG systemctl start jenkins"; exit 1; }
echo "✅ $TAG Jenkins $(dpkg-query -W -f='${Version}' jenkins) instalado (puerto 8080)"
echo "⚠️  Password inicial: sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
