import argparse
import json
import jsonpickle
import itertools
from matching.games import StableRoommates
from concurrent import futures

class Node:
  def __init__(self, players, average_elo):
    self.players = players
    self.average_elo = average_elo
    self.connected_nodes = set()
    self.visited = False
  def add_connection(self, node):
    self.connected_nodes.add(node)


class TeamGraph:
  def __init__(self):
    self.nodes = set()
  def create_node(self, combination):
    #calculate elo
    elo = sum(player["elo"] for player in combination) / len(combination)
    #create node
    new_node = Node(combination, elo)
    #add edges to node if no shared players
    for node in self.nodes:
      team_1 = [player["name"] for player in combination]
      team_2 = [player["name"] for player in node.players]
      if not any(x in team_1 for x in team_2):
        node.add_connection(new_node)
        new_node.add_connection(node)
    #last add to set
    self.nodes.add(new_node)
  def find_cliques_of_size(self, size):
    cliques = []
    k = 2
    #dfs to find all unique edges
    for node in self.nodes:
      node.visited = True
      for connected_node in node.connected_nodes: 
        if connected_node.visited:
          continue
        cliques.append(set({node, connected_node}))
    while cliques and k < size:
      cliques_1 = set()
      for u,v in itertools.combinations(cliques, 2):
        w = u ^ v
        if len(w) == 2 and (list(w)[1]) in list(w)[0].connected_nodes:
          cliques_1.add(tuple( u | w))

      #remove duplicates
      cliques = list(map(set, cliques_1))
      k+=1
    return cliques
    
  def print_graph(self):
    for node in self.nodes:
      print(node.players)
      for connected_node in node.connected_nodes:
        print(connected_node.players)
      print("======================================")


def prune_bad_combinations(combinations, elo_range):
  combination_elo_list = []
  for combination in combinations:
    elo = sum(player["elo"] for player in combination) / len(combination)
    combination_elo_list.append([combination, elo])
  combination_elo_list.sort(key=lambda x:x[1])
    
  elements_to_drop = []
  for i in range(len(combination_elo_list)):
    valid_left = False
    valid_right = False
    current_elo = combination_elo_list[i][1]
    team_1 = combination_elo_list[i][0]
    team_1_players = set(player["name"] for player in team_1)
    #check backwards
    moving_index = i
    while moving_index > 0:
      moving_index -= 1
      team_2 = combination_elo_list[moving_index][0]
      team_2_players = set(player["name"] for player in team_2)
      if not len(team_1_players & team_2_players):
        if current_elo - combination_elo_list[moving_index][1] < elo_range:
          valid_left = True
        break
    #check forwards
    moving_index = i
    while moving_index < len(combination_elo_list) - 1:
      moving_index += 1
      team_2 = combination_elo_list[moving_index][0]
      team_2_players = set(player["name"] for player in team_2)
      if not len(team_1_players & team_2_players):
        if combination_elo_list[moving_index][1] - current_elo< elo_range:
          valid_right = True
        break
    if not valid_left and not valid_right:
      #no fair match for this team
      elements_to_drop.append(combination_elo_list[i][0])
  for i in elements_to_drop:
    combinations.remove(i)
    for player in i:
      print(player)
    print ("=========")
  return combinations

def calculate_matches(clique):
  clique = list(clique)
  preferences_dict = {}
  for node in clique:
    node_elo_diff_list = []
    for node2 in clique:
      if node == node2:
        continue
      node_elo_diff_list.append([node2, abs(node.average_elo - node2.average_elo)])
    node_elo_diff_list.sort(key=lambda x:x[1])
    preferences_dict[node] = [item[0] for item in node_elo_diff_list]
  matches = StableRoommates.create_from_dictionary(preferences_dict)
  return matches.solve()

def build_graph(players, size, elo_range):
  team_graph = TeamGraph()
  combinations = list(itertools.combinations(players,size))
  combinations = prune_bad_combinations(combinations, elo_range)
  for combination in combinations:
    team_graph.create_node(combination)
  return team_graph

def parse_input(input_file):
  with open(input_file) as f:
    player_dict = json.load(f)
  return player_dict

def execute(input_file, output, elo_range):
  player_dict = parse_input(input_file)
  team_graph = build_graph(player_dict["players"],2, elo_range)
  cliques = team_graph.find_cliques_of_size(6)
  pairings = []
  for clique in cliques:
    matches = calculate_matches(clique)
    match_set = set()
    worst_elo_delta = 0
    for k,v in matches.items():
      if k.name.average_elo < v.name.average_elo:
        match_set.add((k.name, v.name))
      else:
        match_set.add((v.name, k.name))
      if abs(k.name.average_elo - v.name.average_elo) > worst_elo_delta:
        worst_elo_delta = abs(k.name.average_elo - v.name.average_elo)
    pairings.append([match_set, worst_elo_delta])
  #sort by best worst match
  pairings.sort(key=lambda x:x[1])
  for pairing in pairings:
    for match in pairing[0]:
      for node in match:
        print(node.players)
        print(node.average_elo)
        print("---------------")
      print(pairing[1])
    print("==============")
    
      
  #for clique in cliques:
  #  for node in clique:
  #    print(node.players)
  #  print ("==================")
  print(len(cliques))
  print(len(team_graph.nodes))
      

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Generate best possible random pairs from a group to maximize match quality")
  parser.add_argument("-e", "--elo", help="Elo range that constitutes a bad matchup", default=25)
  parser.add_argument("input", help="Json containing player names and ratings")
  parser.add_argument("output", help="Name of file to store output to")
  args = parser.parse_args()

  execute(args.input, args.output, args.elo)

