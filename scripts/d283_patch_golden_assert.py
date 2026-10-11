#!/usr/bin/env python3
# DAY283 — assert_golden_state_legal activo en todos los perfiles (no depender de NDEBUG).
# En production (-DNDEBUG) el assert desaparecia: -Werror=unused-parameter rompia el build
# y, aun silenciado, la comprobacion pasaba en vacio.
import re, sys, shutil, pathlib

p = pathlib.Path("/vagrant/ml-detector/tests/integration/correlation_v1_golden_vectors.hpp")
src = p.read_text()

MARK = "DAY283: comprobacion activa sin NDEBUG"
if MARK in src:
    print("YA PARCHEADO: nada que hacer"); sys.exit(0)

pat = re.compile(
    r'assert\(!\(gv\.expect_skip && gv\.expect_reject\)\s*&&\s*'
    r'"GoldenVector ilegal: expect_skip y expect_reject simultáneos"\);')
m = pat.findall(src)
if len(m) != 1:
    print(f"PARAR: assert encontrado {len(m)} veces (esperado 1)"); sys.exit(1)

new = ('// ' + MARK + ' (en production el assert desaparecia y el test pasaba en vacio)\n'
       '    if (gv.expect_skip && gv.expect_reject) {\n'
       '        std::fprintf(stderr, "GoldenVector ilegal (%s): expect_skip y expect_reject simultáneos\\n",\n'
       '                     gv.id.c_str());\n'
       '        std::abort();\n'
       '    }')
src = pat.sub(lambda _: new, src, count=1)

for inc in ("#include <cstdlib>", "#include <cstdio>"):
    if inc not in src:
        i = src.index("#include")
        src = src[:i] + inc + "\n" + src[i:]

shutil.copy(p, str(p) + ".bak_d283")
p.write_text(src)
print("OK: comprobacion reescrita sin assert; copia en .bak_d283")
