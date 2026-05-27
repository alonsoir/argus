Aquí mi feedback para el registro de ADR-042 v2:

---

**Lo que v2 resuelve correctamente:**

La decisión de aislar red antes del poweroff es la corrección más importante. La "paradoja del suicidio" de Gemini era el argumento técnico más sólido de toda la primera ronda, y la solución de jerarquía aislar→verificar→poweroff es la respuesta correcta. El `argus-network-isolate` como `ExecStopPre` antes del `FailureAction=poweroff` es arquitectónicamente limpio y no compromete la filosofía fail-closed — simplemente la hace más robusta.

El initramfs read-only es la decisión correcta para forensics. Tu razonamiento es preciso: un entorno mínimo cargado en RAM desde partición verificada, montando el disco del sistema en read-only, da acceso a los logs sin que el SO comprometido pueda interferir. La restricción de solo consola local — sin ejecución remota — es la garantía que hace que la evidencia tenga cadena de custodia aceptable. No es perfecta sin TPM, pero es significativamente mejor que nada, y es honesto documentarlo así.

P6 — reintegración verificada — es la brecha más importante que faltaba en v1. Qwen y Kimi tenían razón. Un nodo que vuelve a la flota sin pasar `argus-post-recovery-check` puede reintroducir el compromiso. La política de nunca-automático + quarantine 24h + aprobación manual es la única correcta para infraestructura crítica.

**Lo que añadiría o matizaría:**

Sobre `argus-network-isolate`: hay un edge case no documentado. Si el nodo está actuando como gateway (arquitectura HA del paper, figura §4.2), bajar las interfaces de red no solo aísla el nodo — corta el tráfico de red del hospital que pasa por él. Esto puede ser peor que el compromiso en sí durante esos segundos. El script debería ser consciente del modo de despliegue: si es gateway, antes de bajar las interfaces hay que intentar promover el standby o al menos redirigir el tráfico. Si es sensor pasivo, bajar las interfaces es seguro. Esta distinción debería estar documentada.

Sobre la cola persistente de alertas: el path `/var/lib/argus/irp-queue` debe estar en un filesystem separado del disco del sistema, o al menos en una partición con integridad verificada. Si el atacante comprometió el disco, puede vaciar la cola silenciosamente. Una alternativa simple: escribir en `/dev/kmsg` además de en disco — los mensajes del kernel son más difíciles de suprimir sin acceso a ring buffer.

Sobre los tests TDH: `make test-irp-type-a` tal como está definido requiere simular un poweroff real de la VM, lo que rompe el entorno de desarrollo. Necesita una variante `--dry-run` que verifique que todos los pasos anteriores al poweroff se ejecutan correctamente, sin ejecutar el poweroff en sí. Esto es un detalle de implementación pero bloqueante para que el test sea ejecutable en EMECAS.

**Sobre la conexión con el paper:**

ADR-042 es efectivamente material publicable. El protocolo IRP para NDR open-source en infraestructura crítica no está documentado en la literatura con este nivel de detalle operacional. Pero lo más valioso no es el protocolo en sí — es la honestidad sobre las limitaciones. La sección de limitaciones residuales, especialmente el punto sobre single-node hospital y el riesgo de standby comprometido, es exactamente el tipo de contribución que Sommer y Paxson pedían en 2010: documentar honestamente lo que el sistema no puede hacer, no solo lo que puede.

**Posición general:**

ADR-042 v2 está listo para segunda ronda del Consejo. Los cambios respecto a v1 son todos correcciones en la dirección correcta. Las deudas están bien triadas. Las limitaciones están documentadas con honestidad. El sistema puede implementarse incrementalmente empezando por `argus-irp-notify` y `argus-network-isolate` — ambos son de bajo riesgo y alto valor inmediato.

*Claude — DAY 135 — 29 Abril 2026* 🏛️