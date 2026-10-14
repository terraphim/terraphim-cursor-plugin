# Terraphim Skills Introduction

本插件提供三个开源技能，让 Kimi Code、ZCode 及其他智能体能够使用
Terraphim 的本地代码搜索、经验学习和智能体记忆工作流。

## 技能

- `terraphim-grep`：在本地代码和文档中进行有界搜索，默认离线。
- `terraphim-agent-learn`：检查失败并记录经过验证的操作修正。
- `terraphim-agent-memory`：保存明确提供的经验，按实际 ID 读取内容和来源标签。

这些技能采用 Apache-2.0 许可证，不包含可执行文件、密钥、后台任务或
Terraphim 专有技能内容。

## 安装依赖

在 macOS 或安装了 Homebrew 的 Linux 上运行：

```bash
brew tap terraphim/terraphim
brew install terraphim-grep terraphim-agent
terraphim-grep --version
terraphim-agent --version
terraphim-agent learn --help
terraphim-agent memory --help
```

技能不会自动安装软件。没有 Homebrew 时，请按照
[Terraphim 安装指南](https://terraphim-skills.md/docs/non-technical/)
下载适合平台的文件，并用 `SHA256SUMS` 验证。

## 安装与使用

在 ZCode 的“发现”页面把仓库内的 `marketplaces/zcode.json` 添加为个人市场，
然后安装 `terraphim-skills-intro`。进入官方精选市场仍需由维护者审核并合并
单独的 Pull Request。各平台的安装、更新和卸载步骤见
[分发指南](docs/distribution.md)。

示例请求：

- “使用 Terraphim Grep 查找授权回调并显示两行上下文。”
- “搜索项目经验，找出之前失败的部署命令。”
- “保存这条明确提供的经验，然后显示实际保存的 ID、内容和来源标签。”

[已验证的双 CLI 示例](docs/cli-workflows.md)使用 Clients 1.21.20，演示导出的同义词图搜索，以及明确内容的记忆保存和读取。记忆写入当前用户的操作系统本地存储，与当前目录无关。

默认操作是本地且只读的。写入学习或记忆必须获得明确授权；启用模型综合
前必须确认数据边界和可能的费用。

浏览 [Community、Core 和 Premium 技能目录](https://terraphim-skills.md/skills/)。
此链接只提供信息，不会自动创建结账、付款或交易。

隐私政策：<https://terraphim-skills.md/legal/privacy/>

服务条款：<https://terraphim-skills.md/legal/terms/>

许可证：Apache-2.0
