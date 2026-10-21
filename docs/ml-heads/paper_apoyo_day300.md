# Apoyo para el paper — DAY300

Material para la reescritura honesta del paper. Todo medido en el laboratorio (VirtualBox, XDP genérico,
build production). Las cifras absolutas dependen de la máquina; las relaciones y los mecanismos, no.

## 1. La persistencia necesita una parada ordenada, y la parada ordenada hay que medirla

En DAY299 se midió que ningún componente del laboratorio había ejecutado jamás su parada ordenada
(`tmux kill-session` = SIGHUP no tratado). Al arreglarlo apareció el siguiente fallo: cuatro hilos con sueños de
30 s no interrumpibles. La parada es una ruta de código que casi nunca se ejercita y que solo se puede dar por
buena midiéndola (tiempo hasta la salida, marcas en el log, edad del estado restaurado).

## 2. Medir una máscara de señales exige entender qué enseña el kernel

Con `sigwait`, el hilo que espera aparece en `/proc` con SigBlk=0: el kernel le desbloquea temporalmente las
señales mientras espera. Una comprobación ingenua («todos los hilos deben tener las señales bloqueadas») falla
justo en el hilo correcto. La predicción fallida se explicó, no se ajustó: la comprobación válida es SigBlk en
los demás hilos y `wchan = do_sigtimedwait` en el principal.

## 3. El estado por víctima sobrevive a un corte

Reinicio a mitad de un ataque de 60 pps (por debajo del umbral absoluto de 200 pps):

| Modo | Marcados después / antes | DROP / ataque en cable |
|---|---|---|
| sin estado | 0,000 | 0,416 |
| parada ordenada | 1,305 | 0,924 |
| kill -9 (volcado periódico de 34 s) | 1,236 | 0,920 |

Sin estado, un ataque por debajo del umbral absoluto se aprende como base y deja de marcarse. Con estado, lo
único que no se marca es el tiempo con el sensor caído (~25-30 s): ceguera física, no pérdida de memoria. El
kill -9 reproduce un corte de luz.

## 4. Detectar no es decidir: rangos protegidos

La cabeza DDoS clasifica tipos de tráfico, no intenciones: un host interno comprometido o un reflector propio
mal configurado producen el mismo tráfico que un atacante externo (DAY294: el gemelo inocente se marcaba
igual). Separar la decisión de bloqueo de la detección permite seguir viendo (`ALERTA_PROTEGIDO`) sin
bloquear. Medido: con un origen protegido y otro no, sobre la misma víctima y en el mismo segundo, el episodio
contiene solo el no protegido y la contabilidad cierra sin resto: 16113 = 10742 + 5371.

## 5. Amenaza a la validez: el laboratorio es todo privado

En el laboratorio, atacante e inocentes comparten la subred privada 192.168.100.0/24. El defecto seguro de
producción (proteger RFC 1918) haría imposible medir la cabeza DDoS en el lab, así que el JSON del lab declara
explícitamente qué simula Internet y qué un host interno. Los resultados de laboratorio dependen de esa
declaración; en un despliegue real los rangos los calculará el script de cada instalación.

## 6. Predicciones fallidas del día, todas explicadas

- Corte del log antes de la parada (17 s de `vagrant ssh`): 997 marcados del sensor viejo contados como
  «después». Error de protocolo; el firewall, con marcas de tiempo, ya daba 0.
- Marcas de tiempo tomadas a mano: margen de ±2 s insuficiente; se sustituyó por `volcado_wall_ns`.
- Hipótesis de esperas de 1 s en las colas: falsa (son 100 ms); la causa era el bucle principal.
- Mecanismo supuesto (SIGHUP de tmux) para un segundo sniffer: falso; la secuencia real se reconstruyó del log.
- 36 comprobaciones previstas, 38 medidas: error de recuento, no del test.
