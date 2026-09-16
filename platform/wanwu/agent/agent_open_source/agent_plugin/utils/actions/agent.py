import copy
import json
import traceback
import logging
import requests
import types
from abc import ABC, abstractmethod
from typing import Dict, Iterator, List, Optional, Tuple, Union
from utils.actions.llm import get_chat_model
from utils.actions.llm.base import BaseChatModel
from utils.actions.llm.schema import CONTENT, DEFAULT_SYSTEM_MESSAGE, ROLE, SYSTEM, ContentItem, Message
from utils.actions.log import logger
from utils.actions.tools import TOOL_REGISTRY, BaseTool
from utils.actions.utils.utils import has_chinese_messages, merge_generate_cfgs

logger = logging.getLogger(__name__) 

class Agent(ABC):
    """A base class for Agent.

    An agent can receive messages and provide response by LLM or Tools.
    Different agents have distinct workflows for processing messages and generating responses in the `_run` method.
    """

    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 function_calls_list=None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 system_message: Optional[str] = DEFAULT_SYSTEM_MESSAGE,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
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
        """
        if isinstance(llm, dict):
            self.llm = get_chat_model(llm)
        else:
            self.llm = llm
        self.extra_generate_cfg: dict = {}
        self.function_map = {}
        self.function_list = []
        self.function_call = {}
        self.fn_list = []
        self.action_type = action_type
        self.model_name = model_name
        self.model_url = model_url
        
        if self.action_type == "yuanjing_function_call":
            for function in function_calls_list:
                if "name" not in function.keys() and "function_name" in  function.keys():
                    function['name'] = function['function_name']
                    del function['function_name']
                self.function_call['type'] = "function"
                self.function_call['function'] = function
                self.fn_list.append(self.function_call)
            self.function_calls_list = self.fn_list
        else:
            self.function_calls_list = function_calls_list
        
        if function_list:
            for tool in function_list:
                self._init_tool(tool)
        
        # logger.info(f"self.function_map:{self.function_map.values()}")

        self.system_message = system_message
        # print(f"\nself.system_message:{self.system_message}")
        self.name = name
        self.description = description
        

    def run_nonstream(self, messages: List[Union[Dict, Message]], **kwargs) -> Union[List[Message], List[Dict]]:
        """Same as self.run, but with stream=False,
        meaning it returns the complete response directly
        instead of streaming the response incrementally."""
        *_, last_responses = self.run(messages, **kwargs)
        return last_responses

    def run(self, messages: List[Union[Dict, Message]],
            **kwargs) -> Union[Iterator[List[Message]], Iterator[List[Dict]]]:
        """Return one response generator based on the received messages.

        This method performs a uniform type conversion for the inputted messages,
        and calls the _run method to generate a reply.

        Args:
            messages: A list of messages.

        Yields:
            The response generator.
        """
        messages = copy.deepcopy(messages)
        _return_message_type = 'dict'
        new_messages = []
        # Only return dict when all input messages are dict
        if not messages:
            _return_message_type = 'message'
        for msg in messages:
            if isinstance(msg, dict):
                new_messages.append(Message(**msg))
            else:
                new_messages.append(msg)
                _return_message_type = 'message'

        if 'lang' not in kwargs:
            if has_chinese_messages(new_messages):
                kwargs['lang'] = 'zh'
            else:
                kwargs['lang'] = 'en'

        for rsp in self._run(messages=new_messages, **kwargs):
            for i in range(len(rsp)):
                if not rsp[i].name and self.name:
                    rsp[i].name = self.name
            if _return_message_type == 'message':
                yield [Message(**x) if isinstance(x, dict) else x for x in rsp]
            else:
                yield [x.model_dump() if not isinstance(x, dict) else x for x in rsp]

    @abstractmethod
    def _run(self, messages: List[Message], lang: str = 'en', **kwargs) -> Iterator[List[Message]]:
        """Return one response generator based on the received messages.

        The workflow for an agent to generate a reply.
        Each agent subclass needs to implement this method.

        Args:
            messages: A list of messages.
            lang: Language, which will be used to select the language of the prompt
              during the agent's execution process.

        Yields:
            The response generator.
        """
        raise NotImplementedError

    def _call_llm(
        self,
        messages: List[Message],
        functions: Optional[List[Dict]] = None,
        function_calls_list=None,
        model_name = None,
        model_url = None,
        stream: bool = True,
        extra_generate_cfg: Optional[dict] = None,
    ) -> Iterator[List[Message]]:
        """The interface of calling LLM for the agent.

        We prepend the system_message of this agent to the messages, and call LLM.

        Args:
            messages: A list of messages.
            functions: The list of functions provided to LLM.
            stream: LLM streaming output or non-streaming output.
              For consistency, we default to using streaming output across all agents.

        Yields:
            The response generator of LLM.
        """
        messages = copy.deepcopy(messages)
        if messages[0][ROLE] != SYSTEM:
            # messages.insert(0, Message(role=SYSTEM, content=self.system_message))
            messages.insert(0, Message(role=SYSTEM, content=self.system_message))
        elif isinstance(messages[0][CONTENT], str):
            messages[0][CONTENT] = self.system_message + '\n\n' + messages[0][CONTENT]
        else:
            assert isinstance(messages[0][CONTENT], list)
            messages[0][CONTENT] = [ContentItem(text=self.system_message + '\n\n')] + messages[0][CONTENT]
        return self.llm.chat(
                             messages=messages,
                             functions=functions,
                             function_calls_list=self.function_calls_list,
                             model_name = self.model_name,
                             model_url = self.model_url,
                             stream=stream,
                             extra_generate_cfg=merge_generate_cfgs(
                             base_generate_cfg=self.extra_generate_cfg,
                             new_generate_cfg=extra_generate_cfg,
                             ))

    def _call_tool(self, tool_name: str, tool_args: Union[str, dict] = '{}', **kwargs) -> str:
        """The interface of calling tools for the agent.

        Args:
            tool_name: The name of one tool.
            tool_args: Model generated or user given tool parameters.

        Returns:
            The output of tools.
        """
        if tool_name not in self.function_map:
            return f'Tool {tool_name} does not exists.'
        tool = self.function_map[tool_name]
        try:
            tool_result = tool.call(tool_args, **kwargs)
            # logger.info(f"tool_result：{tool_result.text}")
        except Exception as ex:
            exception_type = type(ex).__name__
            exception_message = str(ex)
            traceback_info = ''.join(traceback.format_tb(ex.__traceback__))
            error_message = f'An error occurred when calling tool `{tool_name}`:\n' \
                            f'{exception_type}: {exception_message}\n' \
                            f'Traceback:\n{traceback_info}'
            logger.warning(error_message)
            return error_message

        if isinstance(tool_result, str):
            return tool_result
        elif isinstance(tool_result, types.GeneratorType):
            return tool_result
        elif isinstance(tool_result, requests.models.Response):
            return tool_result
        else:
            return json.dumps(tool_result, ensure_ascii=False, indent=4)

    def _init_tool(self, tool: Union[str, Dict, BaseTool]):
        if isinstance(tool, BaseTool):
            tool_name = tool.name
            if tool_name in self.function_map:
                logger.warning(f'Repeatedly adding tool {tool_name}, will use the newest tool in function list')
            self.function_map[tool_name] = tool
            
            
        else:
            if isinstance(tool, dict):
                tool_name = next(iter(tool))
                # tool_name = tool['name']
                tool_cfg = tool
            else:
                tool_name = tool
                tool_cfg = None
            if tool_name not in TOOL_REGISTRY:
                raise ValueError(f'Tool {tool_name} is not registered.')

            if tool not in self.function_list:
                self.function_list.append(tool)
                tool_class = TOOL_REGISTRY[tool_name]
                try:
                    self.function_map[tool_name] = tool_class(tool_cfg)
                except TypeError:
                    # When using OpenAPI, tool_class is already an instantiated object, not a corresponding class
                    self.function_map[tool_name] = tool_class
                except Exception as e:
                    raise RuntimeError(e)

            # if tool_name in self.function_map:
            #     logger.warning(f'Repeatedly adding tool {tool_name}, will use the newest tool in function list')
            # self.function_map[tool_name] = TOOL_REGISTRY[tool_name](tool_cfg)

    def _detect_tool(self, message: Message) -> Tuple[bool, str, str, str]:
        """A built-in tool call detection for func_call format message.

        Args:
            message: one message generated by LLM.

        Returns:
            Need to call tool or not, tool name, tool args, text replies.
        """
        func_name = None
        func_args = None

        if message.function_call:
            func_call = message.function_call
            func_name = func_call.name
            func_args = func_call.arguments
        text = message.content
        if not text:
            text = ''

        return (func_name is not None), func_name, func_args, text
