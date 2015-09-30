"""Utilities for reading/writing Yed diagrams.

Need to read a state chart into a nx.MultiDiGraph.
g will have nodes as strings OR MultiDiGraph, and edges as strings.

http://networkx.github.com/documentation/latest/tutorial/index.html
http://graphml.graphdrawing.org/primer/graphml-primer.html
http://docs.yworks.com/yfiles/doc/developers-guide/graphml.html

How Yed uses GraphML:
 - node and edge labels are contained in GraphML data tags of
   yfiles.type "nodegraphics" and "edgegraphics"
   - the label strings are in NodeLabel/EdgeLabel tag text
 - subgraphs are contained within nodes of yfiles.foldertype "group"
    or "folder" as graph tags, 
    - there are two 'GroupNodes' within the "nodegraphics" data
    - one has <State closed="false" and the other "true" for displaying
      different graphics when the group is closed/open
    - for the graph "name" we want the open one I think, taking the label
      from the NodeLabel within
    - edges for subgraphs may appear in outer graphs if the subgraph is "open"
       so need to read nodes and structure before edges, and handle edges appearing
       anywhere in the graph
    - the subgraph is identified by the node containing it
 - 

How to encode the statechart as nx.MultiDiGraph:
 - {
 - nodes/edge identifiers are by default strings, we can use the graphml identifiers
 - data is stored in dictionaries associated with the node/edge
   - store label as 'label' attribute
 - no standard way to represent hierarchical graphs
 - use a "flat" representation of the graph with hierarchy represented by node attributes
   - record hierarchy as 'children' attribute (set of nodes)

"""

import networkx as nx
from networkx.readwrite.graphml import GraphMLReader
from xml.etree.ElementTree import Element, ElementTree, tostring

import logging
log = logging.getLogger("yed_graphml")


class YedGraphMLReader(GraphMLReader):
    """
    """

    def decode_data_elements(self, graphml_keys, obj_xml):
        """Overridden to add GroupNode to the list of yfiles node_types
        to look for node labels/geometry.
        """
        data = {}
        for data_element in obj_xml.findall("{%s}data" % self.NS_GRAPHML): 
            key = data_element.get("key")
            try:
                data_name=graphml_keys[key]['name']
                data_type=graphml_keys[key]['type']
            except KeyError:
                raise nx.NetworkXError("Bad GraphML data: no key %s"%key)
            text=data_element.text
            # assume anything with subelements is a yfiles extension
            if text is not None and len(list(data_element))==0:
                if data_type==bool:
                    data[data_name] = self.convert_bool[text]
                else:
                    data[data_name] = data_type(text)
            elif len(list(data_element)) > 0:
                # Assume yfiles as subelements, try to extract node_label
                node_label = None
                for node_type in ['ShapeNode', 'SVGNode', 'ImageNode', 'GroupNode']:
                    geometry = data_element.find(".//{%s}%s/{%s}Geometry" % 
                                (self.NS_Y, node_type, self.NS_Y))
                    if geometry is not None:
                        data['x'] = geometry.get('x')
                        data['y'] = geometry.get('y')
                    if node_label is None:
                        node_label = data_element.find(".//{%s}%s/{%s}NodeLabel" % 
                                (self.NS_Y, node_type, self.NS_Y))
                if node_label is not None:
                    data['label'] = node_label.text
                edge_label = None
                for edge_type in ['PolyLineEdge', 'SplineEdge']:
                    label = data_element.find(".//{%s}%s/{%s}EdgeLabel" %
                            (self.NS_Y, edge_type, self.NS_Y))
                    if label is not None:
                        edge_label = label
                if edge_label is not None:
                    data['label'] = edge_label.text
        return data

    def add_node(self, G, node_xml, graphml_keys):
        GraphMLReader.add_node(self, G, node_xml, graphml_keys)
        # record node as child of G
        node_id = self.node_type(node_xml.get("id"))
        G.graph.setdefault('children',set()).add(node_id)
        # if node has subgraph recurse
        # Note: this involves creating a new graph only to be thrown
        #  away and could be avoided by overriding make_graph()
        graph_xml = node_xml.find("{%s}graph" % self.NS_GRAPHML)
        if graph_xml:
            G2 = self.make_graph(graph_xml, graphml_keys, {})
            children = G.node[node_id]['children'] = set()
            for (node, data) in G2.nodes(data=True):
                G.add_node(node, data)
                if 'parent' not in data:
                    data['parent'] = node_id
                    children.add(node)
            G.add_edges_from(G2.edges(data=True))


def read_file(path):
    reader = YedGraphMLReader()
    with open(path, 'rb') as fp:
        graphs = list(reader(fp))
        return graphs

if __name__ == "__main__":
    graphs = read_file("../examples/cvm.graphml")
    G = graphs[0]
    print "graph: %s" % G.graph
    print "nodes: %s" % "\n,".join(["%s=%r" % (n,d) for n,d in G.nodes(data=True)])
    print "len(edges) = %s" % len(G.edges())
    print "edges: "+ "\n,".join([repr(e) for e in G.edges(data=True)])
