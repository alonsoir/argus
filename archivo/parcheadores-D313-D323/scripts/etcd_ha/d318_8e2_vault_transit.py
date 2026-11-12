#!/usr/bin/env python3
# d318_8e2_vault_transit.py — DAY318, ADR-060 paso 8e.2 [PROTEGIDOS-PUBKEY-D318]: Vault transit para firmar el
# manifiesto de protegidos (clave ed25519 por hospital, no exportable), audit device de fichero + syslog con rotación,
# rol argus-infra (OU=argus-infra, separado de admin), argus_hospital_id en group_vars, y la clave pública al defender
# antes de compilar (make protegidos-pubkey, bootstrap [4b/8]). Necesita, ya copiados en scripts/etcd_ha/:
# protegidos_pubkey.sh y protegidos_pubkey_vm.sh.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_8e2_vault_transit.py --check|--apply <raíz>
# Todo o nada e idempotente: cada cambio se aplica si su texto viejo aparece una vez, se da por hecho si ya está el
# nuevo, y cualquier otro caso para sin escribir nada. Imprime el sha256 de cada fichero antes y después.
import hashlib
import os
import sys

VAGRANTFILE = "Vagrantfile"
MAKEFILE = "Makefile"
PKI = "scripts/etcd_ha/d312_pki.sh"
GV_DEV = "ansible/inventory/group_vars/argus_dev.yml"
GV_PRE = "ansible/inventory/ejemplo-preprod/group_vars/argus_preprod.yml"
NUEVOS = ["scripts/etcd_ha/protegidos_pubkey.sh", "scripts/etcd_ha/protegidos_pubkey_vm.sh"]

CAMBIOS = {
    VAGRANTFILE: [
        ("hospital_id desde group_vars",
         'ARGUS_PKI_DIR = ENV.fetch("ARGUS_PKI_DIR", File.join(Dir.home, "argus-pki"))\n',
         'ARGUS_PKI_DIR = ENV.fetch("ARGUS_PKI_DIR", File.join(Dir.home, "argus-pki"))\n'
         '\n'
         '# [PROTEGIDOS-PUBKEY-D318] ADR-060 8e.2: hospital de este despliegue, de su group_vars (el mismo fichero por despliegue\n'
         '# que rellena Jenkins). Nombra la clave transit del manifiesto de protegidos (argus-transit/keys/protegidos-<hospital>):\n'
         '# una clave por hospital. Sin valor válido Vagrant para aquí: no hay defecto sano para la identidad de un hospital.\n'
         'require "yaml"\n'
         'ARGUS_GROUP_VARS = File.expand_path(File.join("ansible", "inventory", "group_vars", "argus_dev.yml"), __dir__)\n'
         'ARGUS_HOSPITAL_ID = ((YAML.safe_load(File.read(ARGUS_GROUP_VARS)) || {})["argus_hospital_id"]).to_s\n'
         'unless ARGUS_HOSPITAL_ID.match?(/\\A[a-z0-9-]{1,64}\\z/)\n'
         '  abort "[PROTEGIDOS-PUBKEY-D318] argus_hospital_id ausente o mal formado en #{ARGUS_GROUP_VARS} " \\\n'
         '        "(formato: [a-z0-9-], de 1 a 64 caracteres; p. ej. hospital-lab)"\n'
         'end\n'),
        ("PKI de argus-infra a la VM etcd",
         "    %w[ca.crt vault.crt vault.key etcd-server.crt etcd-server.key].each do |f|\n",
         "    # [PROTEGIDOS-PUBKEY-D318] argus-infra: certificado que SOLO firma el manifiesto de protegidos (ver d312_pki.sh)\n"
         "    %w[ca.crt vault.crt vault.key etcd-server.crt etcd-server.key argus-infra.crt argus-infra.key].each do |f|\n"),
        ("hospital al aprovisionador vault-server",
         "    etcd.vm.provision \"shell\", name: \"vault-server\", inline: <<-'VAULT_SERVER'\n",
         "    etcd.vm.provision \"shell\", name: \"vault-server\", env: { \"ARGUS_HOSPITAL_ID\" => ARGUS_HOSPITAL_ID },\n"
         "      inline: <<-'VAULT_SERVER'\n"),
        ("instalar el certificado de argus-infra",
         '        install -m 0600 -o root -g root "$PKI_IN/etcd-server.key" /etc/argus-pki/etcd-server.key\n',
         '        install -m 0600 -o root -g root "$PKI_IN/etcd-server.key" /etc/argus-pki/etcd-server.key\n'
         '        # [PROTEGIDOS-PUBKEY-D318] argus-infra (OU=argus-infra) SOLO firma el manifiesto de protegidos (rol de Vault\n'
         '        # argus-infra-admin). No es admin (OU=admin: en el etcd-server rota claves HMAC y lista componentes).\n'
         '        install -m 0644 -o root -g root "$PKI_IN/argus-infra.crt" /etc/argus-pki/argus-infra.crt\n'
         '        install -m 0600 -o root -g root "$PKI_IN/argus-infra.key" /etc/argus-pki/argus-infra.key\n'),
        ("comprobar el certificado de argus-infra y el hospital",
         "      for f in /etc/vault.d/tls/ca.crt /etc/vault.d/tls/vault.crt /etc/vault.d/tls/vault.key /etc/argus-pki/etcd-server.crt /etc/argus-pki/etcd-server.key; do\n"
         "        [ -s \"$f\" ] || { echo \"❌ vault-server: falta $f (¿existe la PKI del lab en el Mac? ARGUS_PKI_DIR)\"; exit 1; }\n"
         "      done\n",
         "      for f in /etc/vault.d/tls/ca.crt /etc/vault.d/tls/vault.crt /etc/vault.d/tls/vault.key /etc/argus-pki/etcd-server.crt /etc/argus-pki/etcd-server.key /etc/argus-pki/argus-infra.crt /etc/argus-pki/argus-infra.key; do\n"
         "        [ -s \"$f\" ] || { echo \"❌ vault-server: falta $f (¿existe la PKI del lab en el Mac? ARGUS_PKI_DIR)\"; exit 1; }\n"
         "      done\n"
         "      [[ \"${ARGUS_HOSPITAL_ID:-}\" =~ ^[a-z0-9-]{1,64}$ ]] || { echo \"❌ vault-server: ARGUS_HOSPITAL_ID '${ARGUS_HOSPITAL_ID:-}' ausente o mal formado ([a-z0-9-], 1 a 64)\"; exit 1; }\n"
         "      CLAVE_PROT=\"protegidos-$ARGUS_HOSPITAL_ID\"\n"),
        ("directorio y rotación del audit",
         "      chown root:vault /etc/vault.d/vault.hcl; chmod 0640 /etc/vault.d/vault.hcl\n",
         "      chown root:vault /etc/vault.d/vault.hcl; chmod 0640 /etc/vault.d/vault.hcl\n"
         "\n"
         "      # [PROTEGIDOS-PUBKEY-D318] directorio del audit device de fichero y su rotación (sin ella el disco se llena seguro).\n"
         "      # Vault reabre el fichero con SIGHUP. Retención del lab: 30 días (en producción la fija la ley de cada hospital).\n"
         "      install -d -m 0750 -o vault -g vault /var/log/vault\n"
         "      command -v logrotate >/dev/null || apt-get install -y logrotate\n"
         "      cat > /etc/logrotate.d/argus-vault-audit <<'LOGROTATE'\n"
         "# [PROTEGIDOS-PUBKEY-D318] generado por el Vagrantfile; no editar a mano\n"
         "/var/log/vault/audit.log {\n"
         "  daily\n"
         "  rotate 30\n"
         "  missingok\n"
         "  notifempty\n"
         "  compress\n"
         "  delaycompress\n"
         "  create 0640 vault vault\n"
         "  postrotate\n"
         "    systemctl kill -s HUP vault.service > /dev/null 2>&1 || true\n"
         "  endscript\n"
         "}\n"
         "LOGROTATE\n"
         "      logrotate -d /etc/logrotate.d/argus-vault-audit > /dev/null 2>&1 \\\n"
         "        || { echo \"❌ vault-server: logrotate rechaza /etc/logrotate.d/argus-vault-audit\"; exit 1; }\n"),
        ("audit antes que nada en el init",
         '        export VAULT_TOKEN="$ROOT"\n',
         '        export VAULT_TOKEN="$ROOT"\n'
         '        # [PROTEGIDOS-PUBKEY-D318] audit ANTES que todo lo demás (también queda auditada la configuración). Dos devices:\n'
         '        # Vault rechaza TODA petición si no puede escribir en ninguno; con dos, un disco lleno en /var/log no lo para.\n'
         '        vault audit enable file file_path=/var/log/vault/audit.log mode=0640 >/dev/null\n'
         '        vault audit enable syslog tag=vault-audit facility=AUTH >/dev/null\n'),
        ("transit, política y rol de argus-infra en el init",
         "          certificate=@/etc/vault.d/tls/ca.crt allowed_common_names=etcd-server token_ttl=3600 >/dev/null\n",
         "          certificate=@/etc/vault.d/tls/ca.crt allowed_common_names=etcd-server token_ttl=3600 >/dev/null\n"
         "        # [PROTEGIDOS-PUBKEY-D318] ADR-060 8e.2: firma del manifiesto de protegidos. Clave ed25519 por hospital, NO\n"
         "        # exportable y sin borrado: la privada nunca sale de Vault. Solo argus-infra (rol argus-infra-admin) firma, y solo\n"
         "        # desde el CIDR autorizado (lab: 127.0.0.1/32, Vault solo escucha ahí; producción: el de la plantilla de despliegue).\n"
         "        vault secrets enable -path=argus-transit transit >/dev/null\n"
         "        vault write -f \"argus-transit/keys/$CLAVE_PROT\" type=ed25519 exportable=false allow_plaintext_backup=false >/dev/null\n"
         "        vault policy write argus-infra-admin - >/dev/null <<POL\n"
         "# [PROTEGIDOS-PUBKEY-D318] argus-infra firma, verifica y lee la clave pública del manifiesto de su hospital; nada más\n"
         "path \"argus-transit/sign/$CLAVE_PROT\"   { capabilities = [\"update\"] }\n"
         "path \"argus-transit/verify/$CLAVE_PROT\" { capabilities = [\"update\"] }\n"
         "path \"argus-transit/keys/$CLAVE_PROT\"   { capabilities = [\"read\"] }\n"
         "POL\n"
         "        vault write auth/cert/certs/argus-infra display_name=argus-infra policies=argus-infra-admin \\\n"
         "          certificate=@/etc/vault.d/tls/ca.crt allowed_common_names=argus-infra \\\n"
         "          token_ttl=300 token_max_ttl=900 token_bound_cidrs=127.0.0.1/32 >/dev/null\n"
         "        printf '%s\\n' \"$CLAVE_PROT\" > /etc/vault.d/argus-protegidos.clave\n"
         "        chmod 0644 /etc/vault.d/argus-protegidos.clave\n"),
        ("mensaje del init",
         '        echo "✅ vault-server: inicializado (1/1), argus-hmac (kv v2), política etcd-server, auth cert; root revocado"\n',
         '        echo "✅ vault-server: inicializado (1/1), audit (fichero + syslog), argus-hmac (kv v2), política etcd-server, auth cert,"\n'
         '        echo "   argus-transit con $CLAVE_PROT (ed25519, no exportable) y rol argus-infra; root revocado"\n'),
        ("sonda de transit y audit en cada aprovisionamiento",
         "      vault status -format=json | python3 -c 'import sys,json; s=json.load(sys.stdin); print(\"✅ vault-server: sealed=%s storage=%s version=%s\" % (s[\"sealed\"], s[\"storage_type\"], s[\"version\"]))'\n",
         "      # [PROTEGIDOS-PUBKEY-D318] sonda en cada aprovisionamiento: con el certificado de argus-infra se lee la clave del\n"
         "      # manifiesto (ed25519, no exportable, sin borrado), y esa lectura tiene que aparecer en los dos audit devices. Un\n"
         "      # Vault inicializado antes de DAY318 no tiene transit y, con el root revocado, no se puede añadir: se rehace.\n"
         "      REHACER=\"Desde el Mac: vagrant destroy -f etcd && vagrant up etcd\"\n"
         "      [ -s /etc/vault.d/argus-protegidos.clave ] || { echo \"❌ vault-server: Vault sin argus-transit (inicializado antes de DAY318). $REHACER\"; exit 1; }\n"
         "      HAY=$(cat /etc/vault.d/argus-protegidos.clave)\n"
         "      [ \"$HAY\" = \"$CLAVE_PROT\" ] || { echo \"❌ vault-server: este Vault firma con $HAY y el despliegue pide $CLAVE_PROT (argus_hospital_id). Un Vault por hospital. $REHACER\"; exit 1; }\n"
         "      N0=$(wc -l < /var/log/vault/audit.log)\n"
         "      audit_syslog() { journalctl -t vault-audit --since \"-15min\" --no-pager 2>/dev/null | grep -c \"argus-transit/keys/$CLAVE_PROT\"; }\n"
         "      S0=$(audit_syslog)\n"
         "      TI=$(VAULT_CLIENT_CERT=/etc/argus-pki/argus-infra.crt VAULT_CLIENT_KEY=/etc/argus-pki/argus-infra.key \\\n"
         "           vault login -method=cert -path=cert -token-only name=argus-infra 2>/dev/null) || { echo \"❌ vault-server: login cert de argus-infra\"; exit 1; }\n"
         "      INFO=$(curl -s --cacert \"$VAULT_CACERT\" --cert /etc/argus-pki/argus-infra.crt --key /etc/argus-pki/argus-infra.key \\\n"
         "        -H \"X-Vault-Token: $TI\" \"https://127.0.0.1:8200/v1/argus-transit/keys/$CLAVE_PROT\")\n"
         "      unset TI\n"
         "      printf '%s' \"$INFO\" | python3 -c '\n"
         "import sys, json\n"
         "d = json.load(sys.stdin)[\"data\"]\n"
         "ver = {k: d.get(k) for k in (\"type\", \"exportable\", \"deletion_allowed\", \"supports_signing\")}\n"
         "if ver != {\"type\": \"ed25519\", \"exportable\": False, \"deletion_allowed\": False, \"supports_signing\": True}:\n"
         "    sys.exit(\"❌ vault-server: la clave del manifiesto no es ed25519 no exportable y sin borrado: %s\" % ver)\n"
         "print(\"✅ vault-server: argus-transit/keys/%s ed25519, exportable=False, deletion_allowed=False, version %s\" % (sys.argv[1], d[\"latest_version\"]))\n"
         "' \"$CLAVE_PROT\" || exit 1\n"
         "      tail -n +\"$((N0 + 1))\" /var/log/vault/audit.log | grep -q \"argus-transit/keys/$CLAVE_PROT\" \\\n"
         "        || { echo \"❌ vault-server: la lectura de la clave no aparece en /var/log/vault/audit.log (audit de fichero sin escribir)\"; exit 1; }\n"
         "      S1=$S0; for i in 1 2 3 4 5; do S1=$(audit_syslog); [ \"$S1\" -gt \"$S0\" ] && break; sleep 1; done\n"
         "      [ \"$S1\" -gt \"$S0\" ] \\\n"
         "        || { echo \"❌ vault-server: la lectura de la clave no aparece en el audit de syslog (journalctl -t vault-audit: $S0 -> $S1)\"; exit 1; }\n"
         "      echo \"✅ vault-server: los dos audit devices escriben (fichero: $(wc -l < /var/log/vault/audit.log) líneas; syslog: vault-audit)\"\n"
         "      vault status -format=json | python3 -c 'import sys,json; s=json.load(sys.stdin); print(\"✅ vault-server: sealed=%s storage=%s version=%s\" % (s[\"sealed\"], s[\"storage_type\"], s[\"version\"]))'\n"),
    ],
    MAKEFILE: [
        ("PHONY",
         ".PHONY: etcd-vm-deploy etcd-vm-estado etcd-vm-check etcd-vm-aviso\n",
         ".PHONY: etcd-vm-deploy etcd-vm-estado etcd-vm-check etcd-vm-aviso protegidos-pubkey\n"
         "\n"
         "# [PROTEGIDOS-PUBKEY-D318] ADR-060 8e.2 (Mac): clave PÚBLICA del manifiesto de protegidos (Vault transit de la VM etcd)\n"
         "# al defender, donde CMake la compila en el firewall-acl-agent (patrón ADR-025). Lee con el certificado de argus-infra.\n"
         "protegidos-pubkey:\n"
         "\t@bash scripts/etcd_ha/protegidos_pubkey.sh\n"),
        ("bootstrap eBPF [4b/8]",
         "\t@$(MAKE) install-systemd-units\n"
         "\t@echo \"[5/8] Compilando pipeline (incluye pubkey runtime + plugin-test-message)...\"\n",
         "\t@$(MAKE) install-systemd-units\n"
         "\t@echo \"[4b/8] Clave pública del manifiesto de protegidos (Vault transit de la VM etcd) al defender...\"\n"
         "\t@$(MAKE) protegidos-pubkey  # [PROTEGIDOS-PUBKEY-D318] antes de compilar: sin ella el firewall no compila (8e.1)\n"
         "\t@echo \"[5/8] Compilando pipeline (incluye pubkey runtime + plugin-test-message)...\"\n"),
        ("bootstrap libpcap [4b/8]",
         "\t@$(MAKE) install-systemd-units\n"
         "\t@echo \"[5/8] Compilando pipeline (incluye Variant B sniffer-libpcap)...\"\n",
         "\t@$(MAKE) install-systemd-units\n"
         "\t@echo \"[4b/8] Clave pública del manifiesto de protegidos (Vault transit de la VM etcd) al defender...\"\n"
         "\t@$(MAKE) protegidos-pubkey  # [PROTEGIDOS-PUBKEY-D318] antes de compilar: sin ella el firewall no compila (8e.1)\n"
         "\t@echo \"[5/8] Compilando pipeline (incluye Variant B sniffer-libpcap)...\"\n"),
    ],
    PKI: [
        ("roles de administración en la cabecera",
         "# Identidad (DAY312): CN = instancia (clave HMAC propia, /secrets/{CN}); OU = rol (permisos de todo el rol).\n",
         "# Identidad (DAY312): CN = instancia (clave HMAC propia, /secrets/{CN}); OU = rol (permisos de todo el rol).\n"
         "# Roles de administración (DAY318, ADR-060), separados a propósito:\n"
         "#   admin        (OU=admin)        operación diaria en el etcd-server: rotar claves HMAC, listar componentes, /info.\n"
         "#                                  NO puede firmar el manifiesto de protegidos.\n"
         "#   argus-infra  (OU=argus-infra)  SOLO firma el manifiesto de protegidos (Vault transit, rol argus-infra-admin) desde\n"
         "#                                  la máquina del admin. Firmar da inmunidad frente a todo bloqueo de aRGus: si se\n"
         "#                                  compromete el certificado de uso diario, el manifiesto sigue a salvo.\n"
         "#   PKI creada antes de DAY318: bash d312_pki.sh cliente DIR argus-infra\n"),
        ("argus-infra en init",
         "    for r in sniffer ml-detector firewall-acl-agent admin; do firmar \"$r\" \"$r\" \"$r\" clientAuth \"\"; done\n",
         "    for r in sniffer ml-detector firewall-acl-agent admin argus-infra; do firmar \"$r\" \"$r\" \"$r\" clientAuth \"\"; done\n"),
    ],
    GV_DEV: [
        ("argus_hospital_id",
         'argus_prefijo: "/argus/"\n',
         'argus_prefijo: "/argus/"\n'
         '\n'
         '# [PROTEGIDOS-PUBKEY-D318] hospital de este despliegue (ADR-060): nombra la clave transit del manifiesto de protegidos\n'
         '# (argus-transit/keys/protegidos-<hospital>, una por hospital) y es el hospital_id del manifiesto. Formato: [a-z0-9-],\n'
         '# de 1 a 64. Sin defecto en ningún sitio: el Vagrantfile para si falta. Lab: hospital-lab (decisión de Alonso DAY318).\n'
         'argus_hospital_id: "hospital-lab"\n'),
    ],
    GV_PRE: [
        ("argus_hospital_id",
         'argus_prefijo: "/argus/hospital-ejemplo/planta-1/"\n',
         'argus_prefijo: "/argus/hospital-ejemplo/planta-1/"\n'
         '# Hospital de este despliegue (ADR-060): nombra su clave transit del manifiesto de protegidos. Formato: [a-z0-9-], 1-64.\n'
         'argus_hospital_id: "hospital-ejemplo"\n'),
    ],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d318_8e2_vault_transit.py --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    errores = []
    for n in NUEVOS:
        if not os.path.isfile(os.path.join(raiz, n)):
            errores.append(f"falta {n}: créalo antes con su bloque cat > ... <<'EOF'")
    orig, nuevo = {}, {}
    hechos, pendientes = [], []
    for rel, cambios in CAMBIOS.items():
        p = os.path.join(raiz, rel)
        if not os.path.isfile(p):
            errores.append(f"no existe {rel}")
            continue
        orig[rel] = open(p, "rb").read()
        print(f"sha256 previo  {rel}: {sha(orig[rel])}")
        t = orig[rel].decode("utf-8")
        for nombre, viejo, nv in cambios:
            cv, cn = t.count(viejo), t.count(nv)
            if cv == 1 and cn == 0:
                t = t.replace(viejo, nv)
                pendientes.append(f"{rel}: {nombre}")
            elif cn == 1:
                hechos.append(f"{rel}: {nombre}")
            else:
                errores.append(f"{rel}: {nombre}: texto viejo {cv} veces, nuevo {cn} veces")
        nuevo[rel] = t.encode("utf-8")
    print(f"ya aplicados ({len(hechos)})")
    for h in hechos:
        print(f"  = {h}")
    print(f"por aplicar  ({len(pendientes)})")
    for h in pendientes:
        print(f"  + {h}")
    if errores:
        for e in errores:
            print(f"FALLA: {e}")
        print("RESULTADO: FALLA (no se ha escrito nada)")
        return 1
    if modo == "--apply":
        for rel in CAMBIOS:
            if nuevo[rel] != orig[rel]:
                p = os.path.join(raiz, rel)
                modo_f = os.stat(p).st_mode
                with open(p + ".d318tmp", "wb") as f:
                    f.write(nuevo[rel])
                os.chmod(p + ".d318tmp", modo_f)
                os.replace(p + ".d318tmp", p)
    for rel in CAMBIOS:
        estado = "igual" if nuevo[rel] == orig[rel] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {rel}: {sha(nuevo[rel])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
