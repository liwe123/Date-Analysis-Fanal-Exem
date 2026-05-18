# 如何从Hive访问HBase表，以及反之亦然？

- 来源: Stack Overflow
- 原始标题: How do I access HBase table in Hive &amp; vice-versa?
- 问题ID: 30127088
- 标签: hive, hbase, sqoop, apache-hive
- 得分: 11
- 回答数: 2
- 抓取时间(UTC): 2026-05-18T09:50:36.092390+00:00
- 原始链接: https://stackoverflow.com/questions/30127088/how-do-i-access-hbase-table-in-hive-vice-versa

## 问题

作为开发者，我通过使用 `sqoop job` 从现有的 MySQL 表导入数据，为项目创建了 HBase 表。问题在于我们的数据分析团队熟悉 MySQL 语法，这意味着他们可以轻松查询 HIVE 表。因此，我需要将 HBase 表暴露在 HIVE 中。但我不想通过重新在 HIVE 中填充数据来重复存储，而且数据重复将来可能引发一致性问题。我能否在不复制数据的情况下，将 HBase 表暴露在 HIVE 中？如果可以，该如何操作？另外，如果我在 HBase 表中执行 `insert/update/delete` 操作，更新后的数据能否无问题地出现在 HIVE 中？有时，我们的数据分析团队会在 HIVE 中创建表并填充数据。我能否将这些 HIVE 表暴露给 HBase？如果可以，如何操作？

## 最佳回答

HBase-Hive 集成：在 Hive 中为 HBase 表创建 `external table`，可以让你在 Hive 中查询 HBase 数据，而无需复制数据。你只需在 HBase 表中更新或删除数据，便可在 Hive 中看到修改后的表。示例：假设你有一个包含 `id`、`name` 和 `email` 列的 HBase 表。以下是 Hive 中的外部表命令示例：
``` 
`CREATE EXTERNAL TABLE hivehbasetable(key INT, id INT, username STRING, password STRING, email STRING) STORED BY 'org.apache.hadoop.hive.hbase.HBaseStorageHandler' WITH SERDEPROPERTIES ("hbase.columns.mapping" = ":key,id:id,name:username,name:password,email:email") TBLPROPERTIES("hbase.table.name" = "hbasetable");`
```
更多关于 Hive-HBase 集成的信息，请参考这里。
