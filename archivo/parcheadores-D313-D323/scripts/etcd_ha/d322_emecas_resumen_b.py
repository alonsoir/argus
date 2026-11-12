#!/usr/bin/env python3
# d322_emecas_resumen_b.py — DAY322 [EMECAS-RESUMEN-D322], sobre d322_emecas_progreso.py YA aplicado (el avance):
# añade el resumen de cada corrida (logs/lab/emecas/<fecha>_<meta>/: log de cada paso y resumen.md, también si falla;
# se guardan todas) y 3 tests (9 en total).
# Uso, desde la raíz del repo:  python3 scripts/etcd_ha/d322_emecas_resumen_b.py --check | --apply
# Todo o nada: --check comprueba que cada fichero está en su estado de partida (sha256) o ya parcheado; --apply escribe
# todo solo si --check pasa. Idempotente: dos --apply dejan lo mismo.
import hashlib, json, os, sys, tempfile
D = json.loads(r'''{
"cambios": [
{
"ruta": "Makefile",
"sha_antes": "34581cfaaedbb8ac02c4a59715a7d04bbef5174f7ca3d99ce0040cd5a2352d4e",
"sha_despues": "284d890a180760c9a26756d71154de4cd08ace995e2c07b46c603ed42081cad9",
"trozos": [
[
"# envuelto por scripts/emecas/emecas_paso.py, que lo ejecuta igual (misma salida y código de salida) y apunta en\n# logs/lab/emecas_progreso.txt cuándo empieza y acaba. Porcentaje y hora de fin, de los tiempos MEDIDOS en la última\n# corrida buena de la misma meta (logs/lab/emecas_tiempos_<meta>.tsv). Desde otra terminal: make emecas-progreso.\nEMECAS_META := $(firstword $(filter emecas+++ emecas++ emecas,$(MAKECMDGOALS)))\nEMECAS_META_O = $(or $(EMECAS_META),emecas)\nEMECAS_PY := python3 scripts/emecas/emecas_paso.py\n",
"# envuelto por scripts/emecas/emecas_paso.py, que lo ejecuta igual (misma salida y código de salida) y apunta en\n# logs/lab/emecas_progreso.txt cuándo empieza y acaba. Porcentaje y hora de fin, de los tiempos MEDIDOS en la última\n# corrida buena de la misma meta (logs/lab/emecas_tiempos_<meta>.tsv). Desde otra terminal: make emecas-progreso.\n# [EMECAS-RESUMEN-D322] cada corrida deja en logs/lab/emecas/<fecha>_<meta>/ la salida de cada paso (NN_<paso>.log) y\n# resumen.md (al final y también si un paso falla); se guardan todas (decisiones de Alonso DAY322).\nEMECAS_META := $(firstword $(filter emecas+++ emecas++ emecas,$(MAKECMDGOALS)))\nEMECAS_META_O = $(or $(EMECAS_META),emecas)\nEMECAS_PY := python3 scripts/emecas/emecas_paso.py\n"
]
]
},
{
"ruta": "scripts/emecas/emecas_paso.py",
"sha_antes": "fc24606002d6f56832b6b39822d8a85bc7f5c67ae61d52e447a66602a4e622f4",
"sha_despues": "36ed75f865163f89f61326241b730aa54edd41a1c53c7c40e97022a17e0cb3e5",
"trozos": [
[
"# Corre en el Mac (donde corre make), solo biblioteca estándar. Ficheros, en logs/lab/ del repo:\n#   emecas_progreso.txt          la corrida en curso: META, INICIO y FIN de cada paso (una línea por suceso)\n#   emecas_tiempos_<meta>.tsv    lo que tardó cada paso en la última corrida de <meta> que terminó bien\n# El porcentaje y la hora de fin salen de esos tiempos MEDIDOS, no de contar pasos (lab-e2e dura más de una hora y\n# emecas-frescura segundos). La primera corrida de una meta no tiene tiempos: solo pasos hechos y tiempo transcurrido.\n#   emecas_paso.py inicio META                   empieza una corrida (vacía emecas_progreso.txt)\n",
"# Corre en el Mac (donde corre make), solo biblioteca estándar. Ficheros, en logs/lab/ del repo:\n#   emecas_progreso.txt          la corrida en curso: META, INICIO y FIN de cada paso (una línea por suceso)\n#   emecas_tiempos_<meta>.tsv    lo que tardó cada paso en la última corrida de <meta> que terminó bien\n#   emecas/<fecha>_<meta>/       [EMECAS-RESUMEN-D322] una carpeta por corrida (se guardan todas: decisión de Alonso):\n#       NN_<paso>.log            la salida completa de cada paso (también sale por la salida de siempre, sin cambios)\n#       resumen.md               al final, y también si un paso falla: meta, rama, commit, cambios sin commit, horas,\n#                                tabla de pasos (duración, resultado, diferencia con la última corrida buena), las líneas\n#                                de veredicto de cada paso y, si falló, las últimas líneas del paso que falló\n# El porcentaje y la hora de fin salen de esos tiempos MEDIDOS, no de contar pasos (lab-e2e dura más de una hora y\n# emecas-frescura segundos). La primera corrida de una meta no tiene tiempos: solo pasos hechos y tiempo transcurrido.\n#   emecas_paso.py inicio META                   empieza una corrida (vacía emecas_progreso.txt)\n"
],
[
"#   emecas_paso.py ver                           la barra (make emecas-progreso, desde otra terminal)\n# Coste: lineal en el número de pasos (una lectura de dos ficheros pequeños por paso).\nimport os\nimport subprocess\nimport sys\nimport time\n",
"#   emecas_paso.py ver                           la barra (make emecas-progreso, desde otra terminal)\n# Coste: lineal en el número de pasos (una lectura de dos ficheros pequeños por paso).\nimport os\nimport re\nimport subprocess\nimport sys\nimport time\n"
],
[
"PROGRESO = os.path.join(DIR, \"emecas_progreso.txt\")\nMETAS = (\"emecas\", \"emecas++\", \"emecas+++\")\nANCHO = 30\n\n\ndef tiempos_de(meta):\n",
"PROGRESO = os.path.join(DIR, \"emecas_progreso.txt\")\nMETAS = (\"emecas\", \"emecas++\", \"emecas+++\")\nANCHO = 30\nCOLA = 40           # líneas finales del paso que falló, en el resumen\nMAX_VEREDICTO = 60  # líneas de veredicto por paso, en el resumen (el resto, contado)\nVEREDICTO = re.compile(r\"(\\bPASA\\b|\\bFALLA\\b|RESULTADO|PASSED|FAILED|❌|NO PASA)\")\nANSI = re.compile(r\"\\x1b\\[[0-9;?]*[A-Za-z]\")\n\n\ndef tiempos_de(meta):\n"
],
[
"    return t, orden\n\n\ndef leer_progreso():\n    \"\"\"(meta, t0, pasos) con pasos = [[nombre, inicio, fin|None, rc|None], ...] en orden.\"\"\"\n    meta, t0, pasos = None, None, []\n    try:\n        with open(PROGRESO, encoding=\"utf-8\") as f:\n            for ln in f:\n                p = ln.split()\n                if len(p) >= 3 and p[0] == \"META\":\n                    meta, t0 = p[1], int(p[2])\n                elif len(p) >= 3 and p[0] == \"INICIO\":\n                    pasos.append([p[1], int(p[2]), None, None])\n",
"    return t, orden\n\n\ndef leer_progreso(extra=None):\n    \"\"\"(meta, t0, pasos) con pasos = [[nombre, inicio, fin|None, rc|None], ...] en orden. Si extra es un dict, recibe\n    las líneas CARPETA y GIT de la corrida.\"\"\"\n    meta, t0, pasos = None, None, []\n    try:\n        with open(PROGRESO, encoding=\"utf-8\") as f:\n            for ln in f:\n                p = ln.split()\n                if extra is not None and len(p) >= 2 and p[0] in (\"CARPETA\", \"GIT\"):\n                    extra[p[0]] = ln.rstrip(\"\\n\").split(\" \", 1)[1]\n                elif len(p) >= 3 and p[0] == \"META\":\n                    meta, t0 = p[1], int(p[2])\n                elif len(p) >= 3 and p[0] == \"INICIO\":\n                    pasos.append([p[1], int(p[2]), None, None])\n"
],
[
"    n = len(hechos) + (1 if curso else 0)\n    tot = (\"/%d\" % len(orden)) if orden else \"\"\n    lin = [\"[EMECAS-PROGRESO] %s desde las %s (%s)\" % (meta, hora(t0), dur(ahora - t0))]\n    if malo:\n        lin.append(\"  ❌ paso %s FALLÓ (rc=%d) tras %s: EMECAS parado\" % (malo[0], malo[3], dur(malo[2] - malo[1])))\n    elif curso:\n",
"    n = len(hechos) + (1 if curso else 0)\n    tot = (\"/%d\" % len(orden)) if orden else \"\"\n    lin = [\"[EMECAS-PROGRESO] %s desde las %s (%s)\" % (meta, hora(t0), dur(ahora - t0))]\n    c = carpeta()\n    if c:\n        lin.append(\"  logs y resumen: %s/\" % c)\n    if malo:\n        lin.append(\"  ❌ paso %s FALLÓ (rc=%d) tras %s: EMECAS parado\" % (malo[0], malo[3], dur(malo[2] - malo[1])))\n    elif curso:\n"
],
[
"        f.write(texto + \"\\n\")\n\n\ndef main(a):\n    if len(a) >= 2 and a[0] == \"inicio\" and a[1] in METAS:\n        os.makedirs(DIR, exist_ok=True)\n        with open(PROGRESO, \"w\", encoding=\"utf-8\") as f:\n            f.write(\"META %s %d\\n\" % (a[1], int(time.time())))\n        print(\"[EMECAS-PROGRESO] %s empieza a las %s; avance desde otra terminal: make emecas-progreso\" %\n              (a[1], hora(time.time())), flush=True)\n        return 0\n    if len(a) >= 5 and a[0] == \"paso\" and a[1] in METAS and a[3] == \"--\" and a[2].strip():\n        nombre, orden = a[2], a[4:]\n        anotar(\"INICIO %s %d\" % (nombre, int(time.time())))\n        print(estado(), flush=True)\n        try:\n            rc = subprocess.call(orden)\n        except OSError as e:\n            print(\"[EMECAS-PROGRESO] no se pudo lanzar %s: %s\" % (\" \".join(orden), e), flush=True)\n            rc = 127\n",
"        f.write(texto + \"\\n\")\n\n\ndef git_info():\n    \"\"\"rama, commit y nº de ficheros con cambios sin commit del repo en el directorio actual.\"\"\"\n    def g(*a):\n        try:\n            r = subprocess.run([\"git\"] + list(a), capture_output=True, text=True, timeout=20)\n            return r.stdout.strip() if r.returncode == 0 else None\n        except (OSError, subprocess.SubprocessError):\n            return None\n    rama, commit, estado_git = g(\"rev-parse\", \"--abbrev-ref\", \"HEAD\"), g(\"rev-parse\", \"--short=12\", \"HEAD\"), g(\"status\", \"--porcelain\")\n    if rama is None or commit is None:\n        return \"git no disponible (no es un repo o no hay git)\"\n    n = len([x for x in (estado_git or \"\").splitlines() if x.strip()])\n    return \"rama=%s commit=%s cambios_sin_commit=%d\" % (rama, commit, n)\n\n\ndef carpeta():\n    extra = {}\n    leer_progreso(extra)\n    return extra.get(\"CARPETA\")\n\n\ndef log_de(c, n, nombre):\n    return os.path.join(c, \"%02d_%s.log\" % (n, re.sub(r\"[^A-Za-z0-9_.+-]\", \"_\", nombre)))\n\n\ndef ejecutar(orden, ruta_log):\n    \"\"\"Ejecuta orden: su salida (stdout y stderr juntos, como el 2>&1 de siempre) va a la salida y a ruta_log.\"\"\"\n    with open(ruta_log, \"wb\") as lg:\n        p = subprocess.Popen(orden, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)\n        for linea in iter(p.stdout.readline, b\"\"):\n            sys.stdout.buffer.write(linea); sys.stdout.buffer.flush()\n            lg.write(linea)\n        p.stdout.close()\n        return p.wait()\n\n\ndef escribir_resumen(final):\n    \"\"\"resumen.md de la corrida en curso. final: 'PASA' o 'FALLA'. Una pasada por el log de cada paso.\"\"\"\n    extra = {}\n    meta, t0, pasos = leer_progreso(extra)\n    c = extra.get(\"CARPETA\")\n    if not meta or not c or not os.path.isdir(c):\n        return None\n    prev, _ = tiempos_de(meta)\n    ahora = int(time.time())\n    fin = max([p[2] for p in pasos if p[2] is not None] or [ahora])\n    L = [\"# EMECAS %s — %s\" % (meta, final), \"\",\n         \"- %s\" % extra.get(\"GIT\", \"git: sin dato\"),\n         \"- inicio %s, fin %s, duración %s\" % (time.strftime(\"%Y-%m-%d %H:%M:%S\", time.localtime(t0)),\n                                            time.strftime(\"%Y-%m-%d %H:%M:%S\", time.localtime(fin)), dur(fin - t0)),\n         \"- tiempos de referencia: %s\" % (\"última %s buena (emecas_tiempos_%s.tsv)\" % (meta, meta) if prev\n                                          else \"ninguna %s buena anterior\" % meta),\n         \"\", \"| # | paso | duración | resultado | frente a la última buena |\", \"|---|---|---|---|---|\"]\n    malo = None\n    for i, p in enumerate(pasos, 1):\n        if p[2] is None:\n            res, d = \"sin terminar\", \"-\"\n        else:\n            res, d = (\"✅\" if p[3] == 0 else \"❌ rc=%d\" % p[3]), dur(p[2] - p[1])\n            if p[3] != 0 and malo is None:\n                malo = (i, p)\n        ant = prev.get(p[0])\n        if ant is None or p[2] is None:\n            dif = \"-\"\n        else:\n            x = (p[2] - p[1]) - ant\n            dif = \"%s%s (antes %s)\" % (\"+\" if x >= 0 else \"-\", dur(abs(x)), dur(ant))\n        L.append(\"| %d | %s | %s | %s | %s |\" % (i, p[0], d, res, dif))\n    L += [\"\", \"## Veredictos de cada paso\", \"\"]\n    for i, p in enumerate(pasos, 1):\n        ruta = log_de(c, i, p[0])\n        lineas, n_ok, n_mal = [], 0, 0\n        try:\n            with open(ruta, \"rb\") as f:\n                for b in f:\n                    t = ANSI.sub(\"\", b.decode(\"utf-8\", \"replace\")).rstrip()\n                    if \"✅\" in t: n_ok += 1\n                    if \"❌\" in t or \"FALLA\" in t or \"FAILED\" in t: n_mal += 1\n                    if VEREDICTO.search(t): lineas.append(t)\n        except OSError:\n            continue\n        L.append(\"### %d %s (✅ %d, ❌/FALLA %d)\" % (i, p[0], n_ok, n_mal))\n        if lineas:\n            L.append(\"```\")\n            L += lineas[:MAX_VEREDICTO]\n            if len(lineas) > MAX_VEREDICTO:\n                L.append(\"… y %d líneas de veredicto más en %s\" % (len(lineas) - MAX_VEREDICTO, os.path.basename(ruta)))\n            L.append(\"```\")\n        L.append(\"\")\n    if malo:\n        i, p = malo\n        ruta = log_de(c, i, p[0])\n        try:\n            with open(ruta, \"rb\") as f:\n                cola = [ANSI.sub(\"\", b.decode(\"utf-8\", \"replace\")).rstrip() for b in f][-COLA:]\n        except OSError:\n            cola = [\"(sin log)\"]\n        L += [\"## Falló: paso %d %s (rc=%d), últimas %d líneas de %s\" % (i, p[0], p[3], len(cola), os.path.basename(ruta)),\n              \"\", \"```\"] + cola + [\"```\", \"\"]\n    ruta = os.path.join(c, \"resumen.md\")\n    with open(ruta + \".tmp\", \"w\", encoding=\"utf-8\") as f:\n        f.write(\"\\n\".join(L) + \"\\n\")\n    os.replace(ruta + \".tmp\", ruta)\n    return ruta\n\n\ndef main(a):\n    if len(a) >= 2 and a[0] == \"inicio\" and a[1] in METAS:\n        t0 = int(time.time())\n        c = os.path.join(DIR, \"emecas\", \"%s_%s\" % (time.strftime(\"%Y%m%dT%H%M%S\", time.localtime(t0)), a[1]))\n        os.makedirs(c, exist_ok=True)\n        with open(PROGRESO, \"w\", encoding=\"utf-8\") as f:\n            f.write(\"META %s %d\\nCARPETA %s\\nGIT %s\\n\" % (a[1], t0, c, git_info()))\n        print(\"[EMECAS-PROGRESO] %s empieza a las %s; avance desde otra terminal: make emecas-progreso; logs y resumen \"\n              \"en %s/\" % (a[1], hora(t0), c), flush=True)\n        return 0\n    if len(a) >= 5 and a[0] == \"paso\" and a[1] in METAS and a[3] == \"--\" and a[2].strip():\n        nombre, orden = a[2], a[4:]\n        _, _, pasos = leer_progreso()\n        c = carpeta()\n        anotar(\"INICIO %s %d\" % (nombre, int(time.time())))\n        print(estado(), flush=True)\n        try:\n            if c and os.path.isdir(c):\n                rc = ejecutar(orden, log_de(c, len(pasos) + 1, nombre))\n            else:  # corrida empezada antes de [EMECAS-RESUMEN-D322] o sin carpeta: como antes, sin log propio\n                rc = subprocess.call(orden)\n        except OSError as e:\n            print(\"[EMECAS-PROGRESO] no se pudo lanzar %s: %s\" % (\" \".join(orden), e), flush=True)\n            rc = 127\n"
],
[
"        _, _, pasos = leer_progreso()\n        print(\"[EMECAS-PROGRESO] %s %s en %s\" % (\"✅\" if rc == 0 else \"❌\", nombre,\n              dur(pasos[-1][2] - pasos[-1][1]) if pasos else \"?\"), flush=True)\n        return rc\n    if len(a) >= 3 and a[0] == \"fin\" and a[1] in METAS and a[2] in METAS:\n        if a[1] != a[2]:\n",
"        _, _, pasos = leer_progreso()\n        print(\"[EMECAS-PROGRESO] %s %s en %s\" % (\"✅\" if rc == 0 else \"❌\", nombre,\n              dur(pasos[-1][2] - pasos[-1][1]) if pasos else \"?\"), flush=True)\n        if rc != 0:\n            r = escribir_resumen(\"FALLA\")\n            if r:\n                print(\"[EMECAS-RESUMEN] %s\" % r, flush=True)\n        return rc\n    if len(a) >= 3 and a[0] == \"fin\" and a[1] in METAS and a[2] in METAS:\n        if a[1] != a[2]:\n"
],
[
"                    (meta, time.strftime(\"%Y-%m-%d %H:%M\", time.localtime(t0))))\n            for p in pasos:\n                f.write(\"%s\\t%d\\n\" % (p[0], p[2] - p[1]))\n        os.replace(ruta + \".tmp\", ruta)\n        print(\"[EMECAS-PROGRESO] %s terminada en %s: tiempos guardados en %s (darán el porcentaje la próxima vez)\" %\n              (meta, dur(int(time.time()) - t0), ruta), flush=True)\n        return 0\n    if a == [\"ver\"]:\n        print(estado())\n",
"                    (meta, time.strftime(\"%Y-%m-%d %H:%M\", time.localtime(t0))))\n            for p in pasos:\n                f.write(\"%s\\t%d\\n\" % (p[0], p[2] - p[1]))\n        r = escribir_resumen(\"PASA\")   # antes de guardar los tiempos: compara con la corrida buena ANTERIOR\n        os.replace(ruta + \".tmp\", ruta)\n        print(\"[EMECAS-PROGRESO] %s terminada en %s: tiempos guardados en %s (darán el porcentaje la próxima vez)\" %\n              (meta, dur(int(time.time()) - t0), ruta), flush=True)\n        if r:\n            print(\"[EMECAS-RESUMEN] %s\" % r, flush=True)\n        return 0\n    if a == [\"ver\"]:\n        print(estado())\n"
]
]
},
{
"ruta": "scripts/emecas/test_emecas_paso.py",
"sha_antes": "e7b0a79463b1941338232aca06dcb7ac0f4ae9b19155b2d298c5bda86abc89a7",
"sha_despues": "92a6cb37214ffde670ac2b7538ba53aae7741b1a7e8f39fa6653538f6275ba06",
"trozos": [
[
"        self.env = dict(os.environ, EMECAS_PROGRESO_DIR=self.d)\n\n    def h(self, *a):\n        r = subprocess.run([sys.executable, H] + list(a), env=self.env, capture_output=True, text=True)\n        return r.returncode, r.stdout + r.stderr\n\n    def modulo(self):\n        os.environ[\"EMECAS_PROGRESO_DIR\"] = self.d\n",
"        self.env = dict(os.environ, EMECAS_PROGRESO_DIR=self.d)\n\n    def h(self, *a):\n        r = subprocess.run([sys.executable, H] + list(a), env=self.env, capture_output=True, text=True, cwd=self.d)\n        return r.returncode, r.stdout + r.stderr\n\n    def corrida(self):\n        c = [x for x in os.listdir(os.path.join(self.d, \"emecas\"))]\n        self.assertEqual(len(c), 1)\n        return os.path.join(self.d, \"emecas\", c[0])\n\n    def modulo(self):\n        os.environ[\"EMECAS_PROGRESO_DIR\"] = self.d\n"
],
[
"        self.assertIn(\" 40 %\", t)\n        self.assertIn(\"quedan ~10m00s\", t)\n\n    def test_uso(self):\n        self.assertEqual(self.h(\"paso\", \"emecas\", \"x\", \"true\")[0], 2)\n        self.assertEqual(self.h(\"inicio\", \"otra\")[0], 2)\n",
"        self.assertIn(\" 40 %\", t)\n        self.assertIn(\"quedan ~10m00s\", t)\n\n    def test_carpeta_y_log_por_paso_con_la_salida_de_siempre(self):\n        self.h(\"inicio\", \"emecas\")\n        rc, out = self.h(\"paso\", \"emecas\", \"test-all\", \"--\", \"sh\", \"-c\", \"echo por stdout; echo por stderr >&2\")\n        self.assertIn(\"por stdout\", out)\n        self.assertIn(\"por stderr\", out)\n        c = self.corrida()\n        self.assertTrue(c.endswith(\"_emecas\"))\n        with open(os.path.join(c, \"01_test-all.log\"), encoding=\"utf-8\") as f:\n            t = f.read()\n        self.assertIn(\"por stdout\", t)\n        self.assertIn(\"por stderr\", t)\n        self.h(\"paso\", \"emecas\", \"dos\", \"--\", \"true\")\n        self.assertTrue(os.path.exists(os.path.join(c, \"02_dos.log\")))\n\n    def test_resumen_de_una_corrida_buena_con_veredictos_y_diferencias(self):\n        with open(os.path.join(self.d, \"emecas_tiempos_emecas.tsv\"), \"w\", encoding=\"utf-8\") as f:\n            f.write(\"prot\\t100\\n\")\n        self.h(\"inicio\", \"emecas\")\n        self.h(\"paso\", \"emecas\", \"prot\", \"--\", \"sh\", \"-c\",\n               \"echo ruido; printf '\\\\033[32m[VEREDICTO] PASA  P1 manifiesto\\\\033[0m\\\\n'; echo '  ✅ C1 bien'; \"\n               \"echo '[VEREDICTO] RESULTADO PASA (protegidos)'\")\n        rc, out = self.h(\"fin\", \"emecas\", \"emecas\")\n        self.assertIn(\"[EMECAS-RESUMEN]\", out)\n        with open(os.path.join(self.corrida(), \"resumen.md\"), encoding=\"utf-8\") as f:\n            r = f.read()\n        self.assertIn(\"# EMECAS emecas — PASA\", r)\n        self.assertIn(\"git no disponible\", r)                     # el directorio temporal no es un repo\n        self.assertIn(\"| 1 | prot |\", r)\n        self.assertIn(\"(antes 1m40s)\", r)                         # frente a la corrida buena anterior, no a esta\n        self.assertIn(\"[VEREDICTO] PASA  P1 manifiesto\", r)       # sin los códigos de color\n        self.assertNotIn(\"\\x1b\", r)\n        self.assertIn(\"RESULTADO PASA (protegidos)\", r)\n        self.assertNotIn(\"ruido\", r)\n        self.assertIn(\"(✅ 1, ❌/FALLA 0)\", r)\n\n    def test_resumen_al_fallar_con_la_cola_del_paso(self):\n        self.h(\"inicio\", \"emecas+++\")\n        self.h(\"paso\", \"emecas+++\", \"bien\", \"--\", \"true\")\n        rc, out = self.h(\"paso\", \"emecas+++\", \"lab-e2e\", \"--\", \"sh\", \"-c\",\n                         \"for i in $(seq 1 60); do echo linea $i; done; echo '[VEREDICTO] FALLA P2 episodio'; exit 2\")\n        self.assertEqual(rc, 2)\n        self.assertIn(\"[EMECAS-RESUMEN]\", out)\n        with open(os.path.join(self.corrida(), \"resumen.md\"), encoding=\"utf-8\") as f:\n            r = f.read()\n        self.assertIn(\"# EMECAS emecas+++ — FALLA\", r)\n        self.assertIn(\"| 2 | lab-e2e |\", r)\n        self.assertIn(\"❌ rc=2\", r)\n        self.assertIn(\"## Falló: paso 2 lab-e2e (rc=2)\", r)\n        self.assertIn(\"linea 60\", r)\n        self.assertNotIn(\"linea 20\\n\", r)                         # solo las últimas 40 líneas\n        self.assertIn(\"FALLA P2 episodio\", r)\n\n    def test_uso(self):\n        self.assertEqual(self.h(\"paso\", \"emecas\", \"x\", \"true\")[0], 2)\n        self.assertEqual(self.h(\"inicio\", \"otra\")[0], 2)\n"
]
]
}
],
"nuevos": []
}''')
def sha(t): return hashlib.sha256(t.encode()).hexdigest()
def leer(p):
    try: return open(p, encoding="utf-8").read()
    except FileNotFoundError: return None
def plan():
    acciones, errores = [], []
    for c in D["cambios"]:
        t = leer(c["ruta"])
        if t is None: errores.append(f"{c['ruta']}: no existe"); continue
        h = sha(t)
        if h == c["sha_despues"]: print(f"  ya parcheado  {c['ruta']}"); continue
        if h != c["sha_antes"]:
            errores.append(f"{c['ruta']}: sha256 {h[:16]} no es el de partida ({c['sha_antes'][:16]}) ni el parcheado"); continue
        for o, n in c["trozos"]: t = t.replace(o, n, 1)
        assert sha(t) == c["sha_despues"]
        acciones.append((c["ruta"], t, None)); print(f"  se parchea    {c['ruta']} ({len(c['trozos'])} trozos)")
    for n in D["nuevos"]:
        t = leer(n["ruta"])
        if t == n["contenido"]: print(f"  ya está       {n['ruta']}"); continue
        if t is not None: errores.append(f"{n['ruta']}: existe con otro contenido"); continue
        acciones.append((n["ruta"], n["contenido"], n["modo"])); print(f"  se crea       {n['ruta']}")
    return acciones, errores
def escribir(ruta, texto, modo):
    d = os.path.dirname(ruta) or "."
    os.makedirs(d, exist_ok=True)
    m = modo if modo is not None else (os.stat(ruta).st_mode & 0o777)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".d322_")
    with os.fdopen(fd, "w", encoding="utf-8") as f: f.write(texto)
    os.chmod(tmp, m); os.replace(tmp, ruta)
if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: python3 scripts/etcd_ha/d322_emecas_resumen_b.py --check | --apply"); sys.exit(2)
    if not os.path.isfile("Vagrantfile") or not os.path.isdir("scripts/etcd_ha"):
        print("[D322] FALLA: hay que lanzarlo desde la raíz del repo"); sys.exit(2)
    acciones, errores = plan()
    if errores:
        print("[D322] FALLA, no se toca nada:"); [print("  - " + e) for e in errores]; sys.exit(1)
    if sys.argv[1] == "--check":
        print(f"[D322] check OK: {len(acciones)} fichero(s) por escribir"); sys.exit(0)
    for r, t, m in acciones: escribir(r, t, m)
    print(f"[D322] apply OK: {len(acciones)} fichero(s) escrito(s)")
