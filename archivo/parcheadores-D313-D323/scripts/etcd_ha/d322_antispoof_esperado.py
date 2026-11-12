#!/usr/bin/env python3
# d322_antispoof_esperado.py — DAY322 [PROTEGIDOS-BOOTSTRAP-D322]: lab-e2e-antispoof saca lo esperado (redes, ips_mac,
# mac) del manifiesto publicado en vez de llevarlo escrito (era de la v11 del lab). Medido en EMECAS+++ DAY322: con la
# v1 de la plantilla, .20 lleva su MAC y el firewall dio redes=3 ips_mac=2 mac=2; el test esperaba 1 y 1 y paró.
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d322_antispoof_esperado.py --check | --apply
# Todo o nada: --check comprueba que cada fichero está en su estado de partida (sha256) o ya parcheado; --apply escribe
# todo solo si --check pasa. Idempotente: dos --apply dejan lo mismo.
import hashlib, json, os, sys, tempfile
D = json.loads(r'''{
"cambios": [
{
"ruta": "scripts/etcd_ha/d320_antispoof_e2e.sh",
"sha_antes": "c8e9f504385e602a57dec4d6f0645dbcae5188d862153be46c6dc94ba87ec260",
"sha_despues": "b3173bbcdf356bb4b82c000d9920192a299f03e11a26519ea2a9d6a846ffe33a",
"trozos": [
[
"#\n# PREDICCIÓN (escrita antes de la corrida): S1-S4 PASA; el antispoofing se aplica en modo descarta con redes=3\n# (.20, .61, .62), ips_mac=1, mac=1 y sin_ruta=0.\nset -u\nN=${1:?nombre de la corrida}\nexport DIA=${DIA:-day320}\n",
"#\n# PREDICCIÓN (escrita antes de la corrida): S1-S4 PASA; el antispoofing se aplica en modo descarta con redes=3\n# (.20, .61, .62), ips_mac=1, mac=1 y sin_ruta=0.\n# [PROTEGIDOS-BOOTSTRAP-D322] lo esperado (redes, ips_mac, mac) ya no va escrito aquí: sale del manifiesto publicado\n# tras dar de alta .62 (argus-infra list), contado como el firewall (protegidos_antispoof.hpp: redes distintas, IPs /32\n# distintas con MAC, pares IP,MAC distintos). Medido DAY322 en EMECAS+++: con la v1 de la plantilla, .20 lleva su MAC\n# (08:00:27:a2:00:20) y el firewall dio redes=3 ips_mac=2 mac=2; el 1 y 1 escritos aquí eran de la v11 del lab.\nset -u\nN=${1:?nombre de la corrida}\nexport DIA=${DIA:-day320}\n"
],
[
"\npaso \"2 entrada de prueba $IP62 por eth2 con MAC $MAL (argus-infra, VM etcd)\"\ninfra \"add --planta lab-vagrant --categoria intranet --cidr $IP62/32 --interfaz eth2 --mac $MAL --motivo-entrada 'prueba antispoof DAY320' --motivo 'prueba antispoof DAY320 (se quita al acabar)' --si\" | tail -n 4\ninfra \"list\" | grep -q \"$IP62/32\" || falla \"argus-infra no publicó $IP62\"\nENTRADA62=1\n\npaso \"3 pipeline-stop y conmutador SOLO para la prueba (copia exacta en $BAK)\"\n",
"\npaso \"2 entrada de prueba $IP62 por eth2 con MAC $MAL (argus-infra, VM etcd)\"\ninfra \"add --planta lab-vagrant --categoria intranet --cidr $IP62/32 --interfaz eth2 --mac $MAL --motivo-entrada 'prueba antispoof DAY320' --motivo 'prueba antispoof DAY320 (se quita al acabar)' --si\" | tail -n 4\ninfra \"list\" > \"/tmp/${N}_lista.txt\"\ngrep -q \"$IP62/32\" \"/tmp/${N}_lista.txt\" || falla \"argus-infra no publicó $IP62\"\nread -r ER EI EM < <(awk '$1 ~ /^(infraestructura|intranet|dmz|externos_criticos)$/ && $2 ~ /\\// {\n    if (!($2 in vred)) { vred[$2] = 1; r++ }\n    m = \"\"; for (i = 4; i <= NF; i++) if ($i ~ /^mac=/) m = substr($i, 5)\n    if (m != \"\" && m != \"-\" && $2 ~ /\\/32$/) { ip = substr($2, 1, length($2) - 3)\n      if (!(ip in vip)) { vip[ip] = 1; ni++ }; if (!((ip \",\" m) in vpar)) { vpar[ip \",\" m] = 1; nm++ } } }\n  END { printf \"%d %d %d\\n\", r, ni, nm }' \"/tmp/${N}_lista.txt\")\n[[ \"$ER\" =~ ^[1-9][0-9]*$ ]] && [[ \"$EI\" =~ ^[0-9]+$ ]] && [[ \"$EM\" =~ ^[0-9]+$ ]] \\\n  || falla \"no leo del manifiesto publicado cuántas redes e IPs con MAC esperar (/tmp/${N}_lista.txt)\"\necho \"    esperado del manifiesto publicado: redes=$ER ips_mac=$EI mac=$EM\"\nENTRADA62=1\n\npaso \"3 pipeline-stop y conmutador SOLO para la prueba (copia exacta en $BAK)\"\n"
],
[
"paso \"5 antispoofing en modo descarta con la entrada de prueba (máximo 120 s)\"\nok=0\nfor i in $(seq 1 120); do\n  if grep -E \"\\[PROTEGIDOS-ANTISPOOF\\] aplicado .*modo=descarta redes=3 ips_mac=1 mac=1\" \"$F\" > /dev/null 2>&1 && \\\n     vm defender \"sudo ipset save $SM | grep -qi '$IP62,$MAL'\"; then ok=1; break; fi\n  sleep 1\ndone\ngrep \"\\[PROTEGIDOS-ANTISPOOF\\]\" \"$F\" | tail -n 3\n[ \"$ok\" = 1 ] || falla \"no aparece el antispoofing en modo descarta con redes=3 ips_mac=1 mac=1 y $IP62 en $SM\"\nvm defender \"sudo iptables -w -t raw -S PREROUTING | sed -n 2p; sudo iptables -w -t raw -S $AS; sudo iptables -w -t raw -S ${AS}_MAC\" | sed 's/^/    /'\nI0=$(cuenta \"${AS}_IF\"); M0=$(cuenta \"${AS}_MAC\")\nP0=$(vm defender \"sudo ipset save $WL | awk '\\$3 ~ /^192\\\\.168\\\\.100\\\\.20,/ {for (i = 4; i < NF; i++) if (\\$i == \\\"packets\\\") print \\$(i + 1)}'\")\n",
"paso \"5 antispoofing en modo descarta con la entrada de prueba (máximo 120 s)\"\nok=0\nfor i in $(seq 1 120); do\n  if grep -E \"\\[PROTEGIDOS-ANTISPOOF\\] aplicado .*modo=descarta redes=$ER ips_mac=$EI mac=$EM( |$)\" \"$F\" > /dev/null 2>&1 && \\\n     vm defender \"sudo ipset save $SM | grep -qi '$IP62,$MAL'\"; then ok=1; break; fi\n  sleep 1\ndone\ngrep \"\\[PROTEGIDOS-ANTISPOOF\\]\" \"$F\" | tail -n 3\n[ \"$ok\" = 1 ] || falla \"no aparece el antispoofing en modo descarta con redes=$ER ips_mac=$EI mac=$EM y $IP62 en $SM\"\nvm defender \"sudo iptables -w -t raw -S PREROUTING | sed -n 2p; sudo iptables -w -t raw -S $AS; sudo iptables -w -t raw -S ${AS}_MAC\" | sed 's/^/    /'\nI0=$(cuenta \"${AS}_IF\"); M0=$(cuenta \"${AS}_MAC\")\nP0=$(vm defender \"sudo ipset save $WL | awk '\\$3 ~ /^192\\\\.168\\\\.100\\\\.20,/ {for (i = 4; i < NF; i++) if (\\$i == \\\"packets\\\") print \\$(i + 1)}'\")\n"
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
        print("uso: python3 scripts/etcd_ha/d322_antispoof_esperado.py --check | --apply"); sys.exit(2)
    if not os.path.isfile("Vagrantfile") or not os.path.isdir("scripts/etcd_ha"):
        print("[D322] FALLA: hay que lanzarlo desde la raíz del repo"); sys.exit(2)
    acciones, errores = plan()
    if errores:
        print("[D322] FALLA, no se toca nada:"); [print("  - " + e) for e in errores]; sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"[D322] check OK: {len(acciones)} fichero(s) por escribir"); sys.exit(0)
    for r, t, m in acciones: escribir(r, t, m)
    print(f"[D322] apply OK: {len(acciones)} fichero(s) escrito(s)")
