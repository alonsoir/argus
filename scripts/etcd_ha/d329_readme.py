#!/usr/bin/env python3
"""DAY329 [README-D329] README de main tras el PR2b: fila de pre-release-etcd-ha-raft-0.0.11, el plano de control en
tres nodos (etcd en Raft de 3), Falco y Wazuh en todos los nodos, EMECAS con ocho VMs y una sola fecha de Debian,
el resultado del EMECAS+++ de DAY329, la anécdota del primer bug de kernel (Debian #1154153), memoria, limitaciones
y lo siguiente (Vault en HA, PR2c).

Uso (Mac, raíz del repo): python3 -I scripts/etcd_ha/d329_readme.py [--apply]
Sin --apply solo comprueba. Con --apply escribe, y solo si TODO cuadra: sha256 de partida de cada fichero que modifica,
cada ancla exactamente las veces esperadas y ningún fichero nuevo ya existente. Si algo falla no escribe nada.
"""
import hashlib, os, sys

NUEVOS = {}

MODIFICA = {'README.md': ('f804f849811d7de5d89d1740d4117fd7b60448c8d7a38582660dfd7a15a47143', [('| `pre-release-etcd-mtls-vault-0.0.10` | control plane over mTLS, keys in Vault, signed manifest of protected ranges, host surveillance (below) |\n', '| `pre-release-etcd-mtls-vault-0.0.10` | control plane over mTLS, keys in Vault, signed manifest of protected ranges, host surveillance (below) |\n| `pre-release-etcd-ha-raft-0.0.11` | control plane on three nodes: etcd as a 3-member Raft cluster, surveillance on every node, and the whole lab pinned to one Debian date (below) |\n', 1), ('### Control plane — mTLS, keys in Vault, a signed manifest of protected ranges (DAY312–323)\n', '### Control plane — mTLS, keys in Vault, a signed manifest of protected ranges, three nodes (DAY312–329)\n', 1), ('- **Its own VM.** The etcd-server runs on the `etcd` VM (`192.168.100.20`) as a systemd service, next to a real etcd (3.6, gRPC + TLS, RBAC) and a Vault server. Nothing listens on 2379 on the defender any more. The service comes back by itself after a reboot, and Vault starts and unseals without Vagrant (with its own unseal identity).\n', "- **Its own machines.** The control plane runs on three VMs, `control-1`, `control-2` and `control-3` (`192.168.100.20`–`.22`), declared once in the inventory (`argus_control_nodos` in `group_vars`) and read from there by Vagrant and Ansible. **etcd is a 3-member Raft cluster** (3.6, gRPC + TLS, RBAC per certificate CN, mTLS also between members, nftables between nodes, one certificate per node and role). The etcd-server runs on `control-1` as a systemd service, next to a Vault server. Nothing listens on 2379 on the defender any more. The service comes back by itself after a reboot, and Vault starts and unseals without Vagrant (with its own unseal identity). Every gate run checks the cluster for real (`test-etcd-cluster`) and restarts its members one at a time with a writer running (`test-etcd-reinicio`); `etcd-vm-check` requires the etcd-server's own heartbeat to be written to etcd, not only `/health`.\n", 1), ('In the lab it lives on the `etcd` VM and the bootstrap provisions the manifest with it.', 'In the lab it lives on `control-1` and the bootstrap provisions the manifest with it.', 1), ('**Falco** (on the defender and the `etcd` VM) and **Wazuh** agents (file integrity of configuration, PKI and binaries on both machines;', "**Falco** (on the defender and the three control nodes, with a gate step that requires zero CRITICAL alerts from aRGus' rules since the VMs were created) and **Wazuh** agents (file integrity of configuration, PKI and binaries on every one of those machines;", 1), ('the production topology, all six VMs** (defender, client, suricata, zeek, wazuh, etcd): a subset hides faults that only the topology shows (the DAY317 self-inflicted DoS did not exist with two VMs);', "the production topology, all eight VMs** (defender, client, suricata, zeek, wazuh, control-1, control-2, control-3): a subset hides faults that only the topology shows (the DAY317 self-inflicted DoS did not exist with two VMs). Every VM is first brought to **one Debian date** (all Debian sources point to snapshot.debian.org at `argus_debian_snapshot`, a single line in `group_vars/all.yml`), rebooted into that date's kernel and only then provisioned; a gate step checks that all eight *run* it (`uname -r`, not what is installed);", 1), ("Result for `pre-release-etcd-mtls-vault-0.0.10` (DAY323, merge of PR #153): **PASS, rc = 0, 4 h 02 min** on a 2019 laptop. `mitre-check`: aRGus 1,777 events in the graph (1,253 from the attack, in the window), Suricata 31 (31), Zeek 1,114 (1,068), invariant 0, 1,080 corroborated flows. It took four from-scratch runs that day; each stop had its cause measured, its fix tested on its own and its commit (Suricata running with its factory configuration, blind: wrong interface and 0 signatures; one clock per sensor; a MITRE window that mixed days; Jenkins' apt key; the sensors' NTP inside the DDoS episode). None was visible without a from-scratch run.\n", "Result for `pre-release-etcd-mtls-vault-0.0.10` (DAY323, merge of PR #153): **PASS, rc = 0, 4 h 02 min** on a 2019 laptop. `mitre-check`: aRGus 1,777 events in the graph (1,253 from the attack, in the window), Suricata 31 (31), Zeek 1,114 (1,068), invariant 0, 1,080 corroborated flows. It took four from-scratch runs that day; each stop had its cause measured, its fix tested on its own and its commit (Suricata running with its factory configuration, blind: wrong interface and 0 signatures; one clock per sensor; a MITRE window that mixed days; Jenkins' apt key; the sensors' NTP inside the DDoS episode). None was visible without a from-scratch run.\n\nResult for `pre-release-etcd-ha-raft-0.0.11` (DAY329, three control nodes): **PASS, rc = 0, 4 h 35 min**, 35 steps, all eight VMs on kernel `6.1.0-54-amd64`. Bringing the VMs up now takes 77 min in three steps (up, reboot, provision) instead of 53–57 min in one: that is the measured price of a homogeneous lab.\n", 1), ('Each run keeps a `resumen.md` and one log per step under `logs/lab/emecas/`. Sanitizer runs (ASan/TSan) are deliberately left for real pre-production hardware.\n', "Each run keeps a `resumen.md` and one log per step under `logs/lab/emecas/`. Sanitizer runs (ASan/TSan) are deliberately left for real pre-production hardware.\n\n#### Our first kernel bug (DAY328–329)\n\nBetween two from-scratch runs, Debian published a new kernel, `6.1.0-55` (6.1.192-1). The lab installed it without anyone asking for it, through `unattended-upgrades` and a `linux-headers-amd64` that had no version pin. The kernel only ran when the Vault restart test rebooted `control-1`. Twelve seconds after boot, ext4 hit a NULL pointer dereference (`ext4_mb_load_buddy_gfp+0xbc`). From then on the VM answered ping and opened its ports, but every write to disk hung forever, and the gate sat silent for an hour.\n\nWe measured it down to the stack traces and a memory dump, and reported it to Debian as [#1154153](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=1154153). Within hours, another user confirmed the same oops on KVM, with the previous kernel (6.1.190-1) working fine. It was the author's first kernel bug report. It will not be the last thing the gate catches that is not ours.\n\nWhat changed because of it:\n- The whole lab is now pinned to one Debian date on snapshot.debian.org (`argus_debian_snapshot`, a single line in `group_vars/all.yml`).\n- Every VM is rebooted into that date's kernel before provisioning, and a gate step checks that all eight run it (`uname -r`, not what is installed).\n- Every call from the host to a VM now has a time limit and fails with the step's name instead of hanging.\n\nThe next from-scratch run was green.\n", 1), ('first run ~1.5 h from scratch: six VMs,', 'first run ~1.5 h from scratch: eight VMs,', 1), ('**Memory:** the six VMs use about 19 GB of RSS; 32 GB on the host is the measured working size.', '**Memory:** the six VMs before DAY324 used about 19 GB of RSS; the two extra control nodes add 1 GB each (not re-measured as a whole). 32 GB on the host is the measured working size.', 1), ('- **Control plane on a single node.** One etcd member, one Vault server, one etcd-server, all on the `etcd` VM. High availability (≥ 3 etcd nodes, Vault HA, their Ansible) is the next branch. In the lab, Vault is unsealed automatically and `argus-infra` runs on the `etcd` VM, which plays the admin machine (no RAM for one more VM): development simplifications, written down.\n', '- **Vault and the etcd-server on a single node.** etcd is a 3-member Raft cluster on `control-1`..`control-3`, but the Vault server and the etcd-server run only on `control-1`: Vault in HA is the next branch (PR2c), and the components talking to several etcd-server endpoints comes after it. In the lab, Vault is unsealed automatically and `argus-infra` runs on `control-1`, which plays the admin machine (no RAM for one more VM): development simplifications, written down.\n', 1), ('1. **High availability of the control plane** (PR2, in small PRs): ≥ 3 etcd nodes (one node down, re-election, time to resynchronize; all down and back one by one), Vault in HA, the number of nodes in the inventory and `etcd.conf.yml` generated from it.\n', '1. **High availability of the control plane** (PR2, in small PRs): etcd done — a 3-member Raft cluster, with the nodes in the inventory and their restart one by one in every gate run (`pre-release-etcd-ha-raft-0.0.11`). Next: Vault in HA (PR2c), then the components using several etcd-server endpoints. Also: third-party versions pinned per lens, like the Debian date.\n', 1)])}

def main():
    aplicar = "--apply" in sys.argv[1:]
    if not os.path.isfile("Vagrantfile") or not os.path.isfile("Makefile"):
        sys.exit("❌ ejecutar desde la raíz del repo")
    errores, resultado = [], {}
    for ruta in NUEVOS:
        if os.path.exists(ruta):
            errores.append("ya existe " + ruta)
    for ruta, (sha_partida, cambios) in MODIFICA.items():
        datos = open(ruta, "rb").read()
        h = hashlib.sha256(datos).hexdigest()
        if h != sha_partida:
            errores.append("%s: sha256 de partida %s, esperado %s" % (ruta, h, sha_partida))
            continue
        texto = datos.decode("utf-8")
        for viejo, nuevo, veces in cambios:
            n = texto.count(viejo)
            if n != veces:
                errores.append("%s: ancla %d veces, esperadas %d: %r" % (ruta, n, veces, viejo[:90]))
            else:
                texto = texto.replace(viejo, nuevo)
        resultado[ruta] = texto
    if errores:
        print("❌ no se escribe nada:")
        for e in errores:
            print("   - " + e)
        sys.exit(1)
    if not aplicar:
        print("✅ todo cuadra (sin --apply no se escribe nada): %d nuevos, %d modificados" % (len(NUEVOS), len(resultado)))
        return
    for ruta, (contenido, modo) in NUEVOS.items():
        os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(contenido)
        os.chmod(ruta, modo)
        print("  + %s  sha256=%s" % (ruta, hashlib.sha256(contenido.encode()).hexdigest()))
    for ruta, texto in resultado.items():
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(texto)
        print("  ~ %s  sha256=%s" % (ruta, hashlib.sha256(texto.encode()).hexdigest()))
    print("✅ aplicado")

if __name__ == "__main__":
    main()
