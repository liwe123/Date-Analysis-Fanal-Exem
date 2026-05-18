# 数据库（Database）和数据仓库（Data Warehouse）之间的主要区别是什么？

- 来源: Stack Overflow
- 原始标题: What is the difference between a database and a data warehouse?
- 问题ID: 3419353
- 标签: database, data-warehouse
- 得分: 172
- 回答数: 13
- 抓取时间(UTC): 2026-05-18T09:55:29.026379+00:00
- 原始链接: https://stackoverflow.com/questions/3419353/what-is-the-difference-between-a-database-and-a-data-warehouse

## 问题

数据库和数据仓库有什么区别？它们不是同一个东西吗？或者至少是用同一个东西（即 Oracle RDBMS）编写的吧？

## 最佳回答

欲了解更多信息，请参见此处。来自此前链接：  
**数据库** 用于在线事务处理（OLTP），但也可用于其他目的，如数据仓库。它记录用户的历史数据。表和连接较为复杂，因为它们是规范化的（针对关系型数据库管理系统（RDMS））。这样做是为了减少冗余数据并节省存储空间。实体-关系建模技术用于RDMS数据库设计。针对写操作进行优化。分析查询的性能较低。  
**数据仓库** 用于在线分析处理（OLAP）。它读取用户的历史数据以供业务决策使用。表和连接较为简单，因为它们是反规范化的。这样做是为了减少分析查询的响应时间。数据建模技术用于数据仓库设计。针对读操作进行优化。分析查询性能高。通常是一个数据库。同样重要的是要注意，数据仓库可以源自零个到多个数据库。
