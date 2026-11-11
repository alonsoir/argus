#!/usr/bin/env python3
# [PROTEGIDOS-VIGIA-D320] docs de 8e.4a: ADR-060 (plan de 8e.4 en cuatro commits; sección 7 nueva con el diseño fino
# H-A..H-J, la precisión de dry_run, la medida de H-B, 8e.4a y C7; tabla de campos y mensajes de log al día) y BACKLOG
# (sección DAY320 de 8e.4a: medidas del banco y del lab, fallos de predicción, hallazgos, pendiente). Solo documentación.
#
# Uso, desde la raíz del repo:
#   python3 -I scripts/etcd_ha/d320_docs_8e4a.py --check
#   python3 -I scripts/etcd_ha/d320_docs_8e4a.py --apply
# Todo o nada: comprueba el sha256 de cada fichero (y que los nuevos no existan) antes de escribir ninguno.
# Idempotente: si todos tienen ya el sha256 de después, no toca nada. Salidas: 0 bien, 1 no aplicable, 2 uso.
import hashlib, json, os, sys, tempfile

CAMBIOS = json.loads(r"""[
 {
  "ruta": "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md",
  "antes": "810debb5c61455e8e8f03783b39460c7bd56d417934b572a40081f94399e3bfd",
  "despues": "023e2dc95aed7e40d5b9f29b4eb76b899b41a9c958581f63dc347bea2f50460b",
  "bloques": [
   {
    "viejo": "  `pipeline-status`, reglas Falco (en la VM hardened-x86, `check-prod-falco`) y Wazuh. Falco y Wazuh avisan también\n  cuando la partición del audit de Vault (`/var/log/vault`) pasa de un umbral (p. ej. 75 %), con prioridad en el log,\n  y cuando falla uno de los dos audit devices (Alonso DAY318: es su trabajo avisarnos).\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n\n",
    "nuevo": "  `pipeline-status`, reglas Falco (en la VM hardened-x86, `check-prod-falco`) y Wazuh. Falco y Wazuh avisan también\n  cuando la partición del audit de Vault (`/var/log/vault`) pasa de un umbral (p. ej. 75 %), con prioridad en el log,\n  y cuando falla uno de los dos audit devices (Alonso DAY318: es su trabajo avisarnos). Diseño fino cerrado DAY320\n  (sección 7), en cuatro commits:\n  - **8e.4a** (hecho, fe4c94d3) el vigía kernel ↔ manifiesto y C7 en el E2E de la mitigación real.\n  - **8e.4b** antispoofing por interfaz y MAC en `raw PREROUTING` (H-B a H-G).\n  - **8e.4c** versión del manifiesto en el latido y en `pipeline-status` (H-H).\n  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J).\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n\n"
   },
   {
    "viejo": "| `protegidos.manifiesto_cache` | ruta absoluta | `/var/lib/ml-defender/firewall/protegidos.manifiesto` | último manifiesto verificado |\n| `protegidos.aviso_sec` | [30, 86400] | 300 | aviso periódico y nueva verificación de la caché |\n| `protegidos.comprobacion_kernel_sec` | [5, 3600] | 30 | comprobación kernel ↔ manifiesto (8e.4) |\n| `protegidos.consulta_sec` | [5, 3600] | 30 | cada cuánto se pide el manifiesto al etcd-server (8e.3) |\n\n",
    "nuevo": "| `protegidos.manifiesto_cache` | ruta absoluta | `/var/lib/ml-defender/firewall/protegidos.manifiesto` | último manifiesto verificado |\n| `protegidos.aviso_sec` | [30, 86400] | 300 | aviso periódico y nueva verificación de la caché |\n| `protegidos.comprobacion_kernel_sec` | [5, 3600] | 30 | vigía kernel ↔ manifiesto (8e.4a, hecho DAY320) |\n| `protegidos.consulta_sec` | [5, 3600] | 30 | cada cuánto se pide el manifiesto al etcd-server (8e.3) |\n\n"
   },
   {
    "viejo": "- `[PROTEGIDOS-SET-TIPO] el set <nombre> existe con tipo <tipo> (se espera hash:net,iface): ...`\n- `[INFRA-CAMBIO] version A -> B firmante=... altas=... bajas=...`\n- `[PROTEGIDOS-DIVERGENCIA] kernel != manifiesto: ...` / `[PROTEGIDOS-SPOOFING] origen=... interfaz|mac ...` (8e.4)\n- `protegidos:` gana `infraestructura=N`.\n\n",
    "nuevo": "- `[PROTEGIDOS-SET-TIPO] el set <nombre> existe con tipo <tipo> (se espera hash:net,iface): ...`\n- `[INFRA-CAMBIO] version A -> B firmante=... altas=... bajas=...`\n- `[PROTEGIDOS-DIVERGENCIA] set <set> != manifiesto version N: sobran=[...] faltan=[...]` y\n  `[PROTEGIDOS-DIVERGENCIA] reglas: <motivo>`; `[PROTEGIDOS-RECONCILIADO] ...` (comprobado tras volver a leer);\n  `[PROTEGIDOS-VIGIA]` (arranque, resumen `comprobaciones= divergencias= reconciliaciones= fallos=` cada `aviso_sec`,\n  aviso de `dry_run` y `ERROR` si no se pudo reconciliar) (8e.4a, DAY320)\n- `[PROTEGIDOS-SPOOFING] origen=... interfaz|mac ...` (8e.4b)\n- `protegidos:` gana `infraestructura=N`.\n\n"
   },
   {
    "viejo": "`INFRA-INCOMPLETA`; set existente de otro tipo y órdenes del `swap` (en dry_run); barrera por IP con un origen\nprotegido que llega por otra interfaz.\n",
    "nuevo": "`INFRA-INCOMPLETA`; set existente de otro tipo y órdenes del `swap` (en dry_run); barrera por IP con un origen\nprotegido que llega por otra interfaz.\n\n## 7. Diseño fino de 8e.4 (cerrado DAY320)\n\nDecisiones de Alonso DAY320 (H-A a H-J), medidas antes de decidir donde se podía. Reglas que lo cruzan todo: el JSON es\nla ley (cada campo nuevo se lee de ahí y, si falta o está mal formado, defecto del código con aviso; todo al log); toda\noperación nueva o modificada lleva un test que pruebe que hace su trabajo; coste por paquete O(1), como mucho\nO(log n); las reglas, ficheros y procesos que vigilan Wazuh y Falco van en su configuración, no en el código; si algo\nno cuadra, se reconcilia.\n\n**Medido antes de decidir (DAY320, en el código):** nada de 8e.4 existía; el latido solo lleva `{timestamp, status}` y\nel etcd-server ignora su cuerpo; Falco solo está en `hardened-x86` y sus reglas van en un heredoc de `setup-falco.sh`;\nde Wazuh no hay reglas de aRGus; la VM etcd no tiene agente Wazuh ni MAC fija; `/var/log/vault` está en la raíz.\n\n**`dry_run` (precisado DAY320).** Con `operation.dry_run=true` el agente no escribe nada en el kernel (regla de\nDAY302): ni set ni cadena. El vigía no compara y lo dice al arrancar y cada `aviso_sec`. Con `dry_run=false` y el\ncandado cerrado o la mitigación deshabilitada, el vigía compara y reconcilia y el antispoofing (8e.4b) solo cuenta; con\n`dry_run=false`, mitigación habilitada y manifiesto verificado, el antispoofing descarta. La hipótesis de este ADR (con\nla mitigación real, ningún protegido entra en el blacklist) solo se prueba con `dry_run=false` y `habilitada=true`\n(Alonso DAY320): se mide así en EMECAS (C7, abajo) y el lab sigue arrancando en sombra de serie hasta que EMECAS+++ pase\nentero (\"si la mitigación real bloquea a clientes legítimos que no estén en el manifiesto, estamos haciendo algo mal:\nmidamos primero\").\n\n- **H-A** El vigía reconcilia (no solo avisa): lo no firmado pierde la protección y lo que falta se repone.\n- **H-B** Antispoofing con coste constante por paquete: seis reglas fijas en `raw PREROUTING` sobre sets (`hash:net`\n  de las redes protegidas, `hash:net,iface`, `hash:ip` de las IPs con MAC y `hash:ip,mac`), no una regla por entrada.\n  Medido DAY320 en el defender (`scripts/etcd_ha/d320_medir_antispoof.sh`, v2: 19/19): el no protegido sale en la\n  segunda regla con un solo lookup; spoofing por interfaz y por MAC contados exactos; un paquete con interfaz y MAC\n  malas cuenta una sola vez; el DROP en raw no deja pasar nada a mangle; `iptables-restore --noflush` rehace las\n  cadenas de golpe; lectura del vigía 2-3 ms; ipset 7.17 tiene `hash:ip,mac`. Las reglas 3 y 5 saltan con `-g`\n  (goto): con `-j`, en modo solo contar, el paquete volvía y seguía por la cadena (medido en la v1). Los contadores por\n  entrada de ipset suben con cualquier coincidencia, también las negadas: los totales salen de las reglas y la\n  identidad del paquete del LOG.\n- **H-C** Las reglas del antispoofing solo cuentan mientras la mitigación no sea real (ver `dry_run` arriba); con ella,\n  DROP.\n- **H-D** Si la interfaz de una entrada no casa con la ruta del kernel (`ip route get`), no se instala su DROP y\n  `[PROTEGIDOS-RUTA]` es alarma periódica: un DROP por interfaz equivocada sería el DoS autoinfligido otra vez. `-i lo`\n  siempre exento (un `intranet /24` suele contener la IP del propio firewall).\n- **H-E** Evidencia de spoofing: `LOG` con límite (medido: 5 líneas con `--limit-burst 5`, con la MAC de origen) al\n  journal; lo recoge Wazuh. Sin NFLOG ni hilo nuevo.\n- **H-F** `rp_filter` se lee y se informa, no se cambia (medido DAY320: 0 en todas las interfaces del defender).\n- **H-G** MAC fija de la VM etcd en el Vagrantfile y en la plantilla del lab, para probar en EMECAS los dos casos: el\n  client falsificando .20 (entra por `eth2`: lo caza la MAC) y un veth en un netns del defender (lo caza la interfaz).\n- **H-H** Datos de latido genéricos y validados en el etcd-client; el firewall manda `protegidos_version`; el\n  etcd-server lo guarda en el registro y `pipeline-status` marca el firewall desfasado.\n- **H-I** Agente Wazuh en la VM etcd (disco de `/var/log/vault` al 75 % y fallos de los audit devices).\n- **H-J** 8e.4d dentro del PR1.\n\n**8e.4a, el vigía (hecho DAY320, fe4c94d3).** Cada `comprobacion_kernel_sec`, en el bucle principal (fuera del camino\ndel paquete), `vigia_protegidos_paso` (`firewall/protegidos_vigia.hpp`) compara con lo vigente:\n- K1 el set existe y es `hash:net,iface` (si falta, se crea con la misma configuración que al arrancar);\n- K2 su contenido (`IPSetWrapper::list_entries_opciones`: entradas con sus opciones, sin contadores) es exactamente el\n  de las entradas IPv4 del vigente, en forma canónica (red con los bits de host a cero y prefijo explícito: el kernel\n  normaliza y omite `/32`). Una entrada de más, de menos, por otra interfaz o con opciones (`nomatch` anularía la\n  exención) es divergencia. Sin vigente, el set tiene que estar vacío. O(n) con conjuntos hash;\n- K3 la cadena: un único salto INPUT → cadena en la posición 1 y dentro exactamente protegidos `src,src` RETURN y\n  blacklist DROP, en ese orden (`setup_base_rules`).\nSi no cuadra, se reconcilia (sustitución atómica del set; `setup_base_rules` para la cadena) y se vuelve a leer: solo\ncuenta como reconciliado lo que se comprueba. **Set ajeno**: si existe con otro tipo, no se destruye y la cadena se\nrehace sin el RETURN. Medido DAY320: iptables acepta `--match-set <set hash:ip> src,src` e ignora la dimensión de más,\nasí que el RETURN eximiría un contenido que nadie ha firmado; quitarlo no pone en riesgo a nadie (el agente nunca mete a\nun protegido en el blacklist; la barrera de usuario protege por IP) y vuelve en cuanto el set está bien.\n\nMedido DAY320: banco (Debian 12, GCC 12.2, native y skylake, dos pasadas) 119/119 y 0 avisos del código;\n`test_protegidos_vigia` 42/42 (con wrappers falsos que dicen \"hecho\" sin hacerlo); `test_protegidos_vigia_root` 34/34\n(kernel real, S1-S9); 7 mutaciones cazadas. Lab: `pipeline-build` rc 0; `test-firewall` 95/95; `test-firewall-e2e`\nPASA (24, 0 saltados); `lab-e2e-vigia` PASA (E1 6 s, E2-E4 25-26 s, límite 35; kernel igual que al empezar; 0 errores).\n\n**C7 (la hipótesis del DoS autoinfligido, medida con la mitigación real).** `lab-e2e-mitigacion` (`dry_run=false`,\n`habilitada=true`, ataque NTP de .50 y .61) exige la VM etcd arriba y .20 en el set de protegidos, y muestrea cada\nsegundo el blacklist y los contadores por entrada del set. DAY320: C1-C5 y **C7 PASA**: .20 en 0 de 459 muestras del\nblacklist; su entrada del set de protegidos de 223 a 529 paquetes durante los ataques. En la misma corrida `ddos_v2`\nvolvió a marcar DROP a la VM etcd (`[SOMBRA-DDOS] protegidos: ... infraestructura=2`, DEBT-DDOS-V2-NTP-CLIENTE-001):\nel DoS autoinfligido del DAY317 se produjo y la barrera lo paró.\n"
   }
  ],
  "modo": null
 },
 {
  "ruta": "docs/BACKLOG.md",
  "antes": "401e4ed4c189ffc82cef9db77adeda9aee6a3029682759ef6a0b374b092fa070",
  "despues": "6b659ea1155d6e9be86a6f0163c93efab72b100197e938ee01e67ff241113d8d",
  "bloques": [
   {
    "viejo": "pipeline-status, Falco/Wazuh, alarma de disco del audit de Vault al 75 %), 8e.5 (bootstrap con `argus-infra init --si`,\n`d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1.\n",
    "nuevo": "pipeline-status, Falco/Wazuh, alarma de disco del audit de Vault al 75 %), 8e.5 (bootstrap con `argus-infra init --si`,\n`d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1.\n\n---\n\n## DAY320 — paso 8e.4a hecho y diseño fino de 8e.4 [PROTEGIDOS-VIGIA-D320]\n\nCommit fe4c94d3 (8e.4a). Diseño fino de 8e.4 (H-A..H-J, decisiones de Alonso DAY320) y precisión de `dry_run`:\nADR-060, sección 7. Cuatro commits: 8e.4a vigía (hecho), 8e.4b antispoofing, 8e.4c versión en el latido, 8e.4d\nWazuh/Falco (dentro del PR1).\n\n### Medida previa de 8e.4b (H-B), en el defender\n`scripts/etcd_ha/d320_medir_antispoof.sh` (solo mide, lo deja todo como estaba; entra en el commit de 8e.4b): v1 16/17,\nv2 19/19. ipset 7.17 con `hash:ip,mac`; seis reglas fijas en raw PREROUTING clasifican no protegido / spoofing por\ninterfaz / por MAC / bueno con coste constante; DROP en raw efectivo; `iptables-restore --noflush` atómico; 2-3 ms por\nlectura; `rp_filter` 0 en todas las interfaces. Fallo de la v1 = fallo de predicción: con `-j` en modo solo contar el\npaquete seguía por la cadena (doble cuenta posible en sombra); la v2 usa `-g`.\n\n### Medido en el banco (Debian 12, GCC 12.2, banco del firewall rehecho DAY320)\n- Base 117/117. 8e.4a: native y skylake, dos pasadas, 119/119; 0 avisos del código (los 3 avisos de siempre son del\n  enlazador por libsodium .so.23/.so.26).\n- `test_protegidos_vigia` 42/42 (puro; wrappers falsos); `test_protegidos_vigia_root` 34/34 (kernel real, S1-S9).\n- Mutaciones: m1 ignorar lo que sobra, m2 ignorar la interfaz, m3 ignorar las opciones, m4 no mirar el orden de la\n  cadena, m5 no releer el set, m6 no releer las reglas, m7 no quitar el RETURN con un set ajeno: 7/7 cazadas.\n- Fallos de predicción, parados y corregidos antes del lab: (1) con un set ajeno de tipo `hash:ip`, iptables acepta\n  `--match-set ... src,src` y el RETURN seguía eximiendo su contenido: el vigía rehace la cadena sin RETURN; (2) m5\n  sobrevivía (la sustitución real nunca \"miente\"): el paso pasó a plantilla para probarlo con wrappers falsos.\n\n### Medido en el lab (PROFILE=production)\n`pipeline-build` rc 0; `test-firewall` 95/95 (con `test_protegidos_vigia`); `test-firewall-e2e` PASA (24 tests, 0\nsaltados; `test_protegidos_vigia_root` 34/34). `lab-e2e-vigia` PASA: V0 sin divergencias; E1 (entrada de más) 6 s,\nE2 (RETURN borrado) 26 s, E3 (`nomatch`) 25 s, E4 (regla ajena delante del salto) 25 s, límite 35; set y cadena iguales\nque al empezar; 0 `[PROTEGIDOS-VIGIA] ERROR`; JSON restaurado (cmp 0). `lab-e2e-mitigacion` PASA con C7: .20 en 0 de\n459 muestras del blacklist y su entrada del set de protegidos 223 -> 529 paquetes durante los ataques; en la misma\ncorrida `[SOMBRA-DDOS] protegidos: ... infraestructura=2`: `ddos_v2` volvió a marcar DROP a la VM etcd (el DoS\nautoinfligido del DAY317) y la barrera lo paró con la mitigación real.\n\n### Hallazgos DAY320 (8e.4a)\n- Las guardas de `d302_mitigacion_e2e.sh` y `d320_vigia_e2e.sh` exigen `firewall.json` sin cambios pendientes (lo\n  modifican durante la prueba y lo restauran con cmp): los E2E que tocan el JSON se lanzan después del commit.\n- `LAB_E2E_DIA` vale `day303` por defecto: las corridas de hoy quedaron en `logs/lab/day303/`. Funciona, pero confunde;\n  sin decidir.\n- `make test-firewall-e2e` va por la etiqueta `e2e`: un test de root nuevo entra solo en el gate.\n\n### Pendiente (por orden)\n8e.4b (antispoofing; H-B a H-G, con `d320_medir_antispoof.sh`), 8e.4c (versión en el latido y `pipeline-status`),\n8e.4d (Wazuh y Falco, con su configuración en ficheros propios), docs de cada uno, 8e.5 (bootstrap con\n`argus-infra init --si`, `d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++\nPROFILE=production y cierre del PR1.\n"
   }
  ],
  "modo": null
 }
]""")

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d320_docs_8e4a.py --check|--apply  (desde la raíz del repo)", file=sys.stderr); return 2
    aplicar = sys.argv[1] == "--apply"
    hechos, nuevos = 0, {}
    for c in CAMBIOS:
        r = c["ruta"]
        existe = os.path.isfile(r)
        b = open(r, "rb").read() if existe else None
        if existe and sha(b) == c["despues"]:
            hechos += 1; print(f"[YA APLICADO] {r}"); continue
        if c["antes"] is None:
            if existe:
                print(f"[NO APLICABLE] {r} ya existe con otro contenido (sha256={sha(b)})"); return 1
            if not os.path.isdir(os.path.dirname(r) or "."):
                print(f"[NO APLICABLE] no existe el directorio de {r} (¿estás en la raíz del repo?)"); return 1
            n = c["contenido"].encode("utf-8")
            print(f"[APLICABLE] {r} (nuevo, {len(n)} B)")
        else:
            if not existe:
                print(f"[NO APLICABLE] no existe {r} (¿estás en la raíz del repo?)"); return 1
            if sha(b) != c["antes"]:
                print(f"[NO APLICABLE] {r} sha256={sha(b)}\n  esperado antes  ={c['antes']}\n  esperado después={c['despues']}"); return 1
            t = b.decode("utf-8")
            for i, bl in enumerate(c["bloques"], 1):
                if t.count(bl["viejo"]) != 1:
                    print(f"[NO APLICABLE] {r}: el bloque {i} aparece {t.count(bl['viejo'])} veces"); return 1
                t = t.replace(bl["viejo"], bl["nuevo"])
            n = t.encode("utf-8")
            print(f"[APLICABLE] {r} {c['antes'][:16]} -> {c['despues'][:16]} ({len(c['bloques'])} bloques)")
        if sha(n) != c["despues"]:
            print(f"[NO APLICABLE] {r}: el resultado no da el sha256 esperado"); return 1
        nuevos[r] = (n, c.get("modo"))
    if hechos and nuevos:
        print(f"[NO APLICABLE] estado mezclado: {hechos} ya aplicados y {len(nuevos)} no; no se toca nada"); return 1
    if not nuevos:
        print("[YA APLICADO] nada que hacer"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(nuevos)} ficheros); nada escrito"); return 0
    for r, (n, modo) in nuevos.items():
        d = os.path.dirname(r) or "."
        m = (os.stat(r).st_mode & 0o7777) if os.path.exists(r) else (modo or 0o644)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche.")
        with os.fdopen(fd, "wb") as f: f.write(n); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, m); os.replace(tmp, r)
    for c in CAMBIOS:
        s = sha(open(c["ruta"], "rb").read())
        if s != c["despues"]:
            print(f"[ERROR] {c['ruta']} quedó con sha256={s}"); return 1
        print(f"[APLICADO] {c['ruta']} sha256={s}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
