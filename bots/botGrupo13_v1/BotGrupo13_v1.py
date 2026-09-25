import math
from BotInRedUC3M import BotInRedUC3M 
from robocode_tank_royale.bot_api.events import HitByBulletEvent, ScannedBotEvent 

def normalize_bearing(angle: float) -> float:
    """Normaliza cualquier ángulo al rango [-180, 180]."""
    return (angle + 180.0) % 360.0 - 180.0

class BotGrupo13_v1(BotInRedUC3M): 
    def __init__(self): 
        super().__init__("BotGrupo13_v1.json")   
        self._ticks_since_scan = 999

    def turn_towards(self, bearing: float):
        """Gira el chasis hacia el bearing indicado (positivo = izquierda, negativo = derecha)."""
        bearing = normalize_bearing(bearing)
        if bearing > 0:
            self.turn_left(bearing)
        else:
            self.turn_right(-bearing)

    def escape_from_walls(self, margin=90) -> bool:
        """Comprueba si el bot está cerca de una pared; si es así, gira al centro y avanza."""
        near_left = self.x < margin
        near_right = self.x > (self.arena_width - margin)
        near_bottom = self.y < margin
        near_top = self.y > (self.arena_height - margin)

        if near_left or near_right or near_bottom or near_top:
            center_x = self.arena_width / 2
            center_y = self.arena_height / 2
            dx = center_x - self.x
            dy = center_y - self.y
            center_angle = math.degrees(math.atan2(dy, dx)) % 360.0
            bearing_center = normalize_bearing(center_angle - self.direction)
            self.turn_towards(bearing_center)
            self.forward(100)
            return True
        return False

    # Lógica principal: movimiento dinámico con evasión continua
    def run(self): 
        # Desacoplar cañón y radar del chasis para apuntar de forma independiente
        try:
            self.adjust_gun_for_body_turn = True
            self.adjust_radar_for_gun_turn = True
        except Exception:
            pass

        while self.running: 
            # Si estamos cerca del borde, salir de la zona peligrosa hacia el centro
            if not self.escape_from_walls():
                self.forward(100)
                self.turn_left(30)
                self.back(100)
                self.turn_right(30)

            self.go()   # cierra el turno 

    # Choque contra pared: retroceder y reorientar al centro de la arena
    def on_hit_wall(self, e):
        self.back(60)
        center_x = self.arena_width / 2
        center_y = self.arena_height / 2
        dx = center_x - self.x
        dy = center_y - self.y
        center_angle = math.degrees(math.atan2(dy, dx)) % 360.0
        bearing_center = normalize_bearing(center_angle - self.direction)
        self.turn_towards(bearing_center)
        self.forward(100)

    # Cada turno: si hace más de 2 turnos que no vemos al rival, barrer el radar 360°
    def on_tick(self, e):
        self._ticks_since_scan += 1
        if self._ticks_since_scan > 2:
            self.set_turn_radar_right(45)

    # Detección de rival: apuntar con precisión geométrica y disparar
    def on_scanned_bot(self, e: ScannedBotEvent): 
        self._ticks_since_scan = 0

        if hasattr(e, "x") and hasattr(e, "y") and e.x is not None and e.y is not None:
            dx = e.x - self.x
            dy = e.y - self.y
            dist = math.hypot(dx, dy)

            # 1. Potencia dinámica según distancia
            if dist < 200:
                power = 3.0     # Muy cerca: máximo daño (3 pts daño / punto)
            elif dist < 450:
                power = 2.0     # Distancia media: equilibrio velocidad/daño
            else:
                power = 1.0     # Lejos: bala rápida (17 px/tick) y bajo consumo

            # Protección de energía si nos queda poca vida
            if self.energy < 15:
                power = min(power, 1.0)

            # 2. Predicción de posición (adelantar el tiro según velocidad y rumbo del rival)
            bullet_speed = 20.0 - (3.0 * power)
            time_to_hit = dist / bullet_speed
            enemy_speed = getattr(e, "speed", 0.0) or 0.0
            enemy_dir = getattr(e, "direction", 0.0) or 0.0

            if enemy_speed != 0:
                rad = math.radians(enemy_dir)
                target_x = e.x + math.cos(rad) * enemy_speed * time_to_hit
                target_y = e.y + math.sin(rad) * enemy_speed * time_to_hit
                target_x = max(20.0, min(self.arena_width - 20.0, target_x))
                target_y = max(20.0, min(self.arena_height - 20.0, target_y))
            else:
                target_x, target_y = e.x, e.y

            # 3. Orientar cañón hacia la posición calculada
            t_dx = target_x - self.x
            t_dy = target_y - self.y
            angle_to_target = math.degrees(math.atan2(t_dy, t_dx)) % 360.0
            gun_diff = normalize_bearing(angle_to_target - self.gun_direction)

            if gun_diff > 0:
                self.set_turn_gun_left(gun_diff)
            else:
                self.set_turn_gun_right(-gun_diff)

            # 4. Mantener radar fijado sobre el rival (Radar Lock)
            real_angle = math.degrees(math.atan2(dy, dx)) % 360.0
            radar_diff = normalize_bearing(real_angle - self.radar_direction)
            if radar_diff > 0:
                self.set_turn_radar_left(radar_diff * 1.5)
            else:
                self.set_turn_radar_right(-radar_diff * 1.5)

            # 5. DISPARAR cuando el cañón esté suficientemente alineado
            max_error = max(6.0, math.degrees(math.atan2(20.0, max(dist, 1.0))))
            if abs(gun_diff) <= max_error:
                self.set_fire(power)
        else:
            self.set_fire(1)

    # Evasión inteligente al recibir disparo: perpendicular hacia el centro de la arena
    def on_hit_by_bullet(self, e: HitByBulletEvent):
        # Si ya estábamos cerca de una pared, priorizar huir al centro
        if self.escape_from_walls(margin=110):
            return

        bullet_dir = e.bullet.direction
        opt1 = (bullet_dir + 90.0) % 360.0
        opt2 = (bullet_dir - 90.0) % 360.0

        center_x = self.arena_width / 2
        center_y = self.arena_height / 2
        center_angle = math.degrees(math.atan2(center_y - self.y, center_x - self.x)) % 360.0

        diff1 = abs(normalize_bearing(opt1 - center_angle))
        diff2 = abs(normalize_bearing(opt2 - center_angle))

        chosen_angle = opt1 if diff1 <= diff2 else opt2
        turn_needed = normalize_bearing(chosen_angle - self.direction)
        self.turn_towards(turn_needed)
        self.forward(70)

def main(): 
    BotGrupo13_v1().start() 

if __name__ == "__main__": 
    main()