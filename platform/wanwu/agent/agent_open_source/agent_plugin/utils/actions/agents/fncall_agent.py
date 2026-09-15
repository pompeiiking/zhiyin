import copy
from typing import Dict, Iterator, List, Literal, Optional, Union
from utils.actions import Agent
from utils.actions.llm import BaseChatModel
from utils.actions.llm.schema import DEFAULT_SYSTEM_MESSAGE, FUNCTION, Message,ASSISTANT
from utils.actions.memory import Memory
from utils.actions.settings import MAX_LLM_CALL_PER_RUN
from utils.actions.tools import BaseTool
from utils.actions.utils.utils import extract_files_from_messages


class FnCallAgent(Agent):
    """This is a widely applicable function call agent integrated with llm and tool use ability."""

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 function_calls_list=None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 files: Optional[List[str]] = None,
                 action_type = "qwen_agent",
                 model_name = "",
                 model_url = "",
                 **kwargs):
        """Initialization the agent.

        Args:
            function_list: One list of tool name, tool configuration or Tool object,
              such as 'code_interpreter', {'name': 'code_interpreter', 'timeout': 10}, or CodeInterpreter().
            llm: The LLM model configuration or LLM model object.
              Set the configuration as {'model': '', 'api_key': '', 'model_server': ''}.
            system_message: The specified system message for LLM chat.
            name: The name of this agent.
            description: The description of this agent, which will be used for multi_agent.
            files: A file url list. The initialized files for the agent.
        """
        super().__init__(
                         function_list=function_list,
                         function_calls_list=function_calls_list,
                         llm=llm,
                         system_message=system_message,
                         name=name,
                         description=description,
                         action_type = action_type,
                         model_name = model_name,
                         model_url = model_url)
        if not hasattr(self, 'mem'):
            # Default to use Memory to manage files
            self.mem = Memory(llm=self.llm, files=files, **kwargs)

    def _run(self, messages: List[Message], lang: Literal['en', 'zh'] = 'en', **kwargs) -> Iterator[List[Message]]:
        self.tool_descs = '\n'.join(tool.function_plain_text
                                    for tool in self.function_map.values())
        self.tool_names = ', '.join(tool.name
                                    for tool in self.function_map.values())

        messages = copy.deepcopy(messages)
        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        response = []
        while True and num_llm_calls_available > 0:
            num_llm_calls_available -= 1
            output_stream = self._call_llm(messages=messages,
                                           model_name = self.model_name,
                                           functions=[func.function for func in self.function_map.values()],
                                           extra_generate_cfg={'lang': lang})
            output: List[Message] = []
            for output in output_stream:
                if output:
                    yield response + output
            if output:
                response.extend(output)
                messages.extend(output)
                used_any_tool = False
                for out in output:
                    use_tool, tool_name, tool_args, _ = self._detect_tool(out)
                    if use_tool:
                        tool_result = self._call_tool(tool_name, tool_args, messages=messages, **kwargs)
                        fn_msg = Message(
                            role=FUNCTION,
                            name=tool_name,
                            content=tool_result,
                        )
                        messages.append(fn_msg)
                        response.append(fn_msg)
                        yield response
                        used_any_tool = True
                if not used_any_tool:
                    break

    def _call_tool(self, tool_name: str, tool_args: Union[str, dict] = '{}', **kwargs) -> str:
        if tool_name not in self.function_map:
            return f'Tool {tool_name} does not exists.'
        # Temporary plan: Check if it is necessary to transfer files to the tool
        # Todo: This should be changed to parameter passing, and the file URL should be determined by the model
        if self.function_map[tool_name].file_access:
            assert 'messages' in kwargs
            files = extract_files_from_messages(kwargs['messages'], include_images=True) + self.mem.system_files
            return super()._call_tool(tool_name, tool_args, files=files, **kwargs)
        else:
            return super()._call_tool(tool_name, tool_args, **kwargs)
