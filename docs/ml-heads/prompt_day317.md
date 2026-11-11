# Prompt de continuidad — DAY317 (tras DAY316, martes 2026-11-03)

Hola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama
`feat/etcd-mtls-vault`. Responde siempre en español. Lee `docs/ml-heads/day312_diseno.md` (diseño y resultados; las
secciones DAY316: «Diseño del paso 5», «Resultados DAY316 — paso 5...», «Resultados DAY316 — paso 5, commit A»,
«Diseño del commit B», «Resultados DAY316 — commits B1 y B2») y el final de `docs/BACKLOG.md` (secciones DAY316).
Todo lo de DAY316 está documentado allí; aquí va el resumen y el plan.

## Hecho y commiteado DAY316 (todo medido en el laboratorio)

| commit | qué |
|---|---|
| 0de22545a | docs DAY315 |
| dedf1efdc | diseño del paso 5 |
| 1e75d0618 | C4+D3: fuera HttpEtcdRegistrar, CryptoEpochCoordinator (ADR-045) y `/v1/epoch` |
| 59d0fc592 | E4: el Vagrantfile reparte la PKI del lab al defender (`/etc/argus-pki`) |
| 3569385a2 | docs: decisiones y estado deseado del paso 5 |
| fe99a7e70 | **commit A**: libetcd_client con mTLS y lista de direcciones, lector único del bloque `etcd`, JSON a `https://192.168.100.20:2379`, inyectores con la identidad del componente, mitre/ctu/custom-start piden la clave por mTLS (cierra DEBT-HMAC-KEY-INSECURE-TRANSPORT-001) |
| c256e88c4 | docs del commit A y deudas nuevas |
| 8d56ff747 | diseño del commit B (decisiones G1-G7) |
| 370210a28 | **B1**: mantenedor en la librería (un ritmo: `heartbeat_interval_seconds`), ningún componente sale ni espera por etcd, se sube el JSON de `-c` en cada registro, fuera la semilla muerta del sniffer |
| cde7dd213 | **B2**: el firewall pide su clave del CSV cada `hmac_key.check_interval_seconds`, un CSV por clave (`firewall_blocks-<fecha>-<huella>.csv`), `test-parquet` sin CSV = `[PARQUET-SIN-DATOS]` rc 0 (cierra DEBT-FW-HMAC-KEY-ALARM-001) |
| (docs DAY316 final) | resultados de B1 y B2, este prompt |

Medido al final: test-components 9/23/13/7/90; sin etcd-server los tres arrancan y se registran solos cuando vuelve;
caída con el pipeline en marcha → modo extendido y reanudación sin nuevo `/register`; test-e2e-synthetic PASSED;
mitre-start rc 0 (commit A: argus 1518, suricata 32, zeek 1074, invariante 0, 1051 corroborados).

## Estado del laboratorio al cerrar DAY316

- El etcd-server de la VM etcd (192.168.100.20) **se arranca a mano**: `vagrant ssh etcd -c "bash
  /vagrant/scripts/etcd_ha/d313_es_vm.sh arrancar"` (**sin sudo**; con sudo falla por `fs.protected_regular` y el
  `grep` enseña un OK viejo). Tras parar el Mac la VM queda `aborted`: `vagrant up etcd` y volver a arrancarlo.
- El etcd-server del defender (HTTP, memoria) sigue arrancando con `pipeline-start` y el Vault dev del defender sigue en
  marcha (`pipeline-status`), pero ya no los usa ningún componente.
- El CSV viejo del firewall está en `logs/firewall_logs/archivo/`.

## Respuesta a «¿hemos acabado antes de EMECAS?»: NO. Falta el paso 6 y medir lo que EMECAS necesita de la VM etcd

Medido en el Makefile al cerrar: `make emecas` hace `vagrant destroy -f` (destruye también la VM etcd) y luego `vagrant
up defender client suricata`: **no levanta la VM etcd**; `pipeline-start` depende de `etcd-server-start` (el del
defender); `emecas++` lanza `test-e2e-vault`, que usa `vault-dev-seed` (Vault dev del defender). Hoy la VM etcd se
monta con pasos manuales desde el Mac (`d312_pki.sh`, `d312_etcd_vm_deploy.sh`, `make deploy-configs`, `d313_es_vm.sh`).
Sin el paso 6, un EMECAS desde cero dejaría el pipeline sin etcd-server: los componentes arrancan (B1), pero sin clave
HMAC no hay bronce ni CSV firmados; mitre-start necesita la clave (E5) y `lab-e2e` está por medir.

## Plan DAY317

1. **Medir antes de diseñar el paso 6** (sin tocar nada): qué hace hoy cada pieza para montar la VM etcd desde cero
   (provisioners del Vagrantfile de la VM etcd: etcd, Vault, unseal, PKI; `d312_etcd_vm_deploy.sh`; `deploy-configs`;
   `d313_es_vm.sh`), qué targets usan el etcd-server o el Vault del defender (`git grep` de `etcd-server-start`,
   `vault-dev`, `localhost:2379`, `localhost:8200` en Makefile y scripts), y qué espera `test-e2e-vault`.
2. **Diseño del paso 6** (escrito antes del código, decisiones de Alonso): etcd-server de la VM como servicio systemd;
   `make up` y `make emecas` levantan y aprovisionan la VM etcd de cero sin pasos manuales; fuera del defender el
   etcd-server y el Vault dev (y `tls.modo=http`, `almacen.modo=memoria`, `almacen_claves.modo=memoria`);
   `pipeline-start` sin `etcd-server-start`; qué hacer con `test-e2e-vault`; `pipeline-status` mirando el etcd-server de
   la VM (DEBT-PIPELINE-STATUS-LIVENESS-001). Predicción del paso: en el defender nada escucha en 2379 ni 8200.
3. **Paso 7**: instrumento de reinicio de DAY311 en la VM (misma huella, bronce anterior verificable, registro
   conservado, latidos 200). B1/B2 ya midieron misma huella y registro conservado; falta el bronce verificable.
4. **Paso 8: EMECAS+++ production** (rc 0, 5/5 E2E con PASA, cinco líneas de test-components). Antes, rehacer la VM etcd
   (DEBT-LAB-VAULT-CLAVES-PRUEBA-001: claves de prueba inmutables en Vault); EMECAS con `destroy -f` ya lo hace si la VM
   entra en la cadena.

## Plan acordado al cierre de DAY316 (Alonso): primero certificar etcd, después lo demás

1. Cierre del PR1 (un nodo): pasos 6, 7 y 8 de arriba. En el paso 6, `pipeline-status` comprueba el etcd-server Y el etcd
   de la VM (estado real, no solo procesos) y `make up` levanta la VM etcd.
2. PR2, HA de verdad: **al menos 3 nodos etcd** (decisión de Alonso), cada uno con su etcd-server, y Vault HA. Tests:
   tirar un nodo (también el líder) y ver que otro toma el control; el estado de los componentes sigue sincronizado entre
   nodos; medir cuánto tardan en sincronizarse tras la caída y la vuelta. Antes, la RAM (diseño, sección 6).
3. DEBT-ETCD-VIGILANCIA-FALCO-WAZUH-001: Falco y Wazuh vigilando etcd y el etcd-server (Falco ya existe en hardened-x86;
   medir qué vigila hoy). Después del PR2.
4. Jenkinsfile capaz de producir el pipeline en producción (hoy no puede, medido DAY315).
5. Preproducción: imagen mínima con 2-3 servidores detrás del firewall en FORWARD, para ver llegar la protección.
   Cuando etcd y las cabezas estén certificados.

## Deudas abiertas que NO bloquean EMECAS (por si sobra tiempo; ninguna decidida aún)

DEBT-ETCD-CONFIG-SIZE-ENDIAN-001 (tamaño LE/BE en `PUT /v1/config`, el servidor cae a la cabecera HTTP),
DEBT-ETCD-CLIENT-MANUAL-TESTS-CTEST-001, DEBT-SNIFFER-LIBPCAP-ETCD-001, DEBT-FW-CSV-SIN-FILAS-EN-GATE-001 (con la
pregunta abierta de los `DRY_RUN_BLOCK`), DEBT-PKI-AT-REST-001, DEBT-GRAPH-HUECO-SIN-CLAVE-001,
DEBT-CONFIG-AT-REST-PROTECTION-001 (propuesta sin confirmar), DEBT-REPO-RESIDUOS-001 (cuatro `scripts/d31*_parche.py`
sin trackear, `etcd_client_simple.cpp` que es bash, bloque etcd de correlation-engine), PR2 (varios nodos etcd +
etcd-server, Vault HA, `peer-cert-allowed-cn`, una CA por despliegue).

## Herramientas de Claude (en su contenedor, no en el repo)

Banco Debian 12 en `/srv/banco` (GCC 12.2.0, flags de production, libsodium 1.0.19, httplib v0.63.0, etcd-cpp-apiv3
v0.15.3, libbpf v1.4.6, onnxruntime 1.17.1); `banco_completo.sh <árbol> <etiqueta>` compila la cadena del Makefile y
pasa ctest (sniffer 19/23 en el banco: 4 de entorno, `libbpf.so.1` y `boot_id`; `proto rc=1` también en el control: se
compila con los `.pb.*` del repo). Si el contenedor es nuevo, hay que rehacerlo.

## Reglas

Medir, no votar; predicción escrita antes; si algo no da lo esperado, parar. Todo lo que se compile, probarlo antes en
el banco con las opciones de production (g++-12, `-O3 -march=native -DNDEBUG -flto`), dos veces seguidas y contra el
comportamiento viejo (mutaciones: tiene que fallar). Parcheadores con `--check`/`--apply <raíz>`, todo o nada,
idempotentes; se copian a `scripts/etcd_ha/` y se ejecutan desde allí; entregados con su sha256. Comandos exactos, uno
por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM etcd con `vagrant ssh etcd -c`); las salidas largas
a un fichero con `; cat` al final; un log por comando. Búsquedas con `git grep`, nunca `grep -r`. Sin emojis en los
comandos. El repo es de solo lectura para Claude: los commits los hace Alonso, uno por cambio lógico.
