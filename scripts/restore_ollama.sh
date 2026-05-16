#!/bin/sh
# restore_ollama.sh: Restore ollama models from a backup tarball
BACKUP_FILE=${1:-"ollama-backup.tar.gz"}

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Backup file $BACKUP_FILE not found!"
    exit 1
fi

echo "Restoring Ollama models from $BACKUP_FILE..."
docker volume create ollama_models
docker run --rm -v ollama_models:/restore -v "$(pwd)":/backup alpine sh -c "cd /restore && tar xzf /backup/$BACKUP_FILE"
echo "Restore complete."
