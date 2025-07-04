#FELIX ANTONIO MERCEDES MERCEDES
#21-EISN-2-047
import heapq

def heuristic(a, b):
    #funcion de heuristica para el algoritmo A*
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star(grid, start, goal):

    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    #verificamos que A* este dentro de los limites que necesitamos 
    if not (0 <= start[0] < rows and 0 <= start[1] < cols and
            0 <= goal[0] < rows and 0 <= goal[1] < cols):
        return None

    
    if grid[goal[0]][goal[1]] == 1:
        return None

    #iniciamos la estructura de datos para el A*
    open_set = [(0, start)]
    came_from = {}
    g_score = {(r, c): float('inf') for r in range(rows) for c in range(cols)}
    g_score[start] = 0
    f_score = {(r, c): float('inf') for r in range(rows) for c in range(cols)}
    f_score[start] = heuristic(start, goal)

    open_set_hash = {start}

    while open_set:
        current_f, current = heapq.heappop(open_set)
        open_set_hash.remove(current)

        #si llega al objetivo 
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = (current[0] + dr, current[1] + dc)

            if 0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols and grid[neighbor[0]][neighbor[1]] == 0:
                tentative_g_score = g_score[current] + 1

                if tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
                        open_set_hash.add(neighbor)
    

    return None