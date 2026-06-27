## RESPUESTA DEL CONSEJO DE SABIOS — DAY 132

**Acta de revisión científica**  
**Fecha:** 26 abril 2026  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Documentos revisados:** DAY 132 backlog, commits `5a22c068`, `b7d38d1f`, `18d8e101`, `9b3438fb`  
**Método:** Reproducibilidad exigida – todas las respuestas se basan en evidencia documentada y principios de ingeniería de sistemas críticos.

---

### Valoración general del DAY 132

El Consejo felicita al equipo por dedicar una sesión completa a **consolidación documental y preparación de infraestructura**. Este tipo de jornadas, aunque no produzcan código, son esenciales para la **reproducibilidad científica** y la **sostenibilidad del proyecto**. La actualización del paper con cuatro secciones metodológicas nuevas (§6.5, §6.8, §6.10, §6.12) eleva significativamente el rigor de la publicación. El README con prerequisitos explícitos elimina barreras de entrada para nuevos investigadores. El inicio de ADR-030 Variant A con `HARDWARE-REQUIREMENTS.md` y Vagrantfile hardened es el primer paso tangible hacia la imagen de producción.

**Aprobación unánime** de la estrategia: mantener `main` sagrado, trabajar en `feature/adr030-variant-a`, y no subir el draft v17 a arXiv hasta tener validación experimental de las afirmaciones (especialmente la BSR axiom con métricas reales de reducción de paquetes).

---

## Respuestas a las preguntas del Consejo

### Q1 — Makefile targets de producción: ¿Makefile raíz o separado?

**Pregunta:**
> ¿Es correcto mantenerlos en el Makefile raíz, o recomendáis un `Makefile.production` separado para evitar confusión?

**Respuesta:** ✅ **Mantener en el Makefile raíz**, con una convención clara de nombres y protección contra ejecución en entorno equivocado.

**Justificación científica (reproducibilidad):**
- Un único punto de entrada (`make`) reduce la carga cognitiva y sigue el principio de **mínima sorpresa**. Los desarrolladores esperan que todos los targets estén en el Makefile principal.
- La separación en `Makefile.production` podría llevar a invocaciones erróneas (`make -f Makefile.production build`) que omitan verificaciones de entorno.
- **Protección necesaria:** Cada target de producción debe comprobar la variable de entorno `BUILD_ENV` o la presencia de `/etc/argus-dev-env` (un archivo marcador que solo existe en la VM de desarrollo). Si se ejecutan en la VM hardened (sin compilador), deben fallar con un mensaje claro:
  ```makefile
  ifneq ($(wildcard /etc/argus-dev-env),)
      $(info Build environment detected: dev VM)
  else
      $(error Production targets can only be run in the development VM)
  endif
  ```

**Recomendación adicional:** Agrupar todos los targets de producción bajo un prefijo `prod-` para evitar colisiones con targets de desarrollo (`make prod-build`, `make prod-sign`, `make prod-verify`). El actual `build-production-x86` es correcto pero podría simplificarse a `prod-build-x86`.

**Decisión del Consejo:** Aprobado el Makefile raíz con las protecciones indicadas.

---

### Q2 — Vagrantfile hardened-x86: ¿Debian 12 (bookworm) o esperar a Debian 13 (trixie)?

**Pregunta:**
> ¿Recomendáis mantener Debian 12 en el Vagrantfile y documentar el upgrade path a Debian 13 para bare-metal, o buscar una box de Trixie alternativa?

**Respuesta:** ✅ **Mantener Debian 12 (bookworm64) ahora, con documentación explícita del upgrade path.**

**Justificación científica (reproducibilidad):**
- El objetivo de `vagrant/hardened-x86` es **demostrar el concepto de separación build/runtime**, no ser la imagen de producción definitiva. Para la demo FEDER (septiembre 2026), Debian 12 tiene soporte hasta 2028 (LTS), por lo que es perfectamente válido.
- Debian 13 (Trixie) aún está en testing (no estable) y no tiene boxes oficiales en Vagrant Cloud. Usar boxes no oficiales o construir una propia introduce **deriva de reproducibilidad** – otro equipo podría obtener un entorno diferente.
- **Estrategia recomendada:**
  1. El `Vagrantfile` usa `debian/bookworm64`.
  2. El `HARDWARE-REQUIREMENTS.md` documenta: “La imagen de producción bare-metal debe usar Debian 12 o superior. Para Debian 13, se proporcionará un script de migración post-lanzamiento.”
  3. Crear una deuda técnica `DEBT-DEBIAN13-UPGRADE-001` para cuando Debian 13 sea estable (previsto 2027), e incluirla en el roadmap post-FEDER.

**Decisión del Consejo:** No buscar boxes de Trixie. Mantener bookworm64. Añadir nota en `HARDWARE-REQUIREMENTS.md` sobre compatibilidad futura.

---

### Q3 — BSR axiom: ¿`dpkg` es suficiente o añadimos `which gcc`?

**Pregunta:**
> ¿Añadimos `which gcc || which clang || which cc` como segunda capa de verificación, sabiendo que no es exhaustiva pero sí más robusta?

**Respuesta:** ✅ **Sí, añadir ambas verificaciones (dpkg + which) como defensa en profundidad.**

**Justificación científica (reproducibilidad y seguridad):**
- `dpkg -l` detecta compiladores instalados mediante el gestor de paquetes, pero un atacante o un error de aprovisionamiento podría copiar binarios estáticos (ej: `gcc` compilado manualmente en `/usr/local/bin`).
- `which gcc` (o `command -v gcc`) detecta cualquier ejecutable en `$PATH`. No es exhaustivo (un atacante podría ejecutar `gcc` desde una ruta absoluta no en `$PATH`), pero cubre el escenario más probable de error humano o contaminación accidental.
- **Doble verificación con diferentes metodologías** reduce la tasa de falsos negativos. En sistemas hospitalarios, preferimos un falso positivo (bloquear el despliegue por un `gcc` inexistente pero mal detectado) a un falso negativo (dejar pasar un compilador).

**Implementación recomendada en `check-prod-no-compiler`:**
```bash
#!/bin/bash
# Verificación 1: paquetes Debian
if dpkg -l | grep -qE 'gcc|g\+\+|clang|cmake|make'; then
    echo "ERROR: Compiler packages found in dpkg" >&2
    exit 1
fi
# Verificación 2: ejecutables en PATH
for tool in gcc clang cc c++ g++ cmake make; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: $tool found in PATH" >&2
        exit 1
    fi
done
echo "OK: No compiler detected"
```

**Decisión del Consejo:** Añadir la verificación `command -v`. Crear una nota en la documentación: “Esta verificación no es exhaustiva contra atacantes decididos, pero es suficiente para el modelo de amenaza de configuración incorrecta.”

---

### Q4 — Draft v17: revisión de las 4 nuevas secciones §5 (en realidad §6)

**Pregunta:**
> ¿Consideráis que el nivel de rigor y la evidencia empírica presentada en cada sección es suficiente para arXiv cs.CR? ¿Qué añadiríais o reforzaríais?

**Respuesta:** El nivel es **suficientemente riguroso para arXiv**, pero **recomendamos tres mejoras concretas** antes del envío público.

**Análisis sección por sección:**

| Sección | Rigor actual | Carencia / Mejora sugerida |
|---------|--------------|-----------------------------|
| §6.5 (RED→GREEN gate) | ✅ Bueno: describe el proceso, menciona REGLA EMECAS. | **Añadir métrica:** ¿Cuántas veces ha detectado falsos positivos? ¿Tasa de falsos negativos observada? (datos empíricos de DAY 1–132). |
| §6.8 (Fuzzing) | ✅ Bueno: menciona libFuzzer, `validate_chain_name`. | **Añadir:** resultados concretos de la sesión de fuzzing (cuántos inputs generados, cuántos crashes, tiempo de ejecución). Si aún no se ha hecho, marcar como “trabajo futuro” o posponer la sección. |
| §6.10 (CWE-78 execv()) | ✅ Excelente: describe la eliminación de 13 call-sites `popen()/system()`. | **Añadir:** referencias a vulnerabilidades reales en iptables wrappers de otros proyectos (ej: CVE-2021-3773 en firewalld) para contextualizar. |
| §6.12 (BSR axiom) | ✅ Buena motivación, pero **falta evidencia empírica**. | **Crítico:** El axioma actual es teórico. Para arXiv, debe acompañarse de una tabla con métricas reales de la VM hardened vs dev: paquetes instalados, tamaño imagen, CVEs relevantes. El ADR-039 promete estas métricas en “post-implementación”. **Recomendamos no incluir §6.12 en v17** hasta tener esos números, o etiquetarla como “propuesta con validación pendiente”. |

**Recomendaciones concretas para el equipo:**

1. **Ejecutar la VM hardened** (aunque sea con Debian 12) y medir:
  - `dpkg -l | wc -l` comparado con dev VM.
  - `du -sh /` (tamaño del sistema base).
  - `grep -c ^Package /var/lib/dpkg/status` (paquetes).
  - Usar `docker run --rm aquasec/trivy filesystem --no-progress /` para listar CVEs en paquetes instalados.
2. **Incluir esos números en §6.12** como evidencia empírica. Sin ellos, el axioma es una opinión, no un resultado científico.
3. **Para §6.8**, si aún no se ha hecho fuzzing, cambiar el texto de “hemos implementado” a “se ha diseñado un harness; los resultados preliminares se presentarán en la versión final”. O bien posponer la sección.

**Decisión del Consejo (voto unánime):**  
El draft v17 es **aceptable para depósito en arXiv** **solo si se añaden las métricas de BSR axiom antes del envío**. Si el equipo prefiere no demorar, se puede enviar sin §6.12 (dejándola para v18). Recomendamos esperar a tener los números (1-2 días de trabajo) y enviar un preprint más robusto.

---

## Acuerdos y acciones resultantes

| Ítem | Decisión | Responsable | Plazo |
|------|----------|-------------|-------|
| Q1 (Makefile) | Mantener en Makefile raíz con protección `BUILD_ENV`. | Equipo ADR-030 | DAY 133 |
| Q2 (Debian 12 vs 13) | Usar bookworm64. Documentar upgrade path. Crear DEBT-DEBIAN13-UPGRADE-001. | Documentación | DAY 133 |
| Q3 (BSR double check) | Añadir `command -v` a `check-prod-no-compiler`. | Equipo ADR-030 | DAY 133 |
| Q4 (Paper v17) | No enviar a arXiv hasta tener métricas reales de BSR axiom. Completar mediciones en VM hardened. | Equipo paper + ADR-030 | 3 días |

---

## Reflexión final del Consejo

DAY 132 demuestra que la **calidad documental es tan importante como la calidad del código** para un proyecto de investigación reproducible. Las cuatro nuevas secciones del paper son contribuciones originales que merecen ser publicadas, pero la comunidad científica espera **datos, no solo afirmaciones**. El Consejo anima al equipo a dedicar DAY 133 a ejecutar las métricas de la VM hardened y a completar el fuzzing de `validate_chain_name`. Con esos números, el preprint será un hito.

Recordad: *“Lo que no se mide, no se mejora. Lo que no se publica con datos, no se cree.”*

*Firmado por los 8 modelos en consenso, 26 abril 2026*  
*Vía Appia Quality — Un escudo que aprende de su propia sombra.*