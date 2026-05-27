# Guía Rápida: Validación y Merge a Main

## TL;DR - Comandos Esenciales

```bash
# 1. Copiar los nuevos scripts al proyecto
cp pre-merge-validation.sh scripts/
cp validate-eth2.sh scripts/
cp network_diagnostics_enhanced.sh scripts/
chmod +x scripts/*.sh

# 2. Commit de los scripts
git add scripts/
git commit -m "feat: Add validation and diagnostics scripts for eth2"

# 3. Ejecutar validación completa
./scripts/pre-merge-validation.sh

# 4. Si pasa, hacer el merge
git checkout main
git merge --no-ff feature/eth0-vagrantfile
git tag -a v3.2.0 -m "Version 3.2.0 - Bridged network support"
git push origin main --tags
```

---

## Opción 1: Validación Completa (Recomendado)

### Paso 1: Preparar Scripts

Copia los 3 scripts que te he creado a tu proyecto:

```bash
cd /ruta/a/argus

# Crear directorio scripts si no existe
mkdir -p scripts

# Copiar los scripts (asumiendo que los guardaste en /tmp)
cp /tmp/pre-merge-validation.sh scripts/
cp /tmp/validate-eth2.sh scripts/
cp /tmp/network_diagnostics_enhanced.sh scripts/

# Dar permisos de ejecución
chmod +x scripts/*.sh

# Añadir al git
git add scripts/pre-merge-validation.sh
git add scripts/validate-eth2.sh
git add scripts/network_diagnostics_enhanced.sh
git commit -m "feat: Add automated validation scripts for network setup

- pre-merge-validation.sh: Complete validation before merging
- validate-eth2.sh: Quick eth2 interface validation
- network_diagnostics_enhanced.sh: Enhanced network diagnostics
"
```

### Paso 2: Ejecutar Validación

```bash
# Asegúrate de que Vagrant está corriendo
vagrant status

# Si no está corriendo
vagrant up

# Ejecutar validación completa
./scripts/pre-merge-validation.sh
```

**Resultado esperado**: Mensaje final `¡TODAS LAS VALIDACIONES PASARON!`

### Paso 3: Validación Específica de eth2

```bash
# Dentro de la VM
vagrant ssh

# Ejecutar validación de eth2
cd /vagrant
./scripts/validate-eth2.sh
```

**Resultado esperado**: `✓ eth2 ESTÁ LISTA PARA USAR CON EL SNIFFER`

### Paso 4: Merge a Main

```bash
# Volver al host
exit

# Hacer el merge
git checkout main
git merge --no-ff feature/eth0-vagrantfile -m "feat: Add eth2 bridged network support

- Configure 3 network interfaces (NAT, Private, Bridged)
- Add automated validation pipeline
- Enhanced network diagnostics
- Support for packet capture on host WiFi via eth2
- Complete documentation update
"

# Crear tag
git tag -a v3.2.0 -m "Version 3.2.0 - Bridged Network Support"

# Push
git push origin main
git push origin v3.2.0
```

---

## Opción 2: Validación Rápida (Mínima)

Si tienes poco tiempo y confías en que todo funciona:

### Validación Manual en 5 Minutos

```bash
# 1. Levantar Vagrant
vagrant up

# 2. Verificar eth2
vagrant ssh -c "ip addr show eth2"
# Debe mostrar una IP de tu red local

# 3. Test de ping desde eth2
vagrant ssh -c "ping -c 3 -I eth2 8.8.8.8"
# Debe responder

# 4. Compilar sniffer
vagrant ssh -c "cd /vagrant && make sniffer-build-local"
# Debe compilar sin errores

# 5. Test rápido del sniffer
vagrant ssh -c "cd /vagrant && timeout 3 sudo ./sniffer/build/sniffer --verbose"
# Debe mostrar que escucha en eth2

# 6. Si todo OK, merge directo
git checkout main
git merge feature/eth0-vagrantfile
git tag v3.2.0
git push origin main --tags
```

---

## Troubleshooting: Problemas Comunes

### Problema 1: eth2 no tiene IP

**Síntoma**: `ip addr show eth2` no muestra `inet X.X.X.X`

**Solución**:
```bash
# Dentro de la VM
sudo dhclient -r eth2  # Liberar IP
sudo dhclient eth2     # Obtener nueva IP

# O reiniciar networking
sudo systemctl restart networking
```

### Problema 2: eth2 no existe

**Síntoma**: `Device "eth2" does not exist`

**Solución**:
```bash
# Salir de la VM
exit

# Recargar Vagrant
vagrant reload

# Verificar Vagrantfile tiene:
# config.vm.network "public_network"
```

### Problema 3: Sniffer no compila

**Síntoma**: Errores al ejecutar `make sniffer-build-local`

**Solución**:
```bash
vagrant ssh

# Instalar dependencias faltantes
cd /vagrant
make install-deps

# Limpiar y recompilar
make sniffer-clean
make sniffer-build-local
```

### Problema 4: No captura paquetes en eth2

**Síntoma**: `tcpdump -i eth2` no muestra tráfico

**Solución**:
```bash
# Verificar que hay tráfico en la interfaz
vagrant ssh -c "sudo ip -s link show eth2"
# Mira RX/TX packets

# Generar tráfico
ping -I eth2 8.8.8.8 &

# Capturar en otra terminal
sudo tcpdump -i eth2 -n
```

### Problema 5: Permisos del sniffer

**Síntoma**: `Permission denied` al ejecutar sniffer

**Solución**:
```bash
# Ejecutar con sudo
sudo ./sniffer/build/sniffer

# O dar capacidades CAP_NET_RAW
sudo setcap cap_net_raw+ep ./sniffer/build/sniffer
./sniffer/build/sniffer  # Ya no necesita sudo
```

---

## Checklist Mínimo para Merge

Antes de hacer el merge, verifica:

- [ ] `vagrant up` funciona sin errores
- [ ] `ip addr show eth2` muestra IP de tu red local
- [ ] `ping -I eth2 8.8.8.8` funciona
- [ ] `make sniffer-build-local` compila sin errores
- [ ] El sniffer detecta eth2 al ejecutarse
- [ ] No hay commits pendientes (`git status`)

Si todos estos puntos pasan, **estás listo para el merge**.

---

## Post-Merge: Verificación

Después del merge, verifica que main funciona:

```bash
# En un directorio temporal
cd /tmp
git clone <tu-repo> test-fresh
cd test-fresh

# Checkout de main
git checkout main

# Levantar desde cero
vagrant up

# Verificar que funciona
vagrant ssh -c "cd /vagrant && ./scripts/validate-eth2.sh"
```

---

## Comandos de Referencia Rápida

```bash
# Ver estado de interfaces
vagrant ssh -c "ip addr show"

# Ver routing
vagrant ssh -c "ip route"

# Diagnóstico completo de red
vagrant ssh -c "cd /vagrant && ./scripts/network_diagnostics_enhanced.sh"

# Validar solo eth2
vagrant ssh -c "cd /vagrant && ./scripts/validate-eth2.sh"

# Validación completa pre-merge
./scripts/pre-merge-validation.sh

# Test del sniffer
vagrant ssh -c "cd /vagrant && sudo ./sniffer/build/sniffer --verbose"

# Captura de 30 segundos en eth2
vagrant ssh -c "cd /vagrant && ./scripts/capture_zeromq_traffic.sh eth2 30"
```

---

## Siguiente Paso

Ejecuta uno de estos dos flujos:

1. **Flujo Completo** (recomendado): Sigue "Opción 1: Validación Completa"
2. **Flujo Rápido** (si tienes prisa): Sigue "Opción 2: Validación Rápida"

¿Listo para empezar? 🚀