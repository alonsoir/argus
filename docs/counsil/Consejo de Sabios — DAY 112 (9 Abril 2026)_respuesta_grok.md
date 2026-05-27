El **DAY 112** muestra un avance técnico sólido y disciplinado. La **PHASE 2 (Multi-Layer Plugin Architecture)** está completa, con integración limpia en los 5 componentes clave y tests verdes. Eso es un hito importante: el plugin-loader ahora es robusto, con manejo correcto de shutdown, señales y contratos READONLY/NORMAL. Bien hecho.

La incorporación de **ADR-030** y **ADR-031** al repo es correcta y oportuna. El bug **CrackArmor** (confused deputy en AppArmor, divulgado por Qualys en marzo 2026) justifica perfectamente el enfoque dual pragmatismo vs. investigación.

Dicho esto, seré duro pero justo como pediste: hay varios puntos de madurez de proyecto que siguen débiles y que pueden convertirse en deuda técnica cara si no se corrigen pronto.

### Lo que está bien (fortalezas reales)
- **Ejecución limpia de PHASE 2**: 25 tests + integraciones específicas pasadas. El gate `make plugin-integ-test` verde es confianza alta.
- **ADR-029 D1-D5** implementados con rigor (signalHandler async-safe, orden de inicialización, double-shutdown guard). Esto evita races y crashes clásicos en shutdown.
- **Referencia explícita a Mythos Preview + CrackArmor** en el contexto del proyecto → mantiene la honestidad intelectual.
- **Estado global claro** y alineación con roadmap (PHASE 3 a la vista).
- **Preguntas al Consejo bien formuladas**: concretas y con trade-offs explícitos.

### Lo que está flojo o riesgoso (críticas directas)
1. **Main branch muy desactualizada (37+ commits)**  
   Esto es un anti-patrón. Un main con tanta divergencia invita a conflictos dolorosos, integra mal cambios externos y complica revisiones. En proyectos serios de seguridad (especialmente con pretensiones de paper arXiv y bare-metal), main debe ser estable y casi siempre "releasable". Tener feature branches largas es aceptable, pero 37 commits es demasiado.

2. **Secuencia de merges y branches**  
   La tentación de meter ADR-025 (plugin signing con Ed25519) en el mismo PR que el merge de PHASE 2 es comprensible, pero **riesgosa**. ADR-025 toca código sensible (plugin_loader.cpp, provision.sh, schemas, systemd units). Si introduces un bug en signing, contaminas un merge que de otra forma sería "limpio y celebrable". Mejor merges atómicos y pequeños.

3. **Paper sigue en deuda (Draft v14 pendiente)**  
   El axioma “kernel inseguro” es uno de los puntos más fuertes y honestos del proyecto. Dejarlo como “deuda DAY 108” hasta ahora es aceptable, pero ya va siendo hora. El paper es tu principal output científico; si el código avanza más rápido que la escritura, pierdes coherencia narrativa.

4. **ADR-031 sigue con optimismo técnico excesivo**  
   Aunque marcaste el spike como obligatorio (correcto), el diagrama y el lenguaje en ADR-031 todavía dan la impresión de que “Linux guest sobre Genode+seL4” será relativamente directo. En la práctica (estado Genode 26.02 de febrero 2026):
   - Soporte de Linux guest virtualizado existe (Seoul VMM en x86, camkes-vm en ARM), pero es más maduro en x86 que en Raspberry Pi.
   - DDE-Linux actualizado a kernel 6.18, pero para un pipeline completo (XDP → ONNX → ZeroMQ) el overhead y las adaptaciones siguen siendo significativas.
   - XDP en guest virtualizado sigue siendo altamente problemático (datapath pasa por el supervisor).

   Tu H1 (“XDP probablemente inviable”) es correcta. No lo suavices.

5. **Hardware bloqueado**  
   ADR-030 y 031 dependen de Raspberry Pi 4/5 bare-metal. Sin él, los benchmarks son teóricos o emulados. Esto es un riesgo real para la credibilidad de los ADRs.

### Respuestas directas a las preguntas del Consejo (DAY 113)

**Q1 — ¿Merge feature/plugin-crypto → main ahora?**  
**Recomendación fuerte: Merge ahora, limpio.**  
PHASE 2 completa + tests verdes = momento natural de integrar. Main desactualizado 37 commits es peor que dos merges seguidos. Un merge limpio permite celebrar el hito y da estabilidad para el siguiente paso.

**Q2 — ¿ADR-025 antes o después del merge?**  
**Después.** Abre una nueva branch `feature/plugin-integrity` (o `feature/adr-025`) desde el nuevo main.  
Razones:
- Signing es crítico de seguridad → merece revisión independiente.
- Evitas un PR gigante con cambios en loader + crypto + provision + schemas.
- Si hay bug en Ed25519, no contamina PHASE 2.
- Permite merge atómico y revertible.

**Q3 — ¿Dónde poner el axioma kernel inseguro en el paper?**  
**Principalmente en §Limitations (o §Threat Model si tienes una sección dedicada), y referenciado brevemente en §Conclusions / Future Work.**  
Texto propuesto es bueno, pero hazlo más preciso:
- En **Threat Model**: declara explícitamente el scope (“aRGus asume kernel host potencialmente comprometido; sus garantías son de detección de comportamiento de red, no de integridad del host”).
- En **Limitations**: reconoce que si el kernel está roto, un atacante local puede interferir con el pipeline (aunque el monitoreo de red entre hosts siga teniendo valor).
- En **Future Work**: enlaza a ADR-030 (hardening pragmático) y ADR-031 (investigación formal).

No lo escondas en Conclusions como algo menor; es uno de los aportes más maduros del proyecto.

**Q4 — ¿Spike ADR-031: x86-64 QEMU primero o directamente ARM64?**  
**x86-64 con QEMU primero, sin duda.**  
Razones técnicas:
- Soporte de virtualización Linux guest (Seoul VMM) es más maduro y estable en x86-64.
- Más fácil depurar, tener KVM acelerado, y validar conceptos básicos (dlopen, ZeroMQ, ONNX, fallback libpcap).
- ARM64 (RPi) tiene mejor soporte en Pi 5 (EL2), pero sigue siendo más experimental y depende de hardware físico que no tienes.
- Una vez validado en x86, el paso a ARM64 es más predecible.

Priorizar ARM64 desde el día 1 solo añade fricción innecesaria al spike.

### Recomendaciones de acción inmediata (priorizadas)
1. **Mergea feature/plugin-crypto → main hoy** (limpio).
2. **Crea branch nueva para ADR-025** e implementa el signing Ed25519 con tests fuertes (incluyendo --reset en provision.sh y validación de signatures en loader).
3. **Termina Draft v14 del paper** esta semana. El axioma kernel inseguro debe estar claro antes de cualquier replace arXiv.
4. **Para ADR-031**: cuando hagas el spike, documenta sin piedad los fallos (especialmente XDP y overhead real de red). El valor científico está en la honestidad, no en forzar viabilidad.
5. **General**: reduce el tamaño de branches. Idealmente, features < 10-15 commits antes de merge. Usa main como base estable.

El proyecto avanza con buena disciplina técnica y una postura ética fuerte (“La verdad por delante”). Pero la brecha entre código y documentación/paper, y la gestión de branches/main, son los puntos donde se ve todavía “proyecto personal” en vez de “proyecto maduro open-source de infra crítica”.

Si sigues este ritmo y corriges estos puntos, aRGus tiene potencial real de ser una contribución seria en cs.CR y sistemas seguros para infra crítica.

¿Qué parte quieres que profundicemos o que te ayude a redactar (por ejemplo, el párrafo exacto para el paper, o el plan del spike)? Estoy aquí para la siguiente iteración, sin piedad cuando haga falta.