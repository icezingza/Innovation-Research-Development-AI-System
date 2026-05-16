#!/bin/sh
# start_airgap.sh: Start the IRD-AI stack in air-gapped mode and check health

echo "Starting IRD-AI Air-Gapped Stack..."
docker compose -f docker-compose.airgap.yml up -d

echo "Checking system status..."
docker compose -f docker-compose.airgap.yml ps

echo "Verifying API health..."
sleep 5
curl -f http://127.0.0.1:8000/health
if [ $? -eq 0 ]; then
    echo -e "\nSystem is healthy!"
else
    echo -e "\nSystem is not responding to health check. Please check logs."
fi
