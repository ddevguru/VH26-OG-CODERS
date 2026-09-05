from fastapi.testclient import TestClient
from packages.saas.app import app

def test_all_ai_agents_execution():
    client = TestClient(app)
    agents = [
        "hunter",
        "reviewer",
        "root_cause",
        "security",
        "fix_generator",
        "regression",
        "verification",
        "pr_agent",
        "documentation",
        "policy",
    ]
    for agent in agents:
        res = client.post(
            f"/api/v1/ai/agents/{agent}/run",
            json={
                "file_path": "test_module.py",
                "source_code": "f = open('data.txt')\n",
                "line_number": 1,
                "resource_type": "FILE",
                "resource_variable": "f",
            },
        )
        assert res.status_code == 200, f"Agent {agent} failed with {res.status_code}: {res.text}"
        data = res.json()
        assert "agent_name" in data or "status" in data or "overall_status" in data
