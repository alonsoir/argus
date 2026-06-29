# 🏛️ CONSEJO DE SABIOS — RESPUESTA DAY 114
*Feedback sincero, directo y proactivo para ML Defender (aRGus NDR)*

---

## ✅ Reconocimiento inicial

Antes de entrar en materia: **excelente trabajo en DAY 114**. El hecho de que ADR-025 haya funcionado exactamente como se diseñó (`fail-closed → std::terminate()`) es una victoria de arquitectura. Muchos equipos ven los "fallos" como errores; vosotros los estáis tratando como *comportamiento esperado*. Eso es madurez ingenieril.

---

## 🔐 Q1 — DEBT-SIGN-AUTO: Diseño del mecanismo de firma automática

### ✅ Lo que funciona bien:
- **Idempotencia**: Diseño correcto. Poder ejecutar `check-and-sign-plugins` sin efectos secundarios es esencial para automatización y CI/CD.
- **Verificación en tres niveles**: (1) ¿existe `.sig`? (2) ¿es válida? (3) ¿coincide con clave actual? — cubre los casos principales.
- **Integración en Makefile y Vagrant**: Buena práctica de "shift-left" de la seguridad operativa.

### ⚠️ Riesgos y casos edge no cubiertos:
| Riesgo | Impacto | Mitigación propuesta |
|--------|---------|---------------------|
| **Race condition durante deploy** | Plugin firmado en nodo A, desplegado en nodo B antes de replicar clave pública | Usar versión de clave en el `.sig` + validación de timestamp |
| **Clave privada comprometida** | Firma automática podría firmar malware | Separar entorno de firma: clave offline + proceso manual para producción crítica |
| **Plugin modificado post-firma** | `.sig` válido pero binario alterado | Verificar hash del binario al cargar, no solo la firma |
| **Dependencia circular** | `plugin-loader` necesita firmarse a sí mismo | Bootstrapping: loader firmado en build, no en runtime |

### 💡 Recomendación proactiva:
Añadid un **`plugin-manifest.json`** por cada plugin:
```json
{
  "name": "libplugin_hello.so",
  "version": "0.3.0",
  "sha256": "abc123...",
  "signed_at": "2026-04-11T14:30:00Z",
  "key_version": "ed25519-v2",
  "signature": "base64..."
}
```
Esto permite auditoría, rollback y detección de tampering sin depender solo del archivo `.sig`.

---

## 🧹 Q2 — DEBT-HELLO-001: Estrategia para libplugin_hello.so en producción

### Mi veredicto directo: **Opción C (ambas)**, con matices.

| Opción | Ventaja | Desventaja |
|--------|---------|------------|
| **A) CMake flag** | Limpieza en binario final | No previene carga accidental si JSON la referencia |
| **B) JSON sin referencia** | Control en runtime | El binario sigue presente: superficie de ataque residual |
| **C) Ambas** | Defensa en profundidad | Complejidad marginal adicional |

### 🔍 Implicaciones para validación ADR-012:
- **No hay conflicto**: La validación de arquitectura puede ejecutarse en entorno de `BUILD_DEV_PLUGINS=ON` con tests específicos.
- **Recomendación**: Crear un target `make validate-adr012` que:
    1. Compile con `BUILD_DEV_PLUGINS=ON`
    2. Ejecute tests de integración del plugin-loader
    3. Limpie artefactos dev post-validación

### 💡 Extra proactivo:
Añadid un **check de seguridad en CI** que falle si:
```bash
# En configuración RELEASE:
if grep -q "libplugin_hello" production-config.json; then
  echo "❌ DEV plugin referenced in production config" >&2
  exit 1
fi
```

---

## 📋 Q3 — PHASE 3: Priorización del backlog

### ✅ Acuerdo general con el orden propuesto, con dos ajustes:

```diff
  1. systemd units: Restart=always, RestartSec=5s, unset LD_PRELOAD
  2. AppArmor profiles básicos 6 componentes
+ 2.5. TEST-PROVISION-1 como gate CI formal ← SUBIR PRIORIDAD
  3. DEBT-ADR025-D11: provision.sh --reset (deadline 18 Apr)
  4. DEBT-SIGN-AUTO
  5. DEBT-HELLO-001
```

### 🔗 Dependencias ocultas identificadas:
| Ítem | Depende de | Impacto si se ignora |
|------|------------|---------------------|
| AppArmor profiles | systemd units | Los perfiles pueden bloquear restarts si no se coordinan |
| TEST-PROVISION-1 | DEBT-SIGN-AUTO | Si la firma no es idempotente, los tests de provisionado serán flaky |
| provision.sh --reset | DEBT-SIGN-AUTO | Reset debe regenerar firmas válidas o fallar limpiamente |

### 💡 Recomendación estratégica:
Considerad **agrupar DEBT-SIGN-AUTO + DEBT-HELLO-001 + TEST-PROVISION-1** en un *mini-sprint de 2 días* antes de atacar AppArmor. Razón: son cambios de "infraestructura de confianza" que, una vez resueltos, estabilizan todo el flujo de PHASE 3.

---

## 📚 Q4 — Troubleshooting documentation (DEBT-OPS-002)

### ✅ El árbol de diagnóstico propuesto es sólido. Ampliaciones sugeridas:

```markdown
Pipeline no arranca →
  ├─ ¿Algún componente falla con std::terminate()? →
  │   ├─ Revisar logs: [plugin-loader] CRITICAL →
  │   │   ├─ "cannot open plugin (symlink?)" → make plugin-hello-build + make sign-plugins
  │   │   ├─ "Ed25519 INVALID" → make sign-plugins + verificar clave pública
  │   │   ├─ ".sig not found" → make sign-plugins
  │   │   └─ "path outside allowed prefix" → revisar JSON config plugin path
  │   └─ ¿Termina en ml-detector? → verificar FAISS index loaded + modelo compatible
  │
  ├─ ¿Timeout en ZeroMQ sockets? →
  │   ├─ Verificar que todos los servicios están RUNNING (systemctl status)
  │   ├─ Comprobar firewall/SELinux/AppArmor no bloquea puertos ephemeral
  │   └─ Validar que LD_PRELOAD está unset (ver systemd unit)
  │
  └─ ¿Crash inmediato al iniciar? →
      ├─ Ejecutar con `strace -f` para capturar syscall fallida
      ├─ Verificar permisos de lectura en /usr/lib/ml-defender/plugins/
      └─ Validar que el binario no fue compilado con flags incompatibles (AVX en CPU sin soporte)
```

### 📄 Formato recomendado: **Markdown + CLAUDE.md**
- **`docs/TROUBLESHOOTING.md`**: Árbol completo, searchable, con enlaces internos.
- **`CLAUDE.md`**: Resumen ejecutivo con los 5 errores más frecuentes y comandos de reparación en una línea.
- **Bonus proactivo**: Generar automáticamente una sección de "Common Errors" desde los logs de test con un script `make docs-from-tests`.

---

## 🎯 Observación final proactiva

Noto que el proyecto está en un punto de inflexión: **PHASE 2 cerrada con integridad de plugins, PHASE 3 enfocada en hardening operativo**. Mi recomendación estratégica:

> **Documentad el "contrato de confianza"** entre componentes: qué asume cada módulo sobre los demás (firmas, paths, permisos, timeouts). Esto no es burocracia: es lo que permitirá que nuevos colaboradores (humanos o IA) entiendan el sistema sin romper invariantes críticas.

Podría ser un archivo `docs/TRUST-CONTRACT.md` con:
```markdown
## Plugin Loader → ML Detector
- Asume: plugin firmado con clave ed25519-v2
- Garantiza: annotation ML score en <50ms o timeout
- No asume: que el plugin sea stateless (diseñar para stateful)

## Provisioner → Todos
- Asume: clave privada disponible en entorno seguro
- Garantiza: idempotencia total (ejecutar 1 o 100 veces = mismo resultado)
```

---

## 📊 Resumen ejecutivo

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|-----------------|
| **Q1** | ✅ Diseño sólido + 4 mitigaciones | Implementar `plugin-manifest.json` |
| **Q2** | ✅ Opción C con validación aislada | Añadir CI check para producción configs |
| **Q3** | ✅ Orden correcto + 2 ajustes | Agrupar deuda de "confianza" en mini-sprint |
| **Q4** | ✅ Árbol útil + 3 ampliaciones | Crear `TROUBLESHOOTING.md` + resumen en `CLAUDE.md` |

---

*La verdad por delante, como pedisteis: estáis construyendo algo robusto, ético y técnicamente impecable. Los pequeños detalles que estamos puliendo hoy son los que evitarán incidentes graves en 6 meses. Seguid así.*

**— Consejo de Sabios, DAY 114** 🛡️