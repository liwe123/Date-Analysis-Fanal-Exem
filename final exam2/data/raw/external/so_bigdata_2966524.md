# 在 PostgreSQL 中计算并节省空间

- 来源: Stack Overflow
- 原始标题: Calculating and saving space in PostgreSQL
- 问题ID: 2966524
- 标签: postgresql, database-design, storage, bigdata
- 得分: 108
- 回答数: 5
- 抓取时间(UTC): 2026-05-18T09:55:49.639067+00:00
- 原始链接: https://stackoverflow.com/questions/2966524/calculating-and-saving-space-in-postgresql

## 问题

我有一个类似这样的 pg 表：
```
CREATE TABLE t (
    a BIGSERIAL NOT NULL, -- 8 b
    b SMALLINT,           -- 2 b
    c SMALLINT,           -- 2 b
    d REAL,               -- 4 b
    e REAL,               -- 4 b
    f REAL,               -- 4 b
    g INTEGER,            -- 4 b
    h REAL,               -- 4 b
    i REAL,               -- 4 b
    j SMALLINT,           -- 2 b
    k INTEGER,            -- 4 b
    l INTEGER,            -- 4 b
    m REAL,               -- 4 b
    CONSTRAINT a_pkey PRIMARY KEY (a)
);
```
上述字段每行合计 50 字节。根据我的经验，即使没有创建任何用户索引，系统开销还需要额外 40%～50%。因此每行大约 75 字节。该表将包含非常多行，可能高达 1450 亿行，因此表的大小将接近 13～14 TB。请问有什么技巧可以用来压缩此表？我想到以下可能的做法……

将 `real` 值转换为 `integer`。如果它们能存储为 `smallint`，每个字段可节省 2 字节。

将列 b .. m 转换为数组。我不需要在这些列上搜索，但我需要能够一次返回某一列的值。例如，如果需要列 g，我可以这样操作：
```
SELECT a, arr[5] FROM t;
```
使用数组选项是否能节省空间？是否会有性能损失？还有其他想法吗？

## 最佳回答

"列俄罗斯方块" 实际上，你可以做一些优化，但这需要更深入的理解。关键在于对齐填充（alignment padding）。每种数据类型都有特定的对齐要求。通过合理地排序列顺序，你可以最小化列之间的填充所浪费的空间。下面这个（极端的）示例会浪费大量物理磁盘空间：  
```sql
CREATE TABLE t (
  e int2 -- int2 后有 6 字节填充
, a int8
, f int2 -- int2 后有 6 字节填充
, b int8
, g int2 -- int2 后有 6 字节填充
, c int8
, h int2 -- int2 后有 6 字节填充
, d int8
)
```
为了每行节省 24 字节，改用以下方式：  
```sql
CREATE TABLE t (
  a int8
, b int8
, c int8
, d int8
, e int2 -- 4 个 int2 占用 8 字节（MAXALIGN）...
, f int2
, g int2
, h int2 -- ...末尾无填充
)
```
fiddle Old sqlfiddle

经验法则：如果你把 8 字节的列放在前面，然后是 4 字节、2 字节和 1 字节的列放在最后，就不会出错。  
`boolean`、`uuid` (!) 和少数其他类型不需要对齐填充。  
`text`、`varchar`、`jsonb` 和其他 "varlena"（可变长度）类型名义上需要 "int" 对齐（大多数机器上是 4 字节）。但在磁盘存储的 "packed" 格式（不同于 RAM）中，对小尺寸的数据有例外。引用源代码：  
注意，我们还允许在存储 "packed" varlena 时违反名义上的对齐；TOAST 机制负责对大多数代码隐藏这一点。因此，"int" 对齐仅在（可能已压缩的）包含单个前导长度字节的数据超过 127 字节时强制执行。之后 varlena 存储切换为四个前导字节，并需要 "int" 对齐。  

通常，玩 "列俄罗斯方块" 最多每行只能节省几个字节。在大多数情况下，这些都不是必需的。但在数十亿行数据的情况下，这很容易意味着几个 GB 的空间。  
你可以使用函数 `pg_column_size()` 测试实际的列/行大小。某些类型在 RAM 中占用的空间比磁盘上更大（压缩或 "packed" 格式）。当对相同的值（或行值 vs 表行）使用 `pg_column_size()` 测试时，常量（RAM 格式）的结果可能比表列的结果更大。  
最后，某些类型可以被压缩或 "toast"（行外存储），或两者兼有。  
尽可能将 `NOT NULL` 列移到前面，将许多 `NULL` 值的列移到后面。`NULL` 值直接从空位图中获取，因此它们在行中的位置对 `NULL` 值的访问成本没有影响，但会增加一点点计算右侧（行中更靠后）列偏移的成本。  

每个元组（行）的开销：  
- 每行 4 字节用于项标识符——不受上述考虑影响。  
- 至少 24 字节（23 + 填充）用于元组头部。  

手册中关于数据库页面布局的描述：  
有一个固定大小的头部（大多数机器上占用 23 字节），后跟可选的空位图、可选的对象 ID 字段以及用户数据。  
对于头部和用户数据之间的填充，你需要知道服务器上的 `MAXALIGN`——在 64 位操作系统上通常是 8 字节。
