import math

from gi.repository import GdkPixbuf

class AnimeFrameBuffer:
    def __init__(self,n_frames,loop=1):
        self.n_frames=n_frames
        self.width=0
        self.height=0
        self.loop=0 if loop>10 else loop # loop over 10 is infinitely

        self.framelist=[None]*n_frames
        self.duration=0
        self.fps=0

    def add_frame(self,index,pixbuf,duration,background=None):
        if self.n_frames<=index:
            raise EOFError('index over')
        width=pixbuf.get_width()
        height=pixbuf.get_height()
        if self.width*self.height:
            if width!=self.width or height!=self.height:
                raise ValueError('frame with different size')
        else:
            self.width=width
            self.height=height
        if background:
            pixbuf=pixbuf.composite_color_simple(
                width,height,GdkPixbuf.InterpType.NEAREST,
                255,1024,background,background
            )
        self.framelist[index]=(pixbuf,duration)
        self.duration=math.gcd(duration,self.duration)

    def copy(self):
        newbuffer=AnimeFrameBuffer(self.n_frames,loop=self.loop)
        for n,frame in enumerate(self.framelist):
            pixbuf,duration=frame
            newbuffer.add_frame(n,pixbuf,duration)
        return newbuffer

    def create_animation(self):
        if not self.width*self.height:
            raise ValueError('no frames')
        if not self.fps:
            if self.duration:
                self.fps=1000/self.duration
            else:
                # all duration is 0, set fps to 60
                # TODO: correctly deal with 0 duration
                self.fps=60
        anime=GdkPixbuf.PixbufSimpleAnim.new(self.width,self.height,self.fps)
        if self.loop:
            anime.set_loop(False)
        else:
            anime.set_loop(True)
        for l in range(max(1,self.loop)):
            for n,frame in enumerate(self.framelist):
                if not frame:
                    raise OSError('animation corrupted')
                pixbuf,duration=frame
                if not (duration and self.duration):
                    loop=1
                else:
                    loop=duration//self.duration
                for c in range(loop):
                    anime.add_frame(pixbuf)

        anime._framebuffer=self

        return anime

def frame_executor(animation,function,args=(),kwargs={}):
    if not callable(function):
        # function is not a function, do nothing
        return animation
    framebuffer=getattr(animation,'_framebuffer',None)
    if not framebuffer:
        # animation does not have AnimeFrameBuffer, do nothing
        return animation
    # call function on every frame
    anime=AnimeFrameBuffer(framebuffer.n_frames,loop=framebuffer.loop)
    for n,frame in enumerate(framebuffer.framelist):
        pixbuf,duration=frame
        anime.add_frame(n,function(pixbuf,*args,**kwargs),duration)
    return anime.create_animation()
