#!/usr/bin/env python3
# d324_vigilancia_nodos.py — DAY324, PR2b paso 6 de DEBT-ETCD-HA-TLS-RAFT-001 [PLANO-CONTROL-D324]: la vigilancia (Falco,
# argus-disco, agente de Wazuh) en TODOS los nodos del plano de control, no solo en control-1. Decisión de Alonso DAY324
# (opción i): hasta el PR2c los nodos sin Vault usan provisioning/vigilancia/disco-sin-vault.json (solo /var/lib/etcd),
# porque con el estricto /var/log/vault inexistente es ARGUS-DISCO-ERROR; en el PR2c se borra. Cambia: el Vagrantfile
# (la vigilancia sale del 'if primero'; AGENT_NAME = el nodo; VIGILANCIA_DISCO_JSON por nodo), argus_disco_instalar.sh
# (lee VIGILANCIA_DISCO_JSON, validado; defecto disco.json), grupos.tsv (control-2 y control-3 en argus-control) y
# test_argus_disco.py (el JSON nuevo del repo es válido). Antes, en su sitio: provisioning/vigilancia/disco-sin-vault.json.
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_vigilancia_nodos.py
import hashlib
import os
import sys

VF = "Vagrantfile"
INS = "scripts/vigilancia/argus_disco_instalar.sh"
GT = "provisioning/wazuh/argus/grupos.tsv"
TAD = "scripts/vigilancia/test_argus_disco.py"
PARTIDA = {
    VF: "2269fcc45f0da7d547a80f73c9a36bacfe6082c43aacb3996d8143ba9de31be2",
    INS: "5065034c09ff77d63e5ca9960bbe5724f61374a47327da47cbf624b195786dd1",
    GT: "61bacb33ed2ecd4d39998e736595e850bee971ca6c182f894cea107d71162cd1",
    TAD: "688d48eaa77c0a046f14328c6d7bff97b1462c42d24b3474d7ce5aecba2a29dd",
}
NUEVOS = {"provisioning/vigilancia/disco-sin-vault.json": "fe9af36a4d9d2968aa695779a22c68865c75870f87315b96a7d1cd88446e4dba"}

VIG_VIEJO = '''    # [VIGILANCIA-D321] ADR-060 8e.4d (H-I): los sensores de la VM etcd, todo o nada cada uno y run: always (con todo ya
    # puesto no cambian nada). Falco desde su apt firmado (provisioning/falco/VERSION) con las reglas de aRGus;
    # argus-disco (uso del disco del audit de Vault); el agente de Wazuh (grupo argus-control: lo asigna el manager en
    # make vigilancia-manager-deploy, provisioning/wazuh/argus/grupos.tsv).
    etcd.vm.provision "shell", name: "falco", run: "always", inline: "bash /vagrant/scripts/vigilancia/falco_instalar.sh"
    etcd.vm.provision "shell", name: "argus-disco", run: "always",
      inline: "bash /vagrant/scripts/vigilancia/argus_disco_instalar.sh"
    etcd.vm.provision "shell", name: "wazuh-agent", run: "always", env: {"AGENT_NAME" => "control-1"},
      inline: WAZUH_AGENT_INSTALL

    end  # if primero
'''
VIG_NUEVO = '''    end  # if primero

    # [VIGILANCIA-D321] ADR-060 8e.4d (H-I): los sensores de CADA nodo del plano de control [PLANO-CONTROL-D324 paso 6],
    # todo o nada cada uno y run: always (con todo ya puesto no cambian nada). Falco desde su apt firmado
    # (provisioning/falco/VERSION) con las reglas de aRGus; argus-disco (discos del audit de Vault y de los datos de
    # etcd); el agente de Wazuh, que se registra con el nombre del nodo y pide su grupo (argus-control) de
    # provisioning/wazuh/argus/grupos.tsv. [DISCO-RUTAS-D324] Hasta el PR2c solo control-1 tiene Vault: los demás usan
    # disco-sin-vault.json (solo /var/lib/etcd; con el estricto, /var/log/vault inexistente sería ARGUS-DISCO-ERROR).
    # En el PR2c (Vault en todos los nodos) se borran ese fichero y esta elección.
    etcd.vm.provision "shell", name: "falco", run: "always", inline: "bash /vagrant/scripts/vigilancia/falco_instalar.sh"
    etcd.vm.provision "shell", name: "argus-disco", run: "always",
      env: { "VIGILANCIA_DISCO_JSON" => (primero ? "disco.json" : "disco-sin-vault.json") },
      inline: "bash /vagrant/scripts/vigilancia/argus_disco_instalar.sh"
    etcd.vm.provision "shell", name: "wazuh-agent", run: "always", env: {"AGENT_NAME" => nodo["nombre"]},
      inline: WAZUH_AGENT_INSTALL
'''

CAMBIOS = {
    VF: [
        ("    if primero  # [PLANO-CONTROL-D324] etcd-server, argus-infra y vigilancia: solo control-1 (PR2d y paso 6)\n",
         "    if primero  # [PLANO-CONTROL-D324] etcd-server y argus-infra: solo control-1 (PR2d); la vigilancia, en todos\n"),
        (VIG_VIEJO, VIG_NUEVO),
    ],
    INS: [
        ("#   provisioning/vigilancia/disco.json           -> /etc/argus-vigilancia/disco.json (campos y rangos: argus_disco.py)\n",
         "#   provisioning/vigilancia/disco.json           -> /etc/argus-vigilancia/disco.json (campos y rangos: argus_disco.py)\n"
         "#     (o el que diga VIGILANCIA_DISCO_JSON: disco.json o disco-<nombre>.json del mismo directorio [DISCO-RUTAS-D324])\n"),
        ('command -v python3 >/dev/null || fallo "falta python3"\n',
         'command -v python3 >/dev/null || fallo "falta python3"\n'
         '# [DISCO-RUTAS-D324] el JSON del repo que va a $CONF: provisioning/vigilancia/$VIGILANCIA_DISCO_JSON, defecto\n'
         '# disco.json. Lo elige el Vagrantfile por nodo (hasta el PR2c, los nodos sin Vault: disco-sin-vault.json).\n'
         'DISCO_JSON=${VIGILANCIA_DISCO_JSON:-disco.json}\n'
         '[[ "$DISCO_JSON" =~ ^disco(-[a-z0-9]+)*\\.json$ ]] \\\n'
         '  || fallo "VIGILANCIA_DISCO_JSON=\'$DISCO_JSON\' mal formado (disco.json o disco-<nombre>.json, [a-z0-9-])"\n'
         'log "configuración: provisioning/vigilancia/$DISCO_JSON ($([ -n "${VIGILANCIA_DISCO_JSON:-}" ] && echo VIGILANCIA_DISCO_JSON || echo \'defecto: VIGILANCIA_DISCO_JSON ausente\'))"\n'),
        ("for f in scripts/vigilancia/argus_disco.py provisioning/vigilancia/disco.json provisioning/vigilancia/argus-disco.service; do\n",
         "for f in scripts/vigilancia/argus_disco.py provisioning/vigilancia/$DISCO_JSON provisioning/vigilancia/argus-disco.service; do\n"),
        ('poner "$RAIZ/provisioning/vigilancia/disco.json" "$CONF" 0644\n',
         'poner "$RAIZ/provisioning/vigilancia/$DISCO_JSON" "$CONF" 0644\n'),
    ],
    GT: [
        ("control-1\targus-control\n",
         "control-1\targus-control\ncontrol-2\targus-control\ncontrol-3\targus-control\n"),
    ],
    TAD: [
        ("    def test_ausente_da_defectos_y_error(self):\n",
         "    def test_sin_vault_del_repo_valido_y_sin_errores(self):\n"
         "        # [DISCO-RUTAS-D324] el de los nodos sin Vault hasta el PR2c (el Vagrantfile lo pone en control-2 y control-3)\n"
         "        repo = os.path.join(AQUI, \"..\", \"..\", \"provisioning\", \"vigilancia\", \"disco-sin-vault.json\")\n"
         "        valores, origenes, errores = d.leer_config(repo)\n"
         "        self.assertEqual(errores, [])\n"
         "        self.assertEqual(set(origenes.values()), {\"fichero\"})\n"
         "        self.assertEqual(valores, {\"rutas\": (\"/var/lib/etcd\",), \"umbral_pct\": 75, \"periodo_s\": 60})\n\n"
         "    def test_ausente_da_defectos_y_error(self):\n"),
    ],
}


def falla(msg):
    print("[D324-VIGILANCIA-NODOS] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    for ruta, esperado in NUEVOS.items():
        if not os.path.isfile(ruta):
            falla("antes, en su sitio: " + ruta)
        with open(ruta, "rb") as f:
            h = sha(f.read())
        if h != esperado:
            falla(ruta + " no es el entregado: sha256 " + h[:16] + " (esperado " + esperado[:16] + ")")
    nuevos = []
    for ruta, pares in CAMBIOS.items():
        if not os.path.isfile(ruta):
            falla(ruta + " no existe (¿raíz del repo?)")
        with open(ruta, "rb") as f:
            b = f.read()
        if sha(b) != PARTIDA[ruta]:
            falla(ruta + " no es el de partida: sha256 " + sha(b)[:16] + " (esperado " + PARTIDA[ruta][:16] + ")")
        t = b.decode("utf-8")
        for viejo, nuevo in pares:
            k = t.count(viejo)
            if k != 1:
                falla("%s: '%s' aparece %d veces (esperada 1)" % (ruta, viejo.strip()[:70], k))
            t = t.replace(viejo, nuevo)
        nuevos.append((ruta, t))
    for ruta, t in nuevos:
        st = os.stat(ruta)
        tmp = ruta + ".d324tmp"
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-VIGILANCIA-NODOS] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-VIGILANCIA-NODOS] RESULTADO PASA: %d ficheros (y disco-sin-vault.json verificado)" % len(nuevos))


if __name__ == "__main__":
    main()
