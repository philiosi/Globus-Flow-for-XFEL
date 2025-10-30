#!/bin/bash
# deploy_flow.sh - Flow 배포 스크립트

FLOW_TITLE="PAL-XFEL Data Transfer Flow"
DEFINITION_FILE="transfer_flow.json"
SCHEMA_FILE="transfer_schema.json"

echo "=== Globus Flow 배포 ==="
echo "제목: $FLOW_TITLE"
echo "정의 파일: $DEFINITION_FILE"
echo "스키마 파일: $SCHEMA_FILE"
echo ""

# Flow 생성
globus flows create "$FLOW_TITLE" "$DEFINITION_FILE" \
    --input-schema "$SCHEMA_FILE" \
    --format json > flow_info.json

# Flow ID 추출
FLOW_ID=$(jq -r '.id' flow_info.json)

echo "✓ Flow 생성 완료!"
echo "  Flow ID: $FLOW_ID"
echo "  정보 파일: flow_info.json"
echo ""
echo "다음 명령으로 Flow 정보 확인:"
echo "  globus flows show $FLOW_ID"
