#FELIX ANTONIO MERCEDES MERCEDES
#21-EISN-2-047
import math
from .astar import a_star
from .configuracion import *

#arbol de comportamiento
class Node:
    """Clase base para todos los nodos del árbol de comportamiento."""
    def __init__(self, name="Node"):
        self.name = name
        self.status = "READY"  

    def tick(self, enemy, jugador, game_state, copa_pos):
        """Método que debe ser implementado por las clases hijas"""
        raise NotImplementedError

class Composite(Node):
    """Clase base para nodos compuestos (Sequence, Selector)."""
    def __init__(self, name="Composite", children=None):
        super().__init__(name)
        self.children = children if children is not None else []

    def add_child(self, node):
        """añade un nodo hijo a este compuesto"""
        self.children.append(node)

class Sequence(Composite):
    """
    un nodo Sequence ejecuta sus hijos en orden.
    retorna SUCCESS si todos los hijos tienen éxito, de lo contrario FAILURE.
    retorna RUNNING si algún hijo está ejecutándose.
    """
    def tick(self, enemy, jugador, game_state, copa_pos):
        for child in self.children:
            status = child.tick(enemy, jugador, game_state, copa_pos)
            if status == "FAILURE":
                self.status = "FAILURE"
                return self.status
            if status == "RUNNING":
                self.status = "RUNNING"
                return self.status
        self.status = "SUCCESS"
        return self.status

class Selector(Composite):
    """
    un nodo Selector ejecuta sus hijos en orden.
    retorna SUCCESS si algún hijo tiene éxito, de lo contrario FAILURE.
    retorna RUNNING si algún hijo está ejecutándose.
    """
    def tick(self, enemy, jugador, game_state, copa_pos):
        for child in self.children:
            status = child.tick(enemy, jugador, game_state, copa_pos)
            if status == "SUCCESS":
                self.status = "SUCCESS"
                return self.status
            if status == "RUNNING":
                self.status = "RUNNING"
                return self.status
        self.status = "FAILURE"
        return self.status

class Action(Node):
    """clase base para nodo de acción."""
    def __init__(self, name="Action"):
        super().__init__(name)

class Condition(Node):
    """clase base para nodo de condición."""
    def __init__(self, name="Condition"):
        super().__init__(name)

#nodos y condiciones 
class JugadorExiste(Condition):
    """Verifica si existe un jugador en el juego"""
    def tick(self, enemy, jugador, game_state, copa_pos):
        if jugador is not None:
            self.status = "SUCCESS"
            return self.status
        self.status = "FAILURE"
        return self.status

class EnemigoRecibioDano(Condition):
    """Verifica si el enemigo recibió daño recientemente"""
    def tick(self, enemy, jugador, game_state, copa_pos):
        if enemy.target_player_on_hit:
            self.status = "SUCCESS"
            return self.status
        self.status = "FAILURE"
        return self.status

class JugadorEnRangoVision(Condition):
    """Verifica si el jugador está dentro del rango de visión del enemigo"""
    def tick(self, enemy, jugador, game_state, copa_pos):
        if jugador is None:
            self.status = "FAILURE"
            return self.status
        distancia_al_jugador = math.sqrt(
            (enemy.rect.centerx - jugador.rect.centerx) ** 2 + (enemy.rect.centery - jugador.rect.centery) ** 2)
        if distancia_al_jugador < enemy.rango_vision:
            self.status = "SUCCESS"
            return self.status
        self.status = "FAILURE"
        return self.status

class JugadorFueraRangoVision(Condition):
    """Verifica si el jugador está fuera del rango de visión del enemigo"""
    def tick(self, enemy, jugador, game_state, copa_pos):
        if jugador is None:
            self.status = "SUCCESS" 
            return self.status
        distancia_al_jugador = math.sqrt(
            (enemy.rect.centerx - jugador.rect.centerx) ** 2 + (enemy.rect.centery - jugador.rect.centery) ** 2)
        if distancia_al_jugador >= enemy.rango_vision:
            self.status = "SUCCESS"
            return self.status
        self.status = "FAILURE"
        return self.status

#nodos de accion
class PerseguirYAtacar(Action):
    """Acción para perseguir y atacar al jugador"""
    def tick(self, enemy, jugador, game_state, copa_pos):
        if jugador is None:
            self.status = "FAILURE"
            return self.status

        ahora = pygame.time.get_ticks()

        #recarcula el camino si es necesario
        if ahora - enemy.ultimo_path_calculado > enemy.intervalo_calculo_path or not enemy.path:
            enemy.ultimo_path_calculado = ahora

            start_grid = (enemy.rect.centerx // TILE_SIZE, enemy.rect.centery // TILE_SIZE)
            goal_grid = (jugador.rect.centerx // TILE_SIZE, jugador.rect.centery // TILE_SIZE)

            start_grid = (max(0, min(GRID_ANCHO - 1, start_grid[0])), max(0, min(GRID_ALTO - 1, start_grid[1])))
            goal_grid = (max(0, min(GRID_ANCHO - 1, goal_grid[0])), max(0, min(GRID_ALTO - 1, goal_grid[1])))

            if game_state['grid'][goal_grid[0]][goal_grid[1]] == 0:
                enemy.path = a_star(game_state['grid'], start_grid, goal_grid)
            else:
                enemy.path = None
                # busca una posicion alternativa cerca del jugador
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0), (1,1), (1,-1), (-1,1), (-1,-1)]:
                    temp_goal_grid = (goal_grid[0] + dr, goal_grid[1] + dc)
                    if 0 <= temp_goal_grid[0] < GRID_ANCHO and 0 <= temp_goal_grid[1] < GRID_ALTO and \
                       game_state['grid'][temp_goal_grid[0]][temp_goal_grid[1]] == 0:
                        enemy.path = a_star(game_state['grid'], start_grid, temp_goal_grid)
                        if enemy.path:
                            break
                if not enemy.path:
                    # busca otro camino en caso de obstaculos
                    for dr, dc in [(0, 2), (0, -2), (2, 0), (-2, 0)]:
                        temp_goal_grid = (goal_grid[0] + dr, goal_grid[1] + dc)
                        if 0 <= temp_goal_grid[0] < GRID_ANCHO and 0 <= temp_goal_grid[1] < GRID_ALTO and \
                           game_state['grid'][temp_goal_grid[0]][temp_goal_grid[1]] == 0:
                            enemy.path = a_star(game_state['grid'], start_grid, temp_goal_grid)
                            if enemy.path:
                                break

        enemy.mover_a_siguiente_paso(game_state)

        #el enemigo debe de atacar si esta en contacto con el jugador
        if enemy.rect.colliderect(jugador.rect):
            if ahora - enemy.ultimo_ataque_cuerpo_a_cuerpo > enemy.tiempo_entre_ataques_cuerpo_a_cuerpo:
                enemy.ultimo_ataque_cuerpo_a_cuerpo = ahora
                jugador.recibir_daño(ENEMY_MELEE_DAMAGE)
        
        self.status = "RUNNING"  #los ataques de los enemigos son continuos
        return self.status

class Patrullar(Action):
    """Acción para patrullar por puntos predefinidos"""
    def tick(self, enemy, jugador, game_state, copa_pos):
        ahora = pygame.time.get_ticks()

        if not enemy.patrol_points:
            enemy.generar_patrol_points(enemy.rect.centerx, enemy.rect.centery)
            self.status = "RUNNING"
            return self.status

        current_target_point = enemy.patrol_points[enemy.current_patrol_index]

        target_pixel_x = current_target_point[0] * TILE_SIZE + TILE_SIZE // 2
        target_pixel_y = current_target_point[1] * TILE_SIZE + TILE_SIZE // 2

        dist_to_patrol_point = math.sqrt(
            (enemy.rect.centerx - target_pixel_x) ** 2 + (enemy.rect.centery - target_pixel_y) ** 2)

        if dist_to_patrol_point < enemy.velocidad * 1.5:
            if ahora - enemy.last_patrol_point_reached_time > enemy.patrol_wait_time:
                enemy.current_patrol_index = (enemy.current_patrol_index + 1) % len(enemy.patrol_points)
                enemy.last_patrol_point_reached_time = ahora
                enemy.path = []
            else:
                self.status = "RUNNING"  # esperando en el punto de patrulla al jugador
                return self.status

        if not enemy.path or ahora - enemy.ultimo_path_calculado > enemy.intervalo_calculo_path:
            enemy.ultimo_path_calculado = ahora

            start_grid = (enemy.rect.centerx // TILE_SIZE, enemy.rect.centery // TILE_SIZE)
            start_grid = (max(0, min(GRID_ANCHO - 1, start_grid[0])), max(0, min(GRID_ALTO - 1, start_grid[1])))

            current_target_point = (
            max(0, min(GRID_ANCHO - 1, current_target_point[0])), max(0, min(GRID_ALTO - 1, current_target_point[1])))

            enemy.path = a_star(game_state['grid'], start_grid, current_target_point)

            if not enemy.path:
                enemy.current_patrol_index = (enemy.current_patrol_index + 1) % len(enemy.patrol_points)
                enemy.last_patrol_point_reached_time = ahora
                self.status = "RUNNING"
                return self.status

        enemy.mover_a_siguiente_paso(game_state)
        self.status = "RUNNING"  #patrullar siempre sera una accion continua de los enemigos 
        return self.status

class PatrullarAlrededorCopa(Action):
    """Acción para patrullar alrededor de la copa del tesoro"""
    def tick(self, enemy, jugador, game_state, copa_pos):
        if copa_pos is None:
            self.status = "FAILURE"
            return self.status

        ahora = pygame.time.get_ticks()

        if not enemy.patrol_points or ahora - enemy.last_patrol_point_reached_time > enemy.patrol_wait_time:
            enemy.generar_patrol_points(copa_pos[0], copa_pos[1], num_points=3, patrol_radius=150)
            enemy.last_patrol_point_reached_time = ahora
            enemy.path = []
            self.status = "RUNNING"
            return self.status

        current_target_point = enemy.patrol_points[enemy.current_patrol_index]

        target_pixel_x = current_target_point[0] * TILE_SIZE + TILE_SIZE // 2
        target_pixel_y = current_target_point[1] * TILE_SIZE + TILE_SIZE // 2

        dist_to_patrol_point = math.sqrt(
            (enemy.rect.centerx - target_pixel_x) ** 2 + (enemy.rect.centery - target_pixel_y) ** 2)

        if dist_to_patrol_point < enemy.velocidad * 1.5:
            enemy.current_patrol_index = (enemy.current_patrol_index + 1) % len(enemy.patrol_points)
            enemy.last_patrol_point_reached_time = ahora
            enemy.path = []
            self.status = "RUNNING"
            return self.status

        if not enemy.path or ahora - enemy.ultimo_path_calculado > enemy.intervalo_calculo_path:
            enemy.ultimo_path_calculado = ahora

            start_grid = (enemy.rect.centerx // TILE_SIZE, enemy.rect.centery // TILE_SIZE)
            start_grid = (max(0, min(GRID_ANCHO - 1, start_grid[0])), max(0, min(GRID_ALTO - 1, start_grid[1])))

            current_target_point = (
            max(0, min(GRID_ANCHO - 1, current_target_point[0])), max(0, min(GRID_ALTO - 1, current_target_point[1])))

            enemy.path = a_star(game_state['grid'], start_grid, current_target_point)

            if not enemy.path:
                enemy.current_patrol_index = (enemy.current_patrol_index + 1) % len(enemy.patrol_points)
                enemy.last_patrol_point_reached_time = ahora
                self.status = "RUNNING"
                return self.status

        enemy.mover_a_siguiente_paso(game_state)
        self.status = "RUNNING"
        return self.status