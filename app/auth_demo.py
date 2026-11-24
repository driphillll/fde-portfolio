"""教学示例：FastAPI 中「一个接口挂一个或多个中间件」怎么写。

Gin 里用 r.Use / group.Use / GET(path, mw1, mw2) 挂中间件；
FastAPI 对应的是 Depends 依赖注入，分层如下：
  1. 全局：@app.middleware("http") —— 见 app/main.py 里的 request_context
  2. 路由组：APIRouter(dependencies=[...])
  3. 单路由：@router.get(..., dependencies=[...]) 或函数参数 = Depends(...)

本文件自包含、无相对导入，可以直接：
    python -m app.auth_demo
也可以在 PyCharm 里直接 Debug 本文件（不会触发 parent package 报错）。
"""

from __future__ import annotations

import logging
import time

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException

logger = logging.getLogger("auth-demo")

# 演示用 token 表；生产应查 DB/Redis 并验签，这里只为讲清机制
_USERS = {
    "admin-token": {"id": 1, "name": "admin", "role": "admin"},
    "user-token": {"id": 2, "name": "alice", "role": "user"},
}


# 依赖 1：鉴权（对应 Gin 的 Auth 中间件）
def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    scheme, _, token = authorization.partition(" ") if authorization else ("", "", "")
    if scheme.lower() != "bearer" or token not in _USERS:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _USERS[token]


# 依赖 2：角色校验。注意它「嵌套」依赖 1 —— FastAPI 会先跑 get_current_user
def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user


# 依赖 3：yield 型依赖，演示 Gin 里 c.Next() 的前后包裹
# 注意：FastAPI 的 yield 后置代码在「响应发出之后」执行，此时改 response headers 已太晚，
# 所以后置逻辑适合做日志/清理/关连接，不适合改响应内容。
def add_timing():
    start = time.perf_counter()
    yield  # 这里把控制权交回给路由处理函数
    logger.info("elapsed_ms=%.2f", (time.perf_counter() - start) * 1000)


# 依赖 4：只做副作用、不取返回值的依赖（对应 Gin 里不往 Context 写值的中间件）
def audit_log(x_request_id: str | None = Header(default=None)) -> None:
    logger.info("audit: request_id=%s", x_request_id)


router = APIRouter(prefix="/demo", tags=["auth-demo"])


@router.get("/public")
def public():
    return {"msg": "公开接口，无依赖"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"user": user}


# 重点：一个接口挂多个依赖
# 实际执行链：add_timing → audit_log → get_current_user → require_admin → 处理函数
# 注意 require_admin 内部又依赖 get_current_user，同一请求内 FastAPI 只执行一次（有缓存）
@router.get("/admin/report")
def admin_report(
    user: dict = Depends(require_admin),
    _t=Depends(add_timing),
    _a=Depends(audit_log),
):
    return {"report": "secret", "by": user["name"]}


# 路由组级依赖：组内所有接口都要 admin（对应 gin 的 group.Use(Auth, Admin)）
# 这里用 dependencies=[...] 的写法：依赖只做拦截，返回值不注入处理函数
admin_router = APIRouter(
    prefix="/demo/admin",
    tags=["auth-demo-admin"],
    dependencies=[Depends(require_admin), Depends(add_timing)],
)


@admin_router.get("/stats")
def stats():
    return {"stats": "admin-only"}


def create_demo_app() -> FastAPI:
    app = FastAPI(title="auth-demo")
    app.include_router(router)
    app.include_router(admin_router)
    return app


app = create_demo_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8021)
