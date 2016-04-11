#!/usr/bin/env python3

from gi.repository import Gtk, GLib
import socket
import os
import calendar
from datetime import datetime, date
from ssp_stripchart import StripChart, Color

APP_DIR=os.path.dirname(os.path.realpath(__file__))
UI_FILE = os.path.join(APP_DIR,'sspmeteo_gui.glade')

labels = ['a_temp_out','a_hum_out','a_dew_out','d_rain','h_rain','d_rain','a_wind_vel','d_wind_vel',
          'a_wind_dir','a_rel_pressure','a_temp_in', 'd_temp_out_max', 'd_temp_out_min',
          'd_hum_out_max','d_hum_out_min', 'd_temp_in_max', 'd_temp_in_min',
          'd_rel_pressure_max', 'd_rel_pressure_min', 'd_wind_racha']


formatos = ['{:5.1f} ºC','{:5.1f} %','{:5.1f} ºC','{:5.1f} mm','{:5.1f} mm','{:5.1f} mm','{:5.1f} km/h',
            '{:5.1f} km/h','{:5.0f} º','{:5.1f} mbar','{:5.1f} ºC']


class ChartGrid(Gtk.Grid):

    __gtype_name__ = 'ChartGrid'

    def __init__(self):
        Gtk.Grid.__init__(self)

        ancho = 400
        alto = 150
        intervalo_muestreo = 5 * 60
        duracion = 24 * 60 * 60
        self.set_column_homogeneous(True)
        self.set_row_homogeneous(True)
        self.chart1 = StripChart(ancho, alto, font_face='Noto Sans', font_size=11)
        self.chart2 = StripChart(ancho, alto, font_face='Noto Sans', font_size=11)
        self.chart3 = StripChart(ancho, alto, font_face='Noto Sans', font_size=11)
        self.chart4 = StripChart(ancho, alto, False, font_face='Noto Sans', font_size=11)
        self.chart5 = StripChart(ancho, alto, font_face='Noto Sans', font_size=11)
        self.chart6 = StripChart(ancho, alto, font_face='Noto Sans', font_size=11)
        self.chart1.set_ejes(duracion, 10, 20, 5)
        self.chart1.add_curva('Temperatura exterior (ºC)', Color.asulito)
        self.chart1.add_curva('Temperatura interior (ºC)', Color.morado)
        self.chart2.set_ejes(duracion, 30, 60,10)
        self.chart2.add_curva('Humedad exterior (%)', Color.asulito)
        self.chart3.set_ejes(duracion, 0, 20, 5)
        self.chart3.add_curva('Velocidad del viento (km/h)', Color.naranja)
        self.chart3.add_curva('Rachas (km/h)', Color.morado)
        self.chart4.set_ejes(duracion, 0, 360, 90)
        self.chart4.add_curva('Dirección del viento (º)', Color.rojo)
        self.chart5.set_ejes(duracion, 1008, 1010, 2)
        self.chart5.add_curva('Presión (mbar)', Color.negro)
        self.chart6.set_ejes(duracion, 0, 15, 5)
        self.chart6.add_curva('Lluvia (mm)', Color.asulito)
        self.chart6.add_curva('Lluvia últ. hora (mm)', Color.naranja)
        self.attach(self.chart1,0,0,1,1)
        self.attach(self.chart2,1,0,1,1)
        self.attach(self.chart3,0,1,1,1)
        self.attach(self.chart4,1,1,1,1)
        self.attach(self.chart5,0,2,1,1)
        self.attach(self.chart6,1,2,1,1)

    def update(self,datos, hora):
        self.chart1.add_valores(hora, datos[0], datos[10])
        self.chart2.add_valores(hora, datos[1])
        self.chart3.add_valores(hora, datos[6], datos[7])
        self.chart4.add_valores(hora, datos[8])
        self.chart5.add_valores(hora, datos[9])
        self.chart6.add_valores(hora, datos[5], datos[4])

    def clear(self):
        self.chart1.clear()
        self.chart2.clear()
        self.chart3.clear()
        self.chart4.clear()
        self.chart5.clear()
        self.chart6.clear()

    def update_desde_fic(self, fecha):
        global err_conexion
        self.clear()
        if not err_conexion:
            peticion = 'getfile ' + fecha + '.dat\r\n'   # Fichero de la fecha
            conexion.send(peticion.encode())
            fichero = ''
            while True:
                chunk = conexion.recv(4096).decode()
                if 'ERROR' in chunk:
                    print('El fichero no existe.')
                    return
                if len(chunk):
                    fichero += chunk
                    if  '\v' == fichero[-1]:
                        break;
                else:
                    err_conexion = True
                    self.status += ' ERROR DE CONEXION.'
                    return
            lineas_fichero = fichero[:-2].split('\n')   # Quita '\n\v' del final del fichero
            for linea in lineas_fichero:
                campo = linea.split(',')  # Dos primeros campos fecha y hora
                hora = datetime.strptime(campo[0] + campo[1], "%Y-%m-%d%H:%M:%S")
                datos=[float(x) for x in campo[2:]]
                self.update(datos, hora)


class OtroDiaWindow(object):

    def __init__(self):

        self.year_range = 25
        senales = {'_on_window2_destroy': self._on_window2_destroy,
                   '_on_dia_clicked': self._on_dia_clicked}
        builder = Gtk.Builder()
        builder.add_objects_from_file(UI_FILE,['window2', 'image1'])
        builder.connect_signals(senales)
        self.window = builder.get_object('window2')
        self.combo_anyo = builder.get_object('combo_anyo')
        for i in range(self.year_range):
            self.combo_anyo.append_text(str(date.today().year - self.year_range + i + 1))
        self.combo_mes = builder.get_object('combo_mes')
        for mes in calendar.month_name[1:]:
            self.combo_mes.append_text(mes)
        self.combo_dia = builder.get_object('combo_dia')
        for i in range(1,32):
            self.combo_dia.append_text(str(i))
        self.chart_grid = ChartGrid()
        builder.get_object('alignment1').add(self.chart_grid)
        self.window.show_all()

    def _on_dia_clicked(self, boton):
        dia = self.combo_dia.get_active() + 1
        mes = self.combo_mes.get_active() + 1
        anyo = self.combo_anyo.get_active() + date.today().year - self.year_range + 1
        fecha = date(anyo, mes, dia).isoformat()
        self.chart_grid.update_desde_fic(fecha)

    def _on_window2_destroy(self, win):
        Gtk.main_quit()

    def run(self):
        f = date.today()
        self.combo_anyo.set_active(self.year_range - 1)
        self.combo_mes.set_active(f.month - 1)
        self.combo_dia.set_active(f.day - 1)
        Gtk.main()


class MainWindow(object):
    """Clase manejadora de la ventana principal.

    """
    def __init__(self):

        senales = {'_on_otro_dia': self._on_otro_dia,
                   '_on_window1_destroy': self._on_window1_destroy}
        self.primera_vez = True

        builder = Gtk.Builder()
        builder.add_objects_from_file(UI_FILE,['window1'])
        builder.connect_signals(senales)
        self.window=builder.get_object('window1')
        self.status = ''
        self.statusbar = builder.get_object('statusbar')
        self.statusbar.push(0,self.status)
        self.ui_label = {}
        for label in labels:
            self.ui_label[label] = builder.get_object(label)
        self.chart_grid = ChartGrid()
        builder.get_object('alignment9').add(self.chart_grid)
        self.window.show_all()
        self.chart_grid.update_desde_fic(date.today().isoformat())
        self._update_ui()
        GLib.timeout_add(intervalo_muestreo *1000, self._update_ui)


    def _on_otro_dia(self,menuitem):
        OtroDiaWindow().run()

    def _update_labels(self, datos):
        for l,f,v in zip(labels, formatos, datos):
            self.ui_label[l].set_label(f.format(v))
        self.status = 'Último acceso: ' + datetime.now().strftime('%x %X') +\
                      '  Recepción: {:5.1f}%'.format(100.0 * datos[11] / 54.0)
        # Datos calculados
        self.ui_label['d_temp_out_max'].set_label(str(self.chart_grid.chart1.curvas[0].maximo))
        self.ui_label['d_temp_out_min'].set_label(str(self.chart_grid.chart1.curvas[0].minimo))
        self.ui_label['d_temp_in_max'].set_label(str(self.chart_grid.chart1.curvas[1].maximo))
        self.ui_label['d_temp_in_min'].set_label(str(self.chart_grid.chart1.curvas[1].minimo))
        self.ui_label['d_hum_out_max'].set_label(str(self.chart_grid.chart2.curvas[0].maximo))
        self.ui_label['d_hum_out_min'].set_label(str(self.chart_grid.chart2.curvas[0].minimo))
        self.ui_label['d_wind_vel'].set_label(str(round(self.chart_grid.chart3.curvas[0].maximo,1)))
        self.ui_label['d_wind_racha'].set_label(str(round(self.chart_grid.chart3.curvas[1].maximo,1)))
        self.ui_label['d_rel_pressure_max'].set_label(str(round(self.chart_grid.chart5.curvas[0].maximo,1)))
        self.ui_label['d_rel_pressure_min'].set_label(str(round(self.chart_grid.chart5.curvas[0].minimo,1)))

    def _update_ui(self):
        global err_conexion
        self.statusbar.pop(0)
        if not err_conexion:
            conexion.send("getcurrent\r\n".encode())
            respuesta = conexion.recv(128).decode()
            if len(respuesta)>0:
                datos=[float(x) for x in respuesta.split(',')]
                self._update_labels(datos)
                if not self.primera_vez:
                    self.chart_grid.update(datos, datetime.now())
            else:
                err_conexion = True
                self.status += ' ERROR DE CONEXION.'
        else:
            self.status += ' ERROR DE CONEXION.'
        self.statusbar.push(0, self.status)
        self.primera_vez = False
        return True

    def _on_window1_destroy(self, win):
        Gtk.main_quit()

    def run(self):
        Gtk.main()


intervalo_muestreo = 5 * 60
duracion = 24 * 60 * 60
err_conexion = False
#~ err_conexion = True
conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Conectando...')
conexion.connect(('192.168.1.20', 5556))
print('Conectado.')
MainWindow().run()
conexion.close()
