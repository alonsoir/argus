#!/usr/bin/env python3
# DAY298: parametriza el dia de las corridas del orquestador. DIA del entorno, por defecto day297
# (las corridas DAY297 salen igual), formato dayNNN validado en el Mac y en el defender.
# Atomico, todo o nada: comprueba cada sustitucion con su numero exacto de apariciones, pasa bash -n
# a los dos resultados y solo entonces escribe. Uso, desde la raiz del repo: --check | --apply
import os, subprocess, sys, tempfile

MARCA = "DAY298-DIA"
F1 = "scripts/timebase/lab_corrida.sh"
F2 = "scripts/timebase/lab_corrida_defender.sh"
VAL = r'''[[ "$DIA" =~ ^day[0-9]{3}$ ]] || { echo "DIA invalido: '$DIA' (formato dayNNN, p. ej. day298)"; exit 2; }'''
CAMBIOS = {
    F1: [
        ("# Para al primer fallo. Resultado en /vagrant/logs/lab/day297/NOMBRE/.\n",
         "# Para al primer fallo. Resultado en /vagrant/logs/lab/$DIA/NOMBRE/ (DIA del entorno, por defecto day297). [DAY298-DIA]\n", 1),
        ("H=/vagrant/scripts/timebase/lab_corrida_defender.sh\n",
         "H=/vagrant/scripts/timebase/lab_corrida_defender.sh\nDIA=${DIA:-day297}\n" + VAL + "\n", 1),
        ('-c "bash $H ', '-c "DIA=$DIA bash $H ', 6),
        ("HECHO: logs/lab/day297/$N/", "HECHO: logs/lab/$DIA/$N/", 1),
    ],
    F2: [
        ("D=/vagrant/logs/lab/day297\n",
         "DIA=${DIA:-day297}  # [DAY298-DIA]\n" + VAL + "\nD=/vagrant/logs/lab/$DIA\n", 1),
    ],
}

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_dia.py --check | --apply")
    nuevos, errores = {}, []
    for f, cambios in CAMBIOS.items():
        txt = open(f).read()
        if MARCA in txt:
            errores.append(f"{f}: ya lleva la marca {MARCA}")
            continue
        for viejo, nuevo, n in cambios:
            c = txt.count(viejo)
            if c != n:
                errores.append(f"{f}: '{viejo.strip()}' aparece {c} veces, se esperaban {n}")
            else:
                txt = txt.replace(viejo, nuevo)
        nuevos[f] = txt
    if errores:
        print("NO APLICABLE:")
        for e in errores:
            print("  " + e)
        sys.exit(1)
    for f, txt in nuevos.items():
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as t:
            t.write(txt)
        r = subprocess.run(["bash", "-n", t.name], capture_output=True, text=True)
        os.unlink(t.name)
        if r.returncode != 0:
            print(f"NO APLICABLE: bash -n falla en {f}:\n{r.stderr}")
            sys.exit(1)
    if sys.argv[1] == "--check":
        print("CHECK OK: 4 sustituciones en lab_corrida.sh (6 llamadas al ayudante) y 1 en lab_corrida_defender.sh; bash -n limpio")
        return
    for f, txt in nuevos.items():
        modo = os.stat(f).st_mode
        tmp = f + ".tmp"
        with open(tmp, "w") as o:
            o.write(txt)
        os.chmod(tmp, modo)
    for f in nuevos:
        os.replace(f + ".tmp", f)
    print("APLICADO [DAY298-DIA]")

main()
