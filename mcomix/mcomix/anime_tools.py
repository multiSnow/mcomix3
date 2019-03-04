import math

from gi.repository import GdkPixbuf

class AnimeFrameBuffer:
    def __init__(self,width,height,n_frames,loop=1):
        self.n_frames=n_frames
        self.width=width
        self.height=height
        self.loop=0 if loop>10 else loop # loop over 10 is indefinitely

        self.framelist=[None]*n_frames
        self.duration=0
        self.fps=0

    def add_frame(self,index,pixbuf,duration,transparency=None):
        if not duration:
            # zero duration should not be added to animation
            return
        if self.n_frames<=index:
            raise EOFError('index over')
        self.framelist[index]=(pixbuf,duration)
        self.duration=math.gcd(duration,self.duration)

    def create_animation(self):
        if not self.fps:
            self.fps=1000/self.duration
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
                for c in range(duration//self.duration):
                    anime.add_frame(pixbuf)

        anime._framebuffer=self

        return anime
