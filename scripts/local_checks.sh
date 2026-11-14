#!/bin/bash
# =============================================================================
# Script educativo de comprobaciones locales básicas
# =============================================================================
# Este script SOLO implementa unas pocas comprobaciones locales e inofensivas
# inspiradas en conceptos de detección de red/entorno.
#
# NO implementa:
# - Ejecución remota de comandos
# - Volcado de conexiones / análisis de tráfico
# - Sistemas de puntuación de riesgo / KYC
# - Monitorización de redes sociales o GitHub
# - Clasificadores o listas de bloqueo
# - Lectura de GPS u otras técnicas que requieren privilegios o hardware específico
#
# Uso: ./local_checks.sh
# Requiere: bash, comandos básicos de Linux (ping, ip, etc.)
# =============================================================================

set -euo pipefail

echo "=== Comprobaciones locales básicas (educativo) ==="
echo

# 1. Variable SSH_CONNECTION (si existe)
echo "[1] Variable de entorno SSH_CONNECTION:"
if [[ -n "${SSH_CONNECTION:-}" ]]; then
    echo "    Valor: $SSH_CONNECTION"
    echo "    (Contiene IP del cliente, puerto, etc. cuando la sesión es por SSH)"
else
    echo "    No definida (no estás en una sesión SSH o la variable no está presente)"
fi
echo

# 2. Información básica de interfaces de red
echo "[2] Interfaces de red y direcciones:"
ip -brief addr show 2>/dev/null || ifconfig -a 2>/dev/null || echo "    No se pudo obtener información de interfaces"
echo

# 3. Medición simple de latencia (ejemplo a un host público)
echo "[3] Medición básica de latencia (ping a 1.1.1.1):"
if command -v ping >/dev/null 2>&1; then
    ping -c 3 -W 2 1.1.1.1 2>/dev/null | tail -n 2 || echo "    No se pudo completar el ping"
else
    echo "    Comando 'ping' no disponible"
fi
echo

# 4. Información de hardware de red (si está disponible)
echo "[4] Información básica de dispositivos de red:"
if command -v lshw >/dev/null 2>&1; then
    lshw -class network 2>/dev/null | grep -E 'description|product|vendor' | head -10 || true
elif command -v lspci >/dev/null 2>&1; then
    lspci | grep -i net || echo "    No se encontró información clara"
else
    echo "    Herramientas lshw/lspci no disponibles"
fi
echo

# 5. Dominio regulatorio WiFi (si hay interfaz inalámbrica y herramientas)
echo "[5] Intentando leer dominio regulatorio WiFi (si aplica):"
if command -v iw >/dev/null 2>&1; then
    for iface in $(iw dev 2>/dev/null | awk '/Interface/ {print $2}'); do
        echo "    Interfaz: $iface"
        iw reg get 2>/dev/null | head -5 || true
    done
else
    echo "    Comando 'iw' no disponible o no hay interfaces WiFi"
fi
echo

echo "=== Fin de las comprobaciones locales ==="
echo
echo "Nota: Este script es solo demostrativo y limitado."
echo "No realiza detección real de proxies, no envía datos a ningún servidor"
echo "y no implementa el resto de técnicas mencionadas en el post original."