#!/usr/bin/env python3
# d322_vault_arranque_b.py — DAY322 [VAULT-ARRANQUE-D322], segunda parte (sobre el commit 31ae20e62):
#   - Falco: argus_lab_lee_fichero solo cuenta opens con ÉXITO (fd.num>=0, como open_read del reglamento oficial).
#     Medido DAY322: GNU install hace openat(destino, O_RDONLY|O_PATH|O_DIRECTORY), falla y daba un CRITICAL.
#   - vault_arranque_instalar.sh: con el mismo certificado ya puesto no reescribe la identidad (ni lee la clave instalada
#     ni dispara el FIM de Wazuh en cada vagrant up).
#   - d322_reinicio_vault.sh: "unidades fallidas:" solo si hay alguna.
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d322_vault_arranque_b.py --check | --apply
# Todo o nada: --check comprueba que cada fichero está en su estado de partida (sha256) o ya parcheado; --apply escribe
# todo solo si --check pasa. Idempotente: dos --apply dejan lo mismo.
import hashlib, json, os, sys, tempfile
D = json.loads(r'''{
"cambios": [
{
"ruta": "provisioning/falco/argus_lab.yaml",
"sha_antes": "ba8ba34ac349490551057bc8eea1762fe97505a300c553f8e76fbdaf55f2f99c",
"sha_despues": "534bc576a9a304a73a94bc35280dcf1e0f66204cc518b7378607532b598460ba",
"trozos": [
[
"  tags: [argus, exec, adr-060]\n\n# ── 2. Lectura de una clave o una semilla ──────────────────────────────────────────────────────────────────────────\n- macro: argus_lab_lee_fichero\n  condition: evt.type in (open, openat, openat2) and evt.is_open_read=true and fd.typechar=f\n\n- macro: argus_lab_fichero_secreto\n  condition: >\n",
"  tags: [argus, exec, adr-060]\n\n# ── 2. Lectura de una clave o una semilla ──────────────────────────────────────────────────────────────────────────\n# [VAULT-ARRANQUE-D322] fd.num>=0: solo un open que TUVO ÉXITO (como la macro open_read del reglamento oficial de Falco).\n# Medido DAY322: GNU install hace openat(destino, O_RDONLY|O_PATH|O_DIRECTORY) para saber si es un directorio; falla\n# (ENOENT/ENOTDIR), no lee nada y daba un CRITICAL al instalar una clave.\n- macro: argus_lab_lee_fichero\n  condition: evt.type in (open, openat, openat2) and evt.is_open_read=true and fd.typechar=f and fd.num>=0\n\n- macro: argus_lab_fichero_secreto\n  condition: >\n"
]
]
},
{
"ruta": "scripts/etcd_ha/vault_arranque_instalar.sh",
"sha_antes": "2392dc98f5889551148bbc260663c58db49f1356d766ce89f5b5268a0af9645c",
"sha_despues": "c3c080d3398fc3b81726d0e15200507db54e5d55fb943a5ed6fd5e63c29d9e52",
"trozos": [
[
"  P_CRT=$(openssl x509 -in \"$PKI_IN/argus-vault-unseal.crt\" -noout -pubkey | openssl sha256 | awk '{print $NF}')\n  P_KEY=$(openssl pkey -in \"$PKI_IN/argus-vault-unseal.key\" -pubout | openssl sha256 | awk '{print $NF}')\n  [ \"$P_CRT\" = \"$P_KEY\" ] || fallo \"argus-vault-unseal.key no casa con argus-vault-unseal.crt\"\n  install -m 0644 -o root -g root \"$PKI_IN/argus-vault-unseal.crt\" \"$CRT\"\n  install -m 0600 -o root -g root \"$PKI_IN/argus-vault-unseal.key\" \"$KEY\"\n  rm -rf \"$PKI_IN\"\nfi\n[ -s \"$CRT\" ] && [ -s \"$KEY\" ] || fallo \"faltan $CRT o $KEY; en el Mac: bash scripts/etcd_ha/d312_pki.sh cliente \\$ARGUS_PKI_DIR argus-vault-unseal\"\n",
"  P_CRT=$(openssl x509 -in \"$PKI_IN/argus-vault-unseal.crt\" -noout -pubkey | openssl sha256 | awk '{print $NF}')\n  P_KEY=$(openssl pkey -in \"$PKI_IN/argus-vault-unseal.key\" -pubout | openssl sha256 | awk '{print $NF}')\n  [ \"$P_CRT\" = \"$P_KEY\" ] || fallo \"argus-vault-unseal.key no casa con argus-vault-unseal.crt\"\n  # Mismo certificado (público) ya puesto y clave presente: no se reescribe nada. La clave instalada no se lee para\n  # compararla (sería una lectura ajena para Falco) y reescribirla en cada `vagrant up` dispararía el FIM de Wazuh.\n  if [ -s \"$KEY\" ] && [ -f \"$CRT\" ] && cmp -s \"$PKI_IN/argus-vault-unseal.crt\" \"$CRT\"; then\n    log \"identidad sin cambios (mismo certificado): no se reinstala\"\n  else\n    install -m 0644 -o root -g root \"$PKI_IN/argus-vault-unseal.crt\" \"$CRT\"\n    install -m 0600 -o root -g root \"$PKI_IN/argus-vault-unseal.key\" \"$KEY\"\n    log \"identidad instalada en $PKI\"\n  fi\n  rm -rf \"$PKI_IN\"\nfi\n[ -s \"$CRT\" ] && [ -s \"$KEY\" ] || fallo \"faltan $CRT o $KEY; en el Mac: bash scripts/etcd_ha/d312_pki.sh cliente \\$ARGUS_PKI_DIR argus-vault-unseal\"\n"
]
]
},
{
"ruta": "scripts/etcd_ha/d322_reinicio_vault.sh",
"sha_antes": "270de58ed7eaa309100516741f49f7745e0e5b5c45e6a87d280f42cc224ac49b",
"sha_despues": "8e648c24671f0aad9f175916d55c45f84d695a49395900e41b00281c0f1db3ed",
"trozos": [
[
"REINICIADO=si\nlog \"   VM de vuelta en $(( SECONDS - T0 )) s (boot_id $B); systemd: $(V \"timeout 120 systemctl is-system-running --wait\" | tail -n 1)\"\nV \"systemctl --failed --no-legend --plain\" > \"$T\"\n[ -s \"$T\" ] && { log \"   unidades fallidas:\"; sed 's/^/     /' \"$T\"; }\n\nlog \"4 arranque (R1-R4)\"\nV \"bash $H arranque\" > \"$T\"; pinta\n",
"REINICIADO=si\nlog \"   VM de vuelta en $(( SECONDS - T0 )) s (boot_id $B); systemd: $(V \"timeout 120 systemctl is-system-running --wait\" | tail -n 1)\"\nV \"systemctl --failed --no-legend --plain\" > \"$T\"\ngrep -q '[^[:space:]]' \"$T\" && { log \"   unidades fallidas:\"; grep '[^[:space:]]' \"$T\" | sed 's/^/     /'; }\n\nlog \"4 arranque (R1-R4)\"\nV \"bash $H arranque\" > \"$T\"; pinta\n"
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
        print("uso: python3 scripts/etcd_ha/d322_vault_arranque_b.py --check | --apply"); sys.exit(2)
    if not os.path.isfile("Vagrantfile") or not os.path.isdir("scripts/etcd_ha"):
        print("[D322] FALLA: hay que lanzarlo desde la raíz del repo"); sys.exit(2)
    acciones, errores = plan()
    if errores:
        print("[D322] FALLA, no se toca nada:"); [print("  - " + e) for e in errores]; sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"[D322] check OK: {len(acciones)} fichero(s) por escribir"); sys.exit(0)
    for r, t, m in acciones: escribir(r, t, m)
    print(f"[D322] apply OK: {len(acciones)} fichero(s) escrito(s)")
