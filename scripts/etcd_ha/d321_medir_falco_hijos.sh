#!/usr/bin/env bash
# [VIGILANCIA-D321] DAY321 (v2), medida previa a las reglas de Falco de 8e.4d: qué hace DE VERDAD el lab, para no escribir las
# listas de permitidos leyendo el código (autonomy_reactor.cpp usa std::system(), que lanza sh -c).
# Instala Falco 0.43.1 (dist/vendor, sha256 contra CHECKSUMS, modern_ebpf, sin falcoctl) en la VM etcd y en el defender
# con DOS reglas de medida que solo registran (INFORMATIONAL), lanza la carga de trabajo del lab y PURGA Falco al acabar
# (también desde el trap):
#   argus_medida_hijo     todo execve cuyo padre es etcd-server, firewall-acl-agent, sniffer, ml-detector, vault o etcd
#   argus_medida_lectura  toda apertura para leer de una clave o semilla: /etc/argus-pki/*.key, /etc/vault.d/tls/*.key,
#                         /etc/etcd/tls/*.key, /etc/ml-defender/*/seed.bin, /etc/ml-defender/*/private.pem
# Carga de trabajo (Mac): pipeline-stop, pipeline-start (arranque: lecturas de semillas y claves), pipeline-status,
# lab-e2e-mitigacion (mitigación real: el firewall ejecuta ipset/iptables) y pipeline-start para dejarlo arriba. ~15 min.
# Resultado: por VM, los pares (padre, hijo, exe) y (proceso, padre, abuelo, fichero) con su cuenta, y unos cmdline de
# ejemplo de los hijos que son shells. Copia cruda en logs/lab/day321/medida_falco/.
# Uso (Mac, raíz del repo, con el pipeline y las VMs client y etcd arriba):
#   bash scripts/etcd_ha/d321_medir_falco_hijos.sh > /tmp/d321_hijos.txt 2>&1; cat /tmp/d321_hijos.txt
#
# PREDICCIÓN (escrita antes de medir):
# v2 (tras la v1): el padre se identifica por su RUTA (proc.pexepath): el nombre corto del kernel se corta a 15
# caracteres (firewall-acl-ag) y la v1 nunca vio al firewall. Eventos en JSON para contar también las reglas de serie.
#  Hijos: firewall-acl-agent -> /usr/sbin/ipset (o /sbin/ipset), iptables, iptables-restore e ip; sniffer -> /usr/bin/dash
#  (los dos sh -c sysctl de dual_nic_manager.cpp, medidos en la v1) -> sysctl; etcd-server, vault, etcd y ml-detector sin hijos.
#  Lecturas: cada servidor las suyas (etcd-server, vault, etcd en la VM etcd; firewall-acl-agent, sniffer y ml-detector
#  sus semillas en el defender, al arrancar) y, además, curl y etcdctl de etcd_vm_estado.sh (pipeline-status) leyendo
#  /etc/argus-pki/etcd-server.key (medido en la v1, ahora con su ruta). Reglas de serie: las mismas 31 del defender,
#  ahora con su nombre. Tras purgar: sin paquete ni proceso y el pipeline arriba.
set -u
LC_ALL=C; export LC_ALL
vm() { local out rc; out=$(vagrant ssh "$1" -c "export LC_ALL=C; $2" 2>/dev/null); rc=$?
       [ -n "$out" ] && printf '%s\n' "$out" | tr -d '\r' | grep -v '^\[argus\]'; return $rc; }
UNIDAD=falco-modern-bpf.service
DM=logs/lab/day321/medida_falco
INSTALADO=""
purgar() {
  vm "$1" "sudo systemctl stop $UNIDAD 2>/dev/null; sudo rm -f /etc/falco/rules.d/argus_medida.yaml /etc/falco/config.d/argus_medida.yaml; \
    sudo DEBIAN_FRONTEND=noninteractive dpkg --purge falco >/dev/null 2>&1; \
    echo \"paquete: \$(dpkg-query -W -f='\${Status}' falco 2>/dev/null || echo ausente) proceso: \$(pgrep -x falco >/dev/null && echo SIGUE || echo ninguno)\"" \
    | sed "s/^/    $1 purgado: /"
}
restaurar() { local v; for v in $INSTALADO; do purgar "$v"; done; INSTALADO=""; }
trap restaurar EXIT
trap 'exit 130' INT TERM

echo "=== [$(date +%T)] 0 comprobaciones"
DEB=$(ls dist/vendor/falco_*.deb 2>/dev/null | head -n 1)
[ -n "$DEB" ] || { echo "PARADA: no hay dist/vendor/falco_*.deb"; exit 1; }
H=$(shasum -a 256 "$DEB" | cut -d' ' -f1)
grep -q "$H" dist/vendor/CHECKSUMS 2>/dev/null || { echo "PARADA: el sha256 de $DEB no está en dist/vendor/CHECKSUMS"; exit 1; }
for v in client etcd; do vagrant status "$v" 2>/dev/null | grep -qE "^$v +running" || { echo "PARADA: la VM $v no está arriba"; exit 1; }; done
git diff --quiet -- firewall-acl-agent/config/firewall.json || { echo "PARADA: firewall.json con cambios sin commit (lab-e2e-mitigacion no arrancaría)"; exit 1; }
mkdir -p "$DM"
REGLAS='- macro: argus_medida_padre_vigilado
  condition: (proc.pexepath endswith "/firewall-acl-agent" or proc.pexepath endswith "/sniffer" or proc.pexepath endswith "/ml-detector" or proc.pexepath endswith "/etcd-server" or proc.pexepath endswith "/vault" or proc.pexepath endswith "/etcd")
- rule: argus_medida_hijo
  desc: medida DAY321 v2 - todo hijo de un proceso de aRGus, de Vault o de etcd (por la ruta del padre, no por su nombre corto)
  condition: evt.type in (execve, execveat) and argus_medida_padre_vigilado
  output: MEDIDA-HIJO padre=%proc.pexepath hijo=%proc.exepath cmd=%proc.cmdline
  priority: INFORMATIONAL
  tags: [argus, medida]
- rule: argus_medida_lectura
  desc: medida DAY321 v2 - lecturas de claves y semillas
  condition: evt.type in (open, openat, openat2) and evt.is_open_read=true and fd.typechar=f and (fd.name glob "/etc/argus-pki/*.key" or fd.name glob "/etc/vault.d/tls/*.key" or fd.name glob "/etc/etcd/tls/*.key" or fd.name glob "/etc/ml-defender/*/seed.bin" or fd.name glob "/etc/ml-defender/*/private.pem")
  output: MEDIDA-LECTURA proc=%proc.exepath padre=%proc.pexepath abuelo=%proc.aname[2] fichero=%fd.name
  priority: INFORMATIONAL
  tags: [argus, medida]'
CONF='# medida DAY321 v2: eventos en JSON (con el nombre de la regla) para contarlos
json_output: true
json_include_output_property: true'

for V in etcd defender; do
  echo; echo "=== [$(date +%T)] 1 Falco con las reglas de medida en $V"
  if vm "$V" "dpkg-query -W -f='\${Status}' falco 2>/dev/null | grep -q 'install ok installed'"; then
    echo "PARADA: Falco ya estaba instalado en $V (no se toca)"; exit 1
  fi
  INSTALADO="$INSTALADO $V"
  vm "$V" "sudo env FALCO_FRONTEND=noninteractive FALCO_DRIVER_CHOICE=modern_ebpf FALCOCTL_ENABLED=no DEBIAN_FRONTEND=noninteractive \
    dpkg -i /vagrant/$DEB > /tmp/d321_falco_dpkg.txt 2>&1; echo \"dpkg rc=\$?\"; \
    sudo systemctl disable --now falcoctl-artifact-follow.service >/dev/null 2>&1; sudo mkdir -p /etc/falco/rules.d" | sed 's/^/    /'
  printf '%s\n' "$REGLAS" | vagrant ssh "$V" -c "sudo tee /etc/falco/rules.d/argus_medida.yaml > /dev/null" 2>/dev/null
  printf '%s\n' "$CONF" | vagrant ssh "$V" -c "sudo mkdir -p /etc/falco/config.d && sudo tee /etc/falco/config.d/argus_medida.yaml > /dev/null" 2>/dev/null
  vm "$V" "sudo falco --validate /etc/falco/rules.d/argus_medida.yaml 2>&1 | tail -n 2; sudo systemctl restart $UNIDAD; sleep 5; echo \"$UNIDAD: \$(systemctl is-active $UNIDAD)\"" | sed 's/^/    /'
  vm "$V" "pgrep -x falco > /dev/null" || { echo "PARADA: falco no arrancó en $V"; vm "$V" "sudo journalctl -u $UNIDAD -n 15 --no-pager"; exit 1; }
done
T0=$(vm etcd "date +%s"); T0D=$(vm defender "date +%s")

echo; echo "=== [$(date +%T)] 2 carga de trabajo"
make pipeline-stop > /tmp/d321_h_stop.txt 2>&1; echo "    pipeline-stop rc=$?"
make pipeline-start PROFILE=production > /tmp/d321_h_start.txt 2>&1; echo "    pipeline-start rc=$?"
sleep 40
make pipeline-status > /tmp/d321_h_status.txt 2>&1; echo "    pipeline-status rc=$?"
make lab-e2e-mitigacion > /tmp/d321_h_mitig.txt 2>&1; echo "    lab-e2e-mitigacion rc=$? ($(grep -m 1 -o 'RESULTADO [A-Z]*' /tmp/d321_h_mitig.txt))"
make pipeline-start PROFILE=production > /tmp/d321_h_start2.txt 2>&1; echo "    pipeline-start rc=$?"
sleep 40

for V in etcd defender; do
  t=$T0; [ "$V" = defender ] && t=$T0D
  echo; echo "=== [$(date +%T)] 3 resultado en $V"
  vm "$V" "sudo journalctl -u $UNIDAD --since @$t --no-pager -q -o cat | grep '^{'" > "$DM/$V.jsonl"
  echo "    eventos: $(wc -l < "$DM/$V.jsonl") (copia en $DM/$V.jsonl)"
  python3 - "$DM/$V.jsonl" <<'PYEOF'
import collections, json, re, sys
hijos, lect, serie, shells = collections.Counter(), collections.Counter(), collections.Counter(), []
for l in open(sys.argv[1], encoding="utf-8", errors="replace"):
    try:
        e = json.loads(l)
    except Exception:
        continue
    r, o = e.get("rule", "?"), e.get("output", "")
    if r == "argus_medida_hijo":
        m = re.search(r"padre=(\S+) hijo=(\S+)", o)
        hijos[m.groups() if m else ("?", "?")] += 1
        if m and re.search(r"/(sh|bash|dash)$", m.group(2)) and len(shells) < 6:
            shells.append(o[o.find("padre="):][:200])
    elif r == "argus_medida_lectura":
        m = re.search(r"proc=(\S+) padre=(\S+) abuelo=(\S+) fichero=(\S+)", o)
        lect[m.groups() if m else ("?",) * 4] += 1
    else:
        serie[(r, e.get("priority", "?"))] += 1
print("    hijos (cuenta padre -> hijo):")
for (p, h), n in hijos.most_common():
    print("      %5d %s -> %s" % (n, p, h))
print("    lecturas (cuenta proceso padre abuelo fichero):")
for k, n in lect.most_common():
    print("      %5d %s" % (n, " ".join(k)))
print("    ejemplos de hijos que son shells:")
for s in shells:
    print("      " + s)
print("    reglas de serie que saltaron (cuenta regla prioridad):")
for (r, p), n in serie.most_common():
    print("      %5d %s %s" % (n, r, p))
PYEOF
done

echo; echo "=== [$(date +%T)] 4 purga"
restaurar
make pipeline-status > /tmp/d321_h_status2.txt 2>&1
grep -E '✅|❌' /tmp/d321_h_status2.txt | grep -E 'ml-detector|sniffer|firewall|etcd-server' | sed 's/^/   /'
echo "=== [$(date +%T)] fin"
