from multiprocessing.dummy import Pool
import sys
from threading import Event,Lock,Semaphore,Thread,Timer

class Interval:
    # Call function every delay milliseconds with optional args and kwargs.
    def __init__(self,delay,function,args=(),kwargs={}):
        if not callable(function):
            raise ValueError('{} is not callable'.format(function))

        self.delay=delay
        self.function=function
        self.args=args
        self.kwargs=kwargs
        self.timer=None

        self._lock=Lock()
        self._calling=False

    def _caller(self):
        # Call function with optional args and kwargs, then set a new Timer
        self._calling=True
        try:
            self.function(*self.args,**self.kwargs)
        except Exception as e:
            pass
        self._calling=False
        self.reset()

    def _settimer(self):
        # Set and start Timer
        # this function should be always called in lock
        if self.is_running():
            return
        self.timer=Timer(self.delay/1000,self._caller)
        self.timer.start()

    def start(self):
        # Start or restart intervaller.
        with self._lock:
            if self.is_running():
                return
            self._settimer()

    def stop(self):
        # Stop intervaller.
        with self._lock:
            if not self.is_running():
                return
            self.timer.cancel()
            self.timer=None

    def reset(self):
        # Reset Timer
        with self._lock:
            if not self.is_running():
                return
            if self._calling:
                return
            self.timer.cancel()
            self.timer=None
            self._settimer()

    def is_running(self):
        return self.timer is not None


class ThreadPool:
    # multiprocessing.dummy.Pool with exc_info in error_callback
    def __init__(self,name=None,processes=None):

        self._processes=processes
        self._pool=Pool(self._processes)
        self._lock=Lock() # lock for self
        self._cblock=Lock() # lock for callback
        self._errcblock=Lock() # lock for error_callback
        self._closed=False

        self.name=name

        for attr in ('apply','map','map_async',
                     'imap','imap_unordered',
                     'starmap','starmap_async','join'):
            setattr(self,attr,getattr(self._pool,attr))

    def _uiter(self,iterable):
        buf=[]
        for item in iterable:
            if item in buf:
                continue
            yield item
            buf.append(item)
        buf.clear()

    def _trycall(self,func,args=(),kwargs={},lock=None):
        if not callable(func):
            return
        with lock:
            try:
                return func(*args,**kwargs)
            except:
                pass

    def _caller(self,func,args,kwargs,callback,error_callback,exc_raise):
        try:
            result=func(*args,**kwargs)
        except:
            etype,value.tb=sys.exc_info()
            self._trycall(error_callback,args=(self.name,etype,value.tb),
                          lock=self._errcblock)
            if exc_raise:
                raise etype(value)
        else:
            self._trycall(callback,args=(result,),
                          lock=self._cblock)
            return result

    def apply_async(self,func,args=(),kwargs={},
                    callback=None,error_callback=None):
        # run error_callback with ThreadPool.name and exc_info if func failed,
        # callback and error_callback will *not* run in multi thread.
        # other arguments is same as Pool.apply_async
        return self._pool.apply_async(
            self._caller,(func,args,kwargs,None,error_callback,True),
            callback=callback)

    def cbmap(self,func,iterable,chunksize=None,
              callback=None,error_callback=None,block=False):
        # shortcut of:
        #
        # for item in iterable:
        #     apply_async(func,args=(items,),kwargs={},
        #                 callback=callback,error_callback=error_callback)
        #
        # always return None
        # block if block set to True
        (self.starmap if block else self.starmap_async)(
            self._caller,
            ((func,(item,),{},callback,error_callback,not block)
             for item in iterable),
            chunksize=chunksize)

    def ucbmap(self,func,iterable,chunksize=None,
               callback=None,error_callback=None,block=False):
        # unique version of ThreadPool.cbmap
        return self.cbmap(func,self._uiter(iterable),chunksize,
                          callback,error_callback,block)

    def umap(self,func,iterable,chunksize=None):
        # unique version of ThreadPool.map
        return self.map(func,self._uiter(iterable),chunksize=chunksize)

    def umap_async(self,func,iterable,chunksize=None,
                   callback=None,error_callback=None):
        # unique version of ThreadPool.map_async
        return self.map_async(
            func,self._uiter(iterable),chunksize,
            callback,error_callback)

    def uimap(self,func,iterable,chunksize=None):
        # unique version of ThreadPool.imap
        return self.imap(func,self._uiter(iterable),chunksize)

    def uimap_unordered(self,func,iterable,chunksize=None):
        # unique version of ThreadPool.imap_unordered
        return self.imap_unordered(func,self._uiter(iterable),chunksize)

    def ustarmap(self,func,iterable,chunksize=None):
        # unique version of ThreadPool.starmap
        return self.starmap(func,self._uiter(iterable),chunksize)

    def ustarmap_async(self,func,iterable,chunksize=None,
                       callback=None,error_callback=None):
        # unique version of ThreadPool.starmap_async
        return self.starmap_async(
            func,self._uiter(iterable),chunksize,
            callback,error_callback)

    def close(self):
        # same as Pool.close
        self._closed=True
        return self._pool.close()

    def terminate(self):
        # same as Pool.terminate
        self._closed=True
        return self._pool.terminate()

    def renew(self):
        # terminate all process and start a new clean pool
        with self._lock:
            self.terminate()
            self._pool=Pool(self._processes)
            self._closed=False

    @property
    def closed(self):
        # True if ThreadPool closed
        return self._closed

    def __enter__(self):
        return self

    def __exit__(self,etype,value,tb):
        self.terminate()

if __name__=='__main__':
    exit(0)
