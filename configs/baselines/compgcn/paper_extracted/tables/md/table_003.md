# table_003

**Caption**: Table 3: Link prediction performance of COMPGCN and several recent models on FB15k-237 and WN18RR datasets. The results of all the baseline methods are taken directly from the previous papers $\because$ indicates missing values). We find that COMPGCN outperforms all the existing methods on 4 out of 5 metrics on FB15k-237 and 3 out of 5 metrics on WN18RR. Please refer to Section 6.1 for more deta

(Note: rowspan/colspan may not be represented perfectly in this Markdown view.)

|  | FB15k-237 | WN18RR |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MRR | MR | H@10 | H@3 | H@1 | MRR | MR | H@10 | H@3 | H@1 |  |
| TransE (Bordes et al., 2013) | .294 | 357 | .465 | - | - | .226 | 3384 | .501 | - | - |
| DistMult (Yang et al., 2014) | .241 | 254 | .419 | .263 | .155 | .43 | 5110 | .49 | .44 | .39 |
| ComplEx (Trouillon et al, 2016) | .247 | 339 | .428 | .275 | .158 | .44 | 5261 | .51 | .46 | .41 |
| R-GCN (Schlichtkrull et al, 2017) | .248 | - | .417 |  | .151 | - | - | - |  | - |
| KBGAN (Cai & Wang, 2018) | .278 | - | .458 |  | - | .214 | - | .472 | - | - |
| ConvE (Dettmers et al., 2018) | .325 | 244 | .501 | .356 | .237 | .43 | 4187 | .52 | .44 | .40 |
| ConvKB (Nguyen et al., 2018) | .243 | 311 | .421 | .371 | .155 | .249 | 3324 | .524 | .417 | .057 |
| SACN (Shang et al., 2019) | .35 | - | .54 | .39 | .26 | .47 | - | .54 | .48 | .43 |
| HypER (Balažević et al., 2019) | .341 | 250 | .520 | .376 | .252 | .465 | 5798 | .522 | .477 | .436 |
| RotatE (Sun et al., 2019) | .338 | 177 | .533 | .375 | .241 | .476 | 3340 | .571 | .492 | .428 |
| ConvR (Jiang et al., 2019) | .350 | - | .528 | .385 | .261 | .475 | - | .537 | .489 | .443 |
| VR-GCN (Ye et al., 2019) | .248 | - | .432 | .272 | .159 | - | - | - | - | - |
| CoMPGCN (Proposed Method) | .355 | 197 | .535 | .390 | .264 | .479 | 3533 | .546 | .494 | .443 |
