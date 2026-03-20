# Antigravity Recovery Report

Date: 2026-03-18

## Scope

This document reconstructs usable work history from `~/.gemini/antigravity`.
The `.pb` files under `conversations/` and `implicit/` are not directly readable session text in practice.
For recovery, the reliable source is the matching `brain/<uuid>/` folder that stores Markdown artifacts, metadata, and media.

## Recovery Rule

For each conversation UUID:

1. Use `~/.gemini/antigravity/conversations/<uuid>.pb` only as the session index.
2. Recover content from `~/.gemini/antigravity/brain/<uuid>/`.
3. Prioritize these files when present:
   - `task.md`
   - `implementation_plan.md`
   - `walkthrough.md`
   - `PROJECT_STRATEGY.md`
   - `vla_problem_analysis_professor.md`
   - `directory_audit_20260301.md`
   - `REORGANIZATION_SUMMARY.md`
   - `disk_usage_analysis.md`

## Inventory

- `conversations/*.pb`: 66
- `implicit/*.pb`: 38
- `brain/*` directories: 69

## Recovered Sessions

### 2026-03-15

- UUID: `2db62ac0-6d0d-4022-988d-516c1bd4fdac`
- Source:
  - `~/.gemini/antigravity/conversations/2db62ac0-6d0d-4022-988d-516c1bd4fdac.pb`
  - `~/.gemini/antigravity/brain/2db62ac0-6d0d-4022-988d-516c1bd4fdac/disk_usage_analysis.md`
- Recovered topic:
  - MoNaVLA disk usage audit
  - urgent cleanup targets for `third_party/RoboVLMs/runs` and `runs/v4_nav`
  - recommendation to restrict checkpoint retention for V4
- Current repo relation:
  - Analysis artifact exists only in Antigravity recovery source
  - no matching recovery document was found in this repo
- Status: not reflected in repo docs

### 2026-03-13

- UUID: `a661c611-b645-4de2-ad9f-f89a0b55f62f`
- Source:
  - `~/.gemini/antigravity/conversations/a661c611-b645-4de2-ad9f-f89a0b55f62f.pb`
  - `~/.gemini/antigravity/brain/a661c611-b645-4de2-ad9f-f89a0b55f62f/task.md`
  - `~/.gemini/antigravity/brain/a661c611-b645-4de2-ad9f-f89a0b55f62f/implementation_plan.md`
  - `~/.gemini/antigravity/brain/a661c611-b645-4de2-ad9f-f89a0b55f62f/walkthrough.md`
- Recovered topic:
  - VLA MCP integration execution plan
  - branch role split between `vla-driving` and `inference-integration`
  - Jetson MCP server and learning server MCP client design
  - 2DoF override and instruction update path
- Current repo relation:
  - reflected in 2026-03-09 git commits around MCP integration
  - reflected in docs and branch-role reasoning later summarized in repo history
- Status: mostly reflected, Antigravity version keeps the clearest branch-role explanation

### 2026-03-06

- UUID: `ffe4d198-ea35-40c0-b3a7-09ee837d7036`
- Source:
  - `~/.gemini/antigravity/conversations/ffe4d198-ea35-40c0-b3a7-09ee837d7036.pb`
  - `~/.gemini/antigravity/brain/ffe4d198-ea35-40c0-b3a7-09ee837d7036/task.md`
  - `~/.gemini/antigravity/brain/ffe4d198-ea35-40c0-b3a7-09ee837d7036/implementation_plan.md`
- Recovered topic:
  - timing memorization diagnosis
  - dataset v3 redesign to break frame-number memorization
  - close/far/offset/no-obstacle variants
  - recommendation to prefer diversity over raw episode count
- Current repo relation:
  - strongly reflected in:
    - `docs/dataset_analysis_basket_v2_20260306.md`
    - `docs/training_plan_dataset_v3_20260306.md`
    - `docs/research_progress_report_20260306.md`
- Status: reflected in repo

### 2026-03-06

- UUID: `5842cf4d-40a4-45aa-8443-0a1b79440638`
- Source:
  - `~/.gemini/antigravity/conversations/5842cf4d-40a4-45aa-8443-0a1b79440638.pb`
  - `~/.gemini/antigravity/brain/5842cf4d-40a4-45aa-8443-0a1b79440638/PROJECT_STRATEGY.md`
  - `~/.gemini/antigravity/brain/5842cf4d-40a4-45aa-8443-0a1b79440638/vla_problem_analysis_professor.md`
- Recovered topic:
  - overall project strategy
  - professor-facing diagnosis of RoboVLMs assumptions and V3 failure modes
  - recommendation to isolate custom code in `robovlm_nav/` and keep `third_party/RoboVLMs` clean
- Current repo relation:
  - strategy direction is reflected
  - custom code isolation is reflected by later migration into `robovlm_nav/`
  - the professor-style diagnostic memo itself appears to remain only in Antigravity recovery source
- Status: partially reflected

### 2026-03-02

- UUID: `accd1c60-4566-4ff1-9056-f4ec90296219`
- Source:
  - `~/.gemini/antigravity/conversations/accd1c60-4566-4ff1-9056-f4ec90296219.pb`
  - `~/.gemini/antigravity/brain/accd1c60-4566-4ff1-9056-f4ec90296219/directory_audit_20260301.md`
  - `~/.gemini/antigravity/brain/accd1c60-4566-4ff1-9056-f4ec90296219/REORGANIZATION_SUMMARY.md`
- Recovered topic:
  - canonical vs legacy directory audit
  - recommendation that `third_party/RoboVLMs` is canonical
  - recommendation to delete legacy `RoboVLMs/` and `RoboVLMs_upstream_backup/`
  - reorganization guidance for MCP tooling and analysis scripts
- Current repo relation:
  - partially reflected by later cleanup and migration work
  - exact audit memo is not preserved in current repo docs
- Status: partially reflected

## Other Recoverable Sessions Worth Inspecting

These are older but still contain directly readable source material:

- `4052610b-28d9-4f37-ab61-a0f34e5fbef6`
  - hierarchical VLM + MPC + MCP plan
- `b91ff0ca-0bba-4d8b-a8cf-f111e30bb13e`
  - Korean vs English instruction mismatch fix
- `bba23562-8187-4f86-85de-0f6057205b55`
  - RoboVLMs transfer-learning and instruction-grounding analysis
- `d7c5776d-e3a9-4088-a4d3-b3fcd77b2771`
  - action chunking comparison against RoboVLMs defaults

## Practical Conclusion

For actual recovery work, the recommended order is:

1. Recover Antigravity-only artifacts not present in the repo.
   - `disk_usage_analysis.md`
   - `vla_problem_analysis_professor.md`
   - `directory_audit_20260301.md`
   - `REORGANIZATION_SUMMARY.md`
2. Keep already-reflected sessions as references only.
   - MCP integration plan
   - dataset v3 redesign and timing-memorization analysis
3. Treat `.pb` files as opaque indices, not as the primary recovery format.

## Commands Used

```bash
find ~/.gemini/antigravity/conversations -type f -name '*.pb'
find ~/.gemini/antigravity/brain -maxdepth 2 -type f
rg -n "MoNaVLA|vla-driving|inference-integration|MCP|dataset v3|RoboVLMs" ~/.gemini/antigravity/brain/*/*.md
```
