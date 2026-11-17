#!/usr/bin/env python3
# [FALCO-SILENCIO-D327] DAY327, F2g de DEBT-FALCO-RUIDO-ADMIN-001 (PR2b de DEBT-ETCD-HA-TLS-RAFT-001): las dos fuentes de
# CRITICAL que el test de silencio (F2f, 9a91811f2) encontró en la historia del defender y que corren en EMECAS antes
# de falco-silencio.
# - Makefile: test-invariant-seed compara las cuatro semillas con sudo sha256sum (antes od desde sudo bash) y exige
#   las 4 leídas.
# - provisioning/falco/argus_lab.yaml: macros argus_lab_invariante_semilla (sha256sum hijo de sudo sobre un seed.bin) y
#   argus_lab_inyector_sintetico (cada inyector de test-e2e-synthetic, hijo de sudo, su clave y su semilla) = Notice.
# Va sobre el Makefile de F2f (sha256 5b2c51a7...). Después: vagrant provision <vm> --provision-with falco.
# Uso (raíz del repo): python3 -I scripts/etcd_ha/d327_f2g_semillas_inyectores.py --check | --apply
# Todo o nada: comprueba y calcula todos los ficheros antes de escribir ninguno. Idempotente (YA-APLICADO).
import hashlib, os, sys, tempfile

FICHEROS = [
    {
        'ruta': 'Makefile', 'antes': '5b2c51a73705369720c67555dc5c6058692e61ea3cb56cef2b1e03e62c2200b9', 'despues': '8ee762a5304988596a297d62fd93168e4f1f7642a3e50ab9ed6d69ec341b2661', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('\t@vagrant ssh -c \'sudo bash -c " \\\n\t  hashes=\\"\\" ; \\\n\t  for c in etcd-server ml-detector sniffer firewall-acl-agent; do \\\n\t    h=\\$$(od -A n -t x1 /etc/ml-defender/\\$$c/seed.bin | tr -d \\" \\\\n\\") ; \\\n\t    hashes=\\"\\$$hashes \\$$h\\" ; \\\n\t  done ; \\\n\t  unique=\\$$(echo \\$$hashes | tr \\" \\" \\"\\\\n\\" | sort -u | grep -v \\"^$$\\" | wc -l) ; \\\n\t  echo \\"Hashes únicos: \\$$unique\\" ; \\\n\t  [ \\"\\$$unique\\" -eq 1 ] && echo \\"✅ TEST-INVARIANT-SEED PASSED\\" || { echo \\"❌ TEST-INVARIANT-SEED FAILED\\"; exit 1; } \\\n\t"\' || (echo "❌ INVARIANTE-SEED-001 violado: seeds divergentes" && exit 1)\n',
             '\t@# [FALCO-SILENCIO-D327] sha256sum hijo de sudo (traza Notice de Falco: argus_lab_invariante_semilla), no od desde\n\t@# sudo bash: od vuelca la semilla por una tubería y daba 4 CRITICAL en cada EMECAS (medido DAY327 en la historia\n\t@# del 11-nov). Y se exigen las 4 semillas leídas: antes, una semilla ilegible no contaba y podía dar verde.\n\t@vagrant ssh -c \'s=$$(for c in etcd-server ml-detector sniffer firewall-acl-agent; do sudo sha256sum /etc/ml-defender/$$c/seed.bin; done | cut -d" " -f1); \\\n\t  n=$$(echo "$$s" | grep -c .); unique=$$(echo "$$s" | sort -u | grep -c .); \\\n\t  echo "Semillas leídas: $$n de 4; huellas únicas: $$unique"; \\\n\t  [ "$$n" -eq 4 ] && [ "$$unique" -eq 1 ] && echo "✅ TEST-INVARIANT-SEED PASSED" || { echo "❌ TEST-INVARIANT-SEED FAILED"; exit 1; }\' \\\n\t  || (echo "❌ INVARIANTE-SEED-001 violado: seeds divergentes o ilegibles" && exit 1)\n'),
        ],
    },
    {
        'ruta': 'provisioning/falco/argus_lab.yaml', 'antes': 'e93250e0fa414c1a0e94724b422ffb758619e5e5680476460a6ba465d939727b', 'despues': 'b4559ad51419df19959b03858117853553848978d2850c5b8241b4a7d513dfdf', 'modo': None,
        'nuevo': None,
        'trozos': [
            ('#             clave_bronce.py con sudo la del conversor (mitre/ctu/custom-start, lab-e2e-reinicio-etcd).\n',
             '#             clave_bronce.py con sudo la del conversor (mitre/ctu/custom-start, lab-e2e-reinicio-etcd);\n#             sha256sum con sudo las cuatro semillas (test-invariant-seed) y los inyectores sintéticos con sudo la\n#             clave y la semilla del componente al que sustituyen (test-e2e-synthetic); medido DAY327.\n'),
            ('# Herramientas de administración medidas (trazas de bajo nivel, no alertas)\n',
             '# [FALCO-SILENCIO-D327] test-invariant-seed (en test-all) compara las cuatro semillas con sudo sha256sum: solo imprime\n# la huella, basta padre sudo (como en argus_lab_despliegue_etcd_server). Antes era od desde sudo bash, que vuelca el\n# contenido: 4 CRITICAL por EMECAS (medido DAY327 en la historia del defender, 11-nov 18:53:08Z).\n- macro: argus_lab_invariante_semilla\n  condition: >\n    proc.exepath = /usr/bin/sha256sum and proc.pexepath = /usr/bin/sudo and\n    fd.name glob "/etc/ml-defender/*/seed.bin"\n\n# [FALCO-SILENCIO-D327] los inyectores sintéticos de test-e2e-synthetic (sudo env LD_LIBRARY_PATH=... <inyector>; env\n# se sustituye por el inyector, que queda hijo de sudo) se presentan como el componente al que sustituyen (decisión de\n# Alonso DAY316): leen SU clave TLS y SU semilla, nada más. Medido DAY327 en la historia del defender (11-nov): 32\n# CRITICAL en un EMECAS+++. Por ruta, no por nombre (synthetic_sniffer_injector se corta a 15); /vagrant solo existe\n# en el lab.\n- macro: argus_lab_inyector_sintetico\n  condition: >\n    proc.pexepath = /usr/bin/sudo and\n    ((proc.exepath glob "/vagrant/tools/build-*/synthetic_sniffer_injector" and\n      fd.name in (/etc/argus-pki/sniffer.key, /etc/ml-defender/sniffer/seed.bin)) or\n     (proc.exepath glob "/vagrant/tools/build-*/synthetic_ml_output_injector" and\n      fd.name in (/etc/argus-pki/ml-detector.key, /etc/ml-defender/ml-detector/seed.bin)))\n\n# Herramientas de administración medidas (trazas de bajo nivel, no alertas)\n'),
            ('    argus_lab_clave_bronce or\n    (proc.exepath = /usr/bin/openssl and',
             '    argus_lab_clave_bronce or\n    argus_lab_invariante_semilla or\n    argus_lab_inyector_sintetico or\n    (proc.exepath = /usr/bin/openssl and'),
            ('  desc: Traza - una herramienta de administración lee una clave (pipeline-status, provision.sh verify, argus-infra)\n',
             '  desc: Traza - una herramienta de administración lee una clave (pipeline-status, provision.sh verify, argus-infra, tests del lab)\n'),
        ],
    },
]


def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: --check | --apply"); return 2
    aplicar = sys.argv[1] == "--apply"
    if not os.path.isdir(".git"):
        print("[ERROR] ejecutar desde la raíz del repo (no veo .git)"); return 2
    plan, ya, errores = [], 0, 0
    for f in FICHEROS:
        r = f["ruta"]
        if os.path.exists(r):
            actual = open(r, "rb").read()
            h = sha(actual)
            if h == f["despues"]:
                print(f"[YA-APLICADO] {r} {h[:16]}"); ya += 1; continue
            if f["antes"] == "nuevo":
                print(f"[ERROR] {r} existe con otro contenido ({h[:16]}); se esperaba que no existiera"); errores += 1; continue
            if h != f["antes"]:
                print(f"[ERROR] {r} sha256 {h[:16]}, se esperaba {f['antes'][:16]} (antes) o {f['despues'][:16]} (después)"); errores += 1; continue
            t = actual.decode("utf-8")
            for i, (v, n) in enumerate(f["trozos"]):
                if t.count(v) != 1:
                    print(f"[ERROR] {r}: trozo {i + 1} aparece {t.count(v)} veces"); errores += 1; break
                t = t.replace(v, n)
            nb = t.encode("utf-8")
            modo = os.stat(r).st_mode & 0o777
        else:
            if f["antes"] != "nuevo":
                print(f"[ERROR] {r} no existe"); errores += 1; continue
            nb = f["nuevo"].encode("utf-8"); modo = int(f["modo"], 8)
        if sha(nb) != f["despues"]:
            print(f"[ERROR] {r}: el resultado no da el sha256 esperado"); errores += 1; continue
        plan.append((r, nb, modo, f))
        print(f"[APLICABLE] {r} {f['antes'][:16]} -> {f['despues'][:16]} ({len(f['trozos']) if f['nuevo'] is None else 'fichero nuevo'}{' bloques' if f['nuevo'] is None else ''})")
    if errores:
        print(f"[ERROR] {errores} problemas: no se escribe nada"); return 1
    if not plan:
        print(f"[CHECK] todo ya aplicado ({ya} ficheros)"); return 0
    if not aplicar:
        print(f"[CHECK] todo aplicable ({len(plan)} ficheros, {ya} ya aplicados); nada escrito"); return 0
    for r, nb, modo, f in plan:
        d = os.path.dirname(r) or "."
        os.makedirs(d, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".parche_")
        with os.fdopen(fd, "wb") as o: o.write(nb)
        os.chmod(tmp, modo)
        os.replace(tmp, r)
        print(f"[APLICADO] {r} sha256={f['despues']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
