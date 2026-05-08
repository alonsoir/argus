# Actas Consejo de Sabios — DAY 142
## Para: Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral

---

## 1. RESUMEN EJECUTIVO DEL DÍA

DAY 142 ha sido una sesión de alta productividad. Seis commits, tres DEBTs cerradas y el ciclo completo del Incident Response Protocol demostrable por primera vez.

**Commits del día:**
- `4bbc98ee` — fix: test_config_parser safe_path compliant
- `6480e234` — feat: argus-network-isolate pasos 1-3 (snapshot, reglas, dry-run)
- `e8928612` — feat: argus-network-isolate pasos 4-6 (apply, timer systemd, rollback)
- `e3f5f9c4` — fix: EMECAS reproducibility (Vagrantfile + provision.sh + Makefile)
- `7c4dba58` — fix: DEBT-VARIANT-B-BUFFER-SIZE-001 closed (pcap_create)
- `9458a90d` — feat: DEBT-VARIANT-B-MUTEX-001 closed (exclusión mutua tmux)

---

## 2. LO QUE HEMOS CONSTRUIDO

### argus-network-isolate — ADR-042 IRP

Binario C++20 independiente que implementa aislamiento de red transaccional via nftables en 6 pasos:

1. **Snapshot** selectivo del ruleset (solo tabla `argus_isolate`, excluye tablas iptables-managed con expresiones `xt match` incompatibles)
2. **Generación** de reglas con whitelist IP/port configurable
3. **Validación en seco** (`nft -c`) — aborta sin tocar nada si falla
4. **Apply atómico** (`nft -f`) — una sola operación
5. **Timer systemd-run** idempotente — rollback automático en 300s si nadie confirma
6. **Rollback** limpio — elimina tabla `argus_isolate`, restaura estado previo

Ciclo verificado en dev VM (eth2): NORMAL → ISOLATED → STATUS → ROLLBACK → NORMAL. SSH sobrevivió en todo momento (eth0 + whitelist). Forense JSONL operativo.

**Decisión de diseño importante aprobada hoy:** el sistema protege por defecto. `auto_isolate: true` será el default en `isolate.json`. Un hospital que instala aRGus y no toca la configuración debe estar protegido. Apagar el aislamiento automático debe ser un acto explícito y consciente del administrador.

### DEBT-VARIANT-B-BUFFER-SIZE-001

`PcapBackend::open()` refactorizado de `pcap_open_live()` a `pcap_create() + pcap_set_buffer_size() + pcap_activate()`. El campo `buffer_size_mb` del JSON ahora se aplica realmente. Crítico para ARM64/RPi donde el kernel default es 2MB vs 8MB configurado. Verificado: `[pcap] Variant B opened on eth1 buffer=8MB`.

### DEBT-VARIANT-B-MUTEX-001

Script `scripts/check-sniffer-mutex.sh` que detecta si hay una variant de sniffer activa antes de arrancar otra. Usa sesiones tmux como fuente de verdad — la lógica no entra en los binarios, según decisión del Consejo DAY 141. Verificado: Variant B activa + intento Variant A → violación detectada, Variant B detenida, exit 1.

---

## 3. LO QUE HAREMOS MAÑANA — DAY 143

### DEBT-IRP-NFTABLES-001 sesión 3/3 — integración firewall-acl-agent

Es la pieza que convierte el IRP de herramienta manual a sistema automático. El trabajo:

1. Añadir a `isolate.json`: `auto_isolate`, `threat_score_threshold` (default 0.95), `auto_isolate_event_types` (default: ransomware, lateral_movement, c2_beacon)
2. En `firewall-acl-agent`: detectar umbral superado → `execv()` a `argus-network-isolate isolate --interface <iface>`
3. Test de integración con evento sintético score >= 0.95
4. AppArmor profile para `argus-network-isolate`
5. Garantizar reproducibilidad en hardened VM

---

## 4. PREGUNTAS AL CONSEJO

### P1 — Criterio de disparo: ¿umbral único o matriz de decisión?

El diseño actual propone un umbral simple: `threat_score >= 0.95`. Sin embargo, el aislamiento de red en un hospital es una acción de alto impacto — puede interrumpir equipos médicos conectados a la red.

**¿Recomendáis un umbral único configurable, o una matriz de decisión que combine score + tipo de evento + hora del día + número de eventos en ventana temporal?**

Por ejemplo: `score >= 0.95 AND event_type IN (ransomware, c2_beacon) AND events_in_last_60s >= 3`.

Mi posición: el umbral simple es más auditable y predecible para un administrador no experto. La matriz es más precisa pero más difícil de explicar en una demo FEDER.

### P2 — `execv()` vs subprocess en firewall-acl-agent

Para llamar a `argus-network-isolate` desde `firewall-acl-agent` hay dos opciones:

**A)** `execv()` — reemplaza el proceso actual. Simple, sin fork, pero mata el agente de firewall durante el aislamiento.

**B)** `fork() + execv()` — proceso hijo independiente. El agente de firewall sigue monitorizando mientras se aplica el aislamiento.

**¿Cuál recomendáis y por qué?** Mi posición: `fork() + execv()` es más correcto — el agente debe seguir funcionando durante y después del aislamiento para registrar evidencia forense.

### P3 — AppArmor profile para argus-network-isolate

El binario necesita acceso a `/usr/sbin/nft`, `/tmp/argus-*`, `/var/log/argus/`, `systemd-run` y `ip link`.

**¿Recomendáis perfil en modo `enforce` desde el primer deploy, o `complain` hasta validar en producción real?**

Mi posición: `enforce` desde el primer día, coherente con el axioma BSR y la política de AppArmor del proyecto. `complain` es una deuda técnica disfrazada de prudencia.

### P4 — Rollback con backup en `argus-network-isolate`

El snapshot actual captura solo la tabla `argus_isolate` (vacía en primera ejecución). Esto significa que el rollback elimina la tabla pero no restaura un estado previo explícito — las tablas iptables-managed sobreviven solas.

**¿Es suficiente esta aproximación para producción, o deberíamos mantener un estado persistente en `/etc/ml-defender/firewall-acl-agent/last-known-good.nft` que se actualice periódicamente?**

Mi posición: el estado persistente es más robusto para entornos con reglas nftables propias del cliente, pero añade complejidad. Para la demo FEDER, el comportamiento actual es suficiente y demostrable.

---

## 5. MIS RESPUESTAS COMO PUNTO DE PARTIDA

**P1:** Umbral único `score >= 0.95` para el MVP FEDER. La matriz de decisión se registra como `IDEA-IRP-DECISION-MATRIX-001` para post-FEDER. Justificación: auditabilidad y simplicidad para administradores no expertos.

**P2:** `fork() + execv()`. El agente de firewall debe sobrevivir al aislamiento para continuar registrando evidencia. Un agente muerto durante un ataque activo es exactamente lo que el atacante busca.

**P3:** `enforce` desde el primer deploy. Coherente con el axioma BSR y la política del proyecto. Si el perfil bloquea algo legítimo, lo descubrimos en dev antes de llegar a producción.

**P4:** Para FEDER, el comportamiento actual es suficiente. Registrar `DEBT-IRP-LAST-KNOWN-GOOD-001` como mejora post-FEDER para entornos con rulesets nftables propios del cliente.

---

*Actas DAY 142 — aRGus NDR*
*Alonso Isidoro Román + Claude (Anthropic)*
*Badajoz, 5 de Mayo de 2026*