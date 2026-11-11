#!/usr/bin/env bash
# [DEPLOY-SSH-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001, paso 2a: acceso SSH de despliegue defender -> VM etcd.
#   Decisión de Alonso DAY315: clave propia de despliegue (el modelo de producción: Jenkins con su clave hacia los nodos).
#   1. Vagrantfile, defender: provisioner deploy-key (run: always). Genera /root/.ssh/argus_deploy_ed25519 (root, 0600:
#      Jenkins corre como root en dev) si no existe; la privada nunca sale del defender; la pública se deja en
#      /vagrant/dist/deploy/ (dist/* está en el .gitignore).
#   2. Vagrantfile, etcd: provisioner deploy-access (run: always). Usuario argus-deploy con SOLO esa pública en
#      authorized_keys (se reemplaza, no se añade), sudo sin contraseña (SOLO laboratorio) y huella de la VM publicada en
#      /vagrant/dist/deploy/known_hosts_etcd (el defender la verifica: StrictHostKeyChecking=yes).
#   3. ansible/inventory/dev.yml: host etcd (192.168.100.20, argus-deploy) en argus_dev y en el grupo nuevo etcd_servers.
#   4. Makefile deploy-configs: sudo ansible-playbook (la clave es de root, como Jenkins).
# Requiere el paso 1 aplicado (d315_ansible_paso1.sh). No toca git.
# Uso (en el defender):  bash d315_ansible_paso2a.sh --check [RAIZ]   |   bash d315_ansible_paso2a.sh --apply [RAIZ]
set -euo pipefail
export LC_ALL=C

MODO=${1:-}
RAIZ=${2:-/vagrant}
case "$MODO" in --check|--apply) ;; *) echo "uso: $0 --check|--apply [RAIZ]"; exit 2 ;; esac
cd "$RAIZ"

INV=ansible/inventory/dev.yml
SHA_VAGRANTFILE=3bd4bb2c2c3f35d21cd041a19a31ba7ac1d792295770977814b94e24f194e0df
SHA_INV=acd77098359a73597df6238041efdbae573c19312c651fcb81c079764478ae1b
MK_VIEJO='cd /vagrant && ansible-playbook -i ansible/inventory/dev.yml ansible/playbooks/deploy_configs.yml --diff"'
MK_NUEVO='cd /vagrant && sudo ansible-playbook -i ansible/inventory/dev.yml ansible/playbooks/deploy_configs.yml --diff"'

if grep -q 'DEPLOY-SSH-D315' Vagrantfile && grep -q 'DEPLOY-SSH-D315' "$INV" && grep -qF "$MK_NUEVO" Makefile; then
  echo "[DEPLOY-SSH-D315] ya aplicado en $RAIZ: nada que hacer"; exit 0
fi

FALLOS=0
ok()  { echo "✅ $*"; }
mal() { echo "❌ $*"; FALLOS=$((FALLOS+1)); }
[ -f ansible/inventory/group_vars/argus_dev.yml ] && grep -q ANSIBLE-D315 ansible/playbooks/deploy_configs.yml \
  && ok "paso 1 aplicado" || mal "falta el paso 1 (d315_ansible_paso1.sh)"
h=$(sha256sum Vagrantfile | cut -d' ' -f1); [ "$h" = "$SHA_VAGRANTFILE" ] && ok "Vagrantfile (${h:0:16})" || mal "Vagrantfile: sha256 $h, se esperaba $SHA_VAGRANTFILE"
h=$(sha256sum "$INV" | cut -d' ' -f1);      [ "$h" = "$SHA_INV" ] && ok "$INV (${h:0:16})" || mal "$INV: sha256 $h, se esperaba $SHA_INV"
contar() { python3 -c 'import sys; print(open(sys.argv[1],encoding="utf-8").read().count(sys.argv[2]))' "$1" "$2"; }
for t in "  end  # End defender VM"$'\n' "  end  # End etcd VM"$'\n'; do
  n=$(contar Vagrantfile "$t"); [ "$n" = 1 ] && ok "Vagrantfile: ancla «${t%$'\n'}»" || mal "Vagrantfile: «${t%$'\n'}» aparece $n veces"
done
n=$(contar Makefile "$MK_VIEJO"); [ "$n" = 1 ] && ok "Makefile: deploy-configs encontrado" || mal "Makefile: deploy-configs aparece $n veces"
grep -q '^dist/\*$' .gitignore && ok ".gitignore ignora dist/*" || mal ".gitignore no ignora dist/*"

if [ "$FALLOS" != 0 ]; then echo "[DEPLOY-SSH-D315] $FALLOS comprobaciones fallan: no se toca nada"; exit 1; fi
if [ "$MODO" = --check ]; then echo "[DEPLOY-SSH-D315] --check: todo listo para --apply"; exit 0; fi

python3 - "$MK_VIEJO" "$MK_NUEVO" <<'PY'
import sys
mk_viejo, mk_nuevo = sys.argv[1:3]

DEFENDER = r'''
    # [DEPLOY-SSH-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001 paso 2a: clave de despliegue de Ansible/Jenkins (Jenkins corre
    # como root en dev). Se genera aquí y la privada nunca sale del defender; solo la pública se deja en
    # /vagrant/dist/deploy/ (fuera de git) para que la VM etcd la autorice (provisioner deploy-access). run: always: si el
    # defender se rehace, la clave nueva se publica y basta con: vagrant provision etcd --provision-with deploy-access
    defender.vm.provision "shell", name: "deploy-key", run: "always", inline: <<-'DEPLOY_KEY'
      set -e
      K=/root/.ssh/argus_deploy_ed25519
      install -d -m 0700 -o root -g root /root/.ssh
      if [ ! -f "$K" ]; then
        ssh-keygen -q -t ed25519 -N "" -C "argus-deploy@defender" -f "$K"
        echo "✅ deploy-key: clave de despliegue nueva"
      fi
      chmod 0600 "$K"
      mkdir -p /vagrant/dist/deploy
      cp "$K.pub" /vagrant/dist/deploy/argus_deploy_ed25519.pub
      echo "✅ deploy-key: $(ssh-keygen -lf "$K.pub" | awk '{print $2}') publicada en /vagrant/dist/deploy/ (solo la pública)"
    DEPLOY_KEY
'''

ETCD = r'''
    # [DEPLOY-SSH-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001 paso 2a: usuario argus-deploy para Ansible/Jenkins desde el
    # defender. authorized_keys = SOLO la pública que dejó el provisioner deploy-key del defender (se reemplaza, no se
    # añade); sudo sin contraseña SOLO en el laboratorio (en producción, limitado a lo que se despliega); la huella de esta
    # VM se publica para que el defender la verifique (StrictHostKeyChecking=yes, nada se acepta a ciegas). run: always:
    # sigue a la clave del defender y a la huella de esta VM si cualquiera de las dos se rehace.
    etcd.vm.provision "shell", name: "deploy-access", run: "always", inline: <<-'DEPLOY_ACCESS'
      set -e
      PUB=/vagrant/dist/deploy/argus_deploy_ed25519.pub
      [ -s "$PUB" ] || { echo "❌ deploy-access: falta $PUB (antes, desde el Mac: vagrant provision defender --provision-with deploy-key)"; exit 1; }
      grep -qE '^ssh-ed25519 [A-Za-z0-9+/=]+ argus-deploy@defender$' "$PUB" \
        || { echo "❌ deploy-access: $PUB no es una clave ed25519 de argus-deploy@defender"; exit 1; }
      id argus-deploy >/dev/null 2>&1 || useradd -m -s /bin/bash argus-deploy
      install -d -m 0700 -o argus-deploy -g argus-deploy /home/argus-deploy/.ssh
      install -m 0600 -o argus-deploy -g argus-deploy "$PUB" /home/argus-deploy/.ssh/authorized_keys
      echo 'argus-deploy ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/argus-deploy
      chmod 0440 /etc/sudoers.d/argus-deploy
      visudo -cf /etc/sudoers.d/argus-deploy > /dev/null
      echo "192.168.100.20 $(cut -d' ' -f1,2 /etc/ssh/ssh_host_ed25519_key.pub)" > /vagrant/dist/deploy/known_hosts_etcd
      echo "✅ deploy-access: argus-deploy autoriza $(ssh-keygen -lf "$PUB" | awk '{print $2}'); huella de la VM $(ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub | awk '{print $2}') en /vagrant/dist/deploy/known_hosts_etcd"
    DEPLOY_ACCESS
'''

p = "Vagrantfile"
s = open(p, encoding="utf-8").read()
for ancla, bloque in (("  end  # End defender VM\n", DEFENDER), ("  end  # End etcd VM\n", ETCD)):
    assert s.count(ancla) == 1, ancla
    s = s.replace(ancla, bloque.lstrip("\n") + "\n" + ancla)
open(p, "w", encoding="utf-8").write(s)

p = "ansible/inventory/dev.yml"
open(p, "w", encoding="utf-8").write('''# aRGus NDR -- inventario dev (laboratorio Vagrant)
# [DEPLOY-SSH-D315] Ansible corre en el defender como root (igual que Jenkins): el defender en local y la VM etcd por SSH
# con la clave de despliegue (provisioner deploy-key del defender) y la huella publicada por la VM (provisioner
# deploy-access). El grupo etcd_servers es el que usa el play del etcd-server (paso 2b).
all:
  children:
    argus_dev:
      hosts:
        defender:
          ansible_host: 192.168.56.20
          ansible_user: vagrant
          ansible_connection: local
          ansible_ssh_private_key_file: .vagrant/machines/defender/virtualbox/private_key
          ansible_ssh_common_args: "-o StrictHostKeyChecking=no"
        etcd:
          ansible_host: 192.168.100.20
          ansible_user: argus-deploy
          ansible_ssh_private_key_file: /root/.ssh/argus_deploy_ed25519
          # ansible.cfg lleva host_key_checking = False: sin esta línea Ansible antepone StrictHostKeyChecking=no y ssh se
          # queda con la primera opción (medido DAY315: con una huella falsa conectaba igual)
          ansible_host_key_checking: true
          ansible_ssh_common_args: "-o UserKnownHostsFile=/vagrant/dist/deploy/known_hosts_etcd -o StrictHostKeyChecking=yes"
    etcd_servers:
      hosts:
        etcd:
''')

p = "Makefile"
s = open(p, encoding="utf-8").read()
assert s.count(mk_viejo) == 1
open(p, "w", encoding="utf-8").write(s.replace(mk_viejo, mk_nuevo))
PY
echo "✏️  Vagrantfile (deploy-key en defender, deploy-access en etcd), $INV (etcd + etcd_servers), Makefile (sudo)"

set +e; OK=0; MAL=0
chk() { if [ "$2" = 0 ]; then echo "✅ $1"; OK=$((OK+1)); else echo "❌ $1"; MAL=$((MAL+1)); fi; }
[ "$(grep -c 'name: "deploy-key", run: "always"' Vagrantfile)" = 1 ];    chk "Vagrantfile: deploy-key una vez" $?
[ "$(grep -c 'name: "deploy-access", run: "always"' Vagrantfile)" = 1 ]; chk "Vagrantfile: deploy-access una vez" $?
awk '/name: "deploy-key"/{k=NR} /end  # End defender VM/{d=NR} END{exit !(k && k<d)}' Vagrantfile; chk "deploy-key dentro del bloque defender" $?
awk '/end  # End wazuh VM/{w=NR} /name: "deploy-access"/{a=NR} /end  # End etcd VM/{e=NR} END{exit !(a>w && a<e)}' Vagrantfile; chk "deploy-access dentro del bloque etcd" $?
python3 -c 'import yaml,sys; d=yaml.safe_load(open(sys.argv[1])); c=d["all"]["children"]; h=c["argus_dev"]["hosts"]["etcd"]; assert "etcd" in c["etcd_servers"]["hosts"] and h["ansible_host_key_checking"] is True' "$INV"; chk "$INV: etcd en argus_dev y etcd_servers, con host_key_checking" $?
grep -qF "$MK_NUEVO" Makefile;                                              chk "Makefile: deploy-configs con sudo" $?
echo "[DEPLOY-SSH-D315] comprobaciones finales: $OK PASA, $MAL FALLA"
[ "$MAL" = 0 ]
