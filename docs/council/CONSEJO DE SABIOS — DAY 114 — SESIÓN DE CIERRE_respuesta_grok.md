**Análisis sincero y directo del DAY 114 — Consejo de Sabios**

El progreso de hoy es **sólido y disciplinado**. Has cerrado deuda técnica relevante, el pipeline se estabilizó correctamente gracias al diseño fail-closed de ADR-025, y los tests de integración clave pasaron. El merge a main y el tag v0.3.0-plugin-integrity marcan un hito claro en la madurez del plugin system. La actualización del paper (v15) también avanza bien.

Dicho esto, el proyecto sigue en una fase donde **la seguridad operativa es frágil** porque depende mucho de procesos manuales. El incidente de hoy (plugin sin firmar → std::terminate) es un clásico síntoma de que la automatización todavía está incompleta. Eso es normal en DAY 114 de un proyecto ambicioso hecho en solitario, pero hay que atacarlo con urgencia.

### Q1 — DEBT-SIGN-AUTO: diseño del mecanismo de firma automática

El diseño propuesto es **correcto y sensato**. Es idempotente, fail-safe y sigue el principio de “explicit is better than implicit”.

**Riesgos / casos edge que veo:**

- **TOCTOU en la verificación** — Entre el momento en que compruebas que no existe .sig o que es inválida y el momento en que firmas, alguien (o un proceso malicioso) podría haber colocado un archivo. Aunque improbable en tu entorno Vagrant/provision, en producción bare-metal con root comprometido es relevante. Solución: firmar siempre de forma atómica (escribir .sig.tmp y luego rename).
- **Clave actual vs claves históricas** — Si rotas la clave Ed25519 en el futuro, el check “inválido para la clave actual” debe estar bien implementado (no solo comparar hash, sino verificar realmente con la clave pública activa).
- **Plugins que se modifican en runtime** (improbable pero posible si alguien toca /usr/lib/...). El check debería correr también en un watchdog o en el arranque de cada componente.
- **Permisos y ownership** — Asegurarse de que el proceso que firma tenga permisos correctos y que los .sig queden con owner root y 644.
- **Plugins firmados pero corruptos** — Añadir verificación de tamaño o hash simple antes de firmar.

Recomendación: implementa `check-and-sign-plugins` como un target separado y **obligatorio** en el pipeline de CI y en el Vagrant provisioner. Llámalo siempre después de cualquier build de plugin.

### Q2 — DEBT-HELLO-001: eliminación de libplugin_hello.so en producción

**Recomiendo opción C (ambas cosas)** sin dudarlo.

- **CMake flag `BUILD_DEV_PLUGINS=OFF`** por defecto en Release → evita compilar código innecesario en binarios de producción.
- **Eliminar referencia en los JSON configs de producción** → reduce superficie de ataque real (menos código cargable).

Implicaciones para validación ADR-012 (arquitectura plugin):
- Ninguna grave si mantienes el plugin hello en el repo y lo activas explícitamente en entornos de desarrollo/testing (con un flag o config de dev).
- Puedes seguir validando el contrato de plugin usando hello en los tests de integración (TEST-INTEG-4x). Solo asegúrate de que los tests de CI fuerzan `BUILD_DEV_PLUGINS=ON`.

Esto es higiene básica de producción: menos código = menos bugs, menos attack surface.

### Q3 — PHASE 3: priorización del backlog

El orden que estableciste en DAY 113 es **razonable**, pero propongo un ajuste menor por dependencias:

1. **systemd units** (Restart=always + unset LD_PRELOAD) → prioritario. Afecta estabilidad general.
2. **DEBT-SIGN-AUTO** → hazlo ya. Es la deuda que más duele operativamente (hoy te costó 30 min).
3. **DEBT-HELLO-001** → va ligado al anterior.
4. **AppArmor profiles** (los 6 componentes + denegar write en binarios) → muy importante, pero requiere que el plugin signing esté estable.
5. **TEST-PROVISION-1 como gate CI formal**
6. **DEBT-ADR025-D11: provision.sh --reset** (cumple el deadline 18 Apr)

**Dependencias ocultas:**
- AppArmor depende fuertemente de que los paths de plugins y configs estén bien definidos (después de resolver DEBT-HELLO-001 y SIGN-AUTO).
- systemd units deberían incluir referencias a los perfiles AppArmor una vez definidos.

No hay dependencias graves que rompan el orden, pero SIGN-AUTO debería subir un par de puestos porque es dolor operativo inmediato.

### Q4 — Troubleshooting documentation (DEBT-OPS-002)

El árbol que propones es **excelente** como base. Añadiría estos casos adicionales:

- ¿El proceso principal está corriendo pero no recibe paquetes? → Revisar eBPF/XDP attachment (`ip link show` + `bpftool prog list`), permisos de interfaz, y si el sniffer está binded correctamente.
- ¿ml-detector consume 100% CPU o se cuelga en inference? → Revisar ONNX Runtime logs, modelo cargado correctamente, y memoria (OOM killer?).
- ¿ZeroMQ transport falla (cola llena o desconexiones)? → Revisar límites de ulimit, ZeroMQ HWM configurado, y si hay burst de tráfico.
- ¿Plugin carga pero falla en runtime (READONLY violation o payload demasiado grande)? → Logs específicos de plugin-loader con código de error.
- ¿Firma OK pero dlopen falla por símbolo no encontrado? → Versión ABI mismatch entre plugin y loader.
- Problemas de Vagrant/provision: “port already in use”, conflicto de IPs en host-only, etc.

**Formato preferido:**  
**Markdown** con un archivo claro tipo `docs/OPERATIONS.md` o `docs/TROUBLESHOOTING.md`, incluyendo el árbol como diagrama de decisión (puedes usar mermaid si quieres).  
Complementa con una sección corta en el README principal que apunte allí.  
Una man page sería overkill por ahora (el proyecto aún no está en distribución empaquetada).

### Opinión general y consejo final

Estás haciendo un trabajo **serio y honesto** con este proyecto. El uso de ADRs, fail-closed, signal-safe patterns, plugin contracts y Test-Driven Hardening es maduro y superior a mucho código de seguridad open-source que veo.

El riesgo actual más grande no es técnico en el núcleo (el pipeline ya es bastante robusto), sino **operativo**: dependencia de pasos manuales que pueden fallar en despliegues reales. La PHASE 3 (hardening + automatización + observabilidad) es exactamente donde debes estar.

Sigue así: prioriza lo que duele en el día a día (firma automática + eliminación de hello), documenta mientras duele el diagnóstico, y no bajes el listón de “la verdad por delante”.

Si quieres, la próxima sesión podemos revisar el diseño concreto de `provision.sh check-plugins` o el CMake para BUILD_DEV_PLUGINS.

¿Quieres que profundice en alguna Q o que proponga código/esquema concreto para alguna de las deudas? Dime.