"""业务规则层（policies）。

为什么要单独一层
----------------
`ports/` 冻结的是"服务长什么样"，`services/` 放的是"服务怎么跑"，但两者之间
最容易被写乱的是**规则本身**：意图怎么判、主理怎么选、交接何时触发、影响面
怎么算、什么时候才允许打扰用户。这些规则过去没有归宿，实现者只能塞进
Orchestrator 或某个 Service 的方法体里，结果是规则改一处要动一串调用方。

因此本包按"规则类别"分文件，每条规则一个 ABC，**只声明输入与输出**：

    routing.py        意图识别 → 环节判定（轴 B）        FR-ORCH-001
    teaming.py        轴 A × 轴 B × 意图 → 主理/协理      FR-ORCH-002
    handoff.py        交接与"换主理必须告知"              FR-ORCH-003
    impact.py         画像字段 → 受影响资产（重算范围）   FR-ORCH-004
    intervention.py   停滞阈值 / 冷却期 / 打扰上限        FR-REVIEW-001

依赖方向（单向，禁止倒流）
--------------------------
    services/ → policies/ → ports/ → kernel

`policies/` 不得 import `services/`：规则不能反过来依赖某次实现。
规则实现只允许依赖 Port（读黑板、读 registry）与共享内核，因此可以被单测直接
驱动，不需要起整个服务。

参数来源
--------
阈值、冷却期、话术这类**可调参数一律来自动态资源**（`data/registry/*.json`），
不得写死在规则实现里。规则实现只负责"怎么用参数"，不负责"参数是多少"。

状态：本期只冻结接口。轴 A 判定信号、意图→环节兜底、画像置信度算法、
主动干预参数四项业务口径定稿后，由各业务线在此补实现。
"""

from zhiyin_business.policies.handoff import HandoffPolicy
from zhiyin_business.policies.impact import ImpactPolicy
from zhiyin_business.policies.intervention import InterventionPolicy
from zhiyin_business.policies.routing import IntentPolicy, StagePolicy
from zhiyin_business.policies.teaming import LeadPolicy

__all__ = [
    "HandoffPolicy",
    "ImpactPolicy",
    "IntentPolicy",
    "InterventionPolicy",
    "LeadPolicy",
    "StagePolicy",
]
