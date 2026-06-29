El Consejo de Sabios ha deliberado. Estas son nuestras respuestas.

---

**1. Patrón CMake para targets condicionales**

Vemos dos problemas entrelazados: la duplicación accidental y la ambigüedad semántica.  
Recomendamos aplicar **ambas** defensas, pero con distinto peso normativo:

- **Invariante obligatorio:** todo target definido dentro de un bloque condicional debe ir envuelto en `if(NOT TARGET <nombre>)`. Convertid esto en regla de estilo para `cmake-lint` y en check de CI (podéis añadirlo ahora mismo como parte del fix). Así prevenís la regresión incluso cuando la condición se active por primera vez en una build enterprise.
- **Convención de nomenclatura:** cuando un target representa una variante funcional distinta (p. ej., el test de salud con backend Vault vs. sin él), usad nombres explícitos como `test_ntp_health_check_vault`. Esto da claridad y evita que un guard oculte una diferencia semántica relevante. Si los targets son idénticos en código y solo cambia el enlace, el guard es suficiente; si la lógica interna difiere, separadlos.

Para el caso concreto de hoy, el guard habría evitado el error sin cambiar nombres. Implantadlo ya en `common/CMakeLists.txt` y extended la deuda `DEBT-CMAKE-DUPLICATE-TARGETS-001` para incluir la automatización de la verificación.

---

**2. BACKLOG-CRYPTO-VENDOR-KEY-001 – scope del DAY 164**

El roadmap de 8 fases que aprobamos incluye un veto de merge hasta completar las Fases 0-4. La Fase 1, tal como la enunciasteis, consta de tres actos:

1. Mover `vendor.key` a Vault.
2. Leer la clave pública desde `ARGUS_VENDOR_PUBKEY_HEX` en Jenkins.
3. Configurar AppRole por componente (Jenkins ↔ Vault) listo para producción.

La lectura desde variable de entorno **cubre funcionalmente** la necesidad inmediata (la build enterprise puede firmar/verificar sin el secreto en repositorio), pero **no cierra la fase** a los ojos del veto. El AppRole es el mecanismo que garantiza que el secreto no se obtenga sin autenticación explícita y efímera. Sin él, la variable de entorno es un secreto estático en la configuración de Jenkins, con una superficie de exposición mayor.

**Veredicto:**
- Si queréis levantar el veto de merge tras el DAY 164, debéis implementar el AppRole completo en la misma jornada.
- Si el AppRole se pospone (por dependencias externas, petición de infraestructura, etc.), la Fase 1 queda en estado *“provisionalmente funcional”*, pero el veto se mantiene. En ese caso, abrid una tarea de deuda técnica específica (`DEBT-VAULT-APPROLE-GAP`) y acordad un plazo máximo (máximo 2 días) para completarla; el Consejo aceptará un merge con ese ticket abierto y bloqueante para el siguiente paso de integración.

Os sugerimos planificar el DAY 164 para cubrir los tres puntos; el AppRole no debería llevar más de un par de horas si el operador de Vault ya está disponible.

---

**3. EMECAS++ Acto I – cobertura enterprise con VaultProvider**

El Acto I es un gate de compilación y paso de tests unitarios. Su propósito es demostrar que la rama *compila correctamente con todas las flags de enterprise activadas* y que los nuevos artefactos no rompen lo existente.

Por tanto, **es suficiente** con que:
- El código que invoca `VaultProvider` compile sin errores.
- Los tests unitarios que mockean `VaultProvider` o usan un `VaultProvider` falso pasen.
- La VM efímera se levante con `SeedFileProvider` como backend por defecto (Modelo B), porque la inicialización de Vault real requiere secretos que aún no están en el pipeline (el propio `vendor.key`, justamente lo que estáis moviendo).

No forcéis un test E2E contra una instancia real de Vault en este Acto; eso pertenece al Acto II (tests de integración enterprise) y estará listo cuando `BACKLOG-CRYPTO-VENDOR-KEY-001` esté cerrado y el pipeline pueda inyectar el token de AppRole. Para no perder el hilo, cread la tarea `DEBT-EMECAS-E2E-VAULT-001` y asociadla a esa historia.

**Resumen ejecutivo:**
- Acto I → build verde enterprise + tests unitarios con mocks.
- Acto II → integración real con Vault, alimentada por AppRole, cuando la Fase 1 esté completa.

El Consejo considera que este enfoque mantiene el equilibrio correcto entre velocidad y cobertura, y evita que una dependencia de infraestructura bloquee la verificación diaria.