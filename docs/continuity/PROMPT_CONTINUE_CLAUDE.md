# aRGus NDR — DAY 148 CONTINUITY PROMPT
# Estado: main @ v0.7.1-day147 | EMECAS DAY 147: 65/65 PASSED
# Paper: arXiv:2604.04952 | v22 local (v19 en arXiv)
# FEDER deadline: 22-Sep-2026

## COMPLETADO DAY 147
- pipeline-status pgrep fallback (commit 42c04b06) — 6/6 ✅
- Paper v21: §8.13 hallazgos históricos + HTTP C2 + Springer 2023
- Experimento Zeek 8.1.2 offline — experiments/zeek-comparative/
  Resultados: Suricata F1=0.000 | Zeek F1=0.042 P=1.000 TP=14 | aRGus F1=0.9985
  weird.log: IRC:30, HTTP beaconing:62, SMB:33 — Zeek ve todo, no alerta
- Paper v22: §8.14 "Three Paradigms" (tablas, framing, reproducibility §13)
- Consejo de Sabios (8/8): P1/P2/P3 respondidas — ver síntesis abajo
- update_docs_day147.py — README.md + BACKLOG.md pendientes de aplicar

## CONSEJO DAY 147 — SÍNTESIS PARA DAY 148
P1 (metodología offline/live):
- 7/8 aceptan con declaración explícita
- KIMI DISSENTER (BLOQUEANTE): ejecutar suricata -r neris.pcap offline
  Si da 0 alertas → conclusión irrefutable → arXiv desbloqueado
  Si da >0 → problema de setup live, no de motor

P2 (framing científico):
- Keywords OBLIGATORIOS en §8.14: "telemetry", "measurement layer", "classification layer"
- Frase clave ChatGPT: "Observability does not imply classification"
- Framing Kimi: taxonomía de arquitecturas de decisión, no ranking
- Gemini: Zeek = "passive librarian" que necesita aRGus como "cerebro"

P3 (Zeek Phase 2):
- Phase 1 suficiente para arXiv — NO retrasar
- Future work: mencionar detect-botnets.zeek específicamente (DeepSeek)
- Gemini: Intel framework con feeds 2026 no detectaría tráfico 2011 de todas formas

## PENDIENTES DAY 148 (por prioridad)

### P0 — BLOQUEANTES pre-arXiv
1. suricata -r offline (10 min):
   cd experiments/suricata-comparative
   vagrant ssh suricata -c "
   sudo suricata -r /vagrant/datasets/ctu13/botnet-capture-20110810-neris.pcap \
   -c /etc/suricata/suricata.yaml \
   -l /vagrant/logs/experiment/suricata-offline/ \
   --runmode single 2>&1 | tail -5"
   Si 0 alertas: añadir nota metodológica al paper (una línea en §8.13)
   Si >0 alertas: emergencia — rehacer experimento Suricata

2. Refinar §8.14 con keywords Consejo:
   - Reemplazar "observabilidad" por "measurement layer" / "telemetry"
   - Añadir frase "Observability does not imply classification"
   - Afinar framing taxonómico (arquitecturas de decisión, no benchmark)

3. §10 Future Work: añadir párrafo Zeek Phase 2
   - detect-botnets.zeek específicamente
   - Intel framework limitation (feeds históricos no disponibles)
   - Pregunta científica: cuánta ingeniería manual para acercarse a ML behavioral

4. Tabla §8.2 (comparison with state of the art): añadir fila Zeek 8.1.2

### P1 — TÉCNICA
5. DEBT-IRP-FLOAT-TYPES-001:
   - Investigar tipo producido por ml-detector en pipeline ZMQ→protobuf→BatchProcessor
   - float vs double: unificar antes de tests MITRE
   - Revisar Detection::confidence type en proto

### P1 — DOCS (si no se hizo al final DAY 147)
6. Aplicar update_docs_day147.py:
   python3 update_docs_day147.py --dry-run
   python3 update_docs_day147.py
   git add README.md docs/BACKLOG.md
   git commit -m "docs(day147): README + BACKLOG three-paradigm experiment"

### P1 — DECISIÓN
7. arXiv replace v19→v22:
   - Esperar confirmación suricata -r offline (P0 item 1)
   - Si verde: subir v22 como replace con abstract actualizado
   - La diferencia v19→v22 es sustancial: ADR-029, Suricata, Zeek, §8.13, §8.14

## ESTADO TÉCNICO
- Keypair post-destroy DAY 133: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa
- Experimento Suricata: experiments/suricata-comparative/ (VMs pueden estar levantadas)
- Experimento Zeek: experiments/zeek-comparative/ (VMs levantadas DAY 147)
- Logs Zeek: logs/experiment/zeek/{10,50,100}mbps/ + zeek_metrics_v2_10mbps.json
- Paper: docs/latex/main.tex (v22) + docs/latex/references.bib

## REGLAS PERMANENTES
- macOS: nunca sed -i sin -e ''; usar python3 inline
- Makefile: única fuente de verdad
- EMECAS: vagrant destroy -f && vagrant up && make bootstrap && make test-all
- Consejo: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral (8 modelos)

## TABLA TRES PARADIGMAS (referencia)
Sistema              | F1     | Precision | Recall | TP  | Paradigma
Suricata 6.0.10      | 0.000  | ---       | 0.000  | 0   | Signature (ET Open)
Zeek 8.1.2 (default) | 0.042  | 1.000     | 0.022  | 14  | Scripted behavioral
aRGus NDR            | 0.9985 | 0.997     | 1.000  | 646 | ML behavioral