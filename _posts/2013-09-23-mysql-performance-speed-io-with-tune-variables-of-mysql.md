---
layout: default
title: MySQL 性能分析--对MySQL写数据IO参数调优
description: 在MySQL高并发情况下，常常会遇到写的瓶颈，这篇博客主要集中优化MySQL写数据性能.
tags: [MySQL, MySQL高性能, 高并发优化]
---

## MySQL 写数据 IO参数汇总

### MySQL 参数

* autocomit

    如果设置是1，则自动提交事务，所做的修改将是直接影响到表；如果是0，则需要手动commit自己的事务。 [详细](http://dev.mysql.com/doc/refman/5.0/en/commit.html)

* big_tables
    
    在临时表创建时候，如果设置为1，则在磁盘上创建临时表而不是内存；不要设置这个值，默认是0；MySQL只有在需要的时候才会创建磁盘临时表；

* binlog_cache_size
    
    缓存事务语句的cache大小,默认是32768；这个设置需要权衡，如果太大，不仅浪费内存，而且在宕机情况下，还可能造成事务数据丢失的风险；并且这个cache也不是全局的，而是以session为单位共享的；所以太大就更容易浪费内存；

* binlog_stmt_cache_size

    这个和binlog_cache_size类似，不过是缓存一个事务中非支持事务表的语句.

* bulk_insert_buffer_size

    在MyISAM存储引擎下，类似 INSERT ... SELECT , INSERT ... VALUES(), VALUES()... 和 LOAD DATA INFILE 的语句，会创建tree-like（我翻译为树形）的cache；这个cache size 限制了一个线程允许的最大tree-like cache 大小； MyISAM在批量插入数据情况下，应该要优先考虑这个参数来优化.

* data_dir

    数据文件所在目录；在多磁盘系统(比如RAID)下，可以设置合适的目录来提高IO性能.

* default_storage_engine

    默认的存储引擎，在MySQL5.5下，这个值是INNODB, 所以在不明确指定存储引擎的情况下，新建的表是INNODB.

* general_log/general_log_file

    一般日志；这个日志会记录SQL查询语句，包括INSERT, SELECT, UPDATE等；每次查询后都会写入到日志文件，在产品上一定要关闭掉，不然严重影响性能.

### MySQL Innodb 专用参数:

* innodb_adaptive_flushing

    boolean值；设置为on时，innodb 则会按照在innodb buffer pool 里面的dirty page 比率来动态的把dirty page 刷到磁盘里去。 

* innodb_additional_mem_pool_size

    这个pool 用来保存 innodb 的tables, table columns,table indexes等这些meta 数据。这个大小根据数据库情况来设置.innodb表越多，这个值就越大.

* innodb_autoextend_increment

    在共享表空间情况下，如果表空间已满，可以设置这个值来获得更多的空间，默认是8M; 我觉得在应该比8M更大为好，不过根据您的业务量来推算. 另外，如果配置成 innodb_table_per_file=1 那这个设置的值不影响表空间自动增长.

* innodb_buffer_pool_instances

    这个参数用来指示把innodb pool buffer 分割成多少实例； 比如我配置innodb_buffer_pool_size=2GB, innodb_buffer_pool_instances=2,那么每个pool size 是1GB; 这么配置有利于提高并发处理，因为pool每次使用都需要获得锁，与此同时也就让其他的操作挂起直到当前操作完成处理；所以多实例pool instances 有利于高并发；这个参数也很重要，需要有足够的重视.

* innodb_buffer_pool_size

    这个参数指明了当前innodb允许使用的buffer size； innodb buffer pool 用来缓存数据和表上的索引，关于这个参数有丰富的背景知识，[详细点击这里](http://dev.mysql.com/doc/refman/5.5/en/innodb-buffer-pool.html)

## 使用到的测试脚本

在这里我还是使用我之前的python脚本，可以用来模拟并发和自动生成INSERT语句.

下载地址: https://github.com/jackey/MySQLTools

Clone下来后，复制default.config.ini 命名为config.ini 然后输入对应的参数; 创建测试数据库和测试表， 参考 [这里](http://jackey.github.io/2013/09/16/mysql-performance-monitor-disk-io.html)

然后运行:

{% highlight bash %}
./bin/io_test
{% endhighlight %}

重要参数:

```
consume: 并发用户个数
count: 每个consume产生的SQL个数
```

这个脚本还没有开源，入手也比较难，如果有问题可以随时找我. 然后测试的表也是innodb,后面的优化都是基于innodb引擎.

## 目前瓶颈和优化目标

## 优化过程

*第一次测试*:

测试变量:

```
consume: 1
count: 10000 (1万个插入SQL)
```
测试结果:

	Start Running at: 2013-09-23 15:14:39.606895
	Start Consume with name: Thread-1.
	Finished at: 2013-09-23 15:25:20.730606

可以看到一个用户执行1万个插入SQL,竟然需要15mins 41s (忽略毫秒). 这个是一个很严重的性能问题；我们现在要想优化它就要明白MySQL和Innodb做了哪些磁盘IO操作然后通过配置来减少IO操作.

让我们回忆下，下面这些IO操作可能会用到:

* 二进制事务写日志

* 数据写

* 索引更新

* 错误/慢日志


我们一个一个的来优化，然后看下效果； 

***
二进制事务写日志:

因为innodb是事务型存储引擎，所以每次都是一个事务，如果设置为autocommit=1,那就会自动的commit查询；每次事务都需要把事务包含的查询写入日志，这里有几个参数涉及到这个功能点:


- innodb_flush_log_at_trx_commit 

- innodb_log_buffer_size 

- innodb_log_file_size 

我现在MySQL配置里面, 配置是这样子的:

    innodb_flush_log_at_trx_commit=1 (每次事务提交都需要写入日志, [详情](http://dev.mysql.com/doc/refman/5.5/en/innodb-parameters.html#sysvar_innodb_flush_log_at_trx_commit))
    innodb_log_buffer_size=8388608 (近似8MB)
    innodb_log_file_size=5242880 (近似5MB)

很显然，innodb_flush_log_at_trx_commit是有优化的可能，因为每次都需要写入日志文件是一个很大的IO开销, 我设置为0，意思是每隔1s写入日志文件.

    innodb_flush_log_at_trx_commit=0
    innodb_log_buffer_size=8388608
    innodb_log_file_size=5242880

其他变量保持不变。重启MySQL然后用同样的测试变量测试一遍,结果如下:

    Start Running at: 2013-09-23 16:05:19.719965 
    Start Consume with name: Thread-1.
    Finished at: 2013-09-23 16:05:40.266169 

天啦，只花了21s, 提升了将近44.8倍的效率！ 不过设置为0的负作用是有的，因为不是实时的写入事务日志，所以不算严格意义上的ACID,所以如果发生crash事件（包括innodb 引擎的crash）会丢失最后1s的数据. 

然后我们看下是否需要增加log_buffer_size, 这个参数的意义在于如果有一个比较大的事务需要处理，设置这个参数可以让整个事务日志先寄存在buffer里，在完成事务时候再一起刷到磁盘中，在这里我们没有这么大的事务所以不需要设置此值. 然后innodb_log_file_size 这个文件我觉得有必要增加，它的意义在于事务文件的大小，对于innodb来说事务操作无处不在，所以我们需要增加事务文件大小来减少MySQL对日志文件的checkpoint，这样也可以减少IO. [这里有更详细的设置方法](http://www.cnblogs.com/zuoxingyu/archive/2012/10/25/2738864.html)

下面是我修改后的配置:

    innodb_flush_log_at_trx_commit=0
    innodb_log_buffer_size=8388608
    innodb_log_file_size=134217728

下面的是测试结果:

    Start Running at: 2013-09-23 16:31:15.607059 
    Start Consume with name: Thread-1.
    Finished at: 2013-09-23 16:31:22.692315

可以看到速度又有一次飞跃，只花了 7s. 提高了3倍! 在这里我加大了 innodb_log_file_size 到 512MB 但是结果且不满意，多次测试时间大概是7-8s左右 并没有显著提高.

***
数据写优化

Innodb有一个很重要的参数就是 innodb_buffer_pool_size, 它缓存了索引和数据在内存里面，默认大小是128MB. 我增加到1GB试试.

    innodb_buffer_pool_size=2G

不过测试下来结果且不满意，如下:

	Start Running at: 2013-09-23 17:06:41.078170
	Start Consume with name: Thread-1.
	Finished at: 2013-09-23 17:06:48.263859

性能并没有提高;查看了下 innodb status 发现buffer pool还很充足: 

Free buffers       107963




## 总结