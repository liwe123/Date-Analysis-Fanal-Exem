# 事实表（Fact table）与维度表（Dimension table）之间的区别是什么？

- 来源: Stack Overflow
- 原始标题: Difference between Fact table and Dimension table?
- 问题ID: 20036905
- 标签: database, data-warehouse, business-intelligence, fact-table
- 得分: 203
- 回答数: 12
- 抓取时间(UTC): 2026-05-18T09:55:20.954724+00:00
- 原始链接: https://stackoverflow.com/questions/20036905/difference-between-fact-table-and-dimension-table

## 问题

事实表（fact table）与维度表（dimension table）的区别是什么？举一个例子会非常有帮助。

## 最佳回答

在数据仓库建模中，星型模式（star schema）和雪花模式（snowflake schema）由事实表（Fact Table）和维度表（Dimension Table）组成。  
**事实表**：包含所有维度的主键以及相关的事实或度量（可进行计算的属性），例如销售数量、销售额和平均销售额。  
**维度表**：为事实表中记录的所有度量提供描述性信息。与事实表相比，维度表相对较小。常用的维度包括人员、产品、地点和时间。  

图片来源
