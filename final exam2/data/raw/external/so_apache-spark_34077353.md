# 如何在 PySpark 中更改 dataframe 的列名？

- 来源: Stack Overflow
- 原始标题: How to change dataframe column names in PySpark?
- 问题ID: 34077353
- 标签: python, apache-spark, pyspark, apache-spark-sql, rename
- 得分: 351
- 回答数: 25
- 抓取时间(UTC): 2026-05-18T09:47:05.854538+00:00
- 原始链接: https://stackoverflow.com/questions/34077353/how-to-change-dataframe-column-names-in-pyspark

## 问题

我来自 pandas 背景，习惯将 CSV 文件中的数据读入 dataframe，然后使用简单命令更改列名为有用的名称：```df.columns = new_column_name_list```。然而，在通过 sqlContext 创建的 PySpark dataframe 中，同样的方法不起作用。我目前能找到的简便解决方案如下：```df = sqlContext.read.format("com.databricks.spark.csv").options(header='false', inferschema='true', delimiter='\t').load("data.txt") oldSchema = df.schema for i,k in enumerate(oldSchema.fields): k.name = new_column_name_list[i] df = sqlContext.read.format("com.databricks.spark.csv").options(header='false', delimiter='\t').load("data.txt", schema=oldSchema)```这基本上是将变量定义两次，先推断 schema，然后重命名列名，再用更新后的 schema 重新加载 dataframe。有没有更好的方法来实现这一点，就像我们在 pandas 中做的那样？我的 Spark 版本是 1.5.0。

## 最佳回答

有很多方法可以实现：  
**选项1：使用 selectExpr**  
```  
data = sqlContext.createDataFrame([("Alberto", 2), ("Dakota", 2)], ["Name", "askdaosdka"])  
data.show()  
data.printSchema()  
# Output  
#+-------+----------+  
#| Name|askdaosdka|  
#+-------+----------+  
#|Alberto|         2|  
#| Dakota|         2|  
#+-------+----------+  
#root  
# |-- Name: string (nullable = true)  
# |-- askdaosdka: long (nullable = true)  
df = data.selectExpr("Name as name", "askdaosdka as age")  
df.show()  
df.printSchema()  
# Output  
#+-------+---+  
#| name|age|  
#+-------+---+  
#|Alberto|  2|  
#| Dakota|  2|  
#+-------+---+  
#root  
# |-- name: string (nullable = true)  
# |-- age: long (nullable = true)  
```  
**选项2：使用 withColumnRenamed**，注意该方法允许“覆盖”同一列。对于 Python3，将 `xrange` 替换为 `range`。  
```  
from functools import reduce  
oldColumns = data.schema.names  
newColumns = ["name", "age"]  
df = reduce(lambda data, idx: data.withColumnRenamed(oldColumns[idx], newColumns[idx]), xrange(len(oldColumns)), data)  
df.printSchema()  
df.show()  
```  
**选项3：使用 alias**，在 Scala 中也可以使用 as。  
```  
from pyspark.sql.functions import col  
data = data.select(col("Name").alias("name"), col("askdaosdka").alias("age"))  
data.show()  
# Output  
#+-------+---+  
#| name|age|  
#+-------+---+  
#|Alberto|  2|  
#| Dakota|  2|  
#+-------+---+  
```  
**选项4：使用 sqlContext.sql**，让你可以在注册为表的 `DataFrames` 上执行 SQL 查询。  
```  
sqlContext.registerDataFrameAsTable(data, "myTable")  
df2 = sqlContext.sql("SELECT Name AS name, askdaosdka as age from myTable")  
df2.show()  
# Output  
#+-------+---+  
#| name|age|  
#+-------+---+  
#|Alberto|  2|  
#| Dakota|  2|  
#+-------+---+  
```
