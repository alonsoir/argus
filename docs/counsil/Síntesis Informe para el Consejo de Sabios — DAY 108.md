## CONSEJO DE SABIOS — SÍNTESIS DE DELIBERACIÓN
### DAY 108: provision.sh + ADR-026/027 + Gate PASO 4

**Sesión**: DAY 108
**Miembros que respondieron**: ChatGPT5 (OpenAI), DeepSeek x2, Gemini (Google), Grok (xAI)
**Nota de identidad**: `respuesta_qwen.md` declara explícitamente *"Soy DeepSeek — modelo de DeepSeek Research (China, independiente de Alibaba/Tongyi Lab)"*. Patrón consolidado DAY 103–108. Se registra como tercera instancia de DeepSeek. Falta respuesta de Qwen y Parallel.ai.
**Árbitro**: Alonso Isidoro Román
**Fecha**: 2026-04-05

---

## 1. MAPA DE CONVERGENCIAS Y DIVERGENCIAS

### Q1 — `std::terminate()` vs MLD_DEV_MODE

| Miembro | Veredicto | Matiz |
|---------|-----------|-------|
| ChatGPT5 | `terminate` prod / `return false` dev con `#ifdef MLD_DEV_MODE` | Mensaje cerr muy descriptivo |
| DeepSeek | `terminate` prod / `exit(1)` dev con `getenv("MLD_DEV_MODE")` | exit(1) más depurable que terminate |
| Gemini | `terminate` puro, sin escape hatch | Mensaje cerr muy descriptivo antes del terminate |
| Grok | `terminate` prod / `return false` o excepción custom dev | Espíritu "crash early" |
| DeepSeek² | `terminate` prod / flag explícito `MLD_ALLOW_UNCRYPTED`, NO MLD_DEV_MODE | Más estricto: MLD_DEV_MODE no debe desactivar seguridad |

**🏛️ VEREDICTO**: Unánime en `std::terminate()` en producción. Divergencia en el escape hatch de desarrollo.

**Posición más interesante (DeepSeek²)**: `MLD_DEV_MODE` no debe ser el flag — es demasiado genérico y crea un falso sentido de seguridad. Propone `MLD_ALLOW_UNCRYPTED` como flag explícito separado. El desarrollador debe actuar conscientemente para desactivar el fail-closed.

**Decisión del árbitro**: `std::terminate()` en producción (unánime). En desarrollo, usar `MLD_ALLOW_UNCRYPTED` (propuesta DeepSeek²) — no `MLD_DEV_MODE`, que ya tiene otros usos. Mensaje `cerr` muy descriptivo antes del terminate en todos los casos.

---

### Q2 — etcd-client: cache vs rebuild limpio

| Miembro | Veredicto |
|---------|-----------|
| ChatGPT5 | No cache. Rebuild siempre. |
| DeepSeek | No cache. Rebuild siempre. |
| Gemini | No cache. "Impuesto de calidad" aceptable. |
| Grok | No cache por ahora. Checksum simple en el futuro. |
| DeepSeek² | No cache. Añadir mensaje UX que gestione expectativas. |

**🏛️ VEREDICTO UNÁNIME**: No optimizar. Rebuild limpio siempre. Coste aceptable frente a reproducibilidad garantizada. Única adición aceptada: mensaje de log que avise al operador que el build tarda ~2 min intencionalmente.

---

### Q3 — Plugin en rag-ingester: read-only vs modificar MessageContext

| Miembro | Veredicto | Argumento clave |
|---------|-----------|-----------------|
| ChatGPT5 | Read-only + capability explícita futura (`MODIFY_BEFORE_INGEST`) | Riesgo de poisoning del vector store |
| DeepSeek | Read-only. Plugin solo decide accept/reject. | Formato protobuf puede romperse si plugin modifica payload |
| Gemini | Read-only. Plugin = Gatekeeper (CONTINUE/DROP/ALERT) | Pérdida de trazabilidad si plugin modifica antes de FAISS |
| Grok | Read-write permitido con contrato claro | Útil para enriquecimiento de metadata antes de FAISS |
| DeepSeek² | Read-only forzado. `ctx_readonly.payload = nullptr` | FAISS no valida integridad — corrupción silenciosa garantizada si plugin escribe |

**🏛️ VEREDICTO**: Mayoría clara (4 de 5) por read-only. Grok es el único que permite modificación, con argumento de enriquecimiento de metadata.

**Propuesta técnica más sólida (DeepSeek²)**:
```cpp
MessageContext ctx_readonly = ctx;
ctx_readonly.payload = nullptr;
ctx_readonly.length = 0;
plugin->invoke(&ctx_readonly);
// usar ctx original para FAISS
faiss_ingest(ctx.payload, ctx.length);
```

**Decisión del árbitro**: Read-only en PHASE 2b. La capacidad `MODIFY_BEFORE_INGEST` queda reservada para ADR futuro con firma Ed25519 diferenciada (ChatGPT5). El riesgo de corrupción silenciosa de FAISS es inaceptable sin contrato explícito.

---

### Q4 — rag-security/config: provision.sh vs rag-security-start

| Miembro | Veredicto |
|---------|-----------|
| ChatGPT5 | Crear en provision.sh. Binarios no deben crear estructura crítica. |
| DeepSeek | Crear en provision.sh + symlink. Asegurar que el JSON existe en repo. |
| Gemini | Crear en provision.sh. Race condition administrativa si se delega al binario. |
| Grok | Crear en provision.sh. Mantener provision.sh como SSOT. |
| DeepSeek² | Crear en provision.sh + symlink. Determinismo total. |

**🏛️ VEREDICTO UNÁNIME**: `mkdir -p /vagrant/rag-security/config` en `provision.sh`. El symlink también se crea allí. Los binarios no crean estructura del sistema de archivos.

---

## 2. INSIGHTS NUEVOS NO CONTEMPLADOS EN EL INFORME

**ChatGPT5 — provision.sh ahora es parte del TCB**:
> Antes no lo era. Ahora sí. Debe versionarse con cuidado, necesita tests (aunque sean bash), cualquier cambio puede romper todo.

Propone formalizar `TEST-PROVISION-1: vagrant destroy → up → pipeline-start → status == 6/6` como gate formal en CI.

**ChatGPT5 — ADR-028: RAG Ingestion Trust Model**:
El riesgo de integridad del RAG frente a plugins es nuevo y relevante. Merece ADR propio antes de permitir cualquier capacidad de escritura en rag-ingester.

**Gemini — Principio de Espejo Criptográfico**:
Formaliza ADR-027 en términos de diseño general: cualquier canal bidireccional con HKDF debe tener contextos invertidos en el extremo servidor. Principio aplicable a futuros canales.

**DeepSeek² — `MLD_ALLOW_UNCRYPTED` separado de `MLD_DEV_MODE`**:
Importante distinción: `MLD_DEV_MODE` activa comportamientos de desarrollo en general. Desactivar seguridad criptográfica debe requerir un flag explícito y específico que comunique claramente la intención.

---

## 3. DECISIONES DEL ÁRBITRO

### ✅ APROBADO SIN CONDICIONES
1. **Q2**: Rebuild limpio siempre en `install_shared_libs()`. No cache. Añadir mensaje UX.
2. **Q4**: `mkdir -p /vagrant/rag-security/config` + symlink en `provision.sh`.
3. **Q3**: Plugin en rag-ingester = read-only en PHASE 2b. `ctx_readonly.payload = nullptr`.
4. **TEST-PROVISION-1** como gate formal (ChatGPT5) — documentar en Makefile.
5. **ADR-028: RAG Ingestion Trust Model** — redactar antes de cualquier capacidad de escritura.

### ⚠️ APROBADO CON CONDICIÓN
6. **Q1**: `std::terminate()` en producción. Escape hatch: `MLD_ALLOW_UNCRYPTED` (no `MLD_DEV_MODE`). Implementar en DAY 109 junto con los fixes de Q4.

### 📋 NUEVOS ÍTEMS PARA ROADMAP
| Ítem | Origen | Prioridad |
|------|--------|-----------|
| `TEST-PROVISION-1` como gate CI formal | ChatGPT5 | Alta — post PHASE 2b |
| ADR-028: RAG Ingestion Trust Model | ChatGPT5 | Alta — antes de write-capable plugins |
| `MLD_ALLOW_UNCRYPTED` flag explícito | DeepSeek² | Alta — DAY 109 |
| Mensaje UX en `install_shared_libs()` (~2 min) | DeepSeek² | Baja — cosmético |

---

## 4. ORDEN DE TRABAJO DAY 109

```
ANTES de PHASE 2b:
  a) provision.sh: mkdir -p /vagrant/rag-security/config + symlink
  b) Invariant: MLD_ALLOW_UNCRYPTED en 3 adaptadores etcd_client.cpp
  c) Verificar 6/6 tras cambios

PHASE 2b:
  plugin_process_message() en rag-ingester
  Contrato: read-only (ctx_readonly.payload = nullptr)
  Gate: TEST-INTEG-4b (MessageContext, result_code=0)
  Patrón: firewall-acl-agent DAY 105
```

---

## 5. NOTA SOBRE IDENTIDAD DE MIEMBROS

Patrón Qwen→DeepSeek consolidado (DAY 103–108, 6 sesiones consecutivas). Se han recibido en esta sesión **tres respuestas de DeepSeek y cero de Qwen**. Falta respuesta de Parallel.ai en todas las sesiones recientes. Para DAY 109: considerar verificar canal Qwen directamente o documentar la ausencia como permanente.

---

*Síntesis preparada por Claude (Anthropic) — DAY 108*
*Via Appia Quality: la reproducibilidad no es una feature, es el cimiento.*

---

```bash
git add docs/consejo/CONSEJO-DAY108-informe.md \
        docs/consejo/CONSEJO-DAY108-feedback-chatgpt5.md \
        docs/consejo/CONSEJO-DAY108-feedback-deepseek.md \
        docs/consejo/CONSEJO-DAY108-feedback-gemini.md \
        docs/consejo/CONSEJO-DAY108-feedback-grok.md \
        docs/consejo/CONSEJO-DAY108-feedback-qwen.md \
        docs/consejo/CONSEJO-DAY108-sintesis.md

git commit -m "docs(consejo): DAY 108 informe + feedback x5 + síntesis

Q1: std::terminate() prod + MLD_ALLOW_UNCRYPTED dev (no MLD_DEV_MODE)
Q2: rebuild limpio siempre — unánime, no cache
Q3: plugin rag-ingester read-only — ctx_readonly.payload=nullptr
Q4: rag-security/config en provision.sh — unánime

Nuevos ítems aprobados:
- TEST-PROVISION-1 como gate CI formal (ChatGPT5)
- ADR-028: RAG Ingestion Trust Model (ChatGPT5)
- MLD_ALLOW_UNCRYPTED flag explícito (DeepSeek)

Nota: respuesta_qwen.md = DeepSeek (patrón consolidado DAY 103-108)
PHASE 2b desbloqueada: plugin_process_message() rag-ingester, read-only"
```

---

Hasta mañana, Alonso. DAY 108 cerrado limpio. 🛡️