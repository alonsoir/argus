# aRGus NDR — DAY 147 — Prompt de continuidad

## Estado del repositorio

- **Tag activo:** `v0.7.1-day146` | **Branch:** `main`
- **Paper:** arXiv:2604.04952 · Draft v20 (local) / v19 (arXiv)
- **FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026
- **Keypair activo (post-destroy DAY 133):** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`

---

## Resumen DAY 146

**EMECAS:** verde. **65/65 tests PASSED.**

**Deudas cerradas:**
- `DEBT-IRP-TMPFILES-001` ✅ — `/etc/tmpfiles.d/argus.conf` instalado en `provision.sh`
- `DEBT-IRP-IPSET-TMP-001` ✅ — `ipset_wrapper.cpp`: `/tmp` → `/run/argus/irp/`
- `DEBT-BOOTSTRAP-SNIFFER-VERIFY-001` ✅ — `sleep 2→4`, verificación real sniffer antes del banner
- `DEBT-EMECAS-VERIFICATION-001` ✅ — párrafo blockquote en `README.md`

**Experimento comparativo Suricata vs aRGus NDR:**
- Suricata 6.0.10 + 50,010 reglas ET Open (Mayo 2026) → **0 alertas** sobre CTU-13 Neris 2011
- aRGus NDR → **F1=0.9985, Recall=1.0000** sobre el mismo tráfico
- Condiciones idénticas: VM debian/bookworm64, 8192 MB, 6 vCPU, VirtIO, misma topología
- Interpretación: las reglas ET Open 2026 no cubren Neris 2011 — firmas retiradas por obsolescencia. No es fallo de Suricata: los paradigmas son distintos.
- Commits: `c4cdfd5a` · `f9b6c6a3` · `df19f1f8` · `19295a7e` · `ff83b402` · `8e503815` · `e1efbfbc`

**Paper v20 generado** (local): `docs/argus_ndr_v20.tex`
- Nueva §8.13: "Direct Experimental Comparison: aRGus NDR vs Suricata 6.0.10 on CTU-13 Neris"
- Tabla `tab:suricata_comparison`: TP/FP/FN/F1/Recall
- Tabla `tab:suricata_throughput`: Mbps/Alerts/exit por velocidad
- `tab:comparison` actualizada con F1=0.000 empírico + nota `$^{\S}$`
- Conclusión: párrafo sobre paradigmas complementarios
- §13 Reproducibilidad: `make experiment-suricata-run`

**Consejo de Sabios — consenso DAY 146:**
1. "Suricata funciona correctamente" — no atacarlo en el paper
2. Buscar ruleset ET Open 2011 para separar "firma retirada" de "firma nunca existió"
3. §8.13 nueva sección, no ampliar §8.7
4. Declarar asimetrías metodológicas: aRGus entrenado con sintéticos informados por CTU-13; Suricata evaluado con ruleset contemporáneo sobre tráfico histórico
5. Narrativa: sistemas complementarios, no competidores

---

## Tareas DAY 147

### P0 — Paper v20

1. **Revisar `docs/argus_ndr_v20.tex`** — el archivo tiene marcadores `% [Unchanged from v19]` en secciones 3-7, 9-11. Necesita completarse con el contenido del v19 para compilar. El diff real del v19→v20 está en:
    - Abstract (párrafo Suricata nuevo)
    - §8.13 (sección nueva completa)
    - Table 6 `tab:comparison` (fila Suricata actualizada)
    - §12 Conclusion (párrafo Suricata)
    - §13 Reproducibility (comandos `make experiment-suricata-run`)
    - Acknowledgments (145 → 146 días)

2. **Decidir:** ¿subir v20 a arXiv como replace? El experimento Suricata es una contribución científica sólida. Pregunta al Consejo si el paper está listo para replace o si esperar al ruleset histórico.

### P1 — Ruleset ET Open histórico

```bash
# Intento 1: Wayback Machine
curl -s "https://web.archive.org/web/20110810000000*/https://rules.emergingthreats.net/open/suricata/*.rules" | head -20

# Intento 2: GitHub histórico emergingthreats
# https://github.com/EmergingThreats/ET-Open — buscar commits de agosto 2011

# Intento 3: archivos académicos / SecurityOnion
# Papers de 2012-2014 que usaron ET Open como material suplementario
```

Si se encuentra: repetir `make experiment-suricata-run` con ruleset 2011. Documentar resultado. Si F1 > 0: "firma existió y fue retirada" (signature aging). Si F1 ≈ 0: "firma nunca existió" (cobertura siempre insuficiente).

Si no se encuentra en 2-3 horas: documentar el intento en el paper como limitación y motivación para que la comunidad mantenga archivos históricos.

### P2 — Vagrantfile Suricata permanente

Actualizar `experiments/suricata-comparative/Vagrantfile` con los fixes que se aplicaron manualmente durante DAY 146:
- `sed` corregido: `sed -i 's/- interface: eth0/- interface: eth2/'`
- `ip link set eth2 promisc on` en provisioner
- `rule-files: - /var/lib/suricata/rules/suricata.rules` en provisioner
- `sleep 60` en arranque (50K reglas tardan ~60s en cargar)

### P3 — DEBT-IRP-FLOAT-TYPES-001 (si hay tiempo)

Unificar tipos score float/double en `firewall-acl-agent`. Investigar qué tipo produce exactamente `ml-detector` en el pipeline ZMQ → protobuf → BatchProcessor antes de decidir el fix.

---

## VMs al inicio de DAY 147

```bash
VBoxManage list runningvms   # verificar qué VMs están corriendo
# Si suricata + client están corriendo del experimento DAY 146:
make halt-suricata
# Si defender está parado:
make up-argus && make bootstrap && make test-all   # EMECAS si es sesión nueva
```

---

## Reglas permanentes recordatorio

- **macOS:** nunca `sed -i` sin `-e ''`; usar `python3 << 'PYEOF'`
- **Makefile:** única fuente de verdad; nunca cmake/make directo
- **EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **`vagrant ssh defender -c`** para comandos en VM
- **Paper:** `argus_ndr_v20.tex` en `docs/`; arXiv aún en v19

---

## Archivos relevantes DAY 147

```
experiments/suricata-comparative/
  Vagrantfile                    ← fix eth2 + promisc pendiente de hacer permanente
  run_experiment.sh
  parse_results.py
  logs/experiment/
    eve-experiment-suricata-replay-{10,50,100}.json
    suricata_metrics_final.json

docs/
  argus_ndr_v20.tex              ← paper v20 local (incompleto — tiene marcadores)

Makefile                         ← targets nuevos: up-argus, up-suricata, halt-*, experiment-suricata-*
```