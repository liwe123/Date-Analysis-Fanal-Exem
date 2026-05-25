# -*- coding: utf-8 -*-
"""
实验 03 - 无头外科医生
目标：使用 Python 的流式读取方式处理大文件，完成基本日志取证分析

高级工程师: 黎文城
初级开发者 (AI): OpenClaw
"""

import random
import datetime
from pathlib import Path
from collections import deque

# ============================================
# 第 1 步：生成"怪物"日志文件
# ============================================
def generate_log_file(filename="server_chaos.log", lines=500_000):
    """生成大型模拟日志文件

    Args:
        filename: 输出文件名
        lines: 生成行数
    """
    statuses = ["INFO"] * 80 + ["WARNING"] * 15 + ["CRITICAL_FAILURE"] * 5
    ips = [f"192.168.0.{i}" for i in range(1, 20)] + ["10.0.99.99"]  # 10.0.99.99 是"黑客"

    print(f"正在生成 {filename} ({lines:,} 行)...")

    with open(filename, "w", encoding="utf-8") as f:
        for _ in range(lines):
            timestamp = datetime.datetime.now().isoformat()
            status = random.choice(statuses)
            ip = random.choice(ips)
            pid = random.randint(1000, 9999)
            f.write(f"{timestamp} | {status} | Source IP: {ip} | Process ID: {pid}\n")

    print("完成。欢迎来到混乱。\n")


# ============================================
# 第 2 步：检查文件大小（不打开文件）
# ============================================
def check_file_size(filepath):
    """检查文件大小

    Args:
        filepath: 文件路径

    Returns:
        文件大小（字节）
    """
    path = Path(filepath)
    size_bytes = path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_mb / 1024

    print("=" * 50)
    print("文件体检报告")
    print("=" * 50)
    print(f"文件路径：{path.absolute()}")
    print(f"文件大小：{size_bytes:,} 字节")
    print(f"约为：{size_mb:.2f} MB ({size_gb:.4f} GB)")
    print()

    return size_bytes


# ============================================
# 第 3 步：查看前 5 行和后 5 行（流式读取）
# ============================================
def peek_file(filepath, n=5):
    """查看文件开头和结尾，不加载整个文件

    Args:
        filepath: 文件路径
        n: 查看行数
    """
    print("=" * 50)
    print(f"文件预览（前 {n} 行 & 后 {n} 行）")
    print("=" * 50)

    # 看前 n 行
    print(f"\n【前 {n} 行】:")
    with open(filepath, "r", encoding="utf-8") as f:
        for i in range(n):
            line = f.readline().rstrip("\n")
            print(f"  {i+1}: {line}")

    # 看最后 n 行（使用 deque 流式处理）
    print(f"\n【后 {n} 行】:")
    with open(filepath, "r", encoding="utf-8") as f:
        last_n = deque(f, maxlen=n)
        for i, line in enumerate(last_n, 1):
            print(f"  {i}: {line.rstrip(chr(10))}")

    print()


# ============================================
# 第 4 步：统计 CRITICAL_FAILURE 数量（逐行扫描）
# ============================================
def count_critical_failures(filepath):
    """逐行扫描统计严重故障数量

    Args:
        filepath: 文件路径

    Returns:
        统计结果字典
    """
    print("=" * 50)
    print("严重故障统计")
    print("=" * 50)

    critical_count = 0
    warning_count = 0
    info_count = 0
    total_lines = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            if "CRITICAL_FAILURE" in line:
                critical_count += 1
            elif "WARNING" in line:
                warning_count += 1
            elif "INFO" in line:
                info_count += 1

    print(f"总行数：{total_lines:,}")
    print(f"INFO 数量：{info_count:,}")
    print(f"WARNING 数量：{warning_count:,}")
    print(f"CRITICAL_FAILURE 数量：{critical_count:,}")
    print(f"故障率：{critical_count/total_lines*100:.2f}%")
    print()

    return {
        "total": total_lines,
        "info": info_count,
        "warning": warning_count,
        "critical": critical_count
    }


# ============================================
# 第 5 步：统计最频繁的 IP 地址
# ============================================
def analyze_ips(filepath):
    """分析 IP 地址出现频率

    Args:
        filepath: 文件路径

    Returns:
        (排序后的IP列表, 可疑IP出现次数)
    """
    print("=" * 50)
    print("IP 地址分析")
    print("=" * 50)

    ip_counts = {}
    suspicious_ip = "10.0.99.99"
    suspicious_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # 提取 IP 地址
            if "Source IP:" in line:
                parts = line.split("Source IP:")
                if len(parts) > 1:
                    ip = parts[1].split("|")[0].strip()
                    ip_counts[ip] = ip_counts.get(ip, 0) + 1
                    if ip == suspicious_ip:
                        suspicious_count += 1

    # 排序找出最频繁的 IP
    sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)

    print(f"\n【Top 10 最频繁 IP】:")
    for i, (ip, count) in enumerate(sorted_ips[:10], 1):
        marker = " [可疑!]" if ip == suspicious_ip else ""
        print(f"  {i}. {ip}: {count:,} 次{marker}")

    print(f"\n【可疑 IP 分析】:")
    print(f"  IP: {suspicious_ip}")
    print(f"  出现次数：{suspicious_count:,}")
    print(f"  占比：{suspicious_count/sum(ip_counts.values())*100:.2f}%")
    print()

    return sorted_ips, suspicious_count


# ============================================
# 第 6 步：生成分析报告
# ============================================
def generate_report(stats, sorted_ips, suspicious_count, output_file="analysis_report.txt"):
    """将分析结果写入报告文件

    Args:
        stats: 统计结果字典
        sorted_ips: 排序后的IP列表
        suspicious_count: 可疑IP出现次数
        output_file: 输出文件名
    """
    print("=" * 50)
    print("生成分析报告")
    print("=" * 50)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("        服务器日志分析报告 - 无头外科医生实验\n")
        f.write("=" * 60 + "\n\n")

        f.write("【基本信息】\n")
        f.write(f"  总行数：{stats['total']:,}\n")
        f.write(f"  INFO: {stats['info']:,}\n")
        f.write(f"  WARNING: {stats['warning']:,}\n")
        f.write(f"  CRITICAL_FAILURE: {stats['critical']:,}\n")
        f.write(f"  故障率：{stats['critical']/stats['total']*100:.2f}%\n\n")

        f.write("【Top 10 IP 地址】\n")
        for i, (ip, count) in enumerate(sorted_ips[:10], 1):
            marker = " [可疑]" if ip == "10.0.99.99" else ""
            f.write(f"  {i}. {ip}: {count:,} 次{marker}\n")

        f.write(f"\n【安全警告】\n")
        f.write(f"  发现可疑 IP: 10.0.99.99\n")
        f.write(f"  活动次数：{suspicious_count:,}\n")
        f.write(f"  建议：检查该 IP 的所有访问记录\n\n")

        f.write("=" * 60 + "\n")
        f.write("报告生成完成\n")
        f.write("=" * 60 + "\n")

    print(f"报告已保存至：{output_file}")
    print()


# ============================================
# 主程序
# ============================================
if __name__ == "__main__":
    LOG_FILE = "server_chaos.log"
    REPORT_FILE = "analysis_report.txt"

    print("\n" + "=" * 60)
    print("       [实验 03 - 无头外科医生]")
    print("       Python 流式日志分析")
    print("=" * 60 + "\n")

    # 步骤 1：生成日志文件
    generate_log_file(LOG_FILE)

    # 步骤 2：检查文件大小
    check_file_size(LOG_FILE)

    # 步骤 3：预览文件内容
    peek_file(LOG_FILE)

    # 步骤 4：统计故障
    stats = count_critical_failures(LOG_FILE)

    # 步骤 5：分析 IP
    ip_analysis, suspicious_count = analyze_ips(LOG_FILE)

    # 步骤 6：生成报告
    generate_report(stats, ip_analysis, suspicious_count, REPORT_FILE)

    print("=" * 60)
    print("       [实验完成!]")
    print("=" * 60)
    print(f"\n生成的文件:")
    print(f"  - {LOG_FILE} (原始日志)")
    print(f"  - {REPORT_FILE} (分析报告)")
    print()
