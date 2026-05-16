#!/bin/sh
# test_pipeline.sh: Authenticate as admin and run a research task

API_URL="http://127.0.0.1:8000"

echo "Logging in as admin..."
# Assuming we got tenant ID from previous step, pass it as an argument or set default
TENANT_ID=${1:-"<your-tenant-id>"}

LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"admin@your-org.com\",
    \"password\": \"secure-password-here\",
    \"tenant_id\": \"$TENANT_ID\"
  }")

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "Login failed. Check your credentials or tenant ID."
    exit 1
fi

echo "Login successful. Running test research task..."
curl -X POST "$API_URL/research/tasks" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "วิเคราะห์แนวโน้มตลาดการเงินไทย", "domain": "finance"}'

echo -e "\nTest task submitted successfully."
