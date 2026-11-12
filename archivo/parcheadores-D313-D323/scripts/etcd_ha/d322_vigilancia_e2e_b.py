#!/usr/bin/env python3
# d322_vigilancia_e2e_b.py — DAY322 [VIGILANCIA-E2E-D322], sobre d322_vigilancia_e2e.py ya aplicado (sin commit):
#   - lab_e2e_vigilancia_etcd.sh falco-lineas: wc con la ruta como argumento (con "sudo wc -l < f" la redirección la
#     abría vagrant y salía vacío: medido DAY322).
#   - C8 pasa de medida a criterio (decisión de Alonso): trazas de Falco <= VIG_C8_MAX_TRAZAS (defecto 60, rango
#     [1, 100000]) y todas en el manager (alertas 100553 = trazas). Medido DAY322: 14 y 14.
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d322_vigilancia_e2e_b.py --check | --apply
# Todo o nada: --check comprueba que cada fichero está en su estado de partida (sha256) o ya parcheado; --apply escribe
# todo solo si --check pasa. Idempotente: dos --apply dejan lo mismo.
import hashlib, json, os, sys, tempfile
D = json.loads(r'''{
"cambios": [
{
"ruta": "scripts/vigilancia/lab_e2e_vigilancia.sh",
"sha_antes": "313b39bab62fef4ecc5c0ea0ddbf76426fc64f7a35f080f253b89a7fc150b661",
"sha_despues": "a599bddc1e765cef70fb4c5dc33f4388e84e8bd455f94c2c8b5b0a87546c4a45",
"trozos": [
[
"#   C6 Falco: leerla como nobody da la 100552 (argus_lab_clave_intento_fallido) en < 30 s.\n#   C8 MEDIDA (sin PASA/FALLA): etcd parado durante un etcd-vm-check (--esperar 30) deja unas 15 x 17 = 255 trazas\n#      NOTICE en Falco y otras tantas 100553 en el manager.\n#   C7 d322_reinicio_vault.sh PASA (R1-R6).\n#   C4 vigía: una divergencia (E1 de d320_vigia_e2e.sh) da la 100511 y luego la 100512 del agente defender.\n# Trap: deshace todo lo de la VM etcd (lab_e2e_vigilancia_etcd.sh restaurar); C4 y C7 llevan su propio trap. El\n# pipeline queda PARADO, como los demás E2E con la mitigación real (lab-e2e lo vuelve a arrancar al final).\n# Parámetros (entorno), enteros: VIG_ESPERA_S [10, 600] defecto 45 (espera de cada alerta); VIG_ESPERA_DISCO_S\n# [30, 900] defecto 120; VIG_ESPERA_ETCD_S [5, 300] defecto 30 (lo que espera el etcd-vm-check de C8).\nset -u\nLC_ALL=C; export LC_ALL\nN=${1:?nombre de la corrida}\n",
"#   C6 Falco: leerla como nobody da la 100552 (argus_lab_clave_intento_fallido) en < 30 s.\n#   C8 MEDIDA (sin PASA/FALLA): etcd parado durante un etcd-vm-check (--esperar 30) deja unas 15 x 17 = 255 trazas\n#      NOTICE en Falco y otras tantas 100553 en el manager.\n#      MEDIDO DAY322 (primera corrida): 14 trazas en Falco y 14 alertas 100553 (cada etcdctl espera su timeout: caben\n#      un par de vueltas en 36 s, no 15). Desde entonces es criterio (decisión de Alonso): trazas de Falco <=\n#      VIG_C8_MAX_TRAZAS y todas llegan al manager (alertas 100553 = trazas).\n#   C7 d322_reinicio_vault.sh PASA (R1-R6).\n#   C4 vigía: una divergencia (E1 de d320_vigia_e2e.sh) da la 100511 y luego la 100512 del agente defender.\n# Trap: deshace todo lo de la VM etcd (lab_e2e_vigilancia_etcd.sh restaurar); C4 y C7 llevan su propio trap. El\n# pipeline queda PARADO, como los demás E2E con la mitigación real (lab-e2e lo vuelve a arrancar al final).\n# Parámetros (entorno), enteros: VIG_ESPERA_S [10, 600] defecto 45 (espera de cada alerta); VIG_ESPERA_DISCO_S\n# [30, 900] defecto 120; VIG_ESPERA_ETCD_S [5, 300] defecto 30 (lo que espera el etcd-vm-check de C8);\n# VIG_C8_MAX_TRAZAS [1, 100000] defecto 60 (unas 4 veces lo medido DAY322: 14; otro despliegue puede necesitar más).\nset -u\nLC_ALL=C; export LC_ALL\nN=${1:?nombre de la corrida}\n"
],
[
"entero VIG_ESPERA_S \"${VIG_ESPERA_S:-}\" 45 10 600; ESPERA=$VAL\nentero VIG_ESPERA_DISCO_S \"${VIG_ESPERA_DISCO_S:-}\" 120 30 900; ESPERA_DISCO=$VAL\nentero VIG_ESPERA_ETCD_S \"${VIG_ESPERA_ETCD_S:-}\" 30 5 300; ESPERA_ETCD=$VAL\nmkdir -p \"$DM\"\nT=$(mktemp /tmp/vig_e2e.XXXXXX)\nFALLOS=0\n",
"entero VIG_ESPERA_S \"${VIG_ESPERA_S:-}\" 45 10 600; ESPERA=$VAL\nentero VIG_ESPERA_DISCO_S \"${VIG_ESPERA_DISCO_S:-}\" 120 30 900; ESPERA_DISCO=$VAL\nentero VIG_ESPERA_ETCD_S \"${VIG_ESPERA_ETCD_S:-}\" 30 5 300; ESPERA_ETCD=$VAL\nentero VIG_C8_MAX_TRAZAS \"${VIG_C8_MAX_TRAZAS:-}\" 60 1 100000; C8_MAX=$VAL\nmkdir -p \"$DM\"\nT=$(mktemp /tmp/vig_e2e.XXXXXX)\nFALLOS=0\n"
],
[
"log \"C6 intento fallido de leer una clave (Falco WARNING)\"\nmarca; etcd clave-intento; alerta etcd \"$ESPERA\" 100552 argus_lab_clave_intento_fallido\n\nlog \"C8 MEDIDA: trazas de un etcd-vm-check con etcd parado (sin PASA/FALLA)\"\nmarca; D8=$DESDE; I8=$INODO\nV etcd \"bash $HE falco-lineas\" > \"$T\"; L8=$(valor LINEAS)\netcd etcd-parar\nt0=$SECONDS\nV etcd \"bash /vagrant/scripts/etcd_ha/etcd_vm_estado.sh --estricto --esperar $ESPERA_ETCD\" > \"$DM/c8_etcd_vm_check.txt\"\nlog \"   etcd-vm-check con etcd parado: $(( SECONDS - t0 )) s ($(grep -c '' \"$DM/c8_etcd_vm_check.txt\") líneas en $DM/c8_etcd_vm_check.txt)\"\netcd etcd-arrancar\nsleep 20   # que el agente mande lo último\nV etcd \"bash /vagrant/scripts/etcd_ha/d322_medir_falco_admin.sh $L8\" > \"$DM/c8_falco.txt\"\nV wazuh \"bash $HW contar $D8 $I8 etcd 100553\" > \"$T\"; W8=$(valor CUENTA)\nlog \"   Falco (VM etcd), eventos desde la línea $L8:\"; grep -E '^ +[0-9]+ ' \"$DM/c8_falco.txt\" | sed 's/^/     /'\nlog \"   MEDIDA C8: alertas 100553 del agente etcd en el manager: ${W8:-?}\"\necho \"C8 alertas_100553=${W8:-?} espera_s=$ESPERA_ETCD\" >> \"$DM/medidas.txt\"\n\nlog \"C7 reinicio de Vault sin Vagrant (d322_reinicio_vault.sh)\"\nbash scripts/etcd_ha/d322_reinicio_vault.sh > \"$DM/c7_reinicio_vault.txt\" 2>&1; r=$?\n",
"log \"C6 intento fallido de leer una clave (Falco WARNING)\"\nmarca; etcd clave-intento; alerta etcd \"$ESPERA\" 100552 argus_lab_clave_intento_fallido\n\nlog \"C8 trazas de un etcd-vm-check con etcd parado (máximo $C8_MAX, y todas en el manager)\"\nmarca; D8=$DESDE; I8=$INODO\nV etcd \"bash $HE falco-lineas\" > \"$T\"; pinta; L8=$(valor LINEAS)\nif ! [[ \"$L8\" =~ ^[0-9]+$ ]]; then\n  echo \"  ❌ C8 sin el nº de líneas de partida de Falco: no se mide\"; FALLOS=$((FALLOS + 1))\nelse\n  etcd etcd-parar\n  t0=$SECONDS\n  V etcd \"bash /vagrant/scripts/etcd_ha/etcd_vm_estado.sh --estricto --esperar $ESPERA_ETCD\" > \"$DM/c8_etcd_vm_check.txt\"\n  log \"   etcd-vm-check con etcd parado: $(( SECONDS - t0 )) s ($DM/c8_etcd_vm_check.txt)\"\n  etcd etcd-arrancar\n  V etcd \"bash /vagrant/scripts/etcd_ha/d322_medir_falco_admin.sh $L8\" > \"$DM/c8_falco.txt\"\n  log \"   Falco (VM etcd), eventos desde la línea $L8:\"; grep -E '^ +[0-9]+ ' \"$DM/c8_falco.txt\" | sed 's/^/     /'\n  F8=$(grep -E '^ +[0-9]+  argus_lab_clave_leida_admin \\(Notice\\)$' \"$DM/c8_falco.txt\" | awk '{print $1}' | head -n 1)\n  F8=${F8:-0}\n  W8=\"\"; t0=$SECONDS   # que el agente mande lo último: hasta ESPERA s a que el manager tenga las F8\n  while :; do\n    V wazuh \"bash $HW contar $D8 $I8 etcd 100553\" > \"$T\"; W8=$(valor CUENTA)\n    [[ \"$W8\" =~ ^[0-9]+$ ]] && [ \"$W8\" -ge \"$F8\" ] && break\n    [ $(( SECONDS - t0 )) -ge \"$ESPERA\" ] && break\n    sleep 3\n  done\n  echo \"C8 trazas_falco=$F8 alertas_100553=${W8:-?} maximo=$C8_MAX espera_s=$ESPERA_ETCD\" >> \"$DM/medidas.txt\"\n  if [ \"$F8\" -le \"$C8_MAX\" ] && [ \"${W8:-x}\" = \"$F8\" ]; then\n    echo \"  ✅ C8 $F8 trazas NOTICE en Falco (máximo $C8_MAX) y las $W8 en el manager (100553)\"\n  else\n    echo \"  ❌ C8 $F8 trazas en Falco (máximo $C8_MAX), ${W8:-?} alertas 100553 en el manager (tienen que ser las mismas)\"\n    FALLOS=$((FALLOS + 1))\n  fi\nfi\n\nlog \"C7 reinicio de Vault sin Vagrant (d322_reinicio_vault.sh)\"\nbash scripts/etcd_ha/d322_reinicio_vault.sh > \"$DM/c7_reinicio_vault.txt\" 2>&1; r=$?\n"
]
]
},
{
"ruta": "scripts/vigilancia/lab_e2e_vigilancia_etcd.sh",
"sha_antes": "a52caccad70333aaa683998345ef87e93f7aca947fa895985b48c3b03013dfd1",
"sha_despues": "a11eb5acb51939f55e3c5742d0ecf00c3c93a92fabe2ed7aff90b553fae936fa",
"trozos": [
[
"etcd-parar)   sudo systemctl stop etcd && ok \"etcd parado\" || mal \"systemctl stop etcd\";;\netcd-arrancar)\n  sudo systemctl start etcd && systemctl is-active --quiet etcd && ok \"etcd en marcha\" || mal \"etcd no arranca\";;\nfalco-lineas) echo \"E2E|LINEAS|$(sudo wc -l < \"$EVENTOS\")\";;\nrestaurar)\n  sudo rm -f \"$PRUEBA\" \"$COPIA\"\n  sudo chattr -i \"$AUDIT\" 2>/dev/null\n",
"etcd-parar)   sudo systemctl stop etcd && ok \"etcd parado\" || mal \"systemctl stop etcd\";;\netcd-arrancar)\n  sudo systemctl start etcd && systemctl is-active --quiet etcd && ok \"etcd en marcha\" || mal \"etcd no arranca\";;\nfalco-lineas)  # wc con la ruta como argumento: con \"sudo wc -l < f\" la redirección la abre vagrant (medido DAY322)\n  n=$(sudo wc -l \"$EVENTOS\" 2>/dev/null | awk '{print $1}')\n  [[ \"$n\" =~ ^[0-9]+$ ]] && echo \"E2E|LINEAS|$n\" || mal \"no leo el nº de líneas de $EVENTOS\";;\nrestaurar)\n  sudo rm -f \"$PRUEBA\" \"$COPIA\"\n  sudo chattr -i \"$AUDIT\" 2>/dev/null\n"
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
        print("uso: python3 scripts/etcd_ha/d322_vigilancia_e2e_b.py --check | --apply"); sys.exit(2)
    if not os.path.isfile("Vagrantfile") or not os.path.isdir("scripts/etcd_ha"):
        print("[D322] FALLA: hay que lanzarlo desde la raíz del repo"); sys.exit(2)
    acciones, errores = plan()
    if errores:
        print("[D322] FALLA, no se toca nada:"); [print("  - " + e) for e in errores]; sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"[D322] check OK: {len(acciones)} fichero(s) por escribir"); sys.exit(0)
    for r, t, m in acciones: escribir(r, t, m)
    print(f"[D322] apply OK: {len(acciones)} fichero(s) escrito(s)")
