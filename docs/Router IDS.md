# Proyecto IDS en Router Open Source: Plan y Requisitos

Este documento reúne de manera integral toda la planificación, requisitos de hardware y software, estrategia de pruebas y actualización de firmware para el desarrollo de un IDS (Intrusion Detection System) que se integra directamente en un router doméstico o mini-PC, con control total sobre la infraestructura.

Se trata de un documento histórico y de referencia para el proyecto, que demuestra la cooperación entre humanos y sistemas de IA.

---

## 1. Objetivos y Requisitos Innegociables

1. **Root completo en el dispositivo**:

    * Sniffer y firewall-acl-agent deben ejecutar procesos con privilegios de superusuario.
    * Necesario para acceder a la NIC dominante y modificar ACLs dinámicamente.

2. **Doble NIC físico**:

    * Una NIC para tráfico WAN (exterior) y otra para LAN (interior).
    * Aisla tráfico filtrado y reduce carga en la CPU.

3. **Kernel moderno**:

    * Kernel ≥ 6.1.x.
    * Permite soporte de NICs modernas, AppArmor y seguridad hardening.

4. **Capacidad de procesamiento y almacenamiento**:

    * CPU multi-core suficiente para ML en tiempo real.
    * RAM 8–16 GB mínimo.
    * Almacenamiento SSD/HDD de al menos 256 GB para logs, modelos y snapshots.

5. **Firmware Open Source en GitHub**:

    * Mantenido activamente, compatible con licencias libres.
    * Posibilidad de fork para añadir IDS, firewall, AppArmor y actualizaciones.

6. **Actualizaciones controladas**:

    * Componente `etcd` para descargas de paquetes, firmware y modelos.
    * Fusiones periódicas con rama principal upstream para seguridad.

---

## 2. Hardware de Laboratorio Económico (Validación)

| Modelo                 | CPU / Núcleos            | RAM     | NICs                        | Kernel compatible      | Comentarios                                                                          |
| ---------------------- | ------------------------ | ------- | --------------------------- | ---------------------- | ------------------------------------------------------------------------------------ |
| Qotom Q190P / Q192P    | Intel i3/i5, 2–4 núcleos | 4–8 GB  | 2–4 LAN                     | Linux 6.1.x compilable | Económico (~€90–150), doble NIC real, Debian compatible                              |
| Intel NUC 6th/7th gen  | i3/i5, 2–4 núcleos       | 4–16 GB | 1 LAN integrada + 1 USB NIC | Linux 6.1.x            | Fácil de comprar, permite pruebas en portatil y migrar a físico                      |
| PC Engines APU6 / Noah | AMD GX-412TC, 4 hilos    | 4 GB    | 3 NIC Intel                 | Linux 6.1.x            | Hardware más libre, firmware coreboot, RAM limitada, suficiente para pruebas ligeras |

* Este hardware permite **probar todo el pipeline software** en entorno aislado (Vagrant/Debian), incluyendo sniffer y firewall-acl-agent.
* Doble NIC virtualizada en portatil sirve para simulaciones iniciales.

---

## 3. Hardware Potente para Prototipo Físico de Demostración

| Modelo                     | CPU / Núcleos                | RAM      | NICs      | Kernel compatible | Comentarios                                                     |
| -------------------------- | ---------------------------- | -------- | --------- | ----------------- | --------------------------------------------------------------- |
| Protectli Vault Pro VP6670 | Intel i7 / múltiples núcleos | 16–64 GB | 6 puertos | Linux 6.1.x       | Gran capacidad para ML y tráfico real, ideal para demo completa |
| Protectli Vault Fw2B       | Intel i3/i5, 2–4 núcleos     | 8–16 GB  | 2 puertos | Linux 6.1.x       | Más asequible, buena para prototipo, menos puertos              |

* Se utilizará para **mostrar prototipo completo a inversores** y validar rendimiento real.
* Permite pruebas de laboratorio aisladas con tráfico simulado y ataques controlados.

---

## 4. Firmware y Fork Personalizado

1. **Partir de firmware open source con kernel ≥6.1**:

    * OpenWrt, VyOS, pfSense o similar.
    * AppArmor/hardening activado por defecto.

2. **Crear fork en GitHub**:

    * Integrar IDS, firewall-acl-agent y scripts de actualización.
    * Mantener merge con rama upstream para seguridad y estabilidad.

3. **Automatización de actualizaciones**:

    * `etcd` actúa como puente de descarga de paquetes, firmware y modelos.
    * Permite actualizaciones seguras y controladas sin comprometer la infraestructura.

---

## 5. Estrategia de Validación en Laboratorio Virtual

1. **Configuración de red aislada**:

    * Portatil con doble NIC virtualizada.
    * Mini-PCs y smartphones de test conectados al router virtual.
    * Entorno totalmente aislado de redes productivas.

2. **Pruebas de resiliencia**:

    * Uso de herramientas de investigación (Nocturne-Attack y similares).
    * Simulación de DDoS, payloads y ransomware para medir respuesta.

3. **Iteración de software**:

    * Ajustar IDS y firewall dinámico.
    * Reentrenar modelos con tráfico normal y sintético.
    * Validar descargas de actualizaciones y modelos desde infraestructura externa.

4. **Medición y métricas**:

    * CPU, RAM, throughput, latencia de ACLs, logs.
    * Cuellos de botella identifican limitaciones del hardware de pruebas.

---

## 6. Estrategia de Transición a Hardware Físico

1. Validar software completo en portatil y entorno Vagrant.
2. Seleccionar mini-PC económico con doble NIC y kernel 6.1.
3. Instalar fork de firmware con kernel y AppArmor.
4. Ejecutar pruebas aisladas con tráfico simulado y ataques controlados.
5. Documentar métricas para inversores y preparar escalado a hardware más potente.

---

## 7. Documentación y Conservación del Proyecto

* Todo el proyecto debe conservarse como referencia histórica.
* Esta documentación se mantiene en formato Markdown para versionado, actualización y difusión.
* Sirve como guía de desarrollo, validación de software, integración de hardware y estrategia de pruebas de seguridad.

---

**Fin del documento: Proyecto IDS en Router Open Source – Plan y Requisitos**
