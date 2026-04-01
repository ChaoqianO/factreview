# table_007

**Caption**: Table 6: Results on link prediction by relation category on FB15k-237 dataset. Following Wang et al. (2014a), the relations are divided into four categories: one-to-one (1-1), one-to-many (1-N), manyto-one (N-1), and many-to-many (N-N). We find that COMPGCN helps to improve performance on all types of relations compared to existing methods. Please refer to Section A.1 for more details.

(Note: rowspan/colspan may not be represented perfectly in this Markdown view.)

|  | ConvE | ConvE + W-GCN | ConvE + CoMPGCN (Corr) |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MRR | MR | H@10 | MRR | MR | H@10 | MRR | MR | H@10 |  |  |
|  | 1-1 | 0.193 | 459 | 0.385 | 0.422 | 238 | 0.547 | 0.457 | 150 | 0.604 |
|  | 1-N | 0.068 | 922 | 0.116 | 0.093 | 612 | 0.187 | 0.112 | 604 | 0.190 |
|  | N-1 | 0.438 | 123 | 0.638 | 0.454 | 101 | 0.647 | 0.471 | 99 | 0.656 |
|  | N-N | 0.246 | 189 | 0.436 | 0.261 | 169 | 0.459 | 0.275 | 179 | 0.474 |
|  | 1-1 | 0.177 | 402 | 0.391 | 0.406 | 319 | 0.531 | 0.453 | 193 | 0.589 |
|  | 1-N | 0.756 | 66 | 0.867 | 0.771 | 43 | 0.875 | 0.779 | 34 | 0.885 |
|  | N-1 | 0.049 | 783 | 0.09 | 0.068 | 747 | 0.139 | 0.076 | 792 | 0.151 |
|  | N-N | 0.369 | 119 | 0.587 | 0.385 | 107 | 0.607 | 0.395 | 102 | 0.616 |
