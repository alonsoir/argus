Tienes razón. Antes de sintetizar, identifico las desviaciones:

**Claude (mi propia respuesta) — desviación en Q1:** Voté tmpfs. El Consejo mayoritario (6/8) tiene razón: en hospitalario, un reboot no planificado durante AUTONOMOUS es exactamente el escenario que no puede tratarse con tmpfs. Me equivoqué. `/var/lib/argus/` con fsync es la decisión correcta.

**Grok — desviación en Q1:** También voté tmpfs como primaria. Mismo error.

**Mistral — desviación en Q4:** Propuso ADR-047 para el slow joiner de ZMQ. El resto del Consejo (7/8) acertó: es una nota técnica, no una decisión arquitectónica. También reclasificó cosas como P0 sin justificación suficiente.

**Mistral — desviación en Q2:** Propuso "feature flag" de forma inconsistente con la arquitectura existente.

---

**ACTA DE DECISIONES DAY 156 — CONSEJO DE SABIOS (8/8)**

```
═══════════════════════════════════════════════════════════
ACTA DE DECISIONES — Consejo de Sabios
DAY 156 · 2026-05-18 · aRGus NDR · arXiv:2604.04952
Modelos: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral
═══════════════════════════════════════════════════════════

Q1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001
DECISIÓN: /var/lib/argus/crypto-autonomy-state.json
VOTOS: 6/8 (ChatGPT, DeepSeek, Gemini, Kimi, Mistral, Qwen)
DISIDENTES: Claude y Grok (tmpfs — error reconocido)

Implementación acordada:
- Escritura atómica: write temp → fsync → rename → fsync(parent_dir)
- Firma Ed25519 + timestamp anti-replay
- Al arrancar: si estado=AUTONOMOUS y firma válida y timestamp<24h → 
  arrancar en AUTONOMOUS (no en NORMAL)
- Si fichero no existe o firma inválida → NORMAL (comportamiento actual)
- Secuence number para evitar replay

Nota importante (ChatGPT): el restart desde AUTONOMOUS debe pasar por
RECONCILING, nunca asumir NORMAL directamente. El sistema debe verificar
salud real de Vault antes de declararse sano.

Q2 — poll_callback como proxy de Vault
DECISIÓN: Implementar el canal ZMQ SUB, con feature flag para MVP FEDER
VOTOS: mayoría implementar (DeepSeek, Gemini, Kimi, Mistral, Qwen)
       minoría mantener placeholder (Claude, Grok)

Arquitectura acordada (Qwen - propuesta más elegante):
- Feature flag en config: use_dedicated_health_channel (default: false para MVP)
- Cuando true: poll_callback lee last_known_mode_ del AutonomySubscriber existente
- No se crea un segundo socket — se reutiliza el canal autonomy.sock existente
- Registrar como DEBT-CRYPTO-RECONCILIATION-001: RESOLVED-PARTIALLY

Q3 — Suricata: Eve JSON via file watcher
DECISIÓN: UNÁNIME (8/8) — file watcher sobre /var/log/suricata/eve.json
Implementación mínima:
- Watcher inotify (rotation-aware: detectar moved_to/close_write)
- Parser incremental: solo líneas nuevas (offset por inode/mtime)
- Parsear solo eventos alert con community_id para correlación inicial
- Normalización a schema interno antes del bus de eventos
- Feature flag: suricata_integration_enabled
- AppArmor para Suricata en scope de DEBT-ARGUSPP-SENSOR-HARDENING-001
  antes de cualquier despliegue (Suricata tiene historial de RCE)
- ZMQ directo: solo si latencia es cuello de botella demostrado

Q4 — ZMQ slow joiner
DECISIÓN: Nota técnica, NO un ADR (7/8)
DISIDENTE: Mistral (propuso ADR-047 — desviación de contexto)

Formato acordado:
- docs/technical-notes/ZMQ-PUB-SUB-SLOW-JOINER.md
- Wrapper ReliablePubSocket (Qwen) como infraestructura reutilizable
- Comentario obligatorio en cualquier PUB/SUB nuevo
- NUNCA un ADR (el ADR registra decisiones con alternativas, no gotchas
  de librería con solución canónica)

Q5 — Keypair: separar ciclos dev/staging/prod
DECISIÓN: UNÁNIME (8/8)

Estrategia de 3 niveles:
- Desarrollo (EMECAS): regenerar en cada destroy/up (correcto, aislamiento)
- Staging: generado en provisioning (Ansible), nunca en runtime
- Producción CPD UEx: generado UNA VEZ en bootstrap físico del nodo,
  TPM/HSM si disponible, /etc/argus/keys/ 0600 si no
  - NUNCA regenerar automáticamente en restarts
  - Rotación manual documentada con procedimiento de dual-key
  - Backup cifrado offline obligatorio
  - make bootstrap en prod: si keypair existe → cargar; si no → FALLAR
    con mensaje claro (no generar silenciosamente)

DEBT nueva: DEBT-KEYPAIR-LIFECYCLE-PROD-001

ADR-046 — CONDICIONES PARA CERRAR
El ADR queda PENDING-REVISION hasta:
  1. §Label leakage policy: features=solo aRGus, labels=Suricata,
     NUNCA mezclar en el vector de entrada
  2. §Deployment matrix: RPi5=aRGus-only (sin Suricata),
     edge server x86≥16GB=aRGus++ (con Suricata)
  3. §8 datos empíricos: reformular como hipótesis o datos reales
     (antes de arXiv v24)

═══════════════════════════════════════════════════════════
```

Ahora dame el `docs/Backlog.md` y el `README.md` actuales y genero el script de actualización.