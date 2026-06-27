# Consejo ADR-025 Segunda ronda.md

# Antecedentes

Claude:
Hay una pregunta pendiente importante para el Consejo antes de cerrar el ADR, precisamente derivada de lo que acabas de definir sobre `provision.sh --reset`.

**El problema:**

Si la clave pública está hardcoded en el binario (D7), una rotación mensual vía cron significa **recompilar y redesplegar el binario completo** cada mes, además de re-firmar todos los plugins. Eso es operacionalmente costoso y puede ser un problema real en hospitales con ventanas de mantenimiento estrechas.

La alternativa — clave pública en fichero de configuración protegido por AppArmor — es operacionalmente más simple pero ligeramente más débil.

**Pregunta concreta para el Consejo:**

> Dado que provision.sh --reset rotará claves mensualmente (vía cron en build machine o ejecución manual por admin root), y que D7 propone clave pública hardcoded en binario: ¿es aceptable el coste operacional de recompilar + redesplegar el binario en cada rotación, o se debe optar por clave pública en fichero inmutable protegido por AppArmor con hash del fichero embebido en binario como compromiso?

Además hay dos sub-preguntas abiertas que DeepSeek planteó y el Consejo no resolvió explícitamente:

- ¿Qué ocurre con los plugins ya desplegados cuando se rotan las claves? ¿Re-firma obligatoria de todos antes de arrancar?
- ¿El cron corre en la build machine o en el host productivo? Porque si corre en producción, la clave privada estaría en producción — contradice D1.

¿Mandamos esta ronda al Consejo primero, y redacto el ADR-025 completo una vez tengamos esas respuestas?

Alonso:

Si, volvemos a preguntar, esto es importante. En mi opinión, un administrador necesitará o querrá un mecanismo para resetear las claves criptográficas siempre, para tener el control, pero lo ponemos a cargo del consejo. Da tu opinión también, Claude.

Con respecto a las preguntas lanzadas anteriormente, doy mi opinión, que es una más:

1)¿Qué ocurre con los plugins ya desplegados cuando se rotan las claves? ¿Re-firma obligatoria de todos antes de arrancar?
Alonso: 
Preguntemonos que ocurriría si todos los plugins, si todos los componentes de cada familia, siguiera con una clave criptográfica antigua y tenemos que forzar a que roten. Por qué tienen que rotar, en mi opinión, se debe a que la seguridad está comprometida, alguien está envenenando el pipeline desde fuera, y necesitamos volver a tomar el control. En mi opinión, hay que parar, refirmar todo, desechar lo anterior y volver a arrancar. El admin debe VOLVER a guardar las claves privadas en lugar seguro fuera del FS de producción. Esta situación, de ocurrir, dejaría en inutil la posibilidad de guardar el hash del fichero embebido en el binario. Luego, guardar embebido la clave pública del binario compilado en algún fichero del pipeline, entregando el código fuente como vamos a hacer, tampoco me convence mucho. Deberían estar en un lugar del FS donde solo haya permisos de lectura para el root, pero, que pasaría si se hacen con los privilegios del root? necesitamos entonces que algo como Falco vigile esos directorios. Esto es peliagudo, trataremos de llegar a la mejor posición. 
2) ¿El cron corre en la build machine o en el host productivo? Porque si corre en producción, la clave privada estaría en producción — contradice D1.
En mi opinión, en la máquina del pipeline CICD de construcción, externa al host productivo porque no queremos que la clave privada esté en la misma máquina de producción. Si se hacen con ella, adios.

Veamos que nos dice el consejo en esta segunda iteración.

Mi opinión primero, para que entre junto con la tuya en la segunda ronda.

---

## Mi posición (Claude)

**Sobre rotación mensual vía cron:** creo que el framing es incorrecto desde el origen. Cron implica rotación rutinaria. Pero si la clave pública está hardcoded en el binario, rotar implica recompilar y redesplegar — eso no es una tarea de cron, es una operación de mantenimiento planificada. Y si la rotación es respuesta a compromiso de seguridad, tampoco es cron — es respuesta a incidente.

**Propongo separar dos escenarios distintos:**

| Escenario | Trigger | Proceso |
|-----------|---------|---------|
| Rotación preventiva | Decisión admin (trimestral, semestral) | CI/CD: nueva clave → recompila → re-firma plugins → redespliega |
| Rotación de emergencia | Compromiso detectado | Para todo → nueva clave → re-firma todo → redespliega → admin guarda privada offline |

En ninguno de los dos casos tiene sentido cron automático en producción.

**Sobre D7 — clave pública hardcoded:** tu preocupación sobre entregar código fuente abierto es un falso problema. La clave pública *puede* ser pública — su seguridad no depende de ocultarla sino de que la privada esté a salvo. Hardcoded en binario es correcto precisamente porque elimina un fichero en el FS que alguien pueda sustituir.

**Sobre root comprometido:** tienes razón en que si root cae, el juego cambia completamente. Pero eso ya está en el modelo de Falco como capa de detección. No podemos diseñar el plugin-loader para resistir un root comprometido — ese es el trabajo de Falco + imagen hardened. Lo que sí podemos hacer es que Falco vigile los directorios de plugins y claves con alertas de nivel crítico.

**Sobre re-firma de plugins en rotación:** coincido contigo completamente. Estado parcial (algunos plugins firmados con clave nueva, otros con la antigua) es inaceptable. Todo o nada.

---

## Segunda ronda — Pregunta al Consejo

> **Contexto acumulado:**
> ADR-025 establece firma Ed25519 offline (clave privada nunca en host productivo) con clave pública hardcoded en binario. La rotación de claves implica recompilar + redesplegar el binario completo + re-firmar todos los plugins.
>
> **Decisiones ya tomadas por el árbitro:**
> - Cron de rotación corre en build machine externa, nunca en producción
> - En rotación de emergencia: parada total del pipeline, re-firma completa, descarte de todo lo anterior, nueva clave privada offline en custodia del admin
> - Estado parcial (plugins con claves mezcladas) es inaceptable — todo o nada
>
> **Preguntas al Consejo:**
>
> **P1 — Trigger de rotación:**
> ¿Debe `provision.sh --reset` ser exclusivamente una operación manual de admin con privilegios root (sin cron automático), dada la gravedad operacional de una rotación? ¿O tiene sentido un cron como recordatorio sin ejecución automática (notificación sin acción)?
>
> **P2 — Coste operacional de D7:**
> Dado que rotar la clave pública hardcoded en binario exige recompila + redespliega: ¿es este coste aceptable si la rotación es excepcional (respuesta a incidente, no rutina mensual)? ¿O se debe adoptar clave pública en fichero root-only con Falco vigilando el directorio, asumiendo que root comprometido es un threat model de capa superior?
>
> **P3 — provision.sh --reset: comportamiento esperado:**
> Al ejecutar `--reset`, el script debe: (1) advertir explícitamente sobre la naturaleza de la clave privada y exigir confirmación, (2) estampar fecha/hora de creación en el nombre del fichero o en metadatos, (3) después de generar el nuevo par, ¿debe invalidar activamente los `.sig` existentes (borrarlos o marcarlos), o es responsabilidad del admin re-firmar antes de arrancar? ¿Debe bloquearse el arranque del pipeline si detecta que los `.sig` fueron firmados con una clave distinta a la clave pública actual en el binario?
>
> **P4 — Falco como capa de detección:**
> Dado que root comprometido rompe cualquier mecanismo en userspace: ¿debe el ADR-025 documentar explícitamente que Falco (ya en el roadmap como capa complementaria) es la mitigación para este threat model, o se considera fuera de scope del ADR y se referencia a un ADR futuro de runtime monitoring?

---

¿Lo mandas así al Consejo?