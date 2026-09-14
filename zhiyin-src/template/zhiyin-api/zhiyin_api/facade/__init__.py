"""Application Facade：BFF 的唯一业务入口。"""

from zhiyin_api.facade.facade import (
    ApplicationFacade,
    FacadeNotConfiguredError,
    configure_facade,
    get_facade,
)

__all__ = [
    "ApplicationFacade",
    "FacadeNotConfiguredError",
    "configure_facade",
    "get_facade",
]
