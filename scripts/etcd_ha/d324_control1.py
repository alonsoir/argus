#!/usr/bin/env python3
# d324_control1.py — DAY324, PR2b paso 1 de DEBT-ETCD-HA-TLS-RAFT-001 [PLANO-CONTROL-D324]: la VM 'etcd' pasa a
# llamarse 'control-1' (hostname argus-control-1) y su grupo de Wazuh 'argus-etcd' pasa a 'argus-control'. Solo los
# ficheros vivos (los que comprueba scripts/etcd_ha/test_plano_control.py); los parcheadores de un día no se tocan.
# No cambia: el nombre del miembro etcd y del nodo Vault (argus-etcd-1: paso 4), los targets ni las variables del
# Makefile (etcd-vm-estado, ETCD_VM_*), el perfil de AppArmor argus-etcd-server (es el del binario).
# Antes (Mac, raíz del repo): git mv provisioning/wazuh/argus/shared/argus-etcd provisioning/wazuh/argus/shared/argus-control
# Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d324_control1.py
# Exige el sha256 de partida de cada fichero (main en d971ae0), cambia cada ancla exactamente las veces esperadas y no
# escribe nada si algo no cuadra.
import hashlib
import os
import sys

AC = "provisioning/wazuh/argus/shared/argus-control/agent.conf"
CAMBIOS = {
    "Vagrantfile": [
        ("vagrant provision etcd --provision-with deploy-access", "vagrant provision control-1 --provision-with deploy-access", 1),
        ('config.vm.define "etcd", autostart: false do |etcd|', 'config.vm.define "control-1", autostart: false do |etcd|', 1),
        ('etcd.vm.hostname    = "argus-etcd"', 'etcd.vm.hostname    = "argus-control-1"', 1),
        ('vb.name   = "argus-etcd"', 'vb.name   = "argus-control-1"', 1),
        ("vagrant destroy -f etcd && vagrant up etcd", "vagrant destroy -f control-1 && vagrant up control-1", 2),
        ("/vagrant/dist/deploy/known_hosts_etcd", "/vagrant/dist/deploy/known_hosts_control-1", 2),
        ("(grupo argus-etcd:", "(grupo argus-control:", 1),
        ('{"AGENT_NAME" => "etcd"}', '{"AGENT_NAME" => "control-1"}', 1),
    ],
    "Makefile": [
        ("vagrant up defender client etcd\n", "vagrant up defender client control-1\n", 1),
        ("vagrant halt defender client etcd\n", "vagrant halt defender client control-1\n", 1),
        ("wazuh etcd\n", "wazuh control-1\n", 3),
        ("vagrant ssh etcd -c", "vagrant ssh control-1 -c", 10),
        ("vagrant up etcd", "vagrant up control-1", 2),
        ("\n# Cada regla de aRGus contra su línea de provisioning/wazuh/argus/tests/casos_reglas.tsv",
         "\n# [PLANO-CONTROL-D324] comprobaciones estáticas del plano de control (Mac, sin VMs): scripts/etcd_ha/test_plano_control.py\n"
         "test-plano-control:\n\t@python3 -I scripts/etcd_ha/test_plano_control.py\n\n"
         "# Cada regla de aRGus contra su línea de provisioning/wazuh/argus/tests/casos_reglas.tsv", 1),
    ],
    "ansible/inventory/dev.yml": [
        ("        etcd:\n", "        control-1:\n", 2),
        ("/vagrant/dist/deploy/known_hosts_etcd", "/vagrant/dist/deploy/known_hosts_control-1", 1),
    ],
    "provisioning/wazuh/argus/grupos.tsv": [
        ("\netcd\targus-etcd\n", "\ncontrol-1\targus-control\n", 1),
    ],
    AC: [
        ("shared/argus-etcd/agent.conf", "shared/argus-control/agent.conf", 2),
        ("Configuración centralizada del grupo argus-etcd (la VM etcd: etcd-server, etcd y Vault).",
         "Configuración centralizada del grupo argus-control (las VMs del plano de control: etcd-server, etcd y Vault).", 1),
    ],
    "provisioning/wazuh/argus/shared/argus-defender/agent.conf": [
        ("ver la nota de argus-etcd.", "ver la nota de argus-control.", 1),
    ],
    "provisioning/wazuh/argus/tests/casos_reglas.tsv": [
        ("argus-etcd", "argus-control-1", 11),
    ],
    "provisioning/vigilancia/argus-disco.service": [
        ("(grupo argus-etcd).", "(grupo argus-control).", 1),
    ],
    "scripts/vigilancia/argus_disco.py": [
        ("shared/argus-etcd/agent.conf", "shared/argus-control/agent.conf", 1),
    ],
    "scripts/vigilancia/lab_e2e_vigilancia.sh": [
        ('V etcd "', 'V control-1 "', 5),
    ],
    "scripts/etcd_ha/d312_etcd_vm_deploy.sh": [
        ("vagrant ssh-config etcd >>", "vagrant ssh-config control-1 >>", 1),
        ("(¿defender y etcd levantadas?)", "(¿defender y control-1 levantadas?)", 1),
        ('S etcd "', 'S control-1 "', 4),
    ],
    "scripts/etcd_ha/d317_reinicio_vm.sh": [
        ("vagrant ssh etcd -c", "vagrant ssh control-1 -c", 1),
    ],
    "scripts/etcd_ha/d321_latido_e2e.sh": [
        ('vagrant status etcd 2>/dev/null | grep -qE "^etcd +running"',
         'vagrant status control-1 2>/dev/null | grep -qE "^control-1 +running"', 1),
        ("(vagrant up etcd)", "(vagrant up control-1)", 1),
    ],
    "scripts/etcd_ha/d322_reinicio_vault.sh": [
        ("vagrant ssh etcd -c", "vagrant ssh control-1 -c", 2),
    ],
    "scripts/etcd_ha/etcd_vm_estado.sh": [
        ("vagrant ssh etcd -c", "vagrant ssh control-1 -c", 1),
    ],
    "scripts/etcd_ha/protegidos_pubkey.sh": [
        ("vagrant ssh etcd -c", "vagrant ssh control-1 -c", 1),
    ],
    "scripts/etcd_ha/protegidos_pubkey_vm.sh": [
        ("vagrant ssh etcd -c", "vagrant ssh control-1 -c", 1),
        ("vagrant destroy -f etcd && vagrant up etcd", "vagrant destroy -f control-1 && vagrant up control-1", 1),
    ],
    "scripts/timebase/d302_mitigacion_e2e.sh": [
        ("vagrant status etcd 2>/dev/null | grep -qE '^etcd +running'",
         "vagrant status control-1 2>/dev/null | grep -qE '^control-1 +running'", 1),
        ("(vagrant up etcd)", "(vagrant up control-1)", 1),
    ],
    "etcd-server/README.md": [
        ("En la VM `etcd` del laboratorio (192.168.100.20)", "En la VM `control-1` del laboratorio (192.168.100.20)", 1),
    ],
}
PARTIDA = {}  # lo rellena el bloque de abajo


def falla(msg):
    print("[D324-CONTROL1] FALLA: " + msg + " (no se ha escrito nada)")
    sys.exit(1)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if os.path.exists("provisioning/wazuh/argus/shared/argus-etcd"):
        falla("antes: git mv provisioning/wazuh/argus/shared/argus-etcd provisioning/wazuh/argus/shared/argus-control")
    nuevos = []
    for ruta, pares in CAMBIOS.items():
        if not os.path.isfile(ruta):
            falla(ruta + " no existe (¿raíz del repo? ¿hiciste el git mv?)")
        with open(ruta, "rb") as f:
            b = f.read()
        if sha(b) != PARTIDA[ruta]:
            falla(ruta + " no es el de partida: sha256 " + sha(b)[:16] + " (esperado " + PARTIDA[ruta][:16] + ")")
        t = b.decode("utf-8")
        for viejo, nuevo, n in pares:
            k = t.count(viejo)
            if k != n:
                falla("%s: '%s' aparece %d veces (esperadas %d)" % (ruta, viejo.strip()[:60], k, n))
            t = t.replace(viejo, nuevo)
        nuevos.append((ruta, t))
    for ruta, t in nuevos:
        tmp = ruta + ".d324tmp"
        st = os.stat(ruta)
        with open(tmp, "wb") as f:
            f.write(t.encode("utf-8"))
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, ruta)
        print("[D324-CONTROL1] %s sha256 %s" % (ruta, sha(t.encode("utf-8"))))
    print("[D324-CONTROL1] RESULTADO PASA: %d ficheros; ahora: python3 -I scripts/etcd_ha/test_plano_control.py"
          % len(nuevos))


PARTIDA.update({
    "Vagrantfile": "ca1afd00c6f68e828ad6228be42c1e8d6cb7b487e835eb38ab5acf695a55f5d1",
    "Makefile": "5c9460d5f4a51554512a9a7a96e3cd1cb0b66c68d408bf718afdfd9ba434991d",
    "ansible/inventory/dev.yml": "17ae13abe54d2d5afbccfa70e716c443b425d5e05a2d06fe9ef446cc4640bb0a",
    "provisioning/wazuh/argus/grupos.tsv": "46ea22db444788d57506506be860fc4d9ae279df67e14f32481f0b0e72200dfd",
    AC: "369b464b6e69604085913ef81f2490a940c3ec89b8280fcc0a26d7cf4f967dd0",
    "provisioning/wazuh/argus/shared/argus-defender/agent.conf": "ee7940cc012e500509a1d3eee249d5f0f9c975acf4b242d8cb9418aa0b266067",
    "provisioning/wazuh/argus/tests/casos_reglas.tsv": "6ece9a3b415b6a03a273ee612a6c14ef80cc31b4a86d38dc202629df7b139a25",
    "provisioning/vigilancia/argus-disco.service": "c5d1cfb558bc6cdf88c0151d23f894c27996b382381393a562bfaf6e0c5eaddf",
    "scripts/vigilancia/argus_disco.py": "ba2439c52b1036f977710d138bac5b8e47b55a6c44f90094c1fbd38a65dfdb60",
    "scripts/vigilancia/lab_e2e_vigilancia.sh": "a599bddc1e765cef70fb4c5dc33f4388e84e8bd455f94c2c8b5b0a87546c4a45",
    "scripts/etcd_ha/d312_etcd_vm_deploy.sh": "1640e5c1c944610fa6df3b5e2cf98a1f9fa122e55038e5d18c3207fd9ba2d45a",
    "scripts/etcd_ha/d317_reinicio_vm.sh": "0abf6ccd909d3b9468b10dfdd824926aec17556c19a4c44fd9e067b9fd0ce22e",
    "scripts/etcd_ha/d321_latido_e2e.sh": "fa39840f815684b3b46e250f39319a8e6f61aa29b6199b73fec61165ccd3809e",
    "scripts/etcd_ha/d322_reinicio_vault.sh": "8e648c24671f0aad9f175916d55c45f84d695a49395900e41b00281c0f1db3ed",
    "scripts/etcd_ha/etcd_vm_estado.sh": "7e8ff069c40c526d8ad362a1aab98b434f3185b6fcc287e03825d33eb8ac7613",
    "scripts/etcd_ha/protegidos_pubkey.sh": "ae01f4f817eef1e37a69d49f3d68061a081af6ff9ace0f32bff49e6272ee8a29",
    "scripts/etcd_ha/protegidos_pubkey_vm.sh": "1f36c13632b46b056e9622647cf8d5c403eb8a0d3ee3f6719ebe7ddd49c4d845",
    "scripts/timebase/d302_mitigacion_e2e.sh": "6e4938995402470cf8fa69c90bf68c7d5612c6e5855217928c55bc73bc5d3ec3",
    "etcd-server/README.md": "9ed9d0905956c74fe104e29062d87eb2981a109ba8127581d0df1ebf839db333",
})

if __name__ == "__main__":
    main()
