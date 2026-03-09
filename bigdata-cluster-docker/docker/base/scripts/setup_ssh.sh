#!/bin/bash
# Attend que le réseau soit disponible et configure les clés SSH
# entre conteneurs (exécuté en background au démarrage)
sleep 5

NODES="master1 master2 worker1 worker2 edge"
SSH_DIR=/home/hadoop/.ssh
AUTH_KEYS=$SSH_DIR/authorized_keys

for node in $NODES; do
    if [ "$node" != "$(hostname)" ]; then
        # Récupérer la clé publique de chaque pair (best-effort)
        PUB=$(ssh -o StrictHostKeyChecking=no \
                  -o ConnectTimeout=3 \
                  -o BatchMode=yes \
                  -i $SSH_DIR/id_rsa \
                  hadoop@$node \
                  "cat /home/hadoop/.ssh/id_rsa.pub" 2>/dev/null)
        if [ -n "$PUB" ] && ! grep -qF "$PUB" $AUTH_KEYS 2>/dev/null; then
            echo "$PUB" >> $AUTH_KEYS
            echo "[setup_ssh] Clé de $node ajoutée"
        fi
    fi
done
chown hadoop:hadoop $AUTH_KEYS 2>/dev/null || true
