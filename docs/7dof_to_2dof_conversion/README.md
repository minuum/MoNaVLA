# 7dof -> 2dof (vel) Conversion Feasibility

## Issue
-   **Question**: Is it feasible to convert 7DOF (arm) data/model to 2DOF (mobile velocity) with the current dataset size?
-   **Reference**: [7dof->2dof(vel)](https://www.notion.so/7dof-2dof-vel-2b110831b375801d817dc0f75c8525ad?pvs=21)
-   **Status**: Analysis
-   **Findings from `Mobile_VLA_Change_Analysis.md`**:
    -   Proposed "Mobile VLA 4D Action Space": `linear_x`, `linear_y`, `angular_z`, `action_type`.
    -   This effectively maps to the mobile base control.
    -   The feasibility depends on whether the "navigation" intent can be learned from the "manipulation" heavy pre-training or if we have enough mobile-specific data.

## Plan
-   Review `Mobile_VLA_Change_Analysis.md` in detail.
-   Assess the amount of mobile-specific data available.
