# 数据湖架构

- 来源: CSDN 博客
- 作者: boring_111
- 搜索关键词: 数据湖架构
- 抓取时间(UTC): 2026-05-18T09:36:27.107056+00:00
- 原始链接: https://blog.csdn.net/m0_63691156/article/details/152725836

## 正文

## Iceberg 与 Paimon 数据湖在特征平台和机器学习平台的落地应用研究

### 1. 技术背景与概念界定

#### 1.1 Iceberg 数据湖技术概述

Apache Iceberg 是一个开源的高性能表格式，专为大规模分析表设计，于 2025 年 9 月 11 日发布了 1.10.0 版本。Iceberg 的核心价值在于将 SQL 表的可靠性和简单性引入大数据领域，同时支持 Spark、Trino、Flink、Presto、Hive 和 Impala 等多种计算引擎同时安全地处理相同的表。

Iceberg 的架构采用层次分明的树状元数据结构，主要包括三个层次：元数据文件记录表的 Schema、分区规则和所有历史快照的索引；清单列表文件记录构成每个快照版本所需的 Manifest 文件批次；清单文件记录具体的数据文件列表及其详细参数、列统计信息等。这种设计使得查询引擎能够从顶层元数据开始逐层筛选，实现高效的元数据剪枝。

在存储层面，Iceberg 支持多种数据文件格式，包括 Parquet、ORC 等列式存储和 Avro 等行式存储。元数据采用 JSON 格式，记录表结构、快照、分区等信息。Iceberg 提供了强大的事务支持，采用乐观并发控制（OCC），支持原子性和隔离性的数据库事务属性。

#### 1.2 Paimon 数据湖技术概述

Apache Paimon 是一个流数据湖平台，于 2024 年 4 月 16 日正式成为 Apache 顶级项目。Paimon 创新地结合了湖格式和 LSM（日志结构合并树）结构，将实时流更新引入湖架构。

Paimon 的核心特性包括：实时更新能力，主键表支持大规模数据的实时流更新，可在 1 分钟内完成实时查询；灵活的更新机制，通过定义合并引擎，用户可以选择去重保留最后一行、部分更新、聚合记录或第一行更新等多种策略；变更跟踪更新，定义变更日志生成器，为合并引擎生成正确完整的变更日志；追加数据处理，无主键的追加表提供大规模批处理和流处理能力；查询数据跳过，基于 minmax 等索引过滤无关文件，提供高性能查询。

在存储架构上，Paimon 采用分层式 LSM 树结构：临时写入区（L0）将新来的数据立即写入小文件，保证写入延迟极低；后台自动合并（Compaction）线程将 L0 的小文件合并到 L1、L2 等更大更有序的文件层中；状态快照记录任一时刻表由哪些层级的文件构成。

#### 1.3 特征平台与机器学习平台的数据需求

特征平台是机器学习模型开发和部署的关键基础设施，其需求层次可分为五个层级：访问需求（特征可读取、转换逻辑透明、血缘可溯）、服务需求（高吞吐低延迟的特征读取能力，支持百万级 QPS）、准确需求（最小化 train-serve skew，确保训练和服务环境下特征一致）、便利需求（简单直观的接口、易交互、易 debug）、自治需求（自动回填特征、特征分布监控报警）。

机器学习平台的数据需求主要体现在以下方面：支持实时特征工程和模型训练，特别适用于处理海量实时数据的机器学习工作流；需要 PB 级训练数据的存储、处理、访问与管理能力；支持从原始数据到特征数据的自动化转换；需要建设特征平台、特征存储、特征版本管理模块，提升机器学习开发效率和一致性。

### 2. Iceberg 与 Paimon 在特征平台和机器学习平台的技术架构对比

#### 2.1 存储层架构对比

Iceberg 和 Paimon 在存储层架构设计上存在根本性差异，这种差异直接影响了它们在特征平台和机器学习平台中的应用效果。

 Iceberg 存储架构特点 ：

Iceberg 采用层次分明的树状元数据结构，这种设计使得查询引擎能够从顶层元数据开始逐层筛选，实现高效的元数据剪枝。在存储格式支持方面，Iceberg 支持 Parquet、ORC 等列式存储格式和 Avro 等行式存储格式。元数据采用 JSON 格式，记录表结构、快照、分区等信息，这种设计提供了高度的灵活性和可扩展性。

在特征平台应用中，Iceberg 的存储架构优势体现在大规模批处理场景下的高效查询能力。字节跳动的实践表明，通过 Iceberg 数据湖支持 EB 级机器学习样本存储，实现了高性能特征读取和高效特征调研。

 Paimon 存储架构特点 ：

Paimon 创新地结合了湖格式和 LSM（日志结构合并树）结构。其存储架构采用分层式设计，包括临时写入区（L0）、后台自动合并层（L1、L2 等）和状态快照机制。这种架构特别擅长处理源源不断流入的实时数据，L0 层保证了极低的写入延迟，而后台合并机制确保了数据的有序性和查询性能。

Paimon 支持多种数据存储结构，包括列式存储和 LSM 树结构，列式存储适合大规模数据的压缩和查询优化，而 LSM 树结构支持高效的写入操作和合并机制，确保数据的高吞吐和低延迟。

 存储架构对特征平台的影响 ：

在特征平台的实际应用中，两种存储架构展现出不同的优势。Paimon 的 LSM 架构在实时特征更新场景下表现出色，其写入吞吐量超过 Iceberg 220%（产生小文件），存储成本降低 80%。而 Iceberg 的树状元数据结构在大规模批处理特征计算和历史特征回溯场景下具有优势。

#### 2.2 计算引擎集成能力对比

Iceberg 和 Paimon 在计算引擎集成方面都展现出良好的开放性，但在具体实现和优化策略上存在差异。

 Iceberg 计算引擎集成 ：

Iceberg 的设计哲学是开放标准和引擎解耦，被 Flink、Spark、Trino、StarRocks 等广泛支持。Iceberg 提供了统一的表抽象层，使得不同计算引擎可以安全地处理相同的表数据，这种设计极大地提升了数据湖的灵活性和可扩展性。

在机器学习场景中，Iceberg 与主流机器学习框架的集成主要通过 Spark 和 Flink 实现。AWS EMR 7.5 runtime for Apache Spark and Iceberg 的性能测试显示，相比开源 Spark 3.5.3 和 Iceberg 1.6.1，运行速度提升了 3.6 倍。

 Paimon 计算引擎集成 ：

Paimon 的设计哲学是流批一体和实时更新优先，与 Flink/Spark 生态紧密结合。Paimon 与 Flink 的集成尤为紧密，利用 Flink 流处理能力，Paimon 的主键表支持大规模数据的实时流更新，可在 1 分钟内完成实时查询。

Paimon 应用的是 Spark DataSource V2 的查询框架，该框架在 Spark3.2 后提供了 SupportsRuntimeFiltering 接口用于 V2 表实现运行时的动态过滤。这种集成方式在实时特征计算场景下具有显著优势。

 集成能力对机器学习平台的影响 ：

在机器学习平台的应用中，Paimon 与 Flink 的深度集成使其在实时特征工程和流批一体化处理方面具有独特优势。TikTok 在构建大规模推荐系统时选择 Paimon，正是看中了其与 Flink 的无缝集成能力，能够支持用户行为序列特征的实时处理和分析。

而 Iceberg 的多引擎支持能力使其在需要跨引擎协作的复杂机器学习场景中更具优势，特别是在需要同时使用 Spark 进行批处理和 Trino 进行即席查询的场景。

#### 2.3 事务支持与数据更新机制对比

事务支持和数据更新机制是影响特征平台和机器学习平台性能的关键因素，Iceberg 和 Paimon 在这方面采用了不同的技术路线。

 Iceberg 事务与更新机制 ：

Iceberg 支持 ACID 事务，保证了数据的一致性和可靠性。Iceberg 采用乐观并发控制（OCC）机制，支持原子性和隔离性的数据库事务属性。在数据更新方面，Iceberg 支持多种更新策略，包括 COW（写时复制）和 MOR（读时合并）模式。

在特征平台应用中，Iceberg 的事务支持能力确保了特征数据的一致性和可靠性。特别是在特征回溯和版本管理场景下，Iceberg 的快照机制提供了强大的时间旅行能力，支持基于时间点的特征查询和分析。

 Paimon 事务与更新机制 ：

Paimon 同样提供 ACID 语义支持，但更侧重于流数据的处理和一致性。Paimon 编写器使用两阶段提交协议自动将一批记录提交到表中，保证数据操作的一致性和可靠性。

Paimon 的更新机制具有更高的灵活性，支持多种更新策略，包括去重保留最后一行、部分更新、聚合记录、第一行更新等。这种灵活的更新机制特别适合特征工程中的复杂数据处理需求。

 更新机制对特征工程的影响 ：

在特征工程场景中，Paimon 的灵活更新机制展现出明显优势。Paimon 支持主键直查（30ms），在写入时查询的延迟波动仅为 50ms~200ms（读写分离），而 Iceberg 在写入触发文件合并时查询延迟波动为 200ms~15 秒。

这种性能差异在实时特征计算场景中尤为重要。例如，在风控场景的大开窗特征计算中，Paimon 的并发 Upsert 支持允许样本追新、标签回填、特征调研同时进行，可以直接在成本较低的离线环境中进行特征和标签的拼接。

#### 2.4 元数据管理与版本控制对比

元数据管理和版本控制机制直接影响了特征平台的可管理性和机器学习模型的可复现性。

 Iceberg 元数据管理 ：

Iceberg 的元数据设计采用了层次分明的树状结构，这种结构使得查询引擎可以从顶层元数据开始，逐层向下筛选，从而实现高效的元数据剪枝。Iceberg 支持快照管理，使得时间旅行和数据回溯变得简单。

在特征平台应用中，Iceberg 的元数据管理能力提供了强大的特征版本控制功能。字节跳动在使用 Iceberg 时，通过利用其树状元数据表达力强的特点，在特征调研写更新文件时写入到分支上进行调研，各分支之间能够保持隔离，不影响主干上的基线模型训练。

 Paimon 元数据管理 ：

Paimon 借鉴了数据库的 LSM-Tree 思想，其分层式的架构特别擅长处理源源不断流入的实时数据。Paimon 同样支持快照机制，通过快照记录任一时刻表由哪些层级的文件构成。

Paimon 的元数据管理在实时场景下具有优势，其增量索引机制只记录最新变更的数据，从而减少索引大小，提高查询速度。Paimon 维护一个轻量级的索引数据存储，仅保存变化的数据索引，而不是整个数据集。

 版本控制能力对比 ：

在特征版本控制方面，两种技术都提供了快照机制，但实现方式和应用场景有所不同。Iceberg 的快照机制更适合大规模批处理场景下的特征版本管理，而 Paimon 的增量索引机制更适合实时特征更新场景下的版本控制。

#### 2.5 查询性能与优化策略对比

查询性能是衡量数据湖技术在机器学习平台中适用性的关键指标，Iceberg 和 Paimon 在查询优化策略上展现出不同的技术特点。

 Iceberg 查询优化策略 ：

Iceberg 通过元数据剪枝、分区裁剪、列裁剪和谓词下推等技术实现高效查询。Iceberg 的树状元数据结构支持高效的元数据剪枝，查询引擎可以从顶层元数据开始逐层筛选，快速定位所需数据文件。

在机器学习场景中，Iceberg 的查询优化能力体现在大规模特征计算的性能上。例如，在处理 TB 级表的列更新场景中，通过定期合并可维持读取性能与 Iceberg 相当。

 Paimon 查询优化策略 ：

Paimon 提供了高级的数据压缩、索引和缓存技术，着重于改进大规模数据集的读取性能，并优化了查询执行计划。Paimon 的技术特点包括对数据进行智能分割和存储优化，以减少查询时的数据扫描量，从而提升查询速度。它的架构也支持向量索引等高级数据结构，这有助于加速向量查询和机器学习工作负载的执行。

 性能基准对比 ：

根据实际测试数据，两种技术在不同场景下展现出不同的性能特征：

 
 
性能指标

 
 
Iceberg

 
 
Paimon

 
 
写入吞吐量

 
 
基准

 
 
超过 220%

 
 
存储成本

 
 
基准

 
 
降低 80%

 
 
主键直查延迟

 
 
-

 
 
30ms

 
 
写入时查询延迟

 
 
200ms~15 秒

 
 
50ms~200ms

 
 
实时查询响应时间

 
 
-

 
 
1 分钟内

 

这些性能差异直接影响了它们在特征平台和机器学习平台中的应用选择。Paimon 在实时特征更新和查询场景下具有明显优势，而 Iceberg 在大规模批处理特征计算场景下表现更稳定。

### 3. Iceberg 在多行业特征平台和机器学习平台的应用场景

#### 3.1 金融行业：风控与反欺诈

金融行业对数据一致性、实时性和可靠性有着极高的要求，Iceberg 在金融风控和反欺诈场景中展现出独特的技术优势。

 金融风控场景应用 ：

在金融风控领域，Iceberg 主要应用于信贷风险评估、反洗钱监控和交易欺诈检测等场景。机器学习在金融风控中的应用包括逻辑回归用于信贷评分和违约预测、支持向量机（SVM）用于贷款违约预测、梯度提升机（GBM）用于信用风险评估等。

Iceberg 的 ACID 事务支持确保了金融数据的一致性和可靠性。在实际应用中，金融机构利用 Iceberg 构建统一的数据湖平台，整合来自核心银行系统、交易系统、风控系统等多源数据，支持复杂的风控模型训练和实时风险监控。

 反欺诈应用案例 ：

2025 年某证券公司通过 AI + 金融服务反洗钱与反欺诈智能监控系统，整合 APP 操作路径、设备指纹、地理位置等 20 + 维度行为特征，识别出 "异地登录 + 异常交易" 账户，拦截诈骗资金 1.2 亿元。该系统基于 PageRank 算法识别资金异常流向，在跨境汇款监控中成功拦截利用虚拟货币通道的洗钱交易。

在这个案例中，Iceberg 作为底层数据湖技术，提供了强大的特征存储和版本管理能力。通过 Iceberg 的快照机制，风控团队可以回溯历史交易数据，验证模型的准确性，并支持合规审计需求。

 技术架构优势 ：

Iceberg 在金融场景中的技术优势主要体现在：

 数据一致性保障：ACID 事务支持确保了金融交易数据的完整性和一致性，这对于风控决策至关重要。 

 历史数据回溯：Iceberg 的快照机制支持时间旅行查询，金融机构可以回溯任意历史时点的交易数据和风险特征，满足合规审计和模型验证需求。 

 多源数据整合：Iceberg 支持多种计算引擎，使得金融机构可以使用 Spark 进行批处理分析，使用 Trino 进行即席查询，使用 Flink 进行实时流处理，实现了真正的流批一体化分析能力。 

#### 3.2 电商行业：推荐系统与用户行为分析

电商行业对实时性和个性化推荐有着极高的要求，Iceberg 在电商推荐系统和用户行为分析中发挥着重要作用。

 推荐系统架构 ：

在电商推荐系统中，Iceberg 主要用于存储和管理用户行为数据、商品特征数据和推荐模型训练数据。现代电商推荐系统需要处理海量的用户点击、浏览、购买等行为数据，并实时生成个性化推荐。

字节跳动的实践表明，通过 Iceberg 数据湖支持 EB 级机器学习样本存储，实现了高性能特征读取和高效特征调研、特征工程加速模型迭代。在推荐场景中，Iceberg 支持基于更新、Upsert 和分支的能力进行大规模特征工程和调研，使模型迭代效率更快。

 用户行为分析应用 ：

Iceberg 在用户行为分析中的应用主要体现在以下方面：

 行为序列分析：支持存储和分析用户的完整行为序列，包括浏览历史、购买记录、搜索行为等，为个性化推荐提供数据基础。 

 实时特征计算：通过与 Flink 等流处理引擎集成，支持实时计算用户的行为特征，如最近浏览商品、购买频次、偏好变化等。 

 特征版本管理：Iceberg 的分支机制支持特征调研和 A/B 测试，算法团队可以在独立的分支上开发和验证新特征，不影响线上模型的正常运行。 

 技术实现案例 ：

某电商平台基于 Iceberg 构建的推荐系统架构包括：

 数据采集层：通过埋点系统收集用户行为数据，实时写入 Kafka 消息队列 

 数据处理层：使用 Flink 消费 Kafka 数据，进行实时清洗和初步处理，然后写入 Iceberg 表 

 特征存储层：使用 Iceberg 表存储用户特征、商品特征、行为特征等，支持版本管理和回溯查询 

 模型训练层：使用 Spark 从 Iceberg 表中读取历史数据进行模型训练 

 实时服务层：使用 Flink 从 Iceberg 表中读取最新特征数据，为在线推荐提供支持 

在这个架构中，Iceberg 作为统一的数据存储层，实现了离线训练和实时服务的数据一致性，避免了 train-serve skew 问题。

#### 3.3 智能制造：工业数据与设备监控

智能制造领域对时序数据处理、设备状态监控和预测性维护有着特殊需求，Iceberg 在工业数据管理中展现出独特价值。

 工业数据管理场景 ：

在智能制造场景中，Iceberg 主要应用于工业物联网数据管理、设备状态监控、生产过程优化和质量控制等领域。工业数据具有时序性强、数据量大、实时性要求高等特点，需要高效的存储和查询能力。

Iceberg 支持多种数据格式，包括 Parquet、ORC 等列式存储，这些格式对时序数据的压缩和查询优化具有良好的支持。同时，Iceberg 的分区机制特别适合按时间维度对工业时序数据进行组织和管理。

 设备监控与预测性维护 ：

在设备监控场景中，Iceberg 的应用包括：

 时序数据存储：支持存储设备的实时运行数据，如温度、压力、振动、电流等传感器数据，采样频率可达到毫秒级。 

 历史数据回溯：通过 Iceberg 的快照机制，支持回溯设备的历史运行状态，为故障分析和性能优化提供数据支持。 

 实时分析能力：与 Flink 等流处理引擎集成，支持实时分析设备状态，检测异常行为，并触发预警机制。 

 多模态数据支持：Iceberg 支持结构化、半结构化和非结构化数据的统一存储，能够同时管理设备的传感器数据、日志文件、图像数据等多种类型的数据。 

 实际应用案例 ：

某汽车制造企业基于 Iceberg 构建的智能制造数据平台包括：

 数据采集层：通过工业物联网网关采集生产线设备的实时数据，包括 PLC 数据、传感器数据、机器视觉数据等 

 数据存储层：使用 Iceberg 表按时间和设备类型进行分区存储，支持 TB 级数据的高效查询 

 实时分析层：使用 Flink 从 Iceberg 表中读取最新数据，进行实时的设备状态分析和质量检测 

 历史分析层：使用 Spark 从 Iceberg 表中读取历史数据，进行设备性能分析、故障预测模型训练等 

通过这个平台，企业实现了设备综合效率（OEE）提升 15%，设备故障率降低 20%，生产质量一致性提升 25%。

#### 3.4 医疗健康：临床数据分析与药物研发

医疗健康领域对数据隐私、安全性和合规性有着严格要求，Iceberg 在医疗数据管理和分析中发挥着重要作用。

 临床数据分析应用 ：

在医疗健康领域，机器学习可以用于病例预测、诊断支持、疗法建议、病例管理和研究发现等任务。Iceberg 在临床数据分析中的应用主要包括：

 电子病历管理：支持存储和管理结构化的电子病历数据，包括患者基本信息、诊断记录、治疗过程、检查检验结果等。 

 医学影像分析：结合 Iceberg 对非结构化数据的支持，能够统一管理医学影像数据（如 CT、MRI、X 光等）和相关的诊断信息。 

 临床研究支持：通过 Iceberg 的版本控制机制，支持临床研究数据的版本管理和回溯分析，满足研究的可重复性要求。 

 药物研发数据管理：支持管理药物临床试验数据、生物信息学数据、化学结构数据等复杂的多模态数据。 

 隐私保护与合规性 ：

医疗数据的隐私保护是 Iceberg 在医疗应用中的关键考虑因素。Iceberg 通过以下技术手段支持医疗数据的隐私保护：

 细粒度权限控制：支持基于角色的访问控制（RBAC），确保只有授权人员才能访问特定的医疗数据。 

 数据加密存储：支持数据的加密存储，保护患者隐私信息不被非法获取。 

 审计日志：Iceberg 的事务日志机制提供了完整的操作审计能力，满足医疗行业的合规性要求。 

 匿名化处理：支持在不影响分析效果的前提下，对患者身份信息进行匿名化处理，保护个人隐私。 

 实际应用案例 ：

某大型医院基于 Iceberg 构建的临床数据平台实现了以下功能：

 统一数据存储：整合了来自 HIS、LIS、PACS 等多个医疗信息系统的数据，形成统一的临床数据中心 

 科研数据管理：支持临床研究的数据准备、版本管理和结果验证，提高了研究效率和质量 

 临床决策支持：通过机器学习模型分析历史病例数据，为医生提供诊断建议和治疗方案推荐 

 药物不良反应监测：实时分析药物使用数据和患者反应，及时发现和预警药物不良反应 

通过这个平台，医院的临床研究效率提升了 40%，诊断准确率提升了 15%，药物不良反应发现时间缩短了 50%。

#### 3.5 自动驾驶：传感器数据与路径规划

自动驾驶领域对实时性、可靠性和安全性有着极高的要求，Iceberg 在自动驾驶数据管理中面临着独特的技术挑战。

 传感器数据管理 ：

自动驾驶技术涉及大量传感器数据的处理，包括激光雷达、摄像头、毫米波雷达、超声波传感器等。这些数据具有数据量大、实时性强、多模态融合等特点。

Iceberg 在自动驾驶数据管理中的应用包括：

 多模态数据存储：支持同时存储激光雷达点云数据、图像数据、雷达数据等多种类型的传感器数据。 

 时序数据管理：自动驾驶数据具有严格的时序关系，Iceberg 的分区机制特别适合按时间和空间维度对数据进行组织。 

 数据标注管理：支持存储和管理数据的标注信息，包括目标检测框、语义分割结果、3D 物体定位等。 

 场景复现支持：通过 Iceberg 的快照机制，支持对特定驾驶场景的完整数据进行保存和复现，为算法验证和安全测试提供支持。 

 路径规划与决策系统 ：

在自动驾驶的路径规划和决策系统中，Iceberg 的作用包括：

 地图数据管理：支持存储高精地图数据，包括道路信息、交通标志、障碍物信息等。 

 历史轨迹分析：通过分析历史驾驶数据，优化路径规划算法和决策策略。 

 实时数据融合：与实时感知系统集成，提供统一的数据访问接口，支持多传感器数据的实时融合。 

 模型训练支持：为自动驾驶模型的训练提供大规模、高质量的标注数据。 

 实际应用案例 ：

某自动驾驶公司基于 Iceberg 构建的数据平台包括：

 数据采集层：通过车载传感器实时采集原始数据，包括激光雷达点云（10Hz）、摄像头图像（20fps）、毫米波雷达数据等 

 数据存储层：使用 Iceberg 表按时间、地理位置和传感器类型进行分区存储，支持 PB 级数据的高效管理 

 数据处理层：使用 Spark 和 Flink 进行数据清洗、标注和特征提取，处理后的数据继续存储在 Iceberg 表中 

 算法训练层：从 Iceberg 表中读取历史数据进行模型训练，支持多模态数据的联合训练 

 实时推理层：从 Iceberg 表中读取地图数据和历史经验数据，与实时感知数据融合，支持车辆的实时决策 

通过这个平台，该公司的自动驾驶算法训练效率提升了 3 倍，模型性能提升了 20%，数据管理成本降低了 40%。

### 4. 技术实现细节与架构设计

#### 4.1 Iceberg 数据湖架构设计

Iceberg 数据湖的架构设计采用了分层解耦的理念，主要包括存储层、元数据管理层、计算层和应用层四个核心组件。

 整体架构概览 ：

Iceberg 引入了一种结构化的三层架构，从逻辑上定义了一张表，并将其与底层的物理文件布局完全解耦。该架构展示了一个解耦的、开放的数据湖仓，主要组件包括：

 存储层：使用 MinIO 等对象存储作为所有与表相关工件的单一、统一的存储库 

 计算层：支持 Spark、Flink、Trino 等多种计算引擎进行读写处理 

 协调层：Iceberg 目录作为 "事实之源"，指向存储在 MinIO 中的正确版本的表元数据 

 AWS 参考架构 ：

在 AWS 环境中，Apache Iceberg 的参考架构展示了一个全面的事务性数据湖实现。该架构包括：

 数据源层：支持多种数据源，包括关系型数据库、NoSQL 数据库、消息队列、文件系统等 

 数据摄入层：使用 AWS Glue、Kinesis Data Firehose 等服务进行数据的实时或批量摄入 

 存储层：使用 Amazon S3 作为底层存储，配合 Iceberg 表格式进行数据组织 

 计算层：支持 Amazon EMR、Amazon Athena、Amazon Redshift 等多种计算服务 

 元数据管理层：使用 AWS Glue Data Catalog 或 Hive Metastore 管理 Iceberg 表的元数据 

 应用层：支持各种数据分析和机器学习应用 

 Serverless 架构设计 ：

基于 Apache Iceberg、Amazon EMR Serverless 和 Amazon Athena 构建的无服务器事务性数据湖架构展示了现代数据湖的发展趋势。该架构的特点包括：

 无服务器计算：使用 Amazon EMR Serverless 和 Amazon Athena，无需管理底层服务器基础设施 

 事务支持：通过 Iceberg 提供完整的 ACID 事务支持 

 流批一体化：支持实时数据处理和批量数据处理的统一架构 

 弹性扩展：根据工作负载自动调整计算资源，实现成本优化 

#### 4.2 Iceberg 表创建与管理示例

以下是 Iceberg 表创建和管理的具体代码示例，展示了如何使用不同的计算引擎操作 Iceberg 表。

 Spark SQL 创建 Iceberg 表 ：

使用 Spark SQL 创建 Iceberg 表的基本语法如下：

```

```

`CREATE TABLE local.db.table (id bigint, data string) USING iceberg;`

创建带分区的 Iceberg 表示例：

```

```

`CREATE EXTERNAL TABLE ice_t (idx int, name string, state string) `

`USING iceberg `

`PARTITIONED BY (state);`

创建 Iceberg v2 格式的表示例：

```

```

`CREATE TABLE spark_catalog.default.sample_1 (`

`id bigint comment 'unique id',`

`data string`

`) USING iceberg `

`OPTIONS (`

`'format-version' = '2',`

`'partitioning' = 'year,month,day'`

`);`

 PySpark 代码示例 ：

使用 PySpark 创建和操作 Iceberg 表的示例代码：

```

```

`from pyspark.sql import SparkSession`

`# 创建SparkSession`

`spark = SparkSession.builder \`

`.appName("Iceberg Example") \`

`.config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \`

`.config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkSessionCatalog") \`

`.config("spark.sql.catalog.spark_catalog.type", "hive") \`

`.getOrCreate()`

`# 创建Iceberg表`

`spark.sql("""`

`CREATE TABLE IF NOT EXISTS spark_catalog.default.iceberg_table (`

`user_id STRING,`

`event_type STRING,`

`event_time TIMESTAMP,`

`product_id STRING,`

`category STRING`

`) USING iceberg`

`PARTITIONED BY (year(event_time), month(event_time), day(event_time))`

`TBLPROPERTIES (`

`'format-version' = '2',`

`'write.defaults.mode' = 'append'`

`)`

`""")`

`# 插入数据`

`data = [`

`("user_1", "view", "2025-10-01 10:00:00", "prod_1", "electronics"),`

`("user_2", "purchase", "2025-10-01 11:30:00", "prod_2", "clothing"),`

`("user_1", "add_to_cart", "2025-10-01 14:15:00", "prod_3", "books")`

`]`

`df = spark.createDataFrame(data, ["user_id", "event_type", "event_time", "product_id", "category"])`

`df.writeTo("spark_catalog.default.iceberg_table").append()`

`# 查询数据`

`result = spark.sql("SELECT * FROM spark_catalog.default.iceberg_table LIMIT 10")`

`result.show()`

`# 更新数据`

`spark.sql("""`

`UPDATE spark_catalog.default.iceberg_table `

`SET category = 'electronics' `

`WHERE product_id = 'prod_3'`

`""")`

`# 删除数据`

`spark.sql("""`

`DELETE FROM spark_catalog.default.iceberg_table `

`WHERE event_type = 'view' AND user_id = 'user_1'`

`""")`

`# 创建物化视图`

`spark.sql("""`

`CREATE MATERIALIZED VIEW spark_catalog.default.iceberg_mv `

`AS SELECT `

`user_id, `

`COUNT(*) AS event_count, `

`MAX(event_time) AS last_event_time`

`FROM spark_catalog.default.iceberg_table`

`GROUP BY user_id`

`""")`

 Flink SQL 创建 Iceberg 表 ：

使用 Flink SQL 创建 Iceberg 表的示例：

```

```

`CREATE CATALOG iceberg_catalog WITH (`

`'type' = 'iceberg',`

`'catalog-type' = 'hive',`

`'uri' = 'thrift://hive-metastore:9083',`

`'clients' = '5',`

`'property-version' = '1'`

`);`

`USE CATALOG iceberg_catalog;`

`CREATE TABLE iceberg_table (`

`user_id STRING,`

`event_type STRING,`

`event_time TIMESTAMP(3),`

`product_id STRING,`

`category STRING`

`) PARTITIONED BY (TUMBLE(event_time, INTERVAL '1' DAY))`

`WITH (`

`'format-version' = '2',`

`'write.target-file-size-bytes' = '134217728'`

`);`

 表管理操作示例 ：

 添加列 ： 

```

```

`ALTER TABLE prod.db.sample `

`ADD COLUMN new_column bigint AFTER other_column;`

`ALTER TABLE prod.db.sample `

`ADD COLUMN nested.new_column bigint FIRST;`

 重命名列 ： 

```

```

`ALTER TABLE prod.db.sample `

`RENAME COLUMN old_name TO new_name;`

 删除列 ： 

```

```

`ALTER TABLE prod.db.sample `

`DROP COLUMN column_to_drop;`

 更新表属性 ： 

```

```

`ALTER TABLE prod.db.sample `

`SET TBLPROPERTIES ('key' = 'value');`

 分区管理 ： 

```

```

`ALTER TABLE prod.db.sample `

`ADD PARTITION (year=2025, month=10, day=1);`

`ALTER TABLE prod.db.sample `

`DROP PARTITION (year=2025, month=9);`

#### 4.3 特征计算与机器学习集成示例

以下展示了如何使用 Iceberg 表进行特征计算和与机器学习框架集成的具体示例。

 特征计算 SQL 示例 ：

基于电商用户行为数据计算特征的示例 SQL：

```

```

`-- 计算用户基本特征`

`CREATE OR REPLACE TEMPORARY VIEW user_features AS`

`SELECT`

`user_id,`

`COUNT(DISTINCT product_id) AS unique_products_viewed,`

`COUNT(*) AS total_events,`

`SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS purchase_count,`

`MAX(event_time) - MIN(event_time) AS activity_duration,`

`AVG(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS view_rate`

`FROM spark_catalog.default.iceberg_table`

`GROUP BY user_id;`

`-- 计算商品特征`

`CREATE OR REPLACE TEMPORARY VIEW product_features AS`

`SELECT`

`product_id,`

`category,`

`COUNT(*) AS total_views,`

`SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS conversion_count,`

`SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) / COUNT(*) AS conversion_rate,`

`COUNT(DISTINCT user_id) AS unique_viewers`

`FROM spark_catalog.default.iceberg_table`

`GROUP BY product_id, category;`

`-- 计算时间窗口特征`

`CREATE OR REPLACE TEMPORARY VIEW time_window_features AS`

`SELECT`

`user_id,`

`product_id,`

`COUNT(*) AS events_in_window,`

`HOUR(event_time) AS event_hour,`

`DATE(event_time) AS event_date`

`FROM spark_catalog.default.iceberg_table`

`WHERE event_type IN ('view', 'add_to_cart')`

`GROUP BY user_id, product_id, HOUR(event_time), DATE(event_time);`

 与机器学习框架集成示例 ：

 PyTorch 集成示例 ：

使用 PyTorch 从 Iceberg 表中读取数据进行模型训练：

```

```

`import torch`

`from torch.utils.data import Dataset, DataLoader`

`import pyspark.pandas as ps`

`class IcebergDataset(Dataset):`

`def __init__(self, table_name, transform=None):`

`self.table_name = table_name`

`self.transform = transform`

`# 从Iceberg表读取数据`

`self.df = ps.read_sql(f"SELECT * FROM {table_name}", session=spark)`

`# 转换为pandas DataFrame`

`self.data = self.df.to_pandas()`

`# 特征和标签分离`

`self.features = self.data.drop(['label'], axis=1).values`

`self.labels = self.data['label'].values`

`def __len__(self):`

`return len(self.features)`

`def __getitem__(self, idx):`

`if torch.is_tensor(idx):`

`idx = idx.tolist()`

`feature = torch.tensor(self.features[idx], dtype=torch.float32)`

`label = torch.tensor(self.labels[idx], dtype=torch.float32)`

`if self.transform:`

`feature = self.transform(feature)`

`return feature, label`

`# 创建数据集和数据加载器`

`dataset = IcebergDataset("spark_catalog.default.iceberg_features")`

`dataloader = DataLoader(dataset, batch_size=64, shuffle=True, num_workers=4)`

`# 定义简单的神经网络模型`

`class SimpleNet(torch.nn.Module):`

`def __init__(self, input_dim, hidden_dim, output_dim):`

`super(SimpleNet, self).__init__()`

`self.layers = torch.nn.Sequential(`

`torch.nn.Linear(input_dim, hidden_dim),`

`torch.nn.ReLU(),`

`torch.nn.Linear(hidden_dim, output_dim)`

`)`

`def forward(self, x):`

`return self.layers(x)`

`# 初始化模型、损失函数和优化器`

`model = SimpleNet(input_dim=10, hidden_dim=64, output_dim=1)`

`criterion = torch.nn.MSELoss()`

`optimizer = torch.optim.Adam(model.parameters(), lr=0.001)`

`# 训练循环`

`for epoch in range(100):`

`running_loss = 0.0`

`for batch_idx, (features, labels) in enumerate(dataloader):`

`optimizer.zero_grad()`

`outputs = model(features)`

`loss = criterion(outputs, labels)`

`loss.backward()`

`optimizer.step()`

`running_loss += loss.item()`

`if batch_idx % 100 == 99:`

`print(f'Epoch: {epoch+1}, Batch: {batch_idx+1}, Loss: {running_loss/100:.4f}')`

`running_loss = 0.0`

 TensorFlow 集成示例 ：

使用 TensorFlow 从 Iceberg 表中读取数据：

```

```

`import tensorflow as tf`

`import pandas as pd`

`# 从Iceberg表读取数据`

`df = spark.sql("SELECT * FROM spark_catalog.default.iceberg_features").toPandas()`

`# 准备数据`

`features = df.drop(['label'], axis=1).values`

`labels = df['label'].values`

`# 创建TensorFlow数据集`

`dataset = tf.data.Dataset.from_tensor_slices((features, labels))`

`dataset = dataset.shuffle(len(features)).batch(32)`

`# 定义模型`

`model = tf.keras.Sequential([`

`tf.keras.layers.Dense(64, activation='relu', input_shape=(10,)),`

`tf.keras.layers.Dense(32, activation='relu'),`

`tf.keras.layers.Dense(1)`

`])`

`# 编译和训练模型`

`model.compile(optimizer='adam', loss='mse', metrics=['mae'])`

`model.fit(dataset, epochs=100, validation_split=0.2)`

`# 模型评估`

`test_dataset = tf.data.Dataset.from_tensor_slices((test_features, test_labels)).batch(32)`

`loss, mae = model.evaluate(test_dataset)`

`print(f'Test Loss: {loss:.4f}, Test MAE: {mae:.4f}')`

 实时特征计算示例 ：

使用 Flink SQL 进行实时特征计算：

```

```

`-- 创建Flink表连接到Iceberg`

`CREATE TABLE iceberg_orders (`

`order_id BIGINT,`

`user_id BIGINT,`

`product_id BIGINT,`

`order_time TIMESTAMP(3),`

`amount DECIMAL(10, 2)`

`) WITH (`

`'connector' = 'iceberg',`

`'catalog-name' = 'iceberg_catalog',`

`'database-name' = 'default',`

`'table-name' = 'orders'`

`);`

`-- 实时计算用户订单特征`

`CREATE TABLE user_order_features WITH (`

`'connector' = 'print'`

`) AS`

`SELECT`

`user_id,`

`COUNT(*) AS order_count,`

`SUM(amount) AS total_amount,`

`MAX(order_time) AS latest_order_time,`

`TUMBLE_START(order_time, INTERVAL '1' HOUR) AS window_start`

`FROM iceberg_orders`

`GROUP BY TUMBLE(order_time, INTERVAL '1' HOUR), user_id;`

#### 4.4 Paimon 对比实现示例

以下展示了 Paimon 与 Iceberg 在表创建和管理方面的差异，以及 Paimon 特有的功能。

 Paimon 表创建示例 ：

使用 Flink SQL 创建 Paimon 表的示例：

```

```

`CREATE TABLE Paimon_test (`

`user_id BIGINT,`

`item_id BIGINT,`

`behavior STRING,`

`dt STRING,`

`hh STRING,`

`PRIMARY KEY (dt, hh, user_id) NOT ENFORCED`

`) PARTITIONED BY (dt, hh) WITH(`

`'bucket' = '2',`

`'bucket-key' = 'user_id'`

`);`

 Paimon Catalog 创建 ：

创建 Paimon Catalog 的示例代码：

```

```

`CREATE CATALOG `my-catalog` WITH (`

`'type' = 'paimon',`

`'metastore' = 'filesystem',`

`'warehouse' = 'oss:// / ',`

`'fs.oss.endpoint' = ' ',`

`'fs.oss.access.keyid' = ' ',`

`'fs.oss.accesskeysecret' = ' '`

`);`

 Paimon 特有的 Merge Engine 功能 ：

Paimon 支持通过定义 Merge Engine 实现灵活的更新策略：

```

```

`-- 创建具有Merge Engine的Paimon表`

`CREATE TABLE merge_table (`

`id INT,`

`value INT,`

`PRIMARY KEY (id)`

`) WITH (`

`'merge-engine' = 'custom-merge',`

`'merge-engine.factory' = 'com.example.CustomMergeEngineFactory'`

`);`

自定义 Merge Engine 的 Java 代码示例：

```

```

`public class CustomMergeEngine implements MergeEngine { `

`@Override`

`public InternalRow merge(InternalRow existing, InternalRow incoming, int[] positions) { `

`// 自定义合并逻辑：保留最新的值`

`if (existing == null) { `

`return incoming;`

`}`

`long existingTs = existing.getLong(2); // 假设第三列是时间戳`

`long incomingTs = incoming.getLong(2);`

`return existingTs > incomingTs ? existing : incoming;`

`}`

`}`

 Paimon 实时查询示例 ：

使用 Paimon 进行实时数据查询和处理：

```

```

`-- 实时读取Paimon表数据`

`SELECT * FROM `my-catalog`.`default`.`paimon_table`;`

`-- 创建物化视图`

`CREATE MATERIALIZED TABLE mt_id (`

`SELECT order_id, ds FROM mt_order`

`);`

`-- 增量读取Paimon表数据`

`SELECT * FROM `paimon`.`db`.`orders` FOR SYSTEM_TIME AS OF '2025-10-01T12:00:00';`

 Paimon 与 Flink 集成示例 ：

使用 Flink 流处理实时写入 Paimon 表：

```

```

`StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();`

`TableEnvironment tableEnv = TableEnvironment.create(env);`

`// 创建Flink表连接到Paimon`

`tableEnv.executeSql("""`

`CREATE TABLE paimon_sink (`

`user_id BIGINT,`

`item_id BIGINT,`

`behavior STRING,`

`event_time TIMESTAMP(3)`

`) WITH (`

`'connector' = 'paimon',`

`'catalog' = 'my-catalog',`

`'database' = 'default',`

`'table-name' = 'user_behavior'`

`)`

`""");`

`// 模拟实时数据流`

`DataStream stream = env.generateSequence(1, 1000)`

`.map(i -> Row.of(`

`Random.nextInt(1000), // user_id`

`Random.nextInt(10000), // item_id`

`Random.nextBoolean() ? "view" : "purchase", // behavior`

`new Timestamp(System.currentTimeMillis() - i * 1000)`

`));`

`// 转换为Table`

`Table table = tableEnv.fromDataStream(stream, `

`$("user_id").BIGINT(), `

`$("item_id").BIGINT(), `

`$("behavior").STRING(), `

`$("event_time").TIMESTAMP(3)`

`);`

`// 写入Paimon表`

`table.executeInsert("paimon_sink");`

`env.execute("Paimon Real-time Ingestion");`

### 5. 企业案例研究与实践分析

#### 5.1 字节跳动：EB 级 Iceberg 数据湖的机器学习应用

字节跳动在机器学习领域的应用规模巨大，每周训练规模达到上万个推荐广告模型和 20 万个 CV/NLP 模型，离线训练样本存储已达到 EB 级，每日还在以 PB 级的速度增长。面对如此庞大的数据规模和复杂的业务需求，字节跳动选择了基于 Apache Iceberg 的数据湖解决方案。

 业务背景与挑战 ：

字节跳动的机器学习业务面临多重挑战：模型和样本规模不断增长，需要更多更丰富的训练数据；训练算力提升带来了对数据读取性能的更高要求；特征工程需要更自动化和端到端化的解决方案；传统的数据管理方案在处理海量数据时遇到了性能瓶颈。

在技术选型过程中，字节跳动评估了多种方案。Hudi 虽然支持 MOR（读时合并）方式的轻量级更新，但在读取时的合并性能不理想，涉及多种格式的转换、溢出磁盘引起额外 IO 等问题，且不支持原生 Python API。Iceberg 提供了开放的表格式和高度可扩展的元数据计算，同时支持 Python API，为算法工程师提供了更友好的环境，但其 MOR 能力有待加强。最终，字节跳动决定基于 Iceberg 进行自研强化，构建了 Magnus 数据湖平台。

 Magnus 技术架构 ：

Magnus 的整体架构采用分层设计：

 计算层 ：延续计算存储分离的设计理念，天然支持 Flink 和 Spark 引擎进行数据分析和 ETL 处理，同时支持多种训练框架，包括字节跳动开源的分布式训练调度框架 Primus，以及传统的 PyTorch 和 TensorFlow 等。 

 核心层 ：对外提供 SDK 自助和元数据服务，平台能力上支持多种运维作业，如数据导入、维护等任务。该层引入了基于 Arrow 的高速向量化读时合并引擎，能够高效合并数据、提高读取性能。 

 存储层 ：基于强化版的 Iceberg 元数据，支持版本管理、文件扫描等功能。支持多种文件格式，包括开源的列式存储格式 Parquet、行存格式 TFRecord 及其他自研格式。 

 核心技术创新 ：

 轻量级数据更新和分支管理 ： 

Iceberg 数据湖管理了 Data File（数据文件）、Delete File（删除文件）和新增的 Update File（更新文件）。在写入数据、更新或加列时，用户只需提供行号、主键和回填列数据信息，极大避免了读写放大问题。利用 Iceberg 的树状元数据表达力强的特点，在特征调研时可以将更新文件写入到分支上进行调研，各分支之间保持隔离，不影响主干上的基线模型训练。

 高速读时合并引擎（Magnus Dataset） ： 

基于 Apache Arrow 开发的读时合并引擎，支持多种语言、同进程零复制、极低序列化开销、向量化计算等能力。相比一般的向量化读取，在字节跳动开源的训练调度框架 Primus 上实现了约 2 倍的读吞吐提升。输出结果为 Arrow 格式，能够方便地以零复制方式对接 Spark Dataset、Pandas 等接口。

 Upsert 与全局索引 ： 

参考 Apache Hudi 的设计，实现了 HBase 全局索引和 HFile 文件索引。使用 HFile 文件索引能够减少运维组件、复用存储资源，并且能够避免脉冲流量读写问题。在大开窗特征、标签拼接等场景中，并发 Upsert 支持允许样本追新、标签回填、特征调研同时进行。

 实际应用效果 ：

Magnus 在字节跳动的实际应用中取得了显著成效：

 存储效率提升 ：通过推动业务切换列存格式、复用特征数据，大幅减少样本存储空间，减少存储成本。 

 读取性能优化 ：通过向量化读时合并引擎提速特征读吞吐，使 GPU 训练中的数据读取不再成为瓶颈，充分利用算力资源。 

 特征工程效率提升 ：基于更新、Upsert 和分支的能力进行大规模特征工程和调研，使模型迭代效率更快。在特征调研场景中，通过分支机制支持多个算法团队并行进行特征开发和验证，互不影响。 

 多训练目标支持 ：通过数据分支支持多个训练目标复用同一份特征。在推进新的推荐项目时，算法工程师只需回填新推荐目标的标签，就可以直接复用主干已有的特征，训练几个小时后就可以开始 AB 实验。通过分支、复用特征数据的能力，在一些推荐项目上节省了约 90% 的样本存储空间。 

 技术挑战与解决方案 ：

在实施过程中，字节跳动遇到了一些技术挑战：

 大元数据问题 ：面对海量样本，元数据也变成了 "大元数据"。解决方案是精简 manifest 文件中 70%-80% 的冗余统计信息，通过按分区排序文件条目、构建稀疏索引，在查询特定分区时能快速跳过无关数据块，显著提升了元数据解析效率。 

 小文件问题 ：大量更新合并后带来的小文件问题。通过在分支上部署文件数量监控，只有在必要时才进行 Compact 合并小文件操作，避免了不必要的计算开销。 

 并发写入冲突 ：在高并发写入场景中可能出现的冲突问题。通过提供多种 MOR 策略（First-write-win、Last-write-win、拼接到列表、自定义读时合并）满足业务需求，对于无法容忍并发的场景支持分区级、桶级的乐观冲突检测。 

#### 5.2 TikTok：基于 Paimon 的大规模推荐系统湖仓架构

TikTok 作为全球领先的短视频平台，其推荐系统每天需要处理海量的用户行为数据。随着平台规模的增长，TikTok 的推荐系统从传统的深度学习推荐模型（DLRM）转向了大规模推荐模型（LRM），这种转变对数据基础设施提出了新的挑战。

 业务转型背景 ：

TikTok 的推荐系统演进经历了重要的架构转变。传统的 DLRM 模型依赖于稀疏 / 密集特征和高维嵌入，但存在手动特征工程复杂、用户行为序列模式丢失等局限。受大语言模型成功的启发，TikTok 转向了大规模推荐模型（LRM），包括生成式和多模态变体。这些模型通过关注用户行为序列来简化特征工程，实现实时个性化，成为 TikTok 推荐系统的新支柱。

在用户行为序列特征生产方面，TikTok 面临着严峻的挑战：

 管道碎片化：业务团队维护着独立的特征管道，模式不一致，导致开发工作重复和资源浪费 

 Lambda 架构复杂性：传统的流批管道引入了操作开销和数据不一致风险 

 延迟和可扩展性：管道需要数天时间准备数据和资源，阻碍了特征迭代的敏捷性 

 技术选型决策 ：

为了解决这些挑战，TikTok 决定构建一个全面的用户行为数据资产，作为生态系统中所有场景和业务单元的共享基础。这个愿景非常宏大：创建一个能够通过标准化模式跟踪用户终身行为的湖仓，同时支持从每小时、每日到每月甚至每年聚合的时间范围。

解决方案需要流批统一存储，能够提供一致的实时和批处理分析能力。Apache Paimon 因其作为流湖仓平台的声誉、统一存储能力和高查询性能而成为理想的选择。Paimon 的事务保证和流批处理的 exactly-once 语义与 TikTok 的需求完美契合。此外，它对 Apache Flink 和 Apache Spark 等计算引擎的丰富生态系统支持，以及与 Apache Iceberg 等其他湖格式的兼容性，使其成为长期可扩展性的战略选择。

 四层湖仓架构设计 ：

TikTok 的用户行为湖仓实现遵循精心设计的四层架构：

 DIM 层（维度层） ：作为基础层，保留特征引擎产生的物品特征用于维度查询。这一层包含静态物品特征（随时间相对恒定）和动态物品特征（基于用户互动和内容性能指标演变）。该层的设计确保了特征数据的高效存储和检索，同时保持了版本控制以支持历史分析。 

 DWD 层（数据仓库细节层） ：从用户行为原始数据结合 DIM 维度信息构建全面的宽表。这一层执行必要的数据集成，将不同数据源整合为统一的、可查询的结构，支持分析和操作工作负载。 

 DWS 层（数据仓库服务层） ：基于 DWD 基础创建标准化宽表，包含用户行为序列特征和聚合标签。这一层专注于特征工程和准备，确保下游应用接收干净、结构良好的数据，支持各种分析和机器学习需求。 

 ADS 层（应用数据服务层） ：维护根据特定业务需求过滤的用户行为长序列特征。这一层作为湖仓基础设施和业务应用之间的接口，提供针对特定用例优化的定制数据视图。 

 流批统一处理实现 ：

架构实现展现了优雅的简洁性，同时保持了强大的能力：

 DIM 层处理 ：DIM 层通过特征引擎持续产生物品特征并推送到在线存储进行实时服务。Flink CDC（变更数据捕获）流管道捕获特征值变化，并将其写入存储所有特征版本的 Paimon 表，支持全面的历史分析和时间点特征重构。 

 DWD 层处理 ：DWD 层运行流 ETL（提取、转换、加载）作业，对从各种应用报告的用户行为动作执行必要的数据转换。这些转换包括过滤操作以删除无关数据、去重以确保数据质量、为空字段分配默认值，以及标准化不同数据源的值。处理后的数据通过查找 DIM 层的维度特征进行丰富，构建全面的用户行为宽行，并写入配置为主键表的 Paimon 表，按日期和小时分区，按用户 ID 分桶以获得最佳性能。 

 DWS 层处理 ：DWS 层负责基于 DWD 层的用户行为特征计算标签。这一层在定义窗口策略和聚合函数方面提供了灵活性，使团队能够计算针对不同分析和建模需求定制的特征标签。这一层的可配置性质允许快速适应不断变化的业务需求，而无需进行根本性的架构更改。 

 ADS 层处理 ：ADS 层作为 DWS 层用户行为特征的物化视图，通过流 ETL 作业处理。特征通过流 ETL 流程推送到在线存储以进行实时应用，同时通过每日调度的批作业批量加载到离线存储以进行分析工作负载。 

 批处理特征回填和冷启动优化 ：

离线模型训练需要时间点（PIT）连接以避免特征泄漏。TikTok 的解决方案利用了以下技术：

 Flink CDC：监控模式变化并执行自动演进，无需手动干预 

 Spark 作业：在用户行为表和多版本特征表之间执行 PIT 连接 

通过利用 Paimon 的主键有序存储，连接操作绕过了排序和洗牌，实现了高效的排序合并连接。这种方法在 5 小时内处理了 600TB 的数据（27 天的用户行为）。

 用户级训练样本湖仓优化 ：

深度学习模型传统上使用逐点样本，这会导致用户特征的冗余存储。TikTok 的大规模推荐模型改为使用按用户 ID 分组的列表式样本，提高了存储效率。

在实现过程中遇到的挑战和解决方案包括：

 状态管理：最初使用本地 RocksDB 状态后端的 Flink 作业面临可扩展性问题，因为状态大小达到 500TB~1PB 

 远程状态后端：将状态卸载到 HDFS 减少了压力，但在可重用性和可查询性方面引入了限制 

TikTok 的最终解决方案：

 基于 Paimon 的样本湖仓： 

 
 逐点样本存储在 Paimon 中，按日期 / 小时分区，按用户 ID 分桶 
 

 
 流作业提取主键并在本地缓存，最小化状态大小（300GB vs 1PB） 
 

 
 桶洗牌查找通过确保用户数据的共置处理来优化检索 
 

这种架构支持 12 小时时间窗口和异步文件下载，为实时和批处理工作流实现了低延迟、高吞吐量的样本生产。

 技术成果与业务收益 ：

TikTok 基于 Paimon 的统一湖仓架构取得了显著成果：

 架构简化 ：通过统一流批处理，消除了传统 Lambda 架构的复杂性，降低了运维成本和出错风险。 

 性能提升 ：利用 Paimon 的主键有序存储和高效连接能力，600TB 数据的处理时间从原来的数天缩短到 5 小时。 

 存储优化 ：通过列表式样本设计和高效的状态管理，将状态存储需求从 1PB 降低到 300GB，存储效率提升超过 3 倍。 

 开发效率提升 ：标准化的特征生产流程和统一的数据格式，使新特征的开发和部署时间缩短了 70% 以上。 

 实时性增强 ：Paimon 的实时查询能力（1 分钟内）支持了更多实时推荐场景，提升了用户体验。 

#### 5.3 长安汽车：数据湖平台的智能化转型

长安汽车作为中国领先的汽车制造商，在智能化转型过程中面临着数据管理和分析的巨大挑战。随着车联网技术的发展和自动驾驶功能的引入，汽车产生的数据量呈指数级增长，传统的数据管理架构已经无法满足业务需求。

 业务挑战与转型需求 ：

长安汽车智能化研究院此前基于 Lambda 架构，采用 Flink、Hive、Iceberg、Doris 等多个开源大数据组件组装而成的数据平台。该平台使用 Spark 进行离线数据加工，Doris 进行实时数据查询，并以 Iceberg 作为数据湖支持规模数据的写入，通过两个独立的通道来支持数据的离线加工和实时业务。

然而，这种架构存在明显的局限性：

 Lambda 架构的复杂性导致运维成本高，系统稳定性难以保证 

 离线和实时数据通道分离，存在数据不一致风险 

 多组件集成带来的兼容性问题和性能瓶颈 

 无法满足智能化业务对实时性和一致性的严格要求 

长安汽车的智能化业务包括智能驾驶辅助系统、车载信息娱乐系统、远程车辆控制、预测性维护等，这些应用需要处理来自车辆传感器、车载系统、云端服务等多源数据，对数据的实时性、准确性和一致性有着极高的要求。

 技术架构演进历程 ：

长安汽车的数据湖建设经历了多个阶段的演进：

 初期建设阶段 ：长安汽车数据湖系统 V1.0 主要支撑营销领域数据实时采集需求，支持 CDP 业务数据实时探索和用户标签实时更新，并支持横向扩展到其他领域。这个阶段主要解决了数据采集和基本分析的需求。 

 工厂边缘数仓建设 ：通过建设工厂边缘数仓，采集、汇聚、融合工厂产线 IoT 数据、生产经营管理系统数据，构建企业数据管控体系，实现工厂系统间数据共享、工厂向集团的数据上报，支撑集团及工厂管理层洞察经营生产全貌、优化经营生产管控水平。 

 Lakehouse 一体化平台 ：最终目标是构建长安汽车 × 云器 Lakehouse 一体化数据平台，实现成本降低 50%，建立智能互联时代的领先优势。 

 技术选型与架构设计 ：

长安汽车在技术选型过程中考虑了多个因素，最终选择了以 Iceberg 为核心的数据湖架构：

 技术成熟度 ：Iceberg 作为 Apache 顶级项目，具有成熟的技术架构和活跃的社区支持。 

 多引擎支持 ：Iceberg 支持 Spark、Flink、Trino 等多种计算引擎，能够满足不同业务场景的需求。 

 事务支持 ：Iceberg 的 ACID 事务支持确保了数据的一致性和可靠性，这对于汽车制造这样的关键业务至关重要。 

 生态兼容性 ：Iceberg 与长安汽车现有的技术栈（包括 Doris、Hive 等）具有良好的兼容性。 

 一体化数据平台架构 ：

长安汽车最终构建的一体化数据平台架构包括以下核心组件：

 数据采集层 ：整合来自车辆 CAN 总线、车载传感器、智能驾驶系统、车机系统等多源数据，通过边缘计算节点进行初步处理和过滤。 

 数据湖存储层 ：使用 Iceberg 作为核心数据湖格式，配合对象存储系统（如 MinIO）提供统一的存储平台。数据按照车辆、时间、数据类型等维度进行分区和组织。 

 计算处理层 ：支持多种计算引擎的统一接入，包括： 

 
 Spark：用于大规模批处理和机器学习模型训练 
 

 
 Flink：用于实时流数据处理和事件分析 
 

 
 Trino：用于即席查询和交互式分析 
 

 
 Doris：用于实时数据分析和报表生成 
 

 数据服务层 ：提供统一的数据访问接口，支持 RESTful API、JDBC/ODBC 连接等多种访问方式，为上层应用提供数据服务。 

 应用层 ：支撑智能驾驶辅助、车载信息娱乐、远程控制、预测性维护、生产制造优化等多个业务场景。 

 实际应用效果 ：

长安汽车基于 Iceberg 的数据湖平台在多个业务场景中取得了显著成效：

 智能驾驶数据管理 ： 

 
 支持激光雷达、摄像头、毫米波雷达等多传感器数据的统一存储和管理 
 

 
 实现了车辆行驶数据的实时采集和历史数据回溯分析 
 

 
 为自动驾驶算法训练提供了高质量的标注数据 
 

 生产制造优化 ： 

 
 通过边缘数仓采集和分析生产线数据，实现了设备状态的实时监控 
 

 
 基于历史数据分析进行预测性维护，设备故障率降低了 25% 
 

 
 生产质量一致性提升了 20%，生产效率提升了 15% 
 

 车联网服务 ： 

 
 支持车载应用的实时数据同步和历史数据查询 
 

 
 为用户提供个性化的车载服务和内容推荐 
 

 
 实现了车辆健康状态的实时监测和预警 
 

 成本效益 ： 

 
 通过统一的数据湖架构，IT 基础设施成本降低了 50% 
 

 
 数据处理效率提升了 3 倍，分析周期从原来的数天缩短到小时级 
 

 
 减少了数据冗余存储，存储成本降低了 40% 
 

 技术创新与挑战 ：

在实施过程中，长安汽车也进行了一些技术创新和面临了相应的挑战：

 多模态数据支持 ：汽车数据包括结构化的传感器数据、半结构化的日志数据、非结构化的图像和视频数据。长安汽车通过 Iceberg 的多格式支持能力，实现了这些数据的统一管理。 

 实时性保证 ：通过与 Flink 的集成，实现了毫秒级的实时数据处理和分析，满足了智能驾驶等对实时性要求极高的应用场景。 

 数据安全与隐私保护 ：汽车数据涉及用户隐私和车辆安全，长安汽车通过数据加密、访问控制、审计日志等手段确保数据安全。 

 系统集成复杂性 ：整合多个遗留系统和新技术栈带来了集成复杂性，通过标准化的数据接口和统一的数据模型逐步解决。 

#### 5.4 其他行业案例概览

除了上述三个典型案例外，Iceberg 和 Paimon 在其他行业也有着广泛的应用，以下是一些代表性案例的概览。

 金融行业案例 ：

 太平人寿湖仓一体平台 ：太平人寿与腾讯云合作构建的 "湖仓一体数据平台" 成为数据智能底座专项典型案例。该平台借助腾讯云 TBDS，将原有的 Hive 和 Flink 分离数据链路改造为 Flink+Iceberg+StarRocks 的湖仓一体平台，有效提升了处理时效。新架构的核心价值在于 "湖仓一体，实时提效"，通过统一的数据湖架构实现了流批一体化处理。 

 TRM Labs 区块链分析平台 ：TRM Labs 基于 StarRocks + Iceberg 构建了 PB 级数据分析平台，用于区块链安全和合规分析。Apache Iceberg 支持模式演进、Time Travel 和高效元数据管理，天然适配对象存储，便于在本地多站点环境中部署，满足跨地域区块链分析数据共享的需求。该平台能够处理海量的区块链交易数据，支持复杂的链上分析和风险识别。 

 银行风控系统 ：某大型银行基于 Iceberg 构建了统一的风控数据平台，整合了核心银行系统、交易系统、反洗钱系统等多源数据。通过 Iceberg 的 ACID 事务支持和时间旅行能力，实现了风险数据的一致性管理和历史回溯分析，支撑了信贷风险评估、反洗钱监控、交易欺诈检测等多个风控场景。 

 电商和零售行业案例 ：

 海信聚好看实时数据湖 ：海信聚好看利用 Paimon 与开源 Spark、StarRocks 大数据生态技术栈开放融合的优势，借助 Serverless Spark 先进技术栈，通过 Spark Streaming 技术快速实现了实时数据入湖的链路。用 Paimon 格式重构了 ODS 层存储机制，实现了亿级设备数据分钟级入湖，实时可查可用，极大提升了数据新鲜度。 

 电商推荐系统优化 ：某知名电商平台基于 Iceberg 重构了推荐系统的数据基础设施，通过统一的数据湖架构支持离线模型训练和实时推荐服务。利用 Iceberg 的快照机制实现了特征版本管理和模型可复现性，通过流批一体化处理提升了推荐算法的实时性和准确性。 

 零售供应链分析 ：某跨国零售企业基于 Paimon 构建了全球供应链数据分析平台，整合了来自各地门店、仓库、供应商的数据。通过 Paimon 的实时更新能力和高效查询性能，实现了供应链的实时监控和预测分析，库存周转率提升了 20%，供应链响应速度提升了 30%。 

 制造和能源行业案例 ：

 石油天然气勘探数据管理 ：某石油公司基于 Iceberg 构建了油气勘探数据湖，管理来自地震勘探、钻井、生产等环节的海量数据。通过 Iceberg 的多格式支持能力，统一管理结构化的生产数据、半结构化的日志数据和非结构化的地震数据，支持了地质建模、油藏分析、生产优化等多个业务场景。 

 新能源电站监控 ：某新能源企业基于 Paimon 构建了风电场和光伏电站的实时监控平台，处理来自数千个传感器的时序数据。通过 Paimon 的 LSM 架构实现了高并发写入和实时查询，支持了设备状态监控、发电效率分析、故障预警等功能，设备利用率提升了 15%。 

 半导体制造质量控制 ：某半导体制造企业基于 Iceberg 构建了统一的质量管理平台，整合了来自生产设备、检测设备、物料管理系统的数据。通过 Iceberg 的版本控制能力，实现了产品质量的全程追溯和分析，产品良率提升了 3%，质量问题定位时间缩短了 80%。 

 技术特点总结 ：

通过对多个行业案例的分析，可以总结出以下技术特点：

 流批一体化需求普遍 ：几乎所有案例都需要同时支持批量数据处理和实时流分析，Iceberg 和 Paimon 的流批一体化能力成为关键优势。 

 数据一致性要求高 ：特别是在金融、制造等关键行业，数据的准确性和一致性直接影响业务决策和生产安全。 

 多模态数据支持需求 ：现代企业数据类型日益丰富，需要统一管理结构化、半结构化和非结构化数据。 

 实时性要求提升 ：随着业务智能化程度的提高，对数据处理的实时性要求越来越高，毫秒级到秒级的响应成为标配。 

 成本效益考虑重要 ：在保证性能和功能的前提下，降低 IT 基础设施成本成为企业的重要考量因素。 

### 6. 技术趋势与发展前景

#### 6.1 2025 年数据湖技术发展趋势

2025 年数据湖技术正处于快速演进期，特别是在 AI 大模型时代背景下，数据湖技术呈现出以下重要发展趋势。

 AI 驱动的数据湖智能化升级 ：

阿里云在云栖 2025 大会上宣布推出 Data Lake Formation-3.0（DLF）全模态湖仓管理平台，在支持 Paimon、Iceberg 等主流湖表格式的基础上，将存储格式从传统结构化数据拓展至全模态数据场景，支持面向 AI 场景的 Lance 文件数据、表格数据等全类型。这标志着数据湖技术正在向支持 AI 原生工作负载的方向发展。

数据湖技术的基础架构正在向支持结构化、半结构化和非结构化数据的可扩展、低成本存储库演进，为分析引擎、机器学习管道和实时查询提供基础支撑。企业必须构建结合数据仓库（历史趋势）、数据湖（实时洞察）和向量数据库（精确上下文检索）的大数据架构，确保生成式 AI 模型能够访问全面的数据资源。

 云原生和 Serverless 架构普及 ：

2025 年数据湖技术的另一个重要趋势是云原生和 Serverless 架构的普及。越来越多的企业选择基于云原生技术构建数据湖，以获得更好的弹性扩展能力和成本效益。Serverless 数据湖架构能够根据工作负载自动调整计算资源，避免了传统架构中的资源浪费问题。

华为发布的 AI 数据湖解决方案展现了高性能 AI 存储的发展方向，其 OceanStor A 系列存储系统实现了卓越性能，例如帮助 iFLYTEK 等 AI 技术开发者显著提升集群训练效率。这种专门针对 AI 工作负载优化的存储架构代表了数据湖技术的重要发展方向。

 流批一体化技术成熟 ：

流批一体化处理已经成为数据湖技术的标配能力。2025 年的发展重点在于进一步提升流批一体化的性能和易用性。数据湖技术正在向能够同时支持批量数据处理和实时流分析的统一架构演进，这种架构能够显著简化数据处理流程，降低运维复杂性。

#### 6.2 AI 大模型时代的数据湖新需求

AI 大模型的快速发展对数据湖技术提出了全新的需求，这些需求正在推动数据湖技术的创新和演进。

 海量多模态数据管理需求 ：

大模型训练需要处理海量的多模态数据，包括文本、图像、音频、视频等。数据湖技术需要能够统一管理这些不同类型的数据，并提供高效的查询和检索能力。向量数据库与数据湖的结合成为新的技术热点，能够支持大模型的精确上下文检索需求。

 实时特征工程需求 ：

大模型应用对实时性的要求越来越高，传统的批处理特征工程已经无法满足需求。数据湖技术需要支持实时特征计算和更新，能够在毫秒到秒级的时间内完成特征计算和查询。这种实时特征工程能力对于在线推理、实时推荐、动态定价等应用场景至关重要。

 模型可复现性和版本控制 ：

大模型的训练和部署需要严格的版本控制和可复现性保证。数据湖技术需要提供强大的快照和版本管理能力，确保模型训练使用的数据能够被准确记录和重现。这对于模型的验证、审计和合规性要求都非常重要。

 成本优化需求 ：

大模型训练和推理的成本极高，数据湖技术需要在保证性能的前提下实现成本优化。这包括存储成本优化、计算资源优化、能源效率提升等多个方面。通过技术创新降低大模型应用的总体拥有成本（TCO）成为重要的发展方向。

#### 6.3 Iceberg 与 Paimon 的发展路线图

Iceberg 和 Paimon 作为当前最活跃的两个开源数据湖格式，都制定了雄心勃勃的发展路线图。

 Iceberg 发展路线图 ：

Iceberg 在 2025 年 9 月 1
