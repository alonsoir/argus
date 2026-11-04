# ADR-060 — Manifiesto firmado de rangos protegidos, uno por despliegue

| Campo | Valor |
|---|---|
| **ADR** | 060 |
| **Fecha** | 2026-11-04 (DAY 317) |
| **Estado** | Propuesto (decisiones de Alonso DAY317; diseño fino de 8e.1 por revisar DAY318) |
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

**D1. Un manifiesto por despliegue, en un solo sitio.** Todas las listas protegidas salen de un único manifiesto
firmado por despliegue, con cuatro categorías: `infraestructura` (nueva: el plano de control de aRGus, etcd,
etcd-server, Vault), `intranet`, `dmz`, `externos_criticos`. `ddos_protegidos` desaparece de `firewall.json` (lo
deprecado se borra). Las categorías se mantienen separadas para contar y para aplicar a cada una su política.

**D2. Entradas estrechas.** Cada entrada: `{cidr, interfaz, mac?, motivo}`.
- `interfaz` obligatoria: un paquete con origen protegido que llega por otra interfaz no se protege nunca y dispara
  la alerta de spoofing (vale aunque haya routers por medio).
- `mac` opcional, cuando el host está en el mismo segmento L2 que el firewall; una IP protegida con otra MAC es alerta
  de spoofing. (Más allá de un router la MAC que se ve es la del router: por eso es opcional.)
- La plantilla de despliegue fija **el prefijo más amplio permitido por categoría**. `infraestructura`: solo /32 y
  /128, sin excepción. Las demás: el límite que diga la plantilla (p. ej. /24). Un manifiesto que lo supera no se
  firma (`argus-infra` lo rechaza antes de ir a Vault) y el firewall tampoco lo aplicaría.

**D3. Firma asimétrica, clave por hospital.**
- Ed25519, no HMAC: con HMAC el verificador tendría el secreto y un malware en el defender podría firmar.
- Clave privada en **Vault transit**, no exportable, una por **hospital**: el límite de daño coincide con el límite de
  confianza (las plantas de un hospital comparten administración). Lo que separa las plantas es el `despliegue_id`
  del manifiesto. Descartadas: una por planta (más imágenes sin más seguridad real) y una para todos los hospitales
  (comprometerla los expone a todos).
- Clave pública **compilada en el firewall-acl-agent** (patrón ADR-025), inyectada por Jenkins en la compilación de la
  imagen del hospital. No es un fichero que se pueda cambiar: para cambiarla hay que cambiar el binario, que vigilan
  Falco y la verificación de la imagen. Dos ranuras compiladas (actual y siguiente) para rotar sin dejar a los
  firewalls sin poder verificar mientras llega la imagen nueva.

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
   `despliegue_id` y la versión antes de guardarlo en etcd (defensa en profundidad; la autenticidad sale de la firma,
   no del transporte).
3. Cada firewall-acl-agent del despliegue lo recoge con su etcd-client. Verifica firma (clave compilada), versión >
   última aplicada, `despliegue_id` propio y límites. Si cuadra, aplica de forma atómica, registra `[INFRA-CAMBIO]`
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
- Spoofing por interfaz o MAC (D2): alerta nuclear, no se protege.
- Host (Falco): toda operación sobre el set protegido que no venga del agente, y toda escritura en el manifiesto en
  disco o en el binario del agente.
- Wazuh: FIM del manifiesto en disco.
- Vault: audit device con la identidad y la IP de cada firma.
- Falco y Wazuh reportan a la máquina del admin, que concentra la consola, el etcd-server del despliegue y la
  vigilancia.

**D9. La herramienta.** `argus-infra` se instala solo en la máquina del admin, nunca en un componente. Puede ser
código abierto como el resto de aRGus: la seguridad sale de la clave y de la vigilancia, no de ocultar el código
(Kerckhoffs).

**D10. Plantilla de despliegue.** Un fichero de despliegue, generado por Jenkins desde una plantilla certificada por
nosotros, fija: máquina admin, CIDR autorizado, `hospital_id`, `despliegue_id`, límites de prefijo por categoría. Solo
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
- Proteger .20 implica que un paquete falsificado con origen .20 no se bloquea, solo se alerta; lo frena la atadura a
  interfaz/MAC (D2) y el antispoofing de entrada.
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

- **8e.1** firewall-acl-agent: categoría `infraestructura`, carga del manifiesto firmado (Ed25519 con libsodium, clave
  pública compilada en dos ranuras), versión monótona, límites de prefijo, aplicación atómica al set del kernel,
  candado (D6), último verificado y avisos periódicos (D7), contadores por categoría. Fuera `ddos_protegidos` de
  `firewall.json`. Tests.
- **8e.2** Vault: motor transit, clave ed25519 no exportable por hospital, política `argus-infra-admin`,
  `token_bound_cidrs`, audit device. Vagrantfile y Ansible.
- **8e.3** `argus-infra` y las rutas del manifiesto en el etcd-server (`GET`/`PUT`, PUT solo con certificado de admin,
  verificación de firma, versión y despliegue). Fichero de despliegue del lab.
- **8e.4** Comprobación continua kernel ↔ manifiesto, alertas de spoofing por interfaz y MAC, versión en el latido y en
  `pipeline-status`, reglas Falco (en la VM hardened-x86, `check-prod-falco`) y Wazuh.
- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.

## 6. Diseño fino de 8e.1 (borrador para revisar DAY318, antes del parcheador)

**Formato del manifiesto en disco y en etcd** (lo que se firma son bytes exactos, no un JSON reformateado):

```json
{
  "formato": "argus-protegidos/v1",
  "carga_b64": "<base64 de los bytes exactos de la carga>",
  "firma": "vault:v1:<base64 de la firma Ed25519 sobre esos bytes>",
  "ranura_clave": "actual"
}
```

Carga (JSON):

```json
{
  "esquema": 1,
  "hospital_id": "lab",
  "despliegue_id": "lab-vagrant",
  "version": 1,
  "emitido_utc": "2026-11-05T08:00:00Z",
  "firmante": "<entidad de Vault del admin>",
  "motivo": "alta inicial del laboratorio",
  "hash_anterior": "<sha256 de la carga anterior, vacío en la versión 1>",
  "limites": { "infraestructura": 32, "intranet": 24, "dmz": 24, "externos_criticos": 32 },
  "entradas": [
    { "categoria": "infraestructura", "cidr": "192.168.100.20/32", "interfaz": "eth2", "mac": "", "motivo": "VM etcd: etcd, etcd-server, Vault" },
    { "categoria": "intranet", "cidr": "192.168.100.61/32", "interfaz": "eth2", "mac": "", "motivo": "protegido de prueba DAY300" }
  ]
}
```

(`limites` en IPv4; los de IPv6 se añaden en la misma estructura cuando se cierre DEBT-FW-IPV6-SETS-001.)

**Campos nuevos en `firewall.json`** (el JSON sigue siendo la ley para lo que no es la lista):

| Campo | Rango | Defecto | Doc |
|---|---|---|---|
| `protegidos.manifiesto_cache` | ruta absoluta | `/var/lib/ml-defender/firewall/protegidos.manifiesto` | último manifiesto verificado |
| `protegidos.consulta_sec` | [5, 3600] | 30 | cada cuánto se pide el manifiesto al etcd-server |
| `protegidos.comprobacion_kernel_sec` | [5, 3600] | 30 | comprobación kernel ↔ manifiesto |
| `protegidos.aviso_sec` | [30, 86400] | 300 | ritmo del aviso periódico mientras no haya manifiesto verificado |
| `protegidos.despliegue_id` | cadena [1, 64], `[a-z0-9-]` | — | sin valor sano por defecto: si falta, no hay manifiesto verificado (candado cerrado) y se avisa |

**Mensajes de log** (etiquetas para buscar):
- `[PROTEGIDOS-MANIFIESTO] verificado version=N firmante=... despliegue=... entradas=E (infraestructura=a intranet=b dmz=c externos_criticos=d)`
- `[PROTEGIDOS-MANIFIESTO-RECHAZADO] motivo=firma|version|despliegue|limite|formato ...` (se conserva el último verificado)
- `[PROTEGIDOS-SIN-MANIFIESTO] mitigacion real BLOQUEADA (candado); sombra` (periódico)
- `[INFRA-CAMBIO] version A -> B firmante=... altas=... bajas=...`
- `[PROTEGIDOS-DIVERGENCIA] kernel != manifiesto: ...` / `[PROTEGIDOS-SPOOFING] origen=... interfaz|mac ...`
- `protegidos:` gana `infraestructura=N`.

**Tests de 8e.1:** firma válida; firma de otra clave; carga alterada un byte; versión igual y menor; otro
`despliegue_id`; prefijo más amplio que el límite (en `infraestructura`, /31); entrada sin interfaz; cache
ausente/alterada al arrancar; candado con `habilitada=true` y sin manifiesto; último verificado conservado tras un
rechazo en caliente.

**Puntos abiertos para DAY318 (medir o decidir antes del parcheador):**
1. El set del kernel: reutilizar `ml_defender_whitelist` (lo que ya existe y ya está en la cadena de iptables con
   `RETURN`) o crear uno nuevo. Recomendación: reutilizar (no reinventar) y que solo el agente lo escriba.
2. El defecto RFC 1918 de DAY300: con el candado (D6), sin manifiesto verificado no hay bloqueo real, así que ese
   defecto amplio deja de hacer falta para la seguridad. Recomendación: borrarlo. Es una decisión de DAY300 y la
   revisa Alonso.
3. Cómo entra la clave pública en la compilación (opción de CMake que lee un fichero que el bootstrap trae de Vault;
   sin él, la compilación falla con un mensaje claro: aquí no hay defecto sano posible) y el orden en el bootstrap
   (VM etcd y clave transit antes de compilar el firewall).
4. El nombre de la interfaz del lab en las entradas (`eth2` en el defender según el Vagrantfile): medir en la VM.
