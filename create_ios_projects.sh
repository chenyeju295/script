#!/bin/bash

# 设置默认iOS部署版本
IOS_DEPLOYMENT_TARGET="14.0"

# 获取项目名称
read -p "请输入需要创建的iOS项目名称（多个用空格分隔）: " -a PROJECT_NAMES

# 检查输入有效性
if [ ${#PROJECT_NAMES[@]} -eq 0 ]; then
    echo "错误：未输入项目名称！"
    exit 1
fi

# 创建项目流程
for PROJECT_NAME in "${PROJECT_NAMES[@]}"
do
    echo "正在创建纯iOS项目: $PROJECT_NAME"
    
    # 创建项目（仅iOS平台）
    flutter create --platforms=ios -i swift --project-name $PROJECT_NAME $PROJECT_NAME
    
    # 修改部署目标版本
    IOS_PODFILE="$PROJECT_NAME/ios/Podfile"
    if [ -f "$IOS_PODFILE" ]; then
        sed -i '' "s/platform :ios, '.*'/platform :ios, '$IOS_DEPLOYMENT_TARGET'/" "$IOS_PODFILE"
        echo "iOS部署目标已设置为 $IOS_DEPLOYMENT_TARGET"
        
        # 移除无关平台配置
        sed -i '' '/flutter_install_all_ios_plugins/d' "$IOS_PODFILE"
    fi
    
    # 清理Android文件
    rm -rf "$PROJECT_NAME/android" 2>/dev/null
    rm -rf "$PROJECT_NAME/linux" 2>/dev/null
    rm -rf "$PROJECT_NAME/windows" 2>/dev/null
    rm -rf "$PROJECT_NAME/web" 2>/dev/null
    rm -rf "$PROJECT_NAME/macos" 2>/dev/null
    
    echo "✅ 项目 $PROJECT_NAME 创建完成"
    echo "----------------------------------------"
done

echo "所有iOS项目创建完成！"
