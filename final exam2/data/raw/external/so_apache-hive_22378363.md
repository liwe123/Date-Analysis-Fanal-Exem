# Hive 中对多列进行 DISTINCT 去重

- 来源: Stack Overflow
- 原始标题: Distinct on Multiple columns in Hive
- 问题ID: 22378363
- 标签: hadoop, hive, apache-hive
- 得分: 13
- 回答数: 1
- 抓取时间(UTC): 2026-05-18T09:50:23.598272+00:00
- 原始链接: https://stackoverflow.com/questions/22378363/distinct-on-multiple-columns-in-hive

## 问题

请问 Hive 是否支持对多列进行 DISTINCT 操作？例如 `SELECT DISTINCT(a, b, c, d) FROM table`。如果不支持，是否有其他方法可以实现类似功能？

## 最佳回答

是的，Hive 支持对多个列进行去重。你可以通过以下方式实现：``` `SELECT distinct col1, col2, col3 from TABLE ` ``` 如果想要选择不重复的行，可以使用 `*` 代替：``` `SELECT DISTINCT * FROM TABLE ` ```
