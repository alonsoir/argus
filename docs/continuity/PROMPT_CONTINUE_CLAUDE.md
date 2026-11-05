# Prompt de continuidad — DAY319 (tras DAY318, jueves 2026-11-05)

Hola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001** en la rama
`feat/etcd-mtls-vault` (PR1, un nodo) y, dentro de ella, con **DEBT-FW-MANIFIESTO-PROTEGIDOS-001** (ADR-060, paso 8e).
Responde siempre en español. Lee, en este orden:
`docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md` (entero: decisiones D1-D11, D-A..D-I, F-A..F-I, plan
8e.1-8e.5 y diseño fino) y el final de `docs/BACKLOG.md` (secciones `[PROTEGIDOS-MANIFIESTO-D318]` y
`[PROTEGIDOS-PUBKEY-D318]`).

**DAY319 empieza en 8e.3d.** Comprueba antes con `git log --oneline -12` que HEAD es `919813290` (o posterior).

## Hecho DAY318 (10 commits, 07:00-18:10)

| commit | qué |
|---|---|
| addc844a | docs: diseño fino de 8e (D-A..D-I) |
| 77077b47 | 8e.2 Vault transit: clave ed25519 `protegidos-<hospital>` no exportable, rol `argus-infra`, audit fichero + syslog, `make protegidos-pubkey` |
| 9e9c58c6 | docs de 8e.2 |
| 3af32373 | 8e.1a verificador del manifiesto (Ed25519 libsodium, JSON estricto, límites, versión, caché, clave compilada en dos ranuras) |
| f9076a97 | 8e.1b cableado: set `hash:net,iface` con swap atómico, regla `src,src`, candado D6, barrera por IP, avisos D6/D7/D-C; fuera `ddos_protegidos` y la whitelist |
| b8bf8a4a | docs de 8e.1 |
| 7d2b58e1 | docs: diseño de 8e.3 (F-A..F-I) y DEBT-FW-ARGUS-INFRA-LLAVE-HW-001 |
| a5a41ba4 | 8e.3a `libs/protegidos` (estática, `argus::protegidos`); validador de CIDR a `common/include/argus`; falso `stringop-overflow` de GCC 12 con `-march=skylake` |
| 465e6aa4 | 8e.3b etcd-server: `GET/PUT /v1/protegidos` (authz por OU), `verificar_documento`, etcd `protegidos/vigente` + `protegidos/v/<N>`, `protegidos.hospital_id` (Ansible) |
| 91981329 | 8e.3c firewall: `get_protegidos()` en etcd-client, consulta cada `consulta_sec`, `[INFRA-CAMBIO]`, anti-rollback con `<cache>.version` |

Medido en el lab al cierre: huella de la clave `52ba6180cf5e8e9a` igual en el firewall y en el etcd-server de la VM;
el firewall consulta y recibe 404 (no hay manifiesto publicado todavía); el lab está en `dry_run`.

## Lo que queda, por orden

1. **8e.3d** `argus-infra`: un fichero Python con la biblioteca estándar (Python 3.11.2 y OpenSSL 3.0.22 medidos en la
   VM etcd), instalado por el Vagrantfile en la VM etcd. `init --desde PLANTILLA`, `list`, `add`, `del`, `diff`,
   `verificar`, `deshacer N`. Login en Vault con `/etc/argus-pki/argus-infra.{crt,key}` (token 300 s, 127.0.0.1),
   firma con `argus-transit/sign/protegidos-<hospital>`, comprueba los límites de D2 y hace `PUT /v1/protegidos` con
   el mismo certificado. Plantilla `hospital-lab` en el repo: `.20` infraestructura por `eth2`, `.61` intranet.
   **Primera prueba real de 8e.3c:** al publicar la versión 1, el firewall tiene que aplicarla sin reiniciar
   (`[PROTEGIDOS-MANIFIESTO] verificado ... (etcd-server)`, caché y `.version` escritas).
2. **8e.3e** borrar `set/get/del/list_keys` del etcd-client (`/kv/...`, rutas que el servidor no tiene) tras
   comprobar con `git grep` que nadie los usa.
3. **Docs de 8e.3** (ADR-060 y BACKLOG).
4. **8e.4** vigilancia: kernel ↔ manifiesto, antispoofing `raw PREROUTING`, MAC, `rp_filter`, versión en el latido y en
   `pipeline-status`, Falco y Wazuh (incluida la alarma de disco del audit de Vault al 75 %).
5. **8e.5** bootstrap con `argus-infra` (`.20` y `.61`), reescribir `d303_veredicto_protegidos.sh` (P1-P6).
6. **EMECAS+++ PROFILE=production**: rc 0, `lab-e2e-protegidos` P1-P6 PASA, Acto IV con `err_to_row=0`.

Hasta 8e.5, `lab-e2e-mitigacion` y `lab-e2e-protegidos` fallan (sin manifiesto el candado para la mitigación).

## Herramientas de Claude (en su contenedor, no en el repo; si el contenedor es nuevo, hay que rehacerlas)

- Banco Debian 12 en `/srv/banco`: GCC 12.2.0, libsodium 1.0.19, httplib v0.63.0, Vault 2.2.1, gRPC 1.51,
  cpprest, etcd-cpp-apiv3 v0.15.3 (clonado fuera del chroot: dentro no hay CA del proxy).
- `/root/banco_fw.sh ÁRBOL ETIQUETA`: compila las librerías, el firewall y su ctest. Variables: `PUBKEY_ACTUAL`,
  `PUBKEY_SIGUIENTE`, `SOLO_FW=1` (solo el firewall; no sirve si cambia el etcd-client), `ES=1` (también el
  etcd-server y su ctest), `MARCH=skylake` (la CPU del defender; compilar SIEMPRE también así).
- `/root/vault_8e3b.sh` (Vault dev con la clave transit) y `/root/e2e_8e3b.sh` (etcd-server con mTLS + firma real +
  curl por rol, 12 pruebas).
- `/home/claude/gen/generar.py VIEJO NUEVO SALIDA "cabecera"` + `plantilla.py`: parcheador con ficheros nuevos,
  borrados y trozos anclados a partir de dos árboles (lista de rutas en `gen/rutas.txt`).

## Reglas

- Medir, no votar. Predicción escrita antes de medir; si algo no da lo esperado, parar.
- Todo lo que se compile se prueba antes en el banco con las opciones de production (g++-12, `-std=c++20 -Wall -Wextra
  -Wpedantic -Werror -O3 -march=native -DNDEBUG -flto -fno-omit-frame-pointer`, y además con `-march=skylake`), dos
  veces y contra el comportamiento viejo (mutaciones: tiene que fallar).
- Compilar el pipeline completo (`make pipeline-build PROFILE=production`), no un componente suelto.
- Parcheadores: `--check`/`--apply <raíz>`, todo o nada, idempotentes, con sha256 previo y final; se copian a
  `scripts/etcd_ha/` y se ejecutan desde allí; se entregan con su sha256; un sha por línea, nunca diccionarios largos
  con hex (ggshield); quedan sin trackear.
- Comandos: exactos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / VM etcd); salidas largas a
  un fichero con `; cat`; búsquedas con `git grep`; sin emojis.
- El JSON es la ley. Lo deprecado se borra. No romper la seguridad ni abrir un camino para romperla en producción.
- El repo es de solo lectura para Claude: los commits los hace Alonso, uno por cambio lógico; **Claude propone siempre
  el `git commit -m`**. Push solo al cerrar un paso grande o el día: tras cada commit basta `git rev-parse HEAD`.
