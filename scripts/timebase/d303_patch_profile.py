#!/usr/bin/env python3
# DAY303 [ARGUS-PROFILE-D303]: perfil por defecto production y fuera los build-debug fijos.
# Decision de Alonso DAY303: compilar y probar siempre en produccion (maxima confianza en el compilador).
#  - Makefile: PROFILE ?= production; ayuda; pipeline-build incluye tools (los inyectores del E2E sintetico
#    llevaban desde junio sin recompilarse: medido); inyectores desde $(TOOLS_BUILD_DIR); etcd-server de Vault en
#    build-vault-$(PROFILE) (antes reconfiguraba build-debug con ARGUS_VAULT_ENABLED=ON); rag-ingester-start desde
#    $(RAG_INGESTER_BUILD_DIR)
#  - scripts/pipeline_health.sh: build-debug -> build-active
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_profile.py --check | --apply
import difflib
import re
import sys
from pathlib import Path

MARCA = "[ARGUS-PROFILE-D303]"
MK = Path("Makefile")
PH = Path("scripts/pipeline_health.sh")
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_profile.py --check | --apply")
    sys.exit(2)
mk = MK.read_text(encoding="utf-8")
ph = PH.read_text(encoding="utf-8")
if MARCA in mk or MARCA in ph:
    print("YA APLICADO, no se toca nada")
    sys.exit(1)
errores = []


def cambiar(texto, viejo, nuevo, veces, donde):
    n = texto.count(viejo)
    if n != veces:
        errores.append(donde + ": se esperaban " + str(veces) + " apariciones de " + repr(viejo) + ", hay " + str(n))
        return texto
    return texto.replace(viejo, nuevo)


# 1. perfil por defecto + ayuda
mk2 = cambiar(mk, "\nPROFILE ?= debug\n",
              "\n# " + MARCA + " defecto production (decision de Alonso DAY303: compilar y probar siempre en\n"
              "# produccion). Debug, tsan y asan siguen disponibles con PROFILE=... explicito.\n"
              "PROFILE ?= production\n", 1, "Makefile PROFILE")
mk2 = cambiar(mk2, "[DEFAULT] \u2014 desarrollo diario", "\u2014 depuracion a mano (PROFILE=debug)", 1, "ayuda debug")
mk2 = cambiar(mk2, "production  - Optimized (-O3, LTO, march=native)",
              "production  - Optimized (-O3, LTO, march=native) [DEFAULT]", 1, "ayuda production")

# 2. pipeline-build incluye tools
pb = [l for l in mk2.split("\n") if l.startswith("pipeline-build:")]
if len(pb) != 1:
    errores.append("Makefile: lineas 'pipeline-build:' = " + str(len(pb)))
elif re.search(r"\stools(\s|$)", pb[0]):
    errores.append("Makefile: pipeline-build ya incluye tools")
else:
    mk2 = mk2.replace(pb[0] + "\n", pb[0] + " tools\n", 1)

# 3. inyectores del E2E sintetico
mk2 = cambiar(mk2, "/vagrant/tools/build-debug/", "$(TOOLS_BUILD_DIR)/", 2, "inyectores")

# 4. etcd-server de Vault en su propio directorio (no reconfigura el del perfil)
flags = [l for l in mk2.split("\n") if re.match(r"^\s*CMAKE_FLAGS\s*[:+?]?=", l)]
if not flags:
    errores.append("Makefile: no encuentro la definicion de CMAKE_FLAGS")
elif any('"' in l for l in flags):
    errores.append("Makefile: CMAKE_FLAGS lleva comillas dobles (romperia vagrant ssh -c \"...\")")
VAULT_DIR = "/vagrant/etcd-server/build-vault-$(PROFILE)"
mk2 = cambiar(mk2, "cd /vagrant/etcd-server/build-debug && cmake .. -DARGUS_VAULT_ENABLED=ON",
              "mkdir -p " + VAULT_DIR + " && cd " + VAULT_DIR + " && cmake $(CMAKE_FLAGS) .. -DARGUS_VAULT_ENABLED=ON",
              1, "cmake Vault")
mk2 = cambiar(mk2, "/vagrant/etcd-server/build-debug/etcd-server", VAULT_DIR + "/etcd-server", 2, "binario Vault")

# 5. rag-ingester-start
mk2 = cambiar(mk2, "./build-debug/rag-ingester ", "$(RAG_INGESTER_BUILD_DIR)/rag-ingester ", 1, "rag-ingester")

restos = [str(i + 1) + ": " + l.strip()[:100] for i, l in enumerate(mk2.split("\n")) if "build-debug" in l]
if restos:
    errores.append("Makefile: quedan build-debug fijos: " + " | ".join(restos))

# 6. pipeline_health.sh
ph2 = cambiar(ph, "/build-debug/", "/build-active/", 5, str(PH))
if ph2 != ph:
    ph2 = ph2.replace("\n", "\n# " + MARCA + " rutas via build-active (enlace del perfil activo, set-build-profile)\n", 1)

if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)
print("=== " + sys.argv[1] + ": anclas encontradas, 0 errores ===")
print("CMAKE_FLAGS:")
for l in flags:
    print("  " + l)
for p, a, b in ((MK, mk, mk2), (PH, ph, ph2)):
    print("".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                       fromfile="a/" + str(p), tofile="b/" + str(p), n=1)))
if sys.argv[1] == "--apply":
    MK.write_text(mk2, encoding="utf-8")
    PH.write_text(ph2, encoding="utf-8")
    print("APLICADO", MARCA)
