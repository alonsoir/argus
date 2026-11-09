#!/usr/bin/env python3
# [LATIDO-DATOS-D321] docs de 8e.4c (DAY321): ADR-060 (plan; mensajes de log y líneas de pipeline-status; sección 7
# con las decisiones de Alonso, cómo queda, la línea que solo informa, H-F hecho y lo medido) y BACKLOG
# (DEBT-FW-ANTISPOOF-RP-FILTER-001 cerrada; sección DAY321 con decisiones, banco, lab, hallazgos y pendiente).
# Solo documentación.
# Uso (raíz del repo): python3 -I d321_docs_8e4c.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'docs/adr/ADR-060-manifiesto-firmado-rangos-protegidos.md', 'antes': 'b6ec62c398ceb5938d5432a428542bfc815211b427c4d3511ad521a494165316', 'despues': '8c34f10ea8c1f96bd643aae8c703af0581020d401b9e819452c573820801403b', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('  (sección 7), en cuatro commits:\n  - **8e.4a** (hecho, fe4c94d3) el vigía kernel ↔ manifiesto y C7 en el E2E de la mitigación real.\n  - **8e.4b** (hecho, 345f8607) antispoofing por interfaz y MAC en `raw PREROUTING` (H-B a H-E, H-G; H-F pendiente).\n  - **8e.4c** versión del manifiesto en el latido y en `pipeline-status` (H-H).\n  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J).\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n',
             '  (sección 7), en cuatro commits:\n  - **8e.4a** (hecho, fe4c94d3) el vigía kernel ↔ manifiesto y C7 en el E2E de la mitigación real.\n  - **8e.4b** (hecho, 345f8607) antispoofing por interfaz y MAC en `raw PREROUTING` (H-B a H-E, H-G; H-F pasó a 8e.4c).\n  - **8e.4c** (hecho, 1818f4ec) versión del manifiesto en el latido y en `pipeline-status` (H-H) y `rp_filter`\n    informado (H-F).\n  - **8e.4d** Wazuh (FIM, agente en la VM etcd, disco del audit de Vault, fallos de audit) y Falco (H-I, H-J).\n- **8e.5** Bootstrap del lab con `argus-infra` (.20 y .61), veredicto P1–P6, EMECAS+++.\n'),
            ('  evidencia: journalctl -k | grep ARGUS-SPOOF`. En el journal del kernel, `ARGUS-SPOOF-IF` y `ARGUS-SPOOF-MAC`, con\n  la MAC de origen (8e.4b, DAY320)\n- `protegidos:` gana `infraestructura=N`.\n\n',
             '  evidencia: journalctl -k | grep ARGUS-SPOOF`. En el journal del kernel, `ARGUS-SPOOF-IF` y `ARGUS-SPOOF-MAC`, con\n  la MAC de origen (8e.4b, DAY320)\n- `[ETCD-CLIENTE-LATIDO-DATO] <CN>: <clave>=N (nuevo|antes M); va en el siguiente latido` (una línea por cambio, no\n  por latido) o `<motivo>; no se guarda (datos del latido: <formato>)`; `[ETCD-CLIENTE-LATIDO-DATOS-RECHAZADOS]` y\n  `[ETCD-CLIENTE-LATIDO-DATOS-ACEPTADOS]` cuando cambia lo que responde el etcd-server. En el etcd-server,\n  `[ETCD-LATIDO-DATOS-RECHAZADOS] <CN>: <motivo>; el latido se guarda sin datos` y `[ETCD-LATIDO-DATOS-ACEPTADOS]`,\n  también solo al cambiar. `[PROTEGIDOS-RP-FILTER] <interfaz>=<efectivo> (all=a if=b, sin filtro|estricto|laxo) ...;\n  solo se informa, no se cambia (H-F)`, al arrancar y cada `aviso_sec` (8e.4c, DAY321)\n- En `pipeline-status` (`etcd_vm_estado.sh`): `✅ protegidos: vN publicada; K componentes al día`, `⚠️ ... K DESFASADOS`,\n  `⚠️ ... POR DELANTE`, `⚠️ ... sin manifiesto publicado`, `⚠️ ... ningún componente informa protegidos_version` o\n  `❌ ... vigente ilegible`, y debajo una línea por componente (`- <CN> vN al día|DESFASADO|POR DELANTE (activo|muerto,\n  latido hace S s)`) (8e.4c, DAY321)\n- `protegidos:` gana `infraestructura=N`.\n\n'),
            ('(C7) siguen PASA con el antispoofing instalado.\n\n**H-F no está hecho.** `rp_filter` solo lo lee `scripts/etcd_ha/d320_medir_antispoof.sh` (0 en todas las interfaces\ndel defender); el agente no lo lee ni lo informa. Pendiente, como DEBT-FW-ANTISPOOF-RP-FILTER-001.\n\n**El kernel después de los E2E (3c67ca40).** Con la mitigación real, el agente instala también el antispoofing durante\n',
             '(C7) siguen PASA con el antispoofing instalado.\n\n**H-F se hizo en 8e.4c** (DAY321, 1818f4ec), que cierra DEBT-FW-ANTISPOOF-RP-FILTER-001; 8e.4b solo lo leía en el\nscript de medida.\n\n**8e.4c, la versión del manifiesto en el latido y `rp_filter` (hecho DAY321, 1818f4ec).** Decisiones de Alonso\n(DAY321), las cuatro como se recomendaron:\n- **Tipo de los datos del latido: solo enteros.** Regla única en `libs/latido/include/latido/datos_latido.hpp`, que\n  aplican el etcd-client antes de enviar y el etcd-server al recibir: `"datos"` es un objeto de 0 a 8 claves\n  `^[a-z][a-z0-9_]{0,31}$` con enteros en [0, 2^53 − 1] (el mayor entero que cualquier lector JSON representa sin perder\n  precisión). Es contrato del protocolo, no configuración, como el tamaño máximo de la carga del manifiesto. Con una\n  clave mala se rechazan todos los datos de ese latido. O(datos).\n- **Datos mal formados en el etcd-server: 200 sin los datos.** El latido se guarda igual, sin la clave `"datos"`, y la\n  respuesta lo dice en `"datos_rechazados"`. Medido en el código antes de decidir: un 4xx al latido hace que el cliente\n  se dé por desregistrado y quede «sin servicio», así que un dato malo dejaría al componente sin latir y lo acabaría\n  marcando muerto.\n- **Origen de `pipeline-status`: etcd con `etcdctl`**, sin ruta nueva ni reglas de authz nuevas.\n- **E2E del desfase: `protegidos.consulta_sec=3600` solo durante la prueba**, dentro de `lab-e2e`.\n\nCómo queda:\n- `EtcdClient::poner_dato_latido(clave, valor)`, seguro entre hilos; el mantenedor y `heartbeat()` añaden `"datos"`\n  cuando hay alguno. El firewall pone `protegidos_version` (0 sin manifiesto) al arrancar y tras cada consulta.\n- El etcd-server guarda `latido/<CN> = {"ultimo", "estado", "datos"}`. Al marcar un componente muerto se conservan\n  los datos, así que se ve la versión que tenía al morir; el siguiente latido los renueva.\n- `scripts/etcd_ha/etcd_vm_estado.sh` lee `<prefijo>latido/` y `<prefijo>protegidos/vigente` con los certificados que\n  ya usa. La versión publicada sale de la carga del sobre sin verificar la firma, porque el etcd-server solo escribe\n  `vigente` después de verificarla y el firewall la verifica otra vez. Solo lista los componentes que mandan\n  `protegidos_version`. Un desfase es normal hasta `consulta_sec` más un latido después de publicar.\n- **La línea de protegidos solo informa (⚠️): no cuenta en el veredicto de la VM etcd.** Cambio sobre lo que se\n  propuso antes de medir: `--estricto` no lo usa solo EMECAS, también `etcd-vm-check` (dentro de `etcd-vm-deploy` y\n  `etcd-server-start`, con el firewall parado) y `etcd-vm-aviso` (en `pipeline-start`, antes de arrancarlo). Con el\n  desfase contando, un despliegue fallaría solo por haber publicado una versión con el firewall parado.\n- **H-F:** `[PROTEGIDOS-RP-FILTER]` al arrancar y cada `aviso_sec` (`firewall/protegidos_rp_filter.hpp`): por cada\n  interfaz de las entradas IPv4 del vigente, `max(conf/all/rp_filter, conf/<interfaz>/rp_filter)`, que es lo que usa\n  el kernel. Solo se lee. Un nombre que pudiera salir de la raíz (`.`, `..`, `/`) no se lee.\n\nMedido DAY321:\n- Banco (Debian 12, GCC 12.2, native y skylake, dos pasadas cada uno): etcd-client 5/5, etcd-server 9/9, firewall\n  122/122 y 0 avisos del código. `test_latido_datos` 8 tests; L1-L7 en `test_etcd_cliente_tls` (35/35);\n  `test_protegidos_rp_filter` 33/33. Con etcd 3.6.16 real (TLS y RBAC como en el Vagrantfile) y el etcd-server\n  compilado, 16/16 en las cuatro compilaciones. 16 mutaciones cazadas, todas compilando.\n- Lab (`PROFILE=production`): `pipeline-build` rc 0; `test-firewall` 97/97; etcd-server 9/9; etcd-client 5/5;\n  `test-firewall-e2e` PASA (25, 0 saltados); `etcd-vm-deploy` SANO. Tras arrancar, `✅ protegidos: v9 publicada; 1\n  componente al día` y `[PROTEGIDOS-RP-FILTER] eth2=0 (all=0 if=0, sin filtro)`. `lab-e2e-latido` PASA en 7 min 49 s:\n  L0 al día con v9 en 5 s; L1 v10 publicada y el firewall en v9 DESFASADO a los 4 s, con el veredicto en SANO; L2 al día\n  con v10 a los 4 s del rearranque; L3 v11 por la consulta periódica en 37 s (límite 75); L4 0 rechazos en los dos lados.\n  El lab queda en v11, con el contenido de antes de la prueba.\n- Al parar el firewall de forma ordenada, su baja (`/unregister`) borra `latido/<CN>` y deja de salir en la línea; solo\n  sale como muerto si cae sin darse de baja.\n\n**El kernel después de los E2E (3c67ca40).** Con la mitigación real, el agente instala también el antispoofing durante\n'),
        ],
    },
    {
        'ruta': 'docs/BACKLOG.md', 'antes': 'b64c0baddf68a64a695ff86352898c3213ba71f5a3c98a5dcd71ee5d966c13a5', 'despues': '109dbaabc27e927fb71f2612f9a026e76bef75693662c9941b5c9dcbb98b34c1', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('- Sin medir: si `vagrant reload etcd` aplica la MAC fija del Vagrantfile a una VM ya creada.\n\n### DEBT-FW-ANTISPOOF-RP-FILTER-001 — ABIERTA (nueva DAY320)\nH-F (ADR-060, sección 7) dice que el agente lee `rp_filter` y lo informa, sin cambiarlo. 8e.4b no lo hace: solo lo lee\nel script de medida. Arreglo: al arrancar y cada `aviso_sec`, leer `/proc/sys/net/ipv4/conf/{all,<interfaz>}/rp_filter`\n',
             '- Sin medir: si `vagrant reload etcd` aplica la MAC fija del Vagrantfile a una VM ya creada.\n\n### DEBT-FW-ANTISPOOF-RP-FILTER-001 — CERRADA DAY321 (1818f4ec, 8e.4c)\nCerrada con el test de cierre: `test_protegidos_rp_filter` (33/33) lee un árbol `/proc` falso con 0, 1 y 2, valores\nilegibles y nombres que saldrían de la raíz, y en el defender sale `[PROTEGIDOS-RP-FILTER] eth2=0 (all=0 if=0, sin\nfiltro)`. Texto original:\nH-F (ADR-060, sección 7) dice que el agente lee `rp_filter` y lo informa, sin cambiarlo. 8e.4b no lo hace: solo lo lee\nel script de medida. Arreglo: al arrancar y cada `aviso_sec`, leer `/proc/sys/net/ipv4/conf/{all,<interfaz>}/rp_filter`\n'),
            ('P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1. Sin orden decidido:\nDEBT-FW-ANTISPOOF-RP-FILTER-001 y DEBT-ARGUS-INFRA-MOD-001.\n',
             'P1-P6, `test-argus-infra` en EMECAS), EMECAS+++ PROFILE=production y cierre del PR1. Sin orden decidido:\nDEBT-FW-ANTISPOOF-RP-FILTER-001 y DEBT-ARGUS-INFRA-MOD-001.\n\n## DAY321 — paso 8e.4c hecho: versión del manifiesto en el latido y en pipeline-status [LATIDO-DATOS-D321]\n\nCommits: `1818f4ec` (8e.4c), el arreglo de `test-firewall` (`[ARGUS-GATE-PERF-D321]`) y este de documentación.\nDiseño y decisiones en ADR-060, sección 7 («8e.4c»). Cierra DEBT-FW-ANTISPOOF-RP-FILTER-001.\n\n### Decisiones de Alonso (DAY321)\n- Datos del latido: solo enteros. Regla única en `libs/latido/datos_latido.hpp` para el etcd-client y el etcd-server.\n- Datos mal formados: el etcd-server guarda el latido sin ellos, responde 200 y lo dice en `datos_rechazados`.\n- `pipeline-status` lee de etcd con `etcdctl`, sin ruta nueva.\n- E2E del desfase con `protegidos.consulta_sec=3600` solo durante la prueba (`lab-e2e-latido`, dentro de `lab-e2e`).\n- `rp_filter` (H-F) dentro de 8e.4c.\n- `test-firewall` excluye también `perf` (los dos `IPSetWrapperPerfTest` corren en `test-firewall-perf`).\n\n### Medido en el banco (Debian 12, GCC 12.2, banco rehecho DAY321)\n- native y skylake, dos pasadas cada uno: etcd-client 5/5, etcd-server 9/9, firewall 122/122, 0 avisos del código.\n- `test_latido_datos` 8 tests; L1-L7 en `test_etcd_cliente_tls` (35/35); `test_protegidos_rp_filter` 33/33.\n- etcd 3.6.16 real (TLS y RBAC como el Vagrantfile) con el etcd-server compilado y latidos por curl con el certificado\n  de cada componente: 16/16 en las cuatro compilaciones (datos en `latido/<CN>`, desfase, por delante, ilegible,\n  rechazo sin perder el latido, todo o nada, muerto con su versión, revivido, regla `propio` con 403, filtro de\n  `pipeline-status`).\n- 16 mutaciones cazadas, todas compilando (la primera pasada contaba un fallo de compilación como cazada: corregido el\n  script y repetidas las 16).\n- `ctest -N`: con `-LE "e2e"` entraban 97 tests en `test-firewall`; con `-LE "e2e|root|perf"`, 95, y salen exactamente\n  los dos `IPSetWrapperPerfTest`.\n\n### Medido en el lab (PROFILE=production)\n- `pipeline-build` rc 0; `test-firewall` 97/97 (los dos perf salían Skipped, sin root); etcd-server 9/9; etcd-client\n  5/5 (R2 no saltó); `test-firewall-e2e` PASA (25, 0 saltados).\n- `etcd-vm-deploy` SANO, con `⚠️ protegidos: v9 publicada; ningún componente informa protegidos_version` (el firewall\n  aún con el binario viejo). Tras `pipeline-start`: `✅ protegidos: v9 publicada; 1 componente al día` y\n  `- firewall-acl-agent v9 al día (activo, latido hace 7 s)`; en el log `protegidos_version=9 (nuevo)` y\n  `[PROTEGIDOS-RP-FILTER] eth2=0 (all=0 if=0, sin filtro)`.\n- `lab-e2e-latido` PASA (7 min 49 s): L0 al día con v9 en 5 s; L1 v10 publicada, firewall en v9 DESFASADO a los 4 s y\n  veredicto SANO; L2 al día con v10 a los 4 s del rearranque; L3 v11 por la consulta periódica en 37 s (límite 75);\n  L4 0 rechazos en el firewall y en el journal del etcd-server. Lab vigente: v11.\n\n### Hallazgos DAY321\n- Un 4xx al latido deja al etcd-client desregistrado y «sin servicio»: por eso los datos malos no pueden rechazar el\n  latido entero.\n- `--estricto` de `etcd_vm_estado.sh` lo usan también `etcd-vm-deploy`, `etcd-server-start` y `etcd-vm-aviso`, con el\n  firewall parado: la línea de protegidos solo informa.\n- La baja ordenada (`/unregister`) borra `latido/<CN>`: un firewall parado deja de salir en `pipeline-status`; solo\n  sale como muerto si cae sin darse de baja.\n- `test-firewall` lanzaba sin root los tests `perf`, que salían Skipped desde DAY303.\n- El banco necesita `/run/argus/irp` (lo crea `provision.sh`) para los tests de ipset del firewall.\n- `LAB_E2E_DIA` sigue valiendo `day303`: la corrida de hoy está en `logs/lab/day303/`. Sin decidir.\n\n### Pendiente (por orden)\n8e.4d (Wazuh y Falco, con su configuración en ficheros propios, H-I y H-J), sus docs, 8e.5 (bootstrap con\n`argus-infra init --si`, `d303_veredicto_protegidos.sh` P1-P6, `test-argus-infra` en EMECAS), EMECAS+++\nPROFILE=production y cierre del PR1. Sin orden decidido: DEBT-ARGUS-INFRA-MOD-001.\n'),
        ],
    },
]


def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply"); return 2
    aplicar = sys.argv[1] == "--apply"
    if not os.path.isdir(".git"):
        print("[ERROR] ejecutar desde la raíz del repo (no veo .git)"); return 2
    plan, ya, errores = [], 0, 0
    for f in FICHEROS:
        r = f["ruta"]
        if os.path.exists(r):
            actual = open(r, "rb").read()
            h = sha(actual)
            if h == f["despues"]:
                print(f"[YA-APLICADO] {r} {h[:16]}"); ya += 1; continue
            if f["antes"] == "nuevo":
                print(f"[ERROR] {r} existe con otro contenido ({h[:16]}); se esperaba que no existiera"); errores += 1; continue
            if h != f["antes"]:
                print(f"[ERROR] {r} sha256 {h[:16]}, se esperaba {f['antes'][:16]} (antes) o {f['despues'][:16]} (después)"); errores += 1; continue
            t = actual.decode("utf-8")
            for i, (v, n) in enumerate(f["trozos"]):
                if t.count(v) != 1:
                    print(f"[ERROR] {r}: trozo {i + 1} aparece {t.count(v)} veces"); errores += 1; break
                t = t.replace(v, n)
            nb = t.encode("utf-8")
            modo = os.stat(r).st_mode & 0o777
        else:
            if f["antes"] != "nuevo":
                print(f"[ERROR] {r} no existe"); errores += 1; continue
            nb = f["nuevo"].encode("utf-8"); modo = int(f["modo"], 8)
        if sha(nb) != f["despues"]:
            print(f"[ERROR] {r}: el resultado no da el sha256 esperado"); errores += 1; continue
        plan.append((r, nb, modo, f))
        print(f"[APLICABLE] {r} {f['antes'][:16]} -> {f['despues'][:16]} ({len(f['trozos']) if f['nuevo'] is None else 'fichero nuevo'}{' bloques' if f['nuevo'] is None else ''})")
    if errores:
        print(f"[ERROR] {errores} problemas: no se escribe nada"); return 1
    if not plan:
        print(f"[CHECK] todo ya aplicado ({ya} ficheros)"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(plan)} ficheros, {ya} ya aplicados); nada escrito"); return 0
    for r, nb, modo, f in plan:
        d = os.path.dirname(r) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche_")
        with os.fdopen(fd, "wb") as o: o.write(nb)
        os.chmod(tmp, modo)
        os.replace(tmp, r)
        print(f"[APLICADO] {r} sha256={f['despues']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
