#!/bin/bash

# 设置需要清理的根目录（默认脚本所在目录）
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

echo "正在清理所有Flutter项目的构建缓存..."
find "$ROOT_DIR" -name "pubspec.yaml" | while read -r file; do
    project_dir=$(dirname "$file")
    echo "发现Flutter项目: $project_dir"
    # 删除 build 和 .dart_tool 目录
    rm -rf "$project_dir/build" && echo "已删除 build 目录"
    rm -rf "$project_dir/.dart_tool" && echo "已删除 .dart_tool 目录"
done
echo "所有项目清理完成!"