# main.py
from fastapi import FastAPI
from pydantic import BaseModel
import pulp, json, uvicorn

app = FastAPI(title="lp-solver")

class Data(BaseModel):
    objective: dict
    constraints: list[dict]
    sense: str = "Minimize"

@app.post("/solve")
def solve(data: Data):
    prob = pulp.LpProblem('SC', pulp.LpMinimize if data.sense=="Minimize" else pulp.LpMaximize)
    vars = {k: pulp.LpVariable(k, lowBound=0) for k in data.objective}
    prob += pulp.lpSum([data.objective[k]*vars[k] for k in vars])
    for c in data.constraints:
        lhs = pulp.lpSum([c['lhs'][k]*vars[k] for k in c['lhs']])
        if c['sense'] == "<=": prob += lhs <= c['rhs']
        elif c['sense'] == ">=": prob += lhs >= c['rhs']
        else: prob += lhs == c['rhs']
    prob.solve()
    return {"status": pulp.LpStatus[prob.status],
            "vars": {v.name: v.value() for v in vars.values()},
            "optimum": pulp.value(prob.objective)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)