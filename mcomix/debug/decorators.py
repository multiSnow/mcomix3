# -*- coding: utf-8 -*-

import time
import functools

""" Decorators for debugging and testing functions. """

def MeasureTime(function):
	""" Measures the execution time of a function. Probably pretty inaccurate,
	but better than nothing. """

	@functools.wraps(function)
	def wrapper(*args, **kwargs):
		start = time.time()
		result = function(*args, **kwargs)
		end = time.time()

		print "Execution time of %s: %f sec" % (function.__name__, end - start)
		return result
	
	return wrapper
