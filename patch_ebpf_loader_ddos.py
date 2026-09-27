#!/usr/bin/env python3
"""
patch_ebpf_loader_ddos.py  --  DAY273, paso 2

Expone el mapa `ddos_victims` (agregador DDoS en-kernel) desde EbpfLoader:

  sniffer/include/ebpf_loader.hpp
    - accesores  get_ddos_victims_fd() / get_ddos_victims_max_entries()
    - miembros   ddos_victims_map_, ddos_victims_fd_ (-1), ddos_victims_max_entries_ (0)
  sniffer/src/userspace/ebpf_loader.cpp
    - #include "ddos_kernel_agg.hpp"   (layout compartido con el kernel)
    - en load_program(): find_map_by_name("ddos_victims"), tolerante como excluded_ports:
        * sin el mapa      -> INFO, fd=-1  (un .bpf.o anterior al parche sigue funcionando)
        * layout distinto  -> WARNING y se desactiva (no se lee basura)

Precondicion: sniffer/include/ddos_kernel_agg.hpp debe existir (se comprueba).
Los DOS ficheros se parchean juntos o ninguno.

  --dry / --apply / --check   (igual que patch_ddos_kernel_agg.py)

Exit codes: 0 ok | 1 no aplicado (--check) | 2 estado/anclas invalidos |
            3 compilacion fallida o no verificable | 4 error de E/S
"""
import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile

HPP_DEFAULT = "sniffer/include/ebpf_loader.hpp"
CPP_DEFAULT = "sniffer/src/userspace/ebpf_loader.cpp"
AGG_DEFAULT = "sniffer/include/ddos_kernel_agg.hpp"

# Solo sintaxis: el loader necesita cabeceras Linux + libbpf (VM defender), no enlaza aqui.
DEFAULT_CXX = "g++ -std=c++20 -fsyntax-only -Wall -Wextra -I{dir} {src}"

M_HPP_API = "DDOS-KAGG-D273:LOADER-HPP-API"
M_HPP_MEM = "DDOS-KAGG-D273:LOADER-HPP-MEM"
M_CPP_INC = "DDOS-KAGG-D273:LOADER-CPP-INC"
M_CPP_FIND = "DDOS-KAGG-D273:LOADER-CPP-FIND"
HPP_MARKERS = (M_HPP_API, M_HPP_MEM)
CPP_MARKERS = (M_CPP_INC, M_CPP_FIND)

# ------------------------------------------------------------------ anclas
HPP_ANCHOR_API = "int get_interface_configs_fd() const { return interface_configs_fd_; }"
HPP_ANCHOR_MEM = "int interface_configs_fd_ = -1;"
CPP_ANCHOR_INC = '#include "ebpf_loader.hpp"'
CPP_ANCHOR_FIND = "    program_loaded_ = true;\n"
CPP_ANCHOR_CTX = '"iface_configs"'  # el bloque nuevo debe quedar DESPUES de este

TXT_HPP_API = f"""
    // [{M_HPP_API}] Agregador DDoS en-kernel (mapa `ddos_victims`).
    // fd = -1 / max_entries = 0 si el .bpf.o cargado no lo trae (objeto anterior al parche).
    int get_ddos_victims_fd() const {{ return ddos_victims_fd_; }}
    uint32_t get_ddos_victims_max_entries() const {{ return ddos_victims_max_entries_; }}
"""

TXT_HPP_MEM = f"""
    // [{M_HPP_MEM}] Agregador DDoS en-kernel
    struct bpf_map* ddos_victims_map_ = nullptr;
    int ddos_victims_fd_ = -1;
    uint32_t ddos_victims_max_entries_ = 0;
"""

TXT_CPP_INC = f'#include "ddos_kernel_agg.hpp"  // [{M_CPP_INC}] layout de ddos_key/ddos_val'

TXT_CPP_FIND = f"""    // [{M_CPP_FIND}] Agregador DDoS en-kernel. Opcional: un .bpf.o anterior al parche
    // no lo trae. Si el layout no coincide con ddos_kernel_agg.hpp se desactiva en vez
    // de leer basura.
    ddos_victims_map_ = bpf_object__find_map_by_name(bpf_obj_, "ddos_victims");
    if (ddos_victims_map_) {{
        if (bpf_map__key_size(ddos_victims_map_) != sizeof(DdosVictimKey) ||
            bpf_map__value_size(ddos_victims_map_) != sizeof(DdosVictimVal)) {{
            std::cerr << "[WARNING] ddos_victims map layout mismatch (key="
                      << bpf_map__key_size(ddos_victims_map_) << " val="
                      << bpf_map__value_size(ddos_victims_map_) << ", expected "
                      << sizeof(DdosVictimKey) << "/" << sizeof(DdosVictimVal)
                      << "); in-kernel DDoS aggregator disabled" << std::endl;
            ddos_victims_map_ = nullptr;
        }} else {{
            ddos_victims_fd_ = bpf_map__fd(ddos_victims_map_);
            ddos_victims_max_entries_ = bpf_map__max_entries(ddos_victims_map_);
            std::cout << "[INFO] Found ddos_victims map (in-kernel DDoS aggregator), FD: "
                      << ddos_victims_fd_ << ", max_entries: " << ddos_victims_max_entries_
                      << std::endl;
        }}
    }} else {{
        std::cout << "[INFO] ddos_victims map not found (eBPF object without in-kernel DDoS aggregator)"
                  << std::endl;
    }}

"""


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


def count_markers(text, markers):
    return {m: text.count(m) for m in markers}


def require_once(text, needle, what):
    n = text.count(needle)
    if n != 1:
        raise PatchError(f"ancla '{what}' aparece {n} veces (debe ser exactamente 1): {needle!r}\n"
                         f"  -> el fichero ha cambiado respecto a lo medido; no toco nada.")
    return text.index(needle)


def end_of_line(text, idx):
    j = text.find("\n", idx)
    return len(text) if j < 0 else j + 1


def insert_after_line(text, anchor, block, what):
    i = require_once(text, anchor, what)
    e = end_of_line(text, i)
    if e == len(text) and not text.endswith("\n"):
        raise PatchError(f"ancla '{what}' esta en la ultima linea sin salto final; no toco nada.")
    return text[:e] + block + text[e:]


def build_hpp(hpp):
    if "\r" in hpp:
        raise PatchError("ebpf_loader.hpp tiene CR (CRLF); el patcher espera LF.")
    out = insert_after_line(hpp, HPP_ANCHOR_MEM, TXT_HPP_MEM, "miembro interface_configs_fd_")
    out = insert_after_line(out, HPP_ANCHOR_API, TXT_HPP_API, "accesor get_interface_configs_fd")
    return out


def build_cpp(cpp):
    if "\r" in cpp:
        raise PatchError("ebpf_loader.cpp tiene CR (CRLF); el patcher espera LF.")
    i_ctx = require_once(cpp, CPP_ANCHOR_CTX, "busqueda del mapa iface_configs")
    i_end = require_once(cpp, CPP_ANCHOR_FIND, "program_loaded_ = true;")
    require_once(cpp, CPP_ANCHOR_INC, "include de ebpf_loader.hpp")
    if not i_ctx < i_end:
        raise PatchError("orden de anclas inesperado (iface_configs debe ir antes de program_loaded_ = true)")
    out = cpp[:i_end] + TXT_CPP_FIND + cpp[i_end:]
    out = insert_after_line(out, CPP_ANCHOR_INC, TXT_CPP_INC + "\n", "include de ebpf_loader.hpp")
    return out


def state(hpp, cpp):
    sh = count_markers(hpp, HPP_MARKERS)
    sc = count_markers(cpp, CPP_MARKERS)
    allm = list(sh.values()) + list(sc.values())
    if all(n == 0 for n in allm):
        return "clean", {**sh, **sc}
    if all(n == 1 for n in allm):
        return "applied", {**sh, **sc}
    return "partial", {**sh, **sc}


def verify_structure(hpp, cpp):
    for needle, txt in (("get_ddos_victims_fd()", hpp), ("int ddos_victims_fd_ = -1;", hpp),
                        ("uint32_t ddos_victims_max_entries_ = 0;", hpp),
                        ('"ddos_victims"', cpp)):
        if txt.count(needle) != 1:
            raise PatchError(f"'{needle}' aparece {txt.count(needle)} veces, esperaba 1")
    if cpp.index('"ddos_victims"') > cpp.index("    program_loaded_ = true;\n"):
        raise PatchError("la busqueda de ddos_victims quedo despues de program_loaded_ = true")


def try_compile(hpp, cpp, agg_path, cxx, label):
    if cxx is None:
        return None, "no hay g++/clang++ en PATH y no se dio --cxx"
    with tempfile.TemporaryDirectory(prefix="ddos_loader_") as td:
        for name, txt in (("ebpf_loader.hpp", hpp), ("ebpf_loader.cpp", cpp)):
            with open(os.path.join(td, name), "w", encoding="utf-8", newline="") as f:
                f.write(txt)
        shutil.copy(agg_path, os.path.join(td, "ddos_kernel_agg.hpp"))
        cmd = cxx.format(dir=td, src=os.path.join(td, "ebpf_loader.cpp"))
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            return False, f"[{label}] timeout: {cmd}"
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, (f"[{label}] $ {cmd}\n{out}" if out else f"[{label}] $ {cmd}")


def find_cxx(arg):
    if arg:
        return arg
    if shutil.which("g++") or shutil.which("clang++"):
        return DEFAULT_CXX if shutil.which("g++") else DEFAULT_CXX.replace("g++", "clang++", 1)
    return None


def compile_gate(hpp0, cpp0, hpp1, cpp1, agg, cxx, skip):
    if skip:
        print("compile : OMITIDO (--skip-compile). NO verificado por el compilador.")
        return True
    ok0, log0 = try_compile(hpp0, cpp0, agg, cxx, "baseline")
    if ok0 is None:
        print(f"compile : NO VERIFICABLE ({log0}). Pasa --cxx o ejecuta en la VM defender.")
        return False
    if not ok0:
        print(log0)
        print("compile : el BASELINE (sin parche) no compila con este --cxx: es el comando/includes\n"
              "          (libbpf, linux/if_link.h), no el parche. Ejecuta en la VM defender o ajusta --cxx.")
        return False
    print("compile : baseline OK")
    ok1, log1 = try_compile(hpp1, cpp1, agg, cxx, "parcheado")
    if not ok1:
        print(log1)
        print("compile : el parcheado NO compila. No escribo nada.")
        return False
    print("compile : parcheado OK")
    return True


def write_tmp(path, text):
    d = os.path.dirname(os.path.abspath(path))
    st = os.stat(path)
    fd, tmp = tempfile.mkstemp(prefix=".ddos_loader_", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, st.st_mode & 0o7777)
    return tmp


def atomic_write_pair(hpp_path, hpp_new, hpp_old, cpp_path, cpp_new):
    """Los dos o ninguno: si falla el segundo replace, se restaura el primero."""
    tmp_h = tmp_c = None
    try:
        tmp_h = write_tmp(hpp_path, hpp_new)
        tmp_c = write_tmp(cpp_path, cpp_new)
        os.replace(tmp_h, hpp_path)
        tmp_h = None
        try:
            os.replace(tmp_c, cpp_path)
            tmp_c = None
        except OSError:
            tmp_r = write_tmp(hpp_path, hpp_old)
            os.replace(tmp_r, hpp_path)
            raise
    finally:
        for t in (tmp_h, tmp_c):
            if t and os.path.exists(t):
                os.unlink(t)


def udiff(name, a, b):
    return "".join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
                                        fromfile=name + " (antes)", tofile=name + " (despues)", n=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--hpp", default=HPP_DEFAULT)
    ap.add_argument("--cpp", default=CPP_DEFAULT)
    ap.add_argument("--agg", default=AGG_DEFAULT, help="ruta de ddos_kernel_agg.hpp (debe existir)")
    ap.add_argument("--cxx", default=None,
                    help=f"comando con {{dir}} y {{src}}; por defecto: {DEFAULT_CXX}")
    ap.add_argument("--skip-compile", action="store_true")
    a = ap.parse_args()

    try:
        if not os.path.isfile(a.agg):
            raise PatchError(f"falta {a.agg}: coloca ddos_kernel_agg.hpp ahi antes de parchear "
                             f"(el loader lo incluye).")
        hpp, cpp = read_text(a.hpp), read_text(a.cpp)
        cxx = find_cxx(a.cxx)
        st, counts = state(hpp, cpp)

        if a.check:
            if st == "clean":
                print("check   : NO aplicado")
                return 1
            if st == "partial":
                raise PatchError(f"estado parcial, marcadores {counts}")
            verify_structure(hpp, cpp)
            print(f"check   : estructura OK, marcadores {counts}")
            ok, log = try_compile(hpp, cpp, a.agg, cxx, "actual")
            if ok is None:
                print(f"compile : NO VERIFICABLE ({log})")
                return 3
            if not ok:
                print(log)
                return 3
            print("compile : actual OK")
            return 0

        if st == "applied":
            verify_structure(hpp, cpp)
            print("ya aplicado; nada que hacer.")
            return 0
        if st == "partial":
            raise PatchError(f"estado parcial, marcadores {counts}. "
                             f"Deshaz con `git checkout -- {a.hpp} {a.cpp}`.")

        hpp1, cpp1 = build_hpp(hpp), build_cpp(cpp)
        verify_structure(hpp1, cpp1)
        if state(hpp1, cpp1)[0] != "applied":
            raise PatchError("post-condicion: marcadores inconsistentes tras parchear")
        print(udiff(a.hpp, hpp, hpp1), end="")
        print(udiff(a.cpp, cpp, cpp1), end="")

        ok = compile_gate(hpp, cpp, hpp1, cpp1, a.agg, cxx, a.skip_compile)
        if a.dry:
            print("\n--dry: no se ha escrito nada.")
            return 0 if ok else 3
        if not ok:
            return 3
        atomic_write_pair(a.hpp, hpp1, hpp, a.cpp, cpp1)
        print(f"\nAPLICADO: {a.hpp} y {a.cpp}")
        print("Siguiente: `git diff --stat` y `--check`. El patcher NO commitea.")
        return 0
    except PatchError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return e.code
    except OSError as e:
        print(f"ERROR de E/S: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())