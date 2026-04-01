# table_004

**Caption**: Table 4: Performance on link prediction task evaluated on FB15k-237 dataset. $\mathbf { \boldsymbol { X } } + \mathbf { \boldsymbol { M } }$ (Y) denotes that method $\mathbf { M }$ is used for obtaining entity (and relation) embeddings with $\mathrm { X }$ as the scoring function. In the case of COMPGCN, Y denotes the composition operator used. $\boldsymbol { B }$ indicates the number of relatio

(Note: rowspan/colspan may not be represented perfectly in this Markdown view.)

| Scoring Function (=X) → | TransE | DistMult | ConvE |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Methods ↓ | MRR | MR | H@ 10 | MRR | MR | H@10 | MRR | MR | H@10 |
| X | 0.294 | 357 | 0.465 | 0.241 | 354 | 0.419 | 0.325 | 244 | 0.501 |
| X +D-GCN | 0.299 | 351 | 0.469 | 0.321 | 225 | 0.497 | 0.344 | 200 | 0.524 |
| X+R-GCN | 0.281 | 325 | 0.443 | 0.324 | 230 | 0.499 | 0.342 | 197 | 0.524 |
| X + W-GCN | 0.267 | 1520 | 0.444 | 0.324 | 229 | 0.504 | 0.344 | 201 | 0.525 |
| X + CoMPGCN (Sub) | 0.335 | 194 | 0.514 | 0.336 | 231 | 0.513 | 0.352 | 199 | 0.530 |
| X + CoMPGCN (Mult) | 0.337 | 233 | 0.515 | 0.338 | 200 | 0.518 | 0.353 | 216 | 0.532 |
| X+ CoMPGCN (Corr) | 0.336 | 214 | 0.518 | 0.335 | 227 | 0.514 | 0.355 | 197 | 0.535 |
| X + CoMPGCN (B = 50) | 0.330 | 203 | 0.502 | 0.333 | 210 | 0.512 | 0.350 | 193 | 0.530 |
