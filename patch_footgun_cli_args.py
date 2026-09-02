#!/usr/bin/env python3
"""
patch_footgun_cli_args.py — footgun CLI en GenerateDDOSCPPForest.py.

El script parsea input_pkl=argv[1] y output_hpp=argv[2] pero luego LOS IGNORA:
llama a load_ddos_model() y generate_ddos_cpp_header() con literales
hardcodeados. Este parche hace que las dos llamadas usen las variables ya
definidas en main(). input_json permanece como default de convención — la
firma del CLI sigue siendo <pkl> <hpp> (2 args). NO ampliamos alcance.

Idempotente. --check no escribe. Verifica que el resultado compila antes de
tocar el fichero. NO commitea.
"""
from __future__ import annotations
import argparse
import difflib
import py_compile
import tempfile
from pathlib import Path

DEFAULT_TARGET = Path("ml-training/scripts/ddos_detection/GenerateDDOSCPPForest.py")

# (old, new). old debe aparecer exactamente 1 vez cuando el parche NO está aplicado.
EDITS = [
    (
        '    model, dataset_info, scaler = load_ddos_model(\n'
        '        "ddos_detection_model.pkl",\n'
        '        "ddos_detection_dataset.json"\n'
        '    )',
        '    model, dataset_info, scaler = load_ddos_model(\n'
        '        input_pkl,\n'
        '        input_json\n'
        '    )',
    ),
    (
        '    generate_ddos_cpp_header(forest_data, dataset_info, "ddos_trees_inline.hpp")',
        '    generate_ddos_cpp_header(forest_data, dataset_info, output_hpp)',
    ),
]


def classify(text: str, old: str, new: str) -> str:
    has_old, has_new = old in text, new in text
    if has_old and not has_new:
        return "pending"
    if has_new and not has_old:
        return "applied"
    if has_old and has_new:
        return "ambiguous"
    return "missing"


def apply_edits(text: str):
    out, report = text, []
    for i, (old, new) in enumerate(EDITS, 1):
        st = classify(out, old, new)
        report.append((i, st))
        if st == "pending":
            n = out.count(old)
            if n != 1:
                raise SystemExit(f"[edit {i}] esperaba 1 coincidencia, hay {n} — abortando")
            out = out.replace(old, new)
    return out, report


def main() -> None:
    ap = argparse.ArgumentParser(description="Footgun CLI en GenerateDDOSCPPForest.py (idempotente).")
    ap.add_argument("--check", action="store_true", help="no escribe; solo informa del estado")
    ap.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = ap.parse_args()

    target: Path = args.target
    if not target.is_file():
        raise SystemExit(f"no encuentro {target} (¿CWD correcto?)")

    original = target.read_text(encoding="utf-8")
    patched, report = apply_edits(original)

    for i, st in report:
        print(f"  edit {i}: {st}")

    if any(st in ("ambiguous", "missing") for _, st in report):
        raise SystemExit("estado inesperado (fichero cambiado desde el parche) — nada escrito")

    if patched == original:
        print("\u2713 ya aplicado — no-op")
        return

    # Verificar que el resultado compila ANTES de escribir.
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(patched)
        tmp_path = Path(tmp.name)
    try:
        py_compile.compile(str(tmp_path), doraise=True)
    finally:
        tmp_path.unlink(missing_ok=True)
    print("\u2713 el resultado parcheado compila")

    print("".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=str(target), tofile=str(target) + " (parcheado)",
    )))

    if args.check:
        print("--check: NO escrito")
        return

    target.write_text(patched, encoding="utf-8")
    print(f"\u2713 escrito {target}")


if __name__ == "__main__":
    main()