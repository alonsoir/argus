## Consejo de Sabios — Respuestas DAY 129

Evaluación basada en criterios de seguridad, reproducibilidad y operación en entornos hospitalarios (alta criticidad, bajo margen de error).

---

## P1 — Regla permanente transferencia ficheros

**Decisión: ✅ APROBADA (obligatoria)**

La regla propuesta:

> uso exclusivo de `scp -F vagrant-ssh-config` o `vagrant scp`

es correcta y debe formalizarse como **regla de seguridad operativa**, no solo de conveniencia.

### Justificación técnica

* `vagrant ssh -c "cat ..." > file`:

    * depende del shell local (zsh/bash)
    * puede truncar silenciosamente (como ya observado)
    * no garantiza integridad ni atomicidad

### Riesgo en entorno hospitalario

* corrupción silenciosa de:

    * reglas firewall
    * modelos ML
    * seeds criptográficos

→ impacto potencial: **crítico**

### Recomendación adicional

* Añadir checksum obligatorio (`sha256sum`) post-transferencia
* Opcional: wrapper `argus_scp_verify.sh`

---

## P2 — `.gitignore` build-debug

**Decisión: ✅ APROBADO**

Añadir:

```
**/build-debug/
```

### Justificación

* Artefactos generados → no deterministas
* Ruido constante en staging → aumenta probabilidad de error humano
* No aportan valor versionado

### Nota

Si algún binario/debug es necesario:

* usar `build/` reproducible o CI artifacts
* nunca commit directo

---

## P3 — Prioridad DAY 130

**Decisión: 🥇 A) DEBT-FUZZING-LIBFUZZER-001**

### Orden recomendado

1. **A — Fuzzing (CRÍTICO)**
2. B — Capabilities
3. C — Paper

### Justificación

El sistema está en superficie expuesta (input parsing + firewall):

* `validate_chain_name`
* parsers ZMQ
* entrada externa potencialmente hostil

Sin fuzzing:
→ vulnerabilidades desconocidas (unknown unknowns)

### En contexto hospitalario

* inputs pueden venir de red comprometida
* resiliencia ante input malicioso es prioritaria

### Recomendación concreta

* targets iniciales:

    * `validate_chain_name`
    * `validate_filepath`
    * parser ZMQ (alto riesgo)
* integrar en CI (no solo local)

---

## P4 — Null byte en `validate_chain_name`

**Decisión: ⚠️ ACTUALMENTE CORRECTO, PERO INSUFICIENTE A LARGO PLAZO**

El check:

```cpp
name.find('\0') != npos
```

es necesario, pero no suficiente como única defensa.

### Riesgo real

Aunque `execv()`:

* no usa shell
* separa argumentos

El null byte:

* puede truncar strings en capas inferiores (C APIs)
* puede introducir discrepancias entre validación y ejecución

### Recomendación (defensa en profundidad)

1. **Mantener validación actual**
2. **Añadir invariant en `safe_exec()`**:

    * rechazar cualquier argumento con `\0`
3. Opcional:

    * usar estructuras tipo `std::vector<std::string>` → validación centralizada

### Regla resultante

> Ningún input con null byte debe cruzar frontera de ejecución

---

## P5 — `.gitguardian.yaml`

**Decisión: 🟡 POSPONIBLE (no crítico)**

### Evaluación

* No afecta seguridad runtime
* No afecta build
* Es ruido de tooling

### Recomendación

* No priorizar en DAY 130
* Resolver cuando:

    * haya ventana de mantenimiento
    * o se toquen pipelines CI

---

## Evaluación global DAY 129

### Estado

* Eliminación completa de `popen/system` → **salto de seguridad significativo**
* Tests con evidencia RED→GREEN → correcto
* Pipeline estable → positivo

### Riesgos residuales

1. Falta de fuzzing → principal vector abierto
2. Distribución de claves aún en transición (HTTP legacy)
3. Capabilities pendientes → superficie innecesaria

---

## Directiva del Consejo

Para alineación con entornos hospitalarios:

1. **Prioridad absoluta: robustez ante input hostil**
2. **Cero tolerancia a corrupción silenciosa**
3. **Defensa en profundidad obligatoria en fronteras de ejecución**
4. **Reproducibilidad > velocidad de desarrollo**

---

## Veredicto final

* DAY 129 → **VALIDADO**
* Sistema → **seguro en progreso, aún no endurecido completamente**
* DAY 130 → **centrado en fuzzing sin excepción**

---

Si el equipo mantiene este nivel de disciplina (RED→GREEN + evidencia), el sistema está en trayectoria correcta para entornos críticos reales.
