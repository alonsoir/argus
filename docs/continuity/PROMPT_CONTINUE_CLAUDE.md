# aRGus NDR — prompt de continuidad DAY327 (sigue de DAY326)

Responde siempre en español. Alonso es el único desarrollador de aRGus NDR (C++20, NDR para infraestructura crítica,
arXiv:2604.04952). Principio: «medir, no votar». El repo es SOLO LECTURA para Claude: Alonso hace commits, push y PR.

## Dónde estamos
- Rama: `feat/etcd-ha-plano-control` (PR2b de **DEBT-ETCD-HA-TLS-RAFT-001**, ADR-048). F2 (DEBT-FALCO-RUIDO-ADMIN-001)
  casi cerrado: falta el test de silencio en EMECAS.
- Commits de DAY326 (sábado 14-nov), todos subidos al cerrar el día:
    - `f409059ca` **F2a** `argus-infra clave-publica` (clave pública del manifiesto con el cliente de Vault de la propia
      herramienta; 25 tests); se borra `protegidos_pubkey_vm.sh` (curl). Huella `a1b73e22cf85899a` la misma.
    - `1ac905740` **F2b** reglas de Falco: `iptables-restore` del firewall permitido por su nombre CORTADO
      (`iptables-restor`: el kernel corta proc.name a 15) y argus-infra con sudo leyendo su clave = Notice.
    - `b6c8dcfe7` saca `scripts/local_checks.sh` (entró vacío por error en 1ac905740). El prototipo de Alonso está en la
      rama `proto/local-checks` (`ea6c79a33`), para trabajarlo más adelante.
    - `151109ec4` **F2c** `etcd-vm-deploy` sin CRITICAL: `tar` con sudo (solo la orden exacta del script) y `sha256sum`
      hijo de sudo sobre semilla y private.pem del etcd-server = Notice; `d312` usa `sudo sha256sum $(sudo find …)`.
    - `51f4ebd29` **F2d** `scripts/bronze_key/clave_bronce.py` (clave HMAC activa por mTLS con la identidad del conversor,
      Python estándar; 8 tests, `make test-clave-bronce`, paso en emecas). La usan mitre/ctu/custom-start y las claves
      A y B de `d317_reinicio_defender.sh`. Se borra `clave_bronce_ml_detector.sh`.
    - **F2e** `[DESELLADO-PY-D326]` desellado del Vault del lab en Python estándar (`provisioning/vault/argus-vault-unseal`;
      8 tests, `make test-vault-unseal`, paso en emecas). Falco vigila `/etc/vault.d/unseal.key` y reconoce al desellado
      por binario + `proc.args` + fichero, no por el árbol de procesos.
    - Documentación: BACKLOG (DAY325 y DAY326) y este prompt.
- Sin trackear en `scripts/etcd_ha/` (aplicados; se archivan tras el EMECAS): los 9 `d324_*`, `d325_f1_reinicio.py`,
  `d325_f1_escritor.py`, `d325_nombre_viejo.py`, y de DAY326: `d326_f2a_clave_publica.py` (sha256 `0584b4f5…a34b`),
  `d326_f2b_reglas_falco.py` (`a8c610af…231c`), `d326_f2c_despliegue_falco.py` (`3f481f5b…a292`),
  `d326_f2d_clave_bronce.py` (`fa2ff1cc…5e84`), `d326_f2e_desellado.py` (`b2aea248…13e3`) y dos instrumentos de medida:
  `d326_falco_resumen.py`, `d326_falco_grupos.py` (agrupa eventos.json por regla/proceso/padre/fichero; útil).
- Lab al cerrar: todo parado (`make pipeline-stop`, `vagrant halt`). etcd 3/3 SANO; Vault desellado y vigilado.

## Medido DAY326
- **`make lab-e2e LAB_E2E_DIA=day326` entero en VERDE** (04:55-06:42Z, Mac a carga ~6): reinicios antes/ordenada/kill9,
  protegidos P1-P6, mitigación C1-C7, vigía, antispoof S1-S4, latido L0-L4, vigilancia C1-C8 (C8: 16 trazas ≤ 60, C7:
  Vault arranca y se dessella solo) y reinicio del etcd-server. Las dudas escritas de DAY325 quedan medidas.
- Paso 0: con el Mac tranquilo, término etcd estable entre dos `etcd-vm-check` (265 y 265).
- Falco durante lab-e2e: las CRITICAL salían de cuatro sitios que no eran C5 (argus-infra con sudo, curl del desellado al
  arrancar, curl de las claves A/B, iptables-restore). Todos arreglados y probados con su prueba que debe fallar.
- Falco en control-2/3 activo y con nuestras reglas (probado: `sudo head -c 0 /etc/etcd/tls/etcd.key` = 1 CRITICAL).
- Desellado: la CRITICAL de las 04:47Z (padre=<NA>) fue la carrera del arranque: Falco abrió la fuente 1,7 s antes y aún
  no conocía al proceso. Con F2e, `vagrant reload control-1` (margen 2,6 s) y un reinicio de Vault: 0 eventos del
  desellado. Un margen menor de 2 s no se ha visto aún con la regla nueva (la regla ya no depende del padre).

## Lo siguiente, en este orden
1. **Test de silencio en EMECAS** (último trozo de F2): un paso justo antes de `lab-e2e` que exija 0 CRITICAL `argus_*`
   en defender y control-1..3 desde que se crean las VMs (C5 de vigilancia las provoca a propósito: va después).
   Ojo (medido DAY326): en una VM recién creada la carrera del desellado no aparece (Falco ya corre cuando se dessella);
   la que importa es la de una VM que ya existía, y esa la cubre F2e.
2. **Documentación** (decisión de Alonso DAY326): en ADR-060 sección 7 y en el procedimiento de desellado de
   DEBT-VAULT-SELLADO-ALERTA-001, las recomendaciones al admin sobre la clave de desellado en producción: Shamir con
   `-pgp-keys` y la clave PGP privada en YubiKey (umbral 1 por la realidad de las guardias), HSM (solo Vault Enterprise),
   KMS de nube (confianza en el proveedor, depende de Internet), transit desde el Vault de la VM admin; nunca en claro en
   disco. Comprobar contra la documentación de Vault 2.2.1 antes de escribirlo como norma.
   Además ADR-048 (DAY324-326) y ADR-060 (argus-disco con `rutas`, el suelo tras rehacer Vault, `clave-publica`,
   desellado en Python y `unseal.key` vigilada).
3. **Decisiones pendientes de Alonso:**
    - Suelo del manifiesto tras rehacer Vault: (a) paso manual del runbook, o (b) el firewall ata el suelo a la huella de
      la clave compilada (toca ADR-060). Medir si el etcd-server tiene un estado equivalente.
    - **Decidido (DAY325): comprobación de recursos del anfitrión al empezar lab-e2e y EMECAS**, sin arrancar si falta.
      Datos para los umbrales: Mac ahogado (DAY325) carga 46, swap 5,3/6,1 GB → lab-e2e rojo; DAY326 carga ~6 durante
      lab-e2e y 4,65 recién arrancado (CLion indexando) → verde; swap 0; 170 GB libres.
    - `test-etcd-reinicio`: ¿entra en lab-e2e/EMECAS? ¿`test-etcd-cluster` en EMECAS?
4. **EMECAS desde cero** (primera vez con 3 nodos): verde y en silencio de Falco. Incluye los pasos nuevos
   `test-clave-bronce` y `test-vault-unseal`, y por primera vez `mitre-start`/`ctu-start` con `clave_bronce.py`.
   Luego archivar los parcheadores (`d324_*`, `d325_*`, `d326_*`) con un tag/rama en el remoto, borrarlos del Mac, push,
   PR, merge. **Después, PR2c** (Vault en clúster Raft; se borran `disco-sin-vault.json` y `VIGILANCIA_DISCO_JSON`).
5. Borrar (decidido DAY325, commit propio): `d321_medir_falco.sh`, `d321_medir_falco_hijos.sh`, `d321_medir_vigilancia.sh`,
   `d321_comprobar_sensores.sh`; corregir el comentario de `provisioning/falco/argus_lab.yaml` que cita uno de ellos.
   En el defender, borrar `/var/lib/ml-defender/firewall-linaje-anterior/` cuando se decida lo del suelo.

## Lecciones medidas DAY326
- Antes de dar por buena la cola de un log, sacar el veredicto de CADA E2E (`grep`): el PASA global no enseña C7/C8.
- **El kernel corta proc.name a 15 caracteres**: `iptables-restore` es `iptables-restor`. Regla: por ruta y por
  `proc.args`, nunca por nombre (el propio argus_lab.yaml lo advertía y aun así se coló).
- Las CRITICAL de `iptables-restor` no salen al arrancar el pipeline sino cuando el firewall reescribe reglas (mitigación,
  vigía, antispoof): para probar la regla hay que lanzar `lab-e2e-vigia`, no `pipeline-start`.
- **GNU tar no lee los ficheros si la salida es /dev/null** (`-f /dev/null` o `> /dev/null`): una prueba que debe fallar
  con tar tiene que sacar por tubería (`| wc -c`).
- `sudo wc -l < fichero` falla: la redirección la hace la shell sin privilegios. Usar `sudo sh -c 'wc -l < fichero'`.
- `vagrant ssh -c` devuelve líneas con `\r` (lo que sale de dentro de la VM; el aviso de port-check no). `cat -A` no
  existe en macOS: `cat -vet`.
- Marcas de Falco: el `tail` empieza en la marca MÁS UNO, y cada VM tiene la suya. Mejor: comandos que hacen su propia
  marca dentro de la VM, o que Claude dé el número ya puesto.
- Falco tarda ~2 s desde «Opening 'syscall' source» en conocer a los procesos nuevos: una regla que dependa del padre o
  del abuelo falla en el arranque. Reconocer por binario + argumentos + fichero.
- La clave de desellado del lab (`/etc/vault.d/unseal.key`) no estaba vigilada; ahora sí, con un solo dueño.
- `vault operator unseal` solo acepta la clave como argumento (visible en el proceso) o por el aviso interactivo.
- Hipótesis de Claude que los datos tumbaron hoy: «todas las CRITICAL saldrán de C5»; «las claves de control-2 están fuera
  de la lista vigilada» (estaban dentro); «el problema del desellado es curl» (era la carrera); «`-f /dev/null` hace leer a
  tar»; «el `65` sale con `grep -x`» (`\r`).

## Datos útiles
- Nodos: control-1 `192.168.100.20`, control-2 `.21`, control-3 `.22`; 1024 MB, 2 vCPU. etcd 3.6.16 (cliente 2381,
  peers 2382, mTLS, RBAC por CN). Vault 2.2.1 (solo en control-1). Clave transit: huella `a1b73e22cf85899a`.
- Falco: `provisioning/falco/argus_lab.yaml`; se lleva a las VMs con `vagrant provision <vm> --provision-with falco`
  (`falco --dry-run` dentro). Macros de administración (Notice): etcdctl/curl con sudo (etcd-server.key), openssl desde
  bash (private.pem), argus-infra, `argus_lab_despliegue_etcd_server`, `argus_lab_clave_bronce`. Dueño del desellado:
  `argus_lab_es_desellado`. Wazuh: 100551 (Critical), 100552 (Warning), 100553 (Notice), por prioridad.
- Targets nuevos: `test-clave-bronce` (defender), `test-vault-unseal` (control-1). Los de siempre: `etcd-cluster-deploy`,
  `etcd-vm-deploy`, `test-etcd-cluster`, `test-etcd-reinicio`, `test-plano-control`, `etcd-vm-check`, `protegidos-pubkey`,
  `protegidos-bootstrap`, `test-argus-infra`, `lab-e2e` y sus `lab-e2e-*` (vigía ~5 min, reinicio-etcd ~10 min).
- Orden de `lab-e2e`: reinicio antes/ordenada/kill9, protegidos, mitigación, vigía, antispoof, latido, vigilancia,
  pipeline-start, reinicio del etcd-server. ~105 min.

## Forma de trabajar (siguen en vigor)
- Predicción escrita antes de cada medida; si no sale, parar y mirar. Tests que también prueban que fallan cuando
  deben (y que la herramienta no se salte la prueba). Complejidad lineal como mucho. El JSON es la ley.
- Parcheadores: sha256 de partida, cada ancla las veces exactas, nada escrito si algo falla; se copian a
  `scripts/etcd_ha/` y se ejecutan desde ahí, con su sha256. Lo que lleve tabuladores, por parcheador.
- Comandos exactos, en orden, diciendo dónde se ejecutan; salida a `/tmp/…` y `; cat`; no encadenar salidas grandes.
  `git grep`, nunca `grep -rn .` en la raíz. Un commit por cambio lógico, con el mensaje propuesto y `git status`
  antes del `git add` (DAY326 se coló un fichero ajeno). Nunca reescribir la historia. Software de terceros solo de sus
  mantenedores. Sin usos nuevos de curl.
- Claves privadas nunca en el repo ni por /vagrant.
