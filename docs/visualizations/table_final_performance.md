# Final Performance Comparison

|   Rank | Case   | Strategy     |   Chunk |   Val Loss |   Train Loss | Improvement   |
|-------:|:-------|:-------------|--------:|-----------:|-------------:|:--------------|
|      1 | Case 5 | No Chunk     |       1 |   0.000532 |       0.0001 | +98.0%        |
|      2 | Case 8 | No Chunk+Abs |       1 |   0.004    |       5e-05  | +85.2%        |
|      3 | Case 4 | Baseline     |      10 |   0.016    |       0.001  | +40.7%        |
|      4 | Case 1 | Baseline     |      10 |   0.027    |       0.027  | +0.0%         |
|      5 | Case 3 | Aug+Abs      |      10 |   0.05     |       0.044  | -85.2%        |
|      6 | Case 2 | Xavier Init  |      10 |   0.048    |       0.034  | -77.8%        |