#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_correlation_v1_scaffold.py — aRGus NDR — DAY 185 (rev B2)

Valida que el ANDAMIAJE de la extracción de libcorrelation_v1 está en su sitio.
VALIDA, NO ARREGLA. Si algo falta, lo marca; tú lo arreglas.

Cubre:
  Sec 1-4 — módulo lib + Makefile + ml-detector CMake + tests CMake (scaffolding).
  Sec 5   — B1: to_row (capa protobuf que se queda en ml-detector).
  Sec 6   — B2: vectores + harness de captura del golden.

ALCANCE HONESTO:
  SÍ — ficheros presentes en rutas correctas, marcadores en Makefile/CMake/código.
  NO — que compile, que linke, que los bytes sean idénticos al oráculo. Eso lo
       dicen el compilador, capture_golden y el test de oráculo (B3). Verde aquí =
       "no me dejé ningún fichero ni edición", NO "el refactor es correcto".

Uso:
    python3 validate_correlation_v1_scaffold.py [--root /ruta/al/repo]
Exit: 0 si sin FALTA; 1 si falta algo. REVISAR no rompe el exit.
"""

import argparse
import os
import re
import sys

OK, FAIL, WARN = "OK", "FALTA", "REVISAR"
SYM = {OK: "\u2705", FAIL: "\u274c", WARN: "\u26a0\ufe0f "}


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return None


def recipe_block(makefile_text, target):
    if makefile_text is None:
        return ""
    lines = makefile_text.splitlines()
    out, capturing = [], False
    tre = re.compile(r"^" + re.escape(target) + r":")
    for line in lines:
        if not capturing:
            if tre.match(line):
                capturing = True
                out.append(line)
            continue
        if line.startswith("\t"):
            out.append(line)
        else:
            break
    return "\n".join(out)


def window_after(text, anchor, span=900):
    if text is None:
        return ""
    i = text.find(anchor)
    return "" if i < 0 else text[i:i + span]


class Report:
    def __init__(self):
        self.rows = []

    def add(self, section, status, label, detail=""):
        self.rows.append((section, status, label, detail))

    def file_present(self, section, path, label):
        if os.path.isfile(path):
            self.add(section, OK, label, path)
            return True
        self.add(section, FAIL, label, f"NO existe: {path}")
        return False

    def needs(self, section, text, needle, label, severity=FAIL, regex=False):
        if text is None:
            self.add(section, FAIL, label, "fichero ausente")
            return False
        found = (re.search(needle, text) is not None) if regex else (needle in text)
        if found:
            self.add(section, OK, label)
            return True
        self.add(section, severity, label, f"no encontrado: {needle!r}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.getcwd())
    args = ap.parse_args()
    R = args.root

    if not (os.path.isfile(os.path.join(R, "Makefile"))
            and os.path.isdir(os.path.join(R, "ml-detector"))
            and os.path.isdir(os.path.join(R, "libs"))):
        print(f"\u274c '{R}' no parece la raiz del repo aRGus "
              f"(faltan Makefile / ml-detector/ / libs/).")
        sys.exit(2)

    rep = Report()

    lib_dir   = os.path.join(R, "libs", "correlation-v1")
    lib_cmake = os.path.join(lib_dir, "CMakeLists.txt")
    lib_hpp   = os.path.join(lib_dir, "include", "correlation_v1", "correlation_v1.hpp")
    lib_cpp   = os.path.join(lib_dir, "src", "correlation_v1.cpp")
    lib_test  = os.path.join(lib_dir, "tests", "test_correlation_v1.cpp")
    root_mk   = os.path.join(R, "Makefile")
    mld_cmake = os.path.join(R, "ml-detector", "CMakeLists.txt")
    mld_tests = os.path.join(R, "ml-detector", "tests", "CMakeLists.txt")
    wr_hpp    = os.path.join(R, "ml-detector", "include", "correlation_writer.hpp")
    wr_cpp    = os.path.join(R, "ml-detector", "src", "correlation_writer.cpp")
    integ     = os.path.join(R, "ml-detector", "tests", "integration")
    vec_hpp   = os.path.join(integ, "correlation_v1_golden_vectors.hpp")
    cap_cpp   = os.path.join(integ, "capture_golden.cpp")
    golden    = os.path.join(R, "ml-detector", "tests", "data", "correlation_v1_golden.tsv")

    S = "1. Modulo libs/correlation-v1/"
    if os.path.isdir(lib_dir):
        rep.add(S, OK, "Directorio libs/correlation-v1/ (con guion)")
    else:
        rep.add(S, FAIL, "Directorio libs/correlation-v1/ (con guion)",
                f"NO existe: {lib_dir}")

    if rep.file_present(S, lib_cmake, "CMakeLists.txt de la lib"):
        t = read(lib_cmake)
        rep.needs(S, t, "project(correlation_v1", "  project(correlation_v1 ...)")
        rep.needs(S, t, "add_library(correlation_v1 SHARED", "  add_library(correlation_v1 SHARED)")
        rep.needs(S, t, "OpenSSL::Crypto", "  enlaza OpenSSL::Crypto (HMAC)")
        rep.needs(S, t, "install(DIRECTORY include/correlation_v1",
                  "  install include/correlation_v1")
        rep.needs(S, t, "add_executable(test_correlation_v1", "  target de test")

    if rep.file_present(S, lib_hpp, "Header include/correlation_v1/correlation_v1.hpp"):
        t = read(lib_hpp)
        rep.needs(S, t, "namespace correlation_v1", "  namespace correlation_v1")
        rep.needs(S, t, "struct CorrelationV1Row", "  struct CorrelationV1Row")
        rep.needs(S, t, "authoritative_source", "  campo col 17 authoritative_source")
        rep.needs(S, t, "ValidationResult validate(", "  declara validate()")
        rep.needs(S, t, "SerializeResult serialize(", "  declara serialize()")

    if rep.file_present(S, lib_cpp, "Implementacion src/correlation_v1.cpp"):
        t = read(lib_cpp)
        rep.needs(S, t, '#include "correlation_v1/correlation_v1.hpp"',
                  "  include con subdir correlation_v1/")
        rep.needs(S, t, "std::locale::classic()", "  imbue(classic) presente (D-E)")
        rep.needs(S, t, "HMAC(", "  compute_hmac (OpenSSL HMAC)")

    if rep.file_present(S, lib_test, "Test de la lib tests/test_correlation_v1.cpp"):
        t = read(lib_test)
        rep.needs(S, t, '#include "correlation_v1/correlation_v1.hpp"',
                  "  include corregido (con subdir)")
        if t is not None and re.search(r'#include\s+"correlation_v1\.hpp"', t):
            rep.add(S, WARN, "  include BARE sin subdir todavia presente",
                    'cambia a "correlation_v1/correlation_v1.hpp"')

    S = "2. Makefile raiz"
    mk = read(root_mk)
    rep.needs(S, mk, "correlation-v1-build:", "target correlation-v1-build")
    rep.needs(S, mk, "correlation-v1-test:", "target correlation-v1-test")
    rep.needs(S, mk, "correlation-v1-clean:", "target correlation-v1-clean")
    rep.needs(S, mk, "correlation-v1-build", ".PHONY incluye correlation-v1-build",
              severity=WARN)

    if mk is not None:
        m = re.search(r"^ml-detector:[^\n]*", mk, re.MULTILINE)
        if m and "correlation-v1-build" in m.group(0):
            rep.add(S, OK, "ml-detector: tiene prereq correlation-v1-build")
        elif m:
            rep.add(S, FAIL, "ml-detector: tiene prereq correlation-v1-build",
                    f"linea actual: {m.group(0).strip()!r}")
        else:
            rep.add(S, FAIL, "ml-detector: tiene prereq correlation-v1-build",
                    "no encuentro la regla 'ml-detector:'")

    blk = recipe_block(mk, "test-libs")
    if "correlation-v1-test" in blk:
        rep.add(S, OK, "test-libs invoca correlation-v1-test")
    elif mk and "correlation-v1-test" in mk:
        rep.add(S, WARN, "test-libs invoca correlation-v1-test",
                "el invoke existe pero no lo confirmo dentro de la receta test-libs")
    else:
        rep.add(S, FAIL, "test-libs invoca correlation-v1-test")

    blk = recipe_block(mk, "clean-libs")
    if "correlation-v1-clean" in blk:
        rep.add(S, OK, "clean-libs invoca correlation-v1-clean")
    elif mk and "correlation-v1-clean" in mk:
        rep.add(S, WARN, "clean-libs invoca correlation-v1-clean",
                "el invoke existe pero no lo confirmo dentro de la receta clean-libs")
    else:
        rep.add(S, FAIL, "clean-libs invoca correlation-v1-clean")

    S = "3. ml-detector/CMakeLists.txt"
    t = read(mld_cmake)
    rep.needs(S, t, "find_library(CORRELATION_V1_LIB", "find_library(CORRELATION_V1_LIB)")
    rep.needs(S, t, "correlation_v1/correlation_v1.hpp",
              "find_path busca correlation_v1/correlation_v1.hpp")
    win = window_after(t, "target_link_libraries(ml-detector", 900)
    if "CORRELATION_V1_LIB" in win:
        rep.add(S, OK, "ml-detector linka ${CORRELATION_V1_LIB}")
    elif t and "${CORRELATION_V1_LIB}" in t:
        rep.add(S, WARN, "ml-detector linka ${CORRELATION_V1_LIB}",
                "aparece, pero no junto al primer target_link_libraries(ml-detector ...)")
    else:
        rep.add(S, FAIL, "ml-detector linka ${CORRELATION_V1_LIB}")
    rep.needs(S, t, "src/correlation_writer.cpp",
              "correlation_writer.cpp SIGUE en SOURCES (no se mueve)")

    S = "4. ml-detector/tests/CMakeLists.txt"
    t = read(mld_tests)
    win = window_after(t, "test_correlation_roundtrip", 1200)
    if "CORRELATION_V1_LIB" in win:
        rep.add(S, OK, "test_correlation_roundtrip linka ${CORRELATION_V1_LIB}")
    elif t and "test_correlation_roundtrip" in t:
        rep.add(S, FAIL, "test_correlation_roundtrip linka ${CORRELATION_V1_LIB}",
                "el bloque existe pero sin ${CORRELATION_V1_LIB}")
    else:
        rep.add(S, WARN, "test_correlation_roundtrip linka ${CORRELATION_V1_LIB}",
                "no encuentro el bloque test_correlation_roundtrip")
    rep.needs(S, t, "test_correlation_v1_oracle",
              "bloque test_correlation_v1_oracle (durmiente) presente")

    S = "5. B1 - to_row (capa protobuf)"
    th = read(wr_hpp)
    rep.needs(S, th, "correlation_v1/correlation_v1.hpp",
              "correlation_writer.hpp incluye la lib")
    rep.needs(S, th, "to_correlation_v1_row",
              "correlation_writer.hpp declara to_correlation_v1_row")
    tc = read(wr_cpp)
    rep.needs(S, tc, "to_correlation_v1_row",
              "correlation_writer.cpp define to_correlation_v1_row")
    if tc is not None and "build_row" in tc:
        rep.add(S, OK, "build_row aun presente (esperado hasta B4)")
    elif tc is not None:
        rep.add(S, WARN, "build_row aun presente (esperado hasta B4)",
                "no veo build_row -- hiciste el rewire de B4 antes de tiempo?")

    S = "6. B2 - captura del golden"
    if rep.file_present(S, vec_hpp, "tests/integration/correlation_v1_golden_vectors.hpp"):
        t = read(vec_hpp)
        rep.needs(S, t, "namespace argus_golden", "  namespace argus_golden")
        rep.needs(S, t, "make_golden_vectors", "  make_golden_vectors()")
        rep.needs(S, t, "struct GoldenVector", "  struct GoldenVector")
    if rep.file_present(S, cap_cpp, "tests/integration/capture_golden.cpp"):
        t = read(cap_cpp)
        rep.needs(S, t, '#include "correlation_v1_golden_vectors.hpp"',
                  "  incluye los vectores SIN ruta (misma carpeta)")
        rep.needs(S, t, "std::locale::classic()", "  fija locale classic (D-E)")
        rep.needs(S, t, "abababababab", "  clave HMAC test (abab..., igual que roundtrip)")
    t = read(mld_tests)
    win = window_after(t, "add_executable(capture_golden", 600)
    if t is None:
        rep.add(S, FAIL, "tests/CMakeLists.txt registra capture_golden", "fichero ausente")
    elif "add_executable(capture_golden" in t and "CORRELATION_V1_LIB" in win:
        rep.add(S, OK, "tests/CMakeLists.txt registra capture_golden + linka lib")
    elif "add_executable(capture_golden" in t:
        rep.add(S, WARN, "tests/CMakeLists.txt registra capture_golden",
                "el target existe pero no veo ${CORRELATION_V1_LIB} en su bloque")
    else:
        rep.add(S, FAIL, "tests/CMakeLists.txt registra capture_golden")
    if os.path.isfile(golden):
        g = read(golden)
        ok_hdr = g is not None and "correlation_v1 golden" in g
        ok_wr  = g is not None and "WRITTEN" in g
        ok_sk  = g is not None and "SKIPPED" in g
        if ok_hdr and ok_wr and ok_sk:
            rep.add(S, OK, "golden capturado (cabecera + WRITTEN + SKIPPED presentes)")
        else:
            rep.add(S, WARN, "golden presente pero con forma rara",
                    f"hdr={ok_hdr} written={ok_wr} skipped={ok_sk}")
    else:
        rep.add(S, WARN, "golden tests/data/correlation_v1_golden.tsv aun NO capturado",
                "corre capture_golden tras compilar ml-detector")

    print()
    print("\u2554" + "\u2550" * 64 + "\u2557")
    print("  Validacion estructural - libcorrelation_v1 (DAY 185, rev B2)")
    print("  VALIDA, NO ARREGLA - estructura, no semantica")
    print("\u255a" + "\u2550" * 64 + "\u255d")

    n_fail = n_warn = n_ok = 0
    current = None
    for section, status, label, detail in rep.rows:
        if section != current:
            current = section
            print(f"\n-- {section} " + "-" * max(0, 50 - len(section)))
        line = f"  {SYM[status]} {label}"
        if detail and status != OK:
            line += f"\n        -> {detail}"
        print(line)
        n_fail += status == FAIL
        n_warn += status == WARN
        n_ok += status == OK

    print("\n" + "-" * 66)
    print(f"  Resumen: {n_ok} OK - {n_warn} REVISAR - {n_fail} FALTA")
    print("-" * 66)

    print("\n  PROXIMOS PASOS (fuera del alcance de este validador):")
    print("    - B3: test_correlation_v1_oracle.cpp -- serialize(to_row(e)) == golden")
    print("          == write_record(e) en vivo. AQUI se prueba la byte-identidad.")
    print("    - B4: rewire de write_record a serialize() + borrar build_row.")
    print("    - Verde aqui NO implica byte-identidad -- eso lo prueba B3.")

    if n_fail:
        print(f"\n\u274c {n_fail} elemento(s) FALTA(n). Arreglalos y re-ejecuta.")
        sys.exit(1)
    if n_warn:
        print(f"\n\u26a0\ufe0f  Sin FALTA, pero {n_warn} REVISAR -- ojo humano recomendado.")
        sys.exit(0)
    print("\n\u2705 Andamiaje completo (incl. B1+B2).")
    sys.exit(0)


if __name__ == "__main__":
    main()