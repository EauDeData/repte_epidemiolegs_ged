import networkx as nx
import pandas as pd
import os
import copy
from tqdm import tqdm
import numpy as np

PATH_TO_GT = './data_samples/'

SINGLE_DAY_GRAPH = 254
MISSING_GRAPHS = 11

class ErrorChecker:
    def __init__(self, csv_file_cases_reported = 'casos_gt_non_poisoned.csv'):
        graph = nx.read_graphml(os.path.join(PATH_TO_GT, 'graph.ml'))
        casos_diarios = pd.read_csv(os.path.join(PATH_TO_GT, csv_file_cases_reported))
        table = pd.read_csv(os.path.join(PATH_TO_GT, 'translate_clean.csv'))

        sinonims = {"Castelló": "Castellón / Castelló", "Bizkaia": "Vizcaya / Bizkaia",
                         "Illes Balears": "Baleares / Balears", 'Alacant': "Alicante",
           'València': "Valencia / València", "Gipuzcoa": "Guipúzcoa / Gipuzkoa", "Araba": "Álava",
                         "Girona": "Gerona / Girona", "Ourense": "Orense / Ourense",
           "A Coruña": "La Coruña / A Coruña", "Navarra": "Navarra / Nafarroa", "Lleida": "Lérida / Lleida"
                         }

        samples = casos_diarios.fecha.unique()
        graphs = []

        nodes = [graph.nodes.data()[x[0]]['nom'] for x in graph.nodes.data()]
        dict_code = {}
        for n, node in enumerate(nodes):
            node2 = node
            if node in ['Ceuta', 'Melilla']: continue
            if node in sinonims:
                node2 = sinonims[node]
            dict_code[node] = table[table['nom'] == node2]['codi'].to_list()[0]

        name2number = {graph.nodes.data()[x[0]]['nom']: x[0] for x in graph.nodes.data()}
        print("Codis de les provincies:\n\t", dict_code)
        for day in tqdm(samples, desc = 'loading graphs...'):
            graph_copia = copy.deepcopy(graph)
            casos_sampled = casos_diarios[casos_diarios['fecha'] == day]
            data_to_insert = {}
            for provincia in dict_code:
                try:
                    casos = \
                    casos_sampled[casos_sampled['provincia_iso'] == dict_code[provincia]]['num_casos'].to_list()[0]
                except:
                    casos = 0

                data_to_insert[name2number[provincia]] = casos
            data_to_insert[name2number['Ceuta']] = 0
            data_to_insert[name2number['Melilla']] = 0
            nx.set_node_attributes(graph_copia, data_to_insert, name='num_casos')

            graphs.append(graph_copia)
            self.graphs = graphs

        print(f'{len(self.graphs)} graphs loaded correctly')

    def error_checker(self, user_provided_graphs):
        if not isinstance(user_provided_graphs, list):
            raise PermissionError('Users are not permited to upload anything but lists.')

        elif not all([isinstance(g, nx.Graph) for g in user_provided_graphs]):
            raise PermissionError('Users are not permited to upload anything but graphs inside lists.')

        elif len(user_provided_graphs) != len(self.graphs):
            raise PermissionError(f'User should upload a list containing {len(self.graphs)} elements.'
                                  f'Uploaded object {type(user_provided_graphs)} contains {len(user_provided_graphs)}')

    def __call__(self, user_provided_graphs):
        return self.forward(user_provided_graphs)

    def forward(self, user_provided_graphs):
        self.error_checker(user_provided_graphs)
        allowed_error_idxs = [SINGLE_DAY_GRAPH] + list(range(len(self.graphs) - MISSING_GRAPHS, len(self.graphs)))
        errors = [0, 0, 0]

        for num, (g1, g2) in enumerate(zip(self.graphs, user_provided_graphs)):
            g1_cases = {x[0]: g1.nodes.data()[x[0]]['num_casos'] for x in g1.nodes.data()}
            g2_cases = {x[0]: g2.nodes.data()[x[0]]['num_casos'] for x in g2.nodes.data()}

            g1_cases_vector = np.array([g1_cases[key] for key in sorted(list(g1_cases))])
            g2_cases_vector = np.array([g2_cases[key] for key in sorted(list(g2_cases))])

            absolute_diff = ((g1_cases_vector - g2_cases_vector) ** 2).mean()
            if (absolute_diff != 0 and
                    not (num in allowed_error_idxs)):
                raise PermissionError(f'Found non-zero mean squared error (MSE) in index {num}, '
                                      f'predictions should be placed at idxs {allowed_error_idxs}')

            if num == SINGLE_DAY_GRAPH:
                errors[0] = absolute_diff

            elif num in allowed_error_idxs[1:6]:
                errors[1] += absolute_diff

            elif num in allowed_error_idxs[1:]:
                errors[2] += absolute_diff

        return tuple([x / z for (x, z) in zip(errors, [1, 5, 11])])

if __name__ == '__main__':

    err = ErrorChecker()
    user_graph_silly = ErrorChecker('_casos_diagnostico_provincia.csv').graphs
    user_graph_silly = user_graph_silly + user_graph_silly[:MISSING_GRAPHS]
    user_graph_silly[0] = 9
    import pickle
    pickle.dump(user_graph_silly, open('../data_samples/uploader_shit.pkl', 'wb'))
    print(err(user_graph_silly))