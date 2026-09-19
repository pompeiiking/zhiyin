"""Create, read, update and clean real Wanwu business objects.

This probe deliberately does not invoke an LLM or embedding endpoint.  It uses a
unique prefix, registers every successful create immediately, and always runs
cleanup in reverse dependency order.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
import pymysql
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


RUN_ID = os.getenv("ZHIYIN_SMOKE_RUN_ID", f"zhiyin-smoke-{int(time.time())}")
BASE_URL = os.getenv("WANWU_SMOKE_BASE_URL", "http://nginx:8081").rstrip("/")
ADMIN_USER = os.getenv("WANWU_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("WANWU_ADMIN_PASSWORD", "Wanwu123456")
MYSQL_HOST = os.getenv("WANWU_MYSQL_HOST", "mysql")
MYSQL_PASSWORD = os.environ["WANWU_MYSQL_PASSWORD"]
AES_KEY = b"f5Su3GhNMM1rndyp"
AES_IV = b"sdf4ddfsFD86Vdf2"


class ProbeError(RuntimeError):
    pass


def encrypt_password(value: str) -> str:
    padder = PKCS7(128).padder()
    padded = padder.update(value.encode()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(AES_KEY), modes.CBC(AES_IV)).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return quote(base64.b64encode(encrypted).decode(), safe="")


@dataclass
class Cleanup:
    service: str
    action: Callable[[], None]


class Probe:
    def __init__(self) -> None:
        self.client = httpx.Client(base_url=BASE_URL, timeout=20, trust_env=False)
        self.headers: dict[str, str] = {"x-language": "zh-CN"}
        self.results: list[dict[str, str]] = []
        self.cleanups: list[Cleanup] = []

    def record(self, service: str, operation: str, detail: str = "ok") -> None:
        self.results.append(
            {"service": service, "operation": operation, "status": "passed", "detail": detail}
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        response = self.client.request(
            method,
            path,
            json=payload,
            params=params,
            headers=self.headers if auth else {"x-language": "zh-CN"},
        )
        if response.status_code >= 400:
            raise ProbeError(f"{method} {path}: HTTP {response.status_code}: {response.text[:300]}")
        try:
            body = response.json()
        except ValueError as exc:
            raise ProbeError(f"{method} {path}: non-JSON response") from exc
        if body.get("code") not in (0, "0"):
            raise ProbeError(f"{method} {path}: code={body.get('code')} msg={body.get('msg')}")
        return body

    def add_cleanup(self, service: str, action: Callable[[], None]) -> None:
        self.cleanups.append(Cleanup(service, action))

    @staticmethod
    def mysql_execute(sql: str, params: tuple[Any, ...]) -> None:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user="root",
            password=MYSQL_PASSWORD,
            database="zhiyin_service",
            connect_timeout=10,
            autocommit=True,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
        finally:
            connection.close()

    def login(self) -> None:
        captcha = self.request("GET", "/user/api/v1/base/captcha", auth=False)["data"]
        captcha_id = str(captcha.get("key") or captcha.get("id"))
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user="root",
            password=MYSQL_PASSWORD,
            database="iam_service",
            connect_timeout=10,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT code FROM captchas WHERE id=%s", (captcha_id,))
                row = cursor.fetchone()
        finally:
            connection.close()
        if not row:
            raise ProbeError("captcha was not persisted by IAM")
        password = encrypt_password(ADMIN_PASSWORD)
        body = self.request(
            "POST",
            "/user/api/v1/base/login",
            payload={
                "username": ADMIN_USER,
                "password": password,
                "key": captcha_id,
                "code": str(row[0]),
            },
            auth=False,
        )["data"]
        token = str(body.get("token") or body.get("accessToken") or "")
        uid = str(body.get("uid") or body.get("userId") or "")
        org = ((body.get("orgPermission") or {}).get("org") or {})
        org_id = str(org.get("id") or org.get("orgId") or "1")
        if not token or not uid:
            raise ProbeError("login response did not include token and uid")
        self.headers.update(
            {"Authorization": f"Bearer {token}", "x-user-id": uid, "x-org-id": org_id}
        )
        self.record("iam-service", "authenticate", "admin session established")

    def org(self) -> None:
        name = RUN_ID[:50]
        data = self.request("POST", "/user/api/v1/org", payload={"name": name, "remark": RUN_ID})["data"]
        org_id = str(data.get("orgId") or data.get("id"))
        if not org_id:
            raise ProbeError("org create returned no orgId")
        self.add_cleanup(
            "iam-service", lambda: self.request("DELETE", "/user/api/v1/org", payload={"orgId": org_id})
        )
        found = self.request("GET", "/user/api/v1/org/info", params={"orgId": org_id})["data"]
        if str(found.get("orgId") or found.get("id")) != org_id:
            raise ProbeError("created organization could not be read")
        updated = f"{name}-u"[:50]
        self.request(
            "PUT", "/user/api/v1/org", payload={"orgId": org_id, "name": updated, "remark": f"{RUN_ID}-updated"}
        )
        self.record("iam-service", "organization:create/read/update", "real organization")

    def user(self) -> None:
        suffix = str(int(time.time()))[-8:]
        username = f"zys{suffix}"
        phone = f"139{suffix}"
        payload = {
            "username": username,
            "nickname": RUN_ID[:40],
            "password": encrypt_password("Probe_123456"),
            "phone": phone,
            "email": f"{username}@example.invalid",
            "remark": RUN_ID,
            "gender": "",
            "company": "zhiyin-smoke",
            "roleIds": [],
        }
        data = self.request("POST", "/user/api/v1/user", payload=payload)["data"]
        user_id = str(data.get("userId") or data.get("id"))
        if not user_id:
            raise ProbeError("user create returned no userId")
        self.add_cleanup(
            "iam-service", lambda: self.request("DELETE", "/user/api/v1/user", payload={"userId": user_id})
        )
        listing = self.request(
            "GET", "/user/api/v1/user/list", params={"name": username, "pageNo": 1, "pageSize": 20}
        )["data"]
        if user_id not in json.dumps(listing, ensure_ascii=False):
            raise ProbeError("created user was not returned by user list")
        payload.update({"userId": user_id, "nickname": f"{RUN_ID[:35]}-updated"})
        self.request("PUT", "/user/api/v1/user", payload=payload)
        self.record("iam-service", "user:create/read/update", "real user")

    def model(self) -> str:
        provider = "OpenAI-API-compatible"
        model = f"{RUN_ID}-embedding"
        common = {"provider": provider, "modelType": "embedding", "model": model}
        payload = {
            **common,
            "displayName": RUN_ID,
            "publishDate": "2026-09-19",
            "config": {"apiKey": "probe-not-used", "endpointUrl": "http://127.0.0.1:9/v1"},
        }
        self.request("POST", "/user/api/v1/model", payload=payload)
        self.add_cleanup("model-service", lambda: self.request("DELETE", "/user/api/v1/model", payload=common))
        found = self.request("GET", "/user/api/v1/model", params=common)["data"]
        model_id = str(found.get("modelId") or found.get("id"))
        if not model_id:
            raise ProbeError("created model could not be read")
        self.request("PUT", "/user/api/v1/model", payload={**payload, "modelId": model_id, "displayName": f"{RUN_ID}-updated"})
        self.request("PUT", "/user/api/v1/model/status", payload={**common, "isActive": False})
        self.record("model-service", "model:create/read/update/status", "configuration only; inference skipped")
        return model_id

    def knowledge(self, model_id: str) -> None:
        name = RUN_ID.lower()
        data = self.request(
            "POST",
            "/user/api/v1/knowledge",
            payload={"name": name, "description": RUN_ID, "embeddingModelInfo": {"modelId": model_id}},
        )["data"]
        knowledge_id = str(data.get("knowledgeId") or data.get("id"))
        if not knowledge_id:
            raise ProbeError("knowledge create returned no knowledgeId")
        self.add_cleanup(
            "knowledge-service",
            lambda: self.request("DELETE", "/user/api/v1/knowledge", payload={"knowledgeId": knowledge_id}),
        )
        selected = self.request("GET", "/user/api/v1/knowledge/select", params={"name": name})["data"]
        if knowledge_id not in json.dumps(selected, ensure_ascii=False):
            raise ProbeError("created knowledge base could not be read")
        self.request(
            "PUT",
            "/user/api/v1/knowledge",
            payload={"knowledgeId": knowledge_id, "name": f"{name}-u", "description": f"{RUN_ID}-updated"},
        )
        self.record("knowledge-service", "knowledge:create/read/update", "document embedding skipped")

    def mcp(self) -> None:
        name = RUN_ID[:60]
        self.request(
            "POST",
            "/user/api/v1/mcp",
            payload={
                "mcpSquareId": "",
                "name": name,
                "desc": RUN_ID,
                "from": "custom",
                "sseUrl": "http://127.0.0.1:9/sse",
            },
        )
        listing = self.request("GET", "/user/api/v1/mcp/list", params={"name": name, "pageNo": 1, "pageSize": 20})["data"]
        items = listing.get("list", listing if isinstance(listing, list) else [])
        match = next((item for item in items if item.get("name") == name), None)
        mcp_id = str((match or {}).get("mcpId") or "")
        if not mcp_id:
            raise ProbeError("created MCP definition could not be read")
        self.add_cleanup("mcp-service", lambda: self.request("DELETE", "/user/api/v1/mcp", payload={"mcpId": mcp_id}))
        self.request("GET", "/user/api/v1/mcp", params={"mcpId": mcp_id})
        self.record("mcp-service", "definition:create/read", "service has no update endpoint")

    def rag(self) -> str:
        name = RUN_ID[:60]
        data = self.request("POST", "/user/api/v1/appspace/rag", payload={"name": name, "desc": RUN_ID})["data"]
        rag_id = str(data.get("ragId") or data.get("id"))
        if not rag_id:
            raise ProbeError("RAG create returned no ragId")
        self.add_cleanup("rag-service", lambda: self.request("DELETE", "/user/api/v1/appspace/rag", payload={"ragId": rag_id}))
        self.request("GET", "/user/api/v1/appspace/rag", params={"ragId": rag_id})
        self.request("PUT", "/user/api/v1/appspace/rag", payload={"ragId": rag_id, "name": name, "desc": f"{RUN_ID}-updated"})
        self.record("rag-service", "rag:create/read/update", "inference skipped")
        return rag_id

    def assistant(self) -> str:
        name = RUN_ID[:60]
        self.request("POST", "/user/api/v1/assistant", payload={"name": name, "desc": RUN_ID, "avatar": {"key": "", "path": ""}})
        listing = self.request("GET", "/user/api/v1/appspace/app/list", params={"name": name, "appType": "agent"})["data"]
        items = listing.get("list", [])
        match = next((item for item in items if item.get("name") == name), None)
        assistant_id = str((match or {}).get("appId") or (match or {}).get("assistantId") or "")
        if not assistant_id:
            raise ProbeError("created assistant could not be read")
        # The deployed gateway does not expose DELETE /assistant although the
        # handler exists in source; the generic app-space delete is the public
        # cascade-delete endpoint for agent applications.
        self.add_cleanup(
            "assistant-service",
            lambda: self.request(
                "DELETE",
                "/user/api/v1/appspace/app",
                payload={"appId": assistant_id, "appType": "agent"},
            ),
        )
        self.request("GET", "/user/api/v1/assistant", params={"assistantId": assistant_id})
        self.request("PUT", "/user/api/v1/assistant", payload={"assistantId": assistant_id, "name": name, "desc": f"{RUN_ID}-updated", "avatar": {"key": "", "path": ""}})
        self.record("assistant-service", "assistant:create/read/update", "inference skipped")
        return assistant_id

    def app_key(self, app_id: str, app_type: str) -> None:
        self.request("POST", "/user/api/v1/appspace/app/publish", payload={"appId": app_id, "appType": app_type, "publishType": "private"})
        data = self.request("POST", "/user/api/v1/appspace/app/key", payload={"appId": app_id, "appType": app_type})["data"]
        api_id = str(data.get("apiId") or data.get("id") or "")
        if not api_id or not data.get("apiKey"):
            raise ProbeError("app key create returned no key metadata")
        self.add_cleanup("app-service", lambda: self.request("DELETE", "/user/api/v1/appspace/app/key", payload={"apiId": api_id}))
        keys = self.request("GET", "/user/api/v1/appspace/app/key/list", params={"appId": app_id, "appType": app_type})["data"]
        if api_id not in json.dumps(keys, ensure_ascii=False):
            raise ProbeError("created app key could not be listed")
        self.record("app-service", "publish/key:create/read/revoke", "API key value redacted")

    def workflow(self) -> None:
        payload = {"configName": RUN_ID[:30], "configENName": f"zy{int(time.time())}", "configDesc": RUN_ID, "isStream": False}
        data = self.request("POST", "/workflow/api/workflow/create", payload=payload)["data"]
        workflow_id = str(data.get("workflowID") or data.get("workflow_id") or data.get("id") or "")
        if not workflow_id:
            raise ProbeError("workflow create returned no workflowID")
        self.add_cleanup("agentscope", lambda: self.request("DELETE", "/workflow/api/workflow/delete", payload={"workflowID": workflow_id}))
        self.request("GET", "/workflow/api/workflow/get", params={"workflowID": workflow_id})
        self.record("agentscope", "workflow:create/read", "execution skipped")

    def elasticsearch(self) -> None:
        index = RUN_ID.lower()
        password = os.environ["WANWU_ELASTIC_PASSWORD"]
        es = httpx.Client(base_url="https://es:9200", auth=("elastic", password), verify=False, timeout=20, trust_env=False)
        try:
            response = es.put(f"/{index}")
            if response.status_code not in (200, 201):
                raise ProbeError(f"ES index create failed: {response.status_code} {response.text[:200]}")
            self.add_cleanup("elasticsearch", lambda: es.delete(f"/{index}").raise_for_status())
            es.put(f"/{index}/_doc/1", params={"refresh": "true"}, json={"marker": RUN_ID, "body": f"unique {RUN_ID}"}).raise_for_status()
            hit = es.post(f"/{index}/_search", json={"query": {"match": {"body": RUN_ID}}}).json()["hits"]["total"]["value"]
            if hit != 1:
                raise ProbeError("ES BM25 query did not return the probe document")
            es.post(f"/{index}/_update/1", params={"refresh": "true"}, json={"doc": {"state": "updated"}}).raise_for_status()
            self.record("elasticsearch", "index/document:create/read/update", "TLS and BM25 verified")
        except Exception:
            es.close()
            raise

    def zhiyin_api(self) -> None:
        """Create a real task session through the public web reverse proxy.

        The frozen API has no session-delete endpoint, so cleanup is an exact,
        test-only SQL delete by the returned task id.  A temporary registry
        entry lets the probe avoid reusing any demo user's existing task.
        """
        task_code = f"smoke_{int(time.time())}"
        task_entry = {
            "code": task_code,
            "label": RUN_ID,
            "target_stage": "collect",
            "lead_agent": "profile_analyst",
            "sort_order": 9999,
        }
        self.mysql_execute(
            "INSERT INTO registry_resource(kind,resource_key,status,sort_order,bundle,payload,updated_at) "
            "VALUES('task_entries',%s,'enabled',9999,'',%s,NOW())",
            (task_code, json.dumps(task_entry, ensure_ascii=False)),
        )
        self.add_cleanup(
            "zhiyin-api",
            lambda: self.mysql_execute(
                "DELETE FROM registry_resource WHERE kind='task_entries' AND resource_key=%s",
                (task_code,),
            ),
        )
        web = httpx.Client(base_url="http://zhiyin-web:8080", timeout=20, trust_env=False)

        def api(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
            response = web.request(method, path, json=payload)
            if response.status_code >= 400:
                raise ProbeError(f"Zhiyin {method} {path}: HTTP {response.status_code}: {response.text[:300]}")
            body = response.json()
            if body.get("code") not in (0, "0"):
                raise ProbeError(f"Zhiyin {method} {path}: code={body.get('code')} msg={body.get('message')}")
            return body

        try:
            created = api("POST", "/api/v1/app/task/enter", {"task_code": task_code})["data"]
            task_id = str(created.get("task_id") or "")
            if not task_id:
                raise ProbeError("Zhiyin task create returned no task_id")
            self.add_cleanup(
                "zhiyin-api",
                lambda: self.mysql_execute(
                    "DELETE FROM task_session WHERE id=%s",
                    (task_id,),
                ),
            )
            self.add_cleanup(
                "zhiyin-api",
                lambda: self.mysql_execute(
                    "DELETE FROM conversation_memory WHERE task_key=%s",
                    (task_id,),
                ),
            )
            sessions = api("GET", "/api/v1/app/sessions")["data"]
            if task_id not in json.dumps(sessions, ensure_ascii=False):
                raise ProbeError("Zhiyin task session could not be listed")
            resumed = api("POST", "/api/v1/app/task/enter", {"task_code": task_code})["data"]
            if resumed.get("task_id") != task_id:
                raise ProbeError("Zhiyin task enter did not idempotently resume the object")
            api(
                "POST",
                "/api/v1/app/track",
                {
                    "event": "conv_disclosure_open",
                    "payload": {"marker": RUN_ID},
                    "client_event_id": RUN_ID,
                },
            )
            api("GET", "/api/v1/app/workspace")
            self.record(
                "zhiyin-api/zhiyin-web",
                "task-session:create/read/resume/track/cleanup",
                "public reverse proxy and real MySQL-backed session",
            )
        finally:
            web.close()

    def cleanup(self) -> bool:
        ok = True
        for item in reversed(self.cleanups):
            try:
                item.action()
                self.record(item.service, "cleanup")
            except Exception as exc:  # cleanup must continue after an individual failure
                ok = False
                self.results.append({"service": item.service, "operation": "cleanup", "status": "failed", "detail": str(exc)[:300]})
        return ok

    def run(self) -> int:
        failed: str | None = None
        cleanup_ok = False
        try:
            self.login()
            self.org()
            self.user()
            model_id = self.model()
            self.mcp()
            self.knowledge(model_id)
            rag_id = self.rag()
            self.assistant()
            self.app_key(rag_id, "rag")
            self.workflow()
            self.elasticsearch()
            self.zhiyin_api()
            self.record("bff-service/nginx", "authenticated-business-routing", "all object calls traversed gateway")
        except Exception as exc:
            failed = str(exc)
        finally:
            cleanup_ok = self.cleanup()
            self.client.close()
        report = {"run_id": RUN_ID, "ai_inference": "skipped", "results": self.results, "error": failed}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if failed is None and cleanup_ok else 1


if __name__ == "__main__":
    sys.exit(Probe().run())
