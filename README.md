# Hugging Face 模型下载器 (官方工具封装)

## 项目简介

本项目是一个基于 Python 的、对 Hugging Face 官方命令行工具 (`huggingface-cli`) 的用户友好封装。它旨在提供一个简单的交互式或命令行界面，同时利用 `hf_transfer` (如果可用) 实现最快的下载速度。

## 主要功能

- **保留交互式界面**：可通过命令行参数或交互式问答方式指定模型和下载目录。
- **配置文件**：首次在交互模式下输入下载目录和代理地址后，会自动创建 `config.ini` 文件保存设置，方便后续使用。
- **调用官方工具**：底层使用 `huggingface-cli download` 命令，确保下载过程的稳定性和健壮性。
- **自动启用加速**：自动检测并尝试启用 `hf_transfer`，为用户带来极致的下载体验。
- **断点续传**：完美继承官方工具的断点续传功能。
- **跨平台兼容**：在 Windows, macOS 和 Linux 上均可良好运行。
- **单文件下载**：支持只下载模型仓库中的某个特定文件（如权重文件、配置文件等），无需下载整个模型。

## 依赖安装

请先确保已安装 Python 3.7 及以上版本。

推荐使用虚拟环境：

强烈建议在项目根目录下创建虚拟环境，避免依赖冲突：

```bash
python -m venv .venv
# Windows 激活虚拟环境
.venv\\Scripts\\activate
# macOS/Linux 激活虚拟环境
source .venv/bin/activate
```

激活虚拟环境后再安装依赖：

```bash
pip install -r requirements.txt
```

> **注意:** `hf-transfer` 可能会因为网络或权限问题安装失败。但无需担心，即使它安装失败，本工具依然可以正常使用，只是下载速度会回退到普通模式。

## 使用方法

### 命令行方式

```bash
python huggingface_downloader.py --model Qwen/Qwen1.5-0.5B --output_dir ./models --proxy http://127.0.0.1:7890
```

参数说明：

- `--model`：要下载的模型名称 (例如 `Qwen/Qwen1.5-0.5B`)
- `--output_dir`：模型保存的本地目录。如果未指定，将使用 `config.ini` 中的设置。
- `--proxy`：(可选) HTTP/HTTPS 代理地址 (例如 `http://127.0.0.1:7890`)。如果未指定，将使用 `config.ini` 中的设置。
- `--file`：(可选) 只下载模型仓库中的某个文件（如 `clip_l.safetensors`）。如果不指定，则下载整个模型。

### 交互式方式

直接运行脚本，根据提示输入模型名称、保存路径和代理地址（可选）：

```bash
python huggingface_downloader.py
```

> 在交互模式下，脚本会显示 `config.ini` 中已保存的设置作为默认值，可以直接回车使用。输入新值后，会自动保存以供下次使用。

> **单文件下载**：在交互模式下，输入模型名称和保存目录后，会提示你输入"文件名"。如果只想下载某个文件（如 `clip_l.safetensors`），请填写文件名；如果要下载整个模型，直接回车即可。

## 注意事项

- 命令行参数会覆盖 `config.ini` 文件中的设置。
- 本工具是 `huggingface-cli` 的一个外壳，实际的下载进度和日志由 `huggingface-cli` 打印。
- 如果 `hf-transfer` 安装失败或不可用，下载速度会变慢，但功能不受影响。
- 请确保你的网络可以访问 Hugging Face Hub，或者正确配置了代理。

## 贡献与反馈

如有建议或问题，欢迎提交 issue 或联系作者。
