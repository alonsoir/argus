#!/usr/bin/env python3
# d317_docs_resultados_p6.py — resultados del paso 6 de DEBT-ETCD-HA-TLS-RAFT-001 (DAY317).
# Añade al final de docs/ml-heads/day312_diseno.md la sección «Resultados DAY317 — paso 6» y al final de docs/BACKLOG.md
# su resumen (DEBT-ETCD-HA-TLS-RAFT-001 pasos 0-6, DEBT-PIPELINE-STATUS-LIVENESS-001 avanzada, hallazgo de las unidades).
# Uso:  python3 d317_docs_resultados_p6.py --check <raiz_repo>
#       python3 d317_docs_resultados_p6.py --apply <raiz_repo>
# Todo o nada; idempotente (si las dos secciones ya están, no toca nada).
import hashlib, os, sys

DISENO_RUTA = 'docs/ml-heads/day312_diseno.md'
DISENO_PREVIO = 'a9ec98ee57201c1c47e95e4328a8e980bd6be28e707b171e7f2385c1f64ec3ce'
DISENO_MARCA = '## Resultados DAY317 — paso 6'
BACKLOG_RUTA = 'docs/BACKLOG.md'
BACKLOG_PREVIO = 'fd94dbf5f748327c56e88ac987d6ec537cf0d56d53e2c56c6ca7477081303c47'
BACKLOG_MARCA = '## DAY317 — paso 6 de DEBT-ETCD-HA-TLS-RAFT-001 hecho'
DISENO = "\n## Resultados DAY317 — paso 6 (sección aparte, sin reescribir el diseño)\n\nCommits: `430f12421` (diseño del paso 6), `8834cad88` (6a), `4df098f34` (6b), `2e7cfea2a` (6c), `86ab61607` (6d). La\npredicción del paso, «en el defender nada escucha en 2379; en 8200 solo 127.0.0.1», **PASA**: medida con el pipeline\nparado y arrancado, antes y después de 6d.\n\n### 6a — unidad systemd en la VM etcd (`8834cad88`)\n\n- Banco: `ruby -c` del Vagrantfile, `bash -n` del aprovisionador; `systemd-analyze verify` de la unidad limpio con un\n  binario falso; con `Restart=siempre` se queja pero da rc 0, así que el aprovisionador decide por la salida, no por el\n  código de retorno.\n- Laboratorio: `vagrant validate` OK; `vagrant provision etcd --provision-with etcd-server-unit` → activa (pid 1243),\n  escucha `0.0.0.0:2379` (`server.host` del JSON; nftables limita al defender); journal: `tls.modo=mtls`, 13 reglas,\n  almacén etcd, Vault conectado, 4 componentes cargados y tres `[ETCD-COMPONENTE-MUERTO]` (registros de ayer, se\n  conservan).\n- `vagrant reload etcd --no-provision`: etcd, Vault y etcd-server `active`, desellado `Result=success`, etcd-server con\n  pid 478 (lo arrancó systemd); journal del arranque: `[ETCD-VAULT] conectado`, registros cargados, sin `FATAL`.\n  **PASA.**\n\n### 6b — Makefile y `etcd_vm_estado.sh` (`4df098f34`)\n\n- Banco, con dobles de `sudo`, `systemctl`, `curl` y `etcdctl`: 14 casos (un nodo sano, tres nodos con retraso dentro y\n  fuera del límite, dos líderes, etcd caído, Vault sellado, Vault en HA activo + en espera, dos activos, el activo\n  sellado, etcd-server inactivo y activo sin `/health`, opciones mal formadas, espera, JSON ausente). Un doble de `curl`\n  falló (solo reconocía el 8200); corregido el doble, no el script.\n- Laboratorio: `make etcd-vm-estado` → SANO (1/1 miembros, líder `argus-etcd-1`, term 12, retraso 0; Vault 200;\n  `/health` 200). El usuario `etcd-server` de etcd (RBAC `/argus/`) sí puede pedir `member list` y `endpoint status`\n  (riesgo abierto en el diseño, medido). Control negativo: `etcd-server-stop` → `inactive`; `etcd-vm-check` → `NO SANO`\n  tras 31 s, rc 2; `etcd-server-start` → SANO, rc 0. `etcd-vm-deploy` → `RESULTADO PASA`, Ansible `ok=7 changed=0`,\n  SANO. **PASA.**\n\n### 6c — `pipeline-status` (`2e7cfea2a`)\n\n- `pipeline-stop` + `pipeline-start`: el aviso da SANO; `pipeline-status` enseña el etcd-server de la VM, etcd con su\n  miembro, `vault-hmac`, los tres componentes, el Vault dev y Jenkins; ningún `STOPPED`.\n- Componentes: los tres `[ETCD-CLIENTE-REGISTRADO] ... en https://192.168.100.20:2379 al primer intento; config subida`;\n  ml-detector `[BRONCE-CLAVE]` huella `60768287`, firewall `[FW-CSV-CLAVE]` huella `4f60123a` (las de DAY316: Vault\n  conservó las claves). **PASA.**\n\n### 6d — el defender deja el etcd-server (`86ab61607`)\n\n- **Hallazgo:** las tres unidades de los componentes en el defender llevaban `Requires=ml-defender-etcd-server.service`,\n  contra G2 (DAY316). Sin corregirlas, al quitar la unidad del etcd-server no arrancarían nunca por systemd. Corregidas.\n- Banco (Debian 12, GCC 12.2.0, production): control y 6d, dos pasadas; ctest del etcd-server 7/7; los 12 avisos\n  idénticos línea a línea; los 6 tests de los JSON, por nombre, OK. Mutaciones cazadas: el JSON de prueba en `0.0.0.0` o\n  en `mtls`, `etcd-server.json` con almacén, `tls` o claves fuera de producción, y el JSON de prueba con otro latido.\n  `install-systemd-units.sh` con dobles: retira la unidad del defender (ExecStart en\n  `/vagrant/etcd-server/build-active`) y no toca una con el mismo nombre que sea la de la VM. `systemd-analyze verify`\n  de las tres unidades limpio (solo el aviso del bit de ejecución, que ya traen en git como 100755; el instalador las\n  copia con 0644).\n- Laboratorio: `pipeline-build` production rc 0 (19 min); `test-components` 9/23/13/7/90; `install-systemd-units`: 3\n  instaladas y la vieja retirada; `test-provision-1` 8/8 (comprobación 5 con 3); `etcd-vm-deploy` dos veces: `changed=1`\n  (el `_doc` nuevo) y `changed=0`, SANO las dos; Acto I `TEST-E2E-VAULT PASSED` con el smoke escuchando en\n  `http://127.0.0.1:2379` y el aviso nombrando DEBT-VAULT-ENTERPRISE-SMOKE-VM-001; Acto III `VAULT-FAULT-INJECT PASSED`;\n  pipeline rearrancado, todo `RUNNING`; defender: solo `127.0.0.1:8200`. **PASA.**\n- ggshield marcó como secreto dos sha256 de ficheros dentro del parcheador `d317_6d_defender.py` (falso positivo).\n  Decisión de Alonso: el parcheador queda sin trackear; el commit de 6d lleva solo el código, sin nada marcado.\n\n### Lecciones DAY317\n\n- Una predicción que falla sin consecuencias (el enlace que no estaba en la VM) se anota y no se persigue.\n- `systemd-analyze verify` da rc 0 con directivas mal escritas: se decide por la salida.\n- La salida de Ansible lanzada con `-t` lleva códigos de color: para el resumen, `grep -a 'changed='`.\n- Los tests del banco se ejecutan dentro del chroot: fuera no encuentran sus ficheros y fallan por el instrumento.\n- Un resultado raro con dobles de prueba: mirar primero el doble (el de `curl` solo conocía el 8200).\n- Al cambiar dónde vive un servicio, medir también las unidades que dependen de él.\n\n### Pendientes\n\n- Paso 7 (instrumento de reinicio en la VM: falta el bronce anterior verificable) y paso 8 (EMECAS+++ production, con la\n  VM etcd rehecha desde cero: DEBT-LAB-VAULT-CLAVES-PRUEBA-001). `lab-e2e` no se ha corrido en el paso 6: va en el 8.\n- ggshield avisa `Unrecognized key in config: paths_ignore` en cada commit: esas exclusiones probablemente no se\n  aplican. Sin decidir.\n"
BACKLOG = '\n## DAY317 — paso 6 de DEBT-ETCD-HA-TLS-RAFT-001 hecho (rama feat/etcd-mtls-vault)\n\nDocumento: `docs/ml-heads/day312_diseno.md`, «Resultados DAY317 — paso 6». Commits `8834cad88` (6a: etcd-server de la VM\ncomo `ml-defender-etcd-server.service`), `4df098f34` (6b: Makefile con la VM etcd, `etcd_vm_estado.sh`), `2e7cfea2a`\n(6c: `pipeline-status` con el estado real), `86ab61607` (6d: el defender deja el etcd-server).\n\n### DEBT-ETCD-HA-TLS-RAFT-001 — EN CURSO (pasos 0-6 hechos)\nEl etcd-server corre en la VM etcd como servicio systemd, junto a etcd y Vault, y vuelve solo tras reiniciar la VM;\n`make up` y `make emecas` levantan la VM etcd y EMECAS la despliega tras compilar (`etcd-vm-deploy`, con control\nestricto). En el defender nada escucha en 2379; en 8200 solo el Vault dev en 127.0.0.1 (decisión 1). Siguiente: paso 7\n(reinicio en la VM, bronce anterior verificable) y paso 8 (EMECAS+++ production).\n\n### DEBT-PIPELINE-STATUS-LIVENESS-001 — AVANZADA DAY317\n`pipeline-status` enseña el estado real de la VM etcd: el etcd-server (systemd y `/health`), cada miembro etcd (sano,\nlíder, term, retraso respecto al líder) y cada nodo del Vault de las claves HMAC. Los componentes del defender siguen\nmirándose solo por proceso.\n\n### Hallazgo DAY317 — corregido en 6d\nLas unidades systemd de sniffer, ml-detector y firewall en el defender llevaban\n`Requires=ml-defender-etcd-server.service` (contra G2). Fuera.\n'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    F = [(DISENO_RUTA, DISENO_PREVIO, DISENO_MARCA, DISENO), (BACKLOG_RUTA, BACKLOG_PREVIO, BACKLOG_MARCA, BACKLOG)]
    cont, ya = {}, 0
    for ruta, previo, marca, _ in F:
        f = os.path.join(raiz, ruta)
        if not os.path.isfile(f):
            print('FALLA: no existe %s; no se toca nada.' % f); return 1
        b = open(f, 'rb').read(); cont[ruta] = b
        if marca.encode() in b:
            ya += 1
        elif sha(b) != previo:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (ruta, sha(b)[:16])); return 1
    if ya == 2:
        print('YA APLICADO: las dos secciones ya están; no se toca nada.'); return 0
    if ya:
        print('FALLA: una sección está y la otra no; no se toca nada.'); return 1
    if modo == '--check':
        print('APLICABLE: 2 ficheros; se añaden %d y %d líneas.' % (DISENO.count('\n'), BACKLOG.count('\n'))); return 0
    for ruta, _, _, texto in F:
        f = os.path.join(raiz, ruta); t = f + '.d317tmp'
        with open(t, 'wb') as o: o.write(cont[ruta] + texto.encode('utf-8'))
        os.chmod(t, os.stat(f).st_mode & 0o7777); os.replace(t, f); print('  escrito  %s' % ruta)
    print('APLICADO: 2 ficheros.'); return 0

if __name__ == '__main__':
    sys.exit(main())
