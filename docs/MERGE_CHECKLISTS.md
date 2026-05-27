# Checklist de Merge a Main - feature/eth0-vagrantfile

## Pre-requisitos

- [ ] Estás en la branch `feature/eth0-vagrantfile`
- [ ] No hay cambios sin commitear (`git status` limpio)
- [ ] Vagrant está instalado y funcionando
- [ ] VirtualBox está instalado

## Fase 1: Validación Automatizada

### 1.1 Ejecutar Script de Validación

```bash
# Desde el directorio raíz del proyecto
chmod +x scripts/pre-merge-validation.sh
./scripts/pre-merge-validation.sh
```

**Resultado esperado**: Todos los tests deben pasar (TESTS_FAILED = 0)

### 1.2 Si hay fallos

Si el script reporta fallos:

1. Revisa el output detallado de cada test fallido
2. Ejecuta el diagnóstico de red:
   ```bash
   vagrant ssh
   cd /vagrant
   ./scripts/network_diagnostics_enhanced.sh
   ```
3. Corrige los problemas identificados
4. Vuelve a ejecutar `pre-merge-validation.sh`

## Fase 2: Validación Manual del Sniffer

### 2.1 Verificar eth2 específicamente

```bash
vagrant ssh
```

Dentro de la VM:

```bash
# Ver configuración de eth2
ip addr show eth2

# Debe mostrar algo como:
# 3: eth2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
#     inet 192.168.1.XXX/24 brd 192.168.1.255 scope global dynamic eth2
```

- [ ] eth2 existe
- [ ] eth2 tiene estado UP
- [ ] eth2 tiene IP de tu red local (192.168.X.X o 10.X.X.X)

### 2.2 Test de captura en eth2

```bash
# Generar tráfico en eth2
ping -c 10 -I eth2 8.8.8.8 &

# En otra terminal de la VM
cd /vagrant
sudo ./sniffer/build/sniffer --verbose
```

**Resultado esperado**:
- El sniffer debe mostrar que está escuchando en eth2
- Debe capturar paquetes del ping

### 2.3 Test del script de captura

```bash
cd /vagrant
./scripts/capture_zeromq_traffic.sh eth2 30

# Verificar que se creó el archivo
ls -lh /tmp/zeromq_captures/
```

- [ ] El script ejecuta sin errores
- [ ] Se crea un archivo .pcap con contenido (tamaño > 0)

## Fase 3: Validación del Pipeline Completo

### 3.1 Levantar el pipeline

```bash
cd /vagrant
make lab-start
```

- [ ] Todos los contenedores inician correctamente
- [ ] `docker ps` muestra todos los servicios running

### 3.2 Verificar comunicación

```bash
# Ver logs de service1
docker logs service1

# Debe mostrar mensajes enviados a través de ZeroMQ
```

### 3.3 Detener el pipeline

```bash
make lab-stop
```

- [ ] Todos los contenedores se detienen limpiamente

## Fase 4: Documentación

### 4.1 Verificar documentos actualizados

- [ ] `README.md` menciona eth2 y red bridged
- [ ] `DECISIONS.md` tiene las últimas decisiones
- [ ] Existe `docs/NETWORK_SETUP.md` (si aplicable)

### 4.2 Actualizar CHANGELOG (si existe)

```markdown
## [v3.2.0] - 2025-10-06

### Added
- Configuración de red bridged (eth2) para acceso desde LAN
- Script de validación pre-merge automatizada
- Diagnóstico de red mejorado
- Soporte para captura de tráfico en interfaz WiFi del host

### Fixed
- Detección automática de interfaces de red
- Configuración de variables de entorno para múltiples interfaces

### Changed
- Vagrantfile con 3 interfaces: NAT, Private, Bridged
```

## Fase 5: Merge a Main

### 5.1 Preparar el merge

```bash
# Asegúrate de estar en la branch correcta
git checkout feature/eth0-vagrantfile

# Pull de cambios remotos (si trabajas en equipo)
git fetch origin
git pull origin feature/eth0-vagrantfile

# Actualizar main local
git checkout main
git pull origin main

# Volver a feature branch
git checkout feature/eth0-vagrantfile
```

### 5.2 Rebase opcional (recomendado)

```bash
# Solo si main tiene commits nuevos
git rebase main

# Resolver conflictos si los hay
# Luego:
git rebase --continue
```

### 5.3 Ejecutar tests una vez más

```bash
./scripts/pre-merge-validation.sh
```

- [ ] Todos los tests pasan después del rebase

### 5.4 Hacer el merge

```bash
git checkout main
git merge --no-ff feature/eth0-vagrantfile -m "feat: Add eth2 bridged network support for WiFi capture

- Configure 3 network interfaces: NAT (eth0), Private (eth1), Bridged (eth2)
- Add automated pre-merge validation script
- Enhanced network diagnostics for troubleshooting
- Support for packet capture on host WiFi interface via eth2
- Update documentation with network setup guide

Closes #XX (si tienes un issue asociado)"
```

## Fase 6: Crear Tag

### 6.1 Crear tag semántico

```bash
git tag -a v3.2.0 -m "Version 3.2.0 - Bridged Network Support

Features:
- eth2 bridged network for host WiFi access
- Automated validation pipeline
- Enhanced network diagnostics
- Complete sniffer support for bridged interface

Breaking Changes: None

Migration Guide: 
- Run 'vagrant destroy' and 'vagrant up' to recreate VM with new network config
- Verify eth2 is properly bridged to your WiFi interface
"
```

### 6.2 Verificar el tag

```bash
git tag -l -n9 v3.2.0
git show v3.2.0
```

## Fase 7: Push a Remote

### 7.1 Push main branch

```bash
git push origin main
```

### 7.2 Push tag

```bash
git push origin v3.2.0
```

### 7.3 Verificar en GitHub

- [ ] La branch main tiene el merge
- [ ] El tag v3.2.0 aparece en releases
- [ ] Los workflows de CI pasan (si los tienes)

## Fase 8: Limpieza (Opcional)

### 8.1 Eliminar branch feature (local)

```bash
git branch -d feature/eth0-vagrantfile
```

### 8.2 Eliminar branch feature (remota)

```bash
git push origin --delete feature/eth0-vagrantfile
```

### 8.3 Limpiar Vagrant

```bash
# Solo si quieres empezar limpio
vagrant destroy
vagrant up
```

## Rollback (Si algo sale mal)

### Si el