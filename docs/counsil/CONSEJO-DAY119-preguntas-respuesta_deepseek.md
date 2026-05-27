## Dictamen del Consejo de Sabios — DAY 119

*Miembros del Consejo, hemos examinado el informe de DAY 119. Enhorabuena por la tenaz depuración del Vagrantfile y el Makefile. La lección operacional es lapidaria: «El Vagrantfile y el Makefile son la única fuente de verdad» debe grabarse en piedra (y en un `pre-commit` que rechace cambios manuales en la VM sin actualizar el provisioning).*

A continuación, nuestras respuestas a las preguntas, acompañadas de observaciones concretas y, cuando procede, fragmentos de código verificables.

---

## ✅ Lo que está bien (y es ejemplar)

1. **La tabla de 10 problemas resueltos** – Muestra madurez en la gestión de la deuda técnica. Cada fix está vinculado a una causa raíz.
2. **La secuencia canónica de 9 pasos** – Es clara, verificable y documentada. Esto es lo que permite que un nuevo desarrollador (o un auditor) reproduzca el entorno en una hora.
3. **`make sync-pubkey`** – Soluciona elegantemente el problema de la pubkey hardcodeada que ya había causado estragos en DAY 117. La lectura dinámica de la pubkey activa desde la VM es la solución correcta.
4. **El tratamiento de XGBoost** – El fallback apt → pip con timeout es realista para entornos hospitalarios.

---

## ⚠️ Lo que se puede mejorar (con código o comandos)

### 1. Falta un test de integración que valide la secuencia canónica
La secuencia de 9 pasos es manual. Sería muy fácil que un paso se omita o se ejecute fuera de orden. **Propuesta:** Añadir un nuevo test `make test-bootstrap` que ejecute la secuencia completa en una VM recién creada y falle si algún paso no devuelve `0` o si al final `make plugin-integ-test` no es verde.

```makefile
# Makefile
.PHONY: test-bootstrap
test-bootstrap: destroy up sync-pubkey set-build-profile install-systemd-units sign-plugins test-provision-1 pipeline-start pipeline-status plugin-integ-test
	@echo "✅ Bootstrap validation passed"
```

Además, integrarlo en `make test-all` condicionalmente (solo si `FORCE_BOOTSTRAP=1`), para no alargar la CI normal.

### 2. `sync-pubkey` no debería modificar CMakeLists.txt si la pubkey no ha cambiado
Actualmente `sync-pubkey` probablemente reescribe el archivo cada vez, lo que fuerza una recompilación innecesaria de `plugin-loader`. **Mejora:** Calcular el hash del contenido de `CMakeLists.txt` antes y después de la sustitución, y solo tocar el archivo si es diferente. Usar `sed -i` con bandera de backup condicional.

```bash
# Dentro de sync-pubkey
current_pubkey=$(vagrant ssh -c "cat /opt/ml-defender/etc/pubkey.hex" 2>/dev/null | tr -d '\r')
if ! grep -q "$current_pubkey" plugin-loader/CMakeLists.txt; then
    sed -i "s/\(set(MLD_PUBKEY_HEX \)\"[0-9a-f]*\"/\1\"$current_pubkey\"/" plugin-loader/CMakeLists.txt
    # recompilar solo si cambió
    make plugin-loader-build
fi
```

### 3. Falta un `make destroy` limpio que también borre artefactos locales (build/, .vagrant/)
El comando `vagrant destroy` deja basura local (caches de compilación, `build/`, `*.so` no trackeados). **Propuesta:** Añadir `make clean-vagrant` que haga `vagrant destroy -f && rm -rf .vagrant build-*` y opcionalmente `git clean -fdX` (con advertencia).

---

## Respuestas a las preguntas del Consejo

### Q1 — Robustez de `sync-pubkey`

**Vectores de fallo identificados:**

1. **La VM no está en ejecución** – `vagrant ssh` fallará. El target debería comprobar primero `vagrant status | grep -q running`.
2. **La pubkey no se ha generado todavía** – Sucede si se ejecuta `sync-pubkey` antes de que ningún componente haya rotado la keypair. El target debería fallar con un mensaje claro: "No pubkey found. Run `make pipeline-start` first to generate keys."
3. **Cambios en la ruta de la pubkey** – Actualmente asume `/opt/ml-defender/etc/pubkey.hex`. Si esa ruta cambia en el futuro, el target se rompe silenciosamente. **Solución:** Leer la ruta desde `config.mk` o desde una variable de entorno.

**Continuity Prompt:** El Consejo opina que la actualización del Continuity Prompt **debe ser manual**. Es un paso de verificación humano que asegura que la clave pública que se muestra al operador coincide con la que está compilada. Automatizarlo podría ocultar un ataque de reemplazo de clave. Mantenedlo como un paso documentado.

**Veredicto:** El mecanismo es robusto con las salvaguardas anteriores. Aceptado.

---

### Q2 — Vagrantfile vs Makefile: separación de responsabilidades

**Principio acordado:**

| **Vagrantfile** | **Makefile** |
|----------------|---------------|
| Dependencias del sistema (paquetes apt, bibliotecas como libsodium, XGBoost, tmux, xxd) | Compilación de componentes propios (seed_client, plugin-loader, ml-detector, etc.) |
| Creación de directorios del sistema (`/usr/lib/ml-defender/`, `/etc/ml-defender/`) | Instalación de units systemd (aunque esto podría debatirse) |
| Usuarios, grupos, permisos estructurales | Firma de plugins, tests, generación de documentación |

**Excepción que ya han encontrado:** La instalación de `install-systemd-units` y `set-build-profile` son operaciones de «configuración del sistema» pero están en el Makefile porque requieren lógica condicional (perfil de build). El Consejo considera que **es aceptable**, siempre que ambos targets sean idempotentes y se ejecuten después de `make up`.

**Recomendación:** Documentar esta separación en `docs/DEVELOPMENT.md` con una tabla similar a la anterior, para que los nuevos contribuyentes no mezclen responsabilidades.

---

### Q3 — ¿`make bootstrap`? Riesgos y beneficios

**Beneficios:**
- Reduce fricción para nuevos desarrolladores.
- Evita omisiones de pasos.
- Permite integrar en CI un test de «primer clone» completo.

**Riesgos:**
- Enmascara errores intermedios. Si `make bootstrap` falla en el paso 5, el desarrollador no sabrá fácilmente cuál fue la causa (aunque se puede mostrar cada comando con `set -x`).
- No todos los pasos son siempre necesarios (por ejemplo, `make sign-plugins` solo se necesita si se han recompilado plugins).
- Podría fomentar una cultura de «ejecutar el script mágico» en lugar de entender el sistema.

**Decisión del Consejo:**  
✅ **Sí a `make bootstrap`, pero como una macro que ejecuta la secuencia paso a paso mostrando cada comando y deteniéndose en el primer error.**  
Además, debe ser idempotente: si se ejecuta dos veces seguidas, no debe cambiar nada (a excepción de `sync-pubkey` si la pubkey rotó entre medias).

Ejemplo de implementación segura:

```makefile
.PHONY: bootstrap
bootstrap:
	@echo ">>> Starting full bootstrap from clean VM"
	$(MAKE) up
	$(MAKE) sync-pubkey
	$(MAKE) set-build-profile
	$(MAKE) install-systemd-units
	$(MAKE) sign-plugins
	$(MAKE) test-provision-1
	$(MAKE) pipeline-start
	$(MAKE) pipeline-status
	$(MAKE) plugin-integ-test
	@echo ">>> Bootstrap successful"
```

El riesgo se mitiga porque cada sub-make fallará si algo va mal, y el usuario puede inspeccionar el paso concreto.

---

### Q4 — Contrato mínimo de `ctx->payload` para XGBoost

El plugin XGBoost no debe asumir nada sobre el llamador excepto que el payload es un array binario de `float32` en orden nativo, con una longitud que sea múltiplo del tamaño de `float`. El plugin **no debe** interpretar el payload como nada más (ni JSON, ni msgpack, ni texto).

**Contrato propuesto (para documentar en `plugin_loader/plugin_api.h`):**

```c
/**
 * Para el plugin XGBoost, el llamador (ml-detector) debe llenar
 * MessageContext::payload con un array de float32 en orden little-endian.
 * El número de features es payload_size / sizeof(float).
 * El plugin es responsable de:
 *   - Validar que payload_size % sizeof(float) == 0.
 *   - Construir un DMatrix de una sola fila con esos valores.
 *   - Ejecutar XGBoosterPredict y devolver la probabilidad de clase 1.
 *
 * Si payload_size es 0 o no es múltiplo de 4, el plugin debe devolver -1.0f
 * (error) y registrar el fallo.
 */
```

**Código mínimo en `plugin_process_message` (o `plugin_invoke` según la versión):**

```cpp
extern "C" float plugin_process_message(MessageContext* ctx) {
    if (ctx->payload_size % sizeof(float) != 0) {
        fprintf(stderr, "XGBoost plugin: invalid payload size %zu\n", ctx->payload_size);
        return -1.0f;
    }
    size_t n_features = ctx->payload_size / sizeof(float);
    if (n_features != expected_n_features) { // se obtiene del modelo cargado
        fprintf(stderr, "Feature count mismatch: got %zu, expected %zu\n", n_features, expected_n_features);
        return -1.0f;
    }
    const float* features = reinterpret_cast<const float*>(ctx->payload.data());
    // ... construir DMatrix row-major ...
}
```

**Además, el plugin debe ser reentrante** (no usar variables globales mutables sin protección). Dado que XGBoost `BoosterHandle` puede compartirse, pero la predicción es thread-safe según la documentación.

**Veredicto:** El contrato mínimo es ese. Documentarlo en `docs/XGBOOST-PLUGIN-CONTRACT.md` y referenciarlo desde el ADR-026.

---

### Q5 — Puntos ciegos para la reproducción `vagrant destroy` de mañana (DAY 120)

El Consejo anticipa los siguientes posibles fallos:

1. **Caché de apt en la VM** – Después de `vagrant destroy`, la caché de paquetes se pierde. La próxima ejecución descargará de nuevo. No es un fallo, pero puede alargar el tiempo. **No bloqueante.**

2. **La pubkey rotada durante las pruebas** – Si el test `make plugin-integ-test` incluye un reset que rota la clave, `sync-pubkey` se ejecutó al principio y la pubkey en CMakeLists.txt quedará desfasada. **Solución:** Después de `make sign-plugins` (que regenera firmas) debería ejecutarse de nuevo `make sync-pubkey`. Ajustar la secuencia canónica para que `sync-pubkey` se ejecute **antes de compilar cualquier cosa** y **después de cualquier operación que pueda rotar la keypair** (como `make reset-seed` o `make rotate-keys`). Por ahora, como no hay rotación explícita en la secuencia, no debería pasar.

3. **Permisos de `/usr/lib/ml-defender/plugins/`** – Si el usuario `vagrant` no tiene permisos de escritura, `make sign-plugins` fallará al intentar copiar los `.so` firmados. **Verificar** que el bloque de creación en Vagrantfile haga `chown vagrant:vagrant` y `chmod 755`.

4. **Dependencia de red para `pip install xgboost`** – En entornos sin internet (hospitales), el fallback apt usará la versión 1.7 de Debian. Esa versión **no es compatible con la API de C** que usa `XGBoosterLoadModel` de la misma manera que 3.2.0. **Punto ciego grave.** El Consejo recomienda **no usar el fallback apt** para producción, sino ofrecer un método offline: descargar el `.whl` de XGBoost 3.2.0 y colocarlo en un mirror local o en el propio repositorio (aunque sea grande). Añadir una variable `XGBOOST_INSTALL_METHOD=local` que use `pip install /path/to/xgboost-3.2.0.whl`.

5. **`make pipeline-start` depende de que exista el socket de tmux** – Si la sesión tmux ya existe de una ejecución anterior, `tmux new-session -d -s defender` fallará. El target debería hacer `tmux kill-session -t defender 2>/dev/null; tmux new-session -d -s defender`. **Verificar que ya lo hace.**

**Recomendación para DAY 120:** Después de `vagrant destroy && vagrant up`, ejecutar la secuencia canónica **dos veces seguidas** (sin destruir) para comprobar la idempotencia. La segunda ejecución no debe cambiar nada.

---

## Veredicto final del Consejo

El DAY 119 ha sido un paso fundamental para la reproducibilidad. La deuda técnica de infraestructura se ha reducido drásticamente. El Consejo **APRUEBA** la secuencia canónica y las respuestas dadas.

**Acciones inmediatas para DAY 120:**

1. Implementar `make test-bootstrap` (como se describe en la mejora 1).
2. Añadir la comprobación de idempotencia en `sync-pubkey` (mejora 2).
3. Documentar el contrato de `ctx->payload` para XGBoost (Q4).
4. Repetir `vagrant destroy` dos veces seguidas para validar idempotencia y detectar el punto ciego de XGBoost offline.

*Via Appia Quality — la reproducibilidad es la madre de la confianza.*

— **Consejo de Sabios (sesión DAY 119)**