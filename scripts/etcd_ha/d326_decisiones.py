#!/usr/bin/env python3
# d326_decisiones.py — DAY326: recoge en docs/BACKLOG.md y en el prompt de continuidad las tres decisiones de Alonso de
# última hora (suelo del manifiesto: opción b; recursos del anfitrión: se mide todo; test-etcd-cluster y
# test-etcd-reinicio en EMECAS). Sobre el commit de documentación de DAY326.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d326_decisiones.py --check | --apply
import hashlib
import os
import sys

TAG = "[D326-DECISIONES]"
INICIO = {'docs/BACKLOG.md': 'bd32b2595617bbdaaea300db54ea0cf237ca2c226a8ae2250581327b5708163a', 'docs/continuity/PROMPT_CONTINUE_CLAUDE.md': 'a73bf85656f6b3214de71ba47a26f24e8dd382c22650a0a20a8f2a519f43f72c'}
FINAL = {'docs/BACKLOG.md': '2ff0fe7db6296c15cb104e2dfd8a16905d3295594152e12c22b0c8b04a805fdf', 'docs/continuity/PROMPT_CONTINUE_CLAUDE.md': '047c2fe22d31e6240bb588be0846fff2ae61ff76693231d538a247a6603a8fab'}
CAMBIOS = {'docs/BACKLOG.md': [('### DEBT-PROTEGIDOS-SUELO-REVAULT-001 — ABIERTA (nueva DAY325)\nTras rehacer Vault', '### DEBT-PROTEGIDOS-SUELO-REVAULT-001 — ABIERTA (nueva DAY325; opción decidida DAY326)\n**Decidido DAY326 (Alonso): (b)**, «a falta de algo mejor»: el suelo guarda (huella de la clave, versión); si la huella\ncompilada en el firewall no es la del suelo, el suelo se reinicia con aviso en el log. No debilita el anti-retroceso: un\nmanifiesto viejo va firmado con la clave vieja y no verifica con la nueva, y cambiar la clave compilada exige cambiar el\nbinario. Hay que tocar el firewall (C++), el formato del suelo (con migración), sus tests y ADR-060; lo difícil es la\nrotación (ranura actual y siguiente: qué huella manda). Mientras tanto, y en cualquier caso: el rechazo por suelo debe\nsalir como error claro y periódico en el log («versión X ≤ suelo Y; huella del suelo ≠ huella compilada»). Test que pide:\nsuelo del linaje viejo + clave nueva → acepta la v1 con aviso; manifiesto de versión mayor firmado con la clave vieja →\nsigue rechazado. Un análisis del binario (REA) no lo encontraría: el binario hace lo que se diseñó; el fallo es de estado\na lo largo del ciclo de vida y solo lo enseña un E2E (rehacer Vault sin rehacer el defender).\nEl problema (DAY325): tras rehacer Vault', 1), ('### DEBT-CURL-FUERA-PRODUCCION-001 — ABIERTA (nueva DAY326)\n', 'Propuesta DAY326 (Claude, por medir; Alonso: «mediremos todo lo que haga falta»): en un JSON con rango y defecto\navisado, carga media de 5 min ≤ 8 (la mitad de las 16 CPU lógicas; la de 1 min salta con picos y la de 15 arrastra),\nswap usado ≤ 1 GB (la señal más limpia), disco libre ≥ 50 GB (medir cuánto crece en un EMECAS) y, solo en EMECAS antes\ndel vagrant up, RAM disponible ≥ 20 GB. Registrar los mismos valores también al terminar, como dato. Medir antes el Mac\ntranquilo con el lab arriba.\n\n### DEBT-EMECAS-PLANO-CONTROL-001 — ABIERTA (decidida DAY326, Alonso)\n`test-etcd-cluster` y `test-etcd-reinicio` entran en EMECAS, en el grupo de `test-argus-infra` (antes del test de\nsilencio de Falco y de lab-e2e: sus trazas Notice no cuentan como CRITICAL ni caen en la ventana de C8). Alonso: «son\npocos minutos, y encima nos dice si el HA va bien entre PR». Bajar el ruido del escritor de `test-etcd-reinicio` (una\nescritura cada 2 s, intervalo en su configuración). Antes: cronometrar los dos y medir las trazas con el escritor a 2 s.\n\n### DEBT-CURL-FUERA-PRODUCCION-001 — ABIERTA (nueva DAY326)\n', 1)], 'docs/continuity/PROMPT_CONTINUE_CLAUDE.md': [('    - Suelo del manifiesto tras rehacer Vault: (a) paso manual del runbook, o (b) el firewall ata el suelo a la huella de\n      la clave compilada (toca ADR-060). Medir si el etcd-server tiene un estado equivalente.\n', '    - **Decidido DAY326: suelo del manifiesto (b)**, el firewall ata el suelo a la huella de la clave compilada\n      (DEBT-PROTEGIDOS-SUELO-REVAULT-001: toca C++, formato del suelo, tests y ADR-060; lo difícil es la rotación).\n      Antes: medir si el etcd-server tiene un estado equivalente y leer cómo trata el firewall la ranura siguiente.\n', 1), ('    - `test-etcd-reinicio`: ¿entra en lab-e2e/EMECAS? ¿`test-etcd-cluster` en EMECAS?\n', '    - **Decidido DAY326: `test-etcd-cluster` y `test-etcd-reinicio` en EMECAS** (DEBT-EMECAS-PLANO-CONTROL-001), en el\n      grupo de `test-argus-infra`; el escritor a una escritura cada 2 s. Antes: cronometrarlos y medir las trazas.\n    - Umbrales de recursos (propuesta por medir): carga 5 min ≤ 8, swap ≤ 1 GB, disco ≥ 50 GB, RAM ≥ 20 GB solo en EMECAS.\n', 1), ('3. **Decisiones pendientes de Alonso:**\n', '3. **Decisiones de Alonso (las tres tomadas DAY326; faltan las medidas):**\n', 1)]}
NUEVOS = {}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print(f"{TAG} uso: python3 -I scripts/etcd_ha/d326_decisiones.py --check | --apply", file=sys.stderr)
        return 2
    if not (os.path.isfile("Vagrantfile") and os.path.isdir(".git")):
        print(f"{TAG} FALLA: ejecútalo desde la raíz del repo", file=sys.stderr)
        return 1
    nuevos, ya = {}, 0
    for p in sorted(FINAL):
        existe = os.path.exists(p)
        if existe and sha(open(p, "rb").read()) == FINAL[p]:
            print(f"{TAG} {p}: ya aplicado")
            ya += 1
            continue
        if p in NUEVOS:
            if existe:
                print(f"{TAG} FALLA: {p} ya existe y no es el esperado; nada escrito", file=sys.stderr)
                return 1
            r = NUEVOS[p].encode("utf-8")
            que = "nuevo"
        else:
            if not existe:
                print(f"{TAG} FALLA: falta {p}; nada escrito", file=sys.stderr)
                return 1
            b = open(p, "rb").read()
            if sha(b) != INICIO[p]:
                print(f"{TAG} FALLA: {p} sha256 {sha(b)} no es el de partida {INICIO[p]} ni el final; nada escrito",
                      file=sys.stderr)
                return 1
            s = b.decode("utf-8")
            for i, (a, n, veces) in enumerate(CAMBIOS[p]):
                c = s.count(a)
                if c != veces:
                    print(f"{TAG} FALLA: {p} ancla {i} aparece {c} veces (se exigen {veces}); nada escrito",
                          file=sys.stderr)
                    return 1
                s = s.replace(a, n)
            r = s.encode("utf-8")
            que = f"{len(CAMBIOS[p])} anclas con sus veces exactas"
        if sha(r) != FINAL[p]:
            print(f"{TAG} FALLA: {p} resultado {sha(r)} no es el esperado {FINAL[p]}; nada escrito", file=sys.stderr)
            return 1
        nuevos[p] = r
        print(f"{TAG} {p}: {que}; resultado {FINAL[p][:16]}")
    if sys.argv[1] == "--check":
        print(f"{TAG} CHECK OK: {len(nuevos)} por aplicar, {ya} ya aplicados")
        return 0
    for p, r in nuevos.items():
        modo = os.stat(p).st_mode if os.path.exists(p) else 0o100644
        tmp = p + ".d326ztmp"
        with open(tmp, "wb") as f:
            f.write(r)
        os.chmod(tmp, modo & 0o7777)
        os.replace(tmp, p)
    print(f"{TAG} APLICADO: {len(nuevos)} escritos, {ya} ya estaban.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
