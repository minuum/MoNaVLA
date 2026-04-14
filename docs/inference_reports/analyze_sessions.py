import json
import glob
import os
import numpy as np

logs = glob.glob("session_20260305_*.json")
logs.sort()

# Ignore empty or malformed json
results = []
for log in logs:
    with open(log, 'r') as f:
        try:
            data = json.load(f)
            # Extract basic info
            session_id = data.get("session_id", log)
            model_name = data.get("model_name", "unknown")
            instruction = data.get("instruction", "unknown")
            history = data.get("history", [])
            
            # Analyze actions
            actions = [step.get("action", [0,0]) for step in history if "action" in step]
            linear_actions = [a[0] for a in actions]
            angular_actions = [a[1] for a in actions]
            
            if len(actions) > 0:
                avg_linear = sum(linear_actions)/len(linear_actions)
                avg_angular = sum(angular_actions)/len(angular_actions)
            else:
                avg_linear, avg_angular = 0, 0
                
            unique_linear = len(set(linear_actions))
            unique_angular = len(set(angular_actions))
            
            summary = data.get("summary", {})
            total_steps = summary.get("total_steps", len(history))
            avg_latency = summary.get("avg_latency", 0)
            
            results.append({
                "session_id": session_id,
                "model_name": model_name,
                "instruction": instruction,
                "steps": total_steps,
                "avg_latency": avg_latency,
                "avg_action": f"[{avg_linear:.2f}, {avg_angular:.2f}]",
                "unique_linear": unique_linear,
                "unique_angular": unique_angular
            })
            
        except json.JSONDecodeError:
            pass

# Print Report
print("## Session Inference Analysis")
print("| Session ID | Instruction | Steps | Avg Latency | Avg Action (Lin, Ang) | Distinct Linear | Distinct Angular |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for r in results:
    if r['steps'] > 0: # filter out entirely empty ones
        print(f"| {r['session_id']} | {r['instruction']} | {r['steps']} | {r['avg_latency']:.1f}ms | {r['avg_action']} | {r['unique_linear']} | {r['unique_angular']} |")
