# Pregunta al Consejo de Sabios — Métricas de Aceptación Hardware (ADR-029)

**Contexto**: aRGus NDR necesita validar que sus variantes hardened (ADR-029 Variant A: Debian+AppArmor+eBPF/XDP y Variant B: Debian+AppArmor+libpcap) funcionan correctamente sobre hardware real antes de la presentación FEDER (deadline 22 sep 2026). Antes de comprar hardware, necesitamos definir el baseline de aceptación para cada configuración, de modo que cualquier prueba tenga criterio de éxito claro y verificable.

---

## Pregunta

**¿Cuáles deben ser las métricas mínimas de aceptación para las variantes hardened de aRGus sobre hardware físico (x86 y ARM/Raspberry Pi), y cómo se deben medir de forma reproducible?**

Se propone el siguiente conjunto inicial como punto de partida. El Consejo debe validar, criticar y completar:

### Candidatos a métricas de aceptación

| Métrica | Valor propuesto | Justificación |
|---|---|---|
| Throughput sin packet loss | ≥ X Mbps | ¿Cuál es el X correcto para infraestructura crítica (hospital, municipio)? ¿100 Mbps? ¿1 Gbps? |
| Latencia de detección (p50) | ≤ Y ms | ¿Cuál es el Y tolerable para que la respuesta del firewall-acl-agent sea útil? |
| RAM disponible tras arranque | ≥ Z MB | ¿Cuánto headroom es necesario para que el sistema host no se vea comprometido? |
| F1 sobre golden set | ≥ 0.9985 | Igual que en VM — el hardware no debe degradar el modelo. |
| CPU idle durante tráfico normal | ≥ W% | Para garantizar que aRGus no consume el host en condiciones normales. |
| Tiempo de arranque del pipeline | ≤ T segundos | Para escenarios de reinicio de emergencia. |
| 0 packet loss a carga sostenida | Sí/No | ¿A qué Mbps exactamente? ¿Durante cuánto tiempo? |

### Preguntas específicas al Consejo

1. **Sobre Throughput**: Para una red de hospital o municipio típico (10-500 usuarios concurrentes), ¿cuál es el throughput mínimo creíble a demostrar en FEDER? ¿100 Mbps es suficiente o necesitamos 1 Gbps?

2. **Sobre Variant A (eBPF/XDP) vs Variant B (libpcap)**: ¿Cuál es el delta de throughput esperado entre ambas variantes? ¿Es el delta en sí mismo una métrica publicable para el paper?

3. **Sobre ARM/Raspberry Pi**: ¿Las métricas de aceptación deben ser las mismas para x86 y ARM, o ARM tiene un perfil diferente (menor throughput, mayor justificación de coste)?

4. **Sobre el golden set como métrica hardware**: ¿Tiene sentido ejecutar el golden set de ML (ADR-040) como parte del test de aceptación hardware, para verificar que el modelo no se degrada por cambios de arquitectura?

5. **Sobre la herramienta de generación de carga**: ¿Cuál recomendáis para generar tráfico de red reproducible en el entorno Vagrant? ¿tcpreplay sobre pcaps reales de CTU-13? ¿iperf3? ¿Una combinación?

6. **Sobre el criterio de éxito para FEDER**: ¿El baseline debe ser "el sistema funciona" o "el sistema funciona mejor que la alternativa comercial X a Y€/año"? ¿Necesitamos un benchmark comparativo?

---

## Formato de respuesta esperado del Consejo

Para cada pregunta, se solicita:
- **Recomendación concreta** (valor numérico cuando aplique)
- **Justificación técnica** (por qué ese valor y no otro)
- **Riesgo identificado** (qué puede salir mal si usamos ese criterio)
- **Test mínimo reproducible** (cómo se verifica en el entorno Vagrant)

---

## Contexto adicional

- Hardware objetivo: x86 (por definir) y Raspberry Pi 4/5 (ARM64)
- Entorno de prueba: Vagrant VM en desarrollo, hardware físico en validación FEDER
- Pipeline actual: eBPF/XDP sniffer → ml-detector → firewall-acl-agent → rag-ingester → rag-security
- Constraint económico: el hardware debe ser asequible para hospitales y municipios que no pueden permitirse soluciones enterprise
- Referencia de escala: Mercadona Tech buscador: 4.4M búsquedas/semana, latencia p50 = 12 ms, 100 MB RAM — todo sin GPU, sin servicios externos