#!/bin/bash
# Integration test script - tests the webhook endpoints with sample payloads
# Prerequisites: API server running at localhost:8000, demo-company tenant created

set -e

API_URL="${API_URL:-http://localhost:8000/api/v1}"
TENANT_SLUG="${TENANT_SLUG:-demo-company}"

echo "=== B2B Workflow Automation - Integration Tests ==="
echo "API: $API_URL"
echo "Tenant: $TENANT_SLUG"
echo ""

# --- Test 1: Health check ---
echo "--- Test 1: Health Check ---"
HEALTH=$(curl -s "$API_URL/health")
echo "Response: $HEALTH"
echo ""

# --- Test 2: Login ---
echo "--- Test 2: Admin Login ---"
LOGIN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}')
echo "Response: $LOGIN"
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null || echo "")
if [ -z "$TOKEN" ]; then
  echo "ERROR: Failed to get auth token"
  exit 1
fi
echo "Got token: ${TOKEN:0:20}..."
echo ""

# --- Test 3: List tenants ---
echo "--- Test 3: List Tenants ---"
TENANTS=$(curl -s "$API_URL/tenants" \
  -H "Authorization: Bearer $TOKEN")
echo "Response: $TENANTS"
echo ""

# --- Test 4: Submit support ticket ---
echo "--- Test 4: Submit Support Ticket ---"
SUPPORT=$(curl -s -X POST "$API_URL/webhooks/support" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Slug: $TENANT_SLUG" \
  -d @../samples/webhook_support.json)
echo "Response: $SUPPORT"
TICKET_ID=$(echo "$SUPPORT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
echo "Ticket ID: $TICKET_ID"
echo ""

# --- Test 5: Submit sales lead ---
echo "--- Test 5: Submit Sales Lead ---"
LEAD=$(curl -s -X POST "$API_URL/webhooks/leads" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Slug: $TENANT_SLUG" \
  -d @../samples/webhook_lead.json)
echo "Response: $LEAD"
LEAD_ID=$(echo "$LEAD" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
echo "Lead ID: $LEAD_ID"
echo ""

# --- Test 6: List runs ---
echo "--- Test 6: List Runs ---"
sleep 2
RUNS=$(curl -s "$API_URL/runs" \
  -H "Authorization: Bearer $TOKEN")
echo "Response: $RUNS"
echo ""

# --- Test 7: List audit logs ---
echo "--- Test 7: List Audit Logs ---"
AUDIT=$(curl -s "$API_URL/audit" \
  -H "Authorization: Bearer $TOKEN")
echo "Response: $AUDIT"
echo ""

# --- Test 8: Get usage ---
echo "--- Test 8: Check Usage ---"
# Get tenant ID from list
TENANT_ID=$(echo "$TENANTS" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data[0]['id'] if data else '')" 2>/dev/null || echo "")
if [ -n "$TENANT_ID" ]; then
  USAGE=$(curl -s "$API_URL/usage/$TENANT_ID" \
    -H "Authorization: Bearer $TOKEN")
  echo "Response: $USAGE"
fi
echo ""

echo "=== Integration Tests Complete ==="
echo ""
echo "Next steps:"
echo "  - Check the runs endpoint to see if workers processed the tickets/leads"
echo "  - Check the audit log for detailed action tracking"
echo "  - View the admin UI at http://localhost:3000"
