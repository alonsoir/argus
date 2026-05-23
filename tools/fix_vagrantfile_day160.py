
import re

with open("/vagrant/Vagrantfile", "r") as f:
    content = f.read()

old = """      # ── Jenkins (DEBT-VAULT-PROVISION-PROD-001) ───────────────────────────
      # CI/CD controller — solo en dev/central, no en nodos edge (ADR-039)
      if ! command -v jenkins &>/dev/null && [ ! -f /etc/init.d/jenkins ]; then
        echo "📦 Instalando Jenkins..."
        apt-get install -y default-jdk-headless 2>&1 | tail -2
        curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key 2>/dev/null \\
          | gpg --dearmor \\
          | tee /usr/share/keyrings/jenkins-keyring.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.gpg] https://pkg.jenkins.io/debian-stable binary/" | \\
          tee /etc/apt/sources.list.d/jenkins.list
        apt-get update -qq
        apt-get install -y jenkins
        systemctl enable jenkins
        echo "✅ Jenkins instalado (puerto 8080)"
        echo "⚠️  Primer arranque requiere: sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
      else
        echo "✅ Jenkins ya instalado"
      fi
      # ── HashiCorp Vault (DEBT-CRYPTO-MATERIAL-STORAGE-001) ─────────────────
      if ! command -v vault &>/dev/null; then
        echo "📦 Instalando HashiCorp Vault..."
        wget -O - https://apt.releases.hashicorp.com/gpg 2>/dev/null | \\
          gpg --dearmor | \\
          tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main" | \\
          tee /etc/apt/sources.list.d/hashicorp.list
        apt-get update -qq
        apt-get install -y vault
        echo "✅ Vault $(vault version | head -1) instalado"
      else
        echo "✅ Vault ya instalado: $(vault version | head -1)"
      fi"""

new = """      # ── HashiCorp Vault (DEBT-CRYPTO-MATERIAL-STORAGE-001) ─────────────────
      # Fix DAY 160: repo hashicorp OK con dearmor directo
      if ! command -v vault &>/dev/null; then
        echo "📦 Instalando HashiCorp Vault..."
        wget -O - https://apt.releases.hashicorp.com/gpg 2>/dev/null | \\
          gpg --dearmor | \\
          tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com bookworm main" | \\
          tee /etc/apt/sources.list.d/hashicorp.list
        apt-get update -qq
        apt-get install -y vault
        echo "✅ Vault $(vault version | head -1) instalado"
      else
        echo "✅ Vault ya instalado: $(vault version | head -1)"
      fi

      # ── Java 21 via SDKMAN (requerido por Jenkins 2.555+) ──────────────────
      # Fix DAY 160: Java 21 no está en repos Bookworm — SDKMAN + Temurin
      # Jenkins 2.555.2 requiere Java 21 mínimo (Java 17 falla silenciosamente)
      if [ ! -f /root/.sdkman/candidates/java/21.0.7-tem/bin/java ]; then
        echo "📦 Instalando prereqs SDKMAN (unzip, zip)..."
        apt-get install -y unzip zip 2>&1 | tail -1
        echo "📦 Instalando SDKMAN..."
        curl -s https://get.sdkman.io | bash
        echo "📦 Instalando Java 21.0.7 Temurin via SDKMAN..."
        source /root/.sdkman/bin/sdkman-init.sh
        sdk install java 21.0.7-tem < /dev/null
        echo "✅ Java 21 Temurin instalado"
      else
        echo "✅ Java 21 Temurin ya instalado"
      fi

      # ── Jenkins (DEBT-VAULT-PROVISION-PROD-001) ───────────────────────────
      # Fix DAY 160: key via keyserver (jenkins.io-2023.key rotada — NO usar)
      # Fix DAY 160: Jenkins 2.555+ requiere Java 21 — JAVA_HOME en defaults
      # Fix DAY 160: Jenkins como root en dev (Java 21 en /root/.sdkman)
      if ! command -v jenkins &>/dev/null && [ ! -f /etc/init.d/jenkins ]; then
        echo "📦 Instalando Jenkins 2.555+..."
        gpg --keyserver keyserver.ubuntu.com --recv-keys 7198F4B714ABFC68 2>/dev/null
        gpg --export 7198F4B714ABFC68 \\
          | tee /usr/share/keyrings/jenkins-keyring.gpg > /dev/null
        echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.gpg] https://pkg.jenkins.io/debian-stable binary/" \\
          | tee /etc/apt/sources.list.d/jenkins.list
        apt-get update -qq
        apt-get install -y jenkins
        echo "JAVA_HOME=/root/.sdkman/candidates/java/21.0.7-tem" >> /etc/default/jenkins
        echo "JAVA=/root/.sdkman/candidates/java/21.0.7-tem/bin/java" >> /etc/default/jenkins
        sed -i 's/^JENKINS_USER=.*/JENKINS_USER=root/' /etc/default/jenkins
        sed -i 's/^JENKINS_GROUP=.*/JENKINS_GROUP=root/' /etc/default/jenkins
        mkdir -p /etc/systemd/system/jenkins.service.d
        printf '[Service]\\nUser=root\\nGroup=root\\nEnvironment="JAVA_HOME=/root/.sdkman/candidates/java/21.0.7-tem"\\nEnvironment="PATH=/root/.sdkman/candidates/java/21.0.7-tem/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\\n' \\
          > /etc/systemd/system/jenkins.service.d/java21.conf
        systemctl daemon-reload
        systemctl enable jenkins
        systemctl start jenkins
        echo "✅ Jenkins instalado (puerto 8080)"
        echo "⚠️  Password inicial: sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
      else
        echo "✅ Jenkins ya instalado — asegurando arranque..."
        systemctl start jenkins 2>/dev/null || true
      fi

      # ── Vault dev mode autostart ────────────────────────────────────────────
      # Fix DAY 160: Vault dev mode es inmem — no persiste entre reinicios
      # Se arranca automáticamente y se recrea secret/argus/crypto
      if ! pgrep -x vault > /dev/null; then
        echo "🔐 Arrancando Vault dev mode..."
        nohup vault server -dev \\
          -dev-root-token-id=argus-dev-token \\
          -dev-listen-address=0.0.0.0:8200 \\
          > /tmp/vault-dev.log 2>&1 &
        sleep 3
        export VAULT_ADDR=http://127.0.0.1:8200
        export VAULT_TOKEN=argus-dev-token
        vault kv put secret/argus/crypto \\
          seed=argus-dev-seed-32bytes-placeholder \\
          provider=vault_crypto > /dev/null 2>&1
        echo "✅ Vault dev OK — token: argus-dev-token — secret/argus/crypto recreado"
      else
        echo "✅ Vault ya corriendo"
      fi"""

if old in content:
    content = content.replace(old, new)
    with open("/vagrant/Vagrantfile", "w") as f:
        f.write(content)
    print("OK: Vagrantfile actualizado con todos los fixes DAY 160")
else:
    print("ERROR: bloque no encontrado")
    # debug
    idx = content.find("Jenkins (DEBT-VAULT")
    print(f"  Jenkins block at char {idx}")
    print(repr(content[idx:idx+200]))
