#!/bin/bash
# PRD 结构完整性验证脚本
# 用法: ./validate.sh <prd_file>
# 返回: JSON 格式验证结果

set -e

PRd_FILE="$1"

if [ -z "$PRd_FILE" ]; then
  echo '{"error": "Usage: validate.sh <prd_file>"}'
  exit 1
fi

if [ ! -f "$PRd_FILE" ]; then
  echo "{\"error\": \"File not found: $PRd_FILE\"}"
  exit 1
fi

REQUIRED_CHAPTERS=(
  "1. 产品概述"
  "2. 角色与权限"
  "3. 功能页面清单"
  "4. 页面细化"
  "5. 交互流程"
  "6. 接口设计"
  "7. 数据字典"
  "8. 验收标准"
  "9. 非功能需求"
  "10. 三方对接"
)

FOUND_CHAPTERS=()
MISSING_CHAPTERS=()

for chapter in "${REQUIRED_CHAPTERS[@]}"; do
  if grep -q "^## ${chapter}" "$PRd_FILE" || grep -q "^# ${chapter}" "$PRd_FILE"; then
    FOUND_CHAPTERS+=("$chapter")
  else
    MISSING_CHAPTERS+=("$chapter")
  fi
done

# 构建 JSON 数组（不依赖 jq）
if [ ${#FOUND_CHAPTERS[@]} -eq 0 ]; then
  FOUND_JSON="[]"
else
  FOUND_JSON="["
  for i in "${!FOUND_CHAPTERS[@]}"; do
    if [ $i -gt 0 ]; then
      FOUND_JSON+=","
    fi
    FOUND_JSON+="\"${FOUND_CHAPTERS[$i]}\""
  done
  FOUND_JSON+="]"
fi

if [ ${#MISSING_CHAPTERS[@]} -eq 0 ]; then
  MISSING_JSON="[]"
else
  MISSING_JSON="["
  for i in "${!MISSING_CHAPTERS[@]}"; do
    if [ $i -gt 0 ]; then
      MISSING_JSON+=","
    fi
    MISSING_JSON+="\"${MISSING_CHAPTERS[$i]}\""
  done
  MISSING_JSON+="]"
fi

if [ ${#MISSING_CHAPTERS[@]} -eq 0 ]; then
  echo "{\"passed\": true, \"chapters\": $FOUND_JSON, \"missing_chapters\": []}"
else
  echo "{\"passed\": false, \"chapters\": $FOUND_JSON, \"missing_chapters\": $MISSING_JSON}"
fi
