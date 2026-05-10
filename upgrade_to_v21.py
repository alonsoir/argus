#!/usr/bin/env python3
"""
upgrade_to_v21.py — aRGus NDR DAY 147
Aplica los cambios v20 → v21 sobre docs/argus_ndr_v20.tex y references.bib.

Cambios aplicados:
  main.tex:
    1. Cabecera: Draft v20 → v21, DAY 146 → 147, fecha
    2. \date{}: Draft v20 → v21
    3. Acknowledgments: 146 days → 147 days
    4. §8.13 párrafo "Future work: historical rulesets" →
         hallazgos reales DAY 147 (búsqueda infructuosa + HTTP C2 + Springer 2023)

  references.bib:
    5. Añade entrada @article{asad2023perspective} (signature aging, Springer 2023)

Uso:
    python3 upgrade_to_v21.py [--tex PATH] [--bib PATH] [--dry-run]

Por defecto busca:
    ./docs/argus_ndr_v20.tex
    ./references.bib
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime


# ─── Cambio 1: cabecera del fichero ──────────────────────────────────────────

OLD_HEADER = "% Draft v20 --- DAY 146 --- 9 May 2026"
NEW_HEADER = "% Draft v21 --- DAY 147 --- 10 May 2026"

# ─── Cambio 2: \date{} ───────────────────────────────────────────────────────

OLD_DATE = r"\date{Draft v20 --- May 2026}"
NEW_DATE = r"\date{Draft v21 --- May 2026}"

# ─── Cambio 3: Acknowledgments ───────────────────────────────────────────────

OLD_DAYS = r"across \textbf{146 days} of"
NEW_DAYS = r"across \textbf{147 days} of"

# ─── Cambio 4: §8.13 "Future work: historical rulesets" ─────────────────────
# Reemplaza el bloque completo — desde \paragraph hasta el cierre de la subsección
# El delimitador seguro es el comentario de cierre ─────... que existe en el tex.

OLD_HISTORICAL = r"""    \paragraph{Future work: historical rulesets.}
    A complete characterization of the signature-vs-behavior gap would require repeating the
    Suricata experiment with the ET~Open ruleset \emph{from 2011}, to distinguish ``the rule
    was never written'' from ``the rule existed and was later retired.'' Historical ruleset
    archives may be available via the Emerging Threats repository; this experiment is scheduled
    as future work."""

NEW_HISTORICAL = r"""    \paragraph{Historical rulesets: DAY~147 search and findings.}
    A complete characterization of the signature-vs-behavior gap would require repeating the
    Suricata experiment with the ET~Open ruleset \emph{from August~2011}, to distinguish
    ``the rule existed and was later retired'' (signature aging) from ``the rule was never
    written'' (coverage gap from inception).

    A systematic search was conducted in DAY~147 across three independent sources: (1)~the
    Wayback Machine CDX~API --- binary \texttt{.tar.gz} archives are not indexed as
    retrievable snapshots; (2)~the EmergingThreats GitHub organization --- no historical
    rule repositories are publicly available; (3)~bundled rulesets distributed with
    SecurityOnion and alienfault/ossim --- creation timestamps are unverifiable for
    August~2011. No public archive of the ET~Open ruleset from August~2011 was located.

    The search yielded an additional finding with direct scientific relevance: the
    official CTU-13 Neris dataset documentation~\cite{garcia2014} records the bot's C2
    channel as \emph{HTTP-based}, not IRC. The scenario~42 README states explicitly:
    \emph{``The bot sent spam, connected to an HTTP CC, and use HTTP to do some
    ClickFraud.''} This implies that IRC-specific botnet signatures --- the most
    prevalent category of 2011 ET~Open rules targeting Neris-family malware --- would
    not have matched this specific capture regardless of ruleset vintage. The behavioral
    paradigm gap between ML-based and signature-based detection is therefore deeper than
    the signature aging hypothesis alone suggests: even a contemporaneous ruleset would
    have required prior knowledge of Neris's specific HTTP~C2 patterns.

    The signature aging phenomenon is independently documented in the academic
    literature. \citet{asad2023perspective} conducted a perspective-retrospective
    analysis of Snort and Suricata ET~Open rules over a four-year window (2017--2020),
    finding that detection performance does not evolve linearly with ruleset updates ---
    a quantitative confirmation that signatures for historical threat families are retired
    as new coverage emerges~\cite{asad2023perspective}.

    The inability to locate public historical ruleset archives is itself a finding: it
    motivates the security community to maintain versioned, time-stamped public archives
    of open-source IDS rulesets --- analogous to software package repositories with
    locked dependency snapshots --- to enable reproducible longitudinal evaluation. This
    infrastructure gap is noted as a community recommendation."""

# ─── Cambio 5: nueva entrada en references.bib ───────────────────────────────
# Se añade al final del .bib, antes del último salto de línea.
# Los autores (Asad & Gashi) están confirmados por las citas cruzadas en el paper
# (resultado 70 de la búsqueda: "Asad H, Gashi I (2018)..." es la versión anterior
# de los mismos autores; el DOI 10.1007/s10207-023-00794-9 es el paper de 2023).

NEW_BIB_ENTRY = r"""
@article{asad2023perspective,
  author  = {Asad, Hassnain and Gashi, Ilir},
  title   = {A Perspective--Retrospective Analysis of Diversity in Signature-Based
             Open-Source Network Intrusion Detection Systems},
  journal = {International Journal of Information Security},
  year    = {2023},
  volume  = {23},
  doi     = {10.1007/s10207-023-00794-9},
  note    = {Accessed: May 2026}
}
"""

# ─────────────────────────────────────────────────────────────────────────────

CHANGES_TEX = [
    ("Cabecera (v20→v21, DAY 146→147)", OLD_HEADER, NEW_HEADER),
    (r"\date{} (v20→v21)",              OLD_DATE,   NEW_DATE),
    ("Acknowledgments (146→147 days)",  OLD_DAYS,   NEW_DAYS),
    ("§8.13 historical rulesets",       OLD_HISTORICAL, NEW_HISTORICAL),
]


def backup(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(f".bak_{ts}{path.suffix}")
    shutil.copy2(path, bak)
    return bak


def apply_tex(tex_path: Path, dry_run: bool) -> bool:
    content = tex_path.read_text(encoding="utf-8")
    ok = True

    for label, old, new in CHANGES_TEX:
        if old not in content:
            print(f"  ❌ NO ENCONTRADO — {label}")
            print(f"     Busca manualmente: {old[:60]!r}")
            ok = False
        elif dry_run:
            print(f"  🔍 DRY-RUN OK — {label}")
        else:
            content = content.replace(old, new, 1)
            print(f"  ✅ Aplicado — {label}")

    if not dry_run and ok:
        tex_path.write_text(content, encoding="utf-8")

    return ok


def apply_bib(bib_path: Path, dry_run: bool) -> bool:
    content = bib_path.read_text(encoding="utf-8")

    if "asad2023perspective" in content:
        print("  ℹ️  asad2023perspective ya existe en .bib — saltando")
        return True

    if dry_run:
        print("  🔍 DRY-RUN — añadiría @article{asad2023perspective} al .bib")
        return True

    content = content.rstrip() + "\n" + NEW_BIB_ENTRY
    bib_path.write_text(content, encoding="utf-8")
    print("  ✅ Añadida entrada @article{asad2023perspective}")
    return True


def verify_tex(tex_path: Path) -> bool:
    content = tex_path.read_text(encoding="utf-8")
    checks = [
        ("Draft v21",                   "v21 en cabecera/date"),
        ("DAY 147",                     "DAY 147 en cabecera"),
        (r"\textbf{147 days}",          "147 days en acknowledgments"),
        ("DAY~147 search and findings", "§8.13 actualizado"),
        ("HTTP CC",                     "hallazgo HTTP C2"),
        ("asad2023perspective",         "cita Springer 2023"),
    ]
    all_ok = True
    for needle, label in checks:
        if needle in content:
            print(f"  ✅ {label}")
        else:
            print(f"  ❌ FALTA: {label}  ({needle!r})")
            all_ok = False
    return all_ok


def verify_bib(bib_path: Path) -> bool:
    content = bib_path.read_text(encoding="utf-8")
    if "asad2023perspective" in content:
        print("  ✅ @article{asad2023perspective} presente")
        return True
    print("  ❌ @article{asad2023perspective} ausente")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Actualiza argus_ndr_v20.tex y references.bib a la versión v21 (DAY 147)"
    )
    parser.add_argument("--tex", default="docs/argus_ndr_v20.tex",
                        help="Ruta al .tex (default: docs/argus_ndr_v20.tex)")
    parser.add_argument("--bib", default="references.bib",
                        help="Ruta al .bib (default: references.bib)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra cambios sin escribir en disco")
    args = parser.parse_args()

    tex_path = Path(args.tex)
    bib_path = Path(args.bib)

    for p in (tex_path, bib_path):
        if not p.exists():
            print(f"❌ No se encuentra: {p}")
            sys.exit(1)

    print(f"📄 TEX : {tex_path.resolve()}")
    print(f"📄 BIB : {bib_path.resolve()}")
    print(f"{'🔍 DRY-RUN — sin cambios en disco' if args.dry_run else '✏️  Modo escritura'}\n")

    if not args.dry_run:
        bak_tex = backup(tex_path)
        bak_bib = backup(bib_path)
        print(f"📦 Backups: {bak_tex.name} / {bak_bib.name}\n")

    print("── Cambios en main.tex ──────────────────────────────────────")
    tex_ok = apply_tex(tex_path, args.dry_run)

    print("\n── Cambios en references.bib ────────────────────────────────")
    bib_ok = apply_bib(bib_path, args.dry_run)

    if args.dry_run:
        print("\n✅ Dry-run completado — sin cambios en disco.")
        return

    print("\n── Verificación post-parche ─────────────────────────────────")
    tex_ok2 = verify_tex(tex_path)
    bib_ok2 = verify_bib(bib_path)

    if tex_ok and bib_ok and tex_ok2 and bib_ok2:
        print("""
╔════════════════════════════════════════════════════════════╗
║  ✅ v21 aplicado correctamente                            ║
║  Siguiente: pdflatex docs/argus_ndr_v20.tex               ║
║             (o renombra el fichero a argus_ndr_v21.tex)   ║
╚════════════════════════════════════════════════════════════╝""")
    else:
        print("\n❌ Algún cambio no se aplicó — revisa los errores arriba.")
        sys.exit(1)


if __name__ == "__main__":
    main()