#!/usr/bin/env bash

set -euo pipefail

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 帮助信息
show_help() {
    cat <<EOF
用法: $0 [选项]

全面管理 OpenCode 会话，支持按目录排除。

选项:
  -h, --help               显示此帮助
  --all                    删除所有会话（仍会询问排除目录，除非配合 --no-confirm）
  --exclude-dir DIR        排除指定目录下的所有会话（可多次使用）
  --dry-run                只列出会话，不实际删除
  --no-confirm             跳过所有确认（慎用）
  --list-only              仅列出所有会话（含目录），不做任何删除

交互流程（无选项）:
  1. 显示所有会话（含目录）
  2. 询问是否排除某些目录（默认否）
  3. 选择删除模式：
     - 删除全部（除排除目录外）
     - 按编号选择要删除的会话（仅显示未排除的）
EOF
}

# 检查依赖
check_deps() {
    if ! command -v opencode &> /dev/null; then
        echo -e "${RED}错误: 未找到 'opencode' 命令${NC}" >&2
        exit 1
    fi
    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}警告: 未找到 jq，会话目录可能无法准确显示${NC}" >&2
    fi
}

# 获取会话数据（JSON 格式）
get_sessions_json() {
    # 尝试获取 JSON，若失败则返回空
    if opencode session list --format json 2>/dev/null | jq -e '.' >/dev/null 2>&1; then
        opencode session list --format json
    else
        echo "[]"
    fi
}

# 解析会话：生成三个数组：ids, titles, dirs
parse_sessions() {
    local json_data="$1"
    ids=()
    titles=()
    dirs=()
    if [[ "$json_data" == "[]" ]] || [[ -z "$json_data" ]]; then
        return 1
    fi
    if command -v jq &> /dev/null; then
        # 使用 jq 解析
        while IFS=$'\t' read -r id title dir; do
            ids+=("$id")
            titles+=("${title:-无标题}")
            dirs+=("${dir:-未知目录}")
        done < <(echo "$json_data" | jq -r '.[] | [.id, .title // "", .directory // ""] | @tsv')
    else
        # 降级：尝试用 grep/sed 从表格解析（不准确）
        echo -e "${YELLOW}警告: 未安装 jq，无法获取目录信息，将仅显示 ID 和标题${NC}" >&2
        while IFS= read -r line; do
            if [[ "$line" =~ ^[[:space:]]*([a-f0-9-]+)[[:space:]]+(.*) ]]; then
                ids+=("${BASH_REMATCH[1]}")
                titles+=("${BASH_REMATCH[2]}")
                dirs+=("未知")
            fi
        done < <(opencode session list --format table | tail -n +2)
    fi
}

# 打印会话列表（带目录），同时标记排除的会话
print_sessions() {
    local -n excl_arr=$1  # 引用排除索引数组
    echo -e "${BLUE}所有会话列表 (共 ${#ids[@]} 个):${NC}"
    printf "%-4s | %-12s | %-30s | %s\n" "编号" "ID(前8)" "目录" "标题"
    echo "-----|--------------|--------------------------------|----------------------------------"
    for i in "${!ids[@]}"; do
        local short_id="${ids[i]:0:8}"
        local title="${titles[i]:-无标题}"
        local dir="${dirs[i]:-未知目录}"
        # 截断显示
        [[ ${#dir} -gt 30 ]] && dir="${dir:0:27}..."
        [[ ${#title} -gt 32 ]] && title="${title:0:29}..."
        # 标记排除
        local mark=""
        if [[ " ${excl_arr[*]} " =~ " $i " ]]; then
            mark="${YELLOW}[保留]${NC}"
        fi
        printf "%4d | %-12s | %-30s | %s %s\n" "$((i+1))" "$short_id" "$dir" "$title" "$mark"
    done
    echo ""
}

# 交互式排除目录
interactive_exclude_dirs() {
    echo -e "是否要排除某些目录下的所有会话（即保留这些目录下的会话）？(y/N)"
    read -r choice
    if [[ ! "$choice" =~ ^[Yy]$ ]]; then
        return
    fi
    echo "请输入要排除的目录名（支持部分匹配，多个用空格分隔，例如: projectA /home/user/work/projectB）:"
    read -r exclude_input
    # 将输入拆分为数组
    local patterns=($exclude_input)
    if [[ ${#patterns[@]} -eq 0 ]]; then
        return
    fi
    # 遍历会话，匹配目录
    local excluded_indices=()
    for i in "${!dirs[@]}"; do
        local dir="${dirs[i]}"
        for pat in "${patterns[@]}"; do
            if [[ "$dir" == *"$pat"* ]]; then
                excluded_indices+=("$i")
                break
            fi
        done
    done
    if [[ ${#excluded_indices[@]} -gt 0 ]]; then
        echo -e "${GREEN}已排除 ${#excluded_indices[@]} 个会话（目录匹配）。${NC}"
        # 将排除索引添加到全局 EXCLUDE_INDICES 数组
        for idx in "${excluded_indices[@]}"; do
            EXCLUDE_INDICES+=("$idx")
        done
        # 去重
        local unique=()
        for idx in "${EXCLUDE_INDICES[@]}"; do
            local found=0
            for u in "${unique[@]}"; do
                [[ $u -eq $idx ]] && found=1 && break
            done
            [[ $found -eq 0 ]] && unique+=("$idx")
        done
        EXCLUDE_INDICES=("${unique[@]}")
    else
        echo -e "${YELLOW}没有会话匹配输入的目录。${NC}"
    fi
}

# 删除单个会话
delete_session() {
    local id="$1"
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}[DRY-RUN] 将删除会话: $id${NC}"
        return 0
    fi
    if opencode session delete "$id" &> /dev/null; then
        echo -e "${GREEN}✓ 已删除会话: $id${NC}"
        return 0
    else
        echo -e "${RED}✗ 删除会话 $id 失败${NC}" >&2
        return 1
    fi
}

# 删除所有未排除的会话
delete_all_excluding() {
    local to_delete=()
    for i in "${!ids[@]}"; do
        if [[ ! " ${EXCLUDE_INDICES[*]} " =~ " $i " ]]; then
            to_delete+=("$i")
        fi
    done
    if [[ ${#to_delete[@]} -eq 0 ]]; then
        echo "没有可删除的会话（全部被排除）。"
        return
    fi
    echo -e "${YELLOW}将删除 ${#to_delete[@]} 个会话（排除 ${#EXCLUDE_INDICES[@]} 个）。${NC}"
    if [[ "$NO_CONFIRM" != true ]]; then
        echo -e "确认删除? (y/N)"
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            echo "已取消。"
            return
        fi
    fi
    for idx in "${to_delete[@]}"; do
        delete_session "${ids[idx]}"
    done
}

# 交互式按编号删除（只针对未排除的会话）
interactive_select_delete() {
    # 构建未排除的索引列表
    local available=()
    for i in "${!ids[@]}"; do
        if [[ ! " ${EXCLUDE_INDICES[*]} " =~ " $i " ]]; then
            available+=("$i")
        fi
    done
    if [[ ${#available[@]} -eq 0 ]]; then
        echo "没有可删除的会话（全部被排除）。"
        return
    fi
    # 显示可用会话（重新编号）
    echo -e "${BLUE}可删除的会话列表 (共 ${#available[@]} 个):${NC}"
    printf "%-4s | %-12s | %-30s | %s\n" "编号" "ID(前8)" "目录" "标题"
    echo "-----|--------------|--------------------------------|----------------------------------"
    local idx_map=()
    local count=0
    for orig_idx in "${available[@]}"; do
        ((count++))
        idx_map["$count"]="$orig_idx"
        local short_id="${ids[orig_idx]:0:8}"
        local title="${titles[orig_idx]:-无标题}"
        local dir="${dirs[orig_idx]:-未知目录}"
        [[ ${#dir} -gt 30 ]] && dir="${dir:0:27}..."
        [[ ${#title} -gt 32 ]] && title="${title:0:29}..."
        printf "%4d | %-12s | %-30s | %s\n" "$count" "$short_id" "$dir" "$title"
    done
    echo ""
    echo "请输入要删除的编号（空格分隔），或输入 'all' 删除所有可删除会话，或输入 'q' 退出:"
    read -r input
    case "$input" in
        q|Q|quit|exit)
            echo "已取消。"
            return
            ;;
        all|ALL)
            delete_all_excluding
            return
            ;;
        *)
            local selected=()
            for num in $input; do
                if [[ "$num" =~ ^[0-9]+$ ]] && [[ -n "${idx_map[$num]:-}" ]]; then
                    selected+=("${idx_map[$num]}")
                else
                    echo -e "${RED}无效编号: $num${NC}" >&2
                fi
            done
            if [[ ${#selected[@]} -eq 0 ]]; then
                echo "未选择任何有效会话。"
                return
            fi
            echo -e "${YELLOW}将删除以下 ${#selected[@]} 个会话:${NC}"
            for idx in "${selected[@]}"; do
                echo "  ${ids[idx]} (${titles[idx]:-无标题})"
            done
            if [[ "$NO_CONFIRM" != true ]]; then
                echo -e "确认删除? (y/N)"
                read -r confirm
                if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
                    echo "已取消。"
                    return
                fi
            fi
            for idx in "${selected[@]}"; do
                delete_session "${ids[idx]}"
            done
            ;;
    esac
}

# 主流程
main() {
    # 默认参数
    DRY_RUN=false
    NO_CONFIRM=false
    DELETE_ALL=false
    LIST_ONLY=false
    EXCLUDE_DIRS_FROM_CLI=()  # 命令行指定的排除目录

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            --all)
                DELETE_ALL=true
                shift
                ;;
            --exclude-dir)
                if [[ -z "$2" ]]; then
                    echo -e "${RED}错误: --exclude-dir 需要参数${NC}" >&2
                    exit 1
                fi
                EXCLUDE_DIRS_FROM_CLI+=("$2")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-confirm)
                NO_CONFIRM=true
                shift
                ;;
            --list-only)
                LIST_ONLY=true
                shift
                ;;
            *)
                echo -e "${RED}未知选项: $1${NC}" >&2
                show_help
                exit 1
                ;;
        esac
    done

    check_deps

    # 获取会话数据
    local json_data
    json_data=$(get_sessions_json)
    if [[ -z "$json_data" ]] || [[ "$json_data" == "[]" ]]; then
        echo -e "${YELLOW}没有找到任何会话。${NC}"
        exit 0
    fi

    parse_sessions "$json_data"
    if [[ ${#ids[@]} -eq 0 ]]; then
        echo -e "${YELLOW}没有找到任何会话。${NC}"
        exit 0
    fi

    echo -e "${GREEN}找到 ${#ids[@]} 个会话。${NC}"

    # 初始化排除索引数组
    EXCLUDE_INDICES=()

    # 如果有命令行排除目录，直接应用
    if [[ ${#EXCLUDE_DIRS_FROM_CLI[@]} -gt 0 ]]; then
        for pat in "${EXCLUDE_DIRS_FROM_CLI[@]}"; do
            for i in "${!dirs[@]}"; do
                if [[ "${dirs[i]}" == *"$pat"* ]]; then
                    EXCLUDE_INDICES+=("$i")
                fi
            done
        done
        # 去重
        local unique=()
        for idx in "${EXCLUDE_INDICES[@]}"; do
            local found=0
            for u in "${unique[@]}"; do
                [[ $u -eq $idx ]] && found=1 && break
            done
            [[ $found -eq 0 ]] && unique+=("$idx")
        done
        EXCLUDE_INDICES=("${unique[@]}")
        echo -e "${GREEN}通过命令行排除了 ${#EXCLUDE_INDICES[@]} 个会话。${NC}"
    fi

    # 显示所有会话（标记已排除）
    print_sessions EXCLUDE_INDICES

    if [[ "$LIST_ONLY" == true ]]; then
        echo "仅列出会话（--list-only），不执行删除。"
        exit 0
    fi

    # 交互排除目录（如果命令行未指定排除，且不是 --all 且非 --no-confirm）
    if [[ ${#EXCLUDE_DIRS_FROM_CLI[@]} -eq 0 ]]; then
        interactive_exclude_dirs
        # 重新打印列表（更新排除标记）
        print_sessions EXCLUDE_INDICES
    fi

    # 如果 --all 选项，直接删除所有（排除的除外）
    if [[ "$DELETE_ALL" == true ]]; then
        delete_all_excluding
        echo -e "${GREEN}操作完成。${NC}"
        exit 0
    fi

    # 否则进入交互模式：选择删除全部（除排除外）或按编号选择
    echo -e "请选择操作:"
    echo "  1) 删除所有未排除的会话"
    echo "  2) 按编号选择要删除的会话"
    echo "  3) 退出"
    read -r mode
    case "$mode" in
        1)
            delete_all_excluding
            ;;
        2)
            interactive_select_delete
            ;;
        3|q|Q)
            echo "退出。"
            exit 0
            ;;
        *)
            echo -e "${RED}无效选择，退出。${NC}"
            exit 1
            ;;
    esac

    echo -e "${GREEN}操作完成。${NC}"
}

main "$@"