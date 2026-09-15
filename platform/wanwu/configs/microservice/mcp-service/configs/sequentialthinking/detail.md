# 顺序思维 MCP Server

一个 MCP 服务器实现，通过结构化思维过程提供动态和反思性问题解决的工具。

## 特性

- 将复杂问题分解为可管理的步骤
- 随着理解的加深修正和完善思路
- 分支到替代的推理路径
- 动态调整思维的总数
- 生成和验证解决方案假设

## 工具

### sequential_thinking

促进详细的逐步思维过程，以便进行问题解决和分析。

**输入:**
- `thought` (string): 当前思维步骤
- `nextThoughtNeeded` (boolean): 是否需要另一个思维步骤
- `thoughtNumber` (integer): 当前思维编号
- `totalThoughts` (integer): 估计所需的总思维数
- `isRevision` (boolean, optional): 是否修正之前的思维
- `revisesThought` (integer, optional): 正在重新考虑的思维
- `branchFromThought` (integer, optional): 分支点思维编号
- `branchId` (string, optional): 分支标识符
- `needsMoreThoughts` (boolean, optional): 是否需要更多思维

## 使用方法

顺序思维工具旨在：
- 将复杂问题分解为步骤
- 规划和设计时留有修正的余地
- 可能需要调整方向的分析
- 初始时可能不清楚完整范围的问题
- 需要在多个步骤中保持上下文的任务
- 需要过滤掉无关信息的情况

## 配置

### 与 Claude Desktop 一起使用

将以下内容添加到你的 `claude_desktop_config.json` 中：

#### npx

```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking"
      ]
    }
  }
}
```

#### docker

```json
{
  "mcpServers": {
    "sequentialthinking": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "mcp/sequentialthinking"
      ]
    }
  }
}
```

## 构建

Docker:

```bash
docker build -t mcp/sequentialthinking -f src/sequentialthinking/Dockerfile .
```

## 许可证

该 MCP 服务器根据 MIT 许可证授权。这意味着您可以自由使用、修改和分发该软件，前提是遵守 MIT 许可证的条款和条件。有关更多详细信息，请参见项目存储库中的 LICENSE 文件。
