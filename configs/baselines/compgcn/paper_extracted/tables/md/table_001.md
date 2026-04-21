# table_001

**Caption**: Table 1: Comparison of our proposed method, COMPGCN with other Graph Convolutional methods. Here, $K$ denotes the number of layers in the model, $d$ is the embedding dimension, $\boldsymbol { B }$ represents the number of bases and $| \mathcal { R } |$ indicates the total number of relations in the graph. Overall, COMPGCN is most comprehensive and is more parameter efficient than methods which e

| Methods | Node Embeddings | Directions | Relations | Relation Embeddings | Number of Parameters |
| --- | --- | --- | --- | --- | --- |
| GCN Kipf & Welling (2016) | √ |  |  |  | O(Kd2) |
| Directed-GCN Marcheggiani & Titov (2017) | ✓ | √ |  |  | O(Kd2)) |
| Weighted-GCN Shang et al. (2019) | √ |  | √ |  | O(Kd2 + K\|R\|) |
| Relational-GCN Schlichtkrull et al. (2017) | √ | √ | ✓ |  | O(BKd2 + BK\|R\|) |
| CoMPGCN (Proposed Method) | √ | √ | √ | √ | O(Kd2 + Bd + B\|R\|) |
