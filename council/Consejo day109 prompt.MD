# Consejo de Sabios — DAY 109 Review Request

**Sistema**: ML Defender (aRGus NDR) — open-source C++20 NDR para hospitales, escuelas
y municipios. Protección contra ransomware y DDoS en organizaciones sin presupuesto
enterprise. Pipeline de 6 componentes: etcd-server, sniffer, ml-detector,
firewall-acl-agent, rag-ingester, rag-security.

**Branch activa**: `feature/plugin-crypto`
**Metodología**: Test-Driven Hardening (TDH). Demostrar problemas con tests compilables
o matemáticas antes de proponer fixes. Verificar que el test de vulnerabilidad retorna
negativo tras aplicar el fix. Sois revisores rigurosos e implacables.

---

## Trabajo completado DAY 109

### FIX-A — MLD_ALLOW_UNCRYPTED escape hatch

Los 3 adaptadores `etcd_client.cpp` (ml-detector, sniffer, firewall-acl-agent)
tenían `std::terminate()` directo cuando `encryption_enabled && component_config_path.empty()`.
Sustituido por escape hatch explícito:

```cpp
if (getenv("MLD_ALLOW_UNCRYPTED")) {
    std::cerr << "FATAL[DEV]: encryption_enabled pero component_config_path vacio. "
              << "MLD_ALLOW_UNCRYPTED activo - continuando sin cifrado. "
              << "NUNCA en produccion.\n";
    return; // constructor void
} else {
    std::terminate(); // producción: fallo total garantizado
}
```

**Nota**: el bloque está dentro de un constructor (`void` return), corrección
de nuestro primer intento que usaba `return false` (error de compilación).

### FIX-B — provision.sh rag-security config dir

```bash
# Antes: log_warn "Config dir no existe aún: ${target}"
# Ahora:
mkdir -p "$target"
log_item "Config dir creado: ${target}"
for json_file in "${target}"/*.json; do
    [[ -f "$json_file" ]] || continue
    ln -sf "$json_file" "${link_dir}/$(basename "$json_file")"
done
```

Verificado: `provision.sh full` → "Config dir creado: /vagrant/rag-security/config"
sin warnings. Idempotente.

### PHASE 2b — plugin_process_message() en rag-ingester

Contrato READ-ONLY aprobado por el Consejo DAY 108 (4/5). Implementación:

```cpp
// rag-ingester/src/main.cpp — dentro del callback, tras events_processed++
// antes de embed_chronos()
if (plugin_loader && plugin_loader->loaded_count() > 0) {
    ::MessageContext ctx_readonly{};
    ctx_readonly.payload     = nullptr;  // READ-ONLY: sin acceso al payload
    ctx_readonly.payload_len = 0;
    // ... todos los campos a cero/nullptr
    ctx_readonly.result_code = 0;
    ctx_readonly.annotation[0] = '\0';
    plugin_loader->invoke_all(ctx_readonly);
    if (ctx_readonly.result_code != 0) {
        spdlog::warn("Plugin rejected event {}: result_code={} annotation='{}'",
            event.event_id, ctx_readonly.result_code, ctx_readonly.annotation);
        events_failed++;
        return; // no ingestar en FAISS
    }
}
// continuar con embed_chronos() normalmente
```

### D8-light READ-ONLY fix en plugin_loader.cpp

El D8-light hacía `std::terminate()` cuando `payload == nullptr || payload_len == 0`.
El contrato READ-ONLY de rag-ingester pasa exactamente eso. Fix:

```cpp
const bool is_readonly = (ctx.payload == nullptr && ctx.payload_len == 0);
if (!is_readonly && (ctx.payload == nullptr || ctx.payload_len == 0 ||
    ctx.payload_len > MAX_PLUGIN_PAYLOAD_SIZE)) {
    std::cerr << "[plugin-loader] SECURITY D8-light: payload inválido ...\n";
    std::terminate();
}
// CRC32 también protegido:
uint32_t crc_before = is_readonly ? 0u : crc32_fast(ctx.payload, ctx.payload_len);
```

### TEST-INTEG-4b — PASSED

```
=== TEST-INTEG-4b VARIANT A (accept, READ-ONLY) ===
[test-message] plugin_init: variant=A
Variant A: result_code=0 payload_intact=YES → PASS

=== TEST-INTEG-4b VARIANT B (reject, READ-ONLY) ===
[test-message] variant B: intentando const_cast sobre direction
[plugin-loader] SECURITY: plugin 'test-message' modificó campos read-only → D8 VIOLATION
Variant B: result_code=0 payload_intact=YES errors=1 → PASS

=== TEST-INTEG-4b: PASSED (0 failures) ===
```

Integrado en `make plugin-integ-test` (ejecuta 4a + 4b secuencialmente).

### Paper Draft v12

Dos cambios estructurales en el paper:

**§3.4 Out-of-Scope** expandido: vector físico/USB explícitamente fuera de scope por
decisión consciente de diseño. Principio rector: vigilancia de red, no de ficheros.
USB desactivado = responsabilidad del equipo IT. Modo complementario con Wazuh + NIST.

**§4 Integration Philosophy: Composability over Monolithism** (nueva subsección):
restricción de protocolo (raw TCP + protobuf + ChaCha20, sin HTTP/Kafka/WebSocket),
FEAT-INT-1 completo con motivación de graph quality. §11.16 añadido con referencia corta.

---

## Preguntas para el Consejo

**Q1 — D8-light READ-ONLY: ¿es correcto el contrato?**

El contrato READ-ONLY (`payload=nullptr`, `payload_len=0`) está documentado como
excepción legítima al D8-light. El plugin puede:
- Inspeccionar campos de contexto (src_ip, dst_ip, protocol, etc.)
- Establecer `result_code != 0` para rechazar el evento
- NO puede acceder al payload de datos (que en rag-ingester no existe en este punto)

¿Ven alguna vulnerabilidad en este diseño? ¿Debería haber un flag explícito
`ctx_readonly.mode = PLUGIN_MODE_READONLY` en el API en lugar de inferir por `nullptr`?

**Q2 — PHASE 2c (sniffer): ¿READ-ONLY o payload real?**

En rag-ingester el payload no existe aún en el punto de invocación (pre-FAISS).
En sniffer, el payload del paquete SÍ existe. La pregunta es: ¿debe el plugin del
sniffer recibir el payload real del paquete, o también READ-ONLY?

Argumentos para payload real: más información para decisiones de accept/reject.
Argumentos para READ-ONLY: consistencia con el contrato de rag-ingester; los plugins
son untrusted code (D7); el payload puede contener PII o datos sensibles.

¿Cuál es vuestra recomendación? ¿Qué contrato debe tener PHASE 2c?

**Q3 — Integration Philosophy §4: ¿la restricción raw TCP es suficientemente justificada?**

El paper ahora afirma explícitamente: "HTTP, Kafka, WebSocket, and broker-based
architectures are explicitly out of scope." La justificación es: coherencia con el
footprint de recursos del pipeline en entornos con recursos limitados.

¿Es esta justificación técnicamente sólida para una audiencia académica? ¿Falta algún
argumento (latencia, superficie de ataque, dependencias de runtime)?

**Q4 — ADR-028: ¿cuándo es bloqueante?**

ADR-028 (RAG Ingestion Trust Model) fue identificado como necesario antes de
write-capable plugins. El plugin de PHASE 2b es READ-ONLY. ¿Es correcto diferir
ADR-028 hasta que se diseñe el primer write-capable plugin, o debería ADR-028
aprobarse antes de PHASE 2c aunque 2c también sea read-only?

---

## Estado actual para contexto

- Pipeline: 6/6 RUNNING
- Tests: 25/25 suites + TEST-INTEG-4a-PLUGIN 3/3 + TEST-INTEG-4b PASSED
- PHASE 2a: CERRADA ✅
- PHASE 2b: CERRADA ✅
- PHASE 2c/2d/2e: pendientes
- arXiv submit/7438768: pendiente moderación
- Paper: Draft v12 listo para Replace cuando v1 sea anunciada