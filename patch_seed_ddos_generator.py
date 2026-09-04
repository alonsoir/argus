#!/usr/bin/env python3
"""
patch_seed_ddos_generator.py — Paso 1 (semilla) de la reparacion de la cabeza DDoS.

Fija la semilla del generador sintetico DDoS para que regenerar el dataset sea
REPRODUCIBLE bit a bit (mismo dataset -> mismo .hpp). Filosofia Via Appia: un
modelo que el propio autor no reproduce no es defendible.

Aplica DOS ediciones quirurgicas en SyntheticDDOSGenerator.py:
  A) np.random.seed(42) al inicio de create_complete_dataset()  [antes del 1er np.random]
  B) random_state=42 en el shuffle .sample(frac=1)

Propiedades:
  - MIDE antes de tocar: si las lineas ancla no estan, falla ruidosamente (no adivina).
  - IDEMPOTENTE: si ya esta parcheado, no vuelve a aplicar.
  - --check: solo informa el estado, no escribe (para revisar antes de commitear).
  - Verifica que el resultado compila (py_compile).
  - No commitea: git es la red de seguridad y el commit lo decides tu.

Uso:
  python3 patch_seed_ddos_generator.py [ruta] [--check]
  (ruta por defecto: ml-training/scripts/ddos_detection/SyntheticDDOSGenerator.py)
"""
import sys
import os
import difflib
import py_compile

DEFAULT_PATH = "ml-training/scripts/ddos_detection/SyntheticDDOSGenerator.py"

# --- Anclas exactas (tal como se midieron en el fichero real) ---
DOCSTRING_ANCHOR = '        """Crea dataset balanceado normal vs DDoS"""\n'
SEED_LINE = ('        np.random.seed(42)  '
             '# DAY255 reproducibilidad de artefacto: mismo dataset -> mismo .hpp (Via Appia)\n')
SAMPLE_OLD = '        complete_df = complete_df.sample(frac=1).reset_index(drop=True)\n'
SAMPLE_NEW = '        complete_df = complete_df.sample(frac=1, random_state=42).reset_index(drop=True)\n'

SEED_MARKER = "np.random.seed(42)"
SAMPLE_MARKER = "random_state=42"


def analyze(text):
    """Devuelve (needs_seed, needs_sample, problems[])."""
    problems = []
    has_seed = SEED_MARKER in text
    has_sample = "random_state=42" in text and ".sample(frac=1" in text

    needs_seed = not has_seed
    needs_sample = not has_sample

    if needs_seed and DOCSTRING_ANCHOR not in text:
        problems.append("No encuentro el ancla del docstring de create_complete_dataset(). "
                        "El fichero ha cambiado respecto a lo medido; revisar a mano.")
    if needs_sample and SAMPLE_OLD not in text:
        problems.append("No encuentro la linea exacta '.sample(frac=1).reset_index(drop=True)'. "
                        "El fichero ha cambiado respecto a lo medido; revisar a mano.")
    return needs_seed, needs_sample, problems


def apply_patch(text):
    if SEED_MARKER not in text:
        text = text.replace(DOCSTRING_ANCHOR, DOCSTRING_ANCHOR + SEED_LINE, 1)
    if not ("random_state=42" in text and ".sample(frac=1" in text):
        text = text.replace(SAMPLE_OLD, SAMPLE_NEW, 1)
    return text


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    path = args[0] if args else DEFAULT_PATH
    check_only = "--check" in flags

    if not os.path.isfile(path):
        print(f"[ERROR] No existe el fichero: {path}", file=sys.stderr)
        return 2

    with open(path, "r") as f:
        original = f.read()

    needs_seed, needs_sample, problems = analyze(original)

    if not needs_seed and not needs_sample:
        print(f"[OK] Ya parcheado: semilla y random_state presentes en {path}")
        return 0

    if problems:
        for p in problems:
            print(f"[ERROR] {p}", file=sys.stderr)
        return 3

    patched = apply_patch(original)

    # Mostrar el diff siempre (para revision)
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=path + " (antes)", tofile=path + " (despues)",
    )
    sys.stdout.writelines(diff)

    if check_only:
        print(f"\n[CHECK] El parche SE APLICARIA (seed={needs_seed}, sample={needs_sample}). "
              f"No se ha escrito nada (--check).")
        return 10  # codigo != 0 para señalar "pendiente"

    with open(path, "w") as f:
        f.write(patched)

    # Verificar que compila
    try:
        py_compile.compile(path, doraise=True)
    except py_compile.PyCompileError as e:
        print(f"\n[ERROR] El fichero parcheado NO compila:\n{e}", file=sys.stderr)
        return 4

    print(f"\n[OK] Parche aplicado y compila: {path}")
    print("      Revisa el diff de arriba, luego commitea SOLO este cambio:")
    print('      git add ' + path)
    print('      git commit -m "fix(ddos): semilla fija en generador para reproducibilidad de artefacto (DAY255)"')
    return 0


if __name__ == "__main__":
    sys.exit(main())