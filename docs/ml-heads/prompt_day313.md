# Prompt de continuidad — DAY313 (tras DAY312, viernes 2026-10-30)

Hola, Claude. Soy Alonso (aRGus NDR, único desarrollador). Seguimos con **DEBT-ETCD-HA-TLS-RAFT-001**: etcd-server con
HTTPS, autenticación, claves HMAC persistidas con ventana de dos, y HA Raft. Dos PRs como mínimo: **PR1 = nodo único**
(en curso), **PR2 = HA Raft**. Responde siempre en español.

El diseño completo y los resultados medidos están en `docs/ml-heads/day312_diseno.md` (secciones de diseño, R0–R2 con
sus lecciones, y el diseño de 4b). **Léelo antes de proponer nada.**

## Dónde estamos

Rama **`feat/etcd-mtls-vault`** (sale de main `cabac77`). Commits, en orden:

| commit | qué |
|---|---|
| e7309db2 | Vault dev del defender solo en loopback (`[VAULT-DEV-LOOPBACK-D312]`, fuera forwarded_port 8200); `day312_diseno.md`; `scripts/etcd_ha/d312_pki.sh` |
| a3ad992d | VM `etcd` (argus-etcd, 192.168.100.20, 1024 MB, 2 CPU): chrony + nftables `[VM-ETCD-D312]` |
| 7df8914e | `VAULT_INSTALL` única y fijada a 2.2.1-1; Vault en modo servidor en la VM etcd `[VAULT-SERVER-D312]`; `d312_vault_medir.sh` |
| aea129a9 | resultados R0–R2 en el doc de diseño |
| db33e3f8 | etcd 3.6.16 oficial (sha256 fijado) en la VM etcd `[ETCD-LOCAL-D312]`; cert etcd con EKU serverAuth+clientAuth (`d312_pki.sh reemitir`); `d312_etcd_medir.sh` |
| b5227f85 | `scripts/etcd_ha/d312_etcd_vm_deploy.sh` v3 (despliegue BSR: compilar en el defender, solo runtime a la VM etcd) |
| 267729c9 | diseño de 4b en el doc |
| **ee6d07ac** | **4b.1: configuración del etcd-server desde el JSON** (ver abajo) |

Todo medido PASA:
- R0: el Vault dev ya no responde desde fuera (client rc=7, Mac rc=7).
- Paso 1: firewall de la VM etcd (defender 200, client 28).
- Paso 2: Vault M1–M6 (persiste y se auto-desella tras reload; 8200 inalcanzable desde fuera).
- Paso 3: etcd M1–M8 (persiste tras reload).
- Paso 4a: el etcd-server SIN modificar corre en la VM etcd (defender /health 200, client 28).
- Paso 4b.1:
  - ctest del etcd-server 4/4 y total 82/82.
  - `--check-config` medido 3 casos: el JSON real da OK con rc=0; uno con `port:"x"` da 8 defectos y rc=1; uno inexistente, 8 defectos y rc=1.

### Lo que hizo 4b.1 (ee6d07ac)

**Configuración:**
- Nuevo `etcd-server/include/etcd_server/etcd_server_config.hpp`, en el namespace `argus::etcdcfg`. Es header-only, sin estado y al estilo de `flow_table_config.hpp`.
- Lee `server.{host,port}`, `secrets.{grace_period_seconds, default_key_length_bytes, min_rotation_interval_seconds}` y `heartbeat.{interval_seconds, timeout_multiplier, check_interval_seconds}`.
- Si un campo falta, tiene otro tipo o está fuera de rango, avisa con `[CONFIG-DEFAULT]` (campo, formato y límites) y aplica el defecto.
- Reglas: `min_rotation >= grace` (si no, los dos a defecto) y `check <= interval*multiplier` (si no, los tres de heartbeat a defecto).
- Los campos que ya no se usan avisan con `[CONFIG-OBSOLETO]`.
- La línea `[ETCD-CONFIG]` dice el valor y el origen de cada campo.

**main.cpp:**
- Opciones `-c/--config RUTA` y `--check-config` (rc 0 sin defectos, 1 con alguno, 2 si los argumentos están mal).
- `/run/argus` se crea antes del AutonomyPublisher (era el fallo de la VM etcd).
- SecretsManager, EtcdServer (host:puerto), ComponentRegistry (latidos), SeedClient y AlertClient toman todo del mismo JSON.
- El registrador de épocas usa `host:port` (127.0.0.1 si el host es 0.0.0.0).

**Limpieza:**
- Fuera `rotation_interval_hours` y `SecretsManager::Config`.
- `etcd-server.json` sin campos obsoletos y con `_doc`.
- Test nuevo `tests/test_etcd_server_config.cpp`, con 11 casos gtest.

**Este binario NO se ha desplegado aún en la VM etcd.** El que corre allí es el de 4a, sin modificar.

**Detalle cosmético pendiente**, para arreglarlo en 4b.2: la línea resumen `[CONFIG-DEFAULT] N ajustes con valor por defecto en etcd-server.json` pone el nombre fijo aunque el fichero sea otro (`-c /tmp/roto.json`). Debe poner la ruta real.

## Decisiones tomadas (respetarlas)

**Arquitectura:**
- **D1=A:** etcd real como almacén; nuestro etcd-server es la fachada HTTPS. Las claves HMAC viven en Vault y se recuperan de Vault.
- **D2:** mTLS, un cert de cliente por componente. La CA se hace en mi portátil (`~/argus-pki`, `scripts/etcd_ha/d312_pki.sh`: modos `init`, `reemitir etcd|vault`, `cliente ROL [INSTANCIA]`). Jenkins orquestará más adelante.
- **D3:** PR1 nodo único; PR2 HA Raft.
- **D4:** el HA real necesita otras VMs; el etcd-server sale del defender.

**Vault:**
- **V1:** Vault en modo servidor ya. Desellado opción c (clave en disco) solo para el lab: «Seguimos pensando que esto es una herramienta aún no sellada para producción».
- **V2:** Vault sale del defender y va con las VMs nuevas. Topología del PR2 por decidir **con RAM medida**: el Mac tiene 32 GiB y unos 17,4 GB ya están asignados a VMs; cada Debian adicional cuesta 600 MB o más.
- **V3:** en este PR solo las claves HMAC van al Vault servidor; el resto de secretos, en un PR posterior (DEBT-VAULT-REST-SECRETS-001).
- **Camino a:** el Vault dev se queda en el defender, solo en loopback.

**Identidad y despliegue:**
- **P1–P4:** VM `etcd` en 192.168.100.20; PKI en `~/argus-pki`; el converter tiene su propio cert; nombre de clave = CN.
- **Identidad:** CN = instancia, OU = rol; una clave HMAC por instancia (réplicas en HA).
- **Q1:** sin compilador en la VM nueva (BSR): se compila en el defender y se despliega solo el runtime. Algún día habrá que quitar también el compilador del defender.
- **Q2:** la semilla y el material van del defender a la VM etcd por ssh encadenado (`ssh -F <(vagrant ssh-config) -T`), nunca por el disco del Mac ni por /vagrant. «No nos compliquemos en exceso.»

**Binarios:**
- etcd: binario oficial actualizado, «igual que con kuzu» (v3.6.16, sha256 fijado; el 3.4.23 de Debian está EOL).
- Vault: «instala vault de la misma manera que esté en el Vagrantfile… deterministas en el EMECAS» → `VAULT_INSTALL` única, 2.2.1-1.

**4b:**
- **B1=a:** cliente Vault propio y pequeño sobre `httplib::SSLClient` («más sencilla y con menor exposición al ataque»).
- **B2:** «Json es la ley. Se lee del JSON, si no está o trae errores… se avisa y se aplica el valor por defecto.»
- **B3:** «Recuerda el modo HA que requiere algo más que el CN» → la identidad es el par (OU rol, CN instancia):
  - registro, latido y claves por instancia;
  - permisos para todo el rol vía OU;
  - las fachadas etcd-server comparten estado en etcd.
- **B4:** la clave del firewall va a `/secrets/firewall-acl-agent`.

## Estado de la VM etcd (medido)

**Red y tiempo:**
- nftables con policy drop. Solo deja pasar lo, establecidas, ICMP, ssh y 2379 desde 192.168.100.1.
- chrony sincroniza contra el defender.

**Vault 2.2.1 servidor:**
- raft en `/opt/vault/data`; listener `127.0.0.1:8200` con `tls_require_and_verify_client_cert`.
- KV v2 en `argus-hmac`, con política create/read/update y sin delete.
- cert auth para CN=etcd-server; token root revocado.
- Desellado con la unidad systemd `argus-vault-unseal` (clave `/etc/vault.d/unseal.key` por stdin vía la API HTTP).
- Sin usar: el cert autofirmado de `/opt/vault/tls` (se puede quitar).

**etcd 3.6.16:**
- `127.0.0.1:2381` para clientes y `:2382` para peers, con client-cert-auth.
- RBAC por CN: usuario `etcd-server` con rol `argus-rw` readwrite sobre el prefijo `/argus/`; usuario root sin password, y nunca se emite un cert CN=root.

**Hechos medidos de etcd:**
- La pasarela JSON de etcd rechaza toda petición con cert de cliente («CommonName… will be ignored»). Por eso la fachada usa **gRPC** con etcd-cpp-apiv3 v0.15.3: `SyncClient(url, ca, cert, privkey, target_name_override)`, multi-endpoint separado por comas.
- `libetcd-cpp-api` solo depende de paquetes Debian (grpc++ 1.51, protobuf 32, cpprest 2.10, abseil).

**etcd-server 4a:** desplegado con `d312_etcd_vm_deploy.sh`, que copia binario + libs de /usr/local/lib con manifiesto sha256, paquetes vía `dpkg -S`, material de `/etc/ml-defender/etcd-server` y `/run/argus` vía tmpfiles.d.

## Lo que falta (en orden)

1. **4b.2 — HTTPS con mTLS y autorización:**
   - `httplib::SSLServer` con verificación del cert de cliente.
   - Tabla de autorización en el JSON por (OU, CN), aplicada con `set_pre_routing_handler`; un 403 con `[ETCD-AUTHZ-DENEGADO]`.
   - Registrar el status real (hoy `/v1/heartbeat` loguea 200 antes de decidir).
   - Borrar `/seed` y `/secrets/keys`.
   - Arreglar el resumen de `[CONFIG-DEFAULT]` (ruta real).
   - Rutas actuales: /register, /unregister, /components, /seed, /validate, /config, /v1/config, /v1/heartbeat, /v1/epoch (GET/PUT, sin auth), /health, /info, /secrets/keys, /secrets/{c}, /secrets/rotate/{c}, /secrets/valid/{c}.
2. **4b.3 — `IRegistryStore` con `EtcdRegistryStore` sobre gRPC**, bajo el prefijo `/argus/`:
   - claves de registro, config, latido y época;
   - registro rechazado con 403 si el nombre ≠ CN;
   - ComponentRegistry no tiene mutex sobre `components_` (arreglarlo o quitarlo al pasar a etcd).
3. **4b.4 — cliente Vault KV v2** (httplib SSLClient, login por cert):
   - ventana de dos: `argus-hmac/<CN>/<huella8>` y `argus-hmac/<CN>/ventana`;
   - get-or-create con un único cerrojo;
   - caché más `[ETCD-VAULT-NO-DISPONIBLE]`;
   - los logs solo llevan huellas.
4. **4b.6 — borrar código muerto:**
   - `auto_restart`/`system()` y los campos `max_restart_attempts_`/`restart_delay_seconds_`/`auto_restart_enabled_` de ComponentRegistry;
   - métodos deprecados del registro, variantes muertas de etcd-client y bloques de test comentados en CMake;
   - para B4: git grep de quién verifica el CSV del firewall con `/secrets/firewall` antes de renombrar.
5. **Paso 5:**
   - `libetcd_client` con certs de cliente TLS;
   - los JSON de los componentes apuntan a 192.168.100.20;
   - los scripts del lab (mitre_start, ctu_start, custom_start) usan el cert admin.
6. **Paso 6:** quitar el etcd-server del defender.
7. **Paso 7:** adaptar el instrumento de reinicio de DAY311 (`scripts/bronze_key/d311_reinicio_etcd.sh` + `d311_etcd_defender.sh`).
8. **Paso 8:** EMECAS+++.
9. **Después:** PR2 HA Raft (decidir la topología con la RAM medida).

## Deudas anotadas

- DEBT-VAULT-REST-SECRETS-001: resto de secretos a Vault.
- DEBT-VAULT-DEV-EXPOSED-001: cerrada para el Vault dev.
- `tools/prod/collect-libs.sh` lista libsodium.so.26 (el binario necesita .so.23) y le falta libcrypto_provider.
- Los nombres de instancia están fijos en main.cpp (`"etcd-server"` en CryptoProvider, AutonomyPublisher y el registrador). En HA deben salir del JSON: siguiente rama.
- `crypto_cfg.component_config_path` sigue fijo a `/etc/ml-defender/etcd-server/`.
- `build-vault-production` (tarea del Makefile, línea ~1555, Acto I del Vault dev) no lo recompila `pipeline-build`, y puede quedarse viejo.
- El hostname del defender es `bookworm` (no hay `vm.hostname`).
- Falta `scripts/timebase/__pycache__` en `.gitignore`.
- Quitar el compilador del defender (algún día).
- Aviso de simple-token de etcd: solo aplica con auth por password.

## Reglas de trabajo (las de siempre, y lo aprendido en DAY312)

**Medir y predecir:**
- Medir, no votar. Predicción escrita antes de medir; si algo no da lo esperado, **parar**.
- Ventanas de medida de 600–900 s con marcas UTC y control positivo; un resultado vacío no prueba nada (control negativo).

**Parcheadores:**
- Validan todo antes de escribir nada: sha256 de partida y final, anclas únicas, «ya aplicado», `--check`/`--apply`.
- Se prueban en una copia desechable del repo **con el directorio de trabajo de Claude apartado** (DAY312: uno leía un fichero de `/home/claude/work` y en el Mac reventó sin escribir).
- Los de un solo uso no se commitean; los instrumentos sí.

**Entregas y comandos:**
- **Enviar los ficheros con SendUserFile ANTES de describirlos** (dos veces se me olvidó).
- Comandos exactos y completos, uno por bloque, diciendo dónde se ejecuta cada uno (Mac / defender / client / etcd).
- Nada de huecos tipo `BIN` dentro de comillas: zsh rompe con `rc=\$?`. Escribir la ruta real.
- Al copiar comandos le aparecen caracteres de más (`.txtt`, `2>&11`): cada `cat` en su propia línea.
- `git grep`, nunca `grep -rn` desde la raíz. awk con `LC_ALL=C`.
- Para transferir por ssh: `ssh -F <(vagrant ssh-config) -T` (`vagrant ssh --no-tty` sí asigna TTY y rompe el tar). Con sudo, `sudo DEBIAN_FRONTEND=noninteractive apt-get`.
- Nunca poner un secreto en el argv de un comando de prueba (ni en un grep que lo busque).

**Compilar y documentar:**
- Tras un cambio, compilación completa: `make pipeline-build PROFILE=production` y `make test-components PROFILE=production`, revisando las 5 líneas del resumen y el ctest del etcd-server (ahora 4).
- El binario a probar es `/vagrant/etcd-server/build-production/etcd-server`.
- Nunca alterar la historia de git. El código deprecado se borra.
- El repo es de solo lectura para Claude: los commits los hago yo.
- Las secciones del doc escritas antes de medir no se reescriben; los resultados van en una sección aparte.

## Primer paso de DAY313

Leer `docs/ml-heads/day312_diseno.md` (diseño de 4b) y `etcd-server/src/etcd_server.cpp`. Después, proponer 4b.2 (HTTPS con mTLS y autorización por (OU, CN)) con sus predicciones, y entregarlo como parcheador probado.
