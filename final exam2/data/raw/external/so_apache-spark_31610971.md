# Spark - repartition() 与 coalesce()

- 来源: Stack Overflow
- 原始标题: Spark - repartition() vs coalesce()
- 问题ID: 31610971
- 标签: apache-spark, distributed-computing, rdd
- 得分: 433
- 回答数: 21
- 抓取时间(UTC): 2026-05-18T09:46:55.289647+00:00
- 原始链接: https://stackoverflow.com/questions/31610971/spark-repartition-vs-coalesce

## 问题

根据《Learning Spark》，请记住对数据进行重新分区是一项相当昂贵的操作。Spark 还提供了 `repartition()` 的优化版本 `coalesce()`，它可以避免数据移动，但前提是你正在减少 RDD 的分区数量。我注意到的一个区别是：使用 `repartition()` 可以增加或减少分区数量，而使用 `coalesce()` 只能减少分区数量。如果分区分布在多台机器上，并且运行了 `coalesce()`，它又是如何避免数据移动的呢？

## 最佳回答

这避免了完全 shuffle。如果已知分区数在减少，那么 executor 可以安全地将数据保留在最小数量的分区上，只需将数据从多余的节点移动到保留的节点上。因此，过程大致如下：

``` 
Node 1 = 1,2,3 Node 2 = 4,5,6 Node 3 = 7,8,9 Node 4 = 10,11,12 
```

然后使用 `coalesce` 缩减到 2 个分区：

``` 
Node 1 = 1,2,3 + (10,11,12) Node 3 = 7,8,9 + (4,5,6) 
```

请注意，Node 1 和 Node 3 的原始数据无需移动。
