"""Opt-in live LLM evaluation runner; no network calls unless explicitly enabled."""
import asyncio
import json
import os
from pathlib import Path


async def main():
    if os.getenv("RUN_LIVE_LLM_EVALS") != "1":
        raise SystemExit("Set RUN_LIVE_LLM_EVALS=1 to run provider-backed evaluations.")
    from langchain.messages import HumanMessage
    from agent import agent

    cases = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        try:
            response = await agent.ainvoke({"messages": [HumanMessage(content=case["prompt"])]})
            messages = response.get("messages", [])
            tool_names = [getattr(message, "name", "") for message in messages if getattr(message, "type", "") == "tool"]
            answer = messages[-1].content if messages else ""
            results.append({"id": case["id"], "status": "completed", "tools_called": tool_names, "answer": str(answer)[:5000]})
        except Exception as exc:
            results.append({"id": case["id"], "status": "error", "error": f"{type(exc).__name__}: {exc}"})
    output = Path(__file__).with_name("results.json")
    output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    for result in results:
        print(f"{result['id']}: {result['status']} | tools={result.get('tools_called', [])}")
    print(f"Results saved to {output}. Review each answer against cases.json; completion alone does not prove factual correctness.")


if __name__ == "__main__":
    asyncio.run(main())
