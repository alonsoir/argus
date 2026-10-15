#!/usr/bin/env python3
# DAY298: incorpora al diseno las decisiones de Alonso sobre 3 b) (P_abs por instalacion, defecto seguro
# no optimo) y 8 (el log no es via de actuacion; actuar = re-sembrar la base o rango protegido, no ipset).
# Atomico. Uso, desde la raiz del repo: --check | --apply
import os, sys

F = "docs/ml-heads/diseno_etapa1_histeresis_day298.md"
MARCA = "[D298-ALONSO]"
V3B = ("  b) clave FRIA y pps >= P_abs (NUEVO, ddos_victim_abs_pps en sniffer.json, con _doc, rango y defecto\n"
       "     validado; [CONFIG-DEFAULT] si falta o es inválido). Sin esto un ataque presente al arrancar se\n"
       "     aprende como base.\n")
N3B = ("  b) clave FRIA y pps >= P_abs (NUEVO, ddos_victim_abs_pps en sniffer.json; [CONFIG-DEFAULT] si falta o\n"
       "     es inválido). Sin esto un ataque presente al arrancar se aprende como base. [D298-ALONSO] No hay\n"
       "     valor óptimo universal: depende de cada instalación (pipeline en una o varias máquinas, su\n"
       "     capacidad, el tráfico legítimo normal de cada víctima). El _doc presenta el rango de actuación\n"
       "     medido en el laboratorio y el defecto es SEGURO, no óptimo; lo calibra cada instalación. El\n"
       "     defecto concreto sale de la medida del apartado 6.\n")
A8 = "## 8. Preguntas abiertas\n"
N8 = """## 8. Actuación humana y preguntas abiertas [D298-ALONSO]

- Un aviso en un log no es una vía de actuación: el administrador actúa de forma asíncrona desde la
  consola de operación (DAY296, areas/dashboard-export). Hasta que exista, los avisos quedan en el log y
  como contador en el resumen periódico, y figuran como requisito de la consola.
- Actuar sobre una víctima en presión prolongada NO es tocar el ipset (los bans son del firewall,
  temporales y escalados por reincidencia, RECIDIVISM-D276). Es una de dos cosas: aceptar su tráfico
  actual como base nueva (re-sembrar la EWMA) o declararla rango protegido (apartado 5).
- Mientras nadie actúa, el efecto es acotado: la etapa 1 deja pasar todos los flujos de esa víctima al
  RF, que es quien decide; el daño aparece solo si el RF se equivoca (TCP de Wazuh DAY297, p1 0,86).
- Abierta (rama de medidas y modelo): salida automática de presión si en N horas el RF no ha dado ningún
  positivo para la víctima. Requiere realimentación ml-detector -> sniffer; N en el JSON.
- Calibración de P_abs y de los demás umbrales por despliegue (D22): el laboratorio no la decide.
"""

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        sys.exit("uso: d298_patch_diseno.py --check | --apply")
    txt = open(F).read()
    if MARCA in txt:
        sys.exit(f"NO APLICABLE: {F} ya lleva {MARCA}")
    errores = []
    if txt.count(V3B) != 1:
        errores.append(f"apartado 3 b) aparece {txt.count(V3B)} veces, se esperaba 1")
    if txt.count(A8) != 1:
        errores.append(f"cabecera del apartado 8 aparece {txt.count(A8)} veces, se esperaba 1")
    if errores:
        sys.exit("NO APLICABLE:\n  " + "\n  ".join(errores))
    nuevo = txt.replace(V3B, N3B)
    nuevo = nuevo[:nuevo.index(A8)] + N8
    if sys.argv[1] == "--check":
        print("CHECK OK: 3 b) reescrito y apartado 8 sustituido")
        return
    tmp = F + ".tmp"
    with open(tmp, "w") as o:
        o.write(nuevo)
    os.replace(tmp, F)
    print("APLICADO [D298-ALONSO]")

main()
