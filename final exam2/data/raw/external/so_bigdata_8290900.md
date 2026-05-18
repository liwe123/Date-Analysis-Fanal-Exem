# 按ID删除数百万行的最佳方法

- 来源: Stack Overflow
- 原始标题: Best way to delete millions of rows by ID
- 问题ID: 8290900
- 标签: sql, postgresql, bigdata, sql-delete, postgresql-performance
- 得分: 101
- 回答数: 8
- 抓取时间(UTC): 2026-05-18T09:56:09.913097+00:00
- 原始链接: https://stackoverflow.com/questions/8290900/best-way-to-delete-millions-of-rows-by-id

## 问题

我需要从我的PG数据库中删除约200万行数据。我有一个需要删除的ID列表。然而，无论我尝试哪种方法，都耗时数天。我曾尝试将它们放入一张表，然后每100条分批删除。4天后，这个操作仍在运行，仅删除了297268行（我必须从ID表中选择100个ID，然后删除该列表中对应的记录，再从ID表中删除已选的100个ID）。我还尝试了：``` `DELETE FROM tbl WHERE id IN (select * from ids)` ``` 这也花了很长时间。很难估算具体耗时，因为在完成之前无法查看进度，但这个查询运行了2天后仍在继续。我只是想寻找最有效的方法，从已知要删除的具体ID且数量达数百万的表中删除数据。

## 最佳回答

这完全取决于……假设没有对涉及的表进行并发写入访问，否则您可能需要排他锁定表，或者这条路根本不适合您。删除所有索引（可能除了删除本身所需的索引）。之后重新创建它们。这通常比增量更新索引快得多。检查是否有可以安全删除/临时禁用的触发器。是否有外键引用您的表？它们可以被删除吗？临时删除？根据您的 autovacuum 设置，在操作前运行 `VACUUM ANALYZE` 可能会有所帮助。手册中“填充数据库”相关章节列出的某些要点也可能有用，具体取决于您的设置。

如果您删除表的大部分内容，并且剩余部分适合内存，那么最快、最简单的方法可能是这样：
```
BEGIN; -- typically faster and safer wrapped in a single transaction
SET LOCAL temp_buffers = '1000MB'; -- enough to hold the temp table

CREATE TEMP TABLE tmp AS
SELECT t.* FROM tbl t
LEFT JOIN del_list d USING (id)
WHERE d.id IS NULL; -- copy surviving rows into temporary table
-- ORDER BY ? -- optionally order favorably while being at it

TRUNCATE tbl; -- empty table - truncate is very fast for big tables

INSERT INTO tbl TABLE tmp; -- insert back surviving rows.

COMMIT;
```
这样您就不必重新创建视图、外键或其他依赖对象。并且获得一个干净（已排序）且没有膨胀的表。阅读手册中关于 `temp_buffers` 设置的说明。只要表适合内存，或者至少大部分适合，这个方法就很快。事务包装器可以防止服务器在此操作中间崩溃时丢失数据。之后运行 `VACUUM ANALYZE`。或者（通常在采用 `TRUNCATE` 方式后不需要）运行 `VACUUM FULL ANALYZE` 使其达到最小大小（需要排他锁）。

对于大表，考虑替代方案 `CLUSTER` / `pg_repack` 或类似方法：优化时间戳范围上的 Postgres 查询。

对于小表，简单的 `DELETE` 通常比 `TRUNCATE` 更快：
```
DELETE FROM tbl t USING del_list d WHERE t.id = d.id;
```
阅读手册中 `TRUNCATE` 的注释部分。特别是（正如 Pedro 在他的评论中指出的）：如果表有来自其他表的外键引用，则不能使用 `TRUNCATE`，除非在同一个命令中也截断所有这些表。……此外：`TRUNCATE` 不会触发表上可能存在的任何 `ON DELETE` 触发器。
