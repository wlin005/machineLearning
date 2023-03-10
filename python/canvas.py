#!/usr/bin/env python3
#%%
import matplotlib.pyplot as plt
import numpy as np
import cairo
import numbers
from math import fmod


def is_number(x):
    return isinstance(x, numbers.Number)


class Canvas:
    ''' Creates a a pycairo surface that behaves similarly to p5js'''
    def __init__(self, width, height):
        ''' Initialize Canvas with given width and height'''
        # See https://pycairo.readthedocs.io/en/latest/reference/context.html
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surf)
        self.color_scale = 255.0

        ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)

        #ctx.scale(width, height)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 255.0)
        ctx.rectangle(0,0,width,height)
        ctx.fill()

        self._color_mode = 'rgb'
        self.width = width
        self.height = height
        self.surf = surf
        self.ctx = ctx
        self.cur_fill = self._convert_rgba([255.0])
        self.cur_stroke = None
        self.no_draw = False

        self.ctx.select_font_face("sans-serif")
        self.ctx.set_font_size(16)
        self.line_cap('round')

    def set_color_scale(self, scale):
        ''' Set color scale, e.g. if we want to specify colors in the 0-255 range, scale would be 255,
        or if the colors are in the 0-1 range, scale will be 1'''
        self.color_scale = scale

    @property
    def surface(self):
        return self.surf

    def no_fill(self):
        self.fill(None)

    def no_stroke(self):
        self.stroke(None)

    def color_mode(self, mode, scale=255):
        self._color_mode = mode
        self.color_scale = scale

    def _apply_colormode(self, clr):
        if self._color_mode == 'hsv':
            return hsv_to_rgb(clr)
        return clr

    def fill(self, *args):
        if args[0] is None:
            self.cur_fill = None
        else:
            self.cur_fill = self._apply_colormode(self._convert_rgba(args))

    def stroke(self, *args):
        if args[0] is None:
            self.cur_stroke = None
        else:
            self.cur_stroke = self._apply_colormode(self._convert_rgba(args))

    def stroke_weight(self, w):
        self.ctx.set_line_width(w)

    def line_cap(self, cap):
        caps = {'butt': cairo.LINE_CAP_BUTT,
                'round': cairo.LINE_CAP_ROUND,
                'square': cairo.LINE_CAP_SQUARE}
        if cap not in caps:
            print(str(cap) + ' not a valid line cap')
            print('Choose one of ' + str(caps.keys()))
            return

        self.ctx.set_line_cap(caps[cap])

    def text_size(self, size):
        self.ctx.set_font_size(size)

    def push(self):
        self.ctx.save()

    def pop(self):
        self.ctx.restore()

    def translate(self, v):
        self.ctx.translate(*v)

    def scale(self, s):
        if is_number(s):
            s = [s, s]
        self.ctx.scale(*s)

    def rotate(self, rad):
        self.ctx.rotate(rad)

    def _fillstroke(self):
        if self.no_draw: # we are in a begin_shape end_shape pair
            return

        if self.cur_fill is not None:
            self.ctx.set_source_rgba(*self.cur_fill)
            if self.cur_stroke is not None:
                self.ctx.fill_preserve()
            else:
                self.ctx.fill()
        if self.cur_stroke is not None:
            self.ctx.set_source_rgba(*self.cur_stroke)
            self.ctx.stroke()

    def circle(self, center, radius):
        self.ctx.new_sub_path()
        self.ctx.arc(*center, radius, 0,np.pi*2.)
        self._fillstroke()

    def begin_shape(self):
        self.no_draw = True

    def end_shape(self):
        self.no_draw = False
        self._fillstroke()

    def rectangle(self, p, size):
        ''' Draw a rectangle with top left corner `p` and width and height specified in `size`'''
        self.ctx.rectangle(*p, *size)
        self._fillstroke()

    def load_image(self, path):
        ''' Load an image from disk. Currently only supports png!'''
        if not 'png' in path:
            print ("Load image only supports PNG files!!!")
            assert(0)
        surf = cairo.ImageSurface.create_from_png(path)
        return surf

    def image(self, img, pos=[0,0], size=None, opacity=1.0):
        ''' Draw an image at position pos and with (optional) size and opacity.
        if size is not specified the imaged will be drawn with its original size'''
        if type(img) == np.ndarray:
            img = numpy_to_surface(img)
        self.ctx.save()
        self.ctx.translate(pos[0], pos[1])
        if size is not None:
            sx = size[0]/img.get_width()
            sy = size[1]/img.get_height()
            self.ctx.scale(sx, sy)
        self.ctx.set_source_surface(img)
        self.ctx.paint_with_alpha(opacity)
        self.ctx.restore()

    def line(self, a, b):
        ''' Draw a line between a and b'''
        self.ctx.new_path()
        self.ctx.move_to(*a)
        self.ctx.line_to(*b)
        self._fillstroke()

    def shape(self, poly_list, closed=False):
        ''' Draw a shape represented as a list of polylines, see the ~polyline~ method for the format of each polyline'''
        self.begin_shape()
        for P in poly_list:
            self.polyline(P, closed)
        self.end_shape()

    def text(self, pos, text, center=False):
        ''' Draw text at position
            if center=True the text will be horizontally centered'''
        if self.cur_fill is not None:
            self.ctx.set_source_rgba(*self.cur_fill)
        if center:
            (x, y, w, h, dx, dy) = self.ctx.text_extents(text)
            self.ctx.move_to(pos[0]-w/2-x, pos[1])
        else:
            self.ctx.move_to(*pos)
        self.ctx.text_path(text)
        self.ctx.fill()

    def polygon(self, points):
        ''' Draw a closed polyline
        The polyline is specified as either a list of [x,y] pairs or as a numpy array with a point in each column '''
        self.polyline(points, True)

    def polyline(self, points, closed=False):
        ''' Draw a polyline (optionally closed).
        The polyline is specified as either a list of [x,y] pairs or as a numpy array with a point in each column '''
        self.ctx.new_path()
        self.ctx.move_to(*points[0])
        for p in points[1:]:
            self.ctx.line_to(*p)
        if closed:
            self.ctx.close_path()

        self._fillstroke()

    def background(self, *args):
        ''' Clear the canvas with a given color '''
        self.ctx.set_source_rgb(*self._convert_rgb(args))
        self.ctx.rectangle(0, 0, self.width, self.height)
        self.ctx.fill()

    def get_image(self):
        ''' Get canvas image as a numpy array '''
        img = np.ndarray (shape=(self.height, self.width,4), dtype=np.uint8, buffer=self.surf.get_data())[:,:,:3].copy()
        img = img[:,:,::-1]
        return img

    def get_image_grayscale(self):
        ''' Returns the canvas image as a grayscale numpy array (in 0-1 range)'''
        img = self.get_image()
        img = np.sum(img, axis=-1)/3
        return img/255

    def save_image(self, path):
        ''' Save the canvas to an image'''
        self.surf.write_to_png(path)

    def show(self, size=None, title='', axis=False):
        import matplotlib.pyplot as plt
        if size is not None:
            plt.figure(figsize=(size[0]/100, size[1]/100))
        else:
            plt.figure(figsize=(self.width/100, self.height/100))
        if title:
            plt.title(title)
        plt.imshow(self.get_image())
        if not axis:
            plt.gca().axis('off')
        plt.show()

    def _convert_rgb(self, x):
        if len(x)==1:
            if not is_number(x[0]): # array like input
                return np.array(x[0])/self.color_scale
            return (x[0]/self.color_scale,
                    x[0]/self.color_scale,
                    x[0]/self.color_scale)
        return (x[0]/self.color_scale,
                x[1]/self.color_scale,
                x[2]/self.color_scale)

    def _convert_rgba(self, x):
        if len(x)==1:
            if not is_number(x[0]): # array like input
                return np.array(x[0])/self.color_scale
            return (x[0]/self.color_scale,
                    x[0]/self.color_scale,
                    x[0]/self.color_scale, 1.0)
        elif len(x) == 3:
            return (x[0]/self.color_scale,
                    x[1]/self.color_scale,
                    x[2]/self.color_scale, 1.0)
        elif len(x) == 2:
            return (x[0]/self.color_scale,
                    x[0]/self.color_scale,
                    x[0]/self.color_scale,
                    x[1]/self.color_scale)
        return (x[0]/self.color_scale,
                x[1]/self.color_scale,
                x[2]/self.color_scale,
                x[3]/self.color_scale)


def radians(x):
    ''' Get radians given x degrees'''
    return np.pi/180*x


def degrees(x):
    ''' Get degrees given x radians'''
    return x * (180.0/np.pi)


def numpy_to_surface(arr):
    ''' Convert numpy array to a pycairo surface'''
    # Get the shape and data type of the numpy array
    if len(arr.shape) == 2:
        if arr.dtype == np.uint8:
            arr = np.dstack([arr, arr, arr, (np.ones(arr.shape)*255).astype(np.uint8)])
        else:
            # Assume grayscale 0-1 image
            arr = np.dstack([arr, arr, arr, np.ones(arr.shape)])
            arr = (arr * 255).astype(np.uint8)
    else:
        if arr.shape[2] == 3:
            #pdb.set_trace()
            if arr.dtype == np.uint8:
                arr = np.dstack([arr, np.ones(arr.shape[:2], dtype=np.uint8)*255])
            else:
                arr = np.dstack([arr, np.ones(arr.shape[:2])])
                arr = (arr * 255).astype(np.uint8)
        else:
            if arr.dtype != np.uint8:
                arr = (arr * 255).astype(np.uint8)

    arr = arr.copy(order='C') # must be "C-contiguous"
    arr[:, :, :3] = arr[:, :, ::-1][:,:,1:]
    #pdb.set_trace()
    surf = cairo.ImageSurface.create_for_data(
        arr, cairo.FORMAT_ARGB32, arr.shape[1], arr.shape[0])

    return surf


def show_image(im, size=None, title='', cmap='gray'):
    ''' Display a (numpy) image'''
    import matplotlib.pyplot as plt
    if size is not None:
        plt.figure(figsize=size)
    else:
        plt.figure()
    if title:
        plt.title(title)
    plt.imshow(im, cmap)
    plt.show()


def show_images(images, ncols, size=None, title='', cmap='gray'):
    ''' Display multiple images in a grid'''
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    n = len(images)
    nrows = int(np.ceil(n/ncols))
    print(nrows)
    if size is not None:
        plt.figure(figsize=size)
    else:
        plt.figure()
    if title:
        plt.title(title)
    gs = GridSpec(nrows, ncols)
    for i, img in enumerate(images):
        ax = plt.subplot(gs[i])
        plt.imshow(img, cmap)
        ax.axis('off')
    plt.tight_layout()
    plt.show()


def hsv_to_rgb(hsva):
    h, s, v = hsva[:3]
    a = 1
    if len(hsva) > 3:
        a = hsva[3]

    if s == 0.0:
        r = g = b = v
    else:
        h = fmod(h, 1) / (60.0 / 360.0)
        i = int(h)
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if i == 0:
            r, g, b = v, t, p
        elif i == 1:
            r, g, b = q, v, p
        elif i == 2:
            r, g, b = p, v, t
        elif i == 3:
            r, g, b = p, q, v
        elif i == 4:
            r, g, b = t, p, v
        else:
            r, g, b = v, p, q

    return np.array([r,g,b,a])[:len(hsva)]

if __name__ == '__main__':
    from skimage import io

    c = Canvas(26, 26)
    c.background(0, 0, 0)

    c.stroke(255)
    c.no_fill()
    c.stroke_weight(2)
    c.fill([255, 0, 0])
    c.text_size(26)
    c.text([13, 22], "B", center=True)
    im = np.vstack([np.linspace(0, 1, 26) for _ in range(26)]).T

    im = np.dstack([im, np.zeros_like(im), np.zeros_like(im), np.ones_like(im)])
    #im = io.imread('./images/test2.png')
    print(im.shape, im.dtype)
    c.image(im) #np.random.uniform(0, 1, (26, 26)))
    #c.polyline(np.random.uniform(0, 26, (10, 2)))
    c.show()

#%%



    c.no_fill()
    c.stroke_weight(13)
    c.line_cap('round')
    c.circle([20, 50], 10)
    c.stroke(255, 0, 255)
    img = c.load_image('images/test.png')
    c.image(img, [200, 100], [120, 20])
    c.line([0,0], [200,60])
    c.line([0,10], [200,90])
    c.stroke(255, 128)
    c.polygon([[10, 20], [100,30], [200,60], [50, 120]])
    c.polygon([[200 + np.cos(t)*100, 200 + np.sin(t)*100] for t in np.linspace(0, np.pi*2, 100)])
    c.fill(255, 0, 0)
    c.begin_shape()
    c.rectangle([20, 20], [200, 200])
    c.rectangle([40, 40], [100, 100])
    c.end_shape()

    im = c.get_image()
    plt.imshow(im)
    plt.show()
