# Prompt de continuidad — DAY320 (tras DAY319, viernes 2026-11-06)

Hola, Claude. Soy Alonso (aRGus NDR). Seguimos con DEBT-ETCD-HA-TLS-RAFT-001, rama `feat/etcd-mtls-vault`, y dentro con
DEBT-FW-MANIFIESTO-PROTEGIDOS-001 (ADR-060). Responde en español. Lee ADR-060 entero y el final de `docs/BACKLOG.md`.
Comprueba con `git log --oneline -5` que HEAD es el commit de docs de DAY319 (posterior a `6b88a0c84`). **DAY320 empieza en 8e.3e.**

## Hecho DAY319 (3 commits, 05:37-07:30)
| commit | qué |
|---|---|
| a831c44b0 | 8e.3d-0 etcd-server: `GET /v1/protegidos/v/{n}` (solo ou:argus-infra; 400/404/503), 16 reglas authz |
| 6b88a0c84 | 8e.3d `tools/argus-infra/` (Python 3.11 stdlib): init/list/add/del/diff/verificar/deshacer; `argus-infra.lab.json`, `plantillas/hospital-lab.json`, tests unittest, aprovisionador `argus-infra` de la VM etcd (run: always), `make test-argus-infra` |

Decisiones de Alonso DAY319 (G-A..G-G): configuración `/etc/argus-infra/argus-infra.json` sin defecto sano para la
identidad (solo `timeout_s` [1,120] 10); plantilla separada (límites siempre de la configuración); historial por ruta nueva
del etcd-server (G-C); confirmación tecleando el número de versión (`--si` para bootstrap); orden de cada cambio: login
Vault, vigente validado (reglas portadas + transit verify), N+1, diff, confirmar, sign, verify, PUT, GET byte a byte,
revoke-self. Salidas 0/1/2/3 (3 = rechazo del etcd-server).

Cambio sobre G-D, medido: `firmante` = `<cn> entidad=<entity_id de Vault>` (<= 64 caracteres) porque el etcd-server y el
firewall cortan a 64 con `saneado()`; con el formato largo el entity_id se perdía.

## Medido
- Banco: etcd-server 8/8 (native y skylake), 4 mutaciones; unittest 19/19; diferencial C++ (libs/protegidos) vs Python con
  8000 cargas, 0 discrepancias (mutación detectada: 94); E2E 43/43 x3; 12 mutaciones de argus-infra detectadas.
- Lab: `pipeline-build` rc 0; etcd-server ctest 8/8; `etcd-vm-deploy` SANO; `regla 16/16`; huella 52ba6180cf5e8e9a en
  argus-infra, etcd-server y firewall; `make test-argus-infra` 19 OK; publicadas v1..v4. Firewall: al arrancar
  `[PROTEGIDOS-MANIFIESTO] verificado version=3 ... entradas=2 (infraestructura=1 intranet=1 ...) (etcd-server)`, caché
  1036 B y `.version`=3; en vivo `[INFRA-CAMBIO] version 3 -> 4 ... altas=[intranet 192.168.100.62/32 eth2] bajas=[]`.
  Primera prueba real de 8e.3c: PASA. Al cierre: `deshacer 1` firmó la v5 (contenido de la plantilla) y el firewall
  registró `[INFRA-CAMBIO] version 4 -> 5 ... bajas=[intranet 192.168.100.62/32 eth2]`. Lab vigente: v5.
- Notas: `[INFRA-CAMBIO]` solo sale si había vigente (con la v1 no). La VM etcd es `autostart: false`: `vagrant up etcd`
  antes de `etcd-vm-deploy`. `pgrep` sin `-f` no casa nombres de más de 15 caracteres.

## Lo que queda, por orden
1. **8e.3e** borrar `set/get/del/list_keys` del etcd-client (`/kv/...`) tras `git grep` de usos.
2. **Docs de 8e.3** (ADR-060: F-C con la ruta del historial, G-A..G-G, firmante corto; BACKLOG con las medidas de arriba).
3. **8e.4** vigilancia (kernel <-> manifiesto, antispoofing raw PREROUTING, MAC, rp_filter, versión en latido y
   pipeline-status, Falco/Wazuh, alarma de disco del audit de Vault 75 %).
4. **8e.5** bootstrap con `argus-infra init --si` (.20 y .61), reescribir `d303_veredicto_protegidos.sh` (P1-P6),
   meter `test-argus-infra` en EMECAS.
5. **EMECAS+++ PROFILE=production**: rc 0, `lab-e2e-protegidos` P1-P6 PASA, Acto IV con `err_to_row=0`.
6. **Cierre del PR1**: comprobar que el arranque del lab levanta la VM etcd (DAY319: `vagrant up` a secas no, es
   `autostart: false`; el plan de DAY316 pedía `make up` con la VM etcd), README del etcd-server (DAY311), push y PR.
   Lo demás (HA de 3 nodos, Vault HA, Ansible de Vault, transacción de etcd en el PUT) es PR2.

## Banco de Claude (contenedor; si es nuevo, rehacer)
Chroot Debian 12 en `/srv/banco` (debootstrap minbase + `gcc g++` de Debian para el plugin LTO de `ar`, `cppzmq-dev`),
libsodium 1.0.19, httplib v0.63.0, etcd-cpp-apiv3 v0.15.3, Vault 2.2.1, etcd 3.6.16, PKI con `d312_pki.sh init`, identidad
del etcd-server (seed.bin 32 B + par ed25519). Scripts: `/root/banco_plano.sh arrancar hospital-lab` (etcd + Vault como
la VM), `/root/banco_es.sh ARBOL ETIQUETA` (MARCH, LIBS=1), `/root/e2e_8e3d.sh`, `/root/mut_8e3d.py`, `/root/mut_es.sh`,
`/root/dif/{arnes.cpp,dif.py,verifica_sobre.cpp}`. Generador de parcheadores `/home/claude/gen/generar.py VIEJO NUEVO
SALIDA "cabecera" RUTAS...` (funde trozos solapados).

## Reglas
Las de siempre: medir, no votar; predicción escrita antes; si no da, parar. Banco con opciones de production, native y
skylake, dos veces, mutaciones. Pipeline completo. Parcheadores `--check`/`--apply`, todo o nada, idempotentes, sha256, a
`scripts/etcd_ha/`. Comandos exactos, uno por bloque, diciendo dónde. Repo de solo lectura para Claude; Claude propone
el `git commit -m`.
