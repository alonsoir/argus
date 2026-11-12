#!/usr/bin/env python3
# d323_reloj_lab.py — DEBT-ETCD-HA-TLS-RAFT-001, PR1 (DAY323) [LAB-NTP-SENSORES-D323]: un solo reloj para el lab.
# Vagrantfile: suricata, zeek y wazuh toman la hora del defender (provisión lab-ntp, run: always; si no sincroniza con
# 192.168.100.1 en 30 s, FALLA). Makefile: lab-clock-step recorre LAB_CLOCK_VMS (por defecto client, como hasta ahora)
# y mitre-check lo llama antes de la corrida con client suricata zeek. Medido DAY323: los tres sensores iban al pool de
# Debian por la NAT, cada uno con su referencia. Requiere d323_suricata_arranque.py aplicado (commit d44e0a2d0).
# Uso:  python3 d323_reloj_lab.py --check <raiz_repo>
#       python3 d323_reloj_lab.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si CADA fichero está en el estado previo exacto y el resultado da su sha256 final.
import hashlib, os, sys

FICHEROS = {'Vagrantfile': ('4d7dac75bbaa271e0ca36250a8136f025c0cbc139b24e1c4bc2c2d7ad25de8cc', 'd026e01d2120590f0b2f6a89fb84d48a513ddf3b691fe305b6144c59a58dabae', [('WAZUH_AGENT_INSTALL = "bash /vagrant/scripts/vigilancia/wazuh_agente_instalar.sh"\n', 'WAZUH_AGENT_INSTALL = "bash /vagrant/scripts/vigilancia/wazuh_agente_instalar.sh"\n\n# LAB_NTP — [LAB-NTP-SENSORES-D323] los sensores (suricata, zeek, wazuh) toman la hora del defender (192.168.100.1),\n# como el client [ARGUS-LAB-NTP-D294] y la VM etcd: un solo reloj para el lab, con o sin Internet (el defender sirve\n# hora con local stratum 10 aunque pierda sus fuentes). Medido DAY323: los tres iban al pool de Debian por la NAT\n# (162.159.200.1 y 195.95.153.59), cada uno con su referencia, y el reloj de las VMs de VirtualBox deriva de 2000 a\n# 5000 ppm (de 3 a 7 minutos al día sin NTP). Si no sincroniza con el defender en 30 s, la provisión FALLA.\n# run: always: cada vagrant up vuelve a sincronizar (tras suspender el Mac, el reloj de la VM se queda atrás).\nLAB_NTP = <<-\'LAB_NTP_SHELL\'\n  CHRONY_CONF=/etc/chrony/chrony.conf\n  command -v chronyc >/dev/null || { apt-get update -qq; apt-get install -y chrony; }\n  sed -i \'s/^pool /#pool /\' "$CHRONY_CONF"\n  sed -i \'s/^makestep 1 3$/makestep 1 -1/\' "$CHRONY_CONF"\n  grep -q \'^server 192.168.100.1 iburst\' "$CHRONY_CONF" || echo \'server 192.168.100.1 iburst\' >> "$CHRONY_CONF"\n  systemctl restart chrony\n  if ! chronyc waitsync 30 0.1 0 1; then\n    echo "❌ [LAB-NTP] $(hostname): sin sincronizar con 192.168.100.1 en 30 s"; chronyc -n sources; exit 1\n  fi\n  if ! chronyc -n tracking | grep -qF \'(192.168.100.1)\'; then\n    echo "❌ [LAB-NTP] $(hostname): su fuente no es el defender 192.168.100.1"; chronyc -n tracking; exit 1\n  fi\n  echo "✅ [LAB-NTP] $(hostname): $(chronyc -n tracking | grep -E \'Reference ID|System time\' | tr -s \' \' | paste -sd \';\' -)"\nLAB_NTP_SHELL\n', 1), ('    suricata.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN\n', '    suricata.vm.provision "shell", name: "lab-ntp", run: "always", inline: LAB_NTP\n    suricata.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN\n', 1), ('    zeek.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN\n', '    zeek.vm.provision "shell", name: "lab-ntp", run: "always", inline: LAB_NTP\n    zeek.vm.provision "shell", name: "adapter-toolchain", inline: ADAPTER_TOOLCHAIN\n', 1), ('    wazuh.vm.provision "shell", name: "host-adapter-perms", inline: <<-\'PERMS_SHELL\'\n', '    wazuh.vm.provision "shell", name: "lab-ntp", run: "always", inline: LAB_NTP\n    wazuh.vm.provision "shell", name: "host-adapter-perms", inline: <<-\'PERMS_SHELL\'\n', 1)]), 'Makefile': ('284d890a180760c9a26756d71154de4cd08ace995e2c07b46c603ed42081cad9', '9bd4a553df24e837d904185c4fccbf3e08bad32dd15b805db171e372d45f996b', [('LAB_CLOCK_WAIT_TRIES ?= 30\n', 'LAB_CLOCK_WAIT_TRIES ?= 30\n# [LAB-NTP-SENSORES-D323] VMs que se alinean con el defender, después de él. Por defecto solo el client (el uso de\n# siempre, con 3 VMs arriba); mitre-check pasa las de su corrida (client suricata zeek): un solo reloj para el grafo.\nLAB_CLOCK_VMS ?= client\n', 1), ('\t@echo "[LAB-CLOCK-STEP] client: makestep + waitsync (fuente 192.168.100.1)"\n\t@vagrant ssh client -c \'sudo chronyc makestep >/dev/null; chronyc waitsync $(LAB_CLOCK_WAIT_TRIES) $(LAB_CLOCK_MAX_OFFSET_S) 0 1 >/dev/null; rc=$$?; chronyc -n tracking | grep -E "Reference ID|System time"; if ! chronyc -n tracking | grep -qF "(192.168.100.1)"; then echo "[LAB-CLOCK-STEP] FALLO client: su fuente no es el defender 192.168.100.1"; exit 1; fi; if [ $$rc -ne 0 ]; then echo "[LAB-CLOCK-STEP] FALLO client: desfase >= $(LAB_CLOCK_MAX_OFFSET_S) s tras $(LAB_CLOCK_WAIT_TRIES) s"; exit 1; fi; echo "[LAB-CLOCK-STEP] client OK (< $(LAB_CLOCK_MAX_OFFSET_S) s)"\'\n\t@echo "[LAB-CLOCK-STEP] OK: defender y client alineados"\n', '\t@for vm in $(LAB_CLOCK_VMS); do \\\n\t  echo "[LAB-CLOCK-STEP] $$vm: makestep + waitsync (fuente 192.168.100.1)"; \\\n\t  vagrant ssh $$vm -c \'sudo chronyc makestep >/dev/null; chronyc waitsync $(LAB_CLOCK_WAIT_TRIES) $(LAB_CLOCK_MAX_OFFSET_S) 0 1 >/dev/null; rc=$$?; chronyc -n tracking | grep -E "Reference ID|System time"; if ! chronyc -n tracking | grep -qF "(192.168.100.1)"; then echo "[LAB-CLOCK-STEP] FALLO $$(hostname): su fuente no es el defender 192.168.100.1"; exit 1; fi; if [ $$rc -ne 0 ]; then echo "[LAB-CLOCK-STEP] FALLO $$(hostname): desfase >= $(LAB_CLOCK_MAX_OFFSET_S) s tras $(LAB_CLOCK_WAIT_TRIES) s"; exit 1; fi; echo "[LAB-CLOCK-STEP] $$(hostname) OK (< $(LAB_CLOCK_MAX_OFFSET_S) s)"\' || exit 1; \\\n\tdone\n\t@echo "[LAB-CLOCK-STEP] OK: defender y $(LAB_CLOCK_VMS) alineados"\n', 1), ('mitre-check:\n\t@echo "[MITRE-CHECK] $$(date \'+%T\') 1/3 parando el pipeline (log: /tmp/argus_mitre_check_stop.txt)"\n', 'mitre-check:\n\t@# [LAB-NTP-SENSORES-D323] un solo reloj: el grafo del día junta los tres sensores por ventana de tiempo; si una VM\n\t@# de la corrida no va con el defender (< LAB_CLOCK_MAX_OFFSET_S), es un fallo operacional y mitre-check FALLA\n\t@echo "[MITRE-CHECK] $$(date \'+%T\') 0/3 relojes del lab: defender y client suricata zeek (log: /tmp/argus_mitre_check_reloj.txt)"\n\t@$(MAKE) --no-print-directory lab-clock-step LAB_CLOCK_VMS="client suricata zeek" > /tmp/argus_mitre_check_reloj.txt 2>&1 || { tail -n 20 /tmp/argus_mitre_check_reloj.txt; echo "[MITRE-VEREDICTO] FALLA: relojes del lab"; exit 1; }\n\t@echo "[MITRE-CHECK] $$(date \'+%T\') 1/3 parando el pipeline (log: /tmp/argus_mitre_check_stop.txt)"\n', 1)])}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
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
