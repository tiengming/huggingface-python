import argparse
import os
import subprocess
import sys
from pathlib import Path
import logging
import importlib.util
import configparser

# --- 配置 ---
CONFIG_FILE = Path("config.ini")
CONFIG_SECTION = "UserSettings"

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
    if not config.has_section(CONFIG_SECTION):
        config.add_section(CONFIG_SECTION)
    return config

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as configfile:
        config.write(configfile)

def get_config_value(config, key, default=None):
    """从配置中获取值"""
    return config.get(CONFIG_SECTION, key, fallback=default)

def set_config_value(config, key, value):
    """向配置中设置值"""
    if value:
        config.set(CONFIG_SECTION, key, value)

def is_package_installed(package_name: str) -> bool:
    """检查指定的包是否已安装"""
    return importlib.util.find_spec(package_name) is not None

def download_with_huggingface_cli(model_name: str, output_dir: str, proxy: str = None, file_name: str = None):
    """
    使用 huggingface-cli 和 hf_transfer (如果可用) 下载模型或单个文件。
    Args:
        model_name (str): 模型名称。
        output_dir (str): 保存目录。
        proxy (str, optional): 代理地址。
        file_name (str, optional): 只下载指定文件（可选）。
    """
    import shutil
    # 1. 自动拼接模型名子文件夹
    safe_model_name = model_name.replace('/', '-')
    final_output_dir = os.path.join(output_dir, safe_model_name)
    os.makedirs(final_output_dir, exist_ok=True)

    # 环境变量和加速器逻辑保持不变
    env = os.environ.copy()
    hf_transfer_available = is_package_installed("hf_transfer")
    if hf_transfer_available:
        logging.info("hf-transfer is available. Enabling accelerated download.")
        env['HF_HUB_ENABLE_HF_TRANSFER'] = '1'
    else:
        logging.warning("hf-transfer not found. Falling back to default download method.")
        logging.warning("For faster downloads, consider running 'pip install hf-transfer'.")
    if proxy:
        logging.info(f"Using proxy: {proxy}")
        env['HTTP_PROXY'] = proxy
        env['HTTPS_PROXY'] = proxy

    # 构建 huggingface-cli 命令
    if sys.platform == "win32":
        scripts_dir = Path(sys.executable).parent
        cli_path = scripts_dir / "huggingface-cli.exe"
        cli_command = str(cli_path) if cli_path.exists() else "huggingface-cli"
    else:
        cli_command = "huggingface-cli"
    command = [
        cli_command,
        "download",
        model_name,
    ]
    # 如果指定了文件名，只下载该文件
    if file_name:
        command.append(file_name)
    command += [
        "--local-dir", final_output_dir,
        "--local-dir-use-symlinks", "False",
        "--resume-download"
    ]
    logging.info("Starting download with huggingface-cli...")
    logging.info(f"Command: {' '.join(command)}")
    logging.info("This may take a while. Progress will be displayed by huggingface-cli.")
    try:
        process = subprocess.run(
            command,
            env=env,
            check=False,  # 我们自己处理返回码
            encoding='utf-8',
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        # 2. 下载完成后校验
        if process.returncode == 0:
            num_files = 0
            total_size = 0
            incomplete_files = []
            for root, _, files in os.walk(final_output_dir):
                for f in files:
                    num_files += 1
                    fp = os.path.join(root, f)
                    total_size += os.path.getsize(fp)
                    if f.endswith('.incomplete'):
                        incomplete_files.append(fp)
            if incomplete_files:
                print(f"\n警告：有 {len(incomplete_files)} 个文件未完整下载，请检查网络后重试。\n未完成文件示例：{incomplete_files[0] if incomplete_files else ''}")
            else:
                print(f"\n下载成功！共下载 {num_files} 个文件，总大小 {total_size/1024/1024:.2f} MB。\n模型已保存到：{final_output_dir}")
        else:
            print("\n下载失败，请检查网络或代理设置，或查看上方日志信息。\n")
    except Exception as e:
        print(f"\n下载过程中发生异常：{e}\n")

def main():
    """
    主函数，用于解析参数和启动下载。
    """
    parser = argparse.ArgumentParser(
        description="A user-friendly wrapper for huggingface-cli to download models or single files.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--model", 
        type=str, 
        help="The model to download (e.g., 'bert-base-uncased')"
    )
    parser.add_argument(
        "--output_dir", 
        type=str,
        default=None,
        help="Local directory to save the model (overrides config.ini)"
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default=None,
        help="Proxy address to use (e.g., 'http://127.0.0.1:7890', overrides config.ini)"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Only download a specific file from the model repo (e.g., 'clip_l.safetensors')"
    )

    args = parser.parse_args()
    config = load_config()

    # --- 决定最终使用的参数值 (优先级: 命令行 > 配置文件 > None) ---
    model_name = args.model
    output_dir = args.output_dir or get_config_value(config, "output_dir")
    proxy = args.proxy or get_config_value(config, "proxy")
    file_name = args.file

    # --- 交互模式 ---
    if not model_name:
        print("--- Hugging Face Model Downloader (Interactive Mode) ---")
        try:
            model_name = input("Enter model name (e.g., 'bert-base-uncased'): ")

            # 提示输入 output_dir，并将配置文件中的值作为默认值
            output_dir_prompt = f"Enter a directory to save the model [{output_dir or 'not set'}]: "
            new_output_dir = input(output_dir_prompt)
            if new_output_dir:
                output_dir = new_output_dir
            
            # 提示输入 proxy，并将配置文件中的值作为默认值
            proxy_prompt = f"Enter proxy address (optional) [{proxy or 'not set'}]: "
            new_proxy = input(proxy_prompt)
            if new_proxy:
                proxy = new_proxy

            # 新增：提示输入文件名（可选）
            file_prompt = "Enter file name to download (optional, leave blank to download all files): "
            new_file = input(file_prompt)
            if new_file:
                file_name = new_file
            else:
                file_name = None
            
            if not model_name or not output_dir:
                print("Model name and output directory cannot be empty.")
                return

            # 保存更新后的配置
            set_config_value(config, "output_dir", output_dir)
            set_config_value(config, "proxy", proxy)
            save_config(config)
            logging.info(f"Settings saved to {CONFIG_FILE.name}")

        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            return

    print("\n" + "="*40)
    print(f"Download Configuration:")
    print(f"  - Model: {model_name}")
    print(f"  - Output Directory: {output_dir}")
    if file_name:
        print(f"  - File: {file_name}")
    
    # 动态显示加速器状态
    accelerator_status = "hf_transfer (available and enabled)" if is_package_installed("hf_transfer") else "hf_transfer (not available)"
    print(f"  - Accelerator: {accelerator_status}")
    if proxy:
        print(f"  - Proxy: {proxy}")
    print(f"  - Model files will be saved in: {output_dir}/{{模型名}}\n")
    
    download_with_huggingface_cli(model_name, output_dir, proxy, file_name)

if __name__ == "__main__":
    main() 