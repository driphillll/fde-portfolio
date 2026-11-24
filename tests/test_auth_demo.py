"""验证「一个接口挂多个依赖」的行为：嵌套鉴权、角色拦截、yield 后置逻辑。"""

import logging

from fastapi.testclient import TestClient

from app.auth_demo import create_demo_app

client = TestClient(create_demo_app())


def test_public_no_auth():
    r = client.get("/demo/public")
    assert r.status_code == 200
    assert r.json()["msg"] == "公开接口，无依赖"


def test_me_requires_auth():
    assert client.get("/demo/me").status_code == 401
    r = client.get("/demo/me", headers={"Authorization": "Bearer user-token"})
    assert r.status_code == 200
    assert r.json()["user"]["name"] == "alice"


def test_report_multiple_dependencies(caplog):
    # 无 token → 401
    assert client.get("/demo/admin/report").status_code == 401
    # 普通用户 → 403（require_admin 拦截）
    r = client.get(
        "/demo/admin/report", headers={"Authorization": "Bearer user-token"}
    )
    assert r.status_code == 403
    # admin → 200；通过日志确认 yield 后置逻辑与审计依赖都执行了
    with caplog.at_level(logging.INFO, logger="auth-demo"):
        r = client.get(
            "/demo/admin/report",
            headers={"Authorization": "Bearer admin-token", "X-Request-Id": "req-001"},
        )
    assert r.status_code == 200
    assert r.json()["by"] == "admin"
    assert "audit: request_id=req-001" in caplog.text
    assert "elapsed_ms=" in caplog.text


def test_router_group_dependencies():
    # 路由组级依赖：组内所有接口都要 admin
    assert client.get("/demo/admin/stats").status_code == 401
    r = client.get("/demo/admin/stats", headers={"Authorization": "Bearer admin-token"})
    assert r.status_code == 200
