# How to query MongoDB with &quot;like&quot;

- 来源: Stack Overflow
- 问题ID: 3305561
- 标签: sql, mongodb, mongodb-query, sql-like
- 得分: 1992
- 回答数: 47
- 抓取时间(UTC): 2026-05-18T09:34:27.912228+00:00
- 原始链接: https://stackoverflow.com/questions/3305561/how-to-query-mongodb-with-like

## 问题

I want to query something with SQL's `like` query: ``` `SELECT * FROM users WHERE name LIKE '%m%' ` ``` How can I achieve the same in MongoDB? I can't find an operator for `like` in the documentation .

## 最佳回答

That would have to be: ``` `db.users.find({"name": /.*m.*/}) ` ``` Or, similar: ``` `db.users.find({"name": /m/}) ` ``` You're looking for something that contains "m" somewhere (SQL's '`%`' operator is equivalent to regular expressions' '`.*`'), not something that has "m" anchored to the beginning of the string. Note: MongoDB uses regular expressions (see the documentation) which are more powerful than "LIKE" in SQL. With regular expressions you can create any pattern that you imagine. For more information on regular expressions, refer to Regular expressions (MDN).
