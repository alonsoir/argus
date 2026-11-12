#!/usr/bin/env python3
# d322_reinicio_r3.py — DAY322 [REINICIO-R3-FLUJO-D322]: el R3 de lab-e2e-reinicio-antes cuenta solo el flujo del
# ataque. Medido en EMECAS+++ DAY322: 3 marcas tras el reinicio que eran dos AISLADO de 192.168.100.12 (manager de
# Wazuh) -> .1 por TCP, no del ataque (UDP); el R3 viejo contaba todas y fallo.
#   - d300_reinicio_e2e.sh: marca linea_fw_parado (el log del firewall al parar el sniffer).
#   - d303_veredicto_reinicio.sh, modo antes: tras ese corte, 0 INICIO y 0 aislados del ataque (.1 proto 17) y las
#     marcas del ml-detector = aislados de los demás flujos (que salen como dato). ordenada y kill9 sin cambios.
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d322_reinicio_r3.py --check | --apply
# Todo o nada: --check comprueba que cada fichero está en su estado de partida (sha256) o ya parcheado; --apply escribe
# todo solo si --check pasa. Idempotente: dos --apply dejan lo mismo.
import hashlib, json, os, sys, tempfile
D = json.loads(r'''{
"cambios": [
{
"ruta": "scripts/timebase/d300_reinicio_e2e.sh",
"sha_antes": "8dbe186cb2fb54d12041aabd69eb02cdcc8ed58a615c82690873636ce64655f3",
"sha_despues": "36c9b4e9aa3f73a5cefc99bb5698dab46319072433653921ec4822916c69e44b",
"trozos": [
[
"falla() { echo; echo \"PARADA [$(date +%T)]: $*\"; exit 1; }\nmarca() { vagrant ssh defender -c \"mkdir -p $D && echo \\\"$1 \\$(date +%s.%N)\\\" >> $D/tiempos.txt\"; }\nmarca_linea() { vagrant ssh defender -c \"echo \\\"$1 \\$(wc -l < /vagrant/logs/lab/ml-detector.log)\\\" >> $D/tiempos.txt\"; }\n\npaso \"0 lab-clock-step\"\nmake lab-clock-step || falla \"relojes no alineados\"\n",
"falla() { echo; echo \"PARADA [$(date +%T)]: $*\"; exit 1; }\nmarca() { vagrant ssh defender -c \"mkdir -p $D && echo \\\"$1 \\$(date +%s.%N)\\\" >> $D/tiempos.txt\"; }\nmarca_linea() { vagrant ssh defender -c \"echo \\\"$1 \\$(wc -l < /vagrant/logs/lab/ml-detector.log)\\\" >> $D/tiempos.txt\"; }\n# [REINICIO-R3-FLUJO-D322] la misma marca para el log del firewall: el veredicto separa por flujo lo que llega tras el corte\nmarca_linea_fw() { vagrant ssh defender -c \"echo \\\"$1 \\$(wc -l < /vagrant/logs/lab/firewall-agent.log)\\\" >> $D/tiempos.txt\"; }\n\npaso \"0 lab-clock-step\"\nmake lab-clock-step || falla \"relojes no alineados\"\n"
],
[
"esac\nmarca sniffer_parado\nmarca_linea linea_ml_parado\nmake sniffer-start PROFILE=production || falla \"sniffer-start\"\nmarca reinicio_fin\npaso \"11 esperar el fin del cliente (hasta 600 s)\"\n",
"esac\nmarca sniffer_parado\nmarca_linea linea_ml_parado\nmarca_linea_fw linea_fw_parado\nmake sniffer-start PROFILE=production || falla \"sniffer-start\"\nmarca reinicio_fin\npaso \"11 esperar el fin del cliente (hasta 600 s)\"\n"
]
]
},
{
"ruta": "scripts/timebase/d303_veredicto_reinicio.sh",
"sha_antes": "0c887ca26f1b0e979282374498637c922f435623b9bc3abab140084b95b32900",
"sha_despues": "109c9a2247aef5b3d9b8bbd3b56a75ffefdbd873dd2739fb186be6d89465b036",
"trozos": [
[
"#     kill9:    1 x \"sin estado previo\", 1 x \"restauradas ... (1 bajo presion)\", y NINGUN \"volcado de parada\"\n#               antes de ella (restaura del volcado periodico; el volcado del pipeline-stop final va despues)\n#  R3 marcado tras el reinicio:\n#     antes:    0 marcados despues del corte (70 pps < abs_pps=200: en frio el ataque se aprende como base)\n#     ordenada/kill9: marcados_despues >= 0,5 x marcados_antes. Frontera entre los dos regimenes posibles:\n#               con estado ~1,2-1,3 (DAY300: 1,305 y 1,236), sin estado 0. La banda 1,15-1,40 se imprime\n#               como dato y NO decide (depende de lo que tarde vagrant ssh en parar el sniffer).\n",
"#     kill9:    1 x \"sin estado previo\", 1 x \"restauradas ... (1 bajo presion)\", y NINGUN \"volcado de parada\"\n#               antes de ella (restaura del volcado periodico; el volcado del pipeline-stop final va despues)\n#  R3 marcado tras el reinicio:\n#     antes:    0 marcados DEL ATAQUE despues del corte (70 pps < abs_pps=200: en frio el ataque se aprende como\n#               base). [REINICIO-R3-FLUJO-D322] Medido DAY322 en EMECAS+++: 3 marcas tras el reinicio que no eran del\n#               ataque sino dos AISLADO de 192.168.100.12 (manager de Wazuh) -> .1 por TCP (ratio 3,19 >= k_in), sin\n#               episodio ni bloqueo; el R3 viejo contaba TODAS las marcas y fallo. Ahora, en el log del firewall tras\n#               linea_fw_parado: 0 INICIO y 0 eventos AISLADO del flujo del ataque (victima 192.168.100.1 proto 17),\n#               y las marcas del ml-detector tras el corte = eventos AISLADO de los demas flujos (todas explicadas).\n#               Los demas flujos salen como dato (no decide). Los FIN no cuentan: el del episodio del ataque, empezado\n#               antes del reinicio, puede imprimirse despues del corte con los eventos de antes.\n#     ordenada/kill9: marcados_despues >= 0,5 x marcados_antes. Frontera entre los dos regimenes posibles:\n#               con estado ~1,2-1,3 (DAY300: 1,305 y 1,236), sin estado 0. La banda 1,15-1,40 se imprime\n#               como dato y NO decide (depende de lo que tarde vagrant ssh en parar el sniffer).\n"
],
[
"fi\n[ -n \"$L\" ] || { echo \"[VEREDICTO] FALLA: sin linea de corte en $T\"; exit 1; }\necho \"[VEREDICTO] modo=$MODO corrida=$D corte_ml=$L\"\n\nset -- $(awk -v L=\"$L\" '/\\[DDOS-V2\\] bajo_presion=/ {\n    t = 0\n",
"fi\n[ -n \"$L\" ] || { echo \"[VEREDICTO] FALLA: sin linea de corte en $T\"; exit 1; }\necho \"[VEREDICTO] modo=$MODO corrida=$D corte_ml=$L\"\n# [REINICIO-R3-FLUJO-D322] flujo del ataque de d300_reinicio_client.sh (reflexion NTP y base DNS/NTP: UDP a .1)\nVICT=192.168.100.1; PROTO=17\nLF=$(awk '$1==\"linea_fw_parado\"{print $2}' \"$T\" | tail -n 1)\n\nset -- $(awk -v L=\"$L\" '/\\[DDOS-V2\\] bajo_presion=/ {\n    t = 0\n"
],
[
"# R3\nRAZON=$(awk -v a=\"$MA\" -v d=\"$MD\" 'BEGIN { if (a > 0) printf \"%.3f\", d / a; else print \"n/a\" }')\ncase \"$MODO\" in\n  antes) if [ \"$MD\" -eq 0 ]; then ok \"R3 marcado: antes=$MA despues=$MD (en frio, 0 tras el reinicio)\"\n         else ko \"R3 marcado: $MD marcados tras el reinicio con el CSV borrado (esperado 0); antes=$MA\"; fi ;;\n  *)     if [ \"$MA\" -gt 0 ] && [ $((2 * MD)) -ge \"$MA\" ]; then ok \"R3 marcado: antes=$MA despues=$MD razon=$RAZON (frontera 0,5)\"\n         else ko \"R3 marcado: antes=$MA despues=$MD razon=$RAZON (frontera 0,5: el estado no se restauro)\"; fi ;;\nesac\n",
"# R3\nRAZON=$(awk -v a=\"$MA\" -v d=\"$MD\" 'BEGIN { if (a > 0) printf \"%.3f\", d / a; else print \"n/a\" }')\ncase \"$MODO\" in\n  antes)\n    if ! [[ \"$LF\" =~ ^[0-9]+$ ]]; then\n      ko \"R3 marcado: sin linea_fw_parado en $T (corrida anterior a DAY322: no se puede separar el ataque de los demas flujos)\"\n    else\n      set -- $(awk -v L=\"$LF\" -v V=\"$VICT\" -v P=\"$PROTO\" 'NR > L && /\\[SOMBRA-DDOS\\] (INICIO|AISLADO) / {\n          v = \"\"; p = \"\"; e = 0\n          for (i = 1; i <= NF; i++) { split($i, a, \"=\")\n            if (a[1] == \"victima\") v = a[2]; if (a[1] == \"proto\") p = a[2]; if (a[1] == \"eventos_drop\") e = a[2] + 0 }\n          ini = ($0 ~ /\\[SOMBRA-DDOS\\] INICIO /)\n          if (v == V && p == P) { if (ini) ai++; else aa += e } else if (!ini) aj += e }\n        END { printf \"%d %d %d\\n\", ai, aa, aj }' \"$F\")\n      AI=${1:-0}; AA=${2:-0}; AJ=${3:-0}\n      if [ \"$AI\" -eq 0 ] && [ \"$AA\" -eq 0 ] && [ \"$MD\" -eq \"$AJ\" ]; then\n        ok \"R3 marcado: antes=$MA; tras el reinicio 0 del ataque ($VICT proto $PROTO, en frio) y $MD marcas, todas aislados de otros flujos ($AJ)\"\n      else\n        ko \"R3 marcado: tras el reinicio el ataque ($VICT proto $PROTO) tiene $AI INICIO y $AA eventos aislados (esperado 0 y 0); marcas del ml-detector $MD, aislados de otros flujos $AJ (tienen que ser iguales); antes=$MA\"\n      fi\n      awk -v L=\"$LF\" -v V=\"$VICT\" -v P=\"$PROTO\" 'NR > L && /\\[SOMBRA-DDOS\\] AISLADO / {\n          v = \"\"; p = \"\"; e = \"\"; o = \"\"\n          for (i = 1; i <= NF; i++) { split($i, a, \"=\")\n            if (a[1] == \"victima\") v = a[2]; if (a[1] == \"proto\") p = a[2]; if (a[1] == \"eventos_drop\") e = a[2]\n            if (a[1] == \"origenes\") o = substr($i, 10) }\n          if (!(v == V && p == P)) printf \"[VEREDICTO] dato (no decide): tras el reinicio, aislado de otro flujo victima=%s proto=%s eventos_drop=%s origenes=%s\\n\", v, p, e, o }' \"$F\"\n    fi ;;\n  *)     if [ \"$MA\" -gt 0 ] && [ $((2 * MD)) -ge \"$MA\" ]; then ok \"R3 marcado: antes=$MA despues=$MD razon=$RAZON (frontera 0,5)\"\n         else ko \"R3 marcado: antes=$MA despues=$MD razon=$RAZON (frontera 0,5: el estado no se restauro)\"; fi ;;\nesac\n"
]
]
}
],
"nuevos": []
}''')
def sha(t): return hashlib.sha256(t.encode()).hexdigest()
def leer(p):
    try: return open(p, encoding="utf-8").read()
    except FileNotFoundError: return None
def plan():
    acciones, errores = [], []
    for c in D["cambios"]:
        t = leer(c["ruta"])
        if t is None: errores.append(f"{c['ruta']}: no existe"); continue
        h = sha(t)
        if h == c["sha_despues"]: print(f"  ya parcheado  {c['ruta']}"); continue
        if h != c["sha_antes"]:
            errores.append(f"{c['ruta']}: sha256 {h[:16]} no es el de partida ({c['sha_antes'][:16]}) ni el parcheado"); continue
        for o, n in c["trozos"]: t = t.replace(o, n, 1)
        assert sha(t) == c["sha_despues"]
        acciones.append((c["ruta"], t, None)); print(f"  se parchea    {c['ruta']} ({len(c['trozos'])} trozos)")
    for n in D["nuevos"]:
        t = leer(n["ruta"])
        if t == n["contenido"]: print(f"  ya está       {n['ruta']}"); continue
        if t is not None: errores.append(f"{n['ruta']}: existe con otro contenido"); continue
        acciones.append((n["ruta"], n["contenido"], n["modo"])); print(f"  se crea       {n['ruta']}")
    return acciones, errores
def escribir(ruta, texto, modo):
    d = os.path.dirname(ruta) or "."
    os.makedirs(d, exist_ok=True)
    m = modo if modo is not None else (os.stat(ruta).st_mode & 0o777)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".d322_")
    with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(texto)
    os.chmod(tmp, m); os.replace(tmp, ruta)
if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: python3 scripts/etcd_ha/d322_reinicio_r3.py --check | --apply"); sys.exit(2)
    if not os.path.isfile("Vagrantfile") or not os.path.isdir("scripts/etcd_ha"):
        print("[D322] FALLA: hay que lanzarlo desde la raíz del repo"); sys.exit(2)
    acciones, errores = plan()
    if errores:
        print("[D322] FALLA, no se toca nada:"); [print("  - " + e) for e in errores]; sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"[D322] check OK: {len(acciones)} fichero(s) por escribir"); sys.exit(0)
    for r, t, m in acciones: escribir(r, t, m)
    print(f"[D322] apply OK: {len(acciones)} fichero(s) escrito(s)")
