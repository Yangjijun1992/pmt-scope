#!/usr/bin/env bash
# PMTscope 数据同步部署脚本
# 从内网 SQLite 数据库导出 CSV，提交到 Git 仓库，推送到 GitHub
# Streamlit Cloud 检测到推送后会自动重新部署
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQLITE_DB="/mnt/data/TPC/database/pmt_data.db"
SQLITE_TABLE="measurements"
CSV_OUTPUT="$SCRIPT_DIR/data/pmt_data.csv"

echo "=== PMTscope 数据同步部署 ==="
echo ""

# 1. 导出 SQLite → CSV
echo "[1/4] 从 SQLite 导出数据..."
if [ ! -f "$SQLITE_DB" ]; then
    echo "错误: 找不到数据库文件 $SQLITE_DB"
    exit 1
fi

mkdir -p "$(dirname "$CSV_OUTPUT")"

sqlite3 -header -csv "$SQLITE_DB" "SELECT * FROM $SQLITE_TABLE;" > "$CSV_OUTPUT"

row_count=$(tail -n +2 "$CSV_OUTPUT" | wc -l)
echo "      已导出 $row_count 条记录 → $CSV_OUTPUT"

# 2. 提交到 Git
echo "[2/4] 提交变更到 Git..."
cd "$SCRIPT_DIR"
git add data/pmt_data.csv

if git diff --cached --quiet; then
    echo "      数据无变化，跳过提交。"
else
    commit_msg="data: 同步 PMT 数据 ($(date '+%Y-%m-%d %H:%M'), $row_count 条记录)"
    git commit -m "$commit_msg"
    echo "      已提交: $commit_msg"
fi

# 3. 推送到 GitHub
echo "[3/4] 推送到 GitHub..."
git push

echo "[4/4] 完成!"
echo ""
echo "=== 后续步骤 ==="
echo "Streamlit Cloud 检测到推送后将自动重新部署。"
echo "如需手动触发部署，访问: https://share.streamlit.io"
