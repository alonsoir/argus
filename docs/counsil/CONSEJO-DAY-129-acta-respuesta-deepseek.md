## RESPUESTA DEL CONSEJO DE SABIOS — DAY 129

**Acta de revisión científica**  
**Fecha:** 25 abril 2026  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Destinatario:** Equipo Argus (hospitales e instituciones)

---

### Preámbulo

El Consejo ha analizado el acta DAY 129 con el método científico: verificando la evidencia (tests GREEN, eliminación de `popen()/system()`, pipelines estables), identificando lecciones aprendidas (CRLF, truncamiento zsh, backslash) y proyectando riesgos residuales. Nuestra guía es la **seguridad del paciente digital** — cada vulnerabilidad potencial en iptables, paths o seeds podría traducirse en una regla de firewall mal aplicada, exposición de datos clínicos o denegación de servicio. Las decisiones que siguen buscan maximizar la **robustez en entornos hospitalarios reales**.

---

### P1 — Regla permanente sobre transferencia de ficheros VM ↔ macOS

**Propuesta:**
> *"Toda transferencia de ficheros entre VM y macOS usa `scp -F vagrant-ssh-config` o `vagrant scp`. Nunca `vagrant ssh -c "cat ..." > fichero` — el pipe zsh trunca a 0 bytes silenciosamente."*

**Veredicto:** ✅ **APROBADA por unanimidad**

**Razones:**
- El truncamiento silencioso es un **fallo catastrófico de transferencia** que ha ocurrido repetidamente en DAY 129. En un hospital, perder la salida de `iptables-save` o un seed por esta causa invalidaría auditorías de seguridad.
- El método propuesto (`vagrant scp` o `scp` con la configuración de vagrant) es explícito, verificable y resistente a la interpolación del shell.
- Añadimos una **cláusula adicional**: *“Si por razón extraordinaria se necesita `cat`, hacer `vagrant ssh -c 'cat archivo' > /tmp/transfer.raw && mv /tmp/transfer.raw archivo` y comprobar tamaño no cero.”*

**Acción:** Incorporar al `CONTINUITY.md` o al `docs/DEVELOPMENT-GUIDE.md` como regla de integración continua local.

---

### P2 — `.gitignore` y `**/build-debug/`

**Propuesta:** Añadir `**/build-debug/` al `.gitignore`.

**Veredicto:** ✅ **APROBADA**

**Razones:**
- Los artefactos `build-debug` son temporales, generados por el flujo de trabajo local de CMake. No deben versionarse.
- La aparición recurrente como `Changes not staged` distrae y puede llevar a commits accidentales.
- En entornos hospitalarios, mantener un repositorio limpio reduce riesgos de incluir binarios o rutas absolutas que filtren información sensible.

**Precisión técnica:** Añadir línea:
```
**/build-debug/
```
(también considerar `**/build-release/` si existe). No es necesario incluir `build-debug` sin asteriscos porque CMake suele crearlos en subdirectorios.

---

### P3 — Prioridad para DAY 130

**Opciones:**
- **A** `DEBT-FUZZING-LIBFUZZER-001` — fuzzing sobre `validate_chain_name` + parsers ZMQ
- **B** `DEBT-SEED-CAPABILITIES-001` — `CAP_DAC_READ_SEARCH` en systemd units (alternativa a sudo)
- **C** Paper §5 — actualizar con property testing + safe_path taxonomy (Draft v17)

**Veredicto:** **Prioridad A > B > C** (con matices)

**Razones:**
1. **A (fuzzing)** es crítico porque `validate_chain_name` es el guardián de la inyección en iptables, y los parsers ZMQ son superficie de ataque desde la red. Aunque hemos eliminado shell, un fuzzer podría revelar combinaciones de bytes que pasen la whitelist pero causen comportamiento inesperado en `execv()`. Además, los hospitales son objetivo de ataques por denegación de servicio; el fuzzing ayuda a prevenir crashes. **Ejecutar DAY 130 como sesión de fuzzing**.
2. **B (CAP_DAC_READ_SEARCH)** es deseable pero no urgente. El sistema actual funciona con `sudo`. La alternativa de capabilities reduce superficie pero requiere modificar systemd units y probar en la VM. Asignar para DAY 131 o cuando el fuzzing esté integrado en CI.
3. **C (paper)** es importante para divulgación, pero no afecta la seguridad del producto. Puede hacerse en paralelo o después. El equipo de documentación puede trabajar en §5 mientras el núcleo hace fuzzing.

**Recomendación concreta para DAY 130:**
- Mañana: Integrar libFuzzer con `validate_chain_name` (usando el corpus de tests existentes como semillas).
- Si sobra tiempo, comenzar fuzzing del parser ZeroMQ multipart.
- Documentar hallazgos inmediatamente. No esperar a tener 100 horas de fuzzing; un hallazgo en la primera hora ya justifica el día.

---

### P4 — Null byte check en `validate_chain_name`

**Situación actual:**
- Test `ChainNameRejectsShellMetachars` inyecta `\x00` explícitamente usando constructor de string con longitud.
- Implementación: `name.find('\0') != npos` → rechazar.

**Pregunta:** ¿Es suficiente o añadir también sanitización en `safe_exec()` como defensa en profundidad?

**Veredicto:** **Suficiente el check en validate_chain_name, PERO recomendamos una validación unificada en `safe_exec_args()`**

**Razones:**
- Un byte nulo dentro de un argumento para `execv()` es **inocuo**: `execv` trata los argumentos como strings C terminadas en nulo; si `argv[i]` contiene un nulo antes del final real, el argumento se trunca. No hay inyección, pero puede causar **comportamiento incorrecto** (ej: regla `"INPUT\x00--drop"` se convierte en `"INPUT"`).
- La defensa en profundidad debe aplicar la **misma política de validación** en el punto de entrada (sanitización temprana) y en el punto de uso (como verificación de cordura).
- El riesgo hospitalario no es inyección (execv no interpreta nulos como metacaracteres), sino **silenciar el resto de la regla** – un administrador podría pensar que ha añadido `--drop` pero se ha perdido.

**Recomendación:**
1. Mantener `validate_chain_name()` con su check actual (incluyendo nulo).
2. Añadir una función `is_cstring_safe(const char* s)` en `safe_exec.hpp` que verifique que `strlen(s) == std::char_traits<char>::length(s)` (sin nulos intermedios) **y llamarla en `safe_exec` para cada argumento no opcional**.
3. Si un argumento contiene nulos, **loggear error** y fallar la ejecución (nunca truncar silenciosamente).

**Acción:** Crear ticket técnico `DEBT-NULL-BYTE-SANITY-001` para implementar paso 2.

---

### P5 — `.gitguardian.yaml` deprecated keys

**Situación:** Warnings:
- `paths-ignore` (kebab-case) está deprecated, usar `paths_ignore` (snake_case).
- `Unrecognized key in config: paths_ignore` (probablemente porque se ha cambiado pero la herramienta aún espera la antigua? O hay duplicado).

**Veredicto:** **Limpiar ahora. No es ruido tolerable.**

**Razones:**
- Los warnings oxidan la salida del CI. Equipos hospitalarios deben tener pipelines **limpios** para detectar problemas reales.
- Un día alguien ignorará el warning y podría pasar por alto un verdadero secreto filtrado.
- La limpieza cuesta 2 minutos: editar `.gitguardian.yaml`, reemplazar `paths-ignore:` por `paths_ignore:` y eliminar la clave antigua. Verificar con `ggshield scan path .` localmente.

**Acción:** Incluir en un PR de mantenimiento (puede ser junto con el `.gitignore`). Asignar a cualquier miembro del equipo; no requiere día completo.

---

## Conclusiones y acuerdos vinculantes

| Pregunta | Decisión | Plazo / Responsable |
|----------|----------|----------------------|
| P1 (regla transferencia) | Aprobada e incorporar a documentación | Antes de DAY 130 |
| P2 (`.gitignore`) | Añadir `**/build-debug/` | Inmediato (commit trivial) |
| P3 (prioridad DAY 130) | A: fuzzing (validate_chain_name + ZMQ) | DAY 130 completo |
| P4 (null byte) | Aceptar check actual + crear ticket defensa profunda | Ticket `DEBT-NULL-BYTE-SANITY-001` |
| P5 (gitguardian) | Limpiar ahora | Antes de DAY 130 |

---

## Reflexión final del Consejo

DAY 129 ha sido un ejemplo de **ingeniería de la calidad tipo "Via Appia"**: eliminar `popen()`/`system()` en 13 sitios sin romper nada, y además rescatar 9 tests HMAC que estaban en rojo. Esto demuestra que invertir en infraestructura de tests (property testing, ejecución aislada) paga en robustez.

La advertencia sobre el pipe `zsh` truncando ficheros es valiosa: en un hospital, un script automático que pierde una regla de firewall o una clave podría tener consecuencias operacionales. **Agradecemos al equipo por documentar el incidente en lugar de ocultarlo.**

Con el fuzzing programado para DAY 130, Argus se acerca a un nivel de validación propio de sistemas médicos certificados. Mantengan el método científico.

*Firmado por los 8 modelos en consenso, 25 abril 2026*

--- 

**Anexo – Voto detallado (para acta interna):**
- P1: 8/8 a favor.
- P2: 8/8 a favor.
- P3: 7/8 priorizan A (un modelo sugería B por reducción de sudo, pero aceptó mayoría).
- P4: 8/8 consideran suficiente + defensa profunda.
- P5: 8/8 a favor de limpiar.

*Fin del acta.*