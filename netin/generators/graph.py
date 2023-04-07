import time
from collections import Counter
from typing import Union, Set

import networkx as nx
import numpy as np

from netin.utils import constants as const
from netin.utils import validator as val


class Graph(nx.Graph):

    ############################################################
    # Constructor
    ############################################################

    def __init__(self, n: int, f_m: float, seed: object = None, **attr: object):
        """

        Parameters
        ----------
        n: int
            number of nodes (minimum=2)

        f_m: float
            fraction of minorities (minimum=1/n, maximum=(n-1)/n)

        seed: object
            seed for random number generator

        attr: dict
            attributes to add to undigraph as key=value pairs

        Notes
        -----
        The initialization is a undigraph with n nodes and no edges.
        Then, everytime a node is selected as source, it gets connected to k target nodes.
        Target nodes are selected via preferential attachment (in-degree), homophily (h_**),
        and/or triadic closure (tc).

        References
        ----------
        - [1] A. L. Barabasi and R. Albert "Emergence of scaling in random networks", Science 286, pp 509-512, 1999.
        """
        super().__init__(**attr)
        self.n = n
        self.f_m = f_m
        self.seed = seed
        self.n_m = 0
        self.n_M = 0
        self.model_name = None
        self.class_attribute = None
        self.class_values = None
        self.class_labels = None
        self.node_list = None
        self.labels = None
        self._gen_start_time = None
        self._gen_duration = None

    ############################################################
    # Init
    ############################################################

    def _infer_model_name(self):
        pass

    def _validate_parameters(self):
        """
        Validates the parameters of the undigraph.
        """
        val.validate_int(self.n, minimum=2)
        val.validate_float(self.f_m, minimum=1 / self.n, maximum=(self.n - 1) / self.n)
        self.seed = self.seed if self.seed is not None else np.random.randint(0, 2 ** 32)

    def _set_class_info(self, class_attribute: str = 'm', class_values=None, class_labels=None):
        if class_labels is None:
            class_labels = [const.MAJORITY_LABEL, const.MINORITY_LABEL]
        if class_values is None:
            class_values = [0, 1]
        self.set_class_attribute(class_attribute)
        self.set_class_values(class_values)
        self.set_class_labels(class_labels)

    def get_metadata_as_dict(self) -> dict:
        """
        Returns metadata for a undigraph.
        """
        obj = {'name': self.get_model_name(),
               'class_attribute': self.get_class_attribute(),
               'class_values': self.get_class_values(),
               'class_labels': self.get_class_labels(),
               'n': self.n,
               'f_m': self.f_m,
               'seed': self.seed}
        return obj

    ############################################################
    # Getters & Setters
    ############################################################

    def set_model_name(self, model_name):
        self.model_name = model_name

    def get_model_name(self):
        return self.model_name

    def set_class_attribute(self, class_attribute):
        self.class_attribute = class_attribute

    def get_class_attribute(self):
        return self.class_attribute

    def set_class_values(self, class_values):
        self.class_values = class_values

    def get_class_values(self):
        return self.class_values

    def set_class_labels(self, class_labels):
        self.class_labels = class_labels

    def get_class_labels(self):
        return self.class_labels

    ############################################################
    # Generation
    ############################################################

    def _initialize(self, class_attribute: str = 'm', class_values: list = None, class_labels: list = None):
        """
        Initializes the random seed and the undigraph metadata.
        """
        np.random.seed(self.seed)
        self._validate_parameters()
        self._init_graph(class_attribute, class_values, class_labels)
        self._init_nodes()

    def _init_graph(self, class_attribute: str = 'm', class_values: list = None, class_labels: list = None):
        """
        Sets the name of the model, class information, and the undigraph metadata.

        Parameters
        ----------
        class_attribute: str
            name of the class attribute

        class_values: list
            list of class values

        class_labels: list
            list of class labels
        """
        self._infer_model_name()
        self._set_class_info(class_attribute, class_values, class_labels)
        self.graph = self.get_metadata_as_dict()

    def _init_nodes(self):
        """
        Initializes the list of nodes with their respective labels.
        """
        self.node_list = np.arange(self.n)
        self.n_M = int(round(self.n * (1 - self.f_m)))
        self.n_m = self.n - self.n_M
        minorities = np.random.choice(self.node_list, self.n_m, replace=False)
        self.labels = {n: int(n in minorities) for n in self.node_list}

    def get_special_targets(self, source: int) -> object:
        pass

    def get_target(self, source: Union[None, int], targets: Union[None, Set[int]],
                   special_targets: Union[None, object, iter]) -> int:
        pass

    def update_special_targets(self, idx_target: int, source: int, target: int, targets: Set[int],
                               special_targets: Union[None, object, iter]):
        pass

    def on_edge_added(self, source: int, target: int):
        pass

    def generate(self):
        self._gen_start_time = time.time()

    def _terminate(self):
        self._gen_duration = time.time() - self._gen_start_time

    ############################################################
    # Calculations
    ############################################################

    def info_params(self):
        pass

    def info_computed(self):
        pass

    def info(self, **kwargs):
        """

        Returns
        -------
        object
        """
        print("=== Params ===")
        print('n: {}'.format(self.n))
        print('f_m: {}'.format(self.f_m))
        self.info_params()
        print('seed: {}'.format(self.seed))

        print("=== Model ===")
        print('Model: {}'.format(self.get_model_name()))
        print('Class attribute: {}'.format(self.get_class_attribute()))
        print('Class values: {}'.format(self.get_class_values()))
        print('Class labels: {}'.format(self.get_class_labels()))
        print('Generation time: {} (secs)'.format(self._gen_duration))

        print("=== Computed ===")
        print(f'- is directed: {self.is_directed()}')
        print(f'- number of nodes: {self.number_of_nodes()}')
        print(f'- number of edges: {self.number_of_edges()}')
        print(f'- minimum degree: {self.calculate_minimum_degree()}')
        print(f'- fraction of minority: {self.calculate_fraction_of_minority()}')
        print(f'- edge-type counts: {self.count_edges_types()}')
        print(f"- density: {nx.density(self)}")
        try:
            print(f"- diameter: {nx.diameter(self)}")
        except Exception as ex:
            print(f"- diameter: <{ex}>")
        try:
            print(f"- average shortest path length: {nx.average_shortest_path_length(self)}")
        except Exception as ex:
            print(f"- average shortest path length: <{ex}>")
        print(f"- average degree: {sum([d for n, d in self.degree]) / self.number_of_nodes()}")
        print(f"- degree assortativity: {nx.degree_assortativity_coefficient(self)}")
        print(f"- attribute assortativity ({self.class_attribute}): "
              f"{nx.attribute_assortativity_coefficient(self, self.class_attribute)}")
        print(f"- transitivity: {nx.transitivity(self)}")
        print(f"- average clustering: {nx.average_clustering(self)}")
        self.info_computed()

    def calculate_minimum_degree(self):
        return min([d for n, d in self.degree])

    def calculate_fraction_of_minority(self):
        return sum([1 for n, obj in self.nodes(data=True) if obj[self.class_attribute] == self.class_values[
            self.class_labels.index(const.MINORITY_LABEL)]]) / self.number_of_nodes()

    def count_edges_types(self):
        return Counter([f"{self.class_labels[self.nodes[e[0]][self.class_attribute]]}"
                        f"{self.class_labels[self.nodes[e[1]][self.class_attribute]]}"
                        for e in self.edges])
