Perfecto. Aquí tienes un **borrador completo de ADR** para tu enfoque de LLM confinado con skills, listo para integrarlo en el backlog:

---

# ADR: Uso de LLM confinado con skills controladas para RAG-Security

## Contexto

El proyecto **RAG-Security** requiere integrar un modelo de lenguaje (LLM) para procesar información interna, generar salidas estructuradas y ejecutar acciones controladas sobre la infraestructura de manera automatizada.

Se evaluó el uso de **MCP (Model Context Protocol)** como estándar de integración de skills, pero se identificaron problemas críticos:

* MCP depende de un **servidor web o de aplicaciones**, cuya seguridad nunca puede garantizarse completamente.
* La comunicación con el LLM a través de MCP implica exposición a la red, aumentando la superficie de ataque.
* La naturaleza **no determinista del LLM** genera variabilidad en salidas y comportamientos, difícil de controlar en producción.

Por estas razones, se opta por un enfoque **totalmente confinado**, con skills muy concretas, controladas y auditables, limitando al LLM al espacio de acciones estrictamente necesario para su función.

---

## Decisión

Se adoptará la siguiente arquitectura:

1. **LLM confinado internamente**

    * No tiene acceso a Internet ni a recursos externos fuera del pipeline interno.
    * Interactúa únicamente con:

        * Base de datos interna SQLite
        * Índices locales Faiss
        * Pipeline de procesamiento controlado
        * Comandos autorizados del sistema via SSH

2. **Skills controladas**

    * Cada skill tiene un objetivo muy concreto y devuelve **JSON siempre bien formado**.
    * No se permite ejecución arbitraria ni acceso a recursos fuera de los definidos.
    * Validación estricta de entradas y salidas para evitar inyecciones o corrupción.

3. **Cierre de sockets**

    * Todo socket inbound y outbound al exterior se bloquea.
    * El único canal permitido es **SSH hacia comandos autorizados**, replicando un patrón seguro y auditado.

4. **Auditoría y trazabilidad**

    * Todas las llamadas del LLM a skills y comandos se registran.
    * La persistencia de datos está limitada a SQLite y Faiss bajo validación estricta.

5. **Mitigación de no determinismo**

    * El LLM opera en un entorno reducido y predefinido para reducir variabilidad.
    * Salidas no deterministas se validan y corrigen antes de afectar sistemas críticos.

---

## Alternativas consideradas

| Alternativa            | Pros                                   | Contras                                                                                   |
| ---------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------- |
| Uso de MCP estándar    | Estandarizado, portable                | Depende de servidores web inseguros, exposición de red, difícil de controlar determinismo |
| LLM sin confinamiento  | Flexibilidad total, integración rápida | Superficie de ataque enorme, riesgo de fugas y comportamiento impredecible                |
| LLM confinado + skills | Control, seguridad, trazabilidad       | No portable, cada implementación es única, mantenimiento continuo                         |

---

## Riesgos y mitigaciones

| Riesgo                                   | Mitigación                                                         |
| ---------------------------------------- | ------------------------------------------------------------------ |
| Bugs o exploits en skills                | Validación estricta de entradas y salidas, revisiones de código    |
| JSON malformado o inyecciones indirectas | Parser robusto y validación schema-driven                          |
| Corrupción de datos en SQLite o Faiss    | Copias de seguridad, validaciones y transacciones atómicas         |
| Dependencia del sistema operativo y SSH  | Hardenización de OS, actualización de OpenSSH, logging y auditoría |
| No determinismo residual del LLM         | Validación y reintentos controlados, espacio de acción restringido |

---

## Consecuencias

* La arquitectura es **alta seguridad y control**, adecuada para entornos sensibles.
* La solución no es portable ni estandarizable globalmente; cada aplicación requiere definición propia de skills y pipelines.
* Se establece una base sólida para **desarrollo futuro** y escalado a clientes internos o externos bajo control total del LLM.

---

Si quieres, puedo hacer un **diagrama visual** de esta arquitectura para adjuntarlo al ADR y que quede aún más claro para revisores o stakeholders. Esto haría que la decisión se vea tangible y fácil de auditar. ¿Quieres que haga ese diagrama?

```mermaid
flowchart TD
    subgraph LLM_Confined["LLM Confinado"]
        A[LLM] 
    end

    subgraph Skills["Skills Controladas"]
        B1[Skill: Consultar SQLite]
        B2[Skill: Acceder Faiss]
        B3[Skill: Ejecutar comando autorizado via SSH]
    end

    subgraph Pipeline["Pipeline Interno"]
        C1[Preprocesamiento]
        C2[Validación de Salida JSON]
        C3[Postprocesamiento / Logging]
    end

    subgraph DataStore["Persistencia"]
        D1[SQLite]
        D2[Faiss]
    end

    %% Conexiones
    A -->|Invoca| B1
    A -->|Invoca| B2
    A -->|Invoca| B3

    B1 --> D1
    B2 --> D2
    B3 -->|Acceso restringido| Pipeline

    B1 -->|Salida JSON validada| C2
    B2 -->|Salida JSON validada| C2
    B3 -->|Salida JSON validada| C2

    C2 --> C3
    C3 -->|Logs / Auditoría| DataStore

    %% Bloqueos
    style LLM_Confined fill:#f9f,stroke:#333,stroke-width:2px
    style Skills fill:#9ff,stroke:#333,stroke-width:2px
    style Pipeline fill:#ff9,stroke:#333,stroke-width:2px
    style DataStore fill:#9f9,stroke:#333,stroke-width:2px


### Cómo leerlo:
- **LLM Confinado**: Genera solicitudes únicamente a los skills definidos.  
- **Skills Controladas**: Cada skill tiene un objetivo concreto y devuelve siempre JSON validado.  
- **Pipeline Interno**: Se asegura de validar y auditar todas las salidas antes de persistir o actuar.  
- **Persistencia**: SQLite y Faiss bajo control estricto.  
- **Restricciones**: No hay conexión a Internet ni recursos externos, solo canales controlados (SSH).  

Este diagrama deja claro **la separación de responsabilidades**, el **confinamiento del LLM** y dónde se aplican controles de seguridad y auditoría.  

Si quieres, puedo preparar una **versión extendida del diagrama** que también marque **todos los riesgos identificados y mitigaciones** directamente sobre el flujo, para que quede completo dentro del ADR. ¿Quieres que haga eso?

```mermaid
flowchart TD
    %% Nodos principales
    subgraph LLM_Confined["LLM Confinado"]
        A[LLM] 
    end

    subgraph Skills["Skills Controladas"]
        B1[Skill: Consultar SQLite]
        B2[Skill: Acceder Faiss]
        B3[Skill: Ejecutar comando autorizado via SSH]
    end

    subgraph Pipeline["Pipeline Interno"]
        C1[Preprocesamiento]
        C2[Validación de Salida JSON]
        C3[Postprocesamiento / Logging]
    end

    subgraph DataStore["Persistencia"]
        D1[SQLite]
        D2[Faiss]
    end

    %% Conexiones
    A -->|Invoca| B1
    A -->|Invoca| B2
    A -->|Invoca| B3

    B1 --> D1
    B2 --> D2
    B3 -->|Acceso restringido| Pipeline

    B1 -->|Salida JSON validada| C2
    B2 -->|Salida JSON validada| C2
    B3 -->|Salida JSON validada| C2

    C2 --> C3
    C3 -->|Logs / Auditoría| DataStore

    %% Bloqueos y restricciones
    style LLM_Confined fill:#f9f,stroke:#333,stroke-width:2px
    style Skills fill:#9ff,stroke:#333,stroke-width:2px
    style Pipeline fill:#ff9,stroke:#333,stroke-width:2px
    style DataStore fill:#9f9,stroke:#333,stroke-width:2px

    %% Riesgos y mitigaciones
    subgraph Risks["Riesgos y Mitigaciones"]
        R1["Riesgo: Bugs o exploits en skills → Mitigación: Validación de entradas/salidas, revisiones de código"] 
        R2["Riesgo: JSON malformado / inyección → Mitigación: Parsers robustos y schema-driven"] 
        R3["Riesgo: Corrupción de datos → Mitigación: Copias de seguridad, validaciones, transacciones atómicas"] 
        R4["Riesgo: No determinismo del LLM → Mitigación: Espacio de acción restringido, reintentos controlados"] 
        R5["Riesgo: Dependencia de SSH/OS → Mitigación: Hardenización, actualización de OpenSSH, logging/auditoría"]
        R6["Riesgo: Fugas de información → Mitigación: Skills limitados, validación estricta, logs controlados"]
    end

    %% Enlazar riesgos a componentes
    R1 -.-> B1
    R1 -.-> B2
    R1 -.-> B3

    R2 -.-> C2
    R3 -.-> D1
    R3 -.-> D2

    R4 -.-> A
    R5 -.-> B3
    R6 -.-> B1
    R6 -.-> B2
    R6 -.-> B3


### Claves del diagrama extendido:
- **Componentes coloreados** muestran LLM, skills, pipeline y persistencia.  
- **Riesgos** se representan como nodos conectados con líneas punteadas a los elementos donde pueden ocurrir.  
- **Mitigaciones** se listan junto a cada riesgo, dejando claro cómo se protegen los puntos críticos.  
- Este diagrama puede incorporarse directamente al ADR como referencia visual para el backlog, mostrando **confinamiento, seguridad y trazabilidad**, así como los riesgos controlados.

Si quieres, puedo preparar **una versión aún más “lista para presentación a stakeholders”**, con colores de riesgo (alto/medio/bajo) y leyendas de mitigación directamente visibles sobre los flujos, para que quede **intuitivo y profesional** dentro del ADR. ¿Quieres que haga eso también?