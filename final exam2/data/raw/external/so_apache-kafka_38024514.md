# 理解Kafka Topics和Partitions

- 来源: Stack Overflow
- 原始标题: Understanding Kafka Topics and Partitions
- 问题ID: 38024514
- 标签: apache-kafka, kafka-consumer-api, kafka-producer-api
- 得分: 412
- 回答数: 5
- 抓取时间(UTC): 2026-05-18T09:49:15.809318+00:00
- 原始链接: https://stackoverflow.com/questions/38024514/understanding-kafka-topics-and-partitions

## 问题

我开始学习Kafka。在阅读过程中，脑海中浮现出一些问题：当生产者（Producer）发送消息时，它需要指定要发送到哪个主题（Topic），对吗？它会关心分区（Partition）吗？当消费者（Consumer）运行时，它是否需要指定自己的组ID（group id），以便加入一个消费者集群，这个集群关注同一个或多个主题？每个消费者组（Consumer Group）在代理（Broker）上对应一个分区，还是每个消费者对应一个分区？分区是由代理创建的，因此消费者不需要关心？由于这是一个带有每个分区偏移量（Offset）的队列，消费者是否需要指定它想要读取哪些消息？是否需要保存自己的状态？当消息从队列中删除时会发生什么？——例如，消息保留时间为3小时，时间过后，双方（生产者和消费者）如何处理偏移量？

## 最佳回答

这个帖子已有答案，但我从 Kafka 权威指南（Kafka Definitive Guide）中截取了几张图来补充我的观点。在回答问题之前，我们先看看生产者组件的概览：  
生产者生产消息时，会指定想要发送消息的 Topic，对吗？它关心分区吗？  
生产者会根据以下条件决定将消息放置到哪个目标分区：  
- 如果消息中指定了分区 ID，则使用该分区 ID；  
- 如果未指定分区 ID，则根据消息键的哈希值对分区数取模（key % num partitions）；  
- 如果消息中既没有分区 ID 也没有消息键（即只有值），则采用轮询（Round Robin）方式。  

当一个消费者运行时，它会指定自己的 group.id，从而加入一个消费组，该组中的消费者共同消费同一个 Topic 或几个感兴趣的 Topic，对吗？  
除非你使用简单分配 API 并且不需要在 Kafka 中存储偏移量，否则你应该始终配置 group.id。否则该消费者不会属于任何消费组。  
来源（Source）。  

每个消费者组在 Broker 上对应一个分区，还是每个消费者对应一个分区？  
在一个消费者组内，每个分区只由一个消费者处理。可能的情况如下：  
- 如果消费者数量少于 Topic 分区数，则组内某个消费者会被分配多个分区；  
- 如果消费者数量等于 Topic 分区数，则分区与消费者的映射如下图所示：  
- 如果消费者数量多于 Topic 分区数，则分区与消费者的映射如下图所示（消费者 5 效率不高）：  

既然分区是由 Broker 创建的，消费者无需关心分区吗？  
消费者应当了解分区的数量，这在问题 3 中已有讨论。  

由于这是一个带有偏移量的队列，消费者是否需要自行指定要读取哪些消息？是否需要保存自身的状态？  
Kafka（具体来说是 Group Coordinator）通过向内部的 `__consumer_offsets` Topic 生产消息来管理偏移量状态；这种行为也可以通过将 `enable.auto.commit` 设置为 `false` 来改为手动管理。此时，`consumer.commitSync()` 和 `consumer.commitAsync()` 可帮助管理偏移量。  
关于 Group Coordinator 的更多信息：它是 Kafka 服务端集群中选举出的 Broker 之一。消费者与 Group Coordinator 交互以提交偏移量和发起拉取请求。消费者会定期向 Group Coordinator 发送心跳。  

当消息从队列中被删除时会发生什么？例如，保留期为 3 小时，时间过后，双方（生产者和消费者）如何处理偏移量？  
如果任何消费者在保留期之后启动，消息会根据 `auto.offset.reset` 配置进行消费，该配置可以是 `latest`（从最新开始）或 `earliest`（从最早开始）。技术上讲，如果所有消息都已过期且保留期已过，默认行为是 `latest`（开始处理新消息）。
