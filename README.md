# Emulator

## Use
 
 Just run 
 
 > python3 emulator.py
 
 Then you can get some output in the path "output/".
 
 - emulator.log
 - emulator-analysis.jpg

## Config

### block.txt

- 格式

> 单次发送包数量
> 
> 优先级(0-2), 包大小(B), 存活时间(ms)
> 
> ……
> 

- 示例
> 30
> 
> 0,200000,200
> 
> 1,200000,200
> 
> 2,200000,200


### trace.txt

- 格式

> 时刻(ms), 上传速率(MBps), 丢包率(%)
> 
> ……
> 

- 示例
> 0,10,0
> 
> 5,15,0
>
> 10,20,0

## Todo

- [ ] 不同时刻插入新block
- [ ] 多径（每个节点维护待发送队列，bfs处理网络）
- [ ] a,b,c队列的插入方式
- [ ] 往返包设计，RTT
- [ ] 实现tc、iperf之类的工具
- [ ] 交换机

### 链路

- 最大下载和上传速率
- 下载和上传BER
- 下载和上传的传播延时
- mtu，拆包组包

### log

- 目的（源）IP地址、端口
- 协议
- 数据包大小
- 多径的话需要有各个链路的信息


# Emulator version 2.0 (deployment... ...)

## Link

#### Variable

#### Function

## Node

### Host

#### Variable

- packege queue
- link rate and surround host or router 
- host information (time, bandwith, lossrate)

#### Function

- run_stop

### Router (base=Host)

#### Variable

#### Function

- nat_transfer
- nat_retransfer


## Emulator

#### Variable


### Function

- create_network
- get_topo_list

get the execute order of node according to network architecture 
and blocks information in node

- run_stop (stop_time=-1)

only run emulator for "stop_time" ms.
It will run consistently if "stop_time" equal -1.

- adjust_nodes

push blocks in the node to next node

- log block
- analysis



