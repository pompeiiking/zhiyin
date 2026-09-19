"""前后端口径对齐守卫（跨语言，只能靠断言）。

为什么单独一个文件
------------------
后端内部的口径已经有守卫（依赖矩阵、落位表、Bootstrap 字段来源），但**跨语言**的
那几处全靠"注释里写一句必须一致"：

- `client.ts` 抄了一份 `ErrorCode` 数字表，注释写着"必须与后端保持一致"；
- `router/index.ts` 的 `PAGE_ANCHORS` 与 `data/registry/routes.json` 的 `page_code`
  是两份手工维护的锚点，文档说"必须一致"；
- `endpoints.ts` 的 url 清单与后端路由表，两边各写一遍；
- 《前端 README》§二 的页面 → 组件落位表，写了 22 个组件，但没有守卫。

这四处的症状都是"不报错的错"：错误码错一位 → UI 走进通用分支；锚点漂移 →
埋点与页面归属对不上；url 漂移 → 404 而 OpenAPI 里看着有这条路由；
组件表漂移 → 新人照表找文件，文件不存在。

因此这里把它们变成机械可判。**跨语言的比对口径必须写下来，不能靠记忆。**
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = TEMPLATE_ROOT / "zhiyin-web"
SRC = WEB_ROOT / "src"
REGISTRY_DIR = TEMPLATE_ROOT / "data" / "registry"

CLIENT_TS = SRC / "api" / "client.ts"
ENDPOINTS_TS = SRC / "api" / "endpoints.ts"
TYPES_TS = SRC / "api" / "types.ts"
ROUTER_TS = SRC / "router" / "index.ts"
WEB_README = WEB_ROOT / "README.md"

FRONTEND_PREFIX = "/api/v1"
"""前端 baseURL（VITE_API_BASE_URL）。只用于把业务段拼成完整路径做比对。"""


def _block(text: str, header: str) -> str:
    """取出 `export const X = { ... }` 的块体（按首个右花括号收口）。

    只解析这份骨架里格式稳定的两个常量块；解析不到时抛错而不是静默返回空，
    否则守卫会"看起来在跑、其实什么都没比"。
    """
    start = text.index(header)
    body_start = text.index("{", start) + 1
    depth = 1
    index = body_start
    while depth:
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return text[body_start : index - 1]


def _registry(name: str) -> list[dict]:
    return json.loads((REGISTRY_DIR / name).read_text(encoding="utf-8"))["items"]


# --------------------------------------------------------------------------
# 1. 错误码：前端数字表 == 后端 IntEnum
# --------------------------------------------------------------------------


def test_frontend_error_codes_match_backend() -> None:
    """错误码是全站唯一的跨语言常量表，多一位少一位都会让 UI 走进错分支。

    编译期已有一半守卫：`client.ts` 的 `satisfies Record<string, BackendErrorCode>`
    由 `npm run typecheck` 校验（联合类型来自后端 OpenAPI）。这里补上另一半——
    **两个方向都要对**：前端不能少（少了就走通用分支）、也不能多（多了说明后端
    删过码而没人跟）。少/多/错值三种情况都在 CI 失败。
    """
    from zhiyin_api.dto.common import ErrorCode as BackendErrorCode

    frontend = {
        name: int(value)
        for name, value in re.findall(r"(\w+):\s*(\d+)", _block(CLIENT_TS.read_text(encoding="utf-8"), "export const ErrorCode"))
    }
    backend = {member.name: int(member.value) for member in BackendErrorCode}

    assert frontend, "没解析到前端的 ErrorCode 表——守卫会变成空跑"
    missing = sorted(set(backend) - set(frontend))
    extra = sorted(set(frontend) - set(backend))
    wrong = sorted(name for name in set(frontend) & set(backend) if frontend[name] != backend[name])

    assert not (missing or extra or wrong), (
        "前后端错误码不一致（前端 src/api/client.ts ↔ 后端 api/dto/common.py）：\n"
        f"  前端缺失：{missing}\n  前端多出：{extra}\n  数值不符：{wrong}"
    )


# --------------------------------------------------------------------------
# 2. 路由与页面锚点：router/index.ts ↔ data/registry/routes.json
# --------------------------------------------------------------------------


def _frontend_routes() -> list[dict[str, object]]:
    text = ROUTER_TS.read_text(encoding="utf-8")
    anchors = dict(re.findall(r"(\w+):\s*'([^']+)'", _block(text, "export const PAGE_ANCHORS")))
    matches = re.findall(
        r"path:\s*'([^']+)',\s*"
        r"name:\s*'([^']+)',"
        r"[\s\S]*?"
        r"anchor:\s*PAGE_ANCHORS\.(\w+),\s*requireLogin:\s*(true|false)",
        text,
    )
    return [
        {
            "path": path,
            "name": name,
            "anchor": anchors[anchor_key],
            "require_login": require_login == "true",
        }
        for path, name, anchor_key, require_login in matches
    ]


def test_page_anchors_match_the_dynamic_route_table() -> None:
    """`PAGE_ANCHORS` 与 `routes.json` 的 `page_code` 必须逐条对齐。

    两边都是"页面锚点"的口径来源：前端用它做路由与埋点归属，动态资源用它下发
    `require_login` 等页面属性。漂移时前端不会报错，只会让某个页面的登录拦截
    与埋点归属对不上——这正是最难查的一类。
    """
    frontend = _frontend_routes()
    declared = _registry("routes.json")
    assert len(frontend) == len(declared), (
        f"前端路由条数与 routes.json 不一致（解析到 {len(frontend)} 条 / "
        f"动态资源 {len(declared)} 条）。新增路由请同时改两处："
        "src/router/index.ts 与 data/registry/routes.json"
    )

    by_path = {route["path"]: route for route in frontend}
    for item in declared:
        route = by_path.get(item["path"])
        assert route is not None, f"routes.json 里的 {item['path']} 在前端路由里不存在"
        assert route["anchor"] == item["page_code"], (
            f"路径 {item['path']} 的页面锚点不一致："
            f"前端 PAGE_ANCHORS={route['anchor']} / routes.json={item['page_code']}"
        )
        assert route["require_login"] == item["require_login"], (
            f"路径 {item['path']} 的 require_login 不一致："
            f"前端={route['require_login']} / routes.json={item['require_login']}"
        )


def test_menu_routes_point_at_real_routes() -> None:
    """顶层导航菜单指向的 route 必须是真实路由。

    菜单是动态资源，改一条不需要发版——代价是"指向不存在的路由"在运行时只会
    表现为点了没反应。这里挡住。
    """
    paths = {route["path"] for route in _frontend_routes()}
    for menu in _registry("menus.json"):
        assert menu["route"] in paths, (
            f"菜单 {menu['code']} 指向 {menu['route']}，但前端没有这条路由"
        )


# --------------------------------------------------------------------------
# 3. 接口清单：endpoints.ts 的 url ↔ 后端 OpenAPI 路径
# --------------------------------------------------------------------------


def _normalized(path: str) -> str:
    """把路径参数归一化：`/app/assets/{asset_type}/versions` 与
    `/app/assets/${assetType}/versions` 视为同一条。"""
    path = re.sub(r"\$\{[^}]*\}", "{}", path)
    return re.sub(r"\{[^}]*\}", "{}", path)


def _frontend_urls() -> set[str]:
    text = ENDPOINTS_TS.read_text(encoding="utf-8")
    urls = {match for match in re.findall(r"url:\s*[`'\"]([^`'\"]+)[`'\"]", text)}
    assert urls, "没解析到 endpoints.ts 的 url——守卫会变成空跑"
    return {_normalized(FRONTEND_PREFIX + url) for url in urls}


def test_every_frontend_endpoint_exists_on_the_backend() -> None:
    """前端接口清单里的每个 url 都必须在后端真实存在。

    这是"404 而 OpenAPI 里看着有这条路由"的机械防线：前端拼错业务段、后端改了
    路径、前缀两处不一致，都会在这里失败。
    """
    from zhiyin_api.app import create_app

    backend = {_normalized(path) for path in create_app().openapi()["paths"]}
    unknown = sorted(_frontend_urls() - backend)
    assert not unknown, (
        "endpoints.ts 引用了后端不存在的接口：\n  " + "\n  ".join(unknown)
    )


def test_backend_business_endpoints_are_all_used_by_the_frontend() -> None:
    """反向：后端每条业务接口都必须出现在前端清单里（除非显式豁免）。

    一期前端的消费面就是全部业务接口，所以"后端加了接口、前端不知道"应该立刻可见。
    将来出现后台/运营专用接口时，把路径加进下面的豁免表并写清原因。
    """
    from zhiyin_api.app import create_app

    exempt: set[str] = set()
    backend = {
        _normalized(path)
        for path in create_app().openapi()["paths"]
        if path != "/healthz"
    }
    unused = sorted(backend - _frontend_urls() - exempt)
    assert not unused, (
        "后端这些接口还没进前端清单（endpoints.ts）：\n  "
        + "\n  ".join(unused)
        + "\n确属非前端接口时，请加入本用例的 exempt 表并注明用途。"
    )


# --------------------------------------------------------------------------
# 4. 生成物与落位表
# --------------------------------------------------------------------------


def test_api_types_are_generated_not_handwritten() -> None:
    """`types.ts` 必须是生成物。

    它曾经是一个 `export type ApiTypes = Record<string, never>` 的占位——
    占位最坏的地方不是"类型不对"，而是**看起来有类型**（`ApiTypes` 能通过编译，
    但什么字段都接受）。这里钉住"它由 openapi-typescript 生成"。
    """
    text = TYPES_TS.read_text(encoding="utf-8")
    assert "This file was auto-generated by openapi-typescript" in text, (
        "src/api/types.ts 不是生成物。请运行：cd zhiyin-web && npm run gen:api"
    )
    assert f'"{FRONTEND_PREFIX}/app/bootstrap"' in text, (
        "types.ts 里没有 /app/bootstrap——生成源（../contracts/openapi.json）可能过期，"
        "请先运行 python scripts/export_openapi.py"
    )


_COMPONENT_FILES: dict[str, Path] = {}
for _path in sorted((SRC / "components").rglob("*.vue")):
    _COMPONENT_FILES[_path.stem] = _path


def _readme_component_refs() -> set[str]:
    """取出《前端 README》§二 落位表「主要组件」列里的全部引用（归一化为文件名）。

    只读这一列：同一张表的「锚点」列写的是 `#screen-home`、「数据来源」列写的是接口名，
    它们不是文件名，混进来会让守卫把正常的表格判成"文件不存在"。
    """
    text = WEB_README.read_text(encoding="utf-8")
    table_start = text.index("## 二、页面 → 组件 → 接口")
    table_end = text.index("## 三、", table_start)
    references: set[str] = set()
    for row in text[table_start:table_end].splitlines():
        if not row.startswith("|"):
            continue
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < 4 or cells[0] in {"页面", "---"}:
            continue
        # 第 3 列是「页面文件」（App.vue / pages/HomePage.vue），
        # 第 4 列是「主要组件」（home/TaskCardGroup、conversation/{...}）。
        for cell in (cells[2], cells[3]):
            # 花括号展开：conversation/{SessionList,ChatStream,PipelinePanel} → 三个名字
            flattened = cell.replace("{", "").replace("}", "").replace("`", "")
            for token in re.split(r"、|,|\s+", flattened):
                token = token.strip()
                if not token:
                    continue
                name = token.split("/")[-1].removesuffix(".vue")
                # 跳过 `App.vue` / `components/...` 之间的分隔符（`/`、`—` 这类）
                if name and name.isidentifier():
                    references.add(name)
    assert references, "没解析到前端落位表——守卫会变成空跑"
    return references


def test_frontend_placement_table_matches_real_files() -> None:
    """《前端 README》§二 的落位表 ↔ 真实文件（与后端 services 落位表守卫同源）。

    后端已经把"表格里的格子必须是真实文件"做成守卫，前端此前没有：22 个组件
    只写在表格里时，新人照表找文件会扑空，而两个人各自新建同名组件也不会被发现。
    """
    referenced = _readme_component_refs()
    actual = set(_COMPONENT_FILES) | {path.stem for path in (SRC / "pages").glob("*.vue")}
    actual.add("App")

    missing_files = sorted(name for name in referenced if name not in actual)
    undocumented = sorted(name for name in actual if name not in referenced)

    assert not missing_files, (
        f"前端落位表里写了、但文件不存在的组件/页面：{missing_files}。"
        "请补文件，或把表格里的名字改成真实文件名"
    )
    assert not undocumented, (
        f"这些组件/页面文件没有登记进《前端 README》§二 落位表：{undocumented}。"
        "新增组件请同时补表格（一人一格，避免并行时新建同名文件）"
    )


@pytest.mark.parametrize(
    "relative",
    ["src/api/client.ts", "src/api/endpoints.ts", "src/api/schema.ts", "src/api/types.ts"],
)
def test_api_directory_is_documented(relative: str) -> None:
    """`src/api/` 下每个文件都要在 README 里说明职责（口径唯一处不允许隐身）。"""
    assert (WEB_ROOT / relative).is_file(), f"{relative} 不存在"
    assert Path(relative).name in WEB_README.read_text(encoding="utf-8"), (
        f"{relative} 没有写进《前端 README》§一 目录职责表"
    )


# --- 死 CSS 守卫 -----------------------------------------------------------
#
# 这一节的来历：清除前端演示数据时，**删了标记却留下样式**，两轮共潜藏 600+ 行
# 没有对应元素的 CSS（雷达图、维恩图、热力图、演示对话框…）。它不报错、不影响构建，
# 只在后来人读代码时制造"这些功能存在"的错觉。症状是典型的"不报错的错"，
# 因此变成机械可判。
#
# 判定一个类"被引用"的口径（**宁漏不误杀**，避免守卫逼人删真在用的样式）：
#   1. 任意 `.vue` 模板里 `class="a b"` 的字面量（含**父组件给子组件根元素**加类）；
#   2. 任意 `:class` 绑定里的对象键（`{ done: x }`）、字符串字面量，以及模板字面量的
#      字面前缀（`:class="`is-${s.status}`"` → 放行 `is-` 开头的类）；
#   3. **整条**字符串字面量恰好等于类名——覆盖 `:class="agent.theme"` 这类数据驱动取值。
#      必须是整条相等：`'/app/track'` 不等于 `track`，所以 `.track` 仍会被判死；
#   4. `:deep(...)` / `:slotted(...)` 里的类：那是**故意**伸进子组件的，父组件无权断言；
#   5. `<Transition name="pop">` 对应的 `pop-enter-active` 等过渡类。
#
# 已知局限（宁可漏）：`.bar` 这类**跨组件同名**的共用类，只要有一个组件用了，
# 另一个组件里的同名死规则就不会被发现。要覆盖它需要解析组件依赖图，收益不值当。

_TRANSITION_NAMES = re.compile(r"<[Tt]ransition[^>]*\bname=\"([\w-]+)\"")
_TRANSITION_SUFFIXES = (
    "enter-from", "enter-active", "enter-to", "leave-from", "leave-active", "leave-to",
)
_TEMPLATE_LITERAL_PREFIX = re.compile(r"`([A-Za-z][\w-]*-)\$\{")
_PSEUDO = re.compile(r"::?[a-zA-Z-]+(\([^)]*\))?")
_COMBINATOR = re.compile(r"\s*[>+~]\s*|\s+")
_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_CLASS_ATTR = re.compile(r'class="([^"]*)"')
_IMPORT_VUE = re.compile(r"import\s+(\w+)\s+from\s+['\"][^'\"]*/([\w-]+)\.vue['\"]")
_VUE_SOURCES = sorted(SRC.rglob("*.vue"))
_SCRIPT_SOURCES = sorted(p for p in SRC.rglob("*") if p.suffix in {".ts", ".js"})

# 需要按“父组件的 scoped 样式可以给子组件根元素加类”处理的标签名。
_NATIVE_TAGS = {
    "template", "div", "span", "p", "a", "ul", "ol", "li", "section", "header", "footer",
    "main", "nav", "aside", "h1", "h2", "h3", "h4", "h5", "h6", "button", "input", "form",
    "label", "select", "option", "textarea", "img", "svg", "path", "circle", "g", "line",
    "polyline", "polygon", "text", "table", "thead", "tbody", "tr", "th", "td", "b", "i",
    "em", "strong", "small", "code", "pre", "br", "hr", "dl", "dt", "dd", "figure",
    "figcaption", "article", "time", "mark", "abbr", "blockquote", "transition",
    "transition-group", "keep-alive", "teleport", "suspense", "component", "slot", "iframe",
}


def _template_of(text: str) -> str:
    return text[: text.rindex("</template>")] if "</template>" in text else ""


def _root_classes(text: str) -> frozenset[str]:
    """组件模板里第一个带 `class` 的元素（其根元素）的类集合。"""
    remainder = _COMMENT.sub("", _template_of(text))
    match = re.search(r"<([A-Za-z][\w-]*)([^>]*)>", remainder)
    while match:
        classes = _CLASS_ATTR.search(match.group(2))
        if classes:
            return frozenset(classes.group(1).split())
        # 必须真的把剩余串截短：`match.end()` 是相对当前剩余串的偏移，
        # 拿它去切原串会让位置回退，在两个匹配点之间无限振荡。
        remainder = remainder[match.end() :]
        match = re.search(r"<([A-Za-z][\w-]*)([^>]*)>", remainder)
    return frozenset()


def _element_class_sets(text: str) -> list[frozenset[str]]:
    return [frozenset(attr.split()) for attr in _CLASS_ATTR.findall(_template_of(text))]


def _dynamic_classes(text: str) -> tuple[set[str], set[str]]:
    """(动态类名, 动态类名前缀)——静态分析无从断言，一律放行。"""
    names: set[str] = set()
    prefixes: set[str] = set()
    template = _template_of(text)
    for binding in re.findall(r':class="([^"]*)"', template):
        for obj in re.findall(r"\{([^}]*)\}", binding):
            names.update(re.findall(r"([A-Za-z_][\w-]*)\s*:", obj))
        names.update(re.findall(r"'([^'\n]*)'", binding))
        prefixes.update(_TEMPLATE_LITERAL_PREFIX.findall(binding))
    for transition in _TRANSITION_NAMES.findall(template):
        names.update(f"{transition}-{suffix}" for suffix in _TRANSITION_SUFFIXES)
    return names, prefixes


def _global_string_literals() -> set[str]:
    """全前端整条字符串字面量：`:class="agent.theme"` 这类数据驱动取值的来源。

    必须是**整条相等**才算引用：`'/app/track'` 不等于 `track`，所以 `.track` 仍会被判死。
    """
    found: set[str] = set()
    for path in _VUE_SOURCES + _SCRIPT_SOURCES:
        text = path.read_text(encoding="utf-8", errors="ignore")
        found.update(re.findall(r"'([^'\n]*)'", text))
        found.update(re.findall(r'"([^"\n]*)"', text))
    return found


def _reachable_universe() -> dict[str, set[frozenset[str]]]:
    """每个组件"自己的 scoped 样式可能命中的元素类集合"。

    作用域口径：本项目所有 `<style>` 都是 `scoped`，所以父组件的规则只能命中
    **自己模板里的元素**，以及**它渲染的子组件根元素**（Vue scoped 的既定行为）。
    不能拿兄弟组件的模板来"证明"某个类还活着——那正是
    `WorkspacePage` 里 11 条 `.swot-cell*` 死规则此前一直没被发现的原因。
    """
    texts: dict[Path, str] = {}
    for path in _VUE_SOURCES:
        texts[path] = path.read_text(encoding="utf-8")

    by_stem = {path.stem: path for path in _VUE_SOURCES}
    universe: dict[str, set[frozenset[str]]] = {}
    for path, text in texts.items():
        sets = set(_element_class_sets(text))
        # `:deep(.x)` / `:slotted(.x)` 是**故意**伸进子组件的选择器，父组件确实能命中它。
        if "<style" in text:
            style = text[text.index("<style") : text.rindex("</style>")]
            for arg in re.findall(r":(?:deep|slotted)\(([^)]*)\)", style):
                for name in re.findall(r"\.(-?[A-Za-z_][\w-]*)", arg):
                    sets.add(frozenset({name}))
        script = text[: text.index("<template>")] if "<template>" in text else text
        for _local, stem in _IMPORT_VUE.findall(script):
            child = by_stem.get(stem)
            if child is not None and child != path:
                root = _root_classes(texts[child])
                if root:
                    sets.add(root)
        universe[path.relative_to(WEB_ROOT).as_posix()] = sets
    return universe


def _iter_style_rules(style: str, base: int = 0):
    """产出 (选择器, 删除起点, 删除终点)；能正确处理 `@media` 嵌套与注释。

    删除起点取"上一条规则结束之后"，这样连同行间空行一起删掉，不留空段落。
    """
    cursor = 0
    length = len(style)
    while cursor < length:
        brace = style.find("{", cursor)
        if brace == -1:
            return
        raw_selector = _COMMENT.sub("", style[cursor:brace]).strip()
        depth = 1
        end = brace + 1
        while end < length and depth:
            if style[end] == "{":
                depth += 1
            elif style[end] == "}":
                depth -= 1
            end += 1
        if raw_selector.startswith("@"):
            yield from _iter_style_rules(style[brace + 1 : end - 1], base + brace + 1)
        elif raw_selector:
            yield raw_selector, base + cursor, base + end
        cursor = end


def _selector_is_reachable(
    selector: str,
    element_sets: set[frozenset[str]],
    dynamic: set[str],
    prefixes: set[str],
) -> bool:
    """**逗号列表里的任一分支**可能命中真实元素即为可达。

    单条分支再逐"复合部分"（空格/`>`/`+`/`~` 分隔）判定：没有类名的部分（纯标签、`*`）
    恒可满足；含动态类名的部分无法静态断言，放行；否则要求某个真实元素的类集合
    **包含**该部分的全部类名——`.heat-cell.strong` 这类"每个类名各自有人用、组合却没人用"
    的规则正是在这一步被检出。
    """
    for alternative in selector.split(","):
        reachable = True
        for part in _COMBINATOR.split(alternative.strip()):
            classes = set(re.findall(r"\.(-?[A-Za-z_][\w-]*)", part))
            if not classes:
                continue
            if any(name in dynamic for name in classes):
                continue
            if any(name.startswith(prefix) for name in classes for prefix in prefixes):
                continue
            if not any(classes <= element_set for element_set in element_sets):
                reachable = False
                break
        if reachable:
            return True
    return False


def orphan_css_rules() -> list[tuple[str, str, int, int]]:
    """全前端"本组件里无人能命中"的样式规则。

    → [(相对路径, 选择器, 删除起点, 删除终点)]，偏移相对于文件内 `<style>` 之后，
    供修复脚本直接切片删除（测试只关心它是否为空）。
    """
    global_strings = _global_string_literals()
    universe = _reachable_universe()
    orphans: list[tuple[str, str, int, int]] = []
    for path in _VUE_SOURCES:
        text = path.read_text(encoding="utf-8")
        if "<style" not in text or "<template>" not in text:
            continue
        relative = path.relative_to(WEB_ROOT).as_posix()
        element_sets = set(universe.get(relative, set()))
        dynamic, prefixes = _dynamic_classes(text)
        dynamic |= global_strings
        style_start = text.index("<style")
        style = text[style_start : text.rindex("</style>")]
        for selector, start, end in _iter_style_rules(style):
            if _selector_is_reachable(selector, element_sets, dynamic, prefixes):
                continue
            orphans.append((relative, selector, start, end))
    return orphans


def test_no_orphan_css_classes_in_components() -> None:
    """组件 `<style scoped>` 里不得留下**本组件没有任何元素能命中**的规则。

    症状是"删了元素忘了删样式"：不报错、不影响构建，但会让后来人以为功能还在。
    判定口径见 `_reachable_universe` / `_selector_is_reachable` 的注释。
    出现红时按此二选一：**要么删样式，要么在判定口径里说明它为什么算可达**
    （例如由动态类名前缀生成、或属于 `:deep()` 伸入的子组件）。
    不要靠放宽本守卫来变绿。
    """
    orphans = orphan_css_rules()
    assert not orphans, (
        "以下 CSS 规则在本组件内没有任何元素能命中，疑似删除元素后遗留的死样式：\n  "
        + "\n  ".join(f"{path}  {selector}" for path, selector, _, _ in orphans)
    )




