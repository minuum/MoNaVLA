# V5-Exp05: Action-Aware Instructions

## 1. Goal
- Add past/future context to instructions to improve temporal consistency.

## 2. Method
- Changed instructions to include transition context.
- Example: "You were turning left, now navigate forward to align."

## 3. Result
- **Finding**: Improved smooth transitions between different action types.
- **Val Loss**: Stable around 1.1 - 1.2 (relative to foundation experiments).
