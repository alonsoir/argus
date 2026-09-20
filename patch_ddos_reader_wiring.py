#!/usr/bin/env python3
"""patch_ddos_reader_wiring.py -- DAY274: cablea test_ddos_kernel_reader en CMake y Makefile.

Que hace:
  * sniffer/CMakeLists.txt: bloque nuevo (add_executable + add_test) para test_ddos_kernel_reader,
    justo despues del bloque de test_ddos_kernel_agg, con el mismo `if(NOT USE_LIBPCAP)`.
    Hace find_package(Threads REQUIRED) y enlaza Threads::Threads (el test usa std::thread).
  * Makefile: target `sniffer-ddos-reader-test` (misma receta que sniffer-ddos-agg-test).
    Las recetas van con TAB. El test queda registrado con add_test, asi que entra en
    cualquier ctest general del sniffer (se comprueba al final con `make test-components`).

Uso (desde la RAIZ del repo, en la VM `defender`: hace falta cmake y el build-debug configurado):
    python3 patch_ddos_reader_wiring.py --dry      # solo diff; no escribe nada
    python3 patch_ddos_reader_wiring.py --apply    # escribe y VERIFICA; si falla, restaura los originales
    python3 patch_ddos_reader_wiring.py --check    # marcadores + cmake . + build + ctest

Verificacion (salvo --skip-verify), en sniffer/build-debug:
    cmake .  ->  cmake --build . --target test_ddos_kernel_reader  ->  ctest -R test_ddos_kernel_reader
El target del Makefile NO se puede probar desde la VM (usa vagrant): se prueba desde el Mac con
`make sniffer-ddos-reader-test`.

Idempotente (marcador DDOS-KREAD-D274:*). Precondicion: patch_ddos_reader.py aplicado
(existen ddos_kernel_reader.hpp y el test). NO commitea.
"""
import argparse
import difflib
import subprocess
import sys
from pathlib import Path

TAG = "DDOS-KREAD-D274"

HEADER_REL = "sniffer/include/ddos_kernel_reader.hpp"
TEST_REL = "sniffer/tests/test_ddos_kernel_reader.cpp"
CMAKE_REL = "sniffer/CMakeLists.txt"
MAKE_REL = "Makefile"

CMAKE_MARKER = TAG + ":CMAKE"
CMAKE_ANCHOR = 'agregador DDoS en-kernel, parte pura)")\nendif()\n'
CMAKE_INSERT = (
        "\n"
        "# ============================================================================\n"
        "# " + CMAKE_MARKER + "  Hilo lector del agregador DDoS en-kernel (DAY 274)\n"
                              "# Test sin kernel ni root: formato del CSV (funciones puras) y ciclo de vida del\n"
                              "# hilo (start/stop, parada inmediata, cadencia) con fd = -1.\n"
                              "# Solo Variant A (eBPF): la Variant B (libpcap) no tiene libbpf.\n"
                              "# ============================================================================\n"
                              "if(NOT USE_LIBPCAP)\n"
                              "  find_package(Threads REQUIRED)\n"
                              "  add_executable(test_ddos_kernel_reader\n"
                              "          tests/test_ddos_kernel_reader.cpp\n"
                              "  )\n"
                              "  target_include_directories(test_ddos_kernel_reader PRIVATE\n"
                              "          ${CMAKE_SOURCE_DIR}/include\n"
                              "          ${LIBBPF_INCLUDE_DIRS}\n"
                              "  )\n"
                              "  if(LIBBPF_LIBRARY_DIRS)\n"
                              "    target_link_directories(test_ddos_kernel_reader PRIVATE ${LIBBPF_LIBRARY_DIRS})\n"
                              "  endif()\n"
                              "  target_link_libraries(test_ddos_kernel_reader PRIVATE\n"
                              "          ${LIBBPF_LIBRARIES}\n"
                              "          Threads::Threads\n"
                              "  )\n"
                              "  add_test(NAME test_ddos_kernel_reader COMMAND test_ddos_kernel_reader)\n"
                              '  message(STATUS "Unit Test: test_ddos_kernel_reader configured (DAY 274 - hilo lector DDoS + CSV, sin kernel)")\n'
                              "endif()\n"
)

MAKE_MARKER = TAG + ":MAKE"
MAKE_ANCHOR = 'sudo ./test_ddos_kernel_agg --bpf ./sniffer.bpf.o"\n'
MAKE_INSERT = (
        "\n"
        "# ============================================================================\n"
        "# " + MAKE_MARKER + "  Test del hilo lector DDoS (DAY 274): sin root, sin kernel.\n"
                             "# Registrado con add_test en sniffer/CMakeLists.txt: entra en cualquier ctest general.\n"
                             "# ============================================================================\n"
                             ".PHONY: sniffer-ddos-reader-test\n"
                             "\n"
                             "sniffer-ddos-reader-test:\n"
                             '\t@echo "\U0001F9EA test_ddos_kernel_reader (hilo + CSV, sin root ni kernel)..."\n'
                             '\t@vagrant ssh -c "cd $(SNIFFER_BUILD_DIR) && cmake . > /dev/null && '
                             'cmake --build . --target test_ddos_kernel_reader && '
                             'ctest -R test_ddos_kernel_reader --output-on-failure"\n'
)

EDITS = [
    (CMAKE_REL, CMAKE_MARKER, CMAKE_ANCHOR, CMAKE_INSERT),
    (MAKE_REL, MAKE_MARKER, MAKE_ANCHOR, MAKE_INSERT),
]
for _rel, _marker, _anchor, _insert in EDITS:
    assert _marker in _insert, "el texto insertado de %s no lleva su marcador" % _rel


def read_text(p):
    return p.read_bytes().decode("utf-8")


def write_text(p, text):
    p.write_bytes(text.encode("utf-8"))


def plan(root):
    """(cambios, problemas, estado). cambios: rel -> (viejo, nuevo); estado: rel -> aplicado?"""
    changes, problems, state = {}, [], {}
    for rel in (HEADER_REL, TEST_REL):
        if not (root / rel).is_file():
            problems.append("falta %s: aplica antes patch_ddos_reader.py" % rel)
    for rel, marker, anchor, insert in EDITS:
        p = root / rel
        if not p.is_file():
            problems.append("falta %s" % rel)
            continue
        t = read_text(p)
        n_mark = t.count(marker)
        if n_mark == 1:
            state[rel] = True
            continue
        if n_mark > 1:
            problems.append("%s: el marcador %s aparece %d veces" % (rel, marker, n_mark))
            continue
        n_anchor = t.count(anchor)
        if n_anchor != 1:
            problems.append("%s: el ancla aparece %d veces (se esperaba 1):\n      %r" % (rel, n_anchor, anchor))
            continue
        changes[rel] = (t, t.replace(anchor, anchor + insert, 1))
        state[rel] = False
    return changes, problems, state


def print_diff(rel, old, new):
    a = old.splitlines(keepends=True)
    b = new.splitlines(keepends=True)
    for line in difflib.unified_diff(a, b, "%s (antes)" % rel, "%s (despues)" % rel, n=3):
        sys.stdout.write(line if line.endswith("\n") else line + "\n")


def run(cmd, cwd, timeout=1200):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def verify(root, build_rel):
    bd = root / build_rel
    if not (bd / "CMakeCache.txt").is_file():
        print("ERROR: %s no esta configurado (falta CMakeCache.txt). Compila antes con make sniffer-build, "
              "o usa --build-dir / --skip-verify." % build_rel)
        return False
    steps = [
        ("cmake . (reconfigura)", ["cmake", "."]),
        ("cmake --build --target test_ddos_kernel_reader",
         ["cmake", "--build", ".", "--target", "test_ddos_kernel_reader"]),
        ("ctest -R test_ddos_kernel_reader", ["ctest", "-R", "test_ddos_kernel_reader", "--output-on-failure"]),
    ]
    for name, cmd in steps:
        rc, out = run(cmd, bd)
        print("verify  : %s: %s" % (name, "OK" if rc == 0 else "FALLA"))
        lines = out.strip().splitlines()
        if rc != 0:
            for line in lines[-40:]:
                print("    " + line)
            return False
        if cmd[0] == "ctest":
            for line in lines[-6:]:
                print("    " + line)
    return True


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Cableado CMake/Makefile del test del lector DDoS (DAY274)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry", action="store_true", help="diff; no escribe")
    mode.add_argument("--apply", action="store_true", help="escribe, verifica y restaura si falla")
    mode.add_argument("--check", action="store_true", help="marcadores + cmake . + build + ctest")
    ap.add_argument("--build-dir", default="sniffer/build-debug", help="directorio de build (por defecto sniffer/build-debug)")
    ap.add_argument("--skip-verify", action="store_true", help="no reconfigurar/compilar/ejecutar")
    args = ap.parse_args()

    root = Path.cwd().resolve()
    if not (root / "sniffer").is_dir():
        print("ERROR: ejecuta desde la raiz del repo (aqui no hay sniffer/): %s" % root)
        return 2

    changes, problems, state = plan(root)
    if problems:
        print("ERROR: no se puede continuar:")
        for p in problems:
            print("  - " + p)
        return 2

    if args.check:
        pending = [rel for rel, ok in state.items() if not ok]
        if pending:
            print("check   : FALTA aplicar: %s" % pending)
            return 1
        print("check   : marcadores OK (uno por fichero: %s)" % sorted(state))
        if args.skip_verify:
            return 0
        return 0 if verify(root, args.build_dir) else 2

    if not changes:
        print("ya aplicado; nada que hacer.")
        return 0

    for rel, (old, new) in sorted(changes.items()):
        print_diff(rel, old, new)
    print()

    if args.dry:
        print("--dry: no se ha escrito nada.")
        return 0

    if not args.skip_verify and not (root / args.build_dir / "CMakeCache.txt").is_file():
        print("ERROR: %s no esta configurado (falta CMakeCache.txt): no puedo verificar. No se ha escrito nada. "
              "Compila antes (make sniffer-build) o usa --skip-verify." % args.build_dir)
        return 2

    originals = {rel: old for rel, (old, _) in changes.items()}
    for rel, (_, new) in changes.items():
        write_text(root / rel, new)

    if not args.skip_verify and not verify(root, args.build_dir):
        for rel, old in originals.items():
            write_text(root / rel, old)
        try:
            run(["cmake", "."], root / args.build_dir)  # dejar el build-dir coherente con lo restaurado
        except Exception:  # noqa: BLE001
            pass
        print("\nABORTADO: la verificacion fallo; restaurados los ficheros originales.")
        return 2

    print("\nAPLICADO: %s" % ", ".join(sorted(changes)))
    print("Nota: el target del Makefile solo se prueba desde el Mac: `make sniffer-ddos-reader-test`. "
          "El patcher NO commitea.")
    return 0


if __name__ == "__main__":
    sys.exit(main())