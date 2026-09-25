"""Prueba rapida del motor de reglas sin servidor: simula la API y mira que regla gana."""
import math
import BotGrupo13_v1 as m


class Falso(m.BotGrupo13_v1):
    # tapamos las propiedades de solo lectura de la API para poder fijarlas a mano
    for _n in ("energy", "x", "y", "gun_heat", "turn_number", "direction", "gun_direction", "radar_direction",
               "arena_width", "arena_height", "is_running", "adjust_gun_for_body_turn",
               "adjust_radar_for_gun_turn", "adjust_radar_for_body_turn"):
        locals()[_n] = None

    def __init__(self, energy=100, x=400, y=300, gun_heat=0, turn=10):
        self.energy, self.x, self.y, self.gun_heat, self.turn_number = energy, x, y, gun_heat, turn
        self.direction = self.gun_direction = self.radar_direction = 0
        self.arena_width, self.arena_height = 800, 600
        self.acciones = {}
        self._writer = self._log = None   # sin registro CSV en la prueba
        self._rival_x = self._rival_y = self._rival_dist = None
        self._ultimo_escaneo = 0
        self._turno_impacto = -100
        self._dir_bala = 0
        self._choque_pared = False
        self._sentido = 1
        self.is_running = True
        self.adjust_gun_for_body_turn = self.adjust_radar_for_gun_turn = False

    # una sola iteracion del bucle
    def go(self): self.is_running = False
    def _reg(self, k, v): self.acciones[k] = v
    def set_turn_left(self, a): self._reg("giro", round(a, 1))
    def set_forward(self, d): self._reg("avance", d)
    def set_turn_gun_left(self, a): self._reg("canon", round(a, 1))
    def set_turn_radar_right(self, a): self._reg("radar", a)
    def set_turn_radar_left(self, a): self._reg("radar_sigue", round(a, 1))
    def radar_bearing_to(self, x, y): return self.normalize_relative_angle(self.direction_to(x, y) - self.radar_direction)
    def set_fire(self, p): self._reg("fuego", p)
    def distance_to(self, x, y): return math.hypot(x - self.x, y - self.y)
    def direction_to(self, x, y): return math.degrees(math.atan2(y - self.y, x - self.x)) % 360
    def normalize_relative_angle(self, a): return (a + 180) % 360 - 180
    def bearing_to(self, x, y): return self.normalize_relative_angle(self.direction_to(x, y) - self.direction)
    def gun_bearing_to(self, x, y): return self.normalize_relative_angle(self.direction_to(x, y) - self.gun_direction)
    def calc_bearing(self, d): return self.normalize_relative_angle(d - self.direction)


def escanea(b, x, y, speed=0, direction=0):
    class E: pass
    e = E(); e.x, e.y, e.speed, e.direction = x, y, speed, direction
    b.on_scanned_bot(e)


casos = []

b = Falso(); b.run()
casos.append(("R7 por defecto (no visto)", b.acciones, "fuego" not in b.acciones and b.acciones["giro"] == 30))

b = Falso(); escanea(b, 750, 300); b.run()   # dist 350 -> zigzag + potencia 2
casos.append(("R6 zigzag + R10 potencia 2", b.acciones, b.acciones["fuego"] == 2 and b.acciones["giro"] == 90))

b = Falso(); escanea(b, 500, 300); b.run()   # dist 100 -> alejarse + potencia 3
casos.append(("R5 alejarse (marcha atras) + R9 potencia 3", b.acciones, b.acciones["fuego"] == 3 and b.acciones["giro"] == 0 and b.acciones["avance"] == -100))

b = Falso(x=50, y=300); escanea(b, 750, 300); b.run()   # dist 700 -> acercarse + potencia 1
casos.append(("R4 acercarse + R11 potencia 1", b.acciones, b.acciones["fuego"] == 1 and b.acciones["giro"] == 0))

b = Falso(energy=15); escanea(b, 500, 300); b.run()   # retirada a esquina (100,100) o (100,500)
casos.append(("R1 retirada (marcha atras) + R12 potencia 1", b.acciones, b.acciones["fuego"] == 1 and b.acciones["avance"] == -100 and 30 < b.acciones["giro"] < 40))

b = Falso(); escanea(b, 750, 300); b._turno_impacto = 10; b._dir_bala = 180; b.run()
casos.append(("R2 esquiva tras impacto", b.acciones, b.acciones["giro"] == -90))

b = Falso(); b._choque_pared = True; b.run()
casos.append(("R3 rebote en pared", b.acciones, b.acciones["avance"] == -100 and b._sentido == -1))

b = Falso(x=60, y=300); b.direction = 180; escanea(b, 750, 300); b.run()   # mirando a la pared izquierda
casos.append(("R3 pared prevista (sin chocar)", b.acciones, b.acciones["avance"] == -100 and b._sentido == -1))

b = Falso(gun_heat=0.5); escanea(b, 750, 300); b.run()
casos.append(("canon caliente: apunta pero no dispara", b.acciones, "fuego" not in b.acciones and "canon" in b.acciones))

b = Falso(turn=30); escanea(b, 750, 300); b._ultimo_escaneo = 20; b.run()   # hace 10 turnos > N
casos.append(("escaneo viejo (>N): por defecto", b.acciones, b.acciones["giro"] == 30 and "fuego" not in b.acciones))

b = Falso(); b.gun_direction = 90; escanea(b, 750, 300); b.run()
casos.append(("canon no alineado: apunta pero no dispara", b.acciones, "fuego" not in b.acciones and b.acciones["canon"] == -90))

b = Falso(); escanea(b, 750, 300, speed=8, direction=90); b.run()   # rival subiendo: apunta por delante
casos.append(("prediccion: apunta adelantado", b.acciones, 20 < b.acciones["canon"] < 40 and "fuego" not in b.acciones))

b = Falso(); escanea(b, 750, 300); b.run()
casos.append(("radar sigue al rival con margen", b.acciones, b.acciones.get("radar_sigue") == 20 and "radar" not in b.acciones))

ok = True
for nombre, acc, bien in casos:
    print(("OK   " if bien else "FALLA"), nombre, acc)
    ok &= bien
print("TODO OK" if ok else "HAY FALLOS")
