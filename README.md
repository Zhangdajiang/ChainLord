# 我的私人实验室 🧪

这是一个基于 Streamlit 和 SpoonOS SDK 的 AI 聊天应用，支持钱包连接和自定义 AI 人设。

## 功能特性

- 🔗 **钱包连接**：使用 SpoonOS SDK 连接钱包，显示钱包地址
- 🤖 **AI 聊天**：与 AI 进行对话
- ⚙️ **自定义人设**：在左侧边栏设置 AI 的 System Prompt，让 AI 按照你的设定回答问题
- 💬 **聊天历史**：保存对话记录，支持清空

## 安装步骤

### 1. 安装 Python 依赖

在项目目录下运行以下命令：

```bash
pip install streamlit
pip install spoon-ai-sdk
pip install python-dotenv
pip install openai
```

或者一次性安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

1. 复制 `.env.example` 文件为 `.env`：
   ```bash
   copy .env.example .env
   ```
   （在 Linux/Mac 上使用：`cp .env.example .env`）

2. 编辑 `.env` 文件，填入你的 API Key：
   - 至少需要配置一个 LLM API Key（OPENAI_API_KEY、ANTHROPIC_API_KEY 或 DEEPSEEK_API_KEY）
   - 推荐使用 OpenAI 或 Anthropic

### 3. 运行应用

```bash
streamlit run app.py
```

应用会自动在浏览器中打开，默认地址是 `http://localhost:8501`

## 使用说明

1. **连接钱包**：
   - 在左侧边栏点击"连接钱包"按钮
   - 连接成功后，钱包地址会显示在页面顶部

2. **设置 AI 人设**：
   - 在左侧边栏的"AI 人设设置"区域
   - 输入 System Prompt（例如："你是一个专业的金融分析师，擅长分析市场趋势"）
   - 点击"保存人设"按钮

3. **开始聊天**：
   - 在主界面的输入框中输入你的问题
   - AI 会根据你设置的人设来回答
   - 聊天历史会保存在页面中

4. **清空聊天记录**：
   - 点击页面底部的"清空聊天记录"按钮

## 注意事项

- 确保已配置至少一个 LLM API Key
- 钱包连接功能目前是演示版本，实际生产环境需要使用 SpoonOS SDK 的完整钱包连接功能
- 聊天历史仅在当前会话中保存，刷新页面后会清空

## 技术栈

- **Streamlit**：Web 应用框架
- **SpoonOS SDK**：AI Agent 框架
- **Python-dotenv**：环境变量管理
- **OpenAI/Anthropic/DeepSeek**：LLM API

## 问题反馈

如有问题，请查看：
- SpoonOS SDK 文档：https://github.com/XSpoonAi/spoon-core
- Streamlit 文档：https://docs.streamlit.io/
