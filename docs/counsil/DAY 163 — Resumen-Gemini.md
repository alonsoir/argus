¡Saludos, ingenieros! El Consejo de Sabios se ha reunido de urgencia para evaluar el avance. En primer lugar, enhorabuena por cazar la regresión del DAY 167 y devolver `EMECAS++` al verde operacional en poco más de una hora. Es un gran hito para la estabilidad del pipeline.

Aquí tenéis nuestro dictamen y las directrices para el **DAY 164**.

---

## 1. Patrón CMake para targets condicionales

El Consejo **desaconseja** el uso sistemático de `if(NOT TARGET <nombre>)` como solución general. Aunque evita el error de compilación, suele enmascarar problemas estructurales y dependencias cruzadas en el orden de inclusión de los `CMakeLists.txt`.

Para solucionar la deuda `DEBT-CMAKE-DUPLICATE-TARGETS-001`, preferimos las siguientes buenas prácticas:

* **Enfoque Idiomático (Recomendado):** Definir el target **una sola vez** de manera global y utilizar comandos condicionales para inyectar fuentes o dependencias específicas de Enterprise.
```cmake
add_executable(test_ntp_health_check ${COMMON_SOURCES})

if(ARGUS_VAULT_ENABLED)
    target_sources(test_ntp_health_check PRIVATE vault_mock.cpp)
    target_compile_definitions(test_ntp_health_check PRIVATE WITH_VAULT)
endif()

```


* **Enfoque de Identidad Única:** Si el test con Vault habilitado es un binario conceptualmente distinto (mide cosas diferentes, tiene otras dependencias), cambiadle el nombre a `test_ntp_health_check_vault`. Duplicar el nombre exacto de un target bajo flags condicionales siempre acaba pasando factura a largo plazo.

---

## 2. BACKLOG-CRYPTO-VENDOR-KEY-001 — Scope DAY 164

Respecto al corte de la Fase 1 para la jornada de mañana:

> **Dictamen:** La lectura de la pubkey desde la variable de entorno de Jenkins (`ARGUS_VENDOR_PUBKEY_HEX`) **es suficiente** para cerrar la Fase 1, siempre y cuando esa variable sea inyectada dinámicamente por el nodo de Jenkins tras una autenticación huérfana temporal contra Vault.

El **AppRole por componente** (producción-ready) tiene entidad suficiente para ocupar su propio espacio de trabajo. Podéis secuenciarlo para la siguiente jornada. No viola el veto de merge acordado, ya que el pipeline sigue estando protegido en el Acto I y la clave no se está embebiendo en el artefacto final de forma estática.

---

## 3. EMECAS++ Acto I — Cobertura Enterprise

Para el DAY 164, **es suficiente con que compile y pasen los tests unitarios**.

Exigir `VaultProvider` real en el bootstrap de la VM del Acto I en este punto del desarrollo os va a meter en un bloqueo circular (necesitáis la infraestructura del AppRole de la pregunta 2 para que el proveedor real funcione de forma segura en entornos efímeros).

* **Acción:** Mantened el `SeedFileProvider` en el Modelo B efímero por ahora.
* **Condición:** Aseguraos de que el bloque condicional compile correctamente con `-DARGUS_VAULT_ENABLED=ON` y que los mocks unitarios verifiquen el comportamiento del flujo. Ya habrá tiempo de transicionar al proveedor real una vez que el backend de Vault esté completamente integrado con el ciclo de vida de las VMs de test.

---

Considerando el diseño de la inyección de dependencias que vais a implementar mañana, **¿cómo tenéis pensado gestionar el ciclo de vida y la rotación de la credencial temporal que usará Jenkins para extraer esa `ARGUS_VENDOR_PUBKEY_HEX` de Vault?**