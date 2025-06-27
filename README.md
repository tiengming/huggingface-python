# 🤗 Hugging Face 模型下载助手（支持批量下载与加速器）

这是一个基于命令行的 Python 工具，旨在通过 `huggingface-cli` 快速下载 Hugging Face 上的单个或多个模型，支持代理配置、`hf_transfer` 加速、配置文件持久化、失败自动重试、缓存隔离等增强功能。

## 🚀 功能特性

- 支持单个或批量模型下载（读取 `.txt` / `.json` 文件）
- 自动配置加速器：可检测 `hf_transfer` 并启用高速下载
- 下载失败自动重试，默认 3 次
- 支持指定下载模型中的单个文件
- 支持代理设置（HTTP/HTTPS）
- 自动检测 `.incomplete` 文件并清理
- 使用临时缓存目录进行下载，下载完成后安全移动到目标位置
- 中文交互界面，支持非交互命令行模式

## 🛠️ 安装依赖

在使用本工具时，建议你创建独立的 **Python 虚拟环境**。

以下是推荐操作：

```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装依赖
pip install huggingface_hub hf_transfer
```

## 📦 使用方法

```bash
python huggingface_downloader.py [参数]
```

支持的参数：

| 参数           | 说明                                       |
| -------------- | ------------------------------------------ |
| `--model`      | 单个模型名，如 `bert-base-uncased`         |
| `--model_list` | 模型名列表文件路径，支持 `.txt` 或 `.json` |
| `--output_dir` | 模型保存目录                               |
| `--proxy`      | 使用代理，如 `http://127.0.0.1:7890`       |
| `--file`       | 只下载模型仓库中的单个文件                 |
| `--retries`    | 下载失败最大重试次数（默认 3）             |

### 示例

**下载单个模型**

```bash
python huggingface_downloader.py --model stabilityai/sv4d2.0 --output_dir F:\Models --proxy http://127.0.0.1:7890
```

**批量下载模型列表**

创建一个 `model_list.txt` 文件，内容如下：

```
bert-base-uncased
stabilityai/sv4d2.0
runwayml/stable-diffusion-v1-5
```

然后运行：

```bash
python huggingface_downloader.py --model_list model_list.txt --output_dir ./models
```

## 💡 提示

- 若未指定 `--model` 或模型列表文件，脚本将进入中文交互模式。
- 下载临时缓存目录为 `output_dir/__hf_tmp`，任务完成后会自动清除。
- 下载失败提示中包含 Hugging Face 官方页面链接，可用于手动排查。

## 📄 配置文件

首次运行时将生成 `config.ini`，自动保存最近的 `output_dir` 与 `proxy` 设置。下次运行将自动读取。
