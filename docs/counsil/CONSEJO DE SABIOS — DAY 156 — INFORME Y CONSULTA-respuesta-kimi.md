═══════════════════════════════════════════════════════════
PARECER DEL CONSEJO — aRGus NDR
DAY 156 · 2026-05-18 · Respuesta: Kimi
═══════════════════════════════════════════════════════════

## DICTAMEN SOBRE LAS CINCO CUESTIONES

---

### Q1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001: **Fichero regular firmado, no tmpfs**

**Dictamen: Opción (c) — `/var/lib/argus/crypto-autonomy-state.json` con fsync obligatorio.**

El razonamiento es simple: el escenario de ataque exacto que describe — reboot no planificado durante AUTONOMOUS — invalida *ipso facto* a tmpfs. Si el estado desaparece con la memoria volátil, el sistema arranca en NORMAL sin reconciliación, abriendo la ACL precisamente cuando más vulnerable es. Eso convierte la "protección de autonomía" en un mecanismo de ventana de ataque temporal.

**Trade-off correcto:**
- **Persistencia:** fichero regular con `O_SYNC` o `fsync()` explícito tras cada transición de estado.
- **Seguridad:** firma Ed25519 + timestamp anti-replay. Al arrancar, el subscriber verifica la firma y rechaza estados con timestamp > `max_clock_skew` (recomendado: 60s) para evitar restauración de estados antiguos.
- **Rendimiento:** el estado es un JSON de ~200 bytes; el coste de fsync es negligible frente a la transición de modo.
- **Hardening adicional:** atributo inmutable (`chattr +i` durante NORMAL, quitado durante transiciones) si el filesystem lo soporta.

etcd local embebido es *overkill* para un singleton de estado. Añadiría un proceso más que fallar.

---

### Q2 — poll_callback como proxy de Vault: **Segundo canal SUB, no es sobreingeniería**

**Dictamen: Implementar `AutonomySubscriber` dedicado en firewall-acl-agent. Eliminar `etcd_client` del firewall.**

El firewall no debe tener conocimiento de Vault. El principio de separación de responsabilidades del ADR-024 (P2P desacoplado) exige que el firewall sea un *consumer* puro de eventos de autonomía, no un *cliente* de etcd. El `poll_callback` actual viola ese principio y crea un acoplamiento oculto.

**Justificación técnica para el MVP FEDER:**
- Un socket ZMQ SUB adicional tiene coste cero en CPU si no hay eventos (ZMQ es pull-based en el receptor).
- El firewall ya depende de ZMQ para otros componentes (ADR-027). No añade nueva dependencia de transporte.
- Facilita el test E2E: puedes inyectar eventos `AUTONOMOUS` directamente al socket sin levantar etcd-server.

**Patrón recomendado:**
```
firewall-acl-agent/
  ├─ AutonomySubscriber (ZMQ SUB → ipc:///run/argus/autonomy.sock)
  └─ FirewallAutonomyReactor (aplica/quita cadena iptables)
```
Eliminar `EtcdClient` del firewall es deuda técnica que debe cerrarse antes del MVP.

---

### Q3 — Suricata como primera fuente ADR-046: **Eve JSON vía file watcher (inotify)**

**Dictamen: Estrategia mínima = file watcher sobre `/var/log/suricata/eve.json`.**

**Razonamiento:**
- **Alineación con pipeline actual:** El RAG ingester y el ML detector ya consumen vía file watcher (CSV hoy). Añadir un watcher JSON no rompe arquitectura.
- **Sin cambios en Suricata:** No requiere reconfigurar `suricata.yaml` ni activar sockets ZMQ en Suricata, que en algunas distribuciones hospitalarias viene con ZMQ desactivado por dependencias.
- **Rollback seguro:** Si Suricata falla, el file watcher simplemente no ve nuevas líneas. El pipeline sigue operando con aRGus puro.

**Implementación mínima:**
1. Watcher inotify sobre `eve.json` (rotación-aware: detectar `moved_to`/`close_write`).
2. Parser incremental: leer solo líneas nuevas (offset por inode/mtime).
3. Normalización a schema interno aRGus: `{timestamp, src_ip, dest_ip, event_type, signature_id, severity}`.
4. Cola hacia correlador existente (mismo ZMQ PUB que usa el sniffer).

**ZMQ directo de Suricata** se reserva para la fase post-FEDER (ADR-046 v2) cuando se necesite latencia <100ms para contención activa.

---

### Q4 — ZMQ slow joiner: **Nota técnica + patrón de código, no ADR**

**Dictamen: Documentar en `docs/BACKLOG.md` como nota técnica arquitectónica; no elevar a ADR.**

Un ADR debe capturar una *decisión de diseño con alternativas evaluadas*. El slow joiner no es una decisión del proyecto, es un comportamiento de librería con solución conocida. Elevarlo a ADR otorgaría peso institucional a algo que no es controvertido.

**Formato recomendado en BACKLOG:**
```markdown
### NOTA-TEC-ZMQ-SLOW-JOINER
**Problema:** PUB/SUB ZMQ pierde mensajes si SUB conecta antes de PUB bind.
**Impacto:** Tests flaky, pérdida de primer evento AUTONOMOUS en arranque.
**Patrón obligatorio:** En todo fixture o inicialización PUB/SUB, el publisher 
debe hacer `zmq_bind()` antes de que cualquier subscriber haga `zmq_connect()`.
**Referencia:** ZMQ Guide, Chapter 2 — "The Slow Joiner Problem".
```

Además, añadir un `ASSERT` en los tests de integración que falle explícitamente si se detecta el anti-patrón (bind después de connect).

---

### Q5 — Keypair regeneration en EMECAS: **Keypair estable provisionado por bootstrap criptográfico**

**Dictamen: En producción CPD-UEx, el keypair debe ser estable y provisionado fuera del ciclo de vida del nodo.**

**Estrategia para FEDER:**

| Entorno | Keypair | Origen | Rotación |
|---------|---------|--------|----------|
| EMECAS (dev) | Regenerado cada `destroy/up` | `make bootstrap` | Cada sesión |
| STAGING | Estable por deployment | Ansible Vault / sealed secret | Trimestral |
| PROD CPD-UEx | Estable por nodo, HSM-backed | Smart card/HSM en rack o TPM | Semestral, manual |

**Razonamiento hospitalario:**
- Un CPD hospitalario no puede permitirse que un nodo aRGus quede incomunicado porque cambió el keypair tras un `apt upgrade` + reboot. La firma de estado de autonomía debe ser verificable por el nodo mismo tras años.
- El keypair de producción debe generarse **una vez** durante el provisioning físico del nodo (o del contenedor/VM si es virtualizado) y persistir en TPM/TPM2 o HSM USB.

**Implementación práctica para FEDER:**
1. **Bootstrap STEP 0** modificado: si existe `/etc/argus/crypto_material.sk` (provisión previa), usarlo. Si no, generar y persistir en `/etc/argus/` (protegido 0600, root:root).
2. **EMECAS:** mantener regeneración actual (aislamiento de sesión).
3. **Documentación:** añadir check en `make bootstrap` que advierta si se detecta keypair preexistente y pida confirmación antes de sobrescribir.

---

## RESUMEN EJECUTIVO PARA DAY 157

| ID | Prioridad | Acción inmediata |
|----|-----------|------------------|
| DEBT-AUTONOMY-STATE-PERSISTENCE-001 | P1 | Implementar `/var/lib/argus/crypto-autonomy-state.json` firmado + fsync + verificación en arranque. |
| DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 | P1 | Firmar `etcd-bootstrap-status.json` en STEP 0; verificar antes de consumir. |
| Q2 (firewall SUB) | P1 | Refactorizar firewall-acl-agent: eliminar etcd_client, añadir AutonomySubscriber. |
| Q3 (Suricata) | P2 | Watcher inotify sobre `eve.json` con parser incremental. |
| Q4 (slow joiner) | P3 | Nota técnica en BACKLOG + assert en tests. |
| Q5 (keypair) | P2 | Lógica de bootstrap: usar keypair preexistente si existe; documentar estrategia HSM para CPD. |

El Consejo considera que el trabajo de DAY 156 es sólido. La integración end-to-end de autonomía criptográfica con 50/50 tests verdes es hito de arquitectura. Las deudas identificadas para DAY 157 son gestionables y no bloquean el MVP FEDER si se cierran en el orden de prioridad indicado.

═══════════════════════════════════════════════════════════
Dictaminado por el Consejo · DAY 156 · Extremadura, España
═══════════════════════════════════════════════════════════