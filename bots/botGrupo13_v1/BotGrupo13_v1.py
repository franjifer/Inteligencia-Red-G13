import math
from BotInRedUC3M import BotInRedUC3M
from robocode_tank_royale.bot_api.events import ScannedBotEvent, HitByBulletEvent, HitWallEvent

# Umbrales (justificados en la memoria)
N = 8              # turnos que vale un escaneo (una vuelta de radar)
X_RETIRADA = 20    # energia minima para seguir combatiendo
D_CERCA = 150
D_LEJOS = 400
MARGEN = 100       # separacion de la pared del punto de refugio
PASO = 100
T_ZIGZAG = 20
RADAR_EXTRA = 20   # grados de mas al seguir al rival con el radar, para no perderlo
MEDIO_BOT = 18     # medio ancho del bot (36 px): tolerancia para dar por alineado el canon


class BotGrupo13_v1(BotInRedUC3M):

    def __init__(self):
        super().__init__("BotGrupo13_v1.json")
        self._sentido = 1
        self._olvidar_hechos()

    # ---------- HECHOS: aqui solo se percibe, no se decide ----------
    def _olvidar_hechos(self):
        self._rival_x = self._rival_y = self._rival_dist = None
        self._rival_vel = self._rival_dir = 0
        self._ultimo_escaneo = 0
        self._turno_impacto = -100
        self._dir_bala = 0
        self._choque_pared = False

    def on_round_started(self, e):
        self._olvidar_hechos()

    def on_scanned_bot(self, e: ScannedBotEvent):
        self._rival_x, self._rival_y = e.x, e.y
        self._rival_vel, self._rival_dir = e.speed, e.direction
        self._rival_dist = self.distance_to(e.x, e.y)
        self._ultimo_escaneo = self.turn_number

    def on_hit_by_bullet(self, e: HitByBulletEvent):
        self._turno_impacto = self.turn_number
        self._dir_bala = e.bullet.direction

    def on_hit_wall(self, e: HitWallEvent):
        self._choque_pared = True

    # ---------- MOTOR DE INFERENCIAS ----------
    def run(self):
        self.adjust_gun_for_body_turn = True
        self.adjust_radar_for_gun_turn = True

        while self.is_running:
            visto = (self._rival_dist is not None and
                     self.turn_number - self._ultimo_escaneo < N)
            impacto_reciente = self.turn_number - self._turno_impacto <= 1

            # Movimiento: solo gana una regla (orden = prioridad)
            if self.energy < X_RETIRADA:                            # R1 retirada
                rx, ry = self._punto_refugio()
                self.set_turn_left(self.bearing_to(rx, ry))
                self.set_forward(PASO)

            elif impacto_reciente:                                  # R2 esquiva tras impacto
                self.set_turn_left(self.calc_bearing(self._dir_bala + 90))
                self.set_forward(PASO * self._sentido)

            elif self._choque_pared:                                # R3 rebote en pared
                self._choque_pared = False
                self._sentido = -self._sentido
                self.set_forward(PASO * self._sentido)

            elif visto and self._rival_dist > D_LEJOS:              # R4 acercarse
                self.set_turn_left(self.bearing_to(self._rival_x, self._rival_y))
                self.set_forward(PASO)

            elif visto and self._rival_dist < D_CERCA:              # R5 alejarse
                self.set_turn_left(self._girar(self.bearing_to(self._rival_x, self._rival_y) + 180))
                self.set_forward(PASO)

            elif visto:                                             # R6 zigzag perpendicular
                if self.turn_number % T_ZIGZAG == 0:
                    self._sentido = -self._sentido
                self.set_turn_left(self._girar(self.bearing_to(self._rival_x, self._rival_y) + 90))
                self.set_forward(PASO * self._sentido)

            else:                                                   # R7 por defecto: patrullar
                self.set_turn_left(30)
                self.set_forward(PASO * self._sentido)

            # Canon: se ejecuta en el mismo turno que el movimiento
            if visto:
                if self.energy < X_RETIRADA:                        # R12 en retirada, potencia minima
                    potencia = 1
                elif self._rival_dist < D_CERCA:                    # R9
                    potencia = 3
                elif self._rival_dist <= D_LEJOS:                   # R10
                    potencia = 2
                else:                                               # R11
                    potencia = 1

                px, py = self._prediccion(potencia)                 # R8 apuntar a donde estara el rival
                giro_canon = self.gun_bearing_to(px, py)
                self.set_turn_gun_left(giro_canon)
                tolerancia = max(3, math.degrees(math.atan2(MEDIO_BOT, self._rival_dist)))
                alineado = abs(giro_canon) < tolerancia
                if self.gun_heat == 0 and alineado:                 # R9-R12 solo disparan alineados
                    self.set_fire(potencia)

            # Radar: si tenemos rival lo seguimos; si no, barremos
            if visto:
                giro_radar = self.radar_bearing_to(self._rival_x, self._rival_y)
                giro_radar += RADAR_EXTRA if giro_radar >= 0 else -RADAR_EXTRA
                self.set_turn_radar_left(giro_radar)
            else:
                self.set_turn_radar_right(45)
            self.go()

    def _girar(self, angulo):
        return self.normalize_relative_angle(angulo)

    def _prediccion(self, potencia):
        """Posicion donde estara el rival cuando llegue la bala, si sigue recto a la misma velocidad."""
        turnos = (self.turn_number - self._ultimo_escaneo) + self._rival_dist / (20 - 3 * potencia)
        rad = math.radians(self._rival_dir)
        px = self._rival_x + math.cos(rad) * self._rival_vel * turnos
        py = self._rival_y + math.sin(rad) * self._rival_vel * turnos
        px = min(max(px, MEDIO_BOT), self.arena_width - MEDIO_BOT)
        py = min(max(py, MEDIO_BOT), self.arena_height - MEDIO_BOT)
        return px, py

    def _punto_refugio(self):
        """Esquina mas alejada del rival (o del centro si no lo conocemos), con margen a la pared."""
        rx = self._rival_x if self._rival_x is not None else self.arena_width / 2
        ry = self._rival_y if self._rival_y is not None else self.arena_height / 2
        esquinas = [(MARGEN, MARGEN),
                    (self.arena_width - MARGEN, MARGEN),
                    (MARGEN, self.arena_height - MARGEN),
                    (self.arena_width - MARGEN, self.arena_height - MARGEN)]
        return max(esquinas, key=lambda p: (p[0] - rx) ** 2 + (p[1] - ry) ** 2)


def main():
    BotGrupo13_v1().start()


if __name__ == "__main__":
    main()
