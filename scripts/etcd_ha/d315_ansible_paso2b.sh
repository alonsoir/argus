#!/usr/bin/env bash
# [ETCD-CONFIG-ENTORNO-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001, paso 2b: configuración del etcd-server por entorno.
#   1. ansible/playbooks/deploy_configs.yml: play sobre etcd_servers. Toma etcd-server/config/etcd-server.etcd-vm.json
#      del repo, sustituye SOLO almacen.endpoints y almacen.prefijo con etcd_almacen_endpoints y argus_prefijo del
#      inventario (sin defecto: si faltan, falla) y escribe /etc/ml-defender/etcd-server/etcd-server.json en la máquina
#      del etcd-server, validándolo antes con el propio binario (--check-config: si no da 0, el fichero no se toca).
#   2. ansible/inventory/group_vars/argus_dev.yml: los dos valores del lab (un miembro elegido a mano, prefijo /argus/).
#   3. scripts/etcd_ha/d312_etcd_vm_deploy.sh: el tar del material ya no lleva etcd-server.json (lo escribe Ansible).
#   4. scripts/etcd_ha/d313_es_vm.sh: JSON por defecto = /etc/ml-defender/etcd-server/etcd-server.json.
# Requiere los pasos 1 y 2a aplicados. No toca git.
# Uso (en el defender):  bash d315_ansible_paso2b.sh --check [RAIZ]   |   bash d315_ansible_paso2b.sh --apply [RAIZ]
set -euo pipefail
export LC_ALL=C

MODO=${1:-}
RAIZ=${2:-/vagrant}
case "$MODO" in --check|--apply) ;; *) echo "uso: $0 --check|--apply [RAIZ]"; exit 2 ;; esac
cd "$RAIZ"

PB=ansible/playbooks/deploy_configs.yml
GV=ansible/inventory/group_vars/argus_dev.yml
D312=scripts/etcd_ha/d312_etcd_vm_deploy.sh
D313=scripts/etcd_ha/d313_es_vm.sh
declare -A SHA=(
  [$PB]=15b76f6715ef53e455bb6eb174ecac5c253de0e2ad86990171313749f0cff024
  [$GV]=e5549899cf93e5d4d76e4a4e2a62b392cf3d1846a5f09b1726be0d8061b8be07
  [$D312]=5d94a5248708767043d7775400e76c7b044851bd3222a2ed028d87b396a974fd
  [$D313]=932c8cae5e34e0b6d7aba7b25f363ad2aa3ee9324f6eae8364f691ad7795ac6a
)

if grep -q 'ETCD-CONFIG-ENTORNO-D315' "$PB" && grep -q 'ETCD-CONFIG-ENTORNO-D315' "$GV" \
   && grep -q 'ETCD-CONFIG-ENTORNO-D315' "$D312" && grep -q 'ETCD-CONFIG-ENTORNO-D315' "$D313"; then
  echo "[ETCD-CONFIG-ENTORNO-D315] ya aplicado en $RAIZ: nada que hacer"; exit 0
fi

FALLOS=0
ok()  { echo "✅ $*"; }
mal() { echo "❌ $*"; FALLOS=$((FALLOS+1)); }
grep -q 'DEPLOY-SSH-D315' ansible/inventory/dev.yml && ok "paso 2a aplicado" || mal "falta el paso 2a (d315_ansible_paso2a.sh)"
for f in "${!SHA[@]}"; do
  if [ ! -f "$f" ]; then mal "falta $f"; continue; fi
  h=$(sha256sum "$f" | cut -d' ' -f1)
  [ "$h" = "${SHA[$f]}" ] && ok "$f (${h:0:16})" || mal "$f: sha256 $h, se esperaba ${SHA[$f]}"
done
[ -f etcd-server/config/etcd-server.etcd-vm.json ] && ok "existe etcd-server/config/etcd-server.etcd-vm.json" \
  || mal "falta etcd-server/config/etcd-server.etcd-vm.json"

if [ "$FALLOS" != 0 ]; then echo "[ETCD-CONFIG-ENTORNO-D315] $FALLOS comprobaciones fallan: no se toca nada"; exit 1; fi
if [ "$MODO" = --check ]; then echo "[ETCD-CONFIG-ENTORNO-D315] --check: todo listo para --apply"; exit 0; fi

# ---------------------------------------------------------------- 1. playbook
cat > "$PB" <<'YML'
---
# aRGus NDR -- Playbook: configuraciones por entorno
# [ANSIBLE-D315] DEBT-ANSIBLE-DEPLOY-CONFIGS-001: nada de plantillas completas (las de sniffer y ml-detector, DAY161,
# sobrescribían los JSON y se borraron). Patrón: el JSON del repo es la ley y Ansible sustituye solo los campos que
# dependen del despliegue. DEBT-CONFIG-JINJA2-PIPELINE-001: el mismo patrón para sniffer y ml-detector.
# Variables: ansible/inventory/group_vars/<grupo>.yml (Ansible las carga junto al inventario).
# Uso dev:  make deploy-configs        (ansible/inventory/dev.yml)
# Uso prod: make deploy-configs-prod   (ansible/inventory/prod.yml)

# [ETCD-CONFIG-ENTORNO-D315] etcd-server: etcd-server.etcd-vm.json del repo con almacen.endpoints y almacen.prefijo del
# inventario (etcd_almacen_endpoints, argus_prefijo; sin defecto). Se escribe en la máquina del etcd-server, nunca en
# /vagrant, y solo si el propio binario lo da por bueno (--check-config = 0: cualquier defecto lo rechaza).
- name: aRGus NDR -- etcd-server (JSON del repo + almacen del inventario)
  hosts: etcd_servers
  gather_facts: false
  become: true

  vars:
    es_json_repo: "{{ playbook_dir }}/../../etcd-server/config/etcd-server.etcd-vm.json"
    es_json_dest: /etc/ml-defender/etcd-server/etcd-server.json
    es_bin: /opt/argus/etcd-server/bin/etcd-server
    es_lib: /opt/argus/etcd-server/lib
    es_check: "env LD_LIBRARY_PATH={{ es_lib }} {{ es_bin }} --check-config -c"

  tasks:
    - name: "etcd_almacen_endpoints y argus_prefijo vienen del inventario (sin defecto)"
      assert:
        that:
          - etcd_almacen_endpoints is defined
          - etcd_almacen_endpoints is sequence
          - etcd_almacen_endpoints is not string
          - etcd_almacen_endpoints | length > 0
          - argus_prefijo is defined
          - argus_prefijo is string
        fail_msg: >-
          [ETCD-CONFIG-ENTORNO] {{ inventory_hostname }}: faltan o están mal etcd_almacen_endpoints (lista con TODOS los
          miembros etcd del despliegue, "https://IPv4:puerto") o argus_prefijo (texto, p. ej. /argus/<hospital>/<planta>/)
          en el group_vars del inventario. No hay defecto: sin ellos no se despliega.
        quiet: true

    - name: "El binario del etcd-server está instalado (d312_etcd_vm_deploy.sh desde el Mac)"
      stat:
        path: "{{ es_bin }}"
      register: es_bin_st

    - name: "Sin binario no se puede validar: no se despliega"
      assert:
        that: es_bin_st.stat.exists and es_bin_st.stat.executable
        fail_msg: "[ETCD-CONFIG-ENTORNO] {{ inventory_hostname }}: no existe {{ es_bin }} (antes, desde el Mac: bash scripts/etcd_ha/d312_etcd_vm_deploy.sh)"
        quiet: true

    - name: "JSON del repo con almacen.endpoints y almacen.prefijo del inventario"
      set_fact:
        es_json: >-
          {{ lookup('file', es_json_repo) | from_json
             | combine({'almacen': {'endpoints': etcd_almacen_endpoints, 'prefijo': argus_prefijo}}, recursive=True) }}

    - name: "Escribir {{ es_json_dest }} (validado antes con --check-config; nunca sigue un enlace)"
      copy:
        content: "{{ es_json | to_nice_json(indent=2, sort_keys=False) }}\n"
        dest: "{{ es_json_dest }}"
        follow: false
        owner: root
        group: root
        mode: "0640"
        validate: "{{ es_check }} %s"

    - name: "--check-config del fichero desplegado"
      command: "{{ es_check }} {{ es_json_dest }}"
      changed_when: false
      register: es_chk

    - name: "Configuración efectiva del almacén"
      debug:
        msg: "{{ (es_chk.stdout_lines + es_chk.stderr_lines) | select('search', 'ETCD-CONFIG-CHECK|\\[ETCD-ALMACEN\\]') | list }}"
YML

# ---------------------------------------------------------------- 2. group_vars dev
cat >> "$GV" <<'YML'

# [ETCD-CONFIG-ENTORNO-D315] etcd-server: almacen.endpoints y almacen.prefijo de ESTE despliegue (sin defecto en ningún
# sitio: ni aquí ni en el código). La lista lleva TODOS los miembros etcd del clúster del despliegue: el líder lo elige
# Raft, nunca Jenkins; cualquier miembro reenvía las escrituras al líder. El prefijo es por despliegue (p. ej.
# /argus/<hospital>/<planta>/): dos plantas en un mismo clúster sin prefijo propio se pisarían en silencio (los CN son los
# mismos), y el rol RBAC del etcd-server en etcd tiene que cubrirlo (en el lab: readwrite /argus/).
# Lab: un único miembro, elegido a mano (el etcd local de la VM etcd).
etcd_almacen_endpoints:
  - "https://127.0.0.1:2381"
argus_prefijo: "/argus/"
YML

# ---------------------------------------------------------------- 3 y 4. scripts del etcd-server
python3 - "$D312" "$D313" <<'PY'
import sys
d312, d313 = sys.argv[1:3]

def cambiar(p, pares):
    s = open(p, encoding="utf-8").read()
    for viejo, nuevo in pares:
        assert s.count(viejo) == 1, (p, viejo, s.count(viejo))
        s = s.replace(viejo, nuevo)
    open(p, "w", encoding="utf-8").write(s)

cambiar(d312, [
    ('S defender "sudo tar -C /etc/ml-defender -cf - etcd-server" \\\n',
     '# [ETCD-CONFIG-ENTORNO-D315] etcd-server.json NO viaja: en la VM etcd lo escribe Ansible (make deploy-configs), con\n'
     '# almacen.endpoints y almacen.prefijo del inventario; este tar lo pisaría\n'
     'S defender "sudo tar -C /etc/ml-defender --exclude=etcd-server/etcd-server.json -cf - etcd-server" \\\n'),
    ('L=$(S etcd "readlink /etc/ml-defender/etcd-server/etcd-server.json" )\n'
     'echo "[ETCD-DEPLOY] material: $IG de $ND ficheros iguales en defender y etcd; etcd-server.json -> $L"\n',
     'echo "[ETCD-DEPLOY] material: $IG de $ND ficheros iguales en defender y etcd; etcd-server.json no viaja (make deploy-configs)"\n'),
])

cambiar(d313, [
    ('arranca en segundo plano con -c JSON (defecto: el de la VM, con mTLS) y log propio',
     'arranca en segundo plano con -c JSON (defecto: el que escribe Ansible) y log propio'),
    ('JSON=${2:-/vagrant/etcd-server/config/etcd-server.etcd-vm.json}\n',
     '# [ETCD-CONFIG-ENTORNO-D315] por defecto, el JSON que escribe Ansible (make deploy-configs): el del repo con\n'
     '# almacen.endpoints y almacen.prefijo del inventario\n'
     'JSON=${2:-/etc/ml-defender/etcd-server/etcd-server.json}\n'),
    ('    [ -f "$JSON" ] || falla "no existe $JSON"\n',
     '    sudo test -f "$JSON" || falla "no existe $JSON (en la VM etcd lo escribe Ansible: make deploy-configs desde el Mac)"\n'),
])
PY
echo "✏️  $PB (play del etcd-server), $GV (endpoints y prefijo del lab), $D312 (sin etcd-server.json), $D313 (JSON por defecto)"

set +e; OK=0; MAL=0
chk() { if [ "$2" = 0 ]; then echo "✅ $1"; OK=$((OK+1)); else echo "❌ $1"; MAL=$((MAL+1)); fi; }
python3 -c 'import yaml,sys; p=yaml.safe_load(open(sys.argv[1])); assert len(p)==1 and p[0]["hosts"]=="etcd_servers" and any("validate" in t.get("copy",{}) for t in p[0]["tasks"])' "$PB"; chk "playbook: un play sobre etcd_servers con copy validado" $?
python3 -c 'import yaml,sys; g=yaml.safe_load(open(sys.argv[1])); assert g["etcd_almacen_endpoints"]==["https://127.0.0.1:2381"] and g["argus_prefijo"]=="/argus/" and g["argus_env"]=="dev"' "$GV"; chk "group_vars dev: argus_env, etcd_almacen_endpoints y argus_prefijo" $?
grep -q -- '--exclude=etcd-server/etcd-server.json' "$D312" && ! grep -q 'readlink /etc/ml-defender' "$D312"; chk "d312: tar sin etcd-server.json y sin readlink" $?
bash -n "$D312";                                                          chk "d312: sintaxis bash" $?
grep -q '^JSON=${2:-/etc/ml-defender/etcd-server/etcd-server.json}$' "$D313" && grep -q 'sudo test -f "$JSON"' "$D313"; chk "d313_es_vm: JSON por defecto y sudo test" $?
bash -n "$D313";                                                          chk "d313_es_vm: sintaxis bash" $?
echo "[ETCD-CONFIG-ENTORNO-D315] comprobaciones finales: $OK PASA, $MAL FALLA"
[ "$MAL" = 0 ]
