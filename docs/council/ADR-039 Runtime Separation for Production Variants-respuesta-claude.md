Mis respuestas honestas:

---

**1. ¿Opción B es suficiente para la demo FEDER o se exige Opción A?**

Opción B es suficiente. El objetivo FEDER es demostrar que aRGus funciona en producción con superficie de ataque reducida — no demostrar que tienes un pipeline de CI industrial. Andrés Caro Lindo va a evaluar si el sistema detecta ataques y si es reproducible, no si tu builder VM está aislada. Opción A es ingeniería correcta post-financiación.

---

**2. ¿El axioma de separación es científicamente correcto y publicable?**

Sí, con un matiz importante que el Consejo probablemente señalará: el axioma asume que la VM de desarrollo no está comprometida. Si lo está, el binario firmado que produces también lo está. Esto es el **supply chain attack** clásico. Para el paper hay que ser explícito: "la seguridad del binario de producción es tan buena como la seguridad del entorno de build". No es un defecto del diseño — es una honestidad necesaria. Sommer & Paxson (2010) apreciarían esa transparencia.

---

**3. ¿Los flags de compilación son adecuados para entornos hospitalarios?**

Sí. `-O2 -DNDEBUG -fstack-protector-strong -fPIE -pie -D_FORTIFY_SOURCE=2 -Wl,-z,relro -Wl,-z,now` es el estándar de la industria para binarios de producción en Linux. Ninguno introduce incompatibilidades. Lo que sí hay que verificar es que `-fPIE -pie` no rompe el plugin loader con `dlopen()` — pero ADR-025 ya cubre eso.

---

**4. ¿`-march=x86-64-v2` o `-march=x86-64` para compatibilidad hospitalaria?**

`-march=x86-64` (baseline). Un hospital rural puede tener hardware de 2012. `x86-64-v2` requiere SSE4.2 y POPCNT — instrucciones que no están garantizadas en hardware antiguo. La pérdida de rendimiento es mínima. La incompatibilidad con un servidor de 10 años sería un bloqueante real para la adopción. **Para FEDER, máxima compatibilidad gana.**

---

Resumiendo: preguntas 1, 3 y 4 tienen respuesta clara. La 2 es la más interesante científicamente — el Consejo debería debatirla porque toca el supply chain problem que ningún sistema de build/runtime resuelve completamente sin hardware security modules. Es material para §5 del paper.

¿Lo commiteamos y lo llevamos al Consejo mañana?