#!/usr/bin/env bash
# [INVENTARIO-FUERA-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001, paso 2c: inventarios de preproducción y producción.
#   Decisiones de Alonso DAY315: (a) el repo es público: los inventarios reales viven FUERA (operador o Jenkins) y en el
#   repo solo hay un ejemplo con datos ficticios; (b) un inventario sin máquinas del etcd-server FALLA, nunca un éxito vacío.
#   1. ansible/inventory/ejemplo-preprod/{hosts.yml,group_vars/argus_preprod.yml}: tres miembros con direcciones de
#      documentación (RFC 5737, 192.0.2.x), usuario argus-deploy con huella verificada, prefijo propio del despliegue.
#   2. Se borran ansible/inventory/prod.yml y ansible/inventory/group_vars/argus_prod.yml (un inventario de fuera trae su
#      propio group_vars: estos no los cargaría nadie).
#   3. Playbook: primer play en localhost que exige el grupo etcd_servers con al menos una máquina.
#   4. Makefile deploy-configs-prod: INVENTARIO=<ruta> obligatorio. Jenkinsfile.prod: en main, env.ARGUS_INVENTARIO
#      obligatorio (error si falta); las demás ramas, dev.yml.
#   5. scripts/etcd_ha/d312_etcd_vm_deploy.sh: apt-get espera al bloqueo de dpkg hasta 600 s (DPkg::Lock::Timeout;
#      medido DAY315: unattended-upgrades lo tenía tras arrancar la VM y el despliegue se cayó).
# Requiere los pasos 1, 2a y 2b aplicados. No toca git.
# Uso (en el defender):  bash d315_ansible_paso2c.sh --check [RAIZ]   |   bash d315_ansible_paso2c.sh --apply [RAIZ]
set -euo pipefail
export LC_ALL=C

MODO=${1:-}
RAIZ=${2:-/vagrant}
case "$MODO" in --check|--apply) ;; *) echo "uso: $0 --check|--apply [RAIZ]"; exit 2 ;; esac
cd "$RAIZ"

PB=ansible/playbooks/deploy_configs.yml
D312=scripts/etcd_ha/d312_etcd_vm_deploy.sh
EJ=ansible/inventory/ejemplo-preprod
declare -A SHA=(
  [$PB]=791a3520912c80295e5034bbd099ef0013a1d50c02287bec3a1c7f924eba329e
  [$D312]=cd6c74a39d53989701c60c6aae2b62a3cf1a5cda8c8301abff2b7770770c447c
  [ansible/inventory/prod.yml]=f1e3ab4460fcded7bfa5f74f6d8c00fd82a7ef58cfceee337fe68082cab16c74
  [ansible/inventory/group_vars/argus_prod.yml]=45025ce7241d76e1235f14aa8cad7270b6c2ae61c3e5ae2ceeb1bede353c3506
)

MK_VIEJO='deploy-configs-prod:
	@echo "🚀 Desplegando configs por entorno (Ansible) (prod)..."
	@ansible-playbook -i ansible/inventory/prod.yml ansible/playbooks/deploy_configs.yml --diff
'
MK_NUEVO='# [INVENTARIO-FUERA-D315] preproducción/producción: el inventario NO está en este repo (es público). Uso:
#   make deploy-configs-prod INVENTARIO=/ruta/fuera/del/repo/hosts.yml   (forma: ansible/inventory/ejemplo-preprod/)
deploy-configs-prod:
	@test -n "$(INVENTARIO)" || { echo "[ETCD-CONFIG-ENTORNO] falta INVENTARIO=<ruta del inventario de preproducción o producción, fuera de este repo; forma en ansible/inventory/ejemplo-preprod/>"; exit 1; }
	@test -f "$(INVENTARIO)" || { echo "[ETCD-CONFIG-ENTORNO] INVENTARIO=$(INVENTARIO) no existe"; exit 1; }
	@echo "🚀 Desplegando configs por entorno (Ansible) ($(INVENTARIO))..."
	@ansible-playbook -i "$(INVENTARIO)" ansible/playbooks/deploy_configs.yml --diff
'
JK_VIEJO="            // dev:  inventory/dev.yml (Vagrant)
            // prod: inventory/prod.yml (bare-metal) — requiere FEDER server
            steps {
                script {
                    def inventory = (env.BRANCH_NAME == 'main') ? 'ansible/inventory/prod.yml' : 'ansible/inventory/dev.yml'
"
JK_NUEVO="            // dev:  inventory/dev.yml (Vagrant)
            // [INVENTARIO-FUERA-D315] main: el inventario de producción NO está en el repo (es público); llega en
            // ARGUS_INVENTARIO (p. ej. una credencial de tipo fichero). Forma: ansible/inventory/ejemplo-preprod/
            steps {
                script {
                    def inventory = 'ansible/inventory/dev.yml'
                    if (env.BRANCH_NAME == 'main') {
                        if (!env.ARGUS_INVENTARIO?.trim()) {
                            error('[ETCD-CONFIG-ENTORNO] main despliega con el inventario de producción: falta ARGUS_INVENTARIO (ruta fuera del repo)')
                        }
                        inventory = env.ARGUS_INVENTARIO
                    }
"
APT_VIEJO="apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq"
APT_NUEVO="apt-get -o DPkg::Lock::Timeout=600 update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=600 install -y -qq"

if [ -d "$EJ" ] && [ ! -e ansible/inventory/prod.yml ] && grep -q 'INVENTARIO-FUERA-D315' "$PB" Makefile Jenkinsfile.prod "$D312" 2>/dev/null \
   && [ "$(grep -l 'INVENTARIO-FUERA-D315' "$PB" Makefile Jenkinsfile.prod "$D312" | wc -l)" = 4 ]; then
  echo "[INVENTARIO-FUERA-D315] ya aplicado en $RAIZ: nada que hacer"; exit 0
fi

FALLOS=0
ok()  { echo "✅ $*"; }
mal() { echo "❌ $*"; FALLOS=$((FALLOS+1)); }
grep -q 'ETCD-CONFIG-ENTORNO-D315' "$PB" && ok "paso 2b aplicado" || mal "falta el paso 2b (d315_ansible_paso2b.sh)"
for f in "${!SHA[@]}"; do
  if [ ! -f "$f" ]; then mal "falta $f"; continue; fi
  h=$(sha256sum "$f" | cut -d' ' -f1)
  [ "$h" = "${SHA[$f]}" ] && ok "$f (${h:0:16})" || mal "$f: sha256 $h, se esperaba ${SHA[$f]}"
done
[ -e "$EJ" ] && mal "$EJ ya existe" || ok "$EJ no existe todavía"
contar() { python3 -c 'import sys; print(open(sys.argv[1],encoding="utf-8").read().count(sys.argv[2]))' "$1" "$2"; }
n=$(contar Makefile "$MK_VIEJO");         [ "$n" = 1 ] && ok "Makefile: deploy-configs-prod encontrado" || mal "Makefile: deploy-configs-prod aparece $n veces"
n=$(contar Jenkinsfile.prod "$JK_VIEJO"); [ "$n" = 1 ] && ok "Jenkinsfile.prod: elección del inventario encontrada" || mal "Jenkinsfile.prod: elección del inventario aparece $n veces"
n=$(contar "$D312" "$APT_VIEJO");         [ "$n" = 1 ] && ok "d312: apt-get encontrado" || mal "d312: apt-get aparece $n veces"

if [ "$FALLOS" != 0 ]; then echo "[INVENTARIO-FUERA-D315] $FALLOS comprobaciones fallan: no se toca nada"; exit 1; fi
if [ "$MODO" = --check ]; then echo "[INVENTARIO-FUERA-D315] --check: todo listo para --apply"; exit 0; fi

# ---------------------------------------------------------------- 1. ejemplo
mkdir -p "$EJ/group_vars"
cat > "$EJ/hosts.yml" <<'YML'
# aRGus NDR -- inventario de EJEMPLO para preproducción/producción [INVENTARIO-FUERA-D315]
# DATOS FICTICIOS: direcciones de documentación (RFC 5737, 192.0.2.0/24), que no existen en ninguna red real.
# Los inventarios de verdad NO van en este repo (es público: IPs, máquinas y prefijos de hospitales y plantas). Copiar
# este directorio fuera del repo, rellenarlo y pasarlo con:
#   make deploy-configs-prod INVENTARIO=/ruta/hosts.yml      (o ARGUS_INVENTARIO en Jenkins, rama main)
# Un despliegue = un clúster etcd (al menos uno por hospital). etcd_servers lleva las máquinas donde corre el
# etcd-server (cada una con su miembro etcd al lado); la lista de miembros que usa el etcd-server está en group_vars.
# Acceso: el usuario argus-deploy con la clave de despliegue de Jenkins y la huella de cada máquina verificada
# (StrictHostKeyChecking=yes; ansible_host_key_checking: true porque ansible.cfg lleva host_key_checking = False).
all:
  children:
    argus_preprod:
      children:
        etcd_servers:
          hosts:
            etcd-1:
              ansible_host: 192.0.2.11
            etcd-2:
              ansible_host: 192.0.2.12
            etcd-3:
              ansible_host: 192.0.2.13
      vars:
        ansible_user: argus-deploy
        ansible_ssh_private_key_file: /root/.ssh/argus_deploy_ed25519
        ansible_host_key_checking: true
        ansible_ssh_common_args: "-o UserKnownHostsFile=/etc/argus-deploy/known_hosts -o StrictHostKeyChecking=yes"
YML
cat > "$EJ/group_vars/argus_preprod.yml" <<'YML'
# aRGus NDR -- group_vars del EJEMPLO de preproducción [INVENTARIO-FUERA-D315] (datos ficticios, RFC 5737)
argus_env: preprod

# etcd-server: TODOS los miembros etcd del clúster de este despliegue (el líder lo elige Raft, nunca Jenkins). Sin defecto.
etcd_almacen_endpoints:
  - "https://192.0.2.11:2381"
  - "https://192.0.2.12:2381"
  - "https://192.0.2.13:2381"
# Prefijo de este despliegue: dos plantas en el mismo clúster sin prefijo propio se pisarían en silencio. El rol RBAC
# del etcd-server en etcd tiene que cubrirlo. Formato: empieza y acaba en /, [a-z0-9/-], sin //, hasta 64.
argus_prefijo: "/argus/hospital-ejemplo/planta-1/"
YML
echo "📄 $EJ/hosts.yml y $EJ/group_vars/argus_preprod.yml (datos ficticios)"

# ---------------------------------------------------------------- 2. borrar prod del repo
rm -f ansible/inventory/prod.yml ansible/inventory/group_vars/argus_prod.yml
echo "🗑  ansible/inventory/prod.yml y group_vars/argus_prod.yml borrados"

# ---------------------------------------------------------------- 3, 4 y 5
python3 - "$PB" "$D312" "$MK_VIEJO" "$MK_NUEVO" "$JK_VIEJO" "$JK_NUEVO" "$APT_VIEJO" "$APT_NUEVO" <<'PY'
import sys
pb, d312, mkv, mkn, jkv, jkn, aptv, aptn = sys.argv[1:9]

def cambiar(p, pares):
    s = open(p, encoding="utf-8").read()
    for viejo, nuevo in pares:
        assert s.count(viejo) == 1, (p, viejo[:60], s.count(viejo))
        s = s.replace(viejo, nuevo)
    open(p, "w", encoding="utf-8").write(s)

cambiar(pb, [
    ("# Uso prod: make deploy-configs-prod   (ansible/inventory/prod.yml)\n",
     "# Uso prod: make deploy-configs-prod INVENTARIO=<ruta fuera del repo>   (forma: ansible/inventory/ejemplo-preprod/)\n"
     "\n"
     "# [INVENTARIO-FUERA-D315] nunca un éxito vacío: si el inventario no trae máquinas del etcd-server, se falla aquí.\n"
     "- name: aRGus NDR -- el inventario trae las máquinas del etcd-server\n"
     "  hosts: localhost\n"
     "  gather_facts: false\n"
     "  tasks:\n"
     "    - name: \"El grupo etcd_servers existe y tiene al menos una máquina\"\n"
     "      assert:\n"
     "        that:\n"
     "          - groups['etcd_servers'] is defined\n"
     "          - groups['etcd_servers'] | length > 0\n"
     "        fail_msg: >-\n"
     "          [ETCD-CONFIG-ENTORNO] el inventario {{ ansible_inventory_sources | join(', ') }} no tiene el grupo\n"
     "          etcd_servers o está vacío: no se despliega nada. Forma: ansible/inventory/ejemplo-preprod/\n"
     "        quiet: true\n"),
])
cambiar("Makefile", [(mkv, mkn)])
cambiar("Jenkinsfile.prod", [(jkv, jkn)])
cambiar(d312, [(aptv, aptn)])
s = open(d312, encoding="utf-8").read()
ancla = "# ── 3. VM etcd: paquetes + instalación + verificación ────────────────────────\n"
assert s.count(ancla) == 1
open(d312, "w", encoding="utf-8").write(s.replace(ancla, ancla +
    "# [INVENTARIO-FUERA-D315] apt-get espera hasta 600 s al bloqueo de dpkg (medido DAY315: unattended-upgrades lo tenía\n"
    "# tras arrancar la VM y el despliegue se cayó con 'Could not get lock /var/lib/dpkg/lock-frontend')\n"))
PY
echo "✏️  $PB (play de comprobación), Makefile (INVENTARIO obligatorio), Jenkinsfile.prod (ARGUS_INVENTARIO), $D312 (DPkg::Lock::Timeout)"

set +e; OK=0; MAL=0
chk() { if [ "$2" = 0 ]; then echo "✅ $1"; OK=$((OK+1)); else echo "❌ $1"; MAL=$((MAL+1)); fi; }
python3 -c '
import yaml,sys
h=yaml.safe_load(open(sys.argv[1])); g=yaml.safe_load(open(sys.argv[2]))
e=h["all"]["children"]["argus_preprod"]["children"]["etcd_servers"]["hosts"]
assert sorted(e)==["etcd-1","etcd-2","etcd-3"] and all(v["ansible_host"].startswith("192.0.2.") for v in e.values())
assert all(u.startswith("https://192.0.2.") for u in g["etcd_almacen_endpoints"]) and len(g["etcd_almacen_endpoints"])==3
assert g["argus_prefijo"]=="/argus/hospital-ejemplo/planta-1/" and g["argus_env"]=="preprod"' "$EJ/hosts.yml" "$EJ/group_vars/argus_preprod.yml"; chk "ejemplo: 3 miembros RFC 5737 y prefijo propio" $?
[ ! -e ansible/inventory/prod.yml ] && [ ! -e ansible/inventory/group_vars/argus_prod.yml ]; chk "sin prod.yml ni argus_prod.yml" $?
python3 -c 'import yaml,sys; p=yaml.safe_load(open(sys.argv[1])); assert [x["hosts"] for x in p]==["localhost","etcd_servers"]' "$PB"; chk "playbook: localhost (comprobación) y etcd_servers" $?
grep -q 'test -n "$(INVENTARIO)"' Makefile && ! grep -q 'inventory/prod.yml' Makefile; chk "Makefile: INVENTARIO obligatorio, sin prod.yml" $?
grep -q 'ARGUS_INVENTARIO' Jenkinsfile.prod && ! grep -q 'inventory/prod.yml' Jenkinsfile.prod; chk "Jenkinsfile.prod: ARGUS_INVENTARIO, sin prod.yml" $?
[ "$(grep -o 'DPkg::Lock::Timeout=600' "$D312" | wc -l)" = 2 ] && bash -n "$D312"; chk "d312: dos apt-get con DPkg::Lock::Timeout y sintaxis bash" $?
echo "[INVENTARIO-FUERA-D315] comprobaciones finales: $OK PASA, $MAL FALLA"
[ "$MAL" = 0 ]
