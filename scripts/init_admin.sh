#!/bin/sh
# init_admin.sh: Provision the first enterprise tenant and admin user

API_URL="http://127.0.0.1:8000"

echo "Provisioning Enterprise Tenant..."
curl -X POST "$API_URL/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your Organization",
    "domain": "your-org.com",
    "tier": "enterprise",
    "admin_email": "admin@your-org.com",
    "admin_password": "secure-password-here"
  }'

echo -e "\nTenant provisioning complete. Please ensure to update admin_email and admin_password."
