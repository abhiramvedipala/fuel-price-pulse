## Validation experiments

Command: `uv run python -m fuelpulse.experiments` (about 5 minutes).

Scored only on the 52 weekly origins before the 104-week test window (2023-10-23 to 2024-10-14). Models refit every 4 origins on rows whose targets were already published. MAE is in dollars per gallon; coverage is the share of validation targets inside the 80% band.

```
validation origins 2023-10-23 to 2024-10-14

VALIDATION MAE by horizon ($/gal) and last-value MAE
h                      1       2       3       4
fs     var                                      
dev52  base       0.0424  0.0678  0.0957  0.1213
       shrink     0.0420  0.0666  0.0963  0.1247
       strongreg     NaN     NaN  0.0965  0.1242
levels base       0.0428  0.0685  0.0962  0.1200
       shrink     0.0423  0.0674  0.0976  0.1262
       strongreg     NaN     NaN  0.0962  0.1228
last value: {1: 0.0495, 2: 0.0803, 3: 0.11, 4: 0.1353}

mean lambda by h:
 h          1     2     3     4
fs                            
dev52   0.95  0.93  0.95  0.98
levels  0.93  0.90  0.87  0.89

VALIDATION coverage % (target 80) and mean half-width, all horizons
                                 cov     hw
fs     shrink W   width                    
dev52  lam    52  per_series  90.465  0.178
                  pooled      89.744  0.168
                  vol_scaled  84.255  0.153
              104 per_series  95.593  0.219
                  pooled      95.112  0.215
                  vol_scaled  81.651  0.148
       none   52  per_series  90.745  0.179
                  pooled      89.984  0.169
                  vol_scaled  84.415  0.155
              104 per_series  95.473  0.218
                  pooled      94.872  0.214
                  vol_scaled  81.571  0.147
levels lam    52  per_series  90.745  0.180
                  pooled      89.383  0.169
                  vol_scaled  84.455  0.154
              104 per_series  96.114  0.229
                  pooled      95.633  0.225
                  vol_scaled  83.053  0.152
       none   52  per_series  90.585  0.181
                  pooled      89.744  0.171
                  vol_scaled  84.575  0.157
              104 per_series  95.713  0.227
                  pooled      95.192  0.223
                  vol_scaled  82.973  0.150
```

Variants: `levels` is the current feature set; `dev52` replaces price and WTI with deviations from their 52-week mean. `shrink` multiplies the predicted change by a lambda fitted on the most recent 52 calibration weeks; `strongreg` uses 4 leaves, 200 minimum rows and 120 trees. Interval widths: `pooled` (one per horizon), `per_series`, `vol_scaled` (errors divided by trailing 13-week volatility); `W` is the calibration window in weeks.
