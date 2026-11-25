#!/bin/bash
# PRD 格式检查脚本
# 用法: ./check-format.sh <prd_file>
# 返回: JSON 格式检查结果

set -e

PRd_FILE="$1"

if [ -z "$PRd_FILE" ]; then
  echo '{"error": "Usage: check-format.sh <prd_file>"}'
  exit 1
fi

if [ ! -f "$PRd_FILE" ]; then
  echo "{\"error\": \"File not found: $PRd_FILE\"}"
  exit 1
fi

ISSUES=()

# 检查代码块闭合
CODE_BLOCKS=$(grep -c "^\`\`\`" "$PRd_FILE" 2>/dev/null || echo 0)
if [ $((CODE_BLOCKS % 2)) -ne 0 ]; then
  LINE_NUM=$(grep -n "^\`\`\`" "$PRd_FILE" | tail -1 | cut -d: -f1)
  ISSUES+=("{\"type\": \"unclosed_code_block\", \"line\": $LINE_NUM}")
fi

# 检查连续空行（超过3个）
EMPTY_LINE_COUNT=0
while IFS= read -r line; do
  stripped=$(echo "$line" | tr -d '[:space:]')
  if [ -z "$stripped" ]; then
    EMPTY_LINE_COUNT=$((EMPTY_LINE_COUNT + 1))
    if [ $EMPTY_LINE_COUNT -gt 3 ]; then
      LINE_NUM=$(grep -n "^$" "$PRd_FILE" | head -1 | cut -d: -f1)
      ISSUES+=("{\"type\": \"too_many_empty_lines\", \"line\": $LINE_NUM}")
      EMPTY_LINE_COUNT=0
    fi
  else
    EMPTY_LINE_COUNT=0
  fi
done < "$PRd_FILE"

# 输出结果（不依赖 jq）
if [ ${#ISSUES[@]} -eq 0 ]; then
  echo '{"passed": true, "format_issues": []}'
else
  ISSUES_JSON="["
  for i in "${!ISSUES[@]}"; do
    if [ $i -gt 0 ]; then
      ISSUES_JSON+=","
    fi
    ISSUES_JSON+="${ISSUES[$i]}"
  done
  ISSUES_JSON+="]"
  echo "{\"passed\": false, \"format_issues\": $ISSUES_JSON}"
fi
