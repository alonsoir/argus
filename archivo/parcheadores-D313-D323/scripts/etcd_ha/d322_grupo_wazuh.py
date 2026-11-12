#!/usr/bin/env python3
# d322_grupo_wazuh.py — DAY322 [VIGILANCIA-GRUPO-D322]: lo que destapó lab-e2e-vigilancia en EMECAS+++ desde cero.
#   - wazuh_agente_instalar.sh: el agente pide su grupo al registrarse (grupos.tsv, WAZUH_AGENT_GROUP; decisión de
#     Alonso) y, conectado, comprueba que su agent.conf es el de su grupo. La VM etcd se crea después que la wazuh y su
#     agente se quedaba en "default" (sin FIM de /etc/argus-pki ni eventos de Falco: C1, C5, C6 y C8 fallaron).
#   - d322_reinicio_vault_vm.sh preparar: en una VM nueva logrotate no tiene entrada de audit.log; se crea (C7 falló).
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d322_grupo_wazuh.py --check | --apply
# Todo o nada: --check comprueba que cada fichero está en su estado de partida (sha256) o ya parcheado; --apply escribe
# todo solo si --check pasa. Idempotente: dos --apply dejan lo mismo.
import hashlib, json, os, sys, tempfile
D = json.loads(r'''{
"cambios": [
{
"ruta": "scripts/vigilancia/wazuh_agente_instalar.sh",
"sha_antes": "09cfe939169e9914e55ffcb807d5435d37f708dad406e8803c0effce2c5ec75e",
"sha_despues": "e4363c668062d9e6862bc133cf731b81c090722e894853f7034a23a6f2a583df",
"trozos": [
[
"# tardaron ~80 s en volver). Que no conecte se avisa pero no es fallo: la VM wazuh es autostart: false y puede estar\n# parada; el agente se conecta solo cuando el manager vuelve.\n# Una actualización conserva client.keys y ossec.conf (el registro sigue siendo el mismo agente).\nset -u\nLC_ALL=C; export LC_ALL\nSRC=${VIGILANCIA_SRC:-/vagrant/provisioning/wazuh}\n",
"# tardaron ~80 s en volver). Que no conecte se avisa pero no es fallo: la VM wazuh es autostart: false y puede estar\n# parada; el agente se conecta solo cuando el manager vuelve.\n# Una actualización conserva client.keys y ossec.conf (el registro sigue siendo el mismo agente).\n# [VIGILANCIA-GRUPO-D322] (decisión de Alonso) el agente PIDE su grupo al registrarse: lo busca por AGENT_NAME en\n# provisioning/wazuh/argus/grupos.tsv (la única fuente, la misma que lee el manager) y se instala con la variable\n# oficial WAZUH_AGENT_GROUP (el postinst del paquete la pone en <enrollment><groups> de ossec.conf). Medido DAY322 en\n# EMECAS+++ desde cero: la VM etcd se crea después que la wazuh, el manager asignaba los grupos al aprovisionarse y el\n# agente etcd se quedaba en \"default\" (sin FIM de /etc/argus-pki ni eventos de Falco). Un agente que no está en\n# grupos.tsv va a \"default\". Conectado al manager, su agent.conf tiene que ser el de su grupo; si no, FALLA.\nset -u\nLC_ALL=C; export LC_ALL\nSRC=${VIGILANCIA_SRC:-/vagrant/provisioning/wazuh}\n"
],
[
"[[ \"$V\" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+-[0-9]+$ ]] || fallo \"$SRC/VERSION mal formado ('$V'; formato X.Y.Z-N)\"\nM=$(tr -d '[:space:]' < \"$SRC/MANAGER\")\n[[ \"$M\" =~ ^([0-9]{1,3}\\.){3}[0-9]{1,3}$ ]] || fallo \"$SRC/MANAGER mal formado ('$M'; una IPv4)\"\n# shellcheck source=lib_apt_oficial.sh\n. \"$LIB\" || fallo \"no cargo $LIB\"\nlog \"agente '$NOMBRE', versión $V ($SRC/VERSION), manager $M ($SRC/MANAGER)\"\n\napunta() { grep -q \"<address>$M</address>\" \"$O/etc/ossec.conf\" 2>/dev/null; }\nen_marcha() { systemctl is-active --quiet wazuh-agent; }\n\n# 1 nada que hacer\nTENGO=$(dpkg-query -W -f='${Version}' wazuh-agent 2>/dev/null || true)\nFIJADO=$(apt-mark showhold wazuh-agent 2>/dev/null)\nif [ \"$TENGO\" = \"$V\" ] && [ \"$FIJADO\" = wazuh-agent ] && apunta && en_marcha; then\n  log \"OK: wazuh-agent $V ya instalado, fijado, apuntando a $M y en marcha; nada que hacer\"\n  exit 0\nfi\nlog \"estado: instalado '${TENGO:-ninguno}', hold '${FIJADO:-no}'\"\n",
"[[ \"$V\" =~ ^[0-9]+\\.[0-9]+\\.[0-9]+-[0-9]+$ ]] || fallo \"$SRC/VERSION mal formado ('$V'; formato X.Y.Z-N)\"\nM=$(tr -d '[:space:]' < \"$SRC/MANAGER\")\n[[ \"$M\" =~ ^([0-9]{1,3}\\.){3}[0-9]{1,3}$ ]] || fallo \"$SRC/MANAGER mal formado ('$M'; una IPv4)\"\nGT=$SRC/argus/grupos.tsv\n[ -r \"$GT\" ] || fallo \"no leo $GT\"\nGRUPO=$(awk -F'\\t' -v n=\"$NOMBRE\" '!/^#/ && NF == 2 && $1 == n {print $2; exit}' \"$GT\")\n[ -z \"$GRUPO\" ] || [[ \"$GRUPO\" =~ ^[a-z0-9-]{1,64}$ ]] || fallo \"grupo '$GRUPO' de '$NOMBRE' mal formado en $GT ([a-z0-9-], de 1 a 64)\"\n# shellcheck source=lib_apt_oficial.sh\n. \"$LIB\" || fallo \"no cargo $LIB\"\nlog \"agente '$NOMBRE', versión $V ($SRC/VERSION), manager $M ($SRC/MANAGER), grupo ${GRUPO:-default (no está en $GT)}\"\n\napunta() { grep -q \"<address>$M</address>\" \"$O/etc/ossec.conf\" 2>/dev/null; }\nen_marcha() { systemctl is-active --quiet wazuh-agent; }\npide_grupo() { [ -z \"$GRUPO\" ] || grep -q \"<groups>$GRUPO</groups>\" \"$O/etc/ossec.conf\" 2>/dev/null; }\ntiene_grupo() { [ -z \"$GRUPO\" ] || grep -qF \"Configuración centralizada del grupo $GRUPO\" \"$O/etc/shared/agent.conf\" 2>/dev/null; }\n\n# 1 nada que hacer\nTENGO=$(dpkg-query -W -f='${Version}' wazuh-agent 2>/dev/null || true)\nFIJADO=$(apt-mark showhold wazuh-agent 2>/dev/null)\nif [ \"$TENGO\" = \"$V\" ] && [ \"$FIJADO\" = wazuh-agent ] && apunta && en_marcha; then\n  log \"OK: wazuh-agent $V ya instalado, fijado, apuntando a $M y en marcha; nada que hacer\"\n  pide_grupo || log \"AVISO: registrado antes de [VIGILANCIA-GRUPO-D322], sin pedir el grupo $GRUPO: lo asigna make vigilancia-manager-deploy\"\n  tiene_grupo || log \"AVISO: su agent.conf aún no es el del grupo $GRUPO (¿manager parado o sin asignar? make vigilancia-manager-deploy)\"\n  exit 0\nfi\nlog \"estado: instalado '${TENGO:-ninguno}', hold '${FIJADO:-no}'\"\n"
],
[
"repo_oficial wazuh https://packages.wazuh.com/key/GPG-KEY-WAZUH \"$SRC/CLAVE\" \\\n  https://packages.wazuh.com/4.x/apt/ \"stable main\" || fallo \"repositorio de Wazuh\"\napt-get update -qq || fallo \"apt-get update\"\n# WAZUH_MANAGER/WAZUH_AGENT_NAME solo los usa una instalación nueva; una actualización conserva ossec.conf.\nWAZUH_MANAGER=\"$M\" WAZUH_AGENT_NAME=\"$NOMBRE\" instalar_fijado wazuh-agent \"$V\" || fallo \"instalación de wazuh-agent $V\"\n\n# 4 apunta a MANAGER y en marcha\napunta || fallo \"$O/etc/ossec.conf no apunta a $M (¿agente registrado antes con otro manager? revisar <client><server>)\"\n",
"repo_oficial wazuh https://packages.wazuh.com/key/GPG-KEY-WAZUH \"$SRC/CLAVE\" \\\n  https://packages.wazuh.com/4.x/apt/ \"stable main\" || fallo \"repositorio de Wazuh\"\napt-get update -qq || fallo \"apt-get update\"\n# WAZUH_MANAGER/WAZUH_AGENT_NAME/WAZUH_AGENT_GROUP solo los usa una instalación nueva; una actualización conserva\n# ossec.conf (vacía, WAZUH_AGENT_GROUP no pide grupo).\nWAZUH_MANAGER=\"$M\" WAZUH_AGENT_NAME=\"$NOMBRE\" WAZUH_AGENT_GROUP=\"$GRUPO\" instalar_fijado wazuh-agent \"$V\" \\\n  || fallo \"instalación de wazuh-agent $V\"\nif [ -z \"$TENGO\" ]; then\n  pide_grupo || fallo \"instalación nueva sin <groups>$GRUPO</groups> en $O/etc/ossec.conf (WAZUH_AGENT_GROUP no llegó)\"\nelse\n  pide_grupo || log \"AVISO: actualización de un agente registrado sin pedir el grupo $GRUPO: lo asigna make vigilancia-manager-deploy\"\nfi\n\n# 4 apunta a MANAGER y en marcha\napunta || fallo \"$O/etc/ossec.conf no apunta a $M (¿agente registrado antes con otro manager? revisar <client><server>)\"\n"
],
[
"done\nif grep -q \"^status='connected'\" \"$EST\" 2>/dev/null; then\n  log \"OK: wazuh-agent $V en marcha y conectado a $M\"\nelse\n  log \"AVISO: wazuh-agent $V en marcha pero sin conectar con $M en ${ESPERA_S} s ($(grep '^status=' \"$EST\" 2>/dev/null || echo \"sin $EST\")); ¿VM wazuh parada?\"\nfi\n",
"done\nif grep -q \"^status='connected'\" \"$EST\" 2>/dev/null; then\n  log \"OK: wazuh-agent $V en marcha y conectado a $M\"\n  # el manager manda el agent.conf del grupo tras conectar (medido DAY321: el reparto tarda unos segundos)\n  for ((i = 0; i < ESPERA_S; i += 5)); do tiene_grupo && break; sleep 5; done\n  tiene_grupo || fallo \"conectado a $M pero su agent.conf no es el del grupo $GRUPO en ${ESPERA_S} s (manager: agent_groups -s -i <id>)\"\n  [ -z \"$GRUPO\" ] || log \"OK: agent.conf del grupo $GRUPO recibido del manager\"\nelse\n  log \"AVISO: wazuh-agent $V en marcha pero sin conectar con $M en ${ESPERA_S} s ($(grep '^status=' \"$EST\" 2>/dev/null || echo \"sin $EST\")); ¿VM wazuh parada?\"\nfi\n"
]
]
},
{
"ruta": "scripts/etcd_ha/d322_reinicio_vault_vm.sh",
"sha_antes": "aa73077278f9dc8ec180a96d3f75b3db108d06ac5b5e00f7d9a67fc41953e04f",
"sha_despues": "d3821bf770e5d8349b6a3927abdb6ea4dca2e59b541a2d716e8009d74f43db2c",
"trozos": [
[
"  systemctl is-enabled --quiet logrotate.timer && ok \"logrotate.timer habilitado\" || falla \"logrotate.timer no está habilitado\"\n  ;;\npreparar)\n  sudo grep -q '^\"/var/log/vault/audit.log\" ' \"$ST\" || { falla \"$ST sin entrada de /var/log/vault/audit.log (sin ella logrotate no rota la primera vez)\"; exit 1; }\n  sudo test -s /var/log/vault/audit.log || { falla \"/var/log/vault/audit.log vacío (notifempty: no rotaría)\"; exit 1; }\n  sudo install -d -m 0700 \"$BK\"; sudo cp -p \"$ST\" \"$BK/status\"; sudo cp -p \"$SELLO\" \"$BK/sello\" 2>/dev/null || sudo touch \"$BK/sin_sello\"\n  sudo sed -i 's#^\"/var/log/vault/audit.log\" .*#\"/var/log/vault/audit.log\" 2000-1-1-0:0:0#' \"$ST\"\n  sudo touch -d '2 days ago' \"$SELLO\"\n  ok \"rotación pendiente: audit.log con última rotación 2000-1-1 y sello de logrotate.timer de hace 2 días (copia en $BK)\"\n  ;;\nrestaurar)\n  sudo test -d \"$BK\" || { ok \"nada que restaurar\"; exit 0; }\n  sudo cp -p \"$BK/status\" \"$ST\"\n  if sudo test -f \"$BK/sello\"; then sudo cp -p \"$BK/sello\" \"$SELLO\"; else sudo rm -f \"$SELLO\"; fi\n  sudo rm -rf \"$BK\"; ok \"restaurado el estado de logrotate y el sello del timer\"\n  ;;\n",
"  systemctl is-enabled --quiet logrotate.timer && ok \"logrotate.timer habilitado\" || falla \"logrotate.timer no está habilitado\"\n  ;;\npreparar)\n  # [VIGILANCIA-GRUPO-D322] medido DAY322 en EMECAS+++ desde cero: en una VM nueva logrotate aún no ha rotado nunca\n  # audit.log y su estado no tiene la entrada; se crea con fecha vieja (la copia de $BK la deshace con restaurar).\n  sudo test -s /var/log/vault/audit.log || { falla \"/var/log/vault/audit.log vacío (notifempty: no rotaría)\"; exit 1; }\n  sudo install -d -m 0700 \"$BK\"\n  if sudo test -f \"$ST\"; then sudo cp -p \"$ST\" \"$BK/status\"; else sudo touch \"$BK/sin_status\"; fi\n  sudo cp -p \"$SELLO\" \"$BK/sello\" 2>/dev/null || sudo touch \"$BK/sin_sello\"\n  if sudo grep -q '^\"/var/log/vault/audit.log\" ' \"$ST\" 2>/dev/null; then\n    sudo sed -i 's#^\"/var/log/vault/audit.log\" .*#\"/var/log/vault/audit.log\" 2000-1-1-0:0:0#' \"$ST\"\n  else\n    sudo test -f \"$ST\" || echo \"logrotate state -- version 2\" | sudo tee \"$ST\" > /dev/null\n    echo '\"/var/log/vault/audit.log\" 2000-1-1-0:0:0' | sudo tee -a \"$ST\" > /dev/null\n    ok \"sin entrada previa de audit.log en $ST (VM nueva): creada con fecha 2000-1-1\"\n  fi\n  sudo touch -d '2 days ago' \"$SELLO\"\n  ok \"rotación pendiente: audit.log con última rotación 2000-1-1 y sello de logrotate.timer de hace 2 días (copia en $BK)\"\n  ;;\nrestaurar)\n  sudo test -d \"$BK\" || { ok \"nada que restaurar\"; exit 0; }\n  if sudo test -f \"$BK/status\"; then sudo cp -p \"$BK/status\" \"$ST\"; else sudo rm -f \"$ST\"; fi\n  if sudo test -f \"$BK/sello\"; then sudo cp -p \"$BK/sello\" \"$SELLO\"; else sudo rm -f \"$SELLO\"; fi\n  sudo rm -rf \"$BK\"; ok \"restaurado el estado de logrotate y el sello del timer\"\n  ;;\n"
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
        print("uso: python3 scripts/etcd_ha/d322_grupo_wazuh.py --check | --apply"); sys.exit(2)
    if not os.path.isfile("Vagrantfile") or not os.path.isdir("scripts/etcd_ha"):
        print("[D322] FALLA: hay que lanzarlo desde la raíz del repo"); sys.exit(2)
    acciones, errores = plan()
    if errores:
        print("[D322] FALLA, no se toca nada:"); [print("  - " + e) for e in errores]; sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"[D322] check OK: {len(acciones)} fichero(s) por escribir"); sys.exit(0)
    for r, t, m in acciones: escribir(r, t, m)
    print(f"[D322] apply OK: {len(acciones)} fichero(s) escrito(s)")
