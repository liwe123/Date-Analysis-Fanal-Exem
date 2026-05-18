# 在TensorFlow中，logits这个词的含义是什么？

- 来源: Stack Overflow
- 原始标题: What is the meaning of the word logits in TensorFlow?
- 问题ID: 41455101
- 标签: tensorflow, machine-learning, neural-network, deep-learning, cross-entropy
- 得分: 470
- 回答数: 10
- 抓取时间(UTC): 2026-05-18T09:53:04.262026+00:00
- 原始链接: https://stackoverflow.com/questions/41455101/what-is-the-meaning-of-the-word-logits-in-tensorflow

## 问题

在以下 TensorFlow 函数中，我们必须馈送最终层人工神经元的激活值。这部分我能理解，但我不明白为什么它被称为 logits？难道那不是一种数学函数吗？  
```  
loss_function = tf.nn.softmax_cross_entropy_with_logits( logits = last_layer, labels = target_output )  
```

## 最佳回答

"Logit" 和 "logits" 是重载术语，可以指代 `logit` 函数、其输出，或 softmax、sigmoid 等基于指数函数的输入。在数学中，`logit` 是一个双射函数，将概率 (`[0, 1]`) 映射到实数集 R (`(-inf, inf)`)：概率 p = 0.5 映射到 logit L = 0。负 logit L < 0 对应概率 p < 0.5，正 logit L > 0 对应概率 p > 0.5。`logit` 函数也是 logistic sigmoid 的反函数，即 `p = sigmoid(logit(p))`。在机器学习中，"logits" 通常表示分类模型生成的原始（未归一化）预测向量，随后会被传入归一化函数。如果模型解决多分类问题，logits 通常成为 softmax 函数的输入。softmax 函数随后会生成一个（归一化后的）概率向量，其中每个可能类别对应一个值。
