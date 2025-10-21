from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pulp, json

app = FastAPI()

class Constraint(BaseModel):
    name: str
    lhs: dict          # 变量系数
    sense: str = Field(regex="^(<=|>=|==)$")
    rhs: float

class Data(BaseModel):
    objective: dict
    constraints: list[Constraint]
    sense: str = Field(regex="^(Minimize|Maximize)$")

@app.post("/solve")
def solve(data: Data):
    print("---- 原始 payload ----")
    print(data.json())          # 看看到底收到什么
    print("---------------------")

    if not data.objective:
        raise HTTPException(422, "objective 不能为空")
    if not data.constraints:
        raise HTTPException(422,constraints 不能为空")

    prob = pulp.LpProblem('SC', pulp.LpMinimize if data.sense=="Minimize" else pulp.LpMaximize)
    vars = {k: pulp.LpVariable(k, lowBound=0) for k in data.objective}
    prob += pulp.lpSum([data.objective[k]*vars[k] for k in vars])

    for c in data.constraints:
        lhs = pulp.lpSum([c.lhs.get(k,0)*vars[k] for k in vars])
        if c.sense == "<=": prob += lhs <= c.rhs
        elif c.sense == ">=": prob += lhs >= c.rhs
        else: prob += lhs == c.rhs

    prob.solve()
    return {
        "status": pulp.LpStatus[prob.status],
        "vars": {v.name: v.value() for v in vars.values()},
        "optimum": pulp.value(prob.objective)
    }