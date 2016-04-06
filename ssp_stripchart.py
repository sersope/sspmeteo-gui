#!/usr/bin/env python3
"""
A GTK+ widget for graphical representation of values over time.

Requeriments: PyGObject (see https://wiki.gnome.org/Projects/PyGObject).
For python 2 and 3.
Run this in a python console for an example:
    import ssp_stripchart
    ssp_stripchart.test()
"""

from gi.repository import Gtk, Gdk
from collections import deque
from datetime import datetime, timedelta


class Color:
    """Enum containing color definitions as (r, g, b)
    where r, g, b are floats from 0.0 to 1.0
    """
    negro = (0,0,0)
    gris = (0.3, 0.3, 0.3)
    rojo = (1.0, 0, 0)
    asulito = (30/255.0, 144/255.0, 255/255.0)
    morado  = (128/255.0, 0/255.0, 128/255.0)
    naranja = (255/255.0, 79/255.0, 0/255.0)
    fondo = (255/255.0, 244/255.0, 238/255.0)


class Curva:
    """Each of the curves in the graph to represent.

    It consists of a title, a color, a queue to store the values and two
    fields containing the maximum and minimum values.
    """
    titulo = ''
    color = (0, 0, 0)       # tupla (r, g ,b)
    valores = None          # deque de valores eje Y
    maximo = float('-inf')
    minimo = float('inf')


class StripChart(Gtk.DrawingArea):
    """Implements a widget for graphical representation of values over time.

    """

    def __init__(self, ancho=500, alto=250, tipo_linea=True, font_face= '', font_size=11):
        """Constructor.
        Parameters:
            ancho,
            alto:           width and height of the widget in pixels.
            tipo_linea:     define if the curves are drawn with lines connecting values (True) or
                            drawing values as small circles (False).
            font_face,
            font_size:      name and font size to use for text.
        """
        Gtk.DrawingArea.__init__(self)
        self.set_size_request(ancho, alto)
        self.connect("draw", self._on_draw)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        self.connect("motion_notify_event", self._on_mouse_move)
        self.connect("leave_notify_event", self._on_mouse_leave)
        self.connect("enter_notify_event", self._on_mouse_enter)

        self.duracion = 60          # Duracion total del grafico (seg.)
        self.curvas = []            # Contiene las curvas
        self.tiempos = deque()      # Contiene los tiempos datetime de los valores de las curvas
        self.tipo_linea = tipo_linea
        self.font_size = font_size
        self.font_face = font_face
        self.b_izq = 0          # Bordes
        self.b_der = 5          # Bordes
        self.b_sup = 0          # Bordes
        self.b_inf = 0          # Bordes
        self.wrect = 0          # Dimensiones de la ventana del widget
        self.g_ancho = 1        # Anchura del grafico
        self.g_alto = 1         # Altura del grafico
        self.cursor_x = 0
        self.cursor_on = False

    def _on_mouse_enter(self, widget, event):
        if len(self.tiempos):
            self.cursor_on = True

    def _on_mouse_leave(self, widget, event):
        self.cursor_on = False
        self.queue_draw()

    def _on_mouse_move(self, widget, cursor):
        if len(self.tiempos):
            self.cursor_x = cursor.x
            self.queue_draw()
        return False

    def _on_draw(self, widget, ct):
        ct.select_font_face(self.font_face)
        ct.set_font_size(self.font_size)
        (foo, font_desc, font_alto, font_ancho, foo) = ct.font_extents()
        # Anchura bordes
        texto_vmax = str(self.v_max)
        texto_vmin = str(self.v_min)
        self.b_izq = font_ancho + max(ct.text_extents(texto_vmax)[2], ct.text_extents(texto_vmin)[2])
        self.b_sup = self.b_inf = font_alto
        # Area del grafico
        self.wrect = self.get_allocation()
        self.g_ancho = self.wrect.width - self.b_izq - self.b_der
        self.g_alto = self.wrect.height - self.b_sup - self.b_inf
        ct.set_source_rgb(*Color.fondo)
        ct.rectangle(self.b_izq, self.b_sup, self.g_ancho, self.g_alto)
        ct.fill()
        # Etiquetas y lineas secundarias del eje Y
        ct.set_source_rgb(*Color.gris)
        ct.set_line_width(0.2)
        delta_y = self.delta_v * self.g_alto / (self.v_max - self.v_min)
        lineas = round(self.g_alto / delta_y)
        for i in range(0, int(lineas) + 1):
            v = self.v_min + i*self.delta_v
            ct.move_to(font_ancho/2, self.b_sup + self.g_alto - i*delta_y + font_alto/4)
            ct.set_source_rgb(*Color.negro)
            ct.show_text(str(int(v)))
            ct.move_to(self.b_izq, self.b_sup + self.g_alto - i*delta_y)
            ct.set_source_rgb(*Color.gris)
            ct.rel_line_to(self.g_ancho, 0)
        ct.stroke()

        # Cursor y etiquetas del cursor
        secs = (self.b_izq + self.g_ancho - self.cursor_x) * self.duracion / self.g_ancho
        if len(self.tiempos):
            cursor_t = self.tiempos[0] - timedelta(seconds = secs)
            if cursor_t >= self.tiempos[-1] and cursor_t <= self.tiempos[0] and self.cursor_on:
                # Linea vertical
                ct.set_line_width(0.8)
                ct.set_source_rgb(*Color.negro)
                x = self.cursor_x
                ct.move_to(x, self.b_sup)
                ct.rel_line_to(0, self.g_alto)
                ct.stroke()
                # Indice para encontrar los valores Y apuntados por el cursor
                cursor_i = 0
                dt_min = float('inf')
                for i,t in enumerate(self.tiempos):
                    dt = abs((cursor_t - t).total_seconds())
                    if  dt < dt_min:
                        dt_min = dt
                        cursor_i = i
                # Texto a mostrar
                # primero se calcula su extension para colocarlo a un lado u otro del cursor
                texto = texto_hora = datetime.strftime(cursor_t, "%x %H:%M:%S")
                for curva in self.curvas:
                    valor = curva.valores[cursor_i]
                    texto += '  ' + str(round(float(valor),1))
                texto_ext = ct.text_extents(texto)[4]
                y = self.wrect.height - font_desc
                if self.cursor_x > self.wrect.width/2:
                    ct.move_to(x - texto_ext, y)
                else:
                    ct.move_to(x, y)
                ct.show_text(texto_hora)
                for curva in self.curvas   :
                    valor = curva.valores[cursor_i]
                    ct.set_source_rgb(*curva.color)
                    ct.show_text( '  ' + str(round(float(valor),1)))

        # Leyenda
        ct.move_to(self.b_izq, self.b_sup - font_desc)
        for curva in self.curvas:
            ct.set_source_rgb(*curva.color)
            ct.show_text(curva.titulo + '   ')
        # Dibuja curvas de valores
        self._draw_curvas(ct)
        return False

    def _draw_curvas(self, ct):
        x0 = self.b_izq + self.g_ancho
        y0 = self.b_sup + self.g_alto
        ct.set_line_width(1.0)
        for curva in self.curvas:
            ct.set_source_rgb(*curva.color)
            for t,v in zip(self.tiempos,curva.valores):
                dt = (self.tiempos[0] - t).total_seconds()
                dx = dt * self.g_ancho / self.duracion
                dy = (v - self.v_min) * self.g_alto / (self.v_max - self.v_min)
                if self.tipo_linea:
                    if dt==0:
                        ct.move_to(x0, y0 - dy -1)
                    ct.line_to(x0 - dx, y0 - dy)
                else:
                    ct.new_sub_path()
                    ct.arc(x0 - dx, y0 - dy, 1, 0, 2*3.1416)
            ct.stroke()

    def set_ejes(self, duracion, val_min, val_max, sep_lineas):
        """Defines the coordinate axes for graphing.
        Parameters:
        duracion:   X axis width in seconds.
        val_min,
        val_max:    extreme values of the Y axis.
        sep_lineas: distance in units of value between secondary lines of Y axis.
        """
        self.duracion = duracion
        self.v_min = val_min
        self.v_max = val_max
        self.delta_v = sep_lineas

    def add_curva(self, titulo, color):
        """Add a new curve values to represent.
        You can add as many curves are desired.
        Parameters:
            titulo: title for the curve (type string).
            color:  color for the curve (type Color).
        """
        s = Curva()
        s.titulo = titulo
        s.color = color
        s.valores = deque()
        self.curvas.append(s)

    def add_valores(self, hora, *valores):
        """Adds values for the different curves at a particular time.
        Parameters:
            hora:       time coordinate for the added values (type datetime).
            valores:    sequence of values to be displayed in the order of definition of the curves
                        and a value for each curve.
        """
        if len(self.tiempos):
            borrar_valor = int((hora - self.tiempos[-1]).total_seconds()) > int(self.duracion)
        else:
            borrar_valor= False
        for v,c in zip(valores,self.curvas):
            if borrar_valor:
                c.valores.pop()
            c.valores.appendleft(v)
            c.maximo = max(c.valores)
            c.minimo = min(c.valores)
            if c.maximo > self.v_max:
                self.v_max = c.maximo - (c.maximo % self.delta_v) + self.delta_v
            if c.minimo < self.v_min:
                self.v_min = c.minimo - (c.minimo % self.delta_v)
        if borrar_valor:
            self.tiempos.pop()
        self.tiempos.appendleft(hora)
        self.queue_draw()

    def clear(self):
        """Delete curve values and times.

        """
        self.tiempos.clear()
        for curva in self.curvas:
            curva.valores.clear()
            curva.maximo = float('-inf')
            curva.minimo = float('inf')
        self.queue_draw()


def test():
    """ Run an example.
    """
    from gi.repository import GLib
    import random

    def timer():
        chart.add_valores(datetime.now(), random.randint(vmin, vmax), random.randint(20,30), random.randint(70,90))
        return True

    intervalo_muestreo = 3
    duracion = 60
    vmin = 0
    vmax = 45
    sep = 10
    chart = StripChart(900,150, font_face = 'Noto Sans', font_size=11)
    chart.set_ejes(duracion, vmin, vmax, sep)
    chart.add_curva(titulo='Temp. exterior (C)', color=Color.asulito)
    chart.add_curva('Temp. interior (C)', Color.morado)
    chart.add_curva('Hum. exterior (%)', Color.naranja)

    window = Gtk.Window()
    window.add(chart)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    timer()
    GLib.timeout_add(intervalo_muestreo*1000,timer)
    Gtk.main()


if __name__ == "__main__":
    test()
