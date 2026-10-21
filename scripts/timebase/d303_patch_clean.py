#!/usr/bin/env python3
# DAY303 [ARGUS-CLEAN-D303]: EMECAS desde cero de verdad, y lo que corre es lo que se compila.
# Medido en K1-K7 (DAY303):
#  - clean-all no limpiaba common/build (vault-client), host-engine, correlation-engine ni rag
#  - todos los build-active apuntaban a build-debug desde el 14-oct; set-build-profile solo corre en
#    bootstrap y ANTES de pipeline-build (se salta lo que aun no existe)
#  - rag compilaba en rag/build (sin perfil) y arrancaba de rag/build-active = binario debug del 14-abr
#  - tools/build (enlace generado) estaba trackeado en git
# Cambios:
#  1. pipeline-build termina con set-build-profile
#  2. RAG_BUILD_DIR por perfil; rag-start arranca de $(RAG_BUILD_DIR). El deprecado de rag va en su
#     propia rama tras el merge (decision de Alonso DAY303); aqui solo se hace coherente
#  3. clean-all limpia ademas rag, vault-client, host-engine y correlation-engine
#  4. emecas: clean-all tras vagrant up, sello de inicio, y emecas-frescura tras bootstrap
#  5. tools/build fuera del indice de git y en .gitignore (solo con --apply)
# Uso (Mac, raiz del repo): python3 scripts/timebase/d303_patch_clean.py --check | --apply
import difflib
import re
import subprocess
import sys
from pathlib import Path

MARCA = "[ARGUS-CLEAN-D303]"
MK = Path("Makefile")
GI = Path(".gitignore")
FRESCURA = Path("scripts/emecas/emecas_frescura.sh")
SELLO = "/vagrant/logs/lab/emecas_inicio.stamp"
if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
    print("uso: d303_patch_clean.py --check | --apply")
    sys.exit(2)
mk = MK.read_text(encoding="utf-8")
gi = GI.read_text(encoding="utf-8")
if MARCA in mk:
    print("YA APLICADO, no se toca nada")
    sys.exit(1)
errores = []


def cambiar(texto, viejo, nuevo, veces, donde):
    n = texto.count(viejo)
    if n != veces:
        errores.append(donde + ": se esperaban " + str(veces) + " apariciones de " + repr(viejo) + ", hay " + str(n))
        return texto
    return texto.replace(viejo, nuevo)


def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


if not FRESCURA.is_file():
    errores.append("falta " + str(FRESCURA) + " (descargalo y muevelo antes)")

# 1. pipeline-build termina con set-build-profile
if mk.count("\nset-build-profile:") != 1:
    errores.append("Makefile: no encuentro un unico objetivo set-build-profile")
pb = [l for l in mk.split("\n") if l.startswith("pipeline-build:")]
mk2 = mk
if len(pb) != 1:
    errores.append("Makefile: lineas 'pipeline-build:' = " + str(len(pb)))
else:
    mk2 = cambiar(mk2, "\n" + pb[0] + "\n\n",
                  "\n# " + MARCA + " al final, set-build-profile: build-active -> build-$(PROFILE) de lo recien\n"
                  "# compilado (antes solo corria en bootstrap, ANTES de compilar, y se saltaba lo que no existia)\n"
                  + pb[0] + "\n\t@$(MAKE) set-build-profile\n\n", 1, "pipeline-build (sin cuerpo)")

# 2. rag coherente con el perfil
rr = re.findall(r"^RAG_BUILD_DIR[ \t]*:=[ \t]*/vagrant/rag/build[ \t]*$", mk2, flags=re.M)
if len(rr) != 1:
    errores.append("Makefile: definicion RAG_BUILD_DIR := /vagrant/rag/build encontrada " + str(len(rr)) + " veces")
else:
    mk2 = mk2.replace(rr[0], "# " + MARCA + " rag por perfil como el resto (su deprecado va en rama propia)\n"
                      "RAG_BUILD_DIR := /vagrant/rag/build-$(PROFILE)", 1)
mk2 = cambiar(mk2, "cd /vagrant/rag/build-active && ./rag-security", "cd $(RAG_BUILD_DIR) && ./rag-security", 1, "rag-start cd")
mk2 = cambiar(mk2, "(from /vagrant/rag/build-active)", "(from $(RAG_BUILD_DIR))", 1, "rag-start echo")

# 3. clean-all
i = mk2.find("\nclean-all:")
if i < 0 or mk2.count("\nclean-all:") != 1:
    errores.append("Makefile: no encuentro un unico objetivo clean-all")
else:
    m = re.compile(r"\n(?![\t#])").search(mk2, i + 1)
    j = m.start() if m else len(mk2)
    bloque = mk2[i:j]
    ancla = "\t@$(MAKE) clean-libs\n"
    if bloque.count(ancla) != 1:
        errores.append("clean-all: se esperaba 1 '@$(MAKE) clean-libs' dentro del objetivo, hay " + str(bloque.count(ancla)))
    else:
        nuevo = ("\t@echo \"  - " + MARCA + " rag, vault-client (common/build), host-engine, correlation-engine...\"\n"
                 "\t@vagrant ssh -c \"rm -rf /vagrant/rag/build /vagrant/rag/build-*\"\n"
                 "\t@$(MAKE) vault-client-clean\n"
                 "\t@$(MAKE) host-engine-clean\n"
                 "\t@$(MAKE) correlation-engine-clean\n")
        mk2 = mk2[:i] + bloque.replace(ancla, nuevo + ancla, 1) + mk2[j:]
for t in ("vault-client-clean", "host-engine-clean", "correlation-engine-clean"):
    if mk2.count("\n" + t + ":") != 1:
        errores.append("Makefile: no encuentro un unico objetivo " + t)

# 4. emecas
mk2 = cambiar(mk2, "\tvagrant up defender client suricata\n\t$(MAKE) bootstrap\n",
              "\tvagrant up defender client suricata\n"
              "\t$(MAKE) clean-all\n"
              "\tvagrant ssh defender -c \"mkdir -p /vagrant/logs/lab && date -u > " + SELLO + "\"\n"
              "\t$(MAKE) bootstrap\n"
              "\t$(MAKE) emecas-frescura\n", 1, "emecas (up + bootstrap)")
mk2 = cambiar(mk2, "\nemecas++: emecas\n",
              "\n# " + MARCA + " emecas-frescura: cada binario del pipeline existe en build-$(PROFILE), build-active\n"
              "# apunta ahi y es mas nuevo que el sello escrito tras clean-all. Fuera de EMECAS, sin sello:\n"
              "#   vagrant ssh defender -c \"bash /vagrant/scripts/emecas/emecas_frescura.sh production\"\n"
              ".PHONY: emecas-frescura\n"
              "emecas-frescura:\n"
              "\t@vagrant ssh defender -c \"bash /vagrant/" + str(FRESCURA) + " $(PROFILE) " + SELLO + "\"\n"
              "\nemecas++: emecas\n", 1, "objetivo emecas-frescura")

# 5. tools/build
rc, out = git("ls-files", "tools/build")
tools_trackeado = (rc == 0 and out == "tools/build")
# el enlace lo recrea el objetivo tools via variable (medido DAY303: TOOLS_LEGACY_LINK := /vagrant/tools/build,
# ln -sfn $(TOOLS_BUILD_DIR) $(TOOLS_LEGACY_LINK)); se acepta el literal o la variable
legacy_def = re.search(r"^TOOLS_LEGACY_LINK[ \t]*:=[ \t]*/vagrant/tools/build[ \t]*$", mk2, flags=re.M)
lineas_ln = [l.strip()[:140] for l in mk2.split("\n")
             if "ln -s" in l and ("tools/build" in l or (legacy_def and "$(TOOLS_LEGACY_LINK)" in l))]
if tools_trackeado and not lineas_ln:
    errores.append("Makefile: no encuentro quien recrea el enlace tools/build (ln -s ... tools/build); no lo saco de git")
gi2 = gi
if tools_trackeado and not re.search(r"^/?tools/build/?$", gi, flags=re.M):
    gi2 = gi2.rstrip("\n") + "\n# " + MARCA + " enlace generado por el objetivo tools, no se versiona\n/tools/build\n"
rc_rag, _ = git("check-ignore", "-q", "rag/build-production/rag-security")
if rc_rag != 0:
    gi2 = gi2.rstrip("\n") + "\n# " + MARCA + " builds por perfil de rag\n/rag/build-*/\n"

restos = [str(k + 1) + ": " + l.strip()[:100] for k, l in enumerate(mk2.split("\n")) if "rag/build-active" in l]
if restos:
    errores.append("Makefile: quedan rag/build-active: " + " | ".join(restos))

if errores:
    print("PARO: el patcher no toca nada.")
    for e in errores:
        print(" -", e)
    sys.exit(1)
print("=== " + sys.argv[1] + ": anclas encontradas, 0 errores ===")
print("tools/build trackeado en git:", tools_trackeado)
for l in lineas_ln:
    print("  recrea tools/build:", l)
print("rag/build-production ya ignorado por .gitignore:", rc_rag == 0)
for p, a, b in ((MK, mk, mk2), (GI, gi, gi2)):
    print("".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                       fromfile="a/" + str(p), tofile="b/" + str(p), n=1)))
if sys.argv[1] == "--apply":
    MK.write_text(mk2, encoding="utf-8")
    GI.write_text(gi2, encoding="utf-8")
    if tools_trackeado:
        rc, out = git("rm", "--cached", "-q", "tools/build")
        print("git rm --cached tools/build: rc=" + str(rc), out)
    print("APLICADO", MARCA)
