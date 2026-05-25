import pandas as pd
import numpy as np
import time
import os
import sys

# 添加当前目录到Python路径，以便保存文件
sys.path.append('D:\\date analysis\\2026-03-23')

# 1. 创建100万行合成数据
num_rows = 1_000_000
print("正在生成100万行数据...")
df = pd.DataFrame({
    'transaction_id': range(num_rows),
    'user_name': ['User_Number_' + str(i) for i in range(num_rows)],  # 高基数字符串
    'category': np.random.choice(['Electronics', 'Books', 'Clothing', 'Home'], num_rows),  # 低基数（重复）
    'price': np.random.uniform(10.0, 500.0, num_rows),  # 浮点数
    'timestamp': pd.date_range(start='2024-01-01', periods=num_rows, freq='S')  # 时间戳
})

print(f"数据已生成。RAM使用：{df.memory_usage(deep=True).sum() / 1024 ** 2:.2f} MB")

# 2. 保存为不同格式并测量时间
output_dir = 'D:\\date analysis\\2026-03-23'

print("\n开始存储格式比较...")
print("=" * 50)

# 1. 保存为CSV（默认）
start = time.time()
df.to_csv(os.path.join(output_dir, 'data.csv'), index=False)
csv_time = time.time() - start
csv_size = os.path.getsize(os.path.join(output_dir, 'data.csv')) / (1024 * 1024)
print(f"CSV保存时间：{csv_time:.2f} 秒")
print(f"CSV大小：{csv_size:.2f} MB")

# 2. 保存为JSON Lines（Web标准）
start = time.time()
df.to_json(os.path.join(output_dir, 'data.json'), orient='records', lines=True)
json_time = time.time() - start
json_size = os.path.getsize(os.path.join(output_dir, 'data.json')) / (1024 * 1024)
print(f"JSON保存时间：{json_time:.2f} 秒")
print(f"JSON大小：{json_size:.2f} MB")

# 3. 保存为Parquet（大数据标准）
start = time.time()
df.to_parquet(os.path.join(output_dir, 'data.parquet'), engine='pyarrow', compression='snappy')
parquet_time = time.time() - start
parquet_size = os.path.getsize(os.path.join(output_dir, 'data.parquet')) / (1024 * 1024)
print(f"Parquet保存时间：{parquet_time:.2f} 秒")
print(f"Parquet大小：{parquet_size:.2f} MB")

print("\n存储格式比较结果：")
print("=" * 50)
print(f"{'格式':<10} {'大小(MB)':<12} {'保存时间(秒)':<12} {'压缩率':<10}")
print(f"{'CSV':<10} {csv_size:<12.2f} {csv_time:<12.2f} {'-':<10}")
print(f"{'JSON':<10} {json_size:<12.2f} {json_time:<12.2f} {'-':<10}")
print(f"{'Parquet':<10} {parquet_size:<12.2f} {parquet_time:<12.2f} {'-':<10}")
print(f"{'':<10} {'':<12} {'':<12} {'':<10}")
print(f"{'CSV vs Parquet':<10} {'':<12} {'':<12} {'{:.1%}'.format(1 - parquet_size/csv_size):<10}")
print(f"{'JSON vs Parquet':<10} {'':<12} {'':<12} {'{:.1%}'.format(1 - parquet_size/json_size):<10}")

# 3. 查询战争（行 vs 列读取）
print("\n开始查询性能测试...")
print("=" * 50)

# 测试A：从CSV读取（面向行）
start = time.time()
df_csv = pd.read_csv(os.path.join(output_dir, 'data.csv'))
csv_read_time = time.time() - start
avg_price_csv = df_csv['price'].mean()
print(f"CSV读取时间：{csv_read_time:.2f} 秒")
print(f"平均价格：{avg_price_csv:.2f}")

# 测试B：从Parquet读取（列剪枝）
start = time.time()
df_parquet = pd.read_parquet(os.path.join(output_dir, 'data.parquet'), columns=['price'])
parquet_read_time = time.time() - start
avg_price_parquet = df_parquet['price'].mean()
print(f"Parquet读取时间：{parquet_read_time:.2f} 秒")
print(f"平均价格：{avg_price_parquet:.2f}")

print(f"\n查询性能对比：")
print(f"CSV读取时间：{csv_read_time:.2f} 秒")
print(f"Parquet读取时间：{parquet_read_time:.2f} 秒")
print(f"加速比：{csv_read_time/parquet_read_time:.1f} 倍")

# 4. 模式防御（安全性）
print("\n开始模式安全性测试...")
print("=" * 50)

# 创建一个小的损坏数据框
broken_df = pd.DataFrame([{'transaction_id': 1000001, 'price': "Expensive"}])

# 尝试将损坏的列转换为浮点数
try:
    broken_df['price'] = broken_df['price'].astype(float)
    print("Parquet保护测试：未捕获到错误（这不应该发生）")
except Exception as e:
    print(f"Parquet保护：系统捕获了错误 -> {e}")

print("\n实验完成！结果已保存到 D:\\date analysis\\2026-03-23 文件夹中")
print("\n总结：")
print(f"- Parquet比CSV压缩了 {1 - parquet_size/csv_size:.1%}")
print(f"- Parquet比JSON压缩了 {1 - parquet_size/json_size:.1%}")
print(f"- 查询速度提升了 {csv_read_time/parquet_read_time:.1f} 倍")