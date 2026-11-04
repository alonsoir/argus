# Prompt de continuidad — DAY318 (tras DAY317, miércoles 2026-11-04)

Hola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama
`feat/etcd-mtls-vault` (PR1, un nodo). Responde siempre en español. Lee, en este orden:
`docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md` (entero: contexto medido, decisiones D1-D11, plan 8e.1-8e.5
y el **diseño fino de 8e.1 con sus puntos abiertos**), el final de `docs/BACKLOG.md` (sección
`[MANIFIESTO-PROTEGIDOS-D317]` y, antes, las de los pasos 6 y 7) y `docs/ml-heads/day312_diseno.md` (diseño y
resultados de los pasos 6 y 7).

**DAY318 empieza el desarrollo de 8e.** DAY317 terminó solo con documentación: no se escribió código de 8e.

## Hecho DAY317

| paso | qué | estado |
|---|---|---|
| 6a | `ml-defender-etcd-server.service` en la VM etcd (provisioner `etcd-server-unit`) | commit 430f12421 (y 8834cad88) |
| 6b | Makefile: `etcd-vm-deploy`/`-estado`/`-check`/`-aviso`; `etcd-server-start/stop/status` actúan en la VM; `up`/`halt` incluyen etcd | commiteado |
| 6c | `pipeline-status` mira el etcd-server, cada miembro etcd (líder, term, retraso) y Vault de la VM (`scripts/etcd_ha/etcd_vm_estado.sh`) | commiteado |
| 6d | fuera del defender el etcd-server y su unidad; `etcd-server.json` = el de la VM; smoke enterprise con `etcd-server.smoke-enterprise.json` (DEBT-VAULT-ENTERPRISE-SMOKE-VM-001) | commiteado |
| 7 | instrumento de reinicio `d317_reinicio_vm.sh` / `d317_reinicio_defender.sh` con veredicto: `reinicio_vm_2` PASA | commiteado |
| 8d | provisioner global `apt-espera` (espera a unattended-upgrades, `DPkg::Lock::Timeout 600`) | commiteado |
| 8a | el bootstrap hace `etcd-vm-deploy` en `[6c/8]`, antes de `[7/8]` | commiteado |
| 8b | `lab-e2e-reinicio-etcd`: lab-e2e pasa a seis E2E | commiteado |
| 8c | `emecas` levanta las 6 VMs; `emecas+++` gana el Acto IV (adapters desde cero, `mitre-check` con `mitre_veredicto.sh`, fases visibles con su hora) | **comprobar con `git log` que está commiteado** |

Hashes exactos: `git log --oneline -15`.

## Resultado del EMECAS+++ DAY317 (paso 8): FALLA, y con razón

`make emecas+++ PROFILE=production`: 2 h 20 min. Pasa todo hasta `lab-e2e-protegidos`, que **falla P2**:
`origenes=192.168.100.50:10780,192.168.100.20:3`. El Acto IV no llegó a correr.

Medido: .20 es la VM etcd. El episodio es UDP. Chrony de la VM etcd pregunta la hora al defender cada 64 s; 207 s /
64 s = 3 peticiones NTP de cliente que `ddos_v2` marcó junto con la reflexión NTP. Con la mitigación real (hoy en
sombra), la VM etcd quedaría una hora en el blacklist: **DoS autoinfligido del plano de control**. También medido: la
whitelist (`ml_defender_whitelist`, con `RETURN` antes del blacklist en iptables) exime de TODO bloqueo de aRGus, no
solo del de la cabeza DDoS.

Decisión de Alonso: no se relaja EMECAS. Entra en este PR1 **DEBT-FW-MANIFIESTO-PROTEGIDOS-001** (ADR-060): un
manifiesto firmado por despliegue con categorías `infraestructura`/`intranet`/`dmz`/`externos_criticos`, que sustituye
a `ddos_protegidos` de cada `firewall.json`. Resumen de lo decidido (el detalle, en el ADR):
- **Firma:** Ed25519; clave privada en Vault transit, una por hospital, no exportable; la pública, compilada en el
  firewall-acl-agent en dos ranuras (patrón ADR-025).
- **Entradas:** `{cidr, interfaz obligatoria, mac opcional, motivo}`; límites de prefijo por categoría desde la
  plantilla de despliegue (`infraestructura` solo /32 y /128).
- **Cambios:** versión monótona; deshacer firmado.
- **Candado:** la mitigación real exige manifiesto verificado.
- **Fallo en caliente:** conserva el último verificado y avisa periódicamente.
- **Vigilancia:** comprobación continua kernel ↔ manifiesto; alertas de spoofing por interfaz y MAC; Falco, Wazuh y
  audit de Vault.
- **`argus-infra`:** solo en la máquina del admin. En el lab vive en la VM etcd por falta de RAM, y esa limitación
  está escrita.
- **Fuera de este PR:** regla de dos personas, no ahora (DEBT-FW-DOS-PERSONAS-001).

## Plan DAY318

1. **Comprobar el estado** (Mac, raíz del repo): `git status`, `git log --oneline -15`, que ADR-060 y la sección del
   BACKLOG estén commiteados, y `make pipeline-status` si el lab está levantado.
2. **Cerrar los cuatro puntos abiertos del diseño fino** (ADR-060, sección 6), midiendo antes de decidir:
   1. el set del kernel: reutilizar `ml_defender_whitelist` (recomendado) o uno nuevo;
   2. borrar el defecto RFC 1918 de DAY300, que el candado vuelve innecesario (lo decide Alonso);
   3. cómo entra la clave pública en la compilación (opción de CMake que lee un fichero traído de Vault; sin él, la
      compilación falla) y en qué orden en el bootstrap;
   4. el nombre de la interfaz del defender hacia la LAN (`eth2` según el Vagrantfile; medirlo en la VM).

   Antes, leer el código que se va a tocar: `firewall-acl-agent/include/firewall/ddos_protegidos.hpp`,
   `src/core/config_loader.cpp` (lectura de `ddos_protegidos`), `src/main.cpp` (`[ARGUS-WHITELIST-D301]`),
   `src/api/zmq_subscriber.cpp` (`ALERTA_PROTEGIDO`, contadores `protegidos:`), `src/core/iptables_wrapper.cpp`
   (cadena con la whitelist), la verificación Ed25519 de ADR-025 (no reinventar) y
   `scripts/timebase/d303_veredicto_protegidos.sh`.
3. **8e.1** (firewall-acl-agent), con tests y probado en el banco antes de entregar el parcheador. Después
   8e.2 → 8e.5 (ADR-060, sección 5), un commit por cambio lógico.
4. **EMECAS+++ PROFILE=production** de nuevo. Criterio: rc 0; `lab-e2e-protegidos` P1-P6 PASA con .20 aprovisionado
   por `argus-infra` en el bootstrap; Acto IV con `err_to_row=0` en el adapter de Suricata (eve.json nuevo).
5. Después: docs del paso 8, merge de PR1 y PR2 (HA) en rama nueva.

## Pendiente de decidir (Alonso), no bloquea 8e

- **eve.json de Suricata.** Los dos `json ilegible` del adapter son huellas de apagados bruscos de la VM. Medido:
  arranques sin `shutdown`, un registro cortado con otro pegado y 3024 bytes `\0`. El adapter hizo lo correcto.
  Propuesta:
  - (c) `mitre_start` y `ctu_start` dan al adapter solo lo escrito desde T0;
  - (b) `err_to_row=0` obligatorio;
  - opcional: las dos líneas reales como casos de `test_to_row`.
- **DEBT-DDOS-V2-NTP-CLIENTE-001.** El falso positivo del modelo con un cliente NTP. Va a `diag/ml-heads`.
- **Hipótesis de Alonso, sin medir: el DDoS autoinfligido** (tráfico legítimo de aRGus en despliegue distribuido que
  parezca un DDoS contra el plano de control). Se mide en PR2, sin adelantarse.

## Requisitos de PR2 (HA), prometidos al BACKLOG en el paso 8

- 3 nodos etcd, cada uno con su etcd-server, y Vault HA de 3 nodos raft. Antes, la decisión de RAM (VMs pequeñas o
  `ip netns`).
- Fallos:
  - tirar un nodo (también el líder) y ver que otro toma el control;
  - el estado de los componentes sigue sincronizado;
  - medir el tiempo de sincronización tras la caída y tras la vuelta;
  - partición 1+1+1.
- Seguridad: TLS entre pares, `peer-cert-allowed-cn`, una CA por despliegue.
- Despliegue:
  - inventario por despliegue;
  - Ansible genera `vault.hcl` y `etcd.conf.yml`;
  - medir que `EtcdRegistryStore` pasa todas las direcciones.
- Además: la hipótesis del DDoS autoinfligido y la categoría `infraestructura` del manifiesto con los 3 nodos.

## Deudas abiertas que no bloquean (ninguna decidida aún)

- DEBT-REPO-RESIDUOS-001: `__pycache__`, los `scripts/d31*_parche.py` y el patcher de 6d sin trackear (decisión de
  Alonso: dejarlo sin trackear).
- ggshield no reconoce la clave `paths_ignore`.
- La regla `/secrets/valid/{c}` del converter deja leer las claves de cualquier componente (pregunta de mínimo
  privilegio).
- DEBT-VAULT-ENTERPRISE-SMOKE-VM-001.
- DEBT-ETCD-VIGILANCIA-FALCO-WAZUH-001 (después de PR2).
- Las de DAY316: DEBT-ETCD-CONFIG-SIZE-ENDIAN-001, DEBT-ETCD-CLIENT-MANUAL-TESTS-CTEST-001,
  DEBT-SNIFFER-LIBPCAP-ETCD-001, DEBT-FW-CSV-SIN-FILAS-EN-GATE-001, DEBT-PKI-AT-REST-001,
  DEBT-GRAPH-HUECO-SIN-CLAVE-001, DEBT-CONFIG-AT-REST-PROTECTION-001.

## Herramientas de Claude (en su contenedor, no en el repo)

Banco Debian 12 en `/srv/banco` (GCC 12.2.0, libsodium 1.0.19, httplib v0.63.0, etcd-cpp-apiv3 v0.15.3, libbpf v1.4.6,
onnxruntime 1.17.1). `/root/banco_etcd.sh <árbol> <etiqueta>` compila seed-client, crypto-transport, common y
etcd-server con las opciones de production y pasa ctest; los tests se ejecutan DENTRO del chroot. Para 8e hará falta
añadir al banco el firewall-acl-agent. Si el contenedor es nuevo, hay que rehacerlo.

## Reglas

- Medir, no votar. Predicción escrita antes de medir; si algo no da lo esperado, parar.
- Todo lo que se compile se prueba antes en el banco con las opciones de production (g++-12, `-std=c++20 -Wall -Wextra
  -Wpedantic -Werror -O3 -march=native -DNDEBUG -flto -fno-omit-frame-pointer`), dos veces seguidas y contra el
  comportamiento viejo (mutaciones: tiene que fallar).
- Parcheadores:
  - `--check`/`--apply <raíz>`, todo o nada, idempotentes, con sha256 previo y final;
  - se copian a `scripts/etcd_ha/` y se ejecutan desde allí;
  - se entregan con su sha256;
  - un sha por línea de constante, nunca diccionarios largos con hex: ggshield los toma por secretos.
- Comandos:
  - exactos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM etcd con `vagrant ssh etcd -c`);
  - las salidas largas a un fichero, con `; cat` al final;
  - búsquedas con `git grep`, nunca `grep -r`;
  - sin emojis.
- El JSON es la ley.
- Lo deprecado se borra.
- No romper la seguridad ni abrir un camino para romperla en producción.
- El repo es de solo lectura para Claude: los commits los hace Alonso, uno por cambio lógico. **Claude propone siempre
  el mensaje de cada commit** con el `git commit -m` listo.
