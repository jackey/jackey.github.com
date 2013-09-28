#!/usr/bin/env python

import time
from subprocess import call

i = 1

while True:
	print "trying to push %s times" %(i) 
	call(["./push.sh"])
	time.sleep(2)

