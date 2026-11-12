#!/usr/bin/env python3
# d318_docs_diseno_8e.py — DAY318: cierra el diseño fino de 8e en ADR-060 (sección 6 y precisiones en D1, D2, D3, D5,
# D8, D10, consecuencias y plan) y añade al final de docs/BACKLOG.md la sección [MANIFIESTO-PROTEGIDOS-D318] con las
# decisiones de Alonso (D-A a D-I), DEBT-FW-SPOOFING-ORIGENES-AJENOS-001 y los hallazgos del día.
# Uso (Mac, raíz del repo):  python3 scripts/etcd_ha/d318_docs_diseno_8e.py --check|--apply <raíz>
# Todo o nada e idempotente: cada cambio se aplica si su texto viejo aparece una vez, se da por hecho si ya está el
# nuevo, y cualquier otro caso para sin escribir nada. Imprime el sha256 de cada fichero antes y después.
import hashlib
import os
import sys

ADR = "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md"
BACKLOG = "docs/BACKLOG.md"
MARCA_BACKLOG = "[MANIFIESTO-PROTEGIDOS-D318]"

CAMBIOS_ADR = [
    ("título",
     "# ADR-060 — Manifiesto firmado de rangos protegidos, uno por despliegue\n",
     "# ADR-060 — Manifiesto firmado de rangos protegidos, uno por hospital\n"),
    ("estado",
     "| **Estado** | Propuesto (decisiones de Alonso DAY317; diseño fino de 8e.1 por revisar DAY318) |\n",
     "| **Estado** | Aceptado (decisiones de Alonso DAY317; diseño fino cerrado DAY318, sección 6) |\n"),
    ("D1",
     "**D1. Un manifiesto por despliegue, en un solo sitio.** Todas las listas protegidas salen de un único manifiesto\n"
     "firmado por despliegue, con cuatro categorías:",
     "**D1. Un manifiesto por hospital, en un solo sitio.** Todas las listas protegidas salen de un único manifiesto\n"
     "firmado por hospital, con sus plantas dentro (DAY318, sección 6), con cuatro categorías:"),
    ("D2 interfaz",
     "- `interfaz` obligatoria: un paquete con origen protegido que llega por otra interfaz no se protege nunca y dispara\n"
     "  la alerta de spoofing (vale aunque haya routers por medio).\n",
     "- `interfaz` obligatoria: un paquete con origen protegido que llega por otra interfaz es falso por construcción: no\n"
     "  recibe la exención del kernel, se descarta en `raw PREROUTING` (antispoofing, D8, 8e.4) y dispara la alerta de\n"
     "  spoofing (vale aunque haya routers por medio). Precisión DAY318: la barrera de usuario (suscriptor y\n"
     "  `BatchProcessor`) protege por IP siempre, venga por donde venga; si no, falsificar el origen de un protegido\n"
     "  bastaría para que aRGus lo bloqueara, que es el DoS que este ADR evita. Un host con varias interfaces legítimas\n"
     "  lleva una entrada por interfaz.\n"),
    ("D3 plantas",
     "Lo que separa las plantas es el `despliegue_id`\n  del manifiesto.",
     "Lo que separa las plantas es su sección dentro\n  del manifiesto (`plantas.<despliegue_id>`)."),
    ("D3 ranuras",
     "Dos ranuras compiladas (actual y siguiente) para rotar sin dejar a los\n"
     "  firewalls sin poder verificar mientras llega la imagen nueva.\n",
     "Dos ranuras compiladas (actual y siguiente) para rotar sin dejar a los\n"
     "  firewalls sin poder verificar mientras llega la imagen nueva. El agente prueba las dos; el sobre no dice cuál\n"
     "  (DAY318).\n"),
    ("D5 etcd-server",
     "El etcd-server verifica la firma, el\n   `despliegue_id` y la versión",
     "El etcd-server verifica la firma, el\n   `hospital_id` y la versión"),
    ("D5 firewall",
     "última aplicada, `despliegue_id` propio y límites.",
     "última aplicada, `hospital_id` propio, que esté su planta y límites."),
    ("D8 spoofing",
     "- Spoofing por interfaz o MAC (D2): alerta nuclear, no se protege.\n",
     "- Spoofing por interfaz o MAC (D2): alerta nuclear y descarte en `raw PREROUTING` generado desde el manifiesto: una\n"
     "  regla por entrada (origen protegido que no entra por su interfaz = DROP), con contador por regla, resumen\n"
     "  periódico y muestra de los primeros paquetes como evidencia. Postura de partida (Alonso DAY318): agresiva y con\n"
     "  todo registrado; si resulta demasiado dura, se mide y se suaviza.\n"),
    ("D10 plantas",
     "CIDR autorizado, `hospital_id`, `despliegue_id`, límites",
     "CIDR autorizado, `hospital_id`, las plantas (`despliegue_id`), límites"),
    ("consecuencias spoofing",
     "- Proteger .20 implica que un paquete falsificado con origen .20 no se bloquea, solo se alerta; lo frena la atadura a\n"
     "  interfaz/MAC (D2) y el antispoofing de entrada.\n",
     "- Proteger .20 implica que aRGus nunca bloquea la IP .20, aunque llegue tráfico falsificado con ese origen. Si entra\n"
     "  por otra interfaz lo descarta el antispoofing (D2, D8); desde el mismo segmento solo lo frena la MAC, cuando la\n"
     "  entrada la lleva. Falsificar orígenes ajenos con herramientas de fabricación o manipulación de paquetes (Scapy,\n"
     "  hping3, Polymorph) no se resuelve desde el borde del hospital: DEBT-FW-SPOOFING-ORIGENES-AJENOS-001.\n"),
    ("plan 8e.1 y 8e.2",
     "- **8e.1** firewall-acl-agent: categoría `infraestructura`, carga del manifiesto firmado (Ed25519 con libsodium, clave\n"
     "  pública compilada en dos ranuras), versión monótona, límites de prefijo, aplicación atómica al set del kernel,\n"
     "  candado (D6), último verificado y avisos periódicos (D7), contadores por categoría. Fuera `ddos_protegidos` de\n"
     "  `firewall.json`. Tests.\n"
     "- **8e.2** Vault: motor transit, clave ed25519 no exportable por hospital, política `argus-infra-admin`,\n"
     "  `token_bound_cidrs`, audit device. Vagrantfile y Ansible.\n",
     "Orden de los commits (DAY318): 8e.2 va antes que 8e.1, para que el firewall compile en cada commit (desde 8e.1 no\n"
     "compila sin la clave pública). EMECAS se pasa al final, con todos los commits de la rama.\n"
     "\n"
     "- **8e.2** Vault: motor transit, clave ed25519 no exportable por hospital, política `argus-infra-admin`,\n"
     "  `token_bound_cidrs`, audit device. Vagrantfile y Ansible. El bootstrap trae la clave pública al defender.\n"
     "- **8e.1** firewall-acl-agent: categoría `infraestructura`, manifiesto por hospital con sus plantas, carga desde la\n"
     "  caché y verificación (Ed25519 con libsodium, clave pública compilada en dos ranuras), versión monótona, límites de\n"
     "  prefijo, set `hash:net,iface` aplicado de forma atómica con `ipset swap`, candado (D6), último verificado y avisos\n"
     "  periódicos (D7), aviso si falta el plano de control, contadores por categoría. Fuera `ddos_protegidos`,\n"
     "  `ipsets.whitelist` y el defecto RFC 1918. Tests.\n"),
    ("plan 8e.3",
     "verificación de firma, versión y despliegue). Fichero de despliegue del lab.\n",
     "verificación de firma, versión y hospital); el firewall lo pide cada `protegidos.consulta_sec`. Fichero de\n"
     "  despliegue del lab.\n"),
    ("plan 8e.4",
     "- **8e.4** Comprobación continua kernel ↔ manifiesto, alertas de spoofing por interfaz y MAC, versión en el latido y en\n",
     "- **8e.4** Comprobación continua kernel ↔ manifiesto, antispoofing en `raw PREROUTING` generado desde el manifiesto,\n"
     "  alertas de spoofing por interfaz y MAC, versión en el latido y en\n"),
]

SECCION6_INICIO = "## 6. Diseño fino de 8e.1 (borrador para revisar DAY318, antes del parcheador)\n"

SECCION6_NUEVA = """## 6. Diseño fino de 8e.1 (cerrado DAY318)

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
  "hospital_id": "lab",
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

**Campos nuevos en `firewall.json`** (el JSON sigue siendo la ley para lo que no es la lista):

| Campo | Rango | Defecto | Doc |
|---|---|---|---|
| `protegidos.hospital_id` | cadena [1, 64], `[a-z0-9-]` | — | sin valor sano por defecto: si falta, candado cerrado y aviso |
| `protegidos.despliegue_id` | cadena [1, 64], `[a-z0-9-]` | — | la planta de este firewall; sin valor sano por defecto: si falta, candado cerrado y aviso |
| `protegidos.set_name` | lo que acepta `is_valid_set_name` (1 a 31, `[A-Za-z0-9_-]`) | `ml_defender_protegidos` | set `hash:net,iface` del kernel |
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

**Tests de 8e.1:** firma válida con la clave actual y con la siguiente; firma de otra clave; carga alterada un byte;
versión igual y menor; otro `hospital_id`; planta ausente; prefijo más amplio que el límite (en `infraestructura`,
/31); entrada sin interfaz o con interfaz mal formada; caché ausente o alterada al arrancar; candado con
`habilitada=true` y sin manifiesto; último verificado conservado tras un rechazo en caliente; aviso
`INFRA-INCOMPLETA`; set existente de otro tipo y órdenes del `swap` (en dry_run); barrera por IP con un origen
protegido que llega por otra interfaz.
"""

BACKLOG_NUEVO = """
---

## DAY318 — Diseño fino de 8e cerrado [MANIFIESTO-PROTEGIDOS-D318]

Documento: `docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md`, sección 6 (cerrada) y precisiones en D1, D2,
D3, D5, D8, D10, consecuencias y plan. Decisiones de Alonso DAY318:
- **D-A** set nuevo `hash:net,iface` con `ipset swap` atómico; fuera `ipsets.whitelist` (medido en el defender: ipset
  v7.17, `eth2`, `src,src` y `swap` funcionan).
- **D-B** un manifiesto por hospital, con `comun` y `plantas`; solo `motivo` corto (ni ubicación ni función: sería un
  mapa del hospital); fuera el defecto RFC 1918.
- **D-C** aviso `[PROTEGIDOS-INFRA-INCOMPLETA]` si un host de `etcd.endpoints` falta en `infraestructura`; no cierra el
  candado (el hospital siempre protegido). Se compara al aplicar cada manifiesto, no por paquete.
- **D-D** 8e.2 (Vault transit) se commitea antes que 8e.1; EMECAS, al final de la rama.
- **D-E** clave pública con el patrón de ADR-025 (`-D` o fichero traído de Vault; sin ella, `FATAL_ERROR`); el
  firewall enlaza libsodium.
- **D-F** fuera `ranura_clave`: se prueban las dos ranuras.
- **D-G** la barrera de usuario protege por IP siempre; la interfaz y la MAC atan la exención del kernel y el
  antispoofing en `raw PREROUTING` generado desde el manifiesto (8e.4), con todo registrado.
- **D-H** `protegidos.consulta_sec` pasa a 8e.3; 8e.1 trabaja con la caché.
- **D-I** IPv6 como hoy: protegido en la barrera, omitido en el kernel con aviso hasta DEBT-FW-IPV6-SETS-001.

### DEBT-FW-SPOOFING-ORIGENES-AJENOS-001 — ABIERTA, permanente (nueva DAY318)
Falsificar orígenes ajenos (IPs de terceros) con herramientas de fabricación o manipulación de paquetes (Scapy,
hping3, o Polymorph de shramos, que además manipula el tráfico en tiempo de ejecución) no se resuelve desde el borde
del hospital: depende de que los operadores apliquen BCP 38. Lo falsificado con el origen de un protegido sí se cubre
(antispoofing por interfaz y MAC desde el manifiesto, 8e.4). Ideas sin medir: en TCP, que la cabeza DDoS pese solo los
orígenes con el saludo completo (`diag/ml-heads`); en la reflexión UDP el origen que se ve es el reflector real.
Postura de partida (Alonso DAY318): mejor pasarse de duros mientras se diseña y registrarlo todo; si resulta demasiado
lesivo, se mide y se suaviza. Se revisa en cada rama que toque la cabeza DDoS o el firewall.

### Hallazgos DAY318
- El aprovisionamiento del Vagrantfile pone `rp_filter=0` en todas las interfaces del defender (modo gateway). El
  antispoofing de 8e.4 no depende de él; en 8e.4 se mide si el lab lo necesita.
- `firewall-acl-agent/src/rules/*.cpp` (`whitelist_manager`, `rate_limiter`, `temporal_acl`) no se compila: código
  muerto. Sin decidir (DEBT-REPO-RESIDUOS-001).
- La barrera de usuario recorre la lista entera por cada DROP de la cabeza DDoS (no por paquete). Con miles de
  entradas, medir y cambiar a un árbol de prefijos.
- `make up` no arranca el pipeline, ni lo ha hecho nunca (git): solo `make pipeline-start`, `make bootstrap` y EMECAS.
  Un primer `pipeline-status` con la VM etcd apagada tras un `make up` no se reprodujo (la VM arrancó con un
  `vagrant up` posterior); si vuelve a pasar: `make halt`, `make up` mirando la VM `etcd`, `vagrant status`.
"""


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d318_docs_diseno_8e.py --check|--apply <raíz del repo>")
        return 2
    modo, raiz = sys.argv[1], sys.argv[2]
    rutas = {ADR: os.path.join(raiz, ADR), BACKLOG: os.path.join(raiz, BACKLOG)}
    orig = {}
    for k, p in rutas.items():
        if not os.path.isfile(p):
            print(f"FALLA: no existe {p}")
            return 1
        orig[k] = open(p, "rb").read()
        print(f"sha256 previo  {k}: {sha(orig[k])}")
    adr = orig[ADR].decode("utf-8")
    hechos, pendientes, errores = [], [], []
    for nombre, viejo, nuevo in CAMBIOS_ADR:
        nv, nn = adr.count(viejo), adr.count(nuevo)
        if nv == 1:
            adr = adr.replace(viejo, nuevo)
            pendientes.append(nombre)
        elif nv == 0 and nn >= 1:
            hechos.append(nombre)
        else:
            errores.append(f"{nombre}: texto viejo {nv} veces, nuevo {nn} veces")
    i = adr.find(SECCION6_INICIO)
    if i >= 0 and adr.count(SECCION6_INICIO) == 1:
        adr = adr[:i] + SECCION6_NUEVA
        pendientes.append("sección 6")
    elif adr.endswith(SECCION6_NUEVA):
        hechos.append("sección 6")
    else:
        errores.append("sección 6: no aparece el borrador ni la versión cerrada al final")
    bl = orig[BACKLOG].decode("utf-8")
    nm = bl.count(MARCA_BACKLOG)
    if nm == 0:
        bl = bl + ("" if bl.endswith("\n") else "\n") + BACKLOG_NUEVO
        pendientes.append("BACKLOG")
    elif nm == 1 and bl.endswith(BACKLOG_NUEVO):
        hechos.append("BACKLOG")
    else:
        errores.append(f"BACKLOG: la marca {MARCA_BACKLOG} aparece {nm} veces sin coincidir con la sección esperada")
    print(f"ya aplicados ({len(hechos)}): {', '.join(hechos) or '-'}")
    print(f"por aplicar  ({len(pendientes)}): {', '.join(pendientes) or '-'}")
    if errores:
        for e in errores:
            print(f"FALLA: {e}")
        print("RESULTADO: FALLA (no se ha escrito nada)")
        return 1
    nuevos = {ADR: adr.encode("utf-8"), BACKLOG: bl.encode("utf-8")}
    if modo == "--apply":
        for k, p in rutas.items():
            if nuevos[k] != orig[k]:
                with open(p + ".d318tmp", "wb") as f:
                    f.write(nuevos[k])
                os.replace(p + ".d318tmp", p)
    for k in rutas:
        estado = "igual" if nuevos[k] == orig[k] else ("escrito" if modo == "--apply" else "cambiaría")
        print(f"sha256 final   {k}: {sha(nuevos[k])} ({estado})")
    print("RESULTADO: PASA" + (" (solo comprobación)" if modo == "--check" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
