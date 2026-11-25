#!/usr/bin/env python3
# d337_ml_entreno.py — [ML-ENTRENO-D337] el entorno de entrenamiento ML sale de la provisión base del defender
# (Vagrantfile) a un venv opcional (make ml-entreno), y test-ml-entreno entra en el EMECAS tras
# test-apt-oficial-reintento. Se ejecuta desde la raíz del repo, en la rama de PARQUET-SIN-NUMPY-D337 (Makefile de
# llegada de aquel parcheador); el lock, el instalador y el test tienen que estar ya en su sitio con su sha256. Comprueba
# el sha256 de partida de cada fichero, cada ancla las veces exactas y no escribe nada si algo falla; al final, el
# sha256 de llegada. ml-training/requirements-ddos-pinned.txt lo borra git rm, no esto.
import hashlib, sys

def sha(b): return hashlib.sha256(b).hexdigest()

NUEVOS = {
    "provisioning/ml-entreno/requirements.txt": "92916801f420545010efcc23d53a3be25e0ee47e412fd3279ca072658056ad7c",
    "scripts/terceros/ml_entreno_instalar.sh": "f16365a7d468175b07bca38805155a5bbd49312e05a858157adb2205753b2acc",
    "scripts/terceros/test_ml_entreno.sh": "0a41aa7d0f7cc716ff9c8fb0285532aee28c4d7ff100b3887e1e04d0797cf784",
}

VF_VIEJO = """      # Dependencias Python PINNEADAS del crank ML in-VM (RF DDoS).
      # DEUDA-DDOS-REPRO-PIN: versiones exactas o abortar. SIN fallback apt: los
      # python3-pandas/python3-sklearn del repo producen otro entorno → otro sha.
      pip3 install -r /vagrant/ml-training/requirements-ddos-pinned.txt \\
      --break-system-packages --timeout=300 || {
      echo "❌ deps ML pinneadas fallaron — NO se cae a apt (reproducibilidad)"; exit 1;
      }
"""
VF_NUEVO = """      # [ML-ENTRENO-D337] DEBT-LAB-TERCEROS-DESCARGA-SIN-VERIFICAR-001, lente pip B: el entorno de entrenamiento ML
      # (numpy, scikit-learn, pandas, scipy y su cierre) ya no se instala en la base. Medido DAY337: nada del pipeline
      # ni del EMECAS lo usaba (validate_roundtrip.py, el único, ya no usa numpy). Para entrenar: make ml-entreno, un
      # venv aparte (/opt/argus/ml-entreno) con el cierre entero y sus hashes (provisioning/ml-entreno/requirements.txt).
"""
MK_VIEJO_PASO = """\t@$(EMECAS_PASO) test-apt-oficial-reintento -- $(MAKE) test-apt-oficial-reintento
"""
MK_NUEVO_PASO = """\t@$(EMECAS_PASO) test-apt-oficial-reintento -- $(MAKE) test-apt-oficial-reintento
\t@$(EMECAS_PASO) test-ml-entreno -- $(MAKE) test-ml-entreno
"""
MK_VIEJO_TARGET = """.PHONY: test-apt-oficial-reintento
test-apt-oficial-reintento:
\t@bash scripts/vigilancia/test_apt_oficial_reintento.sh
"""
MK_NUEVO_TARGET = """.PHONY: test-apt-oficial-reintento
test-apt-oficial-reintento:
\t@bash scripts/vigilancia/test_apt_oficial_reintento.sh

# [ML-ENTRENO-D337] ml-entreno (opcional, fuera del EMECAS): el entorno de entrenamiento de las cabezas ML en el
# defender, en el venv /opt/argus/ml-entreno, desde provisioning/ml-entreno/requirements.txt (el cierre entero, con
# --require-hashes --no-deps); si ya está, no baja nada. Uso:
#   vagrant ssh defender -c "/opt/argus/ml-entreno/bin/python3 /vagrant/ml-training/scripts/ddos_detection/<script>"
# test-ml-entreno (Mac, sin VMs ni red): el lock, la comparación con pip freeze, que el Vagrantfile ya no instala el
# entorno ML y que el fichero de antes no existe; también contra funciones que lo aceptan todo.
.PHONY: ml-entreno test-ml-entreno
ml-entreno:
\t@vagrant ssh defender -c "sudo bash /vagrant/scripts/terceros/ml_entreno_instalar.sh"

test-ml-entreno:
\t@bash scripts/terceros/test_ml_entreno.sh
"""

CAMBIOS = {
    "Vagrantfile": (
        "4507d0c842acfa248e30066c7608a897d2b66e056e01b48258bcba879edbd82f",
        [(VF_VIEJO, VF_NUEVO, 1)]),
    "Makefile": (
        "1701dc50ca6cc7d9d0347a0b02d9476d9e72407939443bacbcadebbd47df2469",
        [(MK_VIEJO_PASO, MK_NUEVO_PASO, 1), (MK_VIEJO_TARGET, MK_NUEVO_TARGET, 1)]),
}

errores = []
for f, esperado in NUEVOS.items():
    try:
        s = sha(open(f, "rb").read())
    except OSError as e:
        errores.append(f"{f}: {e}"); continue
    if s != esperado:
        errores.append(f"{f}: sha256 {s}, se esperaba {esperado}")

nuevo = {}
for f, (esperado, anclas) in CAMBIOS.items():
    b = open(f, "rb").read()
    if sha(b) != esperado:
        errores.append(f"{f}: sha256 de partida {sha(b)}, se esperaba {esperado}"); continue
    t = b.decode("utf-8")
    for viejo, nuevo_txt, veces in anclas:
        n = t.count(viejo)
        if n != veces:
            errores.append(f"{f}: ancla encontrada {n} veces, se esperaban {veces}: {viejo.splitlines()[0]!r}")
            continue
        t = t.replace(viejo, nuevo_txt)
    nuevo[f] = t.encode("utf-8")

if errores:
    print("❌ no se escribe nada:")
    for e in errores: print("   " + e)
    sys.exit(1)
for f, b in nuevo.items():
    open(f, "wb").write(b)
    print(f"✅ {f}  sha256 de llegada {sha(b)}")
