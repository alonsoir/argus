#!/usr/bin/env python3
"""
patch_ddos_build_wiring.py  --  DAY273

Cablea test_ddos_kernel_agg en la build:

  sniffer/CMakeLists.txt   bloque al FINAL del fichero (tras el ultimo test):
                             add_executable + add_test de la parte PURA (sin root).
                             Protegido con if(NOT USE_LIBPCAP): Variant B no tiene libbpf.
                             Como es ctest, lo ejecuta tambien `make test-components`.
  Makefile (raiz)          dos targets, insertados justo antes de `test-components:`:
                             sniffer-ddos-agg-test      parte pura via ctest (sin root)
                             sniffer-ddos-agg-bpf-test  --bpf contra sniffer.bpf.o (root)

  --dry / --apply / --check      (mismo estilo que los patchers anteriores)

Garantias: idempotente; anclas por texto que deben aparecer exactamente una vez;
estado parcial => aborta; los DOS ficheros se parchean juntos o ninguno; NO commitea.
Se ejecuta desde la RAIZ del repo (en el Mac o en la VM; no compila nada).

Exit codes: 0 ok | 1 no aplicado (--check) | 2 estado/anclas invalidos | 4 error de E/S
"""
import argparse
import difflib
import os
import re
import sys
import tempfile

CMAKE_DEFAULT = "sniffer/CMakeLists.txt"
MAKE_DEFAULT = "Makefile"
TEST_SRC_DEFAULT = "sniffer/tests/test_ddos_kernel_agg.cpp"
HDR_DEFAULT = "sniffer/include/ddos_kernel_agg.hpp"

M_CMAKE = "DDOS-KAGG-D273:CMAKE"
M_MAKE = "DDOS-KAGG-D273:MAKE"

ANCHOR_MAKE = "test-components: correlation-engine-test\n"
TARGET_UNIT = "sniffer-ddos-agg-test"
TARGET_BPF = "sniffer-ddos-agg-bpf-test"
TEST_NAME = "test_ddos_kernel_agg"

# Recetas v2: `cmake .` re-configura si CMakeLists.txt cambio. Sin el, la primera vez tras
# cablear un test nuevo, `cmake --build . --target <nuevo>` falla con "No hay ninguna regla
# para construir el objetivo": el Makefile de nivel superior aun no conoce el target.
# Tambien se separan los --target: con varios a la vez, el segundo se resuelve contra el
# Makefile viejo aunque el primero lo regenere.
NEW_UNIT_CMD = ('\t@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && cmake . > /dev/null && '
                'cmake --build . --target test_ddos_kernel_agg && '
                'ctest -R test_ddos_kernel_agg --output-on-failure"\n')
NEW_BPF_CMD = ('\t@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && cmake . > /dev/null && '
               'cmake --build . --target bpf_program && '
               'cmake --build . --target test_ddos_kernel_agg && '
               'sudo ./test_ddos_kernel_agg --bpf ./sniffer.bpf.o"\n')
# Recetas v1 (primera version del patcher), que se migran a v2 con --apply:
OLD_UNIT_CMD = ('\t@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && '
                'cmake --build . --target test_ddos_kernel_agg && '
                'ctest -R test_ddos_kernel_agg --output-on-failure"\n')
OLD_BPF_CMD = ('\t@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && '
               'cmake --build . --target bpf_program test_ddos_kernel_agg && '
               'sudo ./test_ddos_kernel_agg --bpf ./sniffer.bpf.o"\n')

# NOTA: plantillas SIN f-string a proposito (CMake usa ${...}); @MARK@ se sustituye.
CMAKE_BLOCK = """# ============================================================================
# @MARK@  Agregador DDoS en-kernel: lector userspace (DAY 273)
# Parte pura (compute_delta, ip_to_string): ctest, sin root ni kernel.
# El modo --bpf (BPF_PROG_TEST_RUN contra sniffer.bpf.o) requiere root: lo lanza
# el target sniffer-ddos-agg-bpf-test del Makefile raiz.
# Solo Variant A (eBPF): la Variant B (libpcap) no tiene libbpf.
# ============================================================================
if(NOT USE_LIBPCAP)
  add_executable(test_ddos_kernel_agg
          tests/test_ddos_kernel_agg.cpp
  )
  target_include_directories(test_ddos_kernel_agg PRIVATE
          ${CMAKE_SOURCE_DIR}/include
          ${LIBBPF_INCLUDE_DIRS}
  )
  if(LIBBPF_LIBRARY_DIRS)
    target_link_directories(test_ddos_kernel_agg PRIVATE ${LIBBPF_LIBRARY_DIRS})
  endif()
  target_link_libraries(test_ddos_kernel_agg PRIVATE
          ${LIBBPF_LIBRARIES}
  )
  add_test(NAME test_ddos_kernel_agg COMMAND test_ddos_kernel_agg)
  message(STATUS "🧪 Unit Test: test_ddos_kernel_agg configured (DAY 273 - agregador DDoS en-kernel, parte pura)")
endif()
"""

# Las lineas de receta llevan TAB real (\\t en la plantilla se sustituye abajo).
MAKE_BLOCK = """# ============================================================================
# @MARK@  Agregador DDoS en-kernel (DAY 273)
#   sniffer-ddos-agg-test      parte pura (ctest, sin root). La corre tambien test-components.
#   sniffer-ddos-agg-bpf-test  BPF_PROG_TEST_RUN contra el sniffer.bpf.o real:
#                              requiere root y kernel con BPF; NO entra en test-all.
# ============================================================================
.PHONY: sniffer-ddos-agg-test sniffer-ddos-agg-bpf-test

sniffer-ddos-agg-test:
<TAB>@echo "🧪 test_ddos_kernel_agg (parte pura, sin root)..."
@UNIT_CMD@

sniffer-ddos-agg-bpf-test:
<TAB>@echo "🧪 test_ddos_kernel_agg --bpf (requiere root y kernel con BPF)..."
@BPF_CMD@

""".replace("<TAB>", "\t").replace("@UNIT_CMD@", NEW_UNIT_CMD.rstrip("\n")).replace("@BPF_CMD@", NEW_BPF_CMD.rstrip("\n"))


class PatchError(Exception):
    def __init__(self, msg, code=2):
        super().__init__(msg)
        self.code = code


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            return f.read()
    except OSError as e:
        raise PatchError(f"no puedo leer {path}: {e}", 4)


def unbalanced(text):
    """Bloques CMake abiertos sin cerrar (heuristica por lineas, ignora comentarios)."""
    pairs = [("if", "endif"), ("foreach", "endforeach"), ("function", "endfunction"),
             ("macro", "endmacro"), ("while", "endwhile")]
    bad = []
    for op, cl in pairs:
        o = len(re.findall(r"^[ \t]*%s[ \t]*\(" % op, text, re.M | re.I))
        c = len(re.findall(r"^[ \t]*%s[ \t]*\(" % cl, text, re.M | re.I))
        if o != c:
            bad.append((op, o, cl, c))
    return bad


def count_re(text, pattern):
    return len(re.findall(pattern, text, re.M))


def build_cmake(text):
    if "\r" in text:
        raise PatchError("CMakeLists.txt tiene CR (CRLF); el patcher espera LF.")
    for needle, what in (("enable_testing()", "enable_testing()"),
                         ("option(USE_LIBPCAP", "option(USE_LIBPCAP"),
                         ("pkg_check_modules(LIBBPF", "pkg_check_modules(LIBBPF")):
        if text.count(needle) != 1:
            raise PatchError(f"ancla '{what}' aparece {text.count(needle)} veces (debe ser 1); "
                             f"el CMakeLists ha cambiado respecto a lo medido. No toco nada.")
    if TEST_NAME in text:
        raise PatchError(f"'{TEST_NAME}' ya aparece en el CMakeLists sin nuestro marcador: "
                         f"revisar a mano; no toco nada.")
    bad = unbalanced(text)
    if bad:
        raise PatchError(f"el CMakeLists tiene bloques sin cerrar {bad}; el final del fichero "
                         f"no esta a nivel superior. No toco nada.")
    out = text if text.endswith("\n") else text + "\n"
    out += "\n" + CMAKE_BLOCK.replace("@MARK@", M_CMAKE)
    verify_cmake(out)
    return out


def build_make(text):
    if "\r" in text:
        raise PatchError("Makefile tiene CR (CRLF); el patcher espera LF.")
    if text.count(ANCHOR_MAKE) != 1:
        raise PatchError(f"ancla {ANCHOR_MAKE!r} aparece {text.count(ANCHOR_MAKE)} veces (debe ser 1). "
                         f"No toco nada.")
    if count_re(text, r"^SNIFFER_BUILD_DIR[ \t]*[:?+]?=") < 1:
        raise PatchError("no encuentro la definicion de SNIFFER_BUILD_DIR en el Makefile; "
                         "los targets nuevos dependen de ella. No toco nada.")
    for t in (TARGET_UNIT, TARGET_BPF):
        if count_re(text, r"^%s[ \t]*:" % re.escape(t)) != 0:
            raise PatchError(f"el target '{t}' ya existe sin nuestro marcador; no toco nada.")
    i = text.index(ANCHOR_MAKE)
    out = text[:i] + MAKE_BLOCK.replace("@MARK@", M_MAKE) + text[i:]
    verify_make(out)
    return out


def verify_cmake(text):
    if text.count(M_CMAKE) != 1:
        raise PatchError(f"marcador CMake aparece {text.count(M_CMAKE)} veces, esperaba 1")
    if text.count("add_executable(test_ddos_kernel_agg") != 1:
        raise PatchError("add_executable(test_ddos_kernel_agg debe aparecer exactamente 1 vez")
    if text.count("add_test(NAME test_ddos_kernel_agg COMMAND test_ddos_kernel_agg)") != 1:
        raise PatchError("add_test de test_ddos_kernel_agg debe aparecer exactamente 1 vez")
    if not text.index("enable_testing()") < text.index(M_CMAKE):
        raise PatchError("el bloque nuevo esta antes de enable_testing()")
    bad = unbalanced(text)
    if bad:
        raise PatchError(f"bloques CMake sin cerrar tras parchear {bad}")


def verify_make(text):
    if text.count(M_MAKE) != 1:
        raise PatchError(f"marcador Makefile aparece {text.count(M_MAKE)} veces, esperaba 1")
    for t in (TARGET_UNIT, TARGET_BPF):
        n = count_re(text, r"^%s[ \t]*:" % re.escape(t))
        if n != 1:
            raise PatchError(f"target '{t}' aparece {n} veces, esperaba 1")
    i = text.index(M_MAKE)
    j = text.index(ANCHOR_MAKE)
    if not i < j:
        raise PatchError("el bloque nuevo no esta antes de `test-components:`")
    for line in text[i:j].splitlines():
        if line.strip().startswith("@") and not line.startswith("\t"):
            raise PatchError(f"linea de receta sin TAB inicial: {line!r}")
    if text.count(NEW_UNIT_CMD) != 1 or text.count(NEW_BPF_CMD) != 1:
        raise PatchError("las recetas no estan en la version v2 (con `cmake .`)")


def upgrade_make(text):
    """Migra las recetas v1 a v2. Devuelve (texto, cambiado)."""
    out, changed = text, False
    for old, new in ((OLD_UNIT_CMD, NEW_UNIT_CMD), (OLD_BPF_CMD, NEW_BPF_CMD)):
        n = out.count(old)
        if n > 1:
            raise PatchError(f"la receta v1 aparece {n} veces; no toco nada.")
        if n == 1:
            out, changed = out.replace(old, new), True
    return out, changed


def state(cm, mk):
    a, b = cm.count(M_CMAKE), mk.count(M_MAKE)
    if a == 0 and b == 0:
        return "clean", a, b
    if a == 1 and b == 1:
        return "applied", a, b
    return "partial", a, b


def udiff(name, a, b):
    return "".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                        fromfile=name + " (antes)", tofile=name + " (despues)", n=2))


def write_tmp(path, text):
    d = os.path.dirname(os.path.abspath(path))
    st = os.stat(path)
    fd, tmp = tempfile.mkstemp(prefix=".ddos_wiring_", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, st.st_mode & 0o7777)
    return tmp


def atomic_write_pair(p1, new1, old1, p2, new2):
    """Los dos o ninguno: si falla el segundo replace se restaura el primero."""
    t1 = t2 = None
    try:
        t1 = write_tmp(p1, new1)
        t2 = write_tmp(p2, new2)
        os.replace(t1, p1)
        t1 = None
        try:
            os.replace(t2, p2)
            t2 = None
        except OSError:
            tr = write_tmp(p1, old1)
            os.replace(tr, p1)
            raise
    finally:
        for t in (t1, t2):
            if t and os.path.exists(t):
                os.unlink(t)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true", help="muestra el diff, no escribe")
    g.add_argument("--apply", action="store_true", help="aplica")
    g.add_argument("--check", action="store_true", help="verifica que esta aplicado")
    ap.add_argument("--cmake", default=CMAKE_DEFAULT)
    ap.add_argument("--makefile", default=MAKE_DEFAULT)
    ap.add_argument("--test-src", default=TEST_SRC_DEFAULT)
    ap.add_argument("--header", default=HDR_DEFAULT)
    a = ap.parse_args()

    try:
        for p, what in ((a.test_src, "el test"), (a.header, "la cabecera del lector")):
            if not os.path.isfile(p):
                raise PatchError(f"falta {p} ({what}): colocalo ahi antes de cablear la build. "
                                 f"Ejecuta desde la raiz del repo.")
        cm, mk = read_text(a.cmake), read_text(a.makefile)
        st, na, nb = state(cm, mk)

        if st == "applied":
            verify_cmake(cm)
            mk2, migrated = upgrade_make(mk)
            if a.check:
                if migrated:
                    print("check   : recetas v1 (sin `cmake .`); ejecuta --apply para migrarlas a v2")
                    return 1
                verify_make(mk)
                print(f"check   : estructura OK (CMake={na}, Makefile={nb}, recetas v2)")
                return 0
            if migrated:
                verify_make(mk2)
                print(udiff(a.makefile, mk, mk2), end="")
                if a.dry:
                    print("\n--dry: no se ha escrito nada.")
                    return 0
                tmp = write_tmp(a.makefile, mk2)
                os.replace(tmp, a.makefile)
                print(f"\nMIGRADO a recetas v2: {a.makefile}")
                return 0
            verify_make(mk)
            print("ya aplicado (recetas v2); nada que hacer.")
            return 0

        if a.check:
            if st == "clean":
                print("check   : NO aplicado")
                return 1
            raise PatchError(f"estado parcial (marcadores CMake={na}, Makefile={nb})")

        if st == "partial":
            raise PatchError(f"estado parcial (marcadores CMake={na}, Makefile={nb}). "
                             f"Deshaz con `git checkout -- {a.cmake} {a.makefile}`.")

        cm1, mk1 = build_cmake(cm), build_make(mk)
        print(udiff(a.cmake, cm, cm1), end="")
        print(udiff(a.makefile, mk, mk1), end="")

        if a.dry:
            print("\n--dry: no se ha escrito nada.")
            print("Nota: solo se verifica la ESTRUCTURA; la prueba real es `make sniffer-ddos-agg-test`.")
            return 0
        atomic_write_pair(a.cmake, cm1, cm, a.makefile, mk1)
        print(f"\nAPLICADO: {a.cmake} y {a.makefile}")
        print("Siguiente: `git diff --stat`, luego `make -n sniffer-ddos-agg-test` y `make sniffer-ddos-agg-test`.")
        return 0
    except PatchError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return e.code
    except OSError as e:
        print(f"ERROR de E/S: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())