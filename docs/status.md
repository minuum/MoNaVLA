# Project Status Report

## Summary
This document tracks the status of the Todo items as of November 27, 2025.

## Todo List Status

| Item | Sub-item | Status | Notes |
| :--- | :--- | :--- | :--- |
| **RoboVLMs Validation** | Context Vector | **In Progress** | Identified `action_hs` as the target. Plan to use forward hook. |
| | Model Hooking | **Done** | Analyzed `base_backbone.py`. Hooking `act_head` is the best approach. |
| | Output Analysis | **Todo** | Pending script execution. |
| | Sampling Test | **Todo** | Need to define sampling strategy. |
| **Mobile-VLA** | Box Learning | **Researching** | Concern about model learning "box" object instead of navigation task. |
| | Data Augmentation | **Researching** | Investigating simulation and perturbation methods. |
| **Research Feasibility** | 7dof -> 2dof | **Analysis** | Feasible via "Mobile VLA 4D Action Space". Requires data layer changes. |
| | Mobile vs Manipulator | **Researching** | Transferring "Sequential Task" concepts to "Navigation Scenarios". |
| **Inference** | Scenario Definition | **Defining** | Input: Image+Instr+Scenario -> Output: Movement+ActionType. |

## Detailed Documentation
- [RoboVLMs Validation](RoboVLMs_validation/README.md)
- [Mobile-VLA](Mobile-VLA/README.md)
- [7dof -> 2dof Conversion](7dof_to_2dof_conversion/README.md)
- [Mobile vs Manipulator Research](Mobile_vs_Manipulator_Research/README.md)
- [Inference Scenario](Inference_Scenario/README.md)
