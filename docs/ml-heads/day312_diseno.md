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

## Diseño del paso 4b (código del etcd-server) — DAY312, escrito ANTES de tocar código

Base: rama `feat/etcd-mtls-vault` en `b5227f85` (4a: el etcd-server actual corre en la VM etcd). Lo que sigue es la
propuesta; las decisiones abiertas están en 4b.0 y nada se escribe hasta tenerlas.

### Medido para este diseño

- etcd-cpp-apiv3 v0.15.3 (la que fija el Vagrantfile): `SyncClient(url, ca, cert, privkey, target_name_override)`
  con TLS y certificado de cliente; `url` admite varios endpoints separados por coma (sirve para el PR2). Sus
  dependencias de ejecución son todas paquetes Debian (gRPC 1.51, protobuf 32, cpprest 2.10, abseil): la herramienta
  de despliegue de 4a las resuelve con `dpkg -S` sin cambios.
- La pasarela JSON de etcd 3.6.16 rechaza toda petición con certificado de cliente ("CommonName … will be ignored"):
  con RBAC por CN, el etcd-server habla con etcd solo por gRPC.
- `common/vault_client` es específico de la semilla de familia (token, libcurl, `fetch_seed`): no sirve tal cual
  para KV v2 con auth por certificado.

### 4b.0 Decisiones abiertas para Alonso

- **B1. Cliente de Vault.** (a) clase pequeña nueva en el etcd-server sobre cpp-httplib `SSLClient` (ya enlazado,
  sin dependencias nuevas): login por certificado + KV v2 leer/escribir; (b) extender `common/vault_transport`
  (libcurl) con una interfaz nueva. Propuesta: a.
- **B2. Tabla de autorización por ruta en el JSON** (el JSON es la ley; defectos iguales en el código; cada fila
  registrada en el log al arrancar con `[CONFIG]`/`[CONFIG-DEFAULT]`) frente a fija en el código. Propuesta: JSON.
- **B3. Instancias del registro.** Hoy el nombre con que se registra cada componente está fijo en su `main.cpp`. En
  4b el etcd-server toma la identidad del certificado (CN = instancia, OU = rol) y **rechaza** un registro cuyo nombre
  no coincida con el CN (403). Los componentes no cambian (CN = nombre actual). Propuesta: así.
- **B4. Clave HMAC del firewall** pasa a `/secrets/firewall-acl-agent` (P4). Antes de cambiarlo: `git grep` de
  quién verifica hoy el CSV del firewall con `/secrets/firewall`.

### 4b.1 Configuración: el JSON es la ley

`etcd-server.json` pasa a tener, con rango y formato documentados en el propio JSON (`_doc`), y leído campo a campo:

| Bloque | Campos |
|---|---|
| `server` | `listen_host` (IPv4), `port` (1-65535) |
| `tls` | `ca_file`, `cert_file`, `key_file` (rutas que deben existir) |
| `authz` | tabla ruta → identidades permitidas (CN propio, OU, `admin`) |
| `etcd` | `endpoints` (lista https://…), `ca_file`, `cert_file`, `key_file`, `prefix` (`/argus/`), `timeout_ms` |
| `vault` | `addr`, `ca_file`, `cert_file`, `key_file`, `kv_mount` (`argus-hmac`), `cert_role` (`etcd-server`), `aviso_intervalo_s` |
| `secrets` | los de hoy (`grace_period_seconds`, `rotation_interval_hours`, `default_key_length_bytes`, `min_rotation_interval_seconds`) |
| `heartbeat` | `interval_seconds`, `timeout_multiplier`, `check_interval_seconds` |

Campo ausente o mal formado → defecto (igual al del JSON) + aviso con campo, formato y límites; el log de arranque
recoge la configuración efectiva completa y de dónde sale cada valor. Campos que no hacen nada (`auto_restart.*`,
`security.*`, `server.worker_threads`, `secrets.storage`, `secrets.keys`) → `[CONFIG-OBSOLETO]` y fuera del JSON.
Cierra DEBT-ETCD-SECRETS-CONFIG-HARDCODED-001. `--check-config` local: lee, valida, imprime la configuración
efectiva y sale (rc 0 / 1).

### 4b.2 Arranque

Orden corregido: `/run/argus` antes del `AutonomyPublisher` (medido 4a). Sin Vault ni etcd alcanzables el proceso
arranca igual y sirve lo que tenga (ver 4b.5), con aviso periódico; sin certificados TLS válidos no arranca
(no hay forma segura de servir).

### 4b.3 HTTPS + mTLS y autorización

- `httplib::SSLServer` con la CA del lab y verificación del certificado de cliente obligatoria. Sin certificado
  válido no hay TLS (no llega a ninguna ruta).
- Un único punto de autorización antes del enrutado (`set_pre_routing_handler`): CN y OU del certificado del par →
  tabla `authz`. Denegado → 403 y `[ETCD-AUTHZ-DENEGADO] cn=… ou=… metodo=… ruta=…`.
- Rutas que se borran: `/seed`, `/secrets/keys` (sin uso; medido en el inventario).
- `log_request` registra el estado REAL, después de decidir (DEBT-ETCD-HEARTBEAT-LOG-STATUS-001).

### 4b.4 Registro, configuración y época en etcd

`ComponentRegistry` deja de guardar en un `unordered_map` sin mutex: interfaz `IRegistryStore` con dos
implementaciones, `EtcdRegistryStore` (gRPC, prefijo `/argus/`) y `MemoriaRegistryStore` (solo tests). Claves:
`/argus/registro/<CN>`, `/argus/config/<CN>`, `/argus/latido/<CN>`, `/argus/epoca`. El registro sobrevive a un
reinicio del etcd-server (medido DAY311: hoy vuelve vacío).

### 4b.5 Claves HMAC en Vault (ventana de dos)

- Una entrada inmutable por clave: `argus-hmac/<CN>/<huella8>` = {clave, creada}; un puntero
  `argus-hmac/<CN>/ventana` = {activa, anterior, expira_anterior}. Nunca se borra una clave (la política no lo
  permite: medido M2d).
- Leer-o-crear bajo UN solo bloqueo (la carrera de DAY311: dos primeras peticiones podían crear dos claves).
- Caché en memoria de la ventana. Vault no disponible: se sirve la ventana en caché, `[ETCD-VAULT-NO-DISPONIBLE]`
  cada `aviso_intervalo_s`, no se rota. Sin caché (arranque con Vault caído): no se sirve clave; el ml-detector ya da
  `[BRONCE-SIN-CLAVE]` y el firewall sigue actuando.
- En el log, solo la huella (8 hex del SHA-256), nunca la clave.

### 4b.6 Fuera (código muerto o peligroso)

`auto_restart` + `system("systemctl restart …")`, `get_encryption_seed/key`, `rotate_encryption_key`,
`set_compression_mode/set_encryption_mode` sin uso, el `HttpEtcdRegistrar` del etcd-server hacia sí mismo si deja de
hacer falta (comprobar con `git grep` quién lee `/v1/epoch` aparte de él), `etcd_client_base.cpp`,
`etcd_client_manual.cpp`, `*.day54_*` (DEBT-ETCD-CLIENT-DEAD-VARIANTS-001).

### 4b.7 Pruebas y predicciones

- Tests unitarios nuevos del etcd-server (sin red): lectura del JSON (campo bueno, ausente, mal formado, fuera de
  rango), tabla de autorización, ventana de dos con almacén falso (crear, rotar, expirar, Vault caído). Línea nueva
  en `make test-components PROFILE=production`; las cinco de hoy (9/23/13/3/82) no cambian.
- En la VM etcd (instrumento nuevo `d312_es_medir.sh`): sin certificado → TLS falla; sniffer pide
  `/secrets/ml-detector` → 403; ml-detector pide `/secrets/ml-detector` → 200 y huella; latido de no registrado →
  log con 404; reinicio del etcd-server → misma huella y registro conservado.
- Compilación completa en producción con 0 diagnósticos.
