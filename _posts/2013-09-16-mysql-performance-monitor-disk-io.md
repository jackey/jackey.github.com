---
layout: default
title: MySQL 性能分析--监控系统IO状态
---

### MySQL 性能分析--监控系统IO状态

#### 背景

我经常看到很多博客写了关于iostat 监控IO的事情，不仅列出了数据还分析数据所包含的意义。但是我自己心里始终有些疑问：自己是没有见过高并发的小同学，如何知道在各种高并发情况下IO状态呢, 所以我通过写下这个博客来让自己学会一步一步的模拟一个高并发的场景.

#### 用到的工具
* 监控IO用到的工具
    
    我这里主要用到了iostat.

* MySQL 涉及到磁盘IO的状态变量

* Python 测试脚本

    我这里主要用到了python脚本对数据库重复写数据和读数据操作来观察IO状态变化
    
#### 第一步，建立一个数据库 和 测试表 (数据库就叫test_io， 表叫node, 是来自drupal CMS, 我简化了下)

{% highlight sql %}
create database test_io default charset utf8 collate utf8_general_ci;
CREATE TABLE `node` (
    `nid` int(10) unsigned NOT NULL AUTO_INCREMENT COMMENT 'The primary identifier for a node.',
    `type` varchar(32) NOT NULL DEFAULT '' COMMENT 'The node_type.type of this node.',
    `title` varchar(255) NOT NULL DEFAULT '' COMMENT 'The title of this node, always treated as non-markup plain text.',
    `uid` int(11) NOT NULL DEFAULT '0' COMMENT 'The users.uid that owns this node; initially, this is the user that created it.',
    `status` int(11) NOT NULL DEFAULT '1' COMMENT 'Boolean indicating whether the node is published (visible to non-administrators).',
    `created` int(11) NOT NULL DEFAULT '0' COMMENT 'The Unix timestamp when the node was created.',
    `changed` int(11) NOT NULL DEFAULT '0' COMMENT 'The Unix timestamp when the node was most recently saved.',
    PRIMARY KEY (`nid`),
    KEY `node_changed` (`changed`),
    KEY `node_created` (`created`),
    KEY `node_status_type` (`status`,`type`,`nid`),
    KEY `node_title_type` (`title`,`type`(4)),
    KEY `node_type` (`type`(4)),
    KEY `uid` (`uid`)
) ENGINE=InnoDB AUTO_INCREMENT=30674 DEFAULT CHARSET=utf8 COMMENT='The base table for nodes.
{% endhighlight %}
    
#### 第二步， 创建一个python小脚本, 主要模拟了50个并发。 查询参数和类型在配置文件指定.
[脚本源代码](https://github.com/jackey/MySQLTools "Jackey MySQL Tool")

`usage: ./bin/io_test`
  
#### 开始MySQL测试

    准备工作做好后，我们来发现在不同的并发写情况下 IO的状态值.
    
###### 条件1： 跑5个线程， 1000条插入语句 （模拟10个用户）

运行后，我用iostat监控，命令:
`iostat -dkx 5 10
参数含义:
-d 查询磁盘状态
-k 容量单位是KB
-x 查看扩展数据
5: 每5秒采样一次
10: 总共采样10次`

关于iostat 输出的变量含义，可以参找下这个博客里的，写的还是很详细 [iostat 参数示意](http://blog.csdn.net/wanghai__/article/details/5830375)
    
状态图:
![iostat 状态图](http://i43.tinypic.com/11bj8sk.png)

这里可以看到 %util 在 99%徘徊, 说明磁盘负荷一直很满，然后平均await 44毫秒左右， 说明每个io请求处理等待的时间在44ms左右, 这个值一般在5ms左右为正常，如果大于10ms就很大了。我的这个机器MySQL没有做过太多优化，现在差不多是我的极限了.
我还发现 await 和 w_await 的值几乎是相等的，这也侧面说明了我们现在的IO操作主要在写上面.
    
##### 条件2， 跑1个线程， 1000条插入语句 (模拟2个用户)

状态图:
![iostat 状态图](http://i43.tinypic.com/ddfjps.jpg)
    
这里可以看到 %util 还是在99%左右徘徊。然后 await 有所降低，平均大概在10毫秒左右。我在这里很觉得奇怪，以为减少了并发线程会让%util降低；后面想明白了%util不会随着并发线程的减少而减少， 因为磁盘一次也只能运行有限的请求，就算增加了并发线程也不会让磁盘性能好起来.
    
#### 通过监控IO状态得到的结论:

我发现在线程从5降低到1的过程中 %util和 await 值始终在高水平位，几乎是满载运行，这说明一个硬盘的完成IO请求效率不会随着用户的减少而得到提高；
我并没有在保持线程个数不变，减少插入语句来监控IO, 因为这样子做对磁盘没有意义，只要总查询数没有变化，那么磁盘IO瓶颈依然会在
所以我们需要减少IO次数，来着手来提高MySQL性能；并且很显然，从MySQL数据库角度去看, 如果要提高网站效率，我们必须让每个页面的SQL查询降低到最低（举一个反例，我们有时候利用JAVA的多线程特性，来跑一堆的SQL, 其实这样子不会让IO处理的更快，只会更慢）
    
#### 后续

后面我要用这里用到的结论和工具，通过调节参数来优化MySQL的IO 性能.
    
    

