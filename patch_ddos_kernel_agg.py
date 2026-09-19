#!/usr/bin/env python3
"""
patch_ddos_kernel_agg.py  --  DAY273

Inserta en sniffer/src/kernel/sniffer.bpf.c el agregador DDoS en-kernel:

  1. defines      : BPF_NOEXIST, BPF_MAP_TYPE_LRU_HASH      (tras `#define BPF_ANY 0`)
  2. mapa         : struct ddos_key/ddos_val + ddos_victims (tras el mapa `stats`)
  3. bloque conteo: por victima (dst_ip + proto), paquetes + bytes, ANTES del
                    bpf_ringbuf_reserve -> el conteo no depende del ring.

Estilo patch_force_all_heads.py:
  --dry     muestra el diff, no escribe nada
  --apply   escribe (atomico: tmp + fsync + rename). Exige que compile.
  --check   solo lectura: verifica que el parche esta puesto y es consistente

Garantias:
  - Idempotente: si ya esta aplicado, --apply no toca nada (exit 0).
  - Anclas por TEXTO (no por numero de linea); cada ancla debe aparecer
    EXACTAMENTE una vez o se aborta sin escribir.
  - Estado parcial (algunos marcadores si, otros no) -> aborta (exit 2).
  - Compila el baseline Y el parcheado antes de escribir. El compilador es el
    arbitro: si el baseline no compila con tu --cc, el problema es el comando,
    no el parche, y se dice.
  - NO hace git add / commit.

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

DEFAULT_FILE = "sniffer/src/kernel/sniffer.bpf.c"

# Compilador por defecto: solo objeto BPF, sin enlazar. -g => BTF para __type().
# En la VM defender suele bastar; si tu Makefile usa -I especificos, pasalos con --cc.
DEFAULT_CC = "clang -O2 -g -target bpf -D__TARGET_ARCH_x86 -c {src} -o {out}"

M_DEFS = "DDOS-KAGG-D273:DEFS"
M_MAP = "DDOS-KAGG-D273:MAP"
M_COUNT = "DDOS-KAGG-D273:COUNT"
MARKERS = (M_DEFS, M_MAP, M_COUNT)

# ---------------------------------------------------------------- anclas
ANCHOR_DEFS = "#define BPF_ANY 0\n"
ANCHOR_MAP = '} stats SEC(".maps");\n'
ANCHOR_COUNT = "    // Reserve ring buffer space\n"
# Post-condicion: el bloque de conteo debe quedar DESPUES de estos dos y
# ANTES del reserve, para que `ip` exista y ya sea IPv4 validado.
PRE_IP_DECL = "__u8 *ip = (__u8*)ip_start;"
PRE_IPV4_CHECK = "if ((ip[0] >> 4) != 4)"
RESERVE_CALL = "bpf_ringbuf_reserve(&events"

TXT_DEFS = f"""/* [{M_DEFS}] agregador DDoS en-kernel */
#define BPF_NOEXIST 1
#define BPF_MAP_TYPE_LRU_HASH 9
"""

TXT_MAP = f"""
/* [{M_MAP}] Agregador DDoS en-kernel: contadores MONOTONOS por victima.
 * Clave = dst_ip + protocolo. Userspace lee cada T s; delta = ventana tumbling.
 * dst_ip en orden numerico (a.b.c.d = a<<24|b<<16|c<<8|d), IDENTICO a
 * event->dst_ip: userspace debe interpretarlo igual que ya interpreta ese campo
 * (ver DEBT-SNIFFER-IP-BYTE-ORDER-001).
 * proto es __u32 (no __u8) a proposito: sin padding en la clave, el verificador
 * exige que todos los bytes de la clave en pila esten inicializados.
 * LRU: el desalojo de una victima fria es benigno (no esta bajo flood). */
struct ddos_key {{
    __u32 dst_ip;
    __u32 proto;
}};
struct ddos_val {{
    __u64 pkts;
    __u64 bytes;
}};
struct {{
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 65536);
    __type(key, struct ddos_key);
    __type(value, struct ddos_val);
}} ddos_victims SEC(".maps");
"""

TXT_COUNT = f"""    /* [{M_COUNT}] Conteo por victima ANTES del reserve: independiente del ring,
     * asi no hereda la perdida que queremos medir. Cuenta todo IPv4 de una
     * interfaz activa, incluidos puertos que should_capture_port() descartaria
     * mas abajo (el filtro por puerto es del camino ring, no de este). */
    {{
        struct ddos_key dk = {{
            .dst_ip = ((__u32)ip[16] << 24) | ((__u32)ip[17] << 16) |
                      ((__u32)ip[18] << 8)  |  (__u32)ip[19],
            .proto  = ip[9],
        }};
        __u64 wlen = (__u64)(data_end - data);
        struct ddos_val *dv = bpf_map_lookup_elem(&ddos_victims, &dk);
        if (!dv) {{
            /* Primera vez que se ve la victima. NOEXIST + re-lookup: si otra CPU
             * inserto a la vez, el update falla con EEXIST y el re-lookup coge
             * la entrada ganadora; no se pierde ningun conteo. */
            struct ddos_val nv = {{ .pkts = 0, .bytes = 0 }};
            bpf_map_update_elem(&ddos_victims, &dk, &nv, BPF_NOEXIST);
            dv = bpf_map_lookup_elem(&ddos_victims, &dk);
        }}
        if (dv) {{
            __sync_fetch_and_add(&dv->pkts, 1);
            __sync_fetch_and_add(&dv->bytes, wlen);
        }}
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


def marker_state(text):
    return {m: text.count(m) for m in MARKERS}


def require_once(text, needle, what):
    n = text.count(needle)
    if n != 1:
        raise PatchError(
            f"ancla '{what}' aparece {n} veces (debe ser exactamente 1): {needle!r}\n"
            f"  -> el fichero ha cambiado respecto a lo medido; no toco nada.")
    return text.index(needle)


def build_patched(text):
    """Devuelve el texto parcheado. Lanza PatchError si algo no cuadra."""
    if "\r" in text:
        raise PatchError("el fichero tiene CR (CRLF); el patcher espera LF. No toco nada.")
    st = marker_state(text)
    present = [m for m, n in st.items() if n > 0]
    if present:
        raise PatchError(
            f"estado parcial/ya aplicado: marcadores {st}. "
            f"Usa --check; para deshacer, `git checkout -- <fichero>`.")

    # Localizar TODAS las anclas sobre el texto original antes de editar.
    i_defs = require_once(text, ANCHOR_DEFS, "defines (#define BPF_ANY 0)")
    i_map = require_once(text, ANCHOR_MAP, "mapa stats")
    i_cnt = require_once(text, ANCHOR_COUNT, "reserve del ring")
    require_once(text, PRE_IP_DECL, "declaracion de ip")
    require_once(text, PRE_IPV4_CHECK, "chequeo IPv4")
    if text.count(RESERVE_CALL) != 1:
        raise PatchError(f"esperaba 1 llamada a {RESERVE_CALL}, hay {text.count(RESERVE_CALL)}")

    # Orden esperado en el fichero: defs < stats < ip decl < IPv4 check < reserve
    i_ip = text.index(PRE_IP_DECL)
    i_v4 = text.index(PRE_IPV4_CHECK)
    if not (i_defs < i_map < i_ip < i_v4 < i_cnt):
        raise PatchError("el orden de las anclas no es el medido "
                         "(defs < stats < ip < chequeo IPv4 < reserve). No toco nada.")

    # Editar de atras hacia delante para no invalidar indices.
    out = text
    out = out[:i_cnt] + TXT_COUNT + out[i_cnt:]
    end_map = i_map + len(ANCHOR_MAP)
    out = out[:end_map] + TXT_MAP + out[end_map:]
    end_defs = i_defs + len(ANCHOR_DEFS)
    out = out[:end_defs] + TXT_DEFS + out[end_defs:]
    verify_structure(out)
    return out


def verify_structure(text):
    """Post-condiciones de un fichero parcheado (sirve para --check tambien)."""
    st = marker_state(text)
    bad = {m: n for m, n in st.items() if n != 1}
    if bad:
        raise PatchError(f"marcadores inconsistentes tras parchear: {st}")
    for needle in ("#define BPF_NOEXIST 1", "#define BPF_MAP_TYPE_LRU_HASH 9",
                   "} ddos_victims SEC(\".maps\");"):
        if text.count(needle) != 1:
            raise PatchError(f"'{needle}' aparece {text.count(needle)} veces, esperaba 1")
    i_cnt = text.index(M_COUNT)
    i_res = text.index(RESERVE_CALL)
    i_v4 = text.index(PRE_IPV4_CHECK)
    if not (i_v4 < i_cnt < i_res):
        raise PatchError("el bloque de conteo NO esta entre el chequeo IPv4 y el reserve "
                         "(contaminaria con la perdida del ring, o usaria `ip` sin validar)")
    # El conteo no debe estar dentro de ningun `if (!event)`/rama del ring.
    if text.index("} ddos_victims") > i_cnt:
        raise PatchError("el mapa esta declarado despues de su uso")


def find_compiler_cmd(cc_arg):
    if cc_arg:
        return cc_arg
    if shutil.which("clang"):
        return DEFAULT_CC
    return None


def try_compile(text, cc_cmd, label):
    """Compila `text`. Devuelve (ok, salida). ok=None si no hay compilador."""
    if cc_cmd is None:
        return None, "no hay clang en PATH y no se dio --cc"
    with tempfile.TemporaryDirectory(prefix="ddos_kagg_") as td:
        src = os.path.join(td, "sniffer.bpf.c")
        obj = os.path.join(td, "sniffer.bpf.o")
        with open(src, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        cmd = cc_cmd.format(src=src, out=obj)
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return False, f"[{label}] timeout compilando: {cmd}"
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, f"[{label}] $ {cmd}\n{out}" if out else f"[{label}] $ {cmd}"


def compile_gate(orig, patched, cc_cmd, skip):
    """Baseline y parcheado. Devuelve True si el parcheado compila (o skip)."""
    if skip:
        print("compile : OMITIDO (--skip-compile). NO verificado por el compilador.")
        return True
    ok0, log0 = try_compile(orig, cc_cmd, "baseline")
    if ok0 is None:
        print(f"compile : NO VERIFICABLE ({log0}).")
        print("          Pasa --cc '<tu comando con {src} y {out}>' o ejecuta en la VM defender.")
        return False
    if not ok0:
        print(log0)
        print("compile : el BASELINE (sin parche) ya no compila con este --cc.\n"
              "          El fallo es del comando/includes (-I), no del parche. Ajusta --cc.")
        return False
    print("compile : baseline OK")
    ok1, log1 = try_compile(patched, cc_cmd, "parcheado")
    if not ok1:
        print(log1)
        print("compile : el parcheado NO compila. No escribo nada.")
        return False
    print("compile : parcheado OK")
    return True


def atomic_write(path, text):
    d = os.path.dirname(os.path.abspath(path))
    st = os.stat(path)
    fd, tmp = tempfile.mkstemp(prefix=".ddos_kagg_", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, st.st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry", action="store_true", help="muestra el diff, no escribe")
    g.add_argument("--apply", action="store_true", help="aplica (exige compilar)")
    g.add_argument("--check", action="store_true", help="verifica que esta aplicado")
    ap.add_argument("--file", default=DEFAULT_FILE, help=f"por defecto {DEFAULT_FILE}")
    ap.add_argument("--cc", default=None,
                    help="comando de compilacion con {src} y {out}; "
                         f"por defecto: {DEFAULT_CC}")
    ap.add_argument("--skip-compile", action="store_true",
                    help="no compilar (NO recomendado: el compilador es el arbitro)")
    a = ap.parse_args()

    try:
        text = read_text(a.file)
        cc_cmd = find_compiler_cmd(a.cc)

        if a.check:
            st = marker_state(text)
            if all(n == 0 for n in st.values()):
                print(f"check   : NO aplicado ({a.file})")
                return 1
            verify_structure(text)
            print(f"check   : estructura OK, marcadores {st}")
            ok, log = try_compile(text, cc_cmd, "actual")
            if ok is None:
                print(f"compile : NO VERIFICABLE ({log})")
                return 3
            if not ok:
                print(log)
                return 3
            print("compile : actual OK")
            return 0

        st = marker_state(text)
        if all(n == 1 for n in st.values()):
            verify_structure(text)
            print(f"ya aplicado ({a.file}); nada que hacer.")
            return 0

        patched = build_patched(text)
        diff = "".join(difflib.unified_diff(
            text.splitlines(True), patched.splitlines(True),
            fromfile=a.file + " (antes)", tofile=a.file + " (despues)", n=2))
        print(diff, end="" if diff.endswith("\n") else "\n")

        compiled_ok = compile_gate(text, patched, cc_cmd, a.skip_compile)

        if a.dry:
            print("\n--dry: no se ha escrito nada.")
            return 0 if compiled_ok else 3
        if not compiled_ok:
            return 3
        atomic_write(a.file, patched)
        print(f"\nAPLICADO: {a.file}")
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