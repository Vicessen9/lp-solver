import pulp, uvicorn, sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

print = lambda x: sys.stdout.write(x + "\n") and sys.stdout.flush()  # 强制刷日志

# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pulp
import uvicorn

app = FastAPI(title="lp-solver")

# ---------- 请求体校验 ----------
class Constraint(BaseModel):
    name: str
    lhs: dict          # 变量系数表，例如 {"x":1,"y":2}
    sense: str = Field(regex="^(<=|>=|==)$")
    rhs: float

class Data(BaseModel):
    objective: dict                         # 目标函数系数，例如 {"x":3,"y":2}
    constraints: list[Constraint]
    sense: str = Field(regex="^(Minimize|Maximize)$")

# ---------- 核心求解接口 ----------
@app.post("/solve")
def solve(data: Data):
    # 1. 日志
    print("---- 收到原始 payload ----", flush=True)
    print(data.json(), flush=True)
    print("--------------------------", flush=True)

    # 2. 空值快速拦截
    if not data.objective:
        raise HTTPException(status_code=422, detail="objective 不能为空")
    if not data.constraints:
        raise HTTPException(status_code=422, detail="constraints 不能为空")

    # 3. 建模型
    prob = pulp.LpProblem(
        "SC",
        pulp.LpMinimize if data.sense == "Minimize" else pulp.LpMaximize,
    )
    # 3-1 建变量（>=0）
    vars = {k: pulp.LpVariable(k, lowBound=0) for k in data.objective}
    # 3-2 目标函数
    prob += pulp.lpSum([data.objective[k] * vars[k] for k in vars])

    # 3-3 约束
    for c in data.constraints:
        lhs = pulp.lpSum([c.lhs.get(k, 0) * vars[k] for k in vars])
        if c.sense == "<=":
            prob += lhs <= c.rhs
        elif c.sense == ">=":
            prob += lhs >= c.rhs
        else:  # ==
            prob += lhs == c.rhs

    # 4. 求解
    prob.solve()
    status = pulp.LpStatus[prob.status]
    var_values = {v.name: v.value() for v in vars.values()}
    optimum = pulp.value(prob.objective)

    # 5. 打印结果（方便日志排错）
    print(f"求解完成 -> status={status}, vars={var_values}, optimum={optimum}")

    # 6. 返回
    return {"status": status, "vars": var_values, "optimum": optimum}

# ---------- 健康检查 ----------
@app.get("/")
def root():
    return {"message": "lp-solver is running"}

# ---------- Render 用 gunicorn 启动，本地可 uvicorn ----------
if __name__ == "__main__":
    # 本地调试：uvicorn main:app --host 0.0.0.0 --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)