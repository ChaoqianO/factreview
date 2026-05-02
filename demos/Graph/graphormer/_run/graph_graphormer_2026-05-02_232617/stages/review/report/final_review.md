[Do Transformers Really Perform Bad for Graph Representation?]

## **1. Metadata**
- **Title**: Do Transformers Really Perform Bad for Graph Representation?
- **Task**: Graph representation learning; graph-level prediction (regression/classification) on PCQM4M-LSC, OGBG-MolPCBA, OGBG-MolHIV, and ZINC.
- **Code**: https://github.com/Microsoft/Graphormer

## **2. Technical Positioning**
Graphormer augments standard Transformer with centrality, shortest-path spatial, and edge attention-bias encodings for graph-level representation learning.
| **Research domain** | **Method** | **Standard Transformer backbone** | **Structural node centrality encoding** | **Shortest-path spatial bias in attention** | **Edge-feature encoding via attention bias** |
| --- | --- | --- | --- | --- | --- |
| Graph representation learning | GT | √ | × | × | × |
| Graph representation learning | GIN-vN | × | × | × | × |
| Graph representation learning | DeeperGCN-vN | × | × | × | × |
| This Work | Graphormer | √ | √ | √ | √ |

## **3. Claims**
**Paper scope:** Standard-Transformer-based graph representation model with structural encodings and expressiveness analysis.
**Evaluation scope:** Graph-level benchmarks (PCQM4M-LSC, MolPCBA, MolHIV, ZINC) and ablations on PCQM4M-LSC.
(Status legend: <span style="color: green;">✓ Supported</span>, <span style="color: #E6B800;">⚠ Partially supported</span>, <span style="color: red;">✗ In conflict</span>.)
| **Claim** | **Evidence** | **Assessment** | **Status** | **Location** |
|---|---|---|---|---|
| Graphormer achieves state-of-the-art results on multiple graph-level benchmarks. | Table 1: Graphormer validate MAE 0.1234 vs prior best GIN-vN 0.1395 on PCQM4M-LSC. Tables 2/3/4: Graphormer-FLAG 31.39 AP (MolPCBA), 80.51 AUC (MolHIV), GraphormerSLIM 0.122 MAE (ZINC), each best in listed rows. | The paper cites experimental tables or figures as evidence. Concrete numeric values are present in the evidence. The cited location is Abstract; Sec. 1; Sec. 4.1 Table 1; Sec. 4.2 Tables 2–4. | <span style="color: green;">✓ Supported</span> | Abstract; Sec. 1; Sec. 4.1 Table 1; Sec. 4.2 Tables 2–4 |
| Structural encodings (centrality, spatial, edge attention bias) are effective for Transformer on graphs. | Table 5 ablation: no encoding 0.2276; +Laplacian PE 0.1483; +Spatial 0.1427; +Spatial+Centrality 0.1396; +edge via node 0.1328; +edge via Aggr 0.1327; +edge via attn bias 0.1304 (best). | The paper cites experimental tables or figures as evidence. Concrete numeric values are present in the evidence. The cited location is Sec. 3.1; Sec. 4.3; Table 5. | <span style="color: green;">✓ Supported</span> | Sec. 3.1; Sec. 4.3; Table 5 |
| Graphormer can represent AGGREGATE/COMBINE of popular GNNs and can exceed 1-WL limits with SPD encoding. | Fact 1 states representability for GIN/GCN/GraphSAGE; proof sketch in Sec. 3.3 and details in Appendix A.2. Appendix A.1 (Figure 2) gives an example where SPD distinguishes graphs not distinguished by 1-WL. | The paper cites experimental tables or figures as evidence. Concrete numeric values are present in the evidence. The cited location is Sec. 3.3 (Fact 1); Appendix A.1–A.2; Figure 2. | <span style="color: green;">✓ Supported</span> | Sec. 3.3 (Fact 1); Appendix A.1–A.2; Figure 2 |

## **4. Summary**
This paper presents Graphormer, a graph representation architecture built on standard Transformer layers plus three structural encodings (degree-based centrality, shortest-path spatial bias, and edge-feature attention bias). It also provides expressiveness arguments connecting Graphormer to popular GNN formulations and reports consistent gains on PCQM4M-LSC, MolPCBA, MolHIV, and ZINC benchmarks.

**Strengths:** - Clear method design with explicit equations for each structural encoding and integration into attention.
- Broad empirical evaluation across multiple public graph-level leaderboards with direct baseline comparisons.
- Includes ablation studies isolating node-relation, centrality, and edge-encoding effects.
- Provides theoretical positioning (Fact 1/Fact 2) with appendix proof sketches and examples.

**Weaknesses:** - Strongest competition statement includes an ensemble system, while single-model and ensemble settings are mixed in narrative.
- Full theoretical details are deferred to appendix; main text gives concise sketches.
- Quadratic self-attention complexity is acknowledged as a scalability limitation for large graphs.
- Some claims on over-smoothing are stated qualitatively without a dedicated quantitative table in the main sections.

## **5. Experiment**
### **Main Result**
(Status legend: <span style="color: green;">✓ Supported</span>, <span style="color: #E6B800;">⚠ Inconclusive</span>, <span style="color: red;">✗ In conflict</span>.)
**Location:** Section 4.1 Table 1 (PCQM4M-LSC); Section 4.2 Tables 2–4 (MolPCBA, MolHIV, ZINC).
| **Task** | **Dataset** | **Metric** | **Best Baseline** | **Paper Result** | **Difference (Δ)** | **Evaluation Status** |
| --- | --- | --- | --- | --- | --- | --- |
| Graph-level regression | PCQM4M-LSC | validate MAE | 0.14(GIN-vN) | Graphormer: 0.1234 | <span style="color: red;">-0.0161</span> | <span style="color: #E6B800;">⚠()</span> |
| Graph-level regression | PCQM4M-LSC | validate MAE | 0.14(GIN-vN) | GraphormerSMALL: 0.1264 | <span style="color: red;">-0.0131</span> | <span style="color: #E6B800;">⚠()</span> |
| Graph-level classification | OGBG-MolPCBA | AP (%) | -1.28(GINE-APPNP ±) | Graphormer-FLAG: 31.39±0.32 | <span style="color: green;">+1.60</span> | <span style="color: #E6B800;">⚠()</span> |
| Graph-level classification | OGBG-MolHIV | AUC (%) | -0.28(DGN ±) | Graphormer-FLAG: 80.51±0.53 | <span style="color: green;">+0.81</span> | <span style="color: #E6B800;">⚠()</span> |
| Graph-level regression | ZINC | test MAE | 0.006(SAN ±) | GraphormerSLIM: 0.122±0.006 | <span style="color: red;">-0.017</span> | <span style="color: #E6B800;">⚠()</span> |
### **Ablation Result**
(Status legend: <span style="color: green;">✓ Supported</span>, <span style="color: #E6B800;">⚠ Inconclusive</span>, <span style="color: red;">✗ In conflict</span>.)
**Location:** Section 4.3 Ablation Studies, Table 5 on PCQM4M-LSC (metric: valid MAE).
| **Ablation Dimension** | **Configuration** | **Full Model** | **Paper Result** | **Difference (Δ)** | **Evaluation Status** |
| --- | --- | --- | --- | --- | --- |
| Optimal setup | Spatial + Centrality + via attn bias (Eq.7) | 0.1304 | 0.1304 | **0** | <span style="color: #E6B800;">⚠()</span> |
| Edge Encoding | via node | 0.1304 | 0.1328 | <span style="color: red;">+0.0024</span> | <span style="color: #E6B800;">⚠()</span> |
| Edge Encoding | via Aggr | 0.1304 | 0.1327 | <span style="color: red;">+0.0023</span> | <span style="color: #E6B800;">⚠()</span> |
| Centrality Encoding | remove centrality (Spatial only row) | 0.1304 | 0.1427 | <span style="color: red;">+0.0123</span> | <span style="color: #E6B800;">⚠()</span> |
| Node Relation Encoding | Laplacian PE only | 0.1304 | 0.1483 | <span style="color: red;">+0.0179</span> | <span style="color: #E6B800;">⚠()</span> |
| Structural encodings | none | 0.1304 | 0.2276 | <span style="color: red;">+0.0972</span> | <span style="color: #E6B800;">⚠()</span> |