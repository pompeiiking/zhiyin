"""MinIO 实现目录（**空抽屉**，尚未实现）。

一个目录 = 一套实现。本目录是对象存储这个替换点的落点：把 `LocalFileStore`
（本地目录，含路径穿越防护）换成 MinIO，业务层与接入层**一行都不用改**
（换实现只改 `zhiyin_boot/container/gateways.py` 的装配表）。

待实现的 Port 清单（唯一事实来源是 `zhiyin_data_sdk/gateways/storage.py`）
----------------------------------------------------------------------
| Port | 契约文件 | 第一期本地实现 | 装配位 |
| --- | --- | --- | --- |
| `ObjectStoreGateway` | `gateways/storage.py` | `local/object_store.py::LocalFileStore` | `gateways.object_store` |

开工前必须满足的条件
--------------------
1. **对象键的生成规则不变**：键由 `ObjectStoreGateway.build_key()`（用户 / 资产 /
   版本 / 扩展名）统一生成，调用方不得自行拼路径——换存储时键的语义必须保持一致，
   否则历史对象的读取路径会整体失效。
2. **元数据语义对齐**：`stat()` 对不存在的对象返回 `None`（不是抛异常），
   `delete()` 幂等；这两条是本契约里最容易在换实现时漂移的行为，契约测试会跑。
3. **访问控制落位**：第一期的本地实现没有鉴权（本地目录天然私有）。换 MinIO 时
   必须明确"下载链接怎么发、是否带签名与有效期"，并写进本目录的实现说明——
   这是导出功能（FR-BLOCK-001 真实导出）能否上线的关键一步。
4. **契约测试**：在 `tests/contracts/conftest.py` 的 `GATEWAY_FACTORIES` 里加一行。

不要把这些实现写回 `local/`：那是"无外部依赖即可跑通"的那一套。
"""

