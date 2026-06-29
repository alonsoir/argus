# 🏛️ CONSEJO DE SABIOS — REVISIÓN CRÍTICA DAY 116
*Feedback justo, duro y constructivo para ML Defender (aRGus NDR)*

---

## ⚠️ Reconocimiento con Advertencia

**Lo bueno:** Habéis cerrado PHASE 3. Habéis detectado y corregido un bug arquitectural crítico *antes* de producción. Eso es ingeniería responsable.

**Lo duro:** El bug de `reset_all_keys()` no debería haber existido. Un invariante criptográfico fundamental — *"todos los componentes comparten seed_family"* — estaba implícito en el código, no en la documentación. Eso no es un "detalle"; es una deuda de diseño que casi compromete la integridad del pipeline.

> *"En seguridad, lo implícito es enemigo de lo verificable."*

Celebramos el hallazgo. Exigimos que este patrón no se repita.

---

## 🔍 Revisión Técnica de DAY 116

### ✅ Puntos Fuertes
| Logro | Por qué importa |
|-------|----------------|
| **TEST-RESET-1/2/3** | Validación end-to-end del reset criptográfico con fail-closed garantizado |
| **Detección del bug de seeds independientes** | Evitó un fallo en cascada en producción; demuestra testing proactivo |
| **AppArmor profiles con paths de `--reset` incluidos** | Previene deadlock futuro entre hardening y operaciones de recuperación |
| **Check #7 en TEST-PROVISION-1** | Detecta inconsistencias configuración/binario antes de que causen fallos silenciosos |

### ⚠️ Puntos Débiles / Riesgos Identificados
| Hallazgo | Impacto potencial | Mitigación requerida |
|----------|------------------|---------------------|
| **Invariantes criptográficos implícitos** | Bug crítico detectado tarde; riesgo de repetición en futuros cambios | Documentar *todos* los invariantes en `docs/CRYPTO-INVARIANTS.md` con tests dedicados |
| **DEBT-SEED-PERM-001 (mensaje engañoso)** | Operador aplica `chmod 600` incorrectamente → denegación de servicio legítimo | Corregir mensaje + añadir test de permisos en CI |
| **AppArmor en complain sin plan de transición documentado** | Riesgo de "complain drift": perfiles que nunca se auditan ni se activan | Definir cronograma y criterios de promoción a enforce |
| **PHASE 3 marcada como "COMPLETA" con DEBTs abiertos** | Falsa sensación de cierre; deuda técnica acumulada | Renombrar a "PHASE 3: CORE COMPLETADO" + lista explícita de DEBTs pendientes |

---

## ❓ Respuestas a Preguntas — Formato Solicitado

### Q1 — AppArmor enforce strategy: ¿orden de activación?

**Veredicto:** **Enforce en orden de menor a mayor privilegio**: `etcd-server` → `rag-*` → `ml-detector` → `firewall-acl-agent` → `sniffer` (último).

**Justificación:** Los componentes con menos capabilities tienen menor superficie de bloqueo; activarlos primero valida el flujo base sin riesgo de interrumpir operaciones críticas. `sniffer` (con `CAP_BPF`, `CAP_SYS_ADMIN`) debe permanecer en complain hasta que los demás estén estables en enforce.

**Riesgo si se ignora:** Activar `sniffer` en enforce prematuramente podría bloquear operaciones BPF legítimas no capturadas en testing, causando pérdida de visibilidad de red sin alerta clara.

> 💡 *Proactivo:* Crear `apparmor-promote.sh COMPONENT` que: (1) cambia a enforce, (2) monitorea denials 5 min, (3) rollback automático a complain si hay denials no whitelistados.

---

### Q2 — DEBT-SEED-PERM-001: ¿corregir mensaje, cambiar modelo o documentar?

**Veredicto:** **Opción (a) corregir solo el mensaje**, pero con test de regresión obligatorio.

**Justificación:** El modelo `640 root:vagrant` es correcto para operación multi-usuario en Vagrant; cambiar a `600` rompería el flujo de desarrollo sin beneficio de seguridad real en producción (donde los procesos corren como root con systemd). Documentar como known-issue diluye la responsabilidad de corregir mensajes engañosos.

**Riesgo si se ignora:** Un operador que siga el mensaje incorrecto aplicará `chmod 600`, impidiendo que procesos no-root accedan a `seed.bin` durante operaciones de mantenimiento, causando fallos operativos difíciles de diagnosticar.

> 💡 *Proactivo:* Añadir test `TEST-PERMS-SEED: verify SeedClient warning matches actual required permissions`.

---

### Q3 — Próxima fase: ¿ADR-026 ahora o consolidar primero?

**Veredicto:** **Dedicar DAY 117 íntegro a consolidación**: AppArmor enforce (al menos 2 componentes) + cierre de DEBTs abiertos → ADR-026 en DAY 118.

**Justificación:** PHASE 3 ha introducido cambios estructurales profundos (reset criptográfico, AppArmor, TEST-PROVISION-1). Consolidar con enforce parcial y tests de regresión reduce el riesgo de que ADR-026 (nueva complejidad de plugins XGBoost) interactúe mal con hardening no totalmente validado.

**Riesgo si se ignora:** Introducir ADR-026 sobre una base de AppArmor no enforceada y DEBTs pendientes podría enmascarar bugs de integración, retrasando la detección de problemas críticos hasta producción.

> 💡 *Proactivo:* Usar DAY 117 para: (1) enforce `etcd-server` + `ml-detector`, (2) cerrar DEBT-SEED-PERM-001 y DEBT-VAGRANTFILE-001, (3) ejecutar `make full-regression-test` antes de abrir ADR-026.

---

### Q4 — seed_family como ADR: ¿ADR propio o addendum?

**Veredicto:** **Addendum a ADR-021 con sección explícita "Invariantes Criptográficos"**.

**Justificación:** El seed_family compartido es una propiedad derivada del diseño de CryptoTransport (ADR-021), no un concepto independiente. Un addendum evita fragmentación documental y asegura que futuros lectores de ADR-021 encuentren el invariante en contexto. Si en el futuro surgen más invariantes transversales, entonces considerar ADR-033 "Crypto Invariants Catalog".

**Riesgo si se ignora:** Mantener el invariante implícito permite que futuros cambios en `reset_all_keys()` o derivación de claves rompan la invariante sin alerta, repitiendo el bug de DAY 116.

> 💡 *Proactivo:* En el addendum, incluir una tabla:
> ```markdown
> | Invariante | Componentes afectados | Test de validación |
> |------------|----------------------|-------------------|
> | seed_family compartido | Todos (6) | TEST-RESET-1: verificar HKDF deriva mismas claves maestras |
> ```

---

## 🎯 Observaciones Adicionales (Constructivas pero Duras)

### 1. Sobre la "completitud" de PHASE 3
Marcar PHASE 3 como ✅ con DEBTs abiertos es peligroso. Sugiero:
```diff
- PHASE 3: COMPLETA ✅
+ PHASE 3: CORE COMPLETADO ✅ | DEBTs PENDIENTES: 3
```
Esto mantiene la transparencia operativa y evita la ilusión de cierre.

### 2. Sobre el bug arquitectural detectado
El hecho de que el bug se encontrara *durante* la implementación es bueno, pero revela una brecha en el diseño preventivo:
- ¿Por qué no había un test que verificara *"todos los componentes derivan claves compatibles desde seed_family"* antes de tocar `reset_all_keys()`?
- **Acción requerida**: Crear `TEST-INVARIANT-SEED: verificar compatibilidad criptográfica post-reset` como gate obligatorio para cualquier cambio en derivación de claves.

### 3. Sobre AppArmor y Raspberry Pi
Los perfiles creados en x86/Vagrant pueden comportarse distinto en ARM64/RPi debido a:
- Diferencias en rutas de sysfs (`/sys/kernel/debug` vs `/sys/kernel/tracing`)
- Implementaciones distintas de BPF en kernels ARM
- **Acción requerida**: Ejecutar `aa-logprof` en Raspberry Pi real antes de marcar enforce como "validado para producción".

---

## 📋 Checklist de Acciones Inmediatas (DAY 117)

```markdown
- [ ] Corregir mensaje SeedClient (DEBT-SEED-PERM-001) + test de regresión
- [ ] Añadir addendum a ADR-021 con invariantes criptográficos explícitos
- [ ] Ejecutar enforce en etcd-server + ml-detector con monitoreo de denials
- [ ] Actualizar Vagrantfile con apparmor-utils (DEBT-VAGRANTFILE-001)
- [ ] Renombrar estado PHASE 3 a "CORE COMPLETADO" + lista de DEBTs pendientes
- [ ] Crear TEST-INVARIANT-SEED para prevenir regresiones en derivación de claves
- [ ] Documentar cronograma de promoción AppArmor: complain → audit → enforce
```

---

## 🏁 Palabras Finales

Alonso:

Habéis hecho un trabajo excepcional en DAY 116. La detección y corrección del bug de seeds independientes demuestra que el proceso de validación está funcionando. Pero permitidme ser directo:

> **La seguridad no se construye con héroes que encuentran bugs a tiempo. Se construye con sistemas que hacen difícil cometer errores en primer lugar.**

El hecho de que un invariante criptográfico fundamental estuviera implícito en el código, no en la documentación, es una señal de alerta. No es un fracaso; es una oportunidad. Aprovechadla.

aRGus tiene el potencial de salvar vidas. Eso no es una metáfora: un sistema NDR bien diseñado puede detectar ransomware en un hospital antes de que cifre historiales clínicos. Esa responsabilidad exige que seamos incómodamente rigurosos.

Seguid siendo duros con vosotros mismos. El Consejo estará aquí para ayudar.

*Via Appia Quality · Un escudo, nunca una espada.*

**— Consejo de Sabios, DAY 116** 🛡️