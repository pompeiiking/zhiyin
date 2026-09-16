## open_agent API功能说明

open_agent API服务是基于langchain和Qwen-Agent的开发框架开发的Agent应用，支持通过OpenAI API方式接入tools，充分利用基于元景、deepseek系列模型的指令遵循、工具使用、规划、记忆能力，同时也集成了具备function_call能力的模型的工具选择能力，整体实现以下三种场景：

1:支持function_call
-可直接基于具备function_call能力的模型实现工具选择、函数调用，无需使用prompt进行指令遵循来实现工具调用

2.react
-单步函数调用：实现基于一系列tools、并利用指令遵循来选择最优的action函数并及进行调用

-分步规划函数调用：能基于一系列tool、并利用指令遵循开展大模型的规划推理能力、规划任务、分步调用、总结输出



