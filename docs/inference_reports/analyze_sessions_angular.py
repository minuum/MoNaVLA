import json
import glob

logs = glob.glob("session_20260305_*.json")
logs.sort()

results = []
for log in logs:
    with open(log, 'r') as f:
        try:
            data = json.load(f)
            session_id = data.get("session_id", log)
            instruction = data.get("instruction", "unknown")
            history = data.get("history", [])
            
            actions = [step.get("action", [0,0]) for step in history if "action" in step]
            linear_actions = [a[0] for a in actions]
            angular_actions = [a[1] for a in actions]
            
            summary = data.get("summary", {})
            total_steps = summary.get("total_steps", len(history))
            avg_latency = summary.get("avg_latency", 0)
            
            # extract distribution of angular actions
            from collections import Counter
            ang_counter = Counter(angular_actions)
            # Format: 'val: count'
            ang_dist = ", ".join([f"{k:.2f}: {v}" for k, v in ang_counter.items()])
            
            results.append({
                "session_id": session_id,
                "instruction": instruction,
                "steps": total_steps,
                "avg_latency": avg_latency,
                "ang_dist": ang_dist
            })
            
        except json.JSONDecodeError:
            pass

print("## Angular Action Distribution per Session")
print("| Session ID | Steps | Avg Latency | Angular Distribution (Value: Count) |")
print("| --- | --- | --- | --- |")
for r in results:
    if r['steps'] > 0:
        print(f"| {r['session_id']} | {r['steps']} | {r['avg_latency']:.1f}ms | {r['ang_dist']} |")
