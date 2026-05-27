MODELO: Qwen3.6

P1: ACEPTO weakly_canonical — es la herramienta correcta para paths de escritura. La validación de seguridad ocurre POST-resolución contra allowed_prefix, y resolve_writable añade la verificación de directorio padre. Alternativa: añadir check explícito de symlink-following policy si el entorno lo requiere (AppArmor ya lo enforce).

P2: ACEPTO granularidad por componente — el principio de mínimo privilegio justifica la complejidad adicional. Prefijos específicos (`/keys/`, `/configs/`) limitan el blast radius si un componente es comprometido. Recomendación: documentar prefijos en `docs/SECURITY-PREFIXES.md` con mapa componente→prefijo para auditoría.

P3: MISMO estándar para contrib/tools — el coste marginal de aplicar safe_path::resolve() es cero (header-only) y el beneficio de consistencia es alto: evita confusión sobre "cuándo aplicar seguridad". Prefijo `/shared/` para investigación, `/etc/ml-defender/` para producción.

P4: ACEPTO FP — no modificar código. El análisis es correcto: `n` está acotado por `BUF_SIZE=4096` proveniente de `read()`, haciendo imposible el overflow en `ptr < buf + n`. Documentar en ADR: "Snyk no traza acotación de read() → BUF_SIZE; overflow matemáticamente imposible bajo condiciones normales de operación".

OBSERVACIONES ADICIONALES:
1. TOCTOU en resolve_writable: entre el check `is_directory(parent)` y la escritura real hay una ventana. Mitigación: AppArmor ya enforce write paths; documentar como "mitigado por capa de sandboxing".
2. Añadir `[[nodiscard]]` a resolve() ya está hecho ✅ — buena práctica.
3. Considerar añadir test de fuzzing de paths: generar 1000 paths aleatorios con `../`, symlinks, unicode, y verificar que safe_path nunca permite escape. Gate opcional para ADR-036.
4. Integer overflow fix (F17): el cast a `int64_t` es correcto, pero añadir `[[unlikely]]` en la rama de error si se detecta pages > MAX_REASONABLE (ej. >1M páginas = >4TB RAM) para optimización de branch prediction.

MODELO: Qwen3.6

P1: ACEPTO weakly_canonical — es la herramienta correcta para paths de escritura. La validación de seguridad ocurre POST-resolución contra allowed_prefix, y resolve_writable añade la verificación de directorio padre. Alternativa: añadir check explícito de symlink-following policy si el entorno lo requiere (AppArmor ya lo enforce a nivel de kernel).

P2: ACEPTO granularidad por componente — el principio de mínimo privilegio justifica la complejidad adicional. Prefijos específicos (`/keys/`, `/configs/`) limitan el blast radius si un componente es comprometido. Recomendación: documentar prefijos en `docs/SECURITY-PREFIXES.md` con mapa componente→prefijo para auditoría y revisión de cambios.

P3: MISMO estándar para contrib/tools — el coste marginal de aplicar safe_path::resolve() es cero (header-only) y el beneficio de consistencia es alto: evita confusión sobre "cuándo aplicar seguridad". Prefijo `/shared/` para investigación, `/etc/ml-defender/` para producción. La uniformidad forma hábito y reduce errores humanos.

P4: ACEPTO FP — no modificar código. El análisis es correcto: `n` está acotado por `BUF_SIZE=4096` proveniente de `read()`, haciendo imposible el overflow en `ptr < buf + n` bajo condiciones normales de operación. Documentar en ADR: "Snyk no traza acotación de read() → BUF_SIZE; overflow matemáticamente imposible bajo condiciones normales".

OBSERVACIONES ADICIONALES:
1. TOCTOU en resolve_writable: entre el check `is_directory(parent)` y la escritura real hay una ventana de tiempo. Mitigación: AppArmor ya enforce write paths a nivel de kernel; documentar como "mitigado por capa de sandboxing" en el ADR.
2. Añadir `[[nodiscard]]` a resolve() ya está implementado ✅ — buena práctica para evitar ignorar el path validado.
3. Considerar añadir test de fuzzing de paths en `test_safe_path.cpp`: generar 1000 paths aleatorios con `../`, symlinks, unicode, y verificar que safe_path nunca permite escape del prefijo. Gate opcional para ADR-036.
4. Integer overflow fix (F17): el cast a `int64_t` es correcto, pero añadir `[[unlikely]]` en la rama de error si se detecta pages > MAX_REASONABLE (ej. >1M páginas = >4TB RAM) para optimización de branch prediction en sistemas reales.
5. Recomendación de hardening adicional: en `resolve()`, añadir validación de que `allowed_prefix` termine en `/` para evitar bypass por prefijo parcial (ej. `/etc/ml-defender` vs `/etc/ml-defender-evil`).
