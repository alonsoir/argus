#!/usr/bin/env python3
"""DAY303 [CIERRE-D303]: documentos de cierre del dia, con los numeros leidos del log de EMECAS (no copiados).
Escribe:
  docs/ml-heads/day303_emecas_desde_cero.md   resultados del dia
  docs/ml-heads/paper_apoyo_day303.md          apoyo para el paper (metodologia y numeros)
  docs/ml-heads/prompt_day304.md               prompt de continuidad
  docs/BACKLOG.md                              seccion "Cierre DAY303" anadida al final (idempotente por marca)
Se niega si el log de EMECAS no termina con rc=0 y EMECAS+++ PASSED.
Uso (Mac, raiz del repo): python3 scripts/timebase/d303_cierre.py logs/lab/emecas/emecas_XXXX.log --check|--apply
"""
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

M = "[CIERRE-D303]"
if len(sys.argv) != 3 or sys.argv[2] not in ("--check", "--apply"):
    print(__doc__)
    sys.exit(2)
LOG = Path(sys.argv[1])
errores = []
if not LOG.is_file():
    print("PARO: no existe", LOG)
    sys.exit(1)
log = LOG.read_text(encoding="utf-8", errors="replace")


def una(patron, donde=log):
    m = re.findall(patron, donde, flags=re.M)
    return m[-1] if m else None


ini = una(r"^\[EMECAS-RUN\] inicio (\S+ \S+) objetivo=(\S+) PROFILE=(\S+)")
fin = una(r"^\[EMECAS-RUN\] fin (\S+ \S+) rc=(\d+)")
if not ini or not fin:
    errores.append("el log no tiene las lineas [EMECAS-RUN] inicio/fin")
elif ini[1] != "emecas+++" or ini[2] != "production":
    errores.append("el log es de objetivo=" + ini[1] + " PROFILE=" + ini[2] + ", se esperaba emecas+++ production")
elif fin[1] != "0":
    errores.append("EMECAS termino con rc=" + fin[1] + ": no se documenta como verde")
if "EMECAS+++ PASSED" not in log:
    errores.append("falta 'EMECAS+++ PASSED' en el log")
for f in ("docs/ml-heads/day303_emecas_desde_cero.md", "docs/ml-heads/paper_apoyo_day303.md",
          "docs/ml-heads/prompt_day304.md"):
    if Path(f).exists():
        errores.append("ya existe " + f)
BACK = Path("docs/BACKLOG.md")
if not BACK.is_file():
    errores.append("no existe docs/BACKLOG.md")
elif M in BACK.read_text(encoding="utf-8"):
    errores.append("docs/BACKLOG.md ya tiene la seccion " + M)
if errores:
    print("PARO: no se escribe nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)

t0 = datetime.strptime(ini[0], "%Y-%m-%d %H:%M:%S")
t1 = datetime.strptime(fin[0], "%Y-%m-%d %H:%M:%S")
dur = t1 - t0
DUR = "%dh%02dm" % (dur.seconds // 3600 + dur.days * 24, dur.seconds % 3600 // 60)
# la rama certificada, no la rama de documentos desde la que se ejecuta este script
rama = "fix/ddos-etapa1-histeresis"
commit = subprocess.run(["git", "log", "-1", "--format=%h", rama], capture_output=True, text=True).stdout.strip()
if not commit:
    print("PARO: no encuentro la rama " + rama)
    sys.exit(1)


def lineas(patron):
    return [l.strip() for l in log.splitlines() if re.search(patron, l)]


FRES = "\n".join("    " + l for l in lineas(r"^\[FRESCURA\] (ok|resumen|PASA)"))
VERED = "\n".join("    " + l for l in lineas(r"\[VEREDICTO\] (PASA|RESULTADO|dato)|RESULTADO PASA$|analisis rc="))
GATE = "\n".join("    " + l for l in lineas(r"^\[CTEST-GATE\] (resumen|PASA)"))
PERF = "\n".join("    " + l for l in lineas(r"^\[PERF\]"))
CLEAN = "\n".join("    " + l for l in lineas(r"^\[CLEAN-HOST\] PASA"))
print("EMECAS+++ PROFILE=production: inicio", ini[0], "fin", fin[0], "duracion", DUR, "rc=0")
print("rama", rama, "commit", commit)

RES = """# DAY303 — EMECAS+++ desde cero de verdad, en producción, con los E2E del lab como puerta

Rama certificada `{rama}` (último commit `{commit}`). EMECAS+++ `PROFILE=production`: inicio {ini}, fin {fin},
**{dur}**, rc=0, `EMECAS+++ PASSED`. Log: `{log}`.

## Decisiones de Alonso (DAY303)

- Compilar y probar siempre en producción (`PROFILE ?= production`): máxima confianza en el compilador.
- EMECAS+++ certifica el merge. El pase con sanitizers (ASan/TSan) queda para hardware real de
  preproducción/producción, no para el Mac de 2019.
- EMECAS estricto y determinista: si pasa, el pipeline E2E funciona como se diseñó, sin más.
- rag/rag-security: su deprecado se certifica en una rama propia tras este merge (no se mezclan tareas).

## Lo que estaba mal y cómo se midió

| Hallazgo | Medida | Arreglo |
|---|---|---|
| Inyectores del E2E sintético sin recompilar desde junio | `tools/build-*/synthetic_*` del 7 y 12-jun | `pipeline-build` incluye `tools` |
| Todos los `build-active` apuntaban a `build-debug` desde el 14-oct | `ls -ld */build-active` | `pipeline-build` termina con `set-build-profile` |
| `set-build-profile` solo en `bootstrap` y ANTES de compilar (se salta lo que no existe) | `set-build-profile.sh` + orden de `bootstrap` | idem |
| rag-security arrancaba un binario debug del 14-abr; `rag-build` compilaba en `rag/build` | `ls -l rag/build*/rag-security` | `RAG_BUILD_DIR` por perfil; `rag-start` desde `$(RAG_BUILD_DIR)` |
| EMECAS no limpiaba nada: `/vagrant` es la carpeta del Mac y sobrevive a `vagrant destroy` | K1-K5 | `clean-host-builds` en el Mac, antes de `vagrant up` |
| `provision.sh` compila seed-client, crypto-transport, plugin-loader y etcd-client en `/vagrant/*/build` durante el `up` | K11 | idem (un `clean-all` tras el `up` rompía `libcrypto_transport.so`) |
| `crypto-transport/build` versionado en git (Makefile de CMake y `.so`) | K12 | fuera del índice y en `.gitignore` |
| `tools/build` (enlace generado) versionado | `git ls-files -s` | fuera del índice y en `.gitignore` |
| Los E2E del lab dependían del ruido de fondo de Wazuh/Zeek (5 VMs) para "esperar ESTABLE" | K13-K15: el lector solo escribe claves con paquetes; 6 filas en 120 s con 3 VMs | fondo ICMP controlado solo durante la espera |
| Los análisis de DAY300 no tenían PASA/FALLA (solo medían) | D1 | veredictos estrictos con criterios del diseño |
| Step 4 de Vault: `$(CMAKE_FLAGS)` (con comillas dobles) dentro de `vagrant ssh -c "..."` | 7 argumentos para vagrant (shlex) | comillas simples, verificado con shlex en los 4 perfiles |
| Los E2E del lab paran el pipeline y el acto II lo necesita arrancado | injector sin etcd-server en 2379, timeout 124 | `lab-e2e` termina con `pipeline-start` y exige 5/5 RUNNING |
| `pgrep -a -f` se imprime a sí mismo: su línea contiene `STOPPED` | falso positivo de `grep STOPPED` | patrón estricto `^ *❌ ... STOPPED` |

## Puertas de EMECAS y sus números

Limpieza en el Mac:
{clean}

Frescura (cada binario del pipeline en `build-production`, `build-active` apuntando ahí y más nuevo que el sello
escrito tras el `vagrant up`):
{fres}

Puerta del firewall con root (`ctest_label_gate.sh`, falla con cualquier test saltado o gtest de 0 tests):
{gate}

Medidas de rendimiento (no fallan por tiempo; solo por medida inválida):
{perf}

E2E del lab (`lab-e2e`), veredictos:
{vered}

## Validación de los veredictos antes de usarlos (V1)

Sobre las corridas guardadas de DAY300: `antes2`, `ordenada`, `kill9` y `protegidos` PASA; la `antes` original
(corte del log anotado antes de parar el sniffer, 997 marcados del sniffer viejo) FALLA solo en R3. El veredicto
aprueba lo que DAY300 dio por bueno y rechaza lo que se rechazó entonces.

La banda 1,15-1,40 de la razón no decide: en la corrida suelta de DAY303 `kill9` dio 1,487 (el `pkill` para antes
que `sniffer-stop`: menos ataque antes del corte, más después) y es una corrida correcta.
""".format(rama=rama, commit=commit, ini=ini[0], fin=fin[0], dur=DUR, log=LOG, clean=CLEAN or "    (sin lineas)",
           fres=FRES or "    (sin lineas)", gate=GATE or "    (sin lineas)", perf=PERF or "    (sin lineas)",
           vered=VERED or "    (sin lineas)")

PAPER = """# Apoyo para el paper — DAY303

## Un gate "desde cero" que no lo era

El gate de calidad de aRGus (EMECAS: `vagrant destroy` → `vagrant up` → bootstrap → tests) se presentaba como
reconstrucción desde cero. Medido DAY303: no lo era. La carpeta del repositorio en el anfitrión se monta en las
VMs (`/vagrant`) y sobrevive a `vagrant destroy`, y con ella todos los directorios de compilación. Consecuencias
medidas, cada una con su fecha de fichero:

- los inyectores del E2E sintético llevaban sin recompilarse desde junio (el objetivo de compilación no los
  incluía): el E2E sintético probaba binarios de cuatro meses antes;
- el componente rag-security arrancaba un binario de perfil debug de abril, aunque la compilación producía otro
  en otro directorio;
- los enlaces del perfil activo (`build-active`) apuntaban a debug desde hacía seis días, aunque se compilaba en
  producción;
- el aprovisionamiento compilaba cuatro librerías sobre directorios de compilación anteriores, uno de ellos
  incluso versionado en git.

Ningún test fallaba: todo "funcionaba". La lección metodológica es que un gate verde no demuestra qué binario se
probó. DAY303 añade una comprobación explícita de frescura: un sello escrito tras crear las VMs y, tras compilar,
la comprobación de que cada binario del pipeline es más nuevo que el sello y es el que apunta el perfil activo.
Se validó en negativo antes de usarla: con un sello posterior a la compilación, 8/8 binarios FALLA.

## Dependencias ocultas del entorno

Los E2E de laboratorio de DAY300/302 esperaban a que el lector del kernel estuviera "estable" (≥ 10 sondeos en
30 s). El lector solo escribe las claves con paquetes en la ventana. En las corridas manuales, con cinco VMs, el
tráfico de fondo de los agentes Wazuh y de Zeek cumplía esa condición sin que nadie lo supiera; en el gate, con
tres VMs, el laboratorio estaba casi mudo (6 filas en 120 s) y la espera agotaba sus 15 minutos. Se sustituye el
fondo accidental por uno explícito y controlado (ICMP a 2 pps, otra víctima del agregador, solo durante la
espera). Una reconstrucción desde cero de verdad es lo que destapó la dependencia.

## Criterios PASA/FALLA del diseño, no del reloj

Los E2E pasan a puerta del gate con criterios derivados del diseño:
- identidad exacta, diferencia 0, entre lo que marca el ml-detector y los DROP del firewall (transporte sin
  pérdidas), y DROP_resúmenes = DROP_FIN + alertas en los rangos protegidos;
- restauración del estado según el modo de reinicio (sin estado / parada ordenada / `kill -9`);
- continuidad del marcado tras el reinicio como frontera entre los dos regímenes posibles (con estado ≈ 1,2-1,5;
  sin estado 0), no una banda temporal: la banda medida en DAY300 (1,15-1,40) depende de cuánto tarda la parada y
  una corrida correcta de DAY303 dio 1,487.

Los veredictos se validaron contra corridas ya juzgadas: aprueban las cuatro que DAY300 aceptó y rechazan la que
DAY300 rechazó (control negativo).

## Números de la corrida que certifica la rama

EMECAS+++ `PROFILE=production` desde cero: {dur}, rc=0 ({ini} → {fin}).

{vered}
""".format(dur=DUR, ini=ini[0], fin=fin[0], vered=VERED or "    (sin lineas)")

PROMPT = """# Prompt DAY304 — aRGus NDR

Contexto: DAY303 certificó con EMECAS+++ desde cero (`PROFILE=production`, {dur}, rc=0) la rama
`fix/ddos-etapa1-histeresis` (cabeza DDoS etapa 1 con histéresis, persistencia del estado por víctima, rangos
protegidos, mitigación real E2E) y se fusionó en main. Detalle: `docs/ml-heads/day303_emecas_desde_cero.md`.

Reglas de trabajo: medir, no votar; predicción escrita antes de medir; si algo no da lo esperado, PARAR. Comandos
exactos y completos, en orden, diciendo dónde se ejecuta cada uno (Mac / defender / client). Ficheros generados
como descarga, verificados con sha256 (nada de pegar heredocs largos: comillas tipográficas). Nunca `printf >>`
sobre ficheros del repo (DAY303: `.gitignore` sin salto final rompió una regla): patchers --check/--apply con
marca. awk con `LC_ALL=C`. `git grep`, nunca `grep -rn .` en la raíz. El JSON es la ley.
Compilar siempre en producción (defecto) y el pipeline completo (`make pipeline-build`). EMECAS se lanza con
`nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &` y se vigila con
`bash scripts/emecas/emecas_watch.sh 60`. `make lab-e2e` corre los cinco E2E del lab con veredicto (~65 min).

ORDEN DECIDIDO POR ALONSO (DAY303):
1. Rama nueva desde main: deprecar rag/rag-security de forma certificada. Inventario de partida (K6, DAY303):
   Makefile (27 líneas: rag-build en pipeline-build, rag-start en pipeline-start y pipeline-start-x86-libpcap,
   ctest en test-components, pipeline-status y conteo 6/6 → 5/5, stop, logs, semillas 2581-2654), Vagrantfile (6),
   etcd-server/config/ml-defender-rag-security.service + install-systemd-units.sh, set-build-profile.sh
   (COMPONENTS), AppArmor (security/apparmor/argus.rag-security, tools/apparmor/ml-defender-rag-security,
   tools/apparmor-promote.sh), Falco y setup-filesystem de vagrant/hardened-x86 y hardened-arm64,
   tools/provision.sh, scripts/pipeline_health.sh, tests que lo nombran (plugins/test-message/test_integ_4e.cpp,
   common/tests/test_crypto_autonomy.cpp, libs/seed-client/tests/test_seed_client.cpp), common-rag-ingester/build
   versionado. Medido K8: rag-security no se registra en etcd (MAC verification failed) desde septiembre.
   Criterio de HECHO: `git grep` de rag-security/rag-start/rag-build/rag/build vacío fuera de docs e históricos,
   y EMECAS+++ verde con 5/5 componentes. Valorar en la misma rama DEBT-PIPELINE-STATUS-LIVENESS-001.
2. Interruptor de cabezas (DEBT-HEADS-SWITCH-001, decisiones DAY300 en el BACKLOG).
3. Caducidad de flujos (DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001): la tabla de flujos del
   sniffer (espacio de usuario) tiene tope (16 × 10 000, LRU), así que la memoria NO crece sin límite; lo roto es
   que un flujo nunca caduca por inactividad y sus rasgos (flow_packet_count, flow_completion_rate) se deforman.
   Primeras medidas: RAM por flujo con la tabla llena, y la batería de la etapa 2 antes/después. Predicción
   (DAY303): no hará falta reentrenar, porque caducar acerca el servicio al entrenamiento; decidir con los datos.
4. Después (≈ 2 semanas): REA (BACKLOG-SEC-REA-HARDENING-AUDIT-001): primero auditoría manual del sniffer con
   predicción escrita, luego la fase asíncrona en Jenkins. Revisar antes la licencia de REA.
""".format(dur=DUR)

BACKLOG_TXT = """

## Cierre DAY303 {M}

Resuelto DAY303 (EMECAS+++ production desde cero, {dur}, rc=0): perfil por defecto production; pipeline-build
compila tools y termina con set-build-profile; rag por perfil; clean-host-builds en el Mac antes de vagrant up;
emecas-frescura con sello; puerta e2e/perf del firewall con root (ctest_label_gate.sh); lab-e2e (reinicio
antes/ordenada/kill9, protegidos, mitigacion) con veredictos estrictos; espera ESTABLE con fondo ICMP controlado;
tools/build y crypto-transport/build fuera de git; emecas_run.sh / emecas_watch.sh.

### DEBT-RAG-DEPRECATION-CERT-001 — ABIERTA, siguiente rama (decision de Alonso DAY303)
Deprecado de rag/rag-security nunca certificado: se quito parte del Makefile pero sigue compilandose, arrancando,
perfilado en AppArmor/Falco, con semillas y tests que lo nombran. Inventario K6 en docs/ml-heads/prompt_day304.md.

### DEBT-PIPELINE-STATUS-LIVENESS-001 — ABIERTA
pipeline-status solo comprueba que el proceso existe. rag-security salia RUNNING sin registrarse en etcd desde
septiembre (MAC verification failed, K8). Comprobar registro en etcd o heartbeat aceptado por componente.

### DEBT-APPARMOR-FIREWALL-BIN-NAME-001 — ABIERTA
tools/apparmor-promote.sh usa firewall_acl_agent; el binario es firewall-acl-agent (FIREWALL_BIN). Si el perfil
usa ese path, AppArmor no confina el binario real. Medir en la VM hardened.

### DEBT-FW-LEGACY-LINK-DIR-001 — ABIERTA
firewall-acl-agent/build es un directorio real: ln -sfn $(FIREWALL_BUILD_DIR) $(FIREWALL_LEGACY_LINK) crea el
enlace DENTRO. (clean-host-builds lo borra en EMECAS; en el dia a dia persiste.)

### DEBT-BUILD-INCREMENTAL-001 — ABIERTA
pipeline-build recompila todo en cada llamada (DAY303: 08:35-08:48 y 09:43-09:56 sin cambios de fuente
intermedios relevantes). Medir que cmake/make reconfigura y por que.

### DEBT-EMECAS-SENSOR-VMS-001 — ABIERTA
EMECAS levanta defender, client y suricata; zeek y wazuh no entran en el gate (make up levanta las 5).

### DEBT-LAB-ESTABLE-LECTOR-001 — MITIGADA
day288_esperar_estable.sh necesita trafico: el lector del kernel solo escribe claves con paquetes. Mitigado con
fondo ICMP controlado (d303_esperar_estable_lab.sh). Solucion de fondo: un latido del lector por sondeo.

### DEBT-LAB-VIVOS-DIA-001 — ABIERTA
lab_corrida_defender.sh con DIA invalido (no dayNNN) hace que el E2E diga "quedan procesos vivos": mensaje
enganoso. Distinguir DIA invalido de proceso vivo.

### DEBT-GIT-BUILD-ARTIFACTS-001 — ABIERTA
Quedan versionados common-rag-ingester/build (5 ficheros; va con DEBT-RAG-DEPRECATION-CERT-001) y
plugin-loader/build-enterprise (4; medir quien lo usa antes de quitarlo).

### DEBT-BUILD-BASURA-001 — ABIERTA
Directorios sin dueno en el Makefile: common/build-vault, plugin-loader/build-debug, ml-detector/build_detector_test,
sniffer/build-prod (los build-* los borra clean-host-builds; el resto persiste).

### DEBT-MAKE-DEAD-TARGETS-001 — ABIERTA
test-alert-client y test-wire-protocol no los llama nadie.

### DEBT-VAULT-COMMON-BUILD-001 — ABIERTA
Los actos de Vault reconfiguran common/build con ARGUS_VAULT_ENABLED=ON y lo instalan con sudo make install: en
una sesion manual contamina los builds OSS posteriores (en EMECAS lo limpia clean-host-builds en la siguiente).

### DEBT-PROVISION-LIBS-PROFILE-001 — ABIERTA (a medir)
provision.sh compila las librerias con CMAKE_BUILD_TYPE=Release, no con los flags del perfil production; medir
si pipeline-build las recompila con CMAKE_FLAGS y cual queda instalada en /usr/local/lib.

### DEBT-SANITIZERS-PREPROD-001 — ABIERTA (decision de Alonso DAY303)
Pase ASan/TSan (emecas++++) solo en hardware real de preproduccion/produccion. Existe tsan-all; falta objetivo asan.

### DEBT-SYNTH-E2E-FAIL-FAST-001 — ABIERTA
test-e2e-synthetic-full espera "Injection complete" con timeout 60 y no reacciona a "Error" del injector:
con etcd-server caido tardo 60 s en fallar y sin decir por que. Fallar al ver Error con su mensaje.

### DEBT-MAKE-PREFLIGHT-001 — PROPUESTA (DAY303)
make preflight de segundos antes de cualquier corrida larga: expandir cada vagrant ssh -c (uniendo lineas de
continuacion) y comprobar con shlex 4 argumentos; ficheros del repo con salto de linea final; ningun build*/
versionado; LAB_E2E_DIA con formato dayNNN; patrones de estado que no casen con su propio pgrep.
Habria cazado 3-4 de los fallos de DAY303 antes de lanzar nada.

### Practica DAY303 (Alonso)
Ramas pequenas con su EMECAS al final; EMECAS cuando el Mac no se usa (de noche).

### Leccion DAY303
Nunca printf >> sobre ficheros del repo: .gitignore no terminaba en salto de linea y el anadido rompio la regla
seed-repro/*.json. Siempre patcher que compruebe el salto final.
""".format(M=M, dur=DUR)

out = {
    Path("docs/ml-heads/day303_emecas_desde_cero.md"): RES,
    Path("docs/ml-heads/paper_apoyo_day303.md"): PAPER,
    Path("docs/ml-heads/prompt_day304.md"): PROMPT,
}
for p, t in out.items():
    print("== " + str(p) + " (" + str(len(t.splitlines())) + " lineas)")
print("== docs/BACKLOG.md: +" + str(len(BACKLOG_TXT.splitlines())) + " lineas al final")
if sys.argv[2] == "--check":
    print("\n--- vista previa de los veredictos que se documentan ---")
    print(VERED or "(sin lineas de veredicto)")
    sys.exit(0)
for p, t in out.items():
    p.write_text(t, encoding="utf-8")
b = BACK.read_text(encoding="utf-8")
if not b.endswith("\n"):
    b += "\n"
BACK.write_text(b + BACKLOG_TXT, encoding="utf-8")
print("APLICADO", M)