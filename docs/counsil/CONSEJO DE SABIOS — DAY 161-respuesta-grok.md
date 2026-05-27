**Consejo de Sabios — Respuesta a las preguntas de DAY 161**

¡Saludos, Alonso! Excelente progreso en la maduración del pipeline CI/CD. La separación clara entre `Jenkinsfile.dev` y `.prod`, el cierre de deudas críticas (wire protocol test + E2E delta) y la documentación de deudas estructurales (Jinja2 + .deb) muestran muy buena disciplina. Vamos al grano.

### Q1 — Wire Protocol Test
**Recomendación: Mantén el test actual como está + NO añadas segundo test completo de CryptoTransport en este nivel.**

- El test `test_wire_protocol` es **excelente** en su rol: valida el formato binario wire (LZ4 LE uint32_t) de forma aislada y determinista. Esto protege contra regresiones del bug DAY 98 de forma barata y rápida.
- Los tests existentes en `crypto-transport` ya cubren cifrado + compresión a nivel unitario/integración.
- Añadir un test completo aquí generaría **duplicación** y ralentizaría el pipeline dev innecesariamente.

**Decisión óptima:**  
Mantén este test enfocado en **serialización binaria pura**. Si en el futuro quieres cobertura end-to-end del wire completo, hazlo en un test de integración superior (por ejemplo, `test-engine-communication` o dentro de EMECAS++ con tráfico real).

### Q2 — Jenkinsfile.dev vs Jenkinsfile.prod
**Diseño actual correcto para la fase actual.**

- `agent any` + Vagrant en la Mac del fundador es **perfecto** ahora. Permite iteración rápida sin depender del servidor FEDER.
- La separación de credenciales (`vault-enterprise-token`) es limpia y segura.

**Cuándo mover a `agent { label 'argus-server' }` en dev:**
- Cuando quieras ejecutar los tests de **Enterprise Plugin** de forma consistente y repetible en hardware cercano al target (preferiblemente el propio argus-server o una réplica).
- O cuando el tiempo de ejecución en Vagrant empiece a ser doloroso (compilación pesada + tests crypto).

**Propuesta pragmática:**
Mantén `Jenkinsfile.dev` con `agent any` por ahora.  
Cuando entres en fase de hardware físico real (RPi5/N100), crea un tercer `Jenkinsfile.ci` o usa parámetros/matrix para escoger agente según el stage.

### Q3 — DEBT-CONFIG-JINJA2-PIPELINE-001
**Recomendación fuerte: Valores calculados en runtime según hardware detectado + perfiles base.**

El diseño "JSONs originales sagrados" es correcto. En producción **solo deben existir los generados**.

- **Runtime detection** (CPU cores, RAM, NIC capabilities, etc.) es superior porque:
  - Permite optimización real en hardware heterogéneo (RPi5 vs Intel N100 vs servidor FEDER).
  - Reduce deuda de mantenimiento de perfiles estáticos.
  - Es más robusto ante cambios de hardware.

**Estrategia recomendada:**
1. Tener perfiles base (`naive`, `edge-low`, `edge-medium`, `edge-high`) como valores por defecto / fallback.
2. El script de generación (`generate-configs.sh` o similar) detecta hardware y aplica *overrides* inteligentes sobre el perfil base.
3. Guardar el perfil detectado + hash de hardware en un archivo de manifiesto (para debugging y reproducibility).

Esto escala mejor que perfiles completamente fijos.

### Q4 — EMECAS++ y el fix del delta E2E
**Riesgo real detectado correctamente.**

**Recomendación: Inyectar tráfico sintético mínimo controlado.**

Razones:
- En entornos Vagrant/Mac, el tráfico orgánico puede ser inexistente o muy bajo durante la ventana de 60s.
- Un test que depende de "tráfico real externo" es **flaky** por definición → viola principios de CI/CD.
- El objetivo del test E2E no es validar captación pasiva pura, sino que **todo el pipeline de ingestión → detección → alerting** funcione.

**Solución limpia:**
- Opción `--inject-synthetic` (o siempre activado en modo CI).
- Inyectar 2-3 paquetes mínimos (por ejemplo, un handshake TCP + un par de paquetes de datos) usando `hping3`, `scapy` o directamente desde el código de tests.
- Luego aplicar el delta check.

Esto garantiza que el test sea **determinista** sin perder valor.

### Q5 — Prioridad DAY 162
**Recomendación: A) DEBT-ARGUSPP-SURICATA-001**

Orden de valor actual (mi ranking):

1. **A) DEBT-ARGUSPP-SURICATA-001** — Primera señal externa real. Esto desbloquea mucho: testing realista, demostraciones, validación de correlación. Es el hito más visible y valioso para momentum.
2. **C) DEBT-CRYPTO-AUTONOMY-001** — Muy importante a medio plazo (autonomía en entornos sin Vault), pero puede esperar unos días.
3. **D) DEBT-ALERTING-LIBCRYPTO-PROVIDER-001** — Refactor técnico sano, pero no desbloquea funcionalidad nueva.
4. **B) DEBT-ARGUSPP-NTP-001** — Importante para correlación temporal, pero postergable hasta tener más engines.

**Propuesta de secuencia DAY 162:**
- Merge DAY 161 tras EMECAS++ verde.
- Atacar **Suricata integration** (ADR-048 F2).
- Paralelamente ir madurando el diseño de Crypto Autonomy.

---

**Resumen de decisiones recomendadas:**
- Q1 → No, test actual suficiente.
- Q2 → Diseño actual OK.
- Q3 → Runtime + perfiles base.
- Q4 → Inyectar tráfico sintético mínimo.
- Q5 → Prioridad A (Suricata).

¿Quieres que profundicemos en alguno (especialmente el script de generación Jinja2 o el inyector sintético)? El Consejo está a disposición.

*Via Appia Quality.* 🏛️