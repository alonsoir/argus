# ADR-060 — Manifiesto firmado de rangos protegidos, uno por hospital

| Campo | Valor |
|---|---|
| **ADR** | 060 |
| **Fecha** | 2026-11-04 (DAY 317) |
| **Estado** | Aceptado (decisiones de Alonso DAY317; diseño fino cerrado DAY318, sección 6) |
| **Decisión final** | Alonso |
| **Rama / PR** | `feat/etcd-mtls-vault`, PR1 de DEBT-ETCD-HA-TLS-RAFT-001 (pasos 8e.1–8e.5) |
| **Deuda** | DEBT-FW-MANIFIESTO-PROTEGIDOS-001 |
| **Relaciona** | ADR-025 (firma Ed25519 de plugins: clave privada fuera del host, pública compilada), ADR-024 (topología de despliegue), ADR-048 (etcd HA), DAY300 (DEBT-FW-PROTECTED-RANGES-001), DAY301 (mitigación B1 y whitelist), RECIDIVISM-D276 |

---

## 1. Contexto: lo que midió EMECAS+++ el DAY317

`make emecas+++ PROFILE=production` (2 h 20 min) cayó en `lab-e2e-protegidos`. Todo lo anterior pasó (los tres
reinicios R1–R3, P1, P3, P4, P5). El fallo:

```
[VEREDICTO] FALLA P2 episodio: FIN=1 (esperado 1), origenes=192.168.100.50:10780,192.168.100.20:3
[SOMBRA-DDOS] FIN victima=192.168.100.1 proto=17 ... duracion_s=207 eventos_drop=10783 ...
```

- 192.168.100.20 es la VM etcd (etcd, etcd-server, Vault). Desde el paso 8c, EMECAS levanta todas las VMs, así que
  por primera vez el plano de control está en la red que vigila el sniffer durante `lab-e2e`.
- El episodio es UDP. El HTTPS del etcd-server (TCP) es normal: register, config, secrets y latidos cada 30 s, todos 200.
- Medido: la VM etcd sincroniza con chrony contra el defender (`server 192.168.100.1 iburst`, `Poll 6` = 64 s). Un
  `tcpdump` mostró `192.168.100.20.<p> > 192.168.100.1.123: NTPv4, Client, length 48` cada ~64 s. El episodio duró
  207 s: 207 / 64 = 3,2, es decir, **las 3 peticiones NTP de cliente** que `ddos_v2` marcó junto con la reflexión NTP.

**Consecuencia (el DoS autoinfligido).** Hoy no pasa nada porque la mitigación está en sombra (`dry_run=true`,
`ddos_mitigacion.habilitada=false`). Con la mitigación real, `ddos_mitigacion` mete en el ipset blacklist **la IP de
origen entera** con `min_drops_origen=1` y primer escalón de 3600 s: el primer DDoS NTP contra el defender habría
bloqueado una hora a la VM etcd y, con ella, el HTTPS del etcd-server, es decir, el plano de control completo
(registro, latidos, configuración, claves) justo durante el ataque. P2 hizo su trabajo: no se relaja.

**Lo que hay hoy y por qué no basta.**
- `ddos_protegidos` (DAY300) en `firewall.json`: listas `dmz`, `intranet`, `externos_criticos`. Un DROP de la cabeza
  DDoS con origen protegido se registra como `ALERTA_PROTEGIDO` y no cuenta para el episodio.
- `[ARGUS-WHITELIST-D301]`: el ipset `ml_defender_whitelist` (hash:net) refleja exactamente esos rangos, y la cadena de
  iptables hace `--match-set <whitelist> src ... RETURN` antes del blacklist. **Medido en `iptables_wrapper.cpp`: un
  origen protegido queda exento de TODO bloqueo de aRGus, no solo del de la cabeza DDoS.** Quien escribe en esa lista
  da inmunidad completa.
- Las listas viven en cada `firewall.json`. Con N firewalls en un despliegue (uno por planta) hay N copias de la verdad,
  que pueden contradecirse (¿cuál vale, la de la planta 3 o la de la 4?). El fichero se sube además al etcd
  (`config subida`), otro camino de escritura.
- Si no queda ningún rango válido, DAY300 protege por defecto RFC 1918 y fc00::/7 como intranet: rangos amplísimos.
- Medido: el resumen `protegidos:` cuenta por categoría y las líneas `ALERTA_PROTEGIDO` tienen tope
  (`anomalias_detalle_max`, rango [0, 1000], lab 10). Meter .20 en `intranet` impediría separar sus alertas de las de
  .61 y el veredicto estricto no se podría escribir sin trampas.

## 2. Decisión

**D1. Un manifiesto por hospital, en un solo sitio.** Todas las listas protegidas salen de un único manifiesto
firmado por hospital, con sus plantas dentro (DAY318, sección 6), con cuatro categorías: `infraestructura` (nueva: el plano de control de aRGus, etcd,
etcd-server, Vault), `intranet`, `dmz`, `externos_criticos`. `ddos_protegidos` desaparece de `firewall.json` (lo
deprecado se borra). Las categorías se mantienen separadas para contar y para aplicar a cada una su política.

**D2. Entradas estrechas.** Cada entrada: `{cidr, interfaz, mac?, motivo}`.
- `interfaz` obligatoria: un paquete con origen protegido que llega por otra interfaz es falso por construcción: no
  recibe la exención del kernel, se descarta en `raw PREROUTING` (antispoofing, D8, 8e.4) y dispara la alerta de
  spoofing (vale aunque haya routers por medio). Precisión DAY318: la barrera de usuario (suscriptor y
  `BatchProcessor`) protege por IP siempre, venga por donde venga; si no, falsificar el origen de un protegido
  bastaría para que aRGus lo bloqueara, que es el DoS que este ADR evita. Un host con varias interfaces legítimas
  lleva una entrada por interfaz.
- `mac` opcional, cuando el host está en el mismo segmento L2 que el firewall; una IP protegida con otra MAC es alerta
  de spoofing. (Más allá de un router la MAC que se ve es la del router: por eso es opcional.)
- La plantilla de despliegue fija **el prefijo más amplio permitido por categoría**. `infraestructura`: solo /32 y
  /128, sin excepción. Las demás: el límite que diga la plantilla (p. ej. /24). Un manifiesto que lo supera no se
  firma (`argus-infra` lo rechaza antes de ir a Vault) y el firewall tampoco lo aplicaría.

**D3. Firma asimétrica, clave por hospital.**
- Ed25519, no HMAC: con HMAC el verificador tendría el secreto y un malware en el defender podría firmar.
- Clave privada en **Vault transit**, no exportable, una por **hospital**: el límite de daño coincide con el límite de
  confianza (las plantas de un hospital comparten administración). Lo que separa las plantas es su sección dentro
  del manifiesto (`plantas.<despliegue_id>`). Descartadas: una por planta (más imágenes sin más seguridad real) y una para todos los hospitales
  (comprometerla los expone a todos).
- Clave pública **compilada en el firewall-acl-agent** (patrón ADR-025), inyectada por Jenkins en la compilación de la
  imagen del hospital. No es un fichero que se pueda cambiar: para cambiarla hay que cambiar el binario, que vigilan
  Falco y la verificación de la imagen. Dos ranuras compiladas (actual y siguiente) para rotar sin dejar a los
  firewalls sin poder verificar mientras llega la imagen nueva. El agente prueba las dos; el sobre no dice cuál
  (DAY318).

**D4. Contra la reproducción y el deshacer sin firma.**
- `version` entera que solo crece. El firewall rechaza toda versión ≤ la última aplicada; el etcd-server también.
- Deshacer = volver a aplicar el contenido de una versión anterior **como versión nueva firmada**. Nunca un botón sin
  firma (sería la puerta trasera perfecta). Quitar una entrada también es peligroso: si se quita el etcd vuelve el DoS
  autoinfligido.

**D5. Flujo distribuido.**
1. Admin, en su máquina (la que fija la plantilla de despliegue) y desde el CIDR autorizado:
   `argus-infra add|del|list|diff|deshacer|verificar ...`. La herramienta pide el manifiesto actual, construye la
   versión N+1, comprueba los límites de D2 y la manda a firmar a Vault transit **con la identidad del propio admin**.
   Vault solo acepta desde el CIDR autorizado (`token_bound_cidrs`) y lo registra en su audit device: quién, cuándo,
   desde qué IP.
2. Publica con `PUT` al etcd-server por mTLS con certificado de admin. El etcd-server verifica la firma, el
   `hospital_id` y la versión antes de guardarlo en etcd (defensa en profundidad; la autenticidad sale de la firma,
   no del transporte).
3. Cada firewall-acl-agent del despliegue lo recoge con su etcd-client. Verifica firma (clave compilada), versión >
   última aplicada, `hospital_id` propio, que esté su planta y límites. Si cuadra, aplica de forma atómica, registra `[INFRA-CAMBIO]`
   (firmante, fecha, versión anterior y nueva, diferencias) y lanza la alerta nuclear de cambio.
4. Cada firewall informa en su latido de la versión aplicada. `pipeline-status` y la futura consola muestran qué
   firewall va desfasado.
5. Cada firewall guarda en disco el último manifiesto verificado para arrancar sin etcd. Como va firmado, si alguien
   lo toca la firma no cuadra: se descubre y se avisa periódicamente.

Solo lo consumen los firewalls. Sniffer, ml-detector y RAG no lo ven.

**D6. Candado.** `ddos_mitigacion.habilitada=true` solo surte efecto con un manifiesto verificado. Sin él, el agente
sigue en sombra y lo avisa periódicamente. El JSON es la ley, pero esta llave no la abre un fichero solo.

**D7. Fallo en caliente.** Si un manifiesto nuevo no verifica, o el de disco deja de verificar, el agente se queda con
**el último conjunto verificado en memoria** y avisa **periódicamente**, hasta que el admin vuelve a firmar. El aviso
no puede ser una gota en el océano.

**D8. Vigilancia "como halcones".**
- Comprobación continua: cada N s (en el JSON, con rango y defecto) el agente compara el ipset del kernel con el
  manifiesto. Cualquier diferencia es alarma y la entrada no firmada pierde la protección.
- Spoofing por interfaz o MAC (D2): alerta nuclear y descarte en `raw PREROUTING` generado desde el manifiesto: una
  regla por entrada (origen protegido que no entra por su interfaz = DROP), con contador por regla, resumen
  periódico y muestra de los primeros paquetes como evidencia. Postura de partida (Alonso DAY318): agresiva y con
  todo registrado; si resulta demasiado dura, se mide y se suaviza.
- Host (Falco): toda operación sobre el set protegido que no venga del agente, y toda escritura en el manifiesto en
  disco o en el binario del agente.
- Wazuh: FIM del manifiesto en disco.
- Vault: audit device con la identidad y la IP de cada firma.
- Falco y Wazuh reportan a la máquina del admin, que concentra la consola, el etcd-server del despliegue y la
  vigilancia.

**D9. La herramienta.** `argus-infra` se instala solo en la máquina del admin, nunca en un componente. Puede ser
código abierto como el resto de aRGus: la seguridad sale de la clave y de la vigilancia, no de ocultar el código
(Kerckhoffs).

**D9 bis. Dos roles de administración, separados a propósito (DAY318).**
- `admin` (certificado OU=admin): operación diaria en el etcd-server (rotar claves HMAC, listar componentes,
  `/info`). No puede firmar el manifiesto.
- `argus-infra` (certificado OU=argus-infra; rol de Vault `argus-infra-admin`): solo firma, verifica y lee la clave
  pública del manifiesto de su hospital, y solo publica el manifiesto en el etcd-server. Firmar da inmunidad frente a
  todo bloqueo de aRGus: si se compromete el certificado de uso diario, el manifiesto sigue a salvo.
- Medido DAY318 (banco y lab): `argus-infra` recibe 403 al leer `argus-hmac`, rotar, exportar o reconfigurar su
  clave y firmar con otra; `etcd-server` recibe 403 al firmar. Token de `argus-infra`: 300 s, atado a 127.0.0.1.

**D10. Plantilla de despliegue.** Un fichero de despliegue, generado por Jenkins desde una plantilla certificada por
nosotros, fija: máquina admin, CIDR autorizado, `hospital_id`, las plantas (`despliegue_id`), límites de prefijo por categoría. Solo
desde ahí se pueden firmar cambios. Controlar Jenkins y sus plantillas es imprescindible (siempre lo ha sido).

**D11. Laboratorio.**
- `argus-infra` vive en la VM etcd (no hay RAM para una VM admin). Vault escucha en 127.0.0.1, así que la VM etcd hace
  de máquina admin. Es una simplificación de desarrollo: escrita en el `_doc` y en el BACKLOG.
- Un fichero de despliegue de laboratorio en el repo, con la misma estructura que tendrá la plantilla.
- El bootstrap aprovisiona con la propia herramienta: `192.168.100.20/32` en `infraestructura` (interfaz del defender
  hacia la LAN) y `192.168.100.61/32` en `intranet` (el protegido de prueba de DAY300). EMECAS prueba el camino real.
- Cada EMECAS destruye las VMs: la clave transit se genera de nuevo y la clave pública se inyecta en la compilación
  del firewall. Claves nuevas en cada EMECAS: correcto y determinista.

## 3. Consecuencias

**Veredicto de `lab-e2e-protegidos`, más estricto.**
- P2: un FIN y `origenes=` solo `192.168.100.50` (sin cambios).
- P3: `intranet` = alertas de .61; `dmz` = `externos_criticos` = 0.
- P4: DROP_resumenes = DROP_FIN + alertas (intranet + infraestructura) + aislados + pendientes.
- P5: volumen de `intranet` en [98 %, 100 %] de los paquetes de .61.
- P6 (nuevo): `infraestructura` ≥ 0; .20 no aparece nunca en `origenes=` de INICIO ni de FIN; sus alertas, si las hay,
  son `categoria=infraestructura`.
- P1 cambia: la configuración de rangos ya no sale del JSON, sino del manifiesto verificado (versión, firmante).

**Lo que este ADR no resuelve (escrito para no olvidarlo).**
- Root comprometido en el defender por una vulnerabilidad del kernel lo derrota todo (puede cambiar el binario). Lo
  que se consigue es que no pueda hacerlo en silencio. Contra eso: imágenes con los parches de seguridad del kernel
  siempre al día desde Jenkins.
- Proteger .20 implica que aRGus nunca bloquea la IP .20, aunque llegue tráfico falsificado con ese origen. Si entra
  por otra interfaz lo descarta el antispoofing (D2, D8); desde el mismo segmento solo lo frena la MAC, cuando la
  entrada la lleva. Falsificar orígenes ajenos con herramientas de fabricación o manipulación de paquetes (Scapy,
  hping3, Polymorph) no se resuelve desde el borde del hospital: DEBT-FW-SPOOFING-ORIGENES-AJENOS-001.
- El falso positivo de `ddos_v2` con un cliente NTP de 48 bytes es un defecto del modelo: DEBT-DDOS-V2-NTP-CLIENTE-001
  (rama `diag/ml-heads`). El manifiesto evita el daño, no corrige el modelo.
- Regla de dos personas (Vault control groups): no ahora. Muchos hospitales no tendrán dos administradores. Deuda,
  con campo futuro desactivado por defecto.
- **Hipótesis (Alonso DAY317), sin medir: el DDoS autoinfligido.** En un despliegue distribuido real, el tráfico
  legítimo del propio aRGus (N componentes reconectando a la vez al etcd-server tras una caída, latidos alineados,
  muchos clientes NTP contra el mismo servidor de hora) podría parecer un DDoS contra un nodo del plano de control.
  Se mide en PR2 (3 nodos), sin adelantarse.

**Lección para EMECAS.** Sin el pipeline completo no se habría visto: con solo defender y client no existía .20 y P2
pasaba. El fallo no estaba en el código de ninguna pieza, sino en la topología. EMECAS debe levantar la topología de
producción, no un subconjunto. Y el DoS autoinfligido no solo viene de que alguien escriba en la lista: también de que
falte algo en ella.

## 4. Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Meter .20 en `intranet` de `firewall.json` | Mantiene N copias, el fichero débil y no separa las alertas (P5 no se puede escribir) |
| Relajar P2 para aceptar .20 | Esconde un DoS autoinfligido real; EMECAS hizo bien su trabajo |
| Que el sniffer no vea el tráfico del plano de control | Un ataque contra el plano de control quedaría invisible |
| HMAC o solo sha256 | El verificador tendría el secreto / integridad sin autenticidad |
| Clave en el keyring del kernel | Se pierde al reiniciar; no resuelve "que no se olvide" |
| Ocultar el código de `argus-infra` | No es un control de seguridad (Kerckhoffs) |
| Clave por planta / una para todos | Más imágenes sin más seguridad / un compromiso expone a todos los hospitales |
| Proteger la IP entera sin interfaz | Un UDP falsificado con origen protegido quedaría inmune |

## 5. Plan (dentro de PR1, un commit por cambio lógico)

Orden de los commits (DAY318): 8e.2 va antes que 8e.1, para que el firewall compile en cada commit (desde 8e.1 no
compila sin la clave pública). EMECAS se pasa al final, con todos los commits de la rama.

- **8e.2** Vault: motor transit, clave ed25519 no exportable por hospital, política `argus-infra-admin`,
  `token_bound_cidrs`, audit device. Vagrantfile y Ansible. El bootstrap trae la clave pública al defender.
- **8e.1** firewall-acl-agent, en dos commits (DAY318):
  - **8e.1a** (hecho, 3af32373c) el verificador, sin cambiar el comportamiento del agente: categoría
    `infraestructura`, manifiesto por hospital con sus plantas, verificación Ed25519 con libsodium y clave pública
    compilada en dos ranuras, versión monótona, límites de prefijo, lo vigente seguro entre hilos (D7), caché en
    disco, aviso si falta el plano de control (D-C). Tests.
  - **8e.1b** (hecho, f9076a97c) el cableado: carga desde la caché al arrancar, set `hash:net,iface` sustituido de
    forma atómica con `ipset swap` y regla `src,src`, candado (D6), barrera por IP con los rangos del vigente,
    avisos periódicos (D6, D7, D-C), contadores por categoría. Fuera `ddos_protegidos`, `ipsets.whitelist` y el
    defecto RFC 1918. Tests.
- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server. Diseño cerrado DAY318 (decisiones de Alonso
  F-A..F-I). Hecho: 8e.3a a5a41ba4 (`libs/protegidos`), 8e.3b 465e6aa4 (etcd-server), 8e.3c 91981329 (consulta del
  firewall), 8e.3d-0 a831c44b (historial en el etcd-server), 8e.3d 6b88a0c8 (`argus-infra`), 8e.3e e2f4bb79
  (fuera la familia `/kv` del etcd-client):
  - **F-A** El etcd-server verifica con la clave pública **compilada**, la misma que el firewall (patrón ADR-025;
    CMake lee el mismo `.hex`). No se le da permiso de lectura en Vault. Que REA vea la pública no importa (es
    pública, D9); cambiarla exige cambiar el binario. Consecuencia: con Vault caído no se pueden firmar versiones
    nuevas, pero verificar y proteger no depende de Vault.
  - **F-B** Un solo verificador: el de 8e.1a pasa a una librería compartida (`libs/protegidos`, jsoncpp +
    libsodium) que enlazan el firewall y el etcd-server, con modo "documento entero, sin planta" para el servidor.
  - **F-C** Un etcd-server sirve a un hospital: `protegidos.hospital_id` en su JSON (Ansible, desde
    `argus_hospital_id`). Rutas sin segmento de hospital: `GET /v1/protegidos` (`ou:firewall-acl-agent`,
    `ou:argus-infra`) y `PUT /v1/protegidos` (`ou:argus-infra`). Añadida DAY319 (G-C): `GET /v1/protegidos/v/{n}`
    (solo `ou:argus-infra`), la versión n de `protegidos/v/<N>` tal cual, sin verificar (verifica quien la pide);
    400 si n no es un decimal >= 1 sin ceros a la izquierda que quepa en 64 bits, 404 si no existe, 503 sin
    `hospital_id` o con el almacén caído. El firewall no la puede leer.
  - **F-D** En etcd, el sobre tal cual: `/argus/protegidos/vigente` y `/argus/protegidos/v/<N>` (inmutable). PUT
    rechazado si versión <= vigente, firma u hospital no cuadran o se sale de los límites.
  - **F-E** El firewall lo pide cada `protegidos.consulta_sec` ([5, 3600], 30) con un método nuevo del etcd-client.
    Nueva y verificada: kernel, caché y `[INFRA-CAMBIO]` con altas y bajas. Igual: nada. Menor: rechazo
    `motivo=version` (intento de rollback). Servidor caído o 404: sigue con lo vigente y avisa cada `aviso_sec`.
  - **F-F** Anti-rollback entre reinicios: `protegidos.version` junto a la caché (versión más alta aplicada) y
    consulta al etcd-server antes de aplicar la caché. Caché con versión menor que la del fichero: rechazo y alarma.
  - **F-G** `argus-infra`: un fichero Python con la biblioteca estándar (medido en la VM etcd: Python 3.11.2,
    OpenSSL 3.0.22), instalado por el Vagrantfile en la VM etcd. `init`, `list`, `add`, `del`, `diff`,
    `verificar`, `deshacer N` (contenido de N como N+1 firmado). Firma y verifica con Vault transit; comprueba los
    límites de D2 antes del PUT. Diseño fino DAY319 (decisiones de Alonso G-A..G-G):
    - **G-A** Configuración `/etc/argus-infra/argus-infra.json` (lab: `tools/argus-infra/argus-infra.lab.json`):
      hospital, plantas, límites, Vault, etcd-server y TLS sin defecto sano (sin ellos no firma); solo `timeout_s`
      tiene defecto ([1, 120], 10, con aviso).
    - **G-B** Plantilla sin firmar aparte (`tools/argus-infra/plantillas/hospital-lab.json`); los límites salen
      siempre de la configuración, nunca de la plantilla ni de la versión anterior.
    - **G-C** El historial se lee del etcd-server (`GET /v1/protegidos/v/{n}`, F-C), no de un archivo local: la
      verdad en un solo sitio.
    - **G-D** `firmante` = `<cn> entidad=<entity_id de Vault>`, como mucho 64 caracteres. Cambiado tras medir: el
      etcd-server y el firewall registran el firmante con `saneado()`, que corta a 64, y con el formato largo el
      entity_id se perdía.
    - **G-E** Cada cambio: login en Vault; lo vigente se valida (reglas de `libs/protegidos` portadas a Python y
      transit verify); N+1; diff; confirmación tecleando el número de versión (`--si` para el bootstrap); sign;
      verify; PUT; GET final comparado byte a byte; revoke-self del token.
    - **G-F** Órdenes `init --desde`, `list`, `add`, `del`, `diff`, `verificar` (también la cadena
      `hash_anterior`), `deshacer N`. Salidas: 0 bien, 1 error, 2 uso, 3 rechazo del etcd-server.
    - **G-G** Vive en `tools/argus-infra/`; lo instala el aprovisionador `argus-infra` de la VM etcd (run: always);
      `make test-argus-infra`.
  - **F-H** Plantilla de despliegue sin firmar en el repo (lab: `.20` infraestructura por eth2, `.61` intranet);
    `argus-infra init --desde FICHERO` la rellena y firma la versión 1 solo si no hay ninguna. El bootstrap la usa
    en 8e.5.
  - **F-I** `set/get/del/list_keys` del etcd-client piden `/kv/...`, rutas que el servidor no tiene: se borran en
    un commit propio cuando 8e.3 funcione, tras comprobar con `git grep` que nadie los usa. Hecho DAY320
    (e2f4bb79): medido que borrar solo esos 4 rompe la librería, porque otros 6 métodos suyos los llaman
    (`save_config_master`, `save_config_active`, `get_config_master`, `get_config_active`, `get_component_config`
    y `rollback_config`). Decisión de Alonso: fuera los 10; se queda `put_config` (sí funciona).
- **8e.4** Comprobación continua kernel ↔ manifiesto, antispoofing en `raw PREROUTING` generado desde el manifiesto,
  alertas de spoofing por interfaz y MAC, versión en el latido y en
  `pipeline-status`, reglas Falco (en la VM hardened-x86, `check-prod-falco`) y Wazuh. Falco y Wazuh avisan también
  cuando la partición del audit de Vault (`/var/log/vault`) pasa de un umbral (p. ej. 75 %), con prioridad en el log,
  y cuando falla uno de los dos audit devices (Alonso DAY318: es su trabajo avisarnos). Diseño fino cerrado DAY320
  (sección 7), en cuatro commits:
  - **8e.4a** (hecho, fe4c94d3) el vigía kernel ↔ manifiesto y C7 en el E2E de la mitigación real.
  - **8e.4b** (hecho, 345f8607) antispoofing por interfaz y MAC en `raw PREROUTING` (H-B a H-E, H-G; H-F pasó a 8e.4c).
  - **8e.4c** (hecho, 1818f4ec) versión del manifiesto en el latido y en `pipeline-status` (H-H) y `rp_filter`
    informado (H-F).
  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J), en
    tres commits: **8e.4d-1** (hecho, 464c733bc) el manager; **8e.4d-2** (hecho DAY321) los sensores; **8e.4d-3** el E2E.
- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.

## 6. Diseño fino de 8e.1 (cerrado DAY318)

Decisiones de Alonso DAY318 (D-A a D-I de la revisión), medidas antes de decidir donde se podía. Resumen en
`docs/BACKLOG.md`, sección `[MANIFIESTO-PROTEGIDOS-D318]`.

**Formato del manifiesto en disco y en etcd** (lo que se firma son bytes exactos, no un JSON reformateado):

```json
{
  "formato": "argus-protegidos/v1",
  "carga_b64": "<base64 de los bytes exactos de la carga>",
  "firma": "vault:v1:<base64 de la firma Ed25519 sobre esos bytes>"
}
```

Sin `ranura_clave` (D-F, menos es más): el agente verifica con la clave actual y, si no, con la siguiente, y el log
dice cuál valió. Vault transit firma Ed25519 puro sobre los bytes: basta `crypto_sign_verify_detached`.

**Carga: un manifiesto por hospital, con sus plantas dentro (D-B).**

```json
{
  "esquema": 1,
  "hospital_id": "hospital-lab",
  "version": 1,
  "emitido_utc": "2026-11-05T08:00:00Z",
  "firmante": "<cn> entidad=<entity_id de Vault> (<= 64 caracteres; G-D)",
  "motivo": "alta inicial del laboratorio",
  "hash_anterior": "<sha256 de la carga anterior, vacío en la versión 1>",
  "limites": { "infraestructura": 32, "intranet": 24, "dmz": 24, "externos_criticos": 32 },
  "comun": [],
  "plantas": {
    "lab-vagrant": [
      { "categoria": "infraestructura", "cidr": "192.168.100.20/32", "interfaz": "eth2", "mac": "", "motivo": "VM etcd: etcd, etcd-server, Vault" },
      { "categoria": "intranet", "cidr": "192.168.100.61/32", "interfaz": "eth2", "mac": "", "motivo": "protegido de prueba DAY300" }
    ]
  }
}
```

- Un documento, una firma y una versión describen el hospital entero. Nada de manifiesto de manifiestos.
- Cada firewall aplica `comun` y la sección de su planta (`protegidos.despliegue_id` de su `firewall.json`). Si su
  planta no aparece, no hay manifiesto verificado para él: candado cerrado y aviso.
- Un cambio en una planta sube la versión del hospital; los firewalls de las demás plantas la aplican y registran
  `sin cambios para esta planta`.
- Una entrada por interfaz: un host con dos interfaces legítimas lleva dos entradas.
- Solo un `motivo` corto: ni ubicación ni función de cada máquina. El manifiesto llega a todos los firewalls del
  hospital; con más detalle sería un mapa del hospital para quien tome uno. El inventario rico vive en la consola del
  admin.
- `limites` en IPv4. IPv6 (D-I): la barrera de usuario lo protege; en el kernel se omite con `[CONFIG-AVISO]` hasta
  DEBT-FW-IPV6-SETS-001.
- Interfaz del lab medida DAY318: `eth2` (192.168.100.1; la ruta a .20 sale por `eth2`).

**El set del kernel (D-A).** Medido DAY318 en el defender (`scripts/etcd_ha/d318_medir_set_iface.sh`): ipset v7.17;
`hash:net,iface` acepta `192.168.100.20/32,eth2`; `ipset test` da 0 con `eth2` y 1 con otra interfaz o con otra IP; la
regla `--match-set <set> src,src -j RETURN` entra; `ipset swap` deja el contenido nuevo. `ml_defender_whitelist`
(`hash:net`) no puede llevar interfaz y se cargaba con `flush` + `add` (hueco sin protegidos). Decisión:
- set nuevo `hash:net,iface`, tipo fijo en el código y nombre en `protegidos.set_name`; entradas `cidr,interfaz`;
- regla de la cadena de aRGus `--match-set <set> src,src -j RETURN` (origen e interfaz de entrada);
- aplicación atómica: set temporal, `ipset swap`, borrar el temporal; nunca `flush` + `add`;
- si el set ya existe con otro tipo, `[PROTEGIDOS-SET-TIPO]` claro con la orden para rehacerlo;
- solo el agente lo escribe; fuera `ipsets.whitelist` y su `RETURN` sin interfaz;
- `IPSetWrapper` gana el tipo y la validación de `cidr,interfaz` (interfaz: 1 a 15 caracteres `[A-Za-z0-9._-]`).

**La barrera de usuario (D-G).** El suscriptor (`ALERTA_PROTEGIDO`, fuera del episodio) y `BatchProcessor` (nunca entra
en el blacklist) protegen por IP siempre, venga por donde venga el paquete: si dejaran de proteger lo que llega por
otra interfaz, falsificar el origen de un protegido bastaría para que aRGus lo bloqueara. Además, la interfaz del
evento es la del host del sniffer (el BPF escribe `ifNN` desde el ifindex), que en un despliegue distribuido no es la
del firewall. La interfaz y la MAC atan la exención del kernel y alimentan el antispoofing y la alerta (8e.4).

**El defecto RFC 1918 se borra (D-B).** Medido: el único camino que mete un origen en el blacklist es la mitigación
`ddos_v2`; el camino viejo (`add_detections`) es inalcanzable (DEBT-FW-LEGACY-STEPS-001). Sin manifiesto verificado
el candado (D6) deja la mitigación en sombra, así que el defecto amplio ya no protege nada.

**Plano de control ausente (D-C).** Al arrancar y al aplicar cada manifiesto, el agente compara los hosts de su
`etcd.endpoints` con las entradas `infraestructura` de `comun` y de su planta. Si falta alguno,
`[PROTEGIDOS-INFRA-INCOMPLETA]` cada `protegidos.aviso_sec`. No cierra el candado: el hospital siempre protegido, y
perder el etcd-server no para la protección (DAY316). Coste: dos listas pequeñas, una vez por cambio; nada por paquete
ni acceso al kernel.

**La clave pública (D-E, patrón ADR-025).** `-DARGUS_PROTEGIDOS_PUBKEY_ACTUAL_HEX` (obligatoria) y
`-DARGUS_PROTEGIDOS_PUBKEY_SIGUIENTE_HEX` (vacía si no hay rotación en curso). Sin `-D`, CMake las lee de
`/etc/ml-defender/firewall-acl-agent/protegidos_pubkey_actual.hex` y `..._siguiente.hex` (opcional), que el bootstrap
trae de Vault (8e.2). Sin la actual: `FATAL_ERROR` con mensaje claro; aquí no hay defecto sano posible. En producción,
Jenkins pasa `-D`. El firewall enlaza libsodium (hoy no lo hace). Los tests usan una clave desechable generada en el
propio test.

**Alcance de 8e.1 (D-H).** Carga el manifiesto de la caché al arrancar, la vuelve a verificar cada `aviso_sec` (D7: si
deja de verificar, se queda con lo que tiene en memoria y avisa) y guarda lo vigente en un contenedor seguro entre
hilos (hoy el suscriptor y `BatchProcessor` copian los rangos una sola vez al arrancar). Pedirlo al etcd-server
(`consulta_sec`) va en 8e.3, con sus rutas.

**Límite de 8e.1 (medido DAY318).** La versión monótona protege mientras el agente está vivo: al arrancar no hay
versión aplicada y se acepta cualquier manifiesto bien firmado de la caché, también uno más viejo. La caché solo la
escribe root (O_NOFOLLOW, temporal y rename), pero el anti-rollback entre reinicios (la versión más alta vista,
guardada aparte, o pedida al etcd-server antes de aplicar) se cierra en 8e.3.

**Campos nuevos en `firewall.json`** (el JSON sigue siendo la ley para lo que no es la lista):

| Campo | Rango | Defecto | Doc |
|---|---|---|---|
| `protegidos.hospital_id` | cadena [1, 64], `[a-z0-9-]` | — | sin valor sano por defecto: si falta, candado cerrado y aviso |
| `protegidos.despliegue_id` | cadena [1, 64], `[a-z0-9-]` | — | la planta de este firewall; sin valor sano por defecto: si falta, candado cerrado y aviso |
| `protegidos.set_name` | `[A-Za-z0-9_-]`, de 1 a 29 (el temporal `<set>_n` del swap añade dos y tiene que caber en los 31 de `is_valid_set_name`) | `ml_defender_protegidos` | set `hash:net,iface` del kernel |
| `protegidos.manifiesto_cache` | ruta absoluta | `/var/lib/ml-defender/firewall/protegidos.manifiesto` | último manifiesto verificado |
| `protegidos.aviso_sec` | [30, 86400] | 300 | aviso periódico y nueva verificación de la caché |
| `protegidos.comprobacion_kernel_sec` | [5, 3600] | 30 | vigía kernel ↔ manifiesto (8e.4a, hecho DAY320) |
| `protegidos.antispoof.cadena` | `[A-Za-z0-9_-]`, de 1 a 24 | `ARGUS_ANTISPOOF` | cadena de `raw PREROUTING`; las de spoofing son `<cadena>_IF` y `<cadena>_MAC` (8e.4b) |
| `protegidos.antispoof.set_redes` | `[A-Za-z0-9_-]`, de 1 a 29 | `ml_defender_prot_redes` | `hash:net` de las redes protegidas (8e.4b) |
| `protegidos.antispoof.set_ips_mac` | `[A-Za-z0-9_-]`, de 1 a 29 | `ml_defender_prot_ipmac` | `hash:ip` de las IPs que llevan MAC (8e.4b) |
| `protegidos.antispoof.set_mac` | `[A-Za-z0-9_-]`, de 1 a 29 | `ml_defender_prot_mac` | `hash:ip,mac` (8e.4b) |
| `protegidos.antispoof.log_por_minuto` | [1, 600] | 5 | muestras `LOG` por minuto y cadena (8e.4b) |
| `protegidos.antispoof.log_rafaga` | [1, 100] | 5 | ráfaga inicial del `LOG` (8e.4b) |
| `protegidos.consulta_sec` | [5, 3600] | 30 | cada cuánto se pide el manifiesto al etcd-server (8e.3) |

**Mensajes de log** (etiquetas para buscar):
- `[PROTEGIDOS-MANIFIESTO] verificado version=N clave=actual|siguiente firmante=... hospital=... planta=... entradas=E (infraestructura=a intranet=b dmz=c externos_criticos=d)`
- `[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=firma|version|hospital|planta|limite|formato ...` (se conserva el último verificado)
- `[PROTEGIDOS-SIN-MANIFIESTO] mitigacion real BLOQUEADA (candado); sombra` (periódico)
- `[PROTEGIDOS-INFRA-INCOMPLETA] etcd.endpoints sin entrada infraestructura: ...` (periódico)
- `[PROTEGIDOS-SET-TIPO] el set <nombre> existe con tipo <tipo> (se espera hash:net,iface): ...`
- `[INFRA-CAMBIO] version A -> B firmante=... altas=... bajas=...`
- `[PROTEGIDOS-DIVERGENCIA] set <set> != manifiesto version N: sobran=[...] faltan=[...]` y
  `[PROTEGIDOS-DIVERGENCIA] reglas: <motivo>`; `[PROTEGIDOS-RECONCILIADO] ...` (comprobado tras volver a leer);
  `[PROTEGIDOS-VIGIA]` (arranque, resumen `comprobaciones= divergencias= reconciliaciones= fallos=` cada `aviso_sec`,
  aviso de `dry_run` y `ERROR` si no se pudo reconciliar) (8e.4a, DAY320)
- `[PROTEGIDOS-ANTISPOOF] aplicado (<por qué>): manifiesto version N modo=cuenta|descarta redes= ips_mac= mac= cadena raw <cadena>`,
  `ERROR al aplicar`, `NO se instala: <motivo>` (nombres que chocan, `dry_run=true`) y aviso si el kernel no admite
  `hash:ip,mac` (sin comprobación de MAC); `[PROTEGIDOS-RUTA] <entrada>: esa red no se cuenta ni se descarta`
  (periódico); `[PROTEGIDOS-DIVERGENCIA] antispoof: ...` / `[PROTEGIDOS-RECONCILIADO] antispoof: ...`;
  `[PROTEGIDOS-SPOOFING] origen protegido falsificado: interfaz=+N mac=+N (total interfaz=N mac=N) modo=...;
  evidencia: journalctl -k | grep ARGUS-SPOOF`. En el journal del kernel, `ARGUS-SPOOF-IF` y `ARGUS-SPOOF-MAC`, con
  la MAC de origen (8e.4b, DAY320)
- `[ETCD-CLIENTE-LATIDO-DATO] <CN>: <clave>=N (nuevo|antes M); va en el siguiente latido` (una línea por cambio, no
  por latido) o `<motivo>; no se guarda (datos del latido: <formato>)`; `[ETCD-CLIENTE-LATIDO-DATOS-RECHAZADOS]` y
  `[ETCD-CLIENTE-LATIDO-DATOS-ACEPTADOS]` cuando cambia lo que responde el etcd-server. En el etcd-server,
  `[ETCD-LATIDO-DATOS-RECHAZADOS] <CN>: <motivo>; el latido se guarda sin datos` y `[ETCD-LATIDO-DATOS-ACEPTADOS]`,
  también solo al cambiar. `[PROTEGIDOS-RP-FILTER] <interfaz>=<efectivo> (all=a if=b, sin filtro|estricto|laxo) ...;
  solo se informa, no se cambia (H-F)`, al arrancar y cada `aviso_sec` (8e.4c, DAY321)
- En `pipeline-status` (`etcd_vm_estado.sh`): `✅ protegidos: vN publicada; K componentes al día`, `⚠️ ... K DESFASADOS`,
  `⚠️ ... POR DELANTE`, `⚠️ ... sin manifiesto publicado`, `⚠️ ... ningún componente informa protegidos_version` o
  `❌ ... vigente ilegible`, y debajo una línea por componente (`- <CN> vN al día|DESFASADO|POR DELANTE (activo|muerto,
  latido hace S s)`) (8e.4c, DAY321)
- `protegidos:` gana `infraestructura=N`.

Implementados en 8e.1b, además: `[PROTEGIDOS-CLAVE]` (huellas de las dos ranuras compiladas: los 16 primeros hex
del sha256 de la clave, no los de la clave), `[PROTEGIDOS-SET]`, `[PROTEGIDOS-KERNEL]` (entradas llevadas al set;
las IPv6 solo en la barrera) y `[PROTEGIDOS-CACHE]` (la caché no se lee o ya no verifica: se conserva lo que hay en
memoria). `[INFRA-CAMBIO]` llega con 8e.3, cuando el manifiesto cambia en caliente (medido DAY319: solo se
escribe si ya había un vigente; con la primera versión sale solo `[PROTEGIDOS-MANIFIESTO]`).

**Tests de 8e.1:** firma válida con la clave actual y con la siguiente; firma de otra clave; carga alterada un byte;
versión igual y menor; otro `hospital_id`; planta ausente; prefijo más amplio que el límite (en `infraestructura`,
/31); entrada sin interfaz o con interfaz mal formada; caché ausente o alterada al arrancar; candado con
`habilitada=true` y sin manifiesto; último verificado conservado tras un rechazo en caliente; aviso
`INFRA-INCOMPLETA`; set existente de otro tipo y órdenes del `swap` (en dry_run); barrera por IP con un origen
protegido que llega por otra interfaz.

## 7. Diseño fino de 8e.4 (cerrado DAY320)

Decisiones de Alonso DAY320 (H-A a H-J), medidas antes de decidir donde se podía. Reglas que lo cruzan todo: el JSON es
la ley (cada campo nuevo se lee de ahí y, si falta o está mal formado, defecto del código con aviso; todo al log); toda
operación nueva o modificada lleva un test que pruebe que hace su trabajo; coste por paquete O(1), como mucho
O(log n); las reglas, ficheros y procesos que vigilan Wazuh y Falco van en su configuración, no en el código; si algo
no cuadra, se reconcilia.

**Medido antes de decidir (DAY320, en el código):** nada de 8e.4 existía; el latido solo lleva `{timestamp, status}` y
el etcd-server ignora su cuerpo; Falco solo está en `hardened-x86` y sus reglas van en un heredoc de `setup-falco.sh`;
de Wazuh no hay reglas de aRGus; la VM etcd no tiene agente Wazuh ni MAC fija; `/var/log/vault` está en la raíz.

**`dry_run` (precisado DAY320).** Con `operation.dry_run=true` el agente no escribe nada en el kernel (regla de
DAY302): ni set ni cadena. El vigía no compara y lo dice al arrancar y cada `aviso_sec`. Con `dry_run=false` y el
candado cerrado o la mitigación deshabilitada, el vigía compara y reconcilia y el antispoofing (8e.4b) solo cuenta; con
`dry_run=false`, mitigación habilitada y manifiesto verificado, el antispoofing descarta. La hipótesis de este ADR (con
la mitigación real, ningún protegido entra en el blacklist) solo se prueba con `dry_run=false` y `habilitada=true`
(Alonso DAY320): se mide así en EMECAS (C7, abajo) y el lab sigue arrancando en sombra de serie hasta que EMECAS+++ pase
entero ("si la mitigación real bloquea a clientes legítimos que no estén en el manifiesto, estamos haciendo algo mal:
midamos primero").

- **H-A** El vigía reconcilia (no solo avisa): lo no firmado pierde la protección y lo que falta se repone.
- **H-B** Antispoofing con coste constante por paquete: seis reglas fijas en `raw PREROUTING` sobre sets (`hash:net`
  de las redes protegidas, `hash:net,iface`, `hash:ip` de las IPs con MAC y `hash:ip,mac`), no una regla por entrada.
  Medido DAY320 en el defender (`scripts/etcd_ha/d320_medir_antispoof.sh`, v2: 19/19): el no protegido sale en la
  segunda regla con un solo lookup; spoofing por interfaz y por MAC contados exactos; un paquete con interfaz y MAC
  malas cuenta una sola vez; el DROP en raw no deja pasar nada a mangle; `iptables-restore --noflush` rehace las
  cadenas de golpe; lectura del vigía 2-3 ms; ipset 7.17 tiene `hash:ip,mac`. Las reglas 3 y 5 saltan con `-g`
  (goto): con `-j`, en modo solo contar, el paquete volvía y seguía por la cadena (medido en la v1). Los contadores por
  entrada de ipset suben con cualquier coincidencia, también las negadas: los totales salen de las reglas y la
  identidad del paquete del LOG.
- **H-C** Las reglas del antispoofing solo cuentan mientras la mitigación no sea real (ver `dry_run` arriba); con ella,
  DROP.
- **H-D** Si la interfaz de una entrada no casa con la ruta del kernel (`ip route get`), no se instala su DROP y
  `[PROTEGIDOS-RUTA]` es alarma periódica: un DROP por interfaz equivocada sería el DoS autoinfligido otra vez. `-i lo`
  siempre exento (un `intranet /24` suele contener la IP del propio firewall).
- **H-E** Evidencia de spoofing: `LOG` con límite (medido: 5 líneas con `--limit-burst 5`, con la MAC de origen) al
  journal; lo recoge Wazuh. Sin NFLOG ni hilo nuevo.
- **H-F** `rp_filter` se lee y se informa, no se cambia (medido DAY320: 0 en todas las interfaces del defender).
- **H-G** MAC fija de la VM etcd en el Vagrantfile y en la plantilla del lab, para probar en EMECAS los dos casos: el
  client falsificando .20 (entra por `eth2`: lo caza la MAC) y un veth en un netns del defender (lo caza la interfaz).
- **H-H** Datos de latido genéricos y validados en el etcd-client; el firewall manda `protegidos_version`; el
  etcd-server lo guarda en el registro y `pipeline-status` marca el firewall desfasado.
- **H-I** Agente Wazuh en la VM etcd (disco de `/var/log/vault` al 75 % y fallos de los audit devices).
- **H-J** 8e.4d dentro del PR1.

**8e.4a, el vigía (hecho DAY320, fe4c94d3).** Cada `comprobacion_kernel_sec`, en el bucle principal (fuera del camino
del paquete), `vigia_protegidos_paso` (`firewall/protegidos_vigia.hpp`) compara con lo vigente:
- K1 el set existe y es `hash:net,iface` (si falta, se crea con la misma configuración que al arrancar);
- K2 su contenido (`IPSetWrapper::list_entries_opciones`: entradas con sus opciones, sin contadores) es exactamente el
  de las entradas IPv4 del vigente, en forma canónica (red con los bits de host a cero y prefijo explícito: el kernel
  normaliza y omite `/32`). Una entrada de más, de menos, por otra interfaz o con opciones (`nomatch` anularía la
  exención) es divergencia. Sin vigente, el set tiene que estar vacío. O(n) con conjuntos hash;
- K3 la cadena: un único salto INPUT → cadena en la posición 1 y dentro exactamente protegidos `src,src` RETURN y
  blacklist DROP, en ese orden (`setup_base_rules`).
Si no cuadra, se reconcilia (sustitución atómica del set; `setup_base_rules` para la cadena) y se vuelve a leer: solo
cuenta como reconciliado lo que se comprueba. **Set ajeno**: si existe con otro tipo, no se destruye y la cadena se
rehace sin el RETURN. Medido DAY320: iptables acepta `--match-set <set hash:ip> src,src` e ignora la dimensión de más,
así que el RETURN eximiría un contenido que nadie ha firmado; quitarlo no pone en riesgo a nadie (el agente nunca mete a
un protegido en el blacklist; la barrera de usuario protege por IP) y vuelve en cuanto el set está bien.

Medido DAY320: banco (Debian 12, GCC 12.2, native y skylake, dos pasadas) 119/119 y 0 avisos del código;
`test_protegidos_vigia` 42/42 (con wrappers falsos que dicen "hecho" sin hacerlo); `test_protegidos_vigia_root` 34/34
(kernel real, S1-S9); 7 mutaciones cazadas. Lab: `pipeline-build` rc 0; `test-firewall` 95/95; `test-firewall-e2e`
PASA (24, 0 saltados); `lab-e2e-vigia` PASA (E1 6 s, E2-E4 25-26 s, límite 35; kernel igual que al empezar; 0 errores).

**C7 (la hipótesis del DoS autoinfligido, medida con la mitigación real).** `lab-e2e-mitigacion` (`dry_run=false`,
`habilitada=true`, ataque NTP de .50 y .61) exige la VM etcd arriba y .20 en el set de protegidos, y muestrea cada
segundo el blacklist y los contadores por entrada del set. DAY320: C1-C5 y **C7 PASA**: .20 en 0 de 459 muestras del
blacklist; su entrada del set de protegidos de 223 a 529 paquetes durante los ataques. En la misma corrida `ddos_v2`
volvió a marcar DROP a la VM etcd (`[SOMBRA-DDOS] protegidos: ... infraestructura=2`, DEBT-DDOS-V2-NTP-CLIENTE-001):
el DoS autoinfligido del DAY317 se produjo y la barrera lo paró.

**8e.4b, el antispoofing (hecho DAY320, 345f8607; arreglos del lab 6479804f y 3c67ca40).**
`firewall/protegidos_antispoof.hpp`. `repartir_antispoof` reparte las entradas IPv4 del vigente en tres sets (redes,
IPs con MAC, pares IP-MAC); las que tienen una interfaz que no casa con la ruta del kernel (`ip -o route get`, H-D) se
quedan fuera de `set_redes`, y salen en `[PROTEGIDOS-RUTA]`. `texto_restore_antispoof` genera las cadenas y se cargan
de golpe con `iptables-restore -w --noflush`. En `raw PREROUTING`, una regla de salto y seis reglas fijas:
1. `lo` RETURN;
2. origen fuera de `set_redes` RETURN (lo no protegido sale aquí, con un solo lookup);
3. `(origen, interfaz)` fuera del set de protegidos `-g <cadena>_IF`;
4. origen fuera de `set_ips_mac` RETURN;
5. `(origen, MAC)` fuera de `set_mac` `-g <cadena>_MAC`;
6. RETURN.

`_IF` y `_MAC` llevan `LOG` con límite y una regla de cuenta, que lleva `DROP` solo con la mitigación real (H-C). La
aplicación es inmediata al arrancar y en cuanto cambia la versión del manifiesto o el modo. En cada vuelta del vigía,
`antispoof_paso` comprueba los sets y las cadenas raw y reconcilia (K4 y K5), vuelve a mirar las rutas y suma los
contadores de las reglas de cuenta en `[PROTEGIDOS-SPOOFING]`. Si el kernel no tiene `hash:ip,mac`, el antispoofing
queda sin la parte de MAC y lo avisa.

Medido DAY320: banco (sin `hash:ip,mac` en su kernel) native y skylake, dos pasadas, 121/121 (el test de root sale
Skipped 77) y 0 avisos del código; `test_protegidos_antispoof` 41/41; `test_protegidos_antispoof_root` 15/15 en el
banco (`ARGUS_TEST_SIN_IPMAC=1`) y 16/16 en el defender; 8 mutaciones cazadas. Lab: `test-firewall` 96/96;
`test-firewall-e2e` PASA (25, 0 saltados); `lab-e2e-antispoof` con la mitigación real PASA: el client falsifica .62
(entrada de prueba con una MAC que no es de nadie, firmada al empezar y quitada en el trap) y el kernel cuenta
`SPOOF-MAC` +20 y deja pasar 0 a mangle; un netns del defender falsifica .20 por un veth, `SPOOF-IF` +20 y 0 a mangle;
el tráfico legítimo de .20 suma 0 al spoofing (su entrada del set de protegidos de 209 a 531 paquetes) y la VM etcd
sigue sana; 5 líneas `ARGUS-SPOOF-IF` y 5 `ARGUS-SPOOF-MAC` en el journal. `lab-e2e-vigia` y `lab-e2e-mitigacion`
(C7) siguen PASA con el antispoofing instalado.

**H-F se hizo en 8e.4c** (DAY321, 1818f4ec), que cierra DEBT-FW-ANTISPOOF-RP-FILTER-001; 8e.4b solo lo leía en el
script de medida.

**8e.4c, la versión del manifiesto en el latido y `rp_filter` (hecho DAY321, 1818f4ec).** Decisiones de Alonso
(DAY321), las cuatro como se recomendaron:
- **Tipo de los datos del latido: solo enteros.** Regla única en `libs/latido/include/latido/datos_latido.hpp`, que
  aplican el etcd-client antes de enviar y el etcd-server al recibir: `"datos"` es un objeto de 0 a 8 claves
  `^[a-z][a-z0-9_]{0,31}$` con enteros en [0, 2^53 − 1] (el mayor entero que cualquier lector JSON representa sin perder
  precisión). Es contrato del protocolo, no configuración, como el tamaño máximo de la carga del manifiesto. Con una
  clave mala se rechazan todos los datos de ese latido. O(datos).
- **Datos mal formados en el etcd-server: 200 sin los datos.** El latido se guarda igual, sin la clave `"datos"`, y la
  respuesta lo dice en `"datos_rechazados"`. Medido en el código antes de decidir: un 4xx al latido hace que el cliente
  se dé por desregistrado y quede «sin servicio», así que un dato malo dejaría al componente sin latir y lo acabaría
  marcando muerto.
- **Origen de `pipeline-status`: etcd con `etcdctl`**, sin ruta nueva ni reglas de authz nuevas.
- **E2E del desfase: `protegidos.consulta_sec=3600` solo durante la prueba**, dentro de `lab-e2e`.

Cómo queda:
- `EtcdClient::poner_dato_latido(clave, valor)`, seguro entre hilos; el mantenedor y `heartbeat()` añaden `"datos"`
  cuando hay alguno. El firewall pone `protegidos_version` (0 sin manifiesto) al arrancar y tras cada consulta.
- El etcd-server guarda `latido/<CN> = {"ultimo", "estado", "datos"}`. Al marcar un componente muerto se conservan
  los datos, así que se ve la versión que tenía al morir; el siguiente latido los renueva.
- `scripts/etcd_ha/etcd_vm_estado.sh` lee `<prefijo>latido/` y `<prefijo>protegidos/vigente` con los certificados que
  ya usa. La versión publicada sale de la carga del sobre sin verificar la firma, porque el etcd-server solo escribe
  `vigente` después de verificarla y el firewall la verifica otra vez. Solo lista los componentes que mandan
  `protegidos_version`. Un desfase es normal hasta `consulta_sec` más un latido después de publicar.
- **La línea de protegidos solo informa (⚠️): no cuenta en el veredicto de la VM etcd.** Cambio sobre lo que se
  propuso antes de medir: `--estricto` no lo usa solo EMECAS, también `etcd-vm-check` (dentro de `etcd-vm-deploy` y
  `etcd-server-start`, con el firewall parado) y `etcd-vm-aviso` (en `pipeline-start`, antes de arrancarlo). Con el
  desfase contando, un despliegue fallaría solo por haber publicado una versión con el firewall parado.
- **H-F:** `[PROTEGIDOS-RP-FILTER]` al arrancar y cada `aviso_sec` (`firewall/protegidos_rp_filter.hpp`): por cada
  interfaz de las entradas IPv4 del vigente, `max(conf/all/rp_filter, conf/<interfaz>/rp_filter)`, que es lo que usa
  el kernel. Solo se lee. Un nombre que pudiera salir de la raíz (`.`, `..`, `/`) no se lee.

Medido DAY321:
- Banco (Debian 12, GCC 12.2, native y skylake, dos pasadas cada uno): etcd-client 5/5, etcd-server 9/9, firewall
  122/122 y 0 avisos del código. `test_latido_datos` 8 tests; L1-L7 en `test_etcd_cliente_tls` (35/35);
  `test_protegidos_rp_filter` 33/33. Con etcd 3.6.16 real (TLS y RBAC como en el Vagrantfile) y el etcd-server
  compilado, 16/16 en las cuatro compilaciones. 16 mutaciones cazadas, todas compilando.
- Lab (`PROFILE=production`): `pipeline-build` rc 0; `test-firewall` 97/97; etcd-server 9/9; etcd-client 5/5;
  `test-firewall-e2e` PASA (25, 0 saltados); `etcd-vm-deploy` SANO. Tras arrancar, `✅ protegidos: v9 publicada; 1
  componente al día` y `[PROTEGIDOS-RP-FILTER] eth2=0 (all=0 if=0, sin filtro)`. `lab-e2e-latido` PASA en 7 min 49 s:
  L0 al día con v9 en 5 s; L1 v10 publicada y el firewall en v9 DESFASADO a los 4 s, con el veredicto en SANO; L2 al día
  con v10 a los 4 s del rearranque; L3 v11 por la consulta periódica en 37 s (límite 75); L4 0 rechazos en los dos lados.
  El lab queda en v11, con el contenido de antes de la prueba.
- Al parar el firewall de forma ordenada, su baja (`/unregister`) borra `latido/<CN>` y deja de salir en la línea; solo
  sale como muerto si cae sin darse de baja.

**El kernel después de los E2E (3c67ca40).** Con la mitigación real, el agente instala también el antispoofing durante
`lab-e2e-vigia` y `lab-e2e-mitigacion`, y sus traps no lo conocían: la cadena raw usa el set de protegidos, así que el
`ipset destroy` de ese set fallaba sin decir nada y quedaban en el defender las tres cadenas raw (en modo descarta) y
cuatro sets. Ahora los tres traps llaman a `scripts/etcd_ha/d320_limpia_kernel.sh` (primero los saltos y las cadenas,
raw y filtro; después los sets; los nombres, del JSON), y `lab-e2e` comprueba con `make lab-kernel-limpio` (solo
cuenta) que tras cada uno no queda nada.

**8e.4d, la vigilancia con Wazuh y Falco (8e.4d-1 y 8e.4d-2 hechos DAY321; 8e.4d-3, el E2E, pendiente).** Decisiones
de Alonso (DAY321):
- **Cada sensor en la máquina que vigila**: Falco ve las syscalls del kernel donde corre, y el FIM y el journal son
  locales. Falco en la VM etcd y en el defender; agente de Wazuh en las dos; el manager sigue en la VM wazuh. La VM
  etcd pasa de 1024 a 1536 MB (medido: Falco 114-149 MB de RSS con las reglas de serie, 101 MB con las de aRGus).
- **Falco → fichero → Wazuh**: Falco escribe JSON en `/var/log/falco/eventos.json` y el agente lo lee; Falco no
  conoce al manager.
- **Configuración centralizada**: un grupo del manager por máquina (`argus-etcd`, `argus-defender`), con su
  `agent.conf`, en el repo (`provisioning/wazuh/argus/`). Sin `<command>` en los agentes: exigiría
  `remote_commands=1` y un manager comprometido podría ejecutar órdenes en ellos; el disco lo mide un servicio propio.
- **Origen oficial**: manager, agentes y Falco desde el apt firmado de su mantenedor, con versión fija
  (`provisioning/{wazuh,falco}/VERSION` y `apt-mark hold`) y la clave del repositorio comprobada por huella antes de
  instalarla (`provisioning/{wazuh,falco}/CLAVE`, `scripts/vigilancia/lib_apt_oficial.sh`). Una clave que no está en el
  fichero de huellas para la instalación. Sin `.deb` de terceros en el repo.
- **E2E dentro de `lab-e2e`**.

Cómo queda:
- **Manager** (`scripts/vigilancia/wazuh_manager_desplegar.sh`, aprovisionador `argus-vigilancia` y
  `make vigilancia-manager-deploy`): comprueba la versión; pone decoders, reglas y `agent.conf` con copia de lo
  anterior; valida (`verify-agent-conf` por grupo, `wazuh-analysisd -t`) y, si no valida, restaura; reinicia solo si
  algo cambió; asigna cada agente a su grupo (`grupos.tsv`) comprobando el resultado, no el código de salida; y pasa
  el test de las reglas (`test_reglas_wazuh.sh`, 27 casos con `wazuh-logtest`). Reglas: 100510-100518 firewall
  (`[PROTEGIDOS-*]`: divergencia, reconciliado, spoofing, manifiesto rechazado o ausente, rutas, errores del vigía y
  del antispoofing), 100520 errores del audit de Vault, 100530 `ARGUS-SPOOF-IF|MAC` del kernel, 100540-100542 disco,
  100550-100553 eventos de Falco cuya regla empieza por `argus_` (CRITICAL 12, WARNING 8, NOTICE 4).
- **Agentes** (`wazuh_agente_instalar.sh`, `run: always` en cada VM): versión de `VERSION`, manager de `MANAGER`;
  con todo ya puesto no hace nada ni usa la red. FIM en tiempo real de la configuración y la PKI
  (`/etc/argus-pki`, `/etc/vault.d`, `/etc/etcd`, `/etc/falco`, `/etc/argus-vigilancia`…) y periódico de los binarios;
  journald filtrado (vault `[ERROR]`, `argus-disco`, `ARGUS-SPOOF-*`), `firewall-agent.log` en el defender y los
  eventos de Falco.
- **Falco 0.43.1** (`falco_instalar.sh`, `modern_ebpf`, sin falcoctl-artifact-follow): `config.d/argus_salida.yaml`
  apaga todas las reglas y enciende las `argus_*` (`config.d` se funde en `append`: un `rules_files` ahí se sumaba al
  del paquete y cargaba las reglas dos veces); `rules.d/argus_lab.yaml`, tres reglas por ruta del ejecutable (el
  `comm` del kernel son 15 caracteres): hijo inesperado de un componente (CRITICAL; permitidos: ipset, ip e iptables
  del firewall y las dos órdenes `sysctl` del sniffer, DEBT-SNIFFER-SYSTEM-SYSCTL-001), clave leída por quien no es su
  dueño (CRITICAL) y lectura administrativa de una clave (NOTICE, rastro de `pipeline-status` y `provision.sh
  verify`). Instalación todo o nada: `--dry-run` tiene que cargar `argus_lab.yaml` una vez y dejar activas
  exactamente sus reglas.
- **argus-disco** (`scripts/vigilancia/argus_disco.py`, VM etcd, sin privilegios): cada `periodo_s` mide la partición
  de `ruta` como `df` y escribe `ARGUS-DISCO ruta=… uso=… umbral=… estado=OK|ALTO` al journal; ALTO es la regla 100541.
  `/etc/argus-vigilancia/disco.json` (`ruta`, `umbral_pct` [1, 99] = 75, `periodo_s` [10, 3600] = 60) se relee en
  cada ciclo; un campo malo, desconocido o un fichero ilegible da `ARGUS-DISCO-ERROR` (regla 100542) y ese campo toma
  su defecto; la configuración efectiva sale con su origen al arrancar y cuando cambia.

Medido DAY321 (detalle en BACKLOG, «DAY321 — pasos 8e.4d-1 y 8e.4d-2»): banco 27/27 reglas, `test_argus_disco` 16/16
con 9 mutaciones cazadas, los instaladores restauran con configuraciones rotas y `lib_apt_oficial.sh` rechaza claves
ajenas. Lab: los cinco agentes en 4.14.10-1 desde el apt de Wazuh y conectados, etcd y defender en su grupo, Falco
0.43.1 en las dos VMs con 3 reglas activas, argus-disco `uso=4 estado=OK`, `pipeline-status` en ✅.
