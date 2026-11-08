#!/usr/bin/env python3
# [PROTEGIDOS-ANTISPOOF-D320] docs de 8e.4b: ADR-060 (8e.4b hecho en el plan; campos protegidos.antispoof.* en la tabla;
# mensajes de log del antispoofing; sección 7: el antispoofing, lo medido, H-F pendiente y la limpieza del kernel tras
# los E2E) y BACKLOG (sección DAY320 de 8e.4b: medidas, hallazgos, DEBT-FW-ANTISPOOF-RP-FILTER-001 y
# DEBT-ARGUS-INFRA-MOD-001, pendiente). Solo documentación.
#
# Uso, desde la raíz del repo:
#   python3 -I scripts/etcd_ha/d320_docs_8e4b.py --check
#   python3 -I scripts/etcd_ha/d320_docs_8e4b.py --apply
# Todo o nada: comprueba el sha256 de cada fichero antes de escribir ninguno. Idempotente: si los dos ficheros ya
# tienen el sha256 de después, no toca nada. Salidas: 0 aplicable/aplicado/ya aplicado, 1 no aplicable, 2 uso.
import hashlib, json, os, sys, tempfile

CAMBIOS = json.loads(r'''[
 {
  "ruta": "docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md",
  "antes": "023e2dc95aed7e40d5b9f29b4eb76b899b41a9c958581f63dc347bea2f50460b",
  "despues": "b6ec62c398ceb5938d5432a428542bfc815211b427c4d3511ad521a494165316",
  "bloques": [
   {
    "viejo": "  - **8e.4b** antispoofing por interfaz y MAC en `raw PREROUTING` (H-B a H-G).\n",
    "nuevo": "  - **8e.4b** (hecho, 345f8607) antispoofing por interfaz y MAC en `raw PREROUTING` (H-B a H-E, H-G; H-F pendiente).\n"
   },
   {
    "viejo": "| `protegidos.comprobacion_kernel_sec` | [5, 3600] | 30 | vigía kernel ↔ manifiesto (8e.4a, hecho DAY320) |\n",
    "nuevo": "| `protegidos.comprobacion_kernel_sec` | [5, 3600] | 30 | vigía kernel ↔ manifiesto (8e.4a, hecho DAY320) |\n| `protegidos.antispoof.cadena` | `[A-Za-z0-9_-]`, de 1 a 24 | `ARGUS_ANTISPOOF` | cadena de `raw PREROUTING`; las de spoofing son `<cadena>_IF` y `<cadena>_MAC` (8e.4b) |\n| `protegidos.antispoof.set_redes` | `[A-Za-z0-9_-]`, de 1 a 29 | `ml_defender_prot_redes` | `hash:net` de las redes protegidas (8e.4b) |\n| `protegidos.antispoof.set_ips_mac` | `[A-Za-z0-9_-]`, de 1 a 29 | `ml_defender_prot_ipmac` | `hash:ip` de las IPs que llevan MAC (8e.4b) |\n| `protegidos.antispoof.set_mac` | `[A-Za-z0-9_-]`, de 1 a 29 | `ml_defender_prot_mac` | `hash:ip,mac` (8e.4b) |\n| `protegidos.antispoof.log_por_minuto` | [1, 600] | 5 | muestras `LOG` por minuto y cadena (8e.4b) |\n| `protegidos.antispoof.log_rafaga` | [1, 100] | 5 | ráfaga inicial del `LOG` (8e.4b) |\n"
   },
   {
    "viejo": "- `[PROTEGIDOS-SPOOFING] origen=... interfaz|mac ...` (8e.4b)\n",
    "nuevo": "- `[PROTEGIDOS-ANTISPOOF] aplicado (<por qué>): manifiesto version N modo=cuenta|descarta redes= ips_mac= mac= cadena raw <cadena>`,\n  `ERROR al aplicar`, `NO se instala: <motivo>` (nombres que chocan, `dry_run=true`) y aviso si el kernel no admite\n  `hash:ip,mac` (sin comprobación de MAC); `[PROTEGIDOS-RUTA] <entrada>: esa red no se cuenta ni se descarta`\n  (periódico); `[PROTEGIDOS-DIVERGENCIA] antispoof: ...` / `[PROTEGIDOS-RECONCILIADO] antispoof: ...`;\n  `[PROTEGIDOS-SPOOFING] origen protegido falsificado: interfaz=+N mac=+N (total interfaz=N mac=N) modo=...;\n  evidencia: journalctl -k | grep ARGUS-SPOOF`. En el journal del kernel, `ARGUS-SPOOF-IF` y `ARGUS-SPOOF-MAC`, con\n  la MAC de origen (8e.4b, DAY320)\n"
   },
   {
    "viejo": "el DoS autoinfligido del DAY317 se produjo y la barrera lo paró.\n",
    "nuevo": "el DoS autoinfligido del DAY317 se produjo y la barrera lo paró.\n\n**8e.4b, el antispoofing (hecho DAY320, 345f8607; arreglos del lab 6479804f y 3c67ca40).**\n`firewall/protegidos_antispoof.hpp`. `repartir_antispoof` reparte las entradas IPv4 del vigente en tres sets (redes,\nIPs con MAC, pares IP-MAC); las que tienen una interfaz que no casa con la ruta del kernel (`ip -o route get`, H-D) se\nquedan fuera de `set_redes`, y salen en `[PROTEGIDOS-RUTA]`. `texto_restore_antispoof` genera las cadenas y se cargan\nde golpe con `iptables-restore -w --noflush`. En `raw PREROUTING`, una regla de salto y seis reglas fijas:\n1. `lo` RETURN;\n2. origen fuera de `set_redes` RETURN (lo no protegido sale aquí, con un solo lookup);\n3. `(origen, interfaz)` fuera del set de protegidos `-g <cadena>_IF`;\n4. origen fuera de `set_ips_mac` RETURN;\n5. `(origen, MAC)` fuera de `set_mac` `-g <cadena>_MAC`;\n6. RETURN.\n\n`_IF` y `_MAC` llevan `LOG` con límite y una regla de cuenta, que lleva `DROP` solo con la mitigación real (H-C). La\naplicación es inmediata al arrancar y en cuanto cambia la versión del manifiesto o el modo. En cada vuelta del vigía,\n`antispoof_paso` comprueba los sets y las cadenas raw y reconcilia (K4 y K5), vuelve a mirar las rutas y suma los\ncontadores de las reglas de cuenta en `[PROTEGIDOS-SPOOFING]`. Si el kernel no tiene `hash:ip,mac`, el antispoofing\nqueda sin la parte de MAC y lo avisa.\n\nMedido DAY320: banco (sin `hash:ip,mac` en su kernel) native y skylake, dos pasadas, 121/121 (el test de root sale\nSkipped 77) y 0 avisos del código; `test_protegidos_antispoof` 41/41; `test_protegidos_antispoof_root` 15/15 en el\nbanco (`ARGUS_TEST_SIN_IPMAC=1`) y 16/16 en el defender; 8 mutaciones cazadas. Lab: `test-firewall` 96/96;\n`test-firewall-e2e` PASA (25, 0 saltados); `lab-e2e-antispoof` con la mitigación real PASA: el client falsifica .62\n(entrada de prueba con una MAC que no es de nadie, firmada al empezar y quitada en el trap) y el kernel cuenta\n`SPOOF-MAC` +20 y deja pasar 0 a mangle; un netns del defender falsifica .20 por un veth, `SPOOF-IF` +20 y 0 a mangle;\nel tráfico legítimo de .20 suma 0 al spoofing (su entrada del set de protegidos de 209 a 531 paquetes) y la VM etcd\nsigue sana; 5 líneas `ARGUS-SPOOF-IF` y 5 `ARGUS-SPOOF-MAC` en el journal. `lab-e2e-vigia` y `lab-e2e-mitigacion`\n(C7) siguen PASA con el antispoofing instalado.\n\n**H-F no está hecho.** `rp_filter` solo lo lee `scripts/etcd_ha/d320_medir_antispoof.sh` (0 en todas las interfaces\ndel defender); el agente no lo lee ni lo informa. Pendiente, como DEBT-FW-ANTISPOOF-RP-FILTER-001.\n\n**El kernel después de los E2E (3c67ca40).** Con la mitigación real, el agente instala también el antispoofing durante\n`lab-e2e-vigia` y `lab-e2e-mitigacion`, y sus traps no lo conocían: la cadena raw usa el set de protegidos, así que el\n`ipset destroy` de ese set fallaba sin decir nada y quedaban en el defender las tres cadenas raw (en modo descarta) y\ncuatro sets. Ahora los tres traps llaman a `scripts/etcd_ha/d320_limpia_kernel.sh` (primero los saltos y las cadenas,\nraw y filtro; después los sets; los nombres, del JSON), y `lab-e2e` comprueba con `make lab-kernel-limpio` (solo\ncuenta) que tras cada uno no queda nada.\n"
   }
  ]
 },
 {
  "ruta": "docs/BACKLOG.md",
  "antes": "6b659ea1155d6e9be86a6f0163c93efab72b100197e938ee01e67ff241113d8d",
  "despues": "b64c0baddf68a64a695ff86352898c3213ba71f5a3c98a5dcd71ee5d966c13a5",
  "bloques": [
   {
    "viejo": "`argus-infra init --si`, `d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++\nPROFILE=production y cierre del PR1.\n",
    "nuevo": "`argus-infra init --si`, `d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++\nPROFILE=production y cierre del PR1.\n\n---\n\n## DAY320 — paso 8e.4b hecho: antispoofing en raw PREROUTING [PROTEGIDOS-ANTISPOOF-D320]\n\nCommits 345f8607 (8e.4b), 6479804f (`vm()` del E2E) y 3c67ca40 (limpieza del kernel tras los E2E). Diseño y medidas:\nADR-060, sección 7 (8e.4b). Manifiesto del lab: la entrada de prueba .62 se firma y se quita en cada corrida de\n`lab-e2e-antispoof` (dos versiones por corrida; v9 al acabar el DAY320).\n\n### Medido en el banco (Debian 12, GCC 12.2)\n- native y skylake, dos pasadas: 121/121, 0 avisos del código (los 3 del enlazador por libsodium, como siempre).\n  `test_protegidos_antispoof_root` sale Skipped (77): el kernel del banco no tiene `hash:ip,mac`; con\n  `ARGUS_TEST_SIN_IPMAC=1`, 15/15. `test_protegidos_antispoof` 41/41.\n- Mutaciones, 8/8 cazadas: a1 `-j` en vez de `-g`; a2 sin la regla de `lo`; a3 `DROP` en modo cuenta; a4 una red sin\n  ruta en `set_redes`; a5 el paso no vuelve a leer; a6 `set_cuadra` no normaliza; a7 `--limit-burst 5` siempre escrito;\n  a8 MAC comparada distinguiendo mayúsculas. Las primeras versiones de a5 y a6 eran equivalentes al original (no\n  cambiaban nada observable): se rehicieron, y se quitó una comprobación de opciones redundante. a2 hacía caer el test\n  puro con un segfault: el test lleva ahora guardas y falla limpio.\n- `d320_limpia_kernel.sh`: `test_d320_limpia_kernel.sh` 9/9 en el banco y 9/9 en el defender (con `hash:ip,mac`);\n  T1 reproduce el defecto (con la limpieza antigua quedan 14 líneas raw y el set de protegidos); mutaciones k1-k7\n  cazadas.\n\n### Medido en el lab (PROFILE=production)\n`pipeline-build` rc 0; `test-firewall` 96/96; `test-firewall-e2e` PASA (25 tests, 0 saltados;\n`test_protegidos_antispoof_root` 16/16). `lab-e2e-antispoof` PASA:\n- S1, spoofing por MAC: `SPOOF-MAC` +20 y 0 a mangle;\n- S2, spoofing por interfaz: `SPOOF-IF` +20 y 0 a mangle;\n- S3, el tráfico legítimo de .20 suma 0 al spoofing (su entrada del set de protegidos de 209 a 531 paquetes);\n- S4, 5 `ARGUS-SPOOF-IF` y 5 `ARGUS-SPOOF-MAC` en el journal, 0 `[PROTEGIDOS-RUTA]` y 0 `ERROR`.\n\n`lab-e2e-vigia` y `lab-e2e-mitigacion` siguen PASA con el antispoofing instalado. Tras el arreglo del kernel,\nrepetidos los tres: trap `quedan raw=0 filter=0 sets=0` y `lab-kernel-limpio` PASA en cada uno; C7 .20 en 0 muestras\ndel blacklist, su entrada del set de protegidos de 398 a 1026 paquetes.\n\n### Hallazgos DAY320 (8e.4b)\n- `iptables -S` no imprime `--limit-burst 5` (es el valor por defecto): las reglas esperadas lo omiten cuando\n  `log_rafaga` vale 5, o el vigía vería una divergencia que no existe.\n- El kernel imprime las MAC en mayúsculas: se comparan sin distinguir.\n- El kernel del banco no tiene `hash:ip,mac`. El test de root sale con 77, o corre sin MAC con\n  `ARGUS_TEST_SIN_IPMAC=1`; la prueba con MAC es la del defender.\n- El banco, para `ip netns exec`, necesita `/run/argus/irp`, un `proc` montado de nuevo y la raíz del chroot montada\n  sobre sí misma.\n- `vm()` de `d320_antispoof_e2e.sh` devolvía el código del filtro, no el del comando remoto: un `grep -q` remoto que\n  casaba daba 1. Arreglado en 6479804f.\n- Con la mitigación real, el agente instala el antispoofing en todos los E2E que la usan, y los traps de vigía y\n  mitigación no lo retiraban: quedaban en el defender las tres cadenas raw en modo descarta y cuatro sets. Arreglado en\n  3c67ca40 (ayudante único, `make lab-test-limpia-kernel` y `make lab-kernel-limpio` en `lab-e2e`).\n- `d302_mitigacion_e2e.sh` tenía `CHAIN=ML_DEFENDER_TEST` escrito en el script; ahora lo lee de `iptables.chain_name`\n  (3c67ca40).\n- `LAB_E2E_DIA` sigue valiendo `day303`: las corridas de hoy están en `logs/lab/day303/`. Sin decidir.\n- Sin medir: si `vagrant reload etcd` aplica la MAC fija del Vagrantfile a una VM ya creada.\n\n### DEBT-FW-ANTISPOOF-RP-FILTER-001 — ABIERTA (nueva DAY320)\nH-F (ADR-060, sección 7) dice que el agente lee `rp_filter` y lo informa, sin cambiarlo. 8e.4b no lo hace: solo lo lee\nel script de medida. Arreglo: al arrancar y cada `aviso_sec`, leer `/proc/sys/net/ipv4/conf/{all,<interfaz>}/rp_filter`\nde las interfaces del manifiesto y escribir el valor efectivo (el máximo de `all` y el de la interfaz) en el log.\n**Test de cierre:** un test que lee un árbol `/proc` falso con valores 0, 1 y 2 y comprueba el valor efectivo y la línea\ndel log; en el defender, la línea aparece con `rp_filter` 0 en todas.\n\n### DEBT-ARGUS-INFRA-MOD-001 — ABIERTA (nueva DAY320)\n`argus-infra` no tiene `mod`: cambiar la interfaz o la MAC de una entrada son dos versiones firmadas (`del` y luego\n`add`), y entre una y otra la entrada no está en el manifiesto vigente. Sin medir cuánto dura esa ventana en el agente.\nArreglo: `mod`, que firma una sola versión con la baja y el alta, y `[INFRA-CAMBIO]` que lo muestra como un cambio.\n**Test de cierre:** en `test_argus_infra.py`, `mod` deja una única versión nueva cuyo `diff` con la anterior es solo el\ncampo cambiado; en el lab, el agente pasa de la entrada vieja a la nueva sin ninguna vuelta del vigía en la que falte.\n\n### Pendiente (por orden)\n8e.4c (versión del manifiesto en el latido y en `pipeline-status`, H-H), 8e.4d (Wazuh y Falco, con su configuración en\nficheros propios), docs de cada uno, 8e.5 (bootstrap con `argus-infra init --si`, `d303_veredicto_protegidos.sh`\nP1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1. Sin orden decidido:\nDEBT-FW-ANTISPOOF-RP-FILTER-001 y DEBT-ARGUS-INFRA-MOD-001.\n"
   }
  ]
 }
]''')

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d320_docs_8e4b.py --check|--apply  (desde la raíz del repo)", file=sys.stderr); return 2
    aplicar = sys.argv[1] == "--apply"
    estados, nuevos = [], {}
    for c in CAMBIOS:
        if not os.path.isfile(c["ruta"]):
            print(f"[NO APLICABLE] no existe {c['ruta']} (¿estás en la raíz del repo?)"); return 1
        b = open(c["ruta"], "rb").read(); s = sha(b)
        if s == c["despues"]:
            estados.append("hecho"); print(f"[YA APLICADO] {c['ruta']} sha256={s}"); continue
        if s != c["antes"]:
            print(f"[NO APLICABLE] {c['ruta']} sha256={s}\n  esperado antes  ={c['antes']}\n  esperado después={c['despues']}")
            return 1
        t = b.decode("utf-8"); borradas = 0
        for i, bl in enumerate(c["bloques"], 1):
            v = bl["viejo"]
            if t.count(v) != 1:
                print(f"[NO APLICABLE] {c['ruta']}: el bloque {i} aparece {t.count(v)} veces"); return 1
            t = t.replace(v, bl["nuevo"]); borradas += v.count(chr(10)) - bl["nuevo"].count(chr(10))
        n = t.encode("utf-8")
        if sha(n) != c["despues"]:
            print(f"[NO APLICABLE] {c['ruta']}: el resultado no da el sha256 esperado"); return 1
        estados.append("pendiente"); nuevos[c["ruta"]] = n
        print(f"[APLICABLE] {c['ruta']} {s[:16]} -> {c['despues'][:16]} ({len(c['bloques'])} bloques, {abs(borradas)} líneas {'menos' if borradas >= 0 else 'más'})")
    if "hecho" in estados and "pendiente" in estados:
        print("[NO APLICABLE] estado mezclado: un fichero ya aplicado y otro no; no se toca nada"); return 1
    if not nuevos:
        print("[YA APLICADO] nada que hacer"); return 0
    if not aplicar:
        print("[CHECK] todo aplicable; nada escrito"); return 0
    for ruta, n in nuevos.items():
        modo = os.stat(ruta).st_mode & 0o7777
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta), prefix=".d320.")
        with os.fdopen(fd, "wb") as f: f.write(n); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, modo); os.replace(tmp, ruta)
    for c in CAMBIOS:
        s = sha(open(c["ruta"], "rb").read())
        if s != c["despues"]:
            print(f"[ERROR] {c['ruta']} quedó con sha256={s}"); return 1
        print(f"[APLICADO] {c['ruta']} sha256={s}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
