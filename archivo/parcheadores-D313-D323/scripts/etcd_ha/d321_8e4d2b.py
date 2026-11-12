#!/usr/bin/env python3
# [VIGILANCIA-D321] 8e.4d-2: comprobación de los sensores v2 (sudo en wc y journalctl, grep -a en ossec.log, errores con su hora, contenido del agent.conf recibido en vez de su sha256).
# Uso (raíz del repo): python3 -I d321_8e4d2b.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'scripts/etcd_ha/d321_comprobar_sensores.sh', 'antes': '7c54d4fc24cc0068c5220c1a4538d38802b361e7e4f4ea152711ab5e0e349b3b', 'despues': '99a1302b663ec34dd014224609b06c1282ca24e9c031d81c1a9593cf2d64ed30', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('#    supone provisioning/falco/argus_lab.yaml: si sale otro, hay que corregir la macro).\n#  Agentes: el ossec.log del agente dice que analiza /var/log/falco/eventos.json y journald, sin ERROR 1103 desde el\n#    último arranque; el agent.conf que recibió es el de su grupo (mismo sha256 que en el manager).\n#  Manager: etcd en argus-etcd y defender en argus-defender, los dos Active y con versión v4.14.10.\n#  pipeline-status: ml-detector, sniffer, firewall y etcd-server en ✅ (como antes).\n',
             '#    supone provisioning/falco/argus_lab.yaml: si sale otro, hay que corregir la macro).\n#  Agentes: el ossec.log del agente dice que analiza /var/log/falco/eventos.json y journald, sin ERROR 1103 desde el\n#    último arranque; el agent.conf que recibió lleva lo de su grupo (etcd: argus-disco; defender: firewall-agent.log).\n#    No se compara el sha256 con el del grupo: con dos grupos (default + el de aRGus) el manager envía los dos fundidos\n#    (medido DAY321, v1 de este script: los sha256 no coinciden por eso).\n# v2 DAY321: wc y journalctl con sudo (como vagrant daban "Permission denied" y nada), grep -a en ossec.log (tiene\n#    bytes no imprimibles: "binary file matches"), errores del agente con su hora, y el fichero que deja falcoctl en\n#    config.d.\n#  Manager: etcd en argus-etcd y defender en argus-defender, los dos Active y con versión v4.14.10.\n#  pipeline-status: ml-detector, sniffer, firewall y etcd-server en ✅ (como antes).\n'),
            ('    echo \\"listas de apt con download.falco.org:\\"; grep -lsF download.falco.org /etc/apt/sources.list /etc/apt/sources.list.d/* | while read f; do echo \\"  \\$f: \\$(cat \\$f)\\"; done; \\\n    P=\\$(pgrep -x falco | head -n 1); [ -n \\"\\$P\\" ] && echo \\"RSS de falco: \\$(( \\$(ps -o rss= -p \\$P) / 1024 )) MB\\"; \\\n    sudo ls -l /var/log/falco/eventos.json; echo \\"líneas en eventos.json: \\$(sudo wc -l < /var/log/falco/eventos.json)\\"; \\\n    sudo grep -o \'\\"rule\\":\\"[^\\"]*\\"\' /var/log/falco/eventos.json | sort | uniq -c | head -n 5; \\\n    echo \\"reglas: \\$(ls /etc/falco/rules.d/) config.d: \\$(ls /etc/falco/config.d/ | tr \'\\n\' \' \')\\"" | sed \'s/^/    /\'\ndone\n\n',
             '    echo \\"listas de apt con download.falco.org:\\"; grep -lsF download.falco.org /etc/apt/sources.list /etc/apt/sources.list.d/* | while read f; do echo \\"  \\$f: \\$(cat \\$f)\\"; done; \\\n    P=\\$(pgrep -x falco | head -n 1); [ -n \\"\\$P\\" ] && echo \\"RSS de falco: \\$(( \\$(ps -o rss= -p \\$P) / 1024 )) MB\\"; \\\n    sudo ls -l /var/log/falco/eventos.json; echo \\"líneas en eventos.json: \\$(sudo wc -l /var/log/falco/eventos.json | cut -d\' \' -f1)\\"; \\\n    sudo grep -o \'\\"rule\\":\\"[^\\"]*\\"\' /var/log/falco/eventos.json | sort | uniq -c | head -n 5; \\\n    echo \\"reglas: \\$(ls /etc/falco/rules.d/) config.d: \\$(ls /etc/falco/config.d/ | tr \'\\n\' \' \')\\"; \\\n    echo \\"engine-kind-falcoctl.yaml (lo escribe falcoctl driver config en el postinst):\\"; \\\n    grep -v \'^ *#\' /etc/falco/config.d/engine-kind-falcoctl.yaml 2>/dev/null | sed \'s/^/  /\'" | sed \'s/^/    /\'\ndone\n\n'),
            ('done\nfor V in etcd defender; do\n  vm "$V" "B=\\$(sudo grep -n \'Started (pid\' /var/ossec/logs/ossec.log | tail -n 1 | cut -d: -f1); B=\\${B:-1}; \\\n    echo \\"$V ossec.log desde el último arranque (línea \\$B):\\"; \\\n    sudo tail -n +\\$B /var/ossec/logs/ossec.log | grep -E \'Analyzing|journald|ERROR|1103\' | sed -E \'s/^[0-9\\/ :]+//\' | sort | uniq -c | head -n 12; \\\n    echo \\"agent.conf recibido: \\$(sudo sha256sum /var/ossec/etc/shared/agent.conf 2>/dev/null | cut -c1-16)\\"" | sed \'s/^/    /\'\ndone\n\necho; echo "=== [$(date +%T) Mac] VM etcd: memoria, argus-disco y el ejecutable de vault"\nvm etcd "echo \\"MemTotal: \\$(awk \'/MemTotal/ {print int(\\$2/1024)}\' /proc/meminfo) MB; disponible: \\$(free -m | awk \'NR==2 {print \\$7}\') MB\\"; \\\n  echo \\"argus-disco: \\$(systemctl is-active argus-disco.service)\\"; journalctl -t argus-disco -n 3 -o cat --no-pager; \\\n  P=\\$(pgrep -x vault | head -n 1); echo \\"vault: pid \\$P exe \\$(sudo readlink -f /proc/\\$P/exe)\\"; \\\n  P=\\$(pgrep -x etcd | head -n 1); echo \\"etcd: exe \\$(sudo readlink -f /proc/\\$P/exe)\\"" | sed \'s/^/    /\'\n',
             'done\nfor V in etcd defender; do\n  case $V in etcd) M=argus-disco ;; *) M=firewall-agent.log ;; esac\n  vm "$V" "L=/var/ossec/logs/ossec.log; B=\\$(sudo grep -an \'Started (pid\' \\$L | tail -n 1 | cut -d: -f1); B=\\${B:-1}; \\\n    echo \\"$V ossec.log desde el último arranque, línea \\$B: \\$(sudo sed -n \\"\\${B}p\\" \\$L | cut -c1-19) UTC\\"; \\\n    sudo tail -n +\\$B \\$L | grep -aE \'Analyzing|journald\' | sed -E \'s/^[0-9\\/ :]+//\' | sort | uniq -c | head -n 12; \\\n    echo \\"  errores desde ese arranque: \\$(sudo tail -n +\\$B \\$L | grep -ac \'ERROR\')\\"; \\\n    sudo tail -n +\\$B \\$L | grep -a \'ERROR\' | sed -E \'s/^([0-9\\/]+ [0-9:]+) (.{0,110}).*/\\1 \\2/\' | sed -n \'1p;\\$p\' | sed \'s/^/    primero y último: /\'; \\\n    echo \\"  agent.conf recibido: \\$(sudo sha256sum /var/ossec/etc/shared/agent.conf 2>/dev/null | cut -c1-16), con $M: \\$(sudo grep -c \'$M\' /var/ossec/etc/shared/agent.conf 2>/dev/null) líneas\\"" | sed \'s/^/    /\'\ndone\n\necho; echo "=== [$(date +%T) Mac] VM etcd: memoria, argus-disco y el ejecutable de vault"\nvm etcd "echo \\"MemTotal: \\$(awk \'/MemTotal/ {print int(\\$2/1024)}\' /proc/meminfo) MB; disponible: \\$(free -m | awk \'NR==2 {print \\$7}\') MB\\"; \\\n  echo \\"argus-disco: \\$(systemctl is-active argus-disco.service)\\"; sudo journalctl -t argus-disco -n 3 -o short-iso --no-pager; \\\n  P=\\$(pgrep -x vault | head -n 1); echo \\"vault: pid \\$P exe \\$(sudo readlink -f /proc/\\$P/exe)\\"; \\\n  P=\\$(pgrep -x etcd | head -n 1); echo \\"etcd: exe \\$(sudo readlink -f /proc/\\$P/exe)\\"" | sed \'s/^/    /\'\n'),
        ],
    },
]


def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply"); return 2
    aplicar = sys.argv[1] == "--apply"
    if not os.path.isdir(".git"):
        print("[ERROR] ejecutar desde la raíz del repo (no veo .git)"); return 2
    plan, ya, errores = [], 0, 0
    for f in FICHEROS:
        r = f["ruta"]
        if os.path.exists(r):
            actual = open(r, "rb").read()
            h = sha(actual)
            if h == f["despues"]:
                print(f"[YA-APLICADO] {r} {h[:16]}"); ya += 1; continue
            if f["antes"] == "nuevo":
                print(f"[ERROR] {r} existe con otro contenido ({h[:16]}); se esperaba que no existiera"); errores += 1; continue
            if h != f["antes"]:
                print(f"[ERROR] {r} sha256 {h[:16]}, se esperaba {f['antes'][:16]} (antes) o {f['despues'][:16]} (después)"); errores += 1; continue
            t = actual.decode("utf-8")
            for i, (v, n) in enumerate(f["trozos"]):
                if t.count(v) != 1:
                    print(f"[ERROR] {r}: trozo {i + 1} aparece {t.count(v)} veces"); errores += 1; break
                t = t.replace(v, n)
            nb = t.encode("utf-8")
            modo = os.stat(r).st_mode & 0o777
        else:
            if f["antes"] != "nuevo":
                print(f"[ERROR] {r} no existe"); errores += 1; continue
            nb = f["nuevo"].encode("utf-8"); modo = int(f["modo"], 8)
        if sha(nb) != f["despues"]:
            print(f"[ERROR] {r}: el resultado no da el sha256 esperado"); errores += 1; continue
        plan.append((r, nb, modo, f))
        print(f"[APLICABLE] {r} {f['antes'][:16]} -> {f['despues'][:16]} ({len(f['trozos']) if f['nuevo'] is None else 'fichero nuevo'}{' bloques' if f['nuevo'] is None else ''})")
    if errores:
        print(f"[ERROR] {errores} problemas: no se escribe nada"); return 1
    if not plan:
        print(f"[CHECK] todo ya aplicado ({ya} ficheros)"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(plan)} ficheros, {ya} ya aplicados); nada escrito"); return 0
    for r, nb, modo, f in plan:
        d = os.path.dirname(r) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche_")
        with os.fdopen(fd, "wb") as o: o.write(nb)
        os.chmod(tmp, modo)
        os.replace(tmp, r)
        print(f"[APLICADO] {r} sha256={f['despues']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
