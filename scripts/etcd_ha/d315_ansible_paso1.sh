#!/usr/bin/env bash
# [ANSIBLE-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001, paso 1 (plan aprobado por Alonso DAY314, decisiones DAY315).
#   1. BORRAR: plantillas completas de sniffer y ml-detector (DAY161) y sus tareas en deploy_configs.yml, duplicados
#      ansible/group_vars/dev.yml y prod.yml, y las variables que solo las plantillas leían (DAY315: borrarlas).
#   2. DESPUÉS: mover ansible/group_vars/ junto al inventario (ansible/inventory/group_vars/), donde Ansible las carga.
#   En ese orden, para que nunca pueda correr la versión que sobrescribe los JSON del repo.
#   3. Makefile (deploy-configs, deploy-configs-prod) y Jenkinsfile.prod: fuera el -e @group_vars (ruta que deja de
#      existir) y el vault_token_secret (ya no lo lee nada). El playbook conserva su nombre (DAY315): en el paso 2 se
#      rellena con la configuración del etcd-server.
# Uso (en el defender):  bash d315_ansible_paso1.sh --check [RAIZ]   |   bash d315_ansible_paso1.sh --apply [RAIZ]
# RAIZ por defecto: /vagrant. No toca git: los cambios quedan en el árbol para que Alonso los revise y los commitee.
set -euo pipefail
export LC_ALL=C

MODO=${1:-}
RAIZ=${2:-/vagrant}
case "$MODO" in --check|--apply) ;; *) echo "uso: $0 --check|--apply [RAIZ]"; exit 2 ;; esac
cd "$RAIZ"

A=ansible
GV_VIEJO=$A/group_vars
GV_NUEVO=$A/inventory/group_vars
PLAYBOOK=$A/playbooks/deploy_configs.yml

# Huellas de los ficheros que se borran o reescriben (rama feat/etcd-mtls-vault, 8f41d7f3)
declare -A SHA=(
  [$A/templates/sniffer.json.j2]=37aa2500f8006fa6e965a5de96e584923302d4f8aacb09f86aca73928ca0cdab
  [$A/templates/ml_detector_config.json.j2]=0146c64df417beb4141de2f33202428b10217f2e4c1245e93a4beb5e199bf5c8
  [$PLAYBOOK]=4c8674ed34d7539fd49a2752e371cbda2354970243c69cd7590a8cc6993bb02b
  [$GV_VIEJO/dev.yml]=76d66054424d594b2e0db858c45cd8b3eb1f031dc7575aa2cb00d5cb237dca3b
  [$GV_VIEJO/prod.yml]=87b4aa20c555bc9fefc90c1933145d445587ee99aab5ce12b56f7e09f70d167f
  [$GV_VIEJO/argus_dev.yml]=76d66054424d594b2e0db858c45cd8b3eb1f031dc7575aa2cb00d5cb237dca3b
  [$GV_VIEJO/argus_prod.yml]=87b4aa20c555bc9fefc90c1933145d445587ee99aab5ce12b56f7e09f70d167f
)

# Textos exactos que cambian en Makefile y Jenkinsfile.prod (cada uno debe aparecer UNA vez)
MK_DEV_VIEJO=' -e @ansible/group_vars/argus_dev.yml --diff"'
MK_DEV_NUEVO=' --diff"'
MK_PROD_VIEJO=' -e @ansible/group_vars/argus_prod.yml -e vault_token_secret=$${VAULT_TOKEN_SECRET} --diff'
MK_PROD_NUEVO=' --diff'
MK_ECHO_VIEJO='Desplegando configs Ansible/Jinja2'
MK_ECHO_NUEVO='Desplegando configs por entorno (Ansible)'

ya_aplicado() {
  [ ! -e "$A/templates" ] && [ ! -e "$GV_VIEJO" ] && [ -f "$GV_NUEVO/argus_dev.yml" ] \
    && grep -q 'ANSIBLE-D315' "$PLAYBOOK" && grep -q 'ANSIBLE-D315' Jenkinsfile.prod
}

if ya_aplicado; then
  echo "[ANSIBLE-D315] ya aplicado en $RAIZ: nada que hacer"; exit 0
fi

# ---------------------------------------------------------------- comprobaciones previas (--check y --apply)
FALLOS=0
for f in "${!SHA[@]}"; do
  if [ ! -f "$f" ]; then echo "❌ falta $f"; FALLOS=$((FALLOS+1)); continue; fi
  h=$(sha256sum "$f" | cut -d' ' -f1)
  if [ "$h" = "${SHA[$f]}" ]; then echo "✅ $f (${h:0:16})"; else echo "❌ $f: sha256 $h, se esperaba ${SHA[$f]}"; FALLOS=$((FALLOS+1)); fi
done
[ -e "$GV_NUEVO" ] && { echo "❌ $GV_NUEVO ya existe"; FALLOS=$((FALLOS+1)); }
[ "$(ls -A $A/templates | wc -l)" = "2" ] || { echo "❌ $A/templates tiene ficheros que no son las dos plantillas"; FALLOS=$((FALLOS+1)); }
[ "$(ls -A $GV_VIEJO | wc -l)" = "4" ] || { echo "❌ $GV_VIEJO tiene ficheros inesperados"; FALLOS=$((FALLOS+1)); }

contar() { python3 -c 'import sys; print(open(sys.argv[1],encoding="utf-8").read().count(sys.argv[2]))' "$1" "$2"; }
for par in "Makefile|$MK_DEV_VIEJO" "Makefile|$MK_PROD_VIEJO" "Makefile|$MK_ECHO_VIEJO"; do
  f=${par%%|*}; t=${par#*|}; n=$(contar "$f" "$t")
  if [ "$f" = Makefile ] && [ "$t" = "$MK_ECHO_VIEJO" ]; then esperado=2; else esperado=1; fi
  if [ "$n" = "$esperado" ]; then echo "✅ $f: texto a cambiar encontrado $n vez/veces"; else echo "❌ $f: «$t» aparece $n veces (se esperaba $esperado)"; FALLOS=$((FALLOS+1)); fi
done
n=$(contar Jenkinsfile.prod "stage('Deploy Configs — Ansible/Jinja2')")
[ "$n" = 1 ] && echo "✅ Jenkinsfile.prod: etapa Deploy Configs encontrada" || { echo "❌ Jenkinsfile.prod: etapa Deploy Configs aparece $n veces"; FALLOS=$((FALLOS+1)); }

if [ "$FALLOS" != 0 ]; then echo "[ANSIBLE-D315] $FALLOS comprobaciones fallan: no se toca nada"; exit 1; fi
if [ "$MODO" = --check ]; then echo "[ANSIBLE-D315] --check: todo listo para --apply"; exit 0; fi

# ---------------------------------------------------------------- 1. BORRAR (primero)
rm -f "$A/templates/sniffer.json.j2" "$A/templates/ml_detector_config.json.j2"
rmdir "$A/templates"
rm -f "$GV_VIEJO/dev.yml" "$GV_VIEJO/prod.yml"
echo "🗑  plantillas sniffer/ml-detector y group_vars/dev.yml, prod.yml borrados"

cat > "$PLAYBOOK" <<'YML'
---
# aRGus NDR -- Playbook: configuraciones por entorno
# [ANSIBLE-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001 paso 1: se borraron las plantillas completas de sniffer y ml-detector
# (DAY161). Sobrescribían los JSON (medido DAY314: sniffer.json -502/+8 de 561 líneas) y en dev escribían en /vagrant,
# es decir, en los JSON del repo. Paso 2: aquí entra la configuración del etcd-server (el JSON del repo con
# almacen.endpoints y almacen.prefijo sustituidos desde el inventario). DEBT-CONFIG-JINJA2-PIPELINE-001: el mismo patrón
# para sniffer y ml-detector.
# Variables: ansible/inventory/group_vars/<grupo>.yml (Ansible las carga junto al inventario).
# Uso dev:  make deploy-configs        (ansible/inventory/dev.yml)
# Uso prod: make deploy-configs-prod   (ansible/inventory/prod.yml)

- name: aRGus NDR -- configuraciones por entorno
  hosts: all
  gather_facts: false

  tasks:
    - name: "Sin configuraciones que desplegar todavía [ANSIBLE-D315]"
      debug:
        msg: "argus_env={{ argus_env }}: nada que desplegar hasta el paso 2 (etcd-server)"
YML

cat > "$GV_VIEJO/argus_dev.yml" <<'YML'
# aRGus NDR -- group_vars del grupo argus_dev (Vagrant/VirtualBox, x86-64)
# [ANSIBLE-D315] Las variables de las plantillas de sniffer y ml-detector se borraron con ellas
# (DEBT-ANSIBLE-DEPLOY-CONFIGS-001). Las del etcd-server llegan en el paso 2.

argus_env: dev
YML

cat > "$GV_VIEJO/argus_prod.yml" <<'YML'
# aRGus NDR -- group_vars del grupo argus_prod (bare-metal / VM endurecida, producción)
# [ANSIBLE-D315] Las variables de las plantillas de sniffer y ml-detector se borraron con ellas
# (DEBT-ANSIBLE-DEPLOY-CONFIGS-001). Las del etcd-server llegan en el paso 2.

argus_env: prod
YML
echo "✏️  $PLAYBOOK sin plantillas; group_vars solo con argus_env"

# ---------------------------------------------------------------- 2. MOVER (después)
mv "$GV_VIEJO" "$GV_NUEVO"
echo "📦 $GV_VIEJO -> $GV_NUEVO"

# ---------------------------------------------------------------- 3. Makefile y Jenkinsfile.prod
python3 - "$MK_DEV_VIEJO" "$MK_DEV_NUEVO" "$MK_PROD_VIEJO" "$MK_PROD_NUEVO" "$MK_ECHO_VIEJO" "$MK_ECHO_NUEVO" <<'PY'
import sys
dv, dn, pv, pn, ev, en = sys.argv[1:7]
p = "Makefile"
s = open(p, encoding="utf-8").read()
for v, n, c in ((dv, dn, 1), (pv, pn, 1), (ev, en, 2)):
    assert s.count(v) == c, (v, s.count(v))
    s = s.replace(v, n)
open(p, "w", encoding="utf-8").write(s)

p = "Jenkinsfile.prod"
s = open(p, encoding="utf-8").read()
viejo = """        stage('Deploy Configs — Ansible/Jinja2') {
            // Renderiza templates Jinja2 con vars del ambiente y despliega JSONs
            // dev:  inventory/dev.yml (Vagrant)
            // prod: inventory/prod.yml (bare-metal) — requiere FEDER server
            steps {
                script {
                    def inventory = (env.BRANCH_NAME == 'main') ? 'ansible/inventory/prod.yml' : 'ansible/inventory/dev.yml'
                    sh \"\"\"
                        ansible-playbook -i ${inventory} ansible/playbooks/deploy_configs.yml \\
                            --diff \\
                            -e vault_token_secret=\\${VAULT_TOKEN_SECRET:-argus-dev-token}
                    \"\"\"
                }
            }
            post {
                success { echo 'Configs desplegadas correctamente' }
                failure  { echo 'FAIL: deploy_configs.yml — revisar templates Jinja2' }
            }"""
nuevo = """        stage('Deploy Configs — Ansible') {
            // [ANSIBLE-D315] Configuraciones por entorno; variables en ansible/inventory/group_vars/<grupo>.yml
            // dev:  inventory/dev.yml (Vagrant)
            // prod: inventory/prod.yml (bare-metal) — requiere FEDER server
            steps {
                script {
                    def inventory = (env.BRANCH_NAME == 'main') ? 'ansible/inventory/prod.yml' : 'ansible/inventory/dev.yml'
                    sh \"\"\"
                        ansible-playbook -i ${inventory} ansible/playbooks/deploy_configs.yml --diff
                    \"\"\"
                }
            }
            post {
                success { echo 'Configs desplegadas correctamente' }
                failure  { echo 'FAIL: deploy_configs.yml — revisar inventario y group_vars' }
            }"""
assert s.count(viejo) == 1, s.count(viejo)
open(p, "w", encoding="utf-8").write(s.replace(viejo, nuevo))
PY
echo "✏️  Makefile (deploy-configs, deploy-configs-prod) y Jenkinsfile.prod sin -e"

# ---------------------------------------------------------------- comprobaciones finales
set +e; OK=0; MAL=0
chk() { if [ "$2" = 0 ]; then echo "✅ $1"; OK=$((OK+1)); else echo "❌ $1"; MAL=$((MAL+1)); fi; }
[ ! -e "$A/templates" ];                                   chk "sin ansible/templates" $?
[ ! -e "$GV_VIEJO" ];                                     chk "sin ansible/group_vars" $?
[ "$(ls "$GV_NUEVO" | tr '\n' ' ')" = "argus_dev.yml argus_prod.yml " ]; chk "inventory/group_vars = argus_dev.yml argus_prod.yml" $?
! grep -q 'template:' "$PLAYBOOK";                        chk "playbook sin tareas template" $?
! grep -qE 'group_vars|vault_token_secret' Makefile;      chk "Makefile sin group_vars ni vault_token_secret" $?
! grep -q vault_token_secret Jenkinsfile.prod;            chk "Jenkinsfile.prod sin vault_token_secret" $?
! grep -rqE '\b(sniffer_profile|ml_profile|etcd_endpoints|argus_config_base|vault_k_pseudo_path|vault_token_secret)\b' \
    ansible Makefile Jenkinsfile.dev Jenkinsfile.prod;    chk "ansible/, Makefile y Jenkinsfiles no nombran las variables borradas" $?
echo "[ANSIBLE-D315] comprobaciones finales: $OK PASA, $MAL FALLA"
[ "$MAL" = 0 ]
