---
layout: default
title: Linux系统运维--查询局域网内机器IP
description: 在Linux下面经常会想知道局域网内有哪些机器，并且想查询这些机器的IP.这篇文章通过一段小脚本帮助完成这项工作.
tags: [Linux, 局域网机器查询，ping, bash获得本机IP地址]
---

# 使用bash查询本地局域网所有主机

我经常会遇到查询局域网内所有活跃主机的需求，我这里介绍使用Bash脚本来获取局域网内所有主机的方法.

先看代码，

	#!/usr/bin/env bash

	# Show machine that around me in current local area network
	NET=$( ifconfig | grep 'inet addr' | cut -d: -f2 | awk '{print $1}' | grep -v "127.0.0.1" | cut -d. -f1,2,3 )
	for ip in $(seq 1 254);
	do ping -c 1 $NET.$ip >/dev/null;
		if [ $? -eq 0 ];then
			echo "$NET.$ip" up
		fi
	done

简单来说，就是通过ping来检测. 来分析下代码:

	NET=$( ifconfig | grep 'inet addr' | cut -d: -f2 | awk '{print $1}' | grep -v "127.0.0.1" | cut -d. -f1,2,3 )

这段用来获取本机地址

	seq 1 254

来生成一个大小从1到254的数组，后续根据这个数组元素来组合一段IP进行ping操作

	ping -c 1 $NET.$ip >/dev/null;
	if [ $? -eq 0 ];then
		echo "$NET.$ip" up
	fi

对目标主机进行1次（也只有1次）的ping操作，如果ping程序退出状态是0，则能ping通，主机存在.

这段代码小巧，已经在我的MySQLTools开发包里使用到了，挺好用，希望能帮到你们。