#!/bin/bash
# MCP Server Plan - Quick Test Script (curl-based)
#
# Usage:
#   chmod +x tests/test_mcp_curl.sh
#   ./tests/test_mcp_curl.sh

BASE_URL="http://localhost:5001"

echo "======================================"
echo "  MCP Server Plan - Quick Tests"
echo "======================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Health Check
echo -e "\n${GREEN}1. Health Check${NC}"
curl -s "${BASE_URL}/api/health" | python3 -m json.tool 2>/dev/null || echo "Server not running"

# 2. Classifier Stats
echo -e "\n${GREEN}2. Classifier Statistics${NC}"
curl -s "${BASE_URL}/api/tools/classifier/stats" | python3 -m json.tool

# 3. Classify a SCADA query
echo -e "\n${GREEN}3. Classify Query: 'SCADA sıcaklık değerini göster'${NC}"
curl -s -X POST "${BASE_URL}/api/tools/classify" \
  -H "Content-Type: application/json" \
  -d '{"query": "SCADA sıcaklık değerini göster"}' | python3 -m json.tool

# 4. Classify a Work Order query
echo -e "\n${GREEN}4. Classify Query: 'Yeni iş emri oluştur'${NC}"
curl -s -X POST "${BASE_URL}/api/tools/classify" \
  -H "Content-Type: application/json" \
  -d '{"query": "Yeni iş emri oluştur"}' | python3 -m json.tool

# 5. Classify an Alarm query
echo -e "\n${GREEN}5. Classify Query: 'Kritik alarmları listele'${NC}"
curl -s -X POST "${BASE_URL}/api/tools/classify" \
  -H "Content-Type: application/json" \
  -d '{"query": "Kritik alarmları listele"}' | python3 -m json.tool

# 6. Classify with high-risk tools
echo -e "\n${GREEN}6. Classify Query (High-Risk): 'Python kodu çalıştır'${NC}"
curl -s -X POST "${BASE_URL}/api/tools/classify" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python kodu çalıştır", "include_high_risk": true}' | python3 -m json.tool

# 7. Idempotency Stats
echo -e "\n${GREEN}7. Idempotency Service Stats${NC}"
curl -s "${BASE_URL}/api/services/idempotency/stats" | python3 -m json.tool

# 8. Available Tools
echo -e "\n${GREEN}8. Available Tools (count only)${NC}"
curl -s "${BASE_URL}/api/tools/available" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Total: {d.get(\"count\", 0)} tools')"

echo -e "\n${GREEN}Tests completed!${NC}"
