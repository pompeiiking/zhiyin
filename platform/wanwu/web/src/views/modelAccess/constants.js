export const LLM = 'llm'

export const MODEL_TYPE_OBJ = {
    [LLM]: 'LLM',
    rerank: 'Rerank',
    embedding: 'Embedding',
}

export const MODEL_TYPE = Object.keys(MODEL_TYPE_OBJ).map(key => ({key, name: MODEL_TYPE_OBJ[key]}))

export const YUAN_JING = 'YuanJing'
export const PROVIDER_OBJ = {
    'OpenAI-API-compatible': 'OpenAI-API-compatible',
    [YUAN_JING]: '联通元景'
}

export const PROVIDER_TYPE = Object.keys(PROVIDER_OBJ)
    .map(key => ({key, name: PROVIDER_OBJ[key], children: MODEL_TYPE}))

export const DEFAULT_CALLING = 'noSupport'
export const FUNC_CALLING = [
    {key: 'noSupport', name: '不支持'},
    {key: 'toolCall', name: 'Tool call'},
    {key: 'functionCall', name: 'Function call'},
]