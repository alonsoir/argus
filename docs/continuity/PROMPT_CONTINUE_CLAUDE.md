# aRGus NDR — DAY 149 CONTINUITY PROMPT
# Estado: main @ v0.7.1-day148 | EMECAS DAY 148: 65/65 PASSED
# Paper: arXiv:2604.04952 | v23 local (v3 en arXiv — submit/7576269 procesando)
# FEDER deadline: 22-Sep-2026 | Go/no-go: 1-Ago-2026

## COMPLETADO DAY 148
- Suricata offline -r -k none: 50,010 ET Open rules, 323,154 pkts → 0 firmas ET. Irrefutable.
- Paper v23: §8.13 offline validation, §8.14 taxonomy, §10 Future Work (5 secciones), §8.2 Zeek row
- Abstract v23: tres paradigmas + complementariedad arquitectónica
- arXiv replace v3 submitted (submit/7576269)
- DEBT-IRP-FLOAT-TYPES-001 CERRADA: double→float, parche IEEE 754 eliminado, PROFILE=production ALL TESTS COMPLETE
- PR #58 (fix float) + PR #59 (docs day148) → main @ ab43c6c2
- Tag v0.7.1-day148, ramas limpias

## CONSEJO DAY 148 — SÍNTESIS PARA DAY 149
P1 (complementariedad abstract): 8/8 mantener. Refinamiento: añadir "architecturally" → pendiente v24
P2 (PARQUET schema): 8/8 por flow. Política híbrida: todos ml-detector, solo DENY/DROP firewall.
Tipos Arrow: int64 timestamps, float32 scores, utf8 dictionary IDs, int8 enums
P3 (secuencia): A→C→B→D. No ARM64 antes de A+B+C verdes.
DEPENDENCIA CRÍTICA: email Dr. Andrés Caro Lindo esta semana (DEBT-LEGAL-DATA-RETENTION-001)

## PENDIENTES DAY 149 (por prioridad)

### P0 — BLOQUEANTE pre-FEDER
1. DEBT-PARQUET-SCHEMA-001 (sesión completa):
   a) vagrant up (defender VM)
   b) Localizar CSVs reales: find /vagrant/logs -name "*.csv" | head -20
   c) head -5 de ml-detector CSV y firewall-acl-agent CSV
   d) Contar filas: wc -l *.csv → decidir política registro con datos reales
   e) Definir schema Arrow v1.0 con tipos acordados por Consejo
   f) Generar Parquet prueba: python3 con pyarrow, validar roundtrip
   g) Documentar en ADR-0043 D4b, commit, cerrar deuda
   h) Estimar volumen por nodo por mes

### P1 — GESTIÓN EXTERNA (iniciar hoy)
2. Email Dr. Andrés Caro Lindo (andresc@unex.es):
   - Asunto: DEBT-LEGAL-DATA-RETENTION-001 — consulta GDPR pseudonimización
   - Pregunta: ¿cuándo datos HMAC-SHA256 dejan de ser PII si K_pseudo está en Vault destruido?
   - No bloquea schema Parquet pero sí despliegue productivo — latencia jurídica externa

### P1 — TÉCNICA (si queda tiempo tras P0)
3. DEBT-CRYPTO-MATERIAL-STORAGE-001: HashiCorp Vault dev mode en Vagrant
   - Objetivo: prototipo mínimo K_pseudo + HMAC + firma Ed25519
   - No necesita HA todavía — dev mode suficiente para validar contrato

### P1 — PAPER (mínimo cambio, máximo blindaje)
4. Abstract v24: "are complementary" → "are architecturally complementary by design"
   Una palabra. Aplicar, compilar, no subir a arXiv todavía.

## ESTADO TÉCNICO
- Keypair post-destroy DAY 133: b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa
- CSVs ml-detector: buscar en /vagrant/logs/lab/ o /var/log/argus/
- CSVs firewall-acl-agent: buscar en /vagrant/logs/firewall_logs/
- Schema candidato ADR-0043 D4b: docs/adr/ADR-0043-memoria-episodica-distribuida-v4.md
- Paper: docs/latex/main.tex (v23)

## REGLAS PERMANENTES
- macOS: nunca sed -i sin -e ''; usar python3 inline
- Makefile: única fuente de verdad
- EMECAS: vagrant destroy -f && vagrant up && make bootstrap && make test-all
- Consejo: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral (8 modelos)
- No ARM64 antes de pipeline x86 end-to-end verde (Kimi, DAY 148)

## TABLA TRES PARADIGMAS (referencia)
Sistema              | F1     | Precision | Recall | TP  | Paradigma
Suricata 6.0.10      | 0.000  | ---       | 0.000  | 0   | Signature (ET Open)
Zeek 8.1.2 (default) | 0.042  | 1.000     | 0.022  | 14  | Scripted behavioral
aRGus NDR            | 0.9985 | 0.997     | 1.000  | 646 | ML behavioral

## TIPOS ARROW ACORDADOS (Consejo 8/8 DAY 148)
timestamp_utc_ns: int64 (epoch nanoseconds UTC)
confidence/scores: float32
anon_host_id/flow_id: utf8 dictionary-encoded
event_type/action: int8 o dictionary(utf8)
bytes: int64 | packets: int32 | ports: uint16/int32