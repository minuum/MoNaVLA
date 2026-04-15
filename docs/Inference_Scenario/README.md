# Inference Scenario

## Issue
-   **Goal**: Define the inference scenario.
-   **Reference**: [Inference Scenario](https://www.notion.so/2b110831b375805abb5bc5f7ec33e305?pvs=21)
-   **Status**: Defining
-   **Current Proposal (from Analysis)**:
    -   Input: Image + Instruction + Scenario Context (e.g., "1box_vert_left")
    -   Output: Movement (linear_x, linear_y, angular_z) + Action Type.
    -   Process:
        1.  Preprocess Image/Text/Scenario.
        2.  Model Forward.
        3.  Validate Action (Safety check).
        4.  Execute on Robot (ROS2).

## Plan
-   Formalize the scenario definitions (e.g., what exactly are the 8 scenarios?).
-   Document the exact input/output interface.
