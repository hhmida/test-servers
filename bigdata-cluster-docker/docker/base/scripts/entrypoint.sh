#!/bin/bash
# ════════════════════════════════════════════════════════════════
# entrypoint.sh – Lance systemd comme PID 1 dans le conteneur
# Compatible cgroup v2 (Ubuntu 24.04)
# ════════════════════════════════════════════════════════════════
set -e

# ─── 1. Régénérer les host keys SSH si absentes ──────────────────
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    echo "[entrypoint] Génération des clés SSH host..."
    ssh-keygen -A
fi

# ─── 2. Machine-id unique par conteneur ──────────────────────────
if [ ! -s /etc/machine-id ]; then
    systemd-machine-id-setup 2>/dev/null || \
    dd if=/dev/urandom bs=16 count=1 2>/dev/null | xxd -p | tr -d '\n' > /etc/machine-id
fi
[ -f /var/lib/dbus/machine-id ] || ln -sf /etc/machine-id /var/lib/dbus/machine-id

# ─── 3. /etc/hosts : cluster bigdata ─────────────────────────────
if ! grep -q "master1" /etc/hosts; then
    cat >> /etc/hosts << 'EOF'
172.20.0.11  master1
172.20.0.12  master2
172.20.0.21  worker1
172.20.0.22  worker2
172.20.0.31  edge
EOF
fi

# ─── 4. Script de setup SSH (clés autorisées depuis les pairs) ───
/setup_ssh.sh &

# ─── 5. Lancer systemd ───────────────────────────────────────────
echo "[entrypoint] Démarrage de systemd (PID 1)..."
exec /sbin/init
