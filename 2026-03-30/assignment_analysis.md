# Assignment 05 - Optimized Version Notes

## Files
- Main submission notebook: `05_optimized.ipynb`

## Optimization summary
1. Switched price simulation to geometric random walk so price stays positive.
2. Used compact dtypes for signals (`int8`) to reduce memory.
3. Replaced separate `fillna(0)` steps with `shift(..., fill_value=0)` where appropriate.
4. Simplified SMA and method-chaining sections (removed unnecessary `pd.Series(...)` wrapping).
5. Kept strict vectorized strategy computation (no loop in strategy blocks).

## Runtime snapshots
### Loop baseline
```text
???????????
CPU times: total: 93.8 ms
Wall time: 260 ms
```

### Vectorized version
```text
????????????
CPU times: total: 15.6 ms
Wall time: 27.6 ms
```

### Equality check
```text
循环版和向量化版结果是否一致： True
```

### Final portfolio output
```text
?????????9.07 | ROI: -90.93%
???????48.64 | ROI: -51.36%
????????
```

## Compliance check
- Includes loop baseline as control group.
- Main strategy computations are vectorized.
- Includes shifted signal to avoid look-ahead bias.
- Includes cumulative equity curves and required plots.
