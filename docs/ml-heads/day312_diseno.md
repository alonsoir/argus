# DAY312 — Diseño del PR1 de DEBT-ETCD-HA-TLS-RAFT-001 (etcd-server en un nodo, HTTPS + mTLS, claves en Vault)

Base: `main` `cabac77` (merge PR #152, `pre-release-rag-logger-retire-0.0.9`). Inventario previo:
`day312_inventario_etcd.md`. Este documento se escribe ANTES de medir; los resultados van en secciones aparte.

## 1. Decisiones de Alonso (DAY312)

- **D1 = A.** El etcd real como almacén (Raft y TLS nativos) y nuestro etcd-server como fachada HTTPS sin estado
  propio, hablando con etcd por etcd-cpp-apiv3. Las claves HMAC no van a etcd: van a **Vault**, y el etcd-server las
  recupera de Vault cuando hacen falta.
- **D2.** mTLS: un certificado de cliente por componente; CA generada en el portátil, Jenkins orquesta y verifica
  (igual que la semilla de ChaCha20). Autorización por ruta según la identidad del certificado.
- **D3.** PR1 = un nodo (este documento). PR2 = HA con Raft. El re-registro tras 404 y el comportamiento idéntico de los
  tres componentes van en la rama siguiente (DEBT-FW-HMAC-KEY-ALARM-001).
- **D4.** El etcd-server sale del defender. HA real fuera del defender; el reparto de nodos del PR2 se decide con la
  RAM medida (ver §6).
- **V1.** Vault en modo servidor ya, con persistencia. Desellado **c** (clave de desellado en disco de la propia VM):
  solo para el laboratorio, aRGus sigue sin estar sellado para producción. En producción se decidirá entre a (manual,
  Shamir) y b (auto-unseal).
- **V2.** Vault sale del defender y se va con el etcd-server a la VM nueva.
- **V3.** En este PR solo las claves HMAC pasan al Vault en modo servidor. El resto de secretos (`secret/argus/crypto`,
  `vendor-key`, token enterprise) en otro PR (deuda nueva DEBT-VAULT-REST-SECRETS-001).

## 2. Medidas ya hechas (antes)

- **M0 (DAY312, Mac → client).** Predicción: rc 0, HTTP 200, `initialized:true`, `sealed:false`.
  Resultado: `hostname` = ml-client; `http=200`; `rc=0`; `initialized:true`, `sealed:false`, `version:2.2.1`.
  **PASA.** Vault dev del defender se alcanza sin token desde la posición del atacante (192.168.100.1:8200), igual que
  el 2379 (DAY311). Nueva deuda: DEBT-VAULT-DEV-EXPOSED-001 (se cierra con este PR al sacar Vault del defender).
- DAY311 (instrumento `scripts/bronze_key/d311_reinicio_etcd.sh`): tras reiniciar el etcd-server, claves nuevas (bronce
  anterior no re-verificable), registro vacío, latidos 404 invisibles, log 200 frente a 404. Es el "antes" del paso 7.

## 3. Arquitectura del PR1

```
 defender (192.168.100.1)                          VM nueva "etcd" (propuesta 192.168.100.20)
 ┌───────────────────────────┐   HTTPS + mTLS     ┌────────────────────────────────────────────┐
 │ sniffer / ml-detector /   │ ─────────────────► │ etcd-server (fachada, :2379)               │
 │ firewall (libetcd_client) │                    │   ├─ registro/config/época ─► etcd :2381   │
 └───────────────────────────┘                    │   │        (TLS, solo 127.0.0.1)           │
 Mac: mitre/ctu/custom_start                      │   └─ claves HMAC ─► Vault :8200            │
   (curl con cert de admin)                       │            (TLS, auth por certificado,     │
                                                  │             almacenamiento raft, 1 nodo)   │
                                                  │ nftables: 2379 solo desde .1 .10 .11 .12   │
                                                  └────────────────────────────────────────────┘
```

- etcd y Vault solo los usa el etcd-server: escuchan en 127.0.0.1 de la VM nueva. Nada del pipeline les habla
  directamente.
- Puerto del etcd real distinto de 2379 (que sigue siendo el de la fachada, para no tocar los JSON de los componentes
  más que en el host): propuesta 2381 cliente / 2382 peer. En el JSON del etcd-server.
- **Claves HMAC en Vault KV v2**, una entrada inmutable por clave (`argus-hmac/<componente>/<huella8>`) más un
  puntero (`argus-hmac/<componente>/ventana` = {activa, anterior, expira_anterior}). Nunca se borra una clave: el
  grafo debe poder re-verificarse años después (DAY310). Esto deja preparado DEBT-BRONZE-KEY-ID-001 sin hacerlo aquí.
- Autorización por ruta (identidad = CN del certificado de cliente):

  | Ruta | Quién |
  |---|---|
  | POST /register, /unregister, /v1/heartbeat/{c}, PUT /v1/config/{c}, GET/PUT /config/{c} | solo el CN = {c} |
  | GET /secrets/{c}, GET /secrets/valid/{c} | CN = {c}, y el conversor/verificador (CN propio) en lectura |
  | POST /secrets/rotate/{c}, PUT /v1/epoch, GET /components, /validate, /info | solo CN admin |
  | GET /health | cualquiera con certificado de la CA |
  | GET /seed, GET /secrets/keys | se borran (muertas: ver inventario) |

  Sin certificado válido: el TLS no llega a establecerse. Con certificado válido y ruta no permitida: 403 y línea
  `[ETCD-AUTHZ-DENEGADO]` con CN, método y ruta.
- Fuera en este PR (código muerto o peligroso): `auto_restart` + `system()`, `get_encryption_seed/key`,
  `rotate_encryption_key`, `/seed`, `/secrets/keys`, el `HttpEtcdRegistrar` del etcd-server hacia sí mismo si el
  registro deja de hacer falta (a comprobar), `etcd_client_base.cpp`, `etcd_client_manual.cpp`, `*.day54_*`
  (DEBT-ETCD-CLIENT-DEAD-VARIANTS-001), etcd-cpp-api opcional del ml-detector (ningún fuente lo usa).
- El JSON es la ley: `server.*`, `secrets.*`, `heartbeat.*`, rutas de certificados, direcciones de etcd y Vault, todo
  leído por campo con `[CONFIG]`/`[CONFIG-DEFAULT]` (cierra DEBT-ETCD-SECRETS-CONFIG-HARDCODED-001). Campos que hoy
  no hacen nada y no se implementan aquí (`auto_restart`, `worker_threads` si no se cablea): `[CONFIG-OBSOLETO]` y
  fuera del JSON.
- Versiones fijadas: Vault (hoy sin fijar, se instaló 2.2.1), etcd, cpp-httplib (hoy `git clone` sin etiqueta).
  `CPPHTTPLIB_OPENSSL_SUPPORT` igual en todo lo que enlace `libetcd_client.so` (riesgo ODR, ver inventario §3.10).
- Vault no responde o sellado: el etcd-server sigue entregando la clave vigente que tenga en memoria, marca
  `[ETCD-VAULT-NO-DISPONIBLE]` periódica (intervalo en el JSON) y no rota. Sin clave en memoria (arranque con Vault
  caído): no entrega clave; el ml-detector ya da `[BRONCE-SIN-CLAVE]` y el firewall sigue actuando (D3 de DAY310).

## 4. Pasos, con su predicción

Cada paso: antes/después, compilación completa en producción, `make test-components PROFILE=production` con las
cinco líneas, y PARAR si algo no da lo predicho.

| # | Paso | Predicción escrita antes |
|---|---|---|
| 0 | Material: CA + certificados (etcd-server, sniffer, ml-detector, firewall, conversor, admin), script en el Mac, claves privadas fuera de git | `openssl verify -CAfile ca.pem` OK en los 6; ningún `.key` aparece en `git status` |
| 1 | VM "etcd" en el Vagrantfile (bookworm 12.20240905.1, RAM según §6), nftables | `vagrant up etcd` rc 0; desde el client, `curl` a :2379 → conexión rechazada o timeout; desde el defender, abierto |
| 2 | Vault en modo servidor en la VM: listener TLS, almacenamiento raft (1 nodo), init 1/1, desellado c por systemd, auth cert, política solo-etcd-server | `vault status` → sealed false tras `vagrant reload etcd` sin intervención; escribir clave → reiniciar Vault → misma huella; desde el client :8200 no alcanzable |
| 3 | etcd 1 nodo en la VM, TLS, solo 127.0.0.1 | `etcdctl endpoint health` (TLS) OK; put/get sobrevive a reinicio de etcd |
| 4 | etcd-server: JSON leído, HTTPS+mTLS, autorización, registro/config/época en etcd, claves en Vault con ventana de dos, log con el estado real, mutex/sin carrera, fuera el código muerto | tests nuevos del etcd-server en verde; sin cert → TLS falla; cert de sniffer pidiendo /secrets/ml-detector → 403; latido de no registrado → log con 404 |
| 5 | libetcd_client con TLS + certificado de cliente; JSON de los componentes apuntando a 192.168.100.20; scripts del lab con cert de admin | pipeline-start: los 3 componentes registrados (GET /components con cert admin → 4 con el etcd-server); ml-detector `[BRONCE-CLAVE]` con huella |
| 6 | Vault y etcd-server fuera del defender | en el defender, nada escucha en 2379 ni 8200 |
| 7 | Repetir el instrumento de reinicio de DAY311 (adaptado a la VM nueva) | tras reiniciar el etcd-server: misma huella de clave, bronce anterior verificable, registro conservado, latidos 200 |
| 8 | EMECAS+++ production | rc 0, 5/5 E2E con PASA, cinco líneas de test-components |

## 5. Preguntas abiertas para Alonso

- P1. Nombre e IP de la VM nueva (propuesta: `etcd`, 192.168.100.20, libre en el Vagrantfile).
- P2. Dónde viven en el Mac la CA y las claves privadas del lab (propuesta: directorio fuera del repo, p. ej.
  `~/argus-pki/`, copiado a las VMs en el aprovisionamiento) y si Jenkins ya entra en este PR o en el de producción.
- P3. ¿El conversor bronce→oro y la verificación del grafo entran como CN propio con lectura de `/secrets/valid/{c}`?

## 6. RAM (para decidir el reparto del PR2)

Hoy, con todo levantado: defender 8192 + client 1024 + suricata 2048 + zeek 2048 + wazuh 4096 = 17408 MB asignados.
La VM nueva del PR1 suma lo que se mida (propuesta inicial 1024 MB). Para el PR2 hay dos caminos, a decidir con la RAM
del Mac medida:
- tres nodos en VMs pequeñas (si bookworm + etcd + Vault caben en ~512 MB; medir);
- tres nodos en una sola VM, cada uno en su espacio de red (`ip netns`): Raft, caída de nodo y particiones medibles
  de verdad; la caída de la VM entera no.

## Resultados DAY312 (medidos; se añaden aparte, sin reescribir las secciones de diseño escritas antes de medir)

Rama `feat/etcd-mtls-vault` (sobre `main` `cabac77`). Commits: `e7309db2` (Vault dev en loopback + diseño + PKI),
`a3ad992d` (paso 1, VM etcd), `7df8914e` (paso 2, Vault en modo servidor).

### R0. Exposición del Vault dev del defender

- M0 (client → 192.168.100.1:8200/v1/sys/health): predicción 200, `sealed:false`. Resultado: `ml-client`, 200,
  `initialized:true`, `sealed:false`, 2.2.1. **PASA**. El Vault dev se alcanzaba sin token desde la posición del
  atacante, con el token root `argus-dev-token` escrito en el repo público.
- M0-b, ¿algo de fuera del defender usa el 8200? Primera captura (180 s): `syn_total=0`, **no válida**: la ventana se
  cerró antes de que `pipeline-start` llegara al `vault status` (diario: 07:56:41–07:59:41 CET; el arranque terminó
  hacia las 08:00:30). Control positivo (30 s + `vault status`): 1 SYN desde 127.0.0.1, el instrumento ve loopback.
  Repetición (600 s, parada + arranque + ~6 min): 1 SYN, desde 127.0.0.1 (el `vault status` del final). **PASA**:
  0 SYN no-loopback. Además, el etcd-server no habla con Vault en la compilación actual (0 conexiones en su arranque
  ni en su vigilancia cada 5 s). `git grep` coincide: todo lo que usa 127.0.0.1:8200 corre dentro del defender.
- Cambio (camino a, decisión de Alonso): Vault dev solo en 127.0.0.1 (Vagrantfile y Makefile), fuera el
  forwarded_port 8200. Resultado tras `vagrant reload defender`: escucha solo `127.0.0.1:8200`; defender 200; client
  `http=000` rc=7; Mac `http=000` rc=7; pipeline 4/4 RUNNING y `vault: RUNNING [dev]`. **PASA**.
  DEBT-VAULT-DEV-EXPOSED-001 cerrada para el Vault dev; el resto de secretos del Vault dev sigue en el defender
  hasta DEBT-VAULT-REST-SECRETS-001.

### R1. Paso 1, VM etcd

- `vagrant up etcd` rc=0; `etcd-base OK`, hora de 192.168.100.1, nftables `argus_etcd` cargada.
- Primera medida del cortafuegos: defender rc=7 (rechazo), predicho 200. **PARADA**. Hipótesis escritas antes de
  mirar: H1 ventana de 120 s cerrada; H2 servidor de prueba muerto; H3 regla `reject`. Diario: servidor de prueba
  07:54:06–07:56:06 UTC, `status=124` → H1. El rechazo prueba que el paquete del defender sí cruzaba nftables.
- Repetición (600 s): defender `http=200` rc=0; client `http=000` rc=28 (descartado). **PASA**.

### R2. Paso 2, Vault en modo servidor en la VM etcd

- Versión medida en el defender: `2.2.1-1` (predicho). Fijada en `VAULT_INSTALL`, compartido por defender y etcd.
- Primer `vagrant provision etcd`: rc=1 sin ejecutar nada (`File provisioner: The following settings shouldn't
  exist: name`). Corregido (`provision "pki-…", type: "file"`). Segundo: rc=0, Vault 2.2.1 (0e7c41b9, el mismo build
  que el defender) instalado y fijado, inicializado 1/1, root revocado, `sealed=False storage=raft`.
- `d312_vault_medir.sh`: M1-M6 **PASA** (login CN=etcd-server; escribir y releer; borrar 403; fuera de argus-hmac/
  403; certificado de sniffer 400; sin certificado sin TLS, curl rc 55/56; escucha solo 127.0.0.1:8200; unseal.key
  600 root). 8200 de la VM etcd desde defender y client: rc=28.
- Tras `vagrant reload etcd`, sin intervención: desellado, y `argus-hmac/d312/prueba` sigue con `d312abcd`
  (**persiste**). La entrada de prueba no se puede borrar (política): queda como rastro de la medida.
- Defender: `vault-install` → `✅ Vault 2.2.1-1 ya instalado y fijado` (el cambio de sitio no altera nada).
- Residuo anotado: el paquete genera un certificado autofirmado en `/opt/vault/tls` que no se usa.

### Lecciones DAY312

- La predicción del hostname se saca del Vagrantfile: el defender no tiene `vm.hostname` y se llama `bookworm`.
- Un instrumento que puede no ver nada no refuta nada: control positivo antes de interpretar un 0.
- Las ventanas de medida, con margen amplio y la hora UTC en cada línea: 120 s no alcanzan a ritmo humano con
  `vagrant ssh` (~15 s cada uno).
- Un parcheador se prueba sin los ficheros de trabajo de quien lo escribe (uno leía `/home/claude/work/…`).
- Una validación que pasa sobre una entrada vacía no vale: control negativo (nft sobre un fichero vacío daba OK).
- El aprovisionador `file` de Vagrant no admite `name:`; el nombre va como primer argumento con `type: "file"`.
- Un `grep` que busca un secreto lleva el secreto en sus argumentos: no se comprueba así.
