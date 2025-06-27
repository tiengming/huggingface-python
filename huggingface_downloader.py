import argparse
import os
import subprocess
import sys
from pathlib import Path
import logging
import importlib.util
import configparser
import shutil
import time
import json

CONFIG_FILE = Path("config.ini")
CONFIG_SECTION = "UserSettings"
REQUIRED_DISK_GB = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def load_config():
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE, encoding="utf-8")
    if not config.has_section(CONFIG_SECTION):
        config.add_section(CONFIG_SECTION)
    return config

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        config.write(f)

def get_config_value(config, key, default=None):
    return config.get(CONFIG_SECTION, key, fallback=default)

def set_config_value(config, key, value):
    if value:
        config.set(CONFIG_SECTION, key, value)

def is_package_installed(name):
    return importlib.util.find_spec(name) is not None

def check_disk_space(path, required_gb=REQUIRED_DISK_GB):
    try:
        _, _, free = shutil.disk_usage(path)
        return free / (1024 ** 3) >= required_gb
    except Exception:
        return True

def prompt_for_directory(default_path=None):
    while True:
        output_dir = input(f"请输入保存目录 [{default_path or '未设置'}]：").strip() or default_path
        if not output_dir:
            continue
        path = Path(output_dir)
        if path.is_dir():
            return str(path)
        else:
            answer = input(f"📁 目录不存在：{output_dir}，是否创建？（Y/N）").strip().lower()
            if answer == "y":
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    print(f"✅ 已创建目录：{path}")
                    return str(path)
                except Exception as e:
                    print(f"❌ 创建目录失败：{e}")
            else:
                print("请重新输入有效的目录。")

def parse_model_list_file(path):
    path = Path(path)
    if not path.exists():
        return None
    try:
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"⚠️ 无法读取模型列表文件：{e}")
        return None


def download_with_huggingface_cli(model_name, output_dir, proxy=None, file_name=None, max_retries=3):
    safe_model_name = model_name.replace("/", "-")
    cache_root = Path(output_dir) / "__hf_tmp"
    cache_dir = cache_root / f"{safe_model_name}_{int(time.time())}"
    final_output_dir = Path(output_dir) / safe_model_name
    cache_dir.mkdir(parents=True, exist_ok=True)
    final_output_dir.mkdir(parents=True, exist_ok=True)  # ✅ 确保目录存在（解决 FileNotFoundError）

    if not check_disk_space(str(cache_dir)):
        print(f"❌ 可用磁盘空间不足（< {REQUIRED_DISK_GB}GB），请释放空间后重试。")
        return

    lockfile = final_output_dir / ".download.lock"
    if lockfile.exists():
        print(f"⚠️ 模型 {model_name} 正在被其他进程下载中，跳过。")
        return

    env = os.environ.copy()
    hf_transfer = is_package_installed("hf_transfer")
    env["HF_HUB_ENABLE_HF_TRANSFER"] = "1" if hf_transfer else "0"
    if proxy:
        env["HTTP_PROXY"] = proxy
        env["HTTPS_PROXY"] = proxy

    cli_command = shutil.which("huggingface-cli")
    fallback_command = [sys.executable, "-m", "huggingface_hub.cli"]
    base_cmd = [cli_command or fallback_command[0]] if isinstance(cli_command, str) else fallback_command
    command = base_cmd + ["download", model_name]
    if file_name:
        command.append(file_name)
    command += ["--local-dir", str(cache_dir), "--local-dir-use-symlinks", "False", "--resume-download"]

    try:
        lockfile.touch()
        for attempt in range(1, max_retries + 1):
            print(f"\n🔁 正在下载模型 {model_name}（第 {attempt} 次）...")
            try:
                subprocess.run(command, env=env, check=True, timeout=1800)
                incomplete = list(cache_dir.rglob("*.incomplete"))
                if incomplete:
                    print(f"⚠️ 检测到未完成文件（共 {len(incomplete)} 个），准备重试。")
                    for f in incomplete:
                        try:
                            f.unlink()
                        except Exception as e:
                            print(f"❌ 删除失败：{f}（{e}）")
                    raise RuntimeError("未完成文件存在，重试下载。")
                for item in cache_dir.iterdir():
                    shutil.move(str(item), final_output_dir / item.name)
                print(f"✅ 模型 {model_name} 下载完成，已保存至 {final_output_dir}")
                return
            except subprocess.TimeoutExpired:
                print("⌛ 下载超时（30 分钟），将重试。")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ huggingface-cli 错误：{e}")
            except Exception as e:
                print(f"⚠️ 出现异常：{e}")
            if attempt < max_retries:
                time.sleep(5)
                print("🔁 准备下一次重试...")
            else:
                print(f"❌ 模型 {model_name} 多次重试失败，请访问：https://huggingface.co/{model_name}")
    finally:
        if lockfile.exists():
            lockfile.unlink()
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="🤗 Hugging Face 批量模型下载工具（支持缓存隔离与加速器）")
    parser.add_argument("--model", type=str, help="单个模型名称（可选）")
    parser.add_argument("--model_list", type=str, help="模型列表文件路径（txt 或 json）")
    parser.add_argument("--output_dir", type=str, help="保存路径")
    parser.add_argument("--proxy", type=str, help="代理地址")
    parser.add_argument("--file", type=str, help="指定下载的文件")
    parser.add_argument("--retries", type=int, default=3, help="最大重试次数")
    args = parser.parse_args()

    config = load_config()
    model_list_path = args.model_list or "model_list.txt"
    models = parse_model_list_file(model_list_path)

    if not models:
        if args.model:
            models = [args.model.strip()]
        else:
            print(f"⚠️ 未找到模型列表文件 [{model_list_path}]，转为交互模式。")
            model_input = input("请输入模型名称（多个模型用逗号分隔）：").strip()
            models = [m.strip() for m in model_input.split(",") if m.strip()]

    output_dir = args.output_dir or get_config_value(config, "output_dir")
    if not output_dir or not Path(output_dir).is_dir():
        output_dir = prompt_for_directory(output_dir)

    proxy = args.proxy or get_config_value(config, "proxy")
    file_name = args.file
    retries = args.retries

    set_config_value(config, "output_dir", output_dir)
    set_config_value(config, "proxy", proxy)
    save_config(config)

    print("\n📋 当前下载设置：")
    print(f"  - 模型数量：{len(models)}")
    print(f"  - 保存目录：{output_dir}")
    if file_name:
        print(f"  - 指定文件：{file_name}")
    if proxy:
        print(f"  - 使用代理：{proxy}")
    print(f"  - 加速器状态：{'hf_transfer ✅' if is_package_installed('hf_transfer') else '未启用 ❌'}")
    print(f"  - 重试次数上限：{retries}\n")

    for model in models:
        download_with_huggingface_cli(model, output_dir, proxy, file_name, max_retries=retries)

if __name__ == "__main__":
    main()
