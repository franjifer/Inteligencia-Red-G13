"""
BotInRedUC3M - Clase base de telemetria para "Inteligencia en Red" (Robocode Tank Royale).

Genera un CSV por batalla en ./datos_batallas/. Una fila por evento, siempre
las mismas 20 columnas; la columna 'tipo' dice que representa la fila.

TIPOS DE FILA
  propio            estado de vuestro bot en CADA turno
  rival             estado de un rival en CADA escaneo, con distancia y bearing
  disparo           bala disparada, con el rival y la distancia del ultimo escaneo
  impacto_dado      una bala vuestra acierta a un rival
  impacto_recibido  os acierta la bala de otro bot
  choque_pared      choque contra la pared
  choque_bot        choque contra otro bot
  fin_ronda         lo que consiguio vuestro bot EN ESA RONDA
  fin_juego         totales de vuestro bot en TODA la batalla

Las columnas que no aplican a un tipo de fila se quedan vacias.

NOTA: el servidor solo envia a cada bot SUS PROPIOS resultados oficiales
(rank, puntuacion...). De los rivales solo se tiene lo que ve el radar, que
es justo el material de trabajo de las practicas.
"""

import csv
import functools
import math
import os
import time

from robocode_tank_royale.bot_api import Bot, BotInfo

CARPETA_DATOS = "datos_batallas"

COLUMNAS = [
    # Claves
    "ronda", "turno", "tipo", "id",
    # Estado (propio y rival)
    "x", "y", "energia", "velocidad", "direccion",
    # Geometria hacia el rival escaneado
    "dist_al_rival", "bearing_al_rival",
    # Eventos
    "id_otro", "potencia", "dano",
    # Resultados de ronda / batalla (solo del bot propio)
    "vivo", "rank", "supervivencia", "dano_balas", "dano_embestida", "puntuacion",
]

_MANEJADORES = [
    "on_game_started", "on_round_started", "on_tick", "on_scanned_bot",
    "on_bullet_fired", "on_hit_by_bullet", "on_bullet_hit",
    "on_hit_wall", "on_hit_bot",
    "on_round_ended", "on_game_ended",
]


def _val(obj, *nombres, defecto=""):
    """Primer atributo/metodo disponible (tolera self.x o self.get_x())."""
    for n in nombres:
        if hasattr(obj, n):
            try:
                v = getattr(obj, n)
                return v() if callable(v) else v
            except Exception:
                return defecto
    return defecto


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class BotInRedUC3M(Bot):

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name in _MANEJADORES:
            propio = cls.__dict__.get(name)
            if propio is None:
                continue
            registro = getattr(BotInRedUC3M, name)

            def wrapper(registro, alumno):
                @functools.wraps(alumno)
                def handler(self, e):
                    registro(self, e)
                    return alumno(self, e)
                return handler

            setattr(cls, name, wrapper(registro, propio))

    def __init__(self, config_file):
        super().__init__(BotInfo.from_file(config_file))
        self._round = 0
        self._battle = 0
        self._log = None
        self._writer = None
        self._ultima_energia = None
        self._ultimo_turno = ""
        self._ultimo_rival = None      # (id, x, y) del ultimo escaneo
        self._acumulado = {}
        self._config_name = os.path.splitext(os.path.basename(config_file))[0]
        os.makedirs(CARPETA_DATOS, exist_ok=True)

    @property
    def is_running(self):
        return self.running

    def _open_log(self):
        self._close_log()
        self._battle += 1
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(
            CARPETA_DATOS,
            f"{self._config_name}__{timestamp}_{os.getpid()}_b{self._battle}.csv",
        )
        self._log = open(path, "w", newline="")
        self._writer = csv.DictWriter(self._log, fieldnames=COLUMNAS,
                                      restval="", extrasaction="ignore")
        self._writer.writeheader()

    def _close_log(self):
        try:
            if self._log is not None and not self._log.closed:
                self._log.flush()
                self._log.close()
        except Exception:
            pass
        self._log = None
        self._writer = None

    def _my_id(self):
        return _val(self, "my_id", "get_my_id", defecto=0)

    def _write_data(self, type, **kw):
        if self._writer is None or self._log is None or self._log.closed:
            return
        row = {
            "ronda": self._round,
            "turno": _val(self, "turn_number", "get_turn_number"),
            "tipo": type,
        }
        row.update(kw)
        try:
            self._writer.writerow(row)
        except (ValueError, OSError):
            pass

    _METRICAS = (
        ("supervivencia", "survival"),
        ("dano_balas", "bullet_damage"),
        ("dano_embestida", "ram_damage"),
        ("puntuacion", "total_score"),
    )

    def _resultados(self, r, por_ronda):
        datos = {"rank": getattr(r, "rank", "")}
        for columna, atributo in self._METRICAS:
            total = _num(getattr(r, atributo, None))
            if total is None:
                datos[columna] = ""
                continue
            if por_ronda:
                datos[columna] = round(total - self._acumulado.get(columna, 0.0), 3)
                self._acumulado[columna] = total
            else:
                datos[columna] = total
        return datos

    # ============================================================
    # REGISTRO AUTOMATICO
    # NO TOCAR
    # ============================================================
    def on_game_started(self, e):
        self._round = 0
        self._acumulado = {}
        self._open_log()

    def on_round_started(self, e):
        self._round += 1
        self._ultima_energia = None
        self._ultimo_turno = ""
        self._ultimo_rival = None

    def on_tick(self, e):
        energia = _val(self, "energy", "get_energy")
        turno = _val(self, "turn_number", "get_turn_number")
        self._ultima_energia = _num(energia)
        self._ultimo_turno = turno
        self._write_data(
            "propio",
            id=self._my_id(),
            x=_val(self, "x", "get_x"),
            y=_val(self, "y", "get_y"),
            energia=energia,
            velocidad=_val(self, "speed", "get_speed"),
            direccion=_val(self, "direction", "get_direction"),
        )

    def on_scanned_bot(self, e):
        mx, my = _num(_val(self, "x", "get_x")), _num(_val(self, "y", "get_y"))
        ex, ey = _num(getattr(e, "x", None)), _num(getattr(e, "y", None))
        dist = math.hypot(mx - ex, my - ey) if None not in (mx, my, ex, ey) else ""
        bearing = ""
        try:
            if ex is not None and ey is not None:
                bearing = self.bearing_to(ex, ey)
        except Exception:
            bearing = ""
        self._ultimo_rival = (getattr(e, "scanned_bot_id", ""), ex, ey)
        self._write_data(
            "rival",
            id=getattr(e, "scanned_bot_id", ""),
            x=getattr(e, "x", ""),
            y=getattr(e, "y", ""),
            energia=getattr(e, "energy", ""),
            velocidad=getattr(e, "speed", ""),
            direccion=getattr(e, "direction", ""),
            dist_al_rival=dist,
            bearing_al_rival=bearing,
        )

    def on_bullet_fired(self, e):
        b = getattr(e, "bullet", None)
        id_otro, dist = "", ""
        if self._ultimo_rival is not None:
            id_otro, rx, ry = self._ultimo_rival
            mx, my = _num(_val(self, "x", "get_x")), _num(_val(self, "y", "get_y"))
            if None not in (mx, my, rx, ry):
                dist = math.hypot(mx - rx, my - ry)
        self._write_data(
            "disparo",
            id=self._my_id(),
            x=getattr(b, "x", ""),
            y=getattr(b, "y", ""),
            direccion=getattr(b, "direction", ""),
            potencia=getattr(b, "power", ""),
            energia=_val(self, "energy", "get_energy"),
            id_otro=id_otro,
            dist_al_rival=dist,
        )

    def on_bullet_hit(self, e):
        b = getattr(e, "bullet", None)
        self._write_data(
            "impacto_dado",
            id=self._my_id(),
            id_otro=getattr(e, "victim_id", ""),
            dano=getattr(e, "damage", ""),
            energia=getattr(e, "energy", ""),
            potencia=getattr(b, "power", ""),
        )

    def on_hit_by_bullet(self, e):
        b = getattr(e, "bullet", None)
        self._write_data(
            "impacto_recibido",
            id=self._my_id(),
            id_otro=getattr(b, "owner_id", ""),
            dano=getattr(e, "damage", ""),
            energia=getattr(e, "energy", ""),
            potencia=getattr(b, "power", ""),
        )

    def on_hit_wall(self, e):
        self._write_data(
            "choque_pared",
            id=self._my_id(),
            x=_val(self, "x", "get_x"),
            y=_val(self, "y", "get_y"),
            energia=_val(self, "energy", "get_energy"),
            velocidad=_val(self, "speed", "get_speed"),
            direccion=_val(self, "direction", "get_direction"),
        )

    def on_hit_bot(self, e):
        self._write_data(
            "choque_bot",
            id=self._my_id(),
            id_otro=getattr(e, "victim_id", ""),
            x=getattr(e, "x", ""),
            y=getattr(e, "y", ""),
            energia=getattr(e, "energy", ""),
        )

    def on_round_ended(self, e):
        vivo = 1 if (self._ultima_energia or 0) > 0 else 0
        datos = {"id": self._my_id(), "vivo": vivo, "turno": self._ultimo_turno}
        r = getattr(e, "results", None)
        if r is not None:
            try:
                datos.update(self._resultados(r, por_ronda=True))
            except Exception:
                pass
        self._write_data("fin_ronda", **datos)
        try:
            if self._log is not None and not self._log.closed:
                self._log.flush()
        except Exception:
            pass

    def on_game_ended(self, e):
        r = getattr(e, "results", None)
        if isinstance(r, (list, tuple)):
            r = r[0] if r else None
        datos = {"id": self._my_id(), "turno": self._ultimo_turno}
        if r is not None:
            try:
                datos.update(self._resultados(r, por_ronda=False))
            except Exception:
                pass
        self._write_data("fin_juego", **datos)
        self._close_log()
