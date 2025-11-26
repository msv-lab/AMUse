from collections import defaultdict


# Recursive function to find all paths from 'node' to any leaf node
def find_paths(graph, start, path, all_paths):
    path = path + [start]
    if start not in graph or not graph[start]:  # if it's a leaf node
        all_paths.append(path)
    else:
        for node in graph[start]:
            find_paths(graph, node, path, all_paths)


# Function to find all longest paths in the graph
def longest_paths(edges):
    graph = defaultdict(list)
    # Create the graph
    for start, end in edges:
        graph[start].append(end)

    # Find all paths
    all_paths = []
    for start in graph:
        find_paths(graph, start, [], all_paths)

    # Find the longest length
    max_length = max(len(path) for path in all_paths)
    # Filter paths that are the longest
    longest_paths = [path for path in all_paths if len(path) == max_length]

    return longest_paths
