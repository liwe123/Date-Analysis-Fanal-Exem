# 训练神经网络时的Epoch与Iteration对比

- 来源: Stack Overflow
- 原始标题: Epoch vs Iteration when training neural networks
- 问题ID: 4752626
- 标签: machine-learning, neural-network, deep-learning, artificial-intelligence, terminology
- 得分: 487
- 回答数: 14
- 抓取时间(UTC): 2026-05-18T09:52:47.841763+00:00
- 原始链接: https://stackoverflow.com/questions/4752626/epoch-vs-iteration-when-training-neural-networks

## 问题

在训练多层感知机（multi-layer perceptron）时，epoch 和 iteration 有什么区别？

## 最佳回答

在神经网络术语中：一个 epoch = 对所有训练样本进行一次前向传播和一次反向传播；batch size = 一次前向/反向传播中使用的训练样本数。batch size 越大，所需的内存空间就越多。迭代次数 = 传递的次数，每次传递使用 [batch size] 个样本。需要明确的是：一次传递 = 一次前向传播 + 一次反向传播（我们不将前向传播和反向传播视为两次不同的传递）。例如：如果你有 1000 个训练样本，且 batch size 为 500，那么完成 1 个 epoch 需要 2 次迭代。仅供参考：训练神经网络时在 batch size 与迭代次数之间权衡。术语“batch”存在歧义：有些人用它指代整个训练集，有些人则用它指代一次前向/反向传播中的训练样本数（如我在本回答中所用）。为避免这种歧义并明确 batch 对应一次前向/反向传播中的训练样本数，可以使用术语 mini-batch。
