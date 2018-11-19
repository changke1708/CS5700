class Graph:
	def __init__(self, num_of_vertices):
		self._graph = []

	# Add an edge to graph
	def add_edge(self, u, v, cost):
	  self._graph.append([int(u), int(v), int(cost)])

	# find shortest distances from src to all other vertices
	# using Bellman-Ford algorithm
	def BellmanFord(self, src):
	  # Initialize distances from src to all other vertices as Infinite
	  distance = {}
	  predecessor = {}
	  for u, v, cost in self._graph:
	  	distance[u] = float('inf')
	  	distance[v] = float('inf')

	  distance[src] = 0
	  

	  # Relax all edges |V| - 1 times.
	  for i in range(len(distance) - 1):
	  	for u, v, cost in self._graph:
	  		if distance[u] != float('inf') and distance[u] + cost < distance[v]:
	  			distance[v] = distance[u] + cost
	  			predecessor[v] = u

	  
	  entries = []
	  for dest in distance:
	    next_hop = self._get_next_hop(src, dest, predecessor)
	    if next_hop is not None:
	      entries.append((dest, next_hop, distance[dest]))
	  return entries


	def _get_next_hop(self, src, dest, predecessor):
	  next_hop = dest
	  while next_hop in predecessor and predecessor[next_hop] != src:
	  	next_hop = predecessor[next_hop]
	  if next_hop in predecessor:
	  	return next_hop
	  else:
	  	return None  	  			 	