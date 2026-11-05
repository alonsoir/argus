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
- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server (`GET`/`PUT`, PUT solo con certificado
  OU=argus-infra (D9 bis), verificación de firma, versión y hospital); el firewall lo pide cada
  `protegidos.consulta_sec`. El etcd-server necesita leer la clave pública: medido DAY318, hoy su política de Vault
  da 403 en `argus-transit/keys/...`. Fichero de despliegue del lab.
- **8e.4** Comprobación continua kernel ↔ manifiesto, antispoofing en `raw PREROUTING` generado desde el manifiesto,
  alertas de spoofing por interfaz y MAC, versión en el latido y en
  `pipeline-status`, reglas Falco (en la VM hardened-x86, `check-prod-falco`) y Wazuh. Falco y Wazuh avisan también
  cuando la partición del audit de Vault (`/var/log/vault`) pasa de un umbral (p. ej. 75 %), con prioridad en el log,
  y cuando falla uno de los dos audit devices (Alonso DAY318: es su trabajo avisarnos).
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
  "firmante": "<entidad de Vault del admin>",
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
| `protegidos.comprobacion_kernel_sec` | [5, 3600] | 30 | comprobación kernel ↔ manifiesto (8e.4) |
| `protegidos.consulta_sec` | [5, 3600] | 30 | cada cuánto se pide el manifiesto al etcd-server (8e.3) |

**Mensajes de log** (etiquetas para buscar):
- `[PROTEGIDOS-MANIFIESTO] verificado version=N clave=actual|siguiente firmante=... hospital=... planta=... entradas=E (infraestructura=a intranet=b dmz=c externos_criticos=d)`
- `[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=firma|version|hospital|planta|limite|formato ...` (se conserva el último verificado)
- `[PROTEGIDOS-SIN-MANIFIESTO] mitigacion real BLOQUEADA (candado); sombra` (periódico)
- `[PROTEGIDOS-INFRA-INCOMPLETA] etcd.endpoints sin entrada infraestructura: ...` (periódico)
- `[PROTEGIDOS-SET-TIPO] el set <nombre> existe con tipo <tipo> (se espera hash:net,iface): ...`
- `[INFRA-CAMBIO] version A -> B firmante=... altas=... bajas=...`
- `[PROTEGIDOS-DIVERGENCIA] kernel != manifiesto: ...` / `[PROTEGIDOS-SPOOFING] origen=... interfaz|mac ...` (8e.4)
- `protegidos:` gana `infraestructura=N`.

Implementados en 8e.1b, además: `[PROTEGIDOS-CLAVE]` (huellas de las dos ranuras compiladas: los 16 primeros hex
del sha256 de la clave, no los de la clave), `[PROTEGIDOS-SET]`, `[PROTEGIDOS-KERNEL]` (entradas llevadas al set;
las IPv6 solo en la barrera) y `[PROTEGIDOS-CACHE]` (la caché no se lee o ya no verifica: se conserva lo que hay en
memoria). `[INFRA-CAMBIO]` llega con 8e.3, cuando el manifiesto cambia en caliente.

**Tests de 8e.1:** firma válida con la clave actual y con la siguiente; firma de otra clave; carga alterada un byte;
versión igual y menor; otro `hospital_id`; planta ausente; prefijo más amplio que el límite (en `infraestructura`,
/31); entrada sin interfaz o con interfaz mal formada; caché ausente o alterada al arrancar; candado con
`habilitada=true` y sin manifiesto; último verificado conservado tras un rechazo en caliente; aviso
`INFRA-INCOMPLETA`; set existente de otro tipo y órdenes del `swap` (en dry_run); barrera por IP con un origen
protegido que llega por otra interfaz.
