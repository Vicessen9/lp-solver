# main.py
from fastapi import FastAPI, HTTPException, Request   # Request 新增
from pydantic import BaseModel, Field
import pulp
import uvicorn

app = FastAPI(title="lp-solver")

# ---------- 请求体校验 ----------
class Constraint(BaseModel):
    name: str
    lhs: dict
    sense: str = Field(pattern="^(<=|>=|==)$")
    rhs: float

class Data(BaseModel):
    objective: dict
    constraints: list[Constraint]
    sense: str = Field(pattern="^(Minimize|Maximize)$")

# ---------- 核心求解接口 ----------
@app.post("/solve")
async def solve(request: Request):                      # ① 异步
    raw = await request.json()                          # ② 打印原始 JSON
    print("Dify 原始请求体:", raw)
    data = Data(**raw)                                  # ③ 转 Pydantic

    # 下面逻辑保持你原来不变
    if not data.objective:
        raise HTTPException(status_code=422, detail="objective 不能为空")
    if not data.constraints:
        raise HTTPException(status_code=422, detail="constraints 不能为空")

    prob = pulp.LpProblem("SC", pulp.LpMinimize if data.sense == "Minimize" else pulp.LpMaximize)
    vars = {k: pulp.LpVariable(k, lowBound=0) for k in data.objective}
    prob += pulp.lpSum([data.objective[k] * vars[k] for k in vars])

    for c in data.constraints:
        lhs = pulp.lpSum([c.lhs.get(k, 0) * vars[k] for k in vars])
        print(f"约束: {c.name}, lhs={c.lhs}, sense={c.sense}, rhs={c.rhs}")
        print(f"  本约束实际表达式 = {lhs} {c.sense} {c.rhs}")
        print(f"  当前变量字典 vars = {vars}")
        if c.sense == "<=":
            prob += lhs <= c.rhs
        elif c.sense == ">=":
            prob += lhs >= c.rhs
        else:
            prob += lhs == c.rhs

    prob.solve()
    status = pulp.LpStatus[prob.status]
    var_values = {v.name: v.value() for v in vars.values()}
    optimum = pulp.value(prob.objective)
    print(f"求解完成 -> status={status}, vars={var_values}, optimum={optimum}")
    return {"status": status, "vars": var_values, "optimum": optimum}

@app.get("/")
def root():
    return {"message": "lp-solver is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)