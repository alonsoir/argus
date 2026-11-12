#!/usr/bin/env python3
# d323_emecas_progreso.py — (DAY323) [EMECAS-PROGRESO-D323]: con un paso fallido, la cabecera de make emecas-progreso
# para su reloj en el fallo («desde las 18:09 hasta las 18:47 (38m)») en vez de seguir contando hasta ahora. Test nuevo
# en scripts/emecas/test_emecas_paso.py. Aplicar con EMECAS PARADO (cada paso de EMECAS ejecuta emecas_paso.py).
# Uso:  python3 d323_emecas_progreso.py --check <raiz_repo>
#       python3 d323_emecas_progreso.py --apply <raiz_repo>
# Todo o nada; idempotente; solo escribe si CADA fichero está en el estado previo exacto y el resultado da su sha256 final.
import hashlib, os, sys

FICHEROS = {'scripts/emecas/emecas_paso.py': ('36ed75f865163f89f61326241b730aa54edd41a1c53c7c40e97022a17e0cb3e5', 'b24126bc1acdc7e807be690386d70c04abd74cb60666f69019b4f154752b50f4', [('    lin = ["[EMECAS-PROGRESO] %s desde las %s (%s)" % (meta, hora(t0), dur(ahora - t0))]\n', '    # [EMECAS-PROGRESO-D323] con un paso fallido el reloj de la cabecera se para en el fallo: antes seguía contando hasta\n    # ahora («desde las 18:09 (4h09m)» horas después de parar, medido DAY322)\n    if malo:\n        lin = ["[EMECAS-PROGRESO] %s desde las %s hasta las %s (%s)" % (meta, hora(t0), hora(malo[2]), dur(malo[2] - t0))]\n    else:\n        lin = ["[EMECAS-PROGRESO] %s desde las %s (%s)" % (meta, hora(t0), dur(ahora - t0))]\n', 1)]), 'scripts/emecas/test_emecas_paso.py': ('92a6cb37214ffde670ac2b7538ba53aae7741b1a7e8f39fa6653538f6275ba06', 'cbce8fb49443f53c1d2ec12134e44a79e945d288a99683a4e14114e65870512e', [('    def test_carpeta_y_log_por_paso_con_la_salida_de_siempre(self):\n', '    def test_con_un_paso_fallido_la_cabecera_se_para_en_el_fallo(self):\n        # [EMECAS-PROGRESO-D323] cuatro horas después de parar, la cabecera sigue diciendo lo que duró hasta el fallo\n        with open(os.path.join(self.d, "emecas_progreso.txt"), "w", encoding="utf-8") as f:\n            f.write("META emecas 1000\\nINICIO uno 1000\\nFIN uno 1100 0\\nINICIO dos 1100\\nFIN dos 1400 2\\n")\n        m = self.modulo()\n        t = m.estado(ahora=1400 + 4 * 3600)\n        cab = t.splitlines()[0]\n        self.assertIn("hasta las %s (6m40s)" % m.hora(1400), cab)\n        self.assertNotIn("4h", cab)\n        self.assertIn("paso dos FALLÓ (rc=2) tras 5m00s", t)\n        # sin fallo, la cabecera cuenta hasta ahora, como antes\n        with open(os.path.join(self.d, "emecas_progreso.txt"), "w", encoding="utf-8") as f:\n            f.write("META emecas 1000\\nINICIO uno 1000\\n")\n        self.assertIn("(4m10s)", m.estado(ahora=1250).splitlines()[0])\n\n    def test_carpeta_y_log_por_paso_con_la_salida_de_siempre(self):\n', 1)])}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ('--check', '--apply'):
        sys.exit('uso: %s --check|--apply <raiz_repo>' % sys.argv[0])
    modo, raiz = sys.argv[1], sys.argv[2]
    p = lambda r: os.path.join(raiz, r)
    nuevos, ya = {}, []
    for ruta, (previo, final, cambios) in FICHEROS.items():
        if not os.path.isfile(p(ruta)):
            print('FALLA: no existe %s; no se toca nada.' % ruta); return 1
        b = open(p(ruta), 'rb').read()
        if sha(b) == final:
            ya.append(ruta); continue
        if sha(b) != previo:
            print('FALLA: %s no está en el estado esperado (sha256 %s); no se toca nada.' % (ruta, sha(b)[:16])); return 1
        t = b.decode('utf-8')
        for i, (v, n, k) in enumerate(cambios, 1):
            if t.count(v) != k:
                print('FALLA: %s, cambio %d: %d apariciones (se exigen %d); no se toca nada.' % (ruta, i, t.count(v), k)); return 1
            t = t.replace(v, n)
        if sha(t.encode('utf-8')) != final:
            print('FALLA: %s: el resultado no da el sha256 final; no se toca nada.' % ruta); return 1
        nuevos[ruta] = t.encode('utf-8')
    if not nuevos:
        print('YA APLICADO: no se toca nada.'); return 0
    if ya:
        print('FALLA: aplicado a medias (ya: %s); no se toca nada.' % ', '.join(ya)); return 1
    if modo == '--check':
        print('APLICABLE: %s.' % ', '.join('%s (%d cambios)' % (r, len(FICHEROS[r][2])) for r in nuevos)); return 0
    for ruta, nuevo in nuevos.items():
        tmp = p(ruta) + '.d323tmp'
        with open(tmp, 'wb') as o: o.write(nuevo)
        os.chmod(tmp, os.stat(p(ruta)).st_mode & 0o7777); os.replace(tmp, p(ruta))
        print('  escrito  %s (sha256 %s)' % (ruta, FICHEROS[ruta][1][:16]))
    print('APLICADO.'); return 0

if __name__ == '__main__':
    sys.exit(main())
