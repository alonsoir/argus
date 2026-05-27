Unanimidad casi total en los 8 modelos. Sintetizo el consenso real antes de las dudas:

---

**Q1 — .deb vs Vagrant:** 8/8 dicen ambos, `.deb` como artefacto primario, Vagrant como entorno de validación. La Vagrant box se genera **desde el `.deb`**, nunca al revés. Esto es más fuerte que mi posición inicial — el matiz de ChatGPT es el correcto.

**Q2 — Valores naive:** 8/8 hardcoded para DAY 161. ChatGPT y Kimi añaden algo que yo no dije: perfiles por hardware (`edge-low/medium/high`) en lugar de un único valor. Eso es más inteligente que un solo hardcoded.

**Q3 — Token:** 8/8 Jenkins Credentials. Grok y Qwen van más lejos: AppRole en lugar de token estático. Es la arquitectura correcta para producción. Para DAY 161 dev mode, Secret Text es suficiente. AppRole va en el Vagrantfile de staging.

**Q4 — Wire protocol:** 8/8 antes. Mistral es el más duro: si no está cerrado, no proceder con DAY 161. Comparto esa posición — son 30 minutos, no hay excusa.

**Q5 — Vault dev mode:** Hay una divergencia interesante. Yo y la mayoría: no bloqueante para FEDER si el prospecto lo documenta. Mistral dice bloqueante. La posición más honesta está en el medio: no bloqueante para el pipeline de CI, **sí bloqueante para la demo final FEDER**. Hay que abrir `DEBT-VAULT-PROD-SETUP-001` con deadline explícita — primera semana de septiembre.

---

**Decisiones que actualizo respecto a mi posición inicial:**

1. `.deb` multi-arch desde el primer día — arm64 para RPi5, x86_64 para N100.
2. Perfiles de hardware (`edge-low/medium/high`) en lugar de valores hardcoded planos.
3. AppRole en el roadmap explícito, no como "post-FEDER vago".
4. `DEBT-VAULT-PROD-SETUP-001` con deadline septiembre — nueva deuda a abrir.

---

¿Cuáles son tus dudas?