import os
import json
import re
from typing import List, Dict
import google.generativeai as genai
import subprocess
from pathlib import Path

def print_debug(title: str, content: str):
    """打印调试信息"""
    print(f"\n{'='*20} {title} {'='*20}")
    print(content)
    print('='*50)

# Initialize Gemini AI client
GEMINI_API_KEY = "AIzaSyDJJ-6xkPT8d02qanw8ShssipgnAs8htLk"
genai.configure(api_key=GEMINI_API_KEY)

class ImageGenerationSystem:
    def __init__(self):
        self.lib_path = ""
        self.project_root = ""  # 添加项目根目录路径
        self.dart_files = []
        self.generated_prompts = []
        self.last_processed_files = []
        self.errors = []
        self.debug = True  # 调试模式开关

    def extract_lib_path(self, dart_file_path: str) -> str:
        """从Dart文件路径中提取lib路径和项目根目录"""
        try:
            path = Path(dart_file_path)
            # 查找 'lib' 目录
            lib_index = -1
            for i, part in enumerate(path.parts):
                if part == 'lib':
                    lib_index = i
                    break
            
            if lib_index != -1:
                # 构建到 lib 的路径
                lib_path = os.path.join(*path.parts[:lib_index + 1])
                # 构建项目根目录路径（lib的父目录）
                project_root = os.path.join(*path.parts[:lib_index])
                return lib_path, project_root
            return "", ""
        except Exception as e:
            self.errors.append(f"提取路径时出错: {str(e)}")
            return "", ""

    def set_paths(self):
        """设置路径"""
        print("\n=== 设置路径 ===")
        while True:
            dart_file = input("请输入Dart文件路径 (直接回车完成输入): ").strip()
            if not dart_file:
                break
            
            if not os.path.exists(dart_file):
                print(f"错误: 文件 '{dart_file}' 不存在")
                continue
                
            if not dart_file.endswith('.dart'):
                print("错误: 请输入.dart文件")
                continue
                
            self.dart_files.append(dart_file)
            
            # 从第一个Dart文件提取lib路径和项目根目录
            if not self.lib_path and self.dart_files:
                self.lib_path, self.project_root = self.extract_lib_path(self.dart_files[0])
                if self.lib_path and self.project_root:
                    print(f"自动检测到lib路径: {self.lib_path}")
                    print(f"项目根目录: {self.project_root}")
                else:
                    print("警告: 无法自动检测路径，请确保Dart文件在lib目录下")
        
        if self.dart_files:
            print("\n设置成功:")
            print(f"项目根目录: {self.project_root}")
            print(f"Lib路径: {self.lib_path}")
            print("Dart文件:")
            for file in self.dart_files:
                print(f"- {file}")
        else:
            print("未指定任何Dart文件。")

    def parse_dart_file(self, file_path: str) -> List[Dict]:
        """解析 Dart 文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if self.debug:
                print_debug("Dart文件内容", content[:500] + "..." if len(content) > 500 else content)

            # 让 AI 解析文件内容
            context = f"""分析以下 Dart 文件内容，提取所有角色信息。文件内容如下:

{content}

请提取以下信息:
1. 所有角色的基本信息（名字、描述、背景故事等）
2. 角色的特征和属性
3. 角色的个性特点
4. 其他相关的角色描述信息

以 JSON 格式返回，格式如下:
[
    {{
        "name": "角色名",
        "description": "角色描述",
        "background": "背景故事",
        "traits": ["特征1", "特征2"],
        "personality": "性格特点"
    }},
    ...
]

注意：请确保返回的是有效的 JSON 格式，只返回 JSON 数据，不要包含任何其他文字说明。"""

            if self.debug:
                print_debug("发送给AI的提示词", context)

            response = genai.GenerativeModel("gemini-2.0-flash").generate_content(
                contents=context
            )

            if self.debug:
                print_debug("AI返回的原始响应", response.text)

            try:
                # 尝试清理响应文本，确保是有效的JSON
                response_text = response.text.strip()
                # 如果响应包含多余的反引号（markdown代码块），去除它们
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                elif response_text.startswith('```'):
                    response_text = response_text.replace('```', '').strip()

                if self.debug:
                    print_debug("清理后的JSON文本", response_text)

                characters = json.loads(response_text)
                
                if self.debug:
                    print_debug("解析后的JSON数据", json.dumps(characters, indent=2, ensure_ascii=False))

                data = []
                for char in characters:
                    data.append({
                        'class_name': char['name'],
                        'fields': char.get('traits', []),
                        'comments': [
                            char.get('description', ''),
                            char.get('background', ''),
                            char.get('personality', '')
                        ]
                    })
                return data
            except json.JSONDecodeError as e:
                error_msg = f"AI 返回的数据格式不正确: {str(e)}\n响应内容: {response_text}"
                self.errors.append(error_msg)
                print(f"错误: {error_msg}")
                return []

        except Exception as e:
            error_msg = f"读取或解析文件时出错: {str(e)}"
            self.errors.append(error_msg)
            print(f"错误: {error_msg}")
            return []

    def generate_prompt(self, data: Dict) -> Dict:
        """使用角色数据生成图像提示词"""
        context = f"""基于以下角色信息创建详细的图像生成提示词:

角色名称: {data['class_name']}
特征: {', '.join(data['fields']) if data['fields'] else 'None'}
描述: {' '.join(data['comments']) if data['comments'] else 'None'}

要求:
1. 如果是女性角色，描述为年轻、迷人的欧美女性，时尚优雅的外表
2. 包含具体的造型、外观、姿势和表情细节
3. 添加专业的摄影细节（光线、焦点、构图）
4. 生成详细的、适合AI图像生成的描述
5. 根据角色特点和背景设定合适的场景

只返回提示词文本，不要包含任何其他说明。"""
        
        if self.debug:
            print_debug("发送给AI的提示词生成请求", context)

        response = genai.GenerativeModel("gemini-2.0-flash").generate_content(
            contents=context
        )

        if self.debug:
            print_debug("AI返回的提示词", response.text)

        # 清理响应文本
        prompt_text = response.text.strip()
        if prompt_text.startswith('```'):
            prompt_text = prompt_text.replace('```', '').strip()

        # 确定图像比例
        ratio = "1/1"  # 默认正方形
        if any(keyword in data['class_name'].lower() for keyword in ['banner', 'header', 'cover']):
            ratio = "16/9"
        elif any(keyword in data['class_name'].lower() for keyword in ['profile', 'avatar']):
            ratio = "1/1"

        result = {
            "name": data['class_name'].lower(),
            "prompt": prompt_text,
            "ratio": ratio,
            "subfolder": "characters"  # 统一放在 characters 目录下
        }

        if self.debug:
            print_debug("生成的最终提示词数据", json.dumps(result, indent=2, ensure_ascii=False))

        return result

    def process_dart_files(self):
        """处理 Dart 文件生成提示词"""
        if not self.dart_files:
            print("错误: 未指定 Dart 文件，请先设置文件路径")
            return

        self.generated_prompts = []
        self.last_processed_files = self.dart_files.copy()

        for dart_file in self.dart_files:
            print(f"\n处理文件: {dart_file}...")
            try:
                characters = self.parse_dart_file(dart_file)
                if not characters:
                    print(f"警告: 在文件 {dart_file} 中未找到角色信息")
                    continue

                for char_data in characters:
                    print(f"\n分析角色: {char_data['class_name']}")
                    try:
                        prompt = self.generate_prompt(char_data)
                        self.generated_prompts.append(prompt)
                        print(f"已生成提示词: {char_data['class_name']}")
                    except Exception as e:
                        error_msg = f"生成角色 {char_data['class_name']} 的提示词时出错: {str(e)}"
                        self.errors.append(error_msg)
                        print(f"错误: {error_msg}")

            except Exception as e:
                error_msg = f"处理文件 {dart_file} 时出错: {str(e)}"
                self.errors.append(error_msg)
                print(f"错误: {error_msg}")

        if self.generated_prompts:
            print(f"\n共生成 {len(self.generated_prompts)} 个提示词")
            # 自动执行下一步
            print("\n自动执行: 保存提示词...")
            self.update_prompts_json()
        else:
            print("未生成任何提示词")

    def update_prompts_json(self, output_file: str = 'prompts.json'):
        """更新提示词JSON文件"""
        if not self.generated_prompts:
            print("错误: 没有可保存的提示词，请先处理Dart文件")
            return

        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = {"prompts": []}

        # 添加新提示词，避免重复
        existing_names = {prompt['name'] for prompt in existing_data['prompts']}
        added_count = 0
        for prompt in self.generated_prompts:
            if prompt['name'] not in existing_names:
                existing_data['prompts'].append(prompt)
                existing_names.add(prompt['name'])
                added_count += 1

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            print(f"\n已保存 {added_count} 个新提示词到 {output_file}")
        except Exception as e:
            error_msg = f"保存提示词到文件时出错: {str(e)}"
            self.errors.append(error_msg)
            print(f"错误: {error_msg}")

    def generate_images(self):
        """生成图像"""
        if not self.project_root:
            print("错误: 未检测到项目根目录，请先设置文件路径")
            return

        try:
            # 确保项目根目录下的 assets/images 目录存在
            assets_path = os.path.join(self.project_root, "assets", "images")
            os.makedirs(assets_path, exist_ok=True)
            
            # 修改generate_images.py中的输出路径
            try:
                with open('generate_images.py', 'r') as f:
                    content = f.read()
                
                new_content = content.replace(
                    '"output_path": "assets/"',
                    f'"output_path": "{assets_path}"'
                )
                
                with open('generate_images.py', 'w') as f:
                    f.write(new_content)

                print(f"\n图像将保存到: {assets_path}")
                # 运行图像生成脚本
                result = subprocess.run(['python3', 'generate_images.py'], capture_output=True, text=True)
                
                if result.returncode != 0:
                    error_msg = f"图像生成脚本执行失败: {result.stderr}"
                    self.errors.append(error_msg)
                    print(f"错误: {error_msg}")
                else:
                    print("图像生成完成")
                    
            except Exception as e:
                error_msg = f"修改或执行图像生成脚本时出错: {str(e)}"
                self.errors.append(error_msg)
                print(f"错误: {error_msg}")
                
        except Exception as e:
            error_msg = f"创建输出目录时出错: {str(e)}"
            self.errors.append(error_msg)
            print(f"错误: {error_msg}")

    def show_menu(self):
        """显示主菜单"""
        while True:
            print("\n=== 图像生成系统菜单 ===")
            print("1. 设置文件路径")
            print("2. 处理Dart文件生成提示词")
            print("3. 保存提示词到JSON")
            print("4. 生成图像")
            print("5. 执行完整流程")
            print("6. 显示当前状态")
            print("7. 显示错误日志")
            print("0. 退出")
            
            try:
                choice = input("\n请输入选项 (0-7): ").strip()
                
                if choice == "1":
                    self.set_paths()
                elif choice == "2":
                    self.process_dart_files()
                elif choice == "3":
                    self.update_prompts_json()
                elif choice == "4":
                    self.generate_images()
                elif choice == "5":
                    print("\n开始执行完整流程...")
                    self.set_paths()
                    if self.dart_files:
                        self.process_dart_files()
                        if self.generated_prompts:
                            self.update_prompts_json()
                            self.generate_images()
                elif choice == "6":
                    self.show_status()
                elif choice == "7":
                    self.show_errors()
                elif choice == "0":
                    print("\n程序退出...")
                    break
                else:
                    print("\n无效的选项，请重试。")
            except Exception as e:
                self.errors.append(f"菜单操作错误: {str(e)}")
                print(f"\n发生错误: {str(e)}")

    def show_errors(self):
        """显示错误日志"""
        print("\n=== 错误日志 ===")
        if not self.errors:
            print("没有错误记录")
        else:
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")

    def show_status(self):
        """显示当前状态"""
        print("\n=== 当前状态 ===")
        print(f"项目根目录: {self.project_root or '未设置'}")
        print(f"Lib路径: {self.lib_path or '未设置'}")
        print("\nDart文件:")
        if self.dart_files:
            for file in self.dart_files:
                print(f"- {file}")
        else:
            print("未指定文件")
        
        print(f"\n已生成提示词数量: {len(self.generated_prompts)}")
        if self.last_processed_files:
            print("\n最近处理的文件:")
            for file in self.last_processed_files:
                print(f"- {file}")
        
        if self.errors:
            print(f"\n错误数量: {len(self.errors)}")

def main():
    try:
        system = ImageGenerationSystem()
        system.show_menu()
    except Exception as e:
        print(f"\n程序运行出错: {str(e)}")
        print("程序异常退出")

if __name__ == "__main__":
    main()