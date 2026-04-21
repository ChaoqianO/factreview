# COMPOSITION-BASED MULTI-RELATIONAL GRAPH CONVOLUTIONAL NETWORKS

Shikhar Vashishth∗ † 1,2 Soumya Sanyal∗1 Vikram Nitin† 3 Partha Talukdar1 1Indian Institute of Science, 2Carnegie Mellon University, 3Columbia University svashish@cs.cmu.edu, {shikhar,soumyasanyal,ppt}@iisc.ac.in, vikram.nitin@columbia.edu

# ABSTRACT

Graph Convolutional Networks (GCNs) have recently been shown to be quite successful in modeling graph-structured data. However, the primary focus has been on handling simple undirected graphs. Multi-relational graphs are a more general and prevalent form of graphs where each edge has a label and direction associated with it. Most of the existing approaches to handle such graphs suffer from over-parameterization and are restricted to learning representations of nodes only. In this paper, we propose COMPGCN, a novel Graph Convolutional framework which jointly embeds both nodes and relations in a relational graph. COMPGCN leverages a variety of entity-relation composition operations from Knowledge Graph Embedding techniques and scales with the number of relations. It also generalizes several of the existing multi-relational GCN methods. We evaluate our proposed method on multiple tasks such as node classification, link prediction, and graph classification, and achieve demonstrably superior results. We make the source code of COMPGCN available to foster reproducible research.

# 1 INTRODUCTION

Graphs are one of the most expressive data-structures which have been used to model a variety of problems. Traditional neural network architectures like Convolutional Neural Networks (Krizhevsky et al., 2012) and Recurrent Neural Networks (Hochreiter & Schmidhuber, 1997) are constrained to handle only Euclidean data. Recently, Graph Convolutional Networks (GCNs) (Bruna et al., 2013; Defferrard et al., 2016) have been proposed to address this shortcoming, and have been successfully applied to several domains such as social networks (Hamilton et al., 2017), knowledge graphs (Schlichtkrull et al., 2017), natural language processing (Marcheggiani & Titov, 2017), drug discovery (Ramsundar et al., 2019), crystal property prediction (Sanyal et al., 2018), and natural sciences (Fout et al., 2017).

However, most of the existing research on GCNs (Kipf & Welling, 2016; Hamilton et al., 2017; Velickovi ˇ c et al., 2018) have focused on learning representations of nodes in simple undirected ´ graphs. A more general and pervasive class of graphs are multi-relational graphs1. A notable example of such graphs is knowledge graphs. Most of the existing GCN based approaches for handling relational graphs (Marcheggiani & Titov, 2017; Schlichtkrull et al., 2017) suffer from overparameterization and are limited to learning only node representations. Hence, such methods are not directly applicable for tasks such as link prediction which require relation embedding vectors. Initial attempts at learning representations for relations in graphs (Monti et al., 2018; Beck et al., 2018) have shown some performance gains on tasks like node classification and neural machine translation.

There has been extensive research on embedding Knowledge Graphs (KG) (Nickel et al., 2016; Wang et al., 2017) where representations of both nodes and relations are jointly learned. These methods are restricted to learning embeddings using link prediction objective. Even though GCNs can learn from task-specific objectives such as classification, their application has been largely restricted to non-relational graph setting. Thus, there is a need for a framework which can utilize KG embedding techniques for learning task-specific node and relation embeddings. In this paper, we propose COMPGCN, a novel GCN framework for multi-relational graphs which systematically leverages entity-relation composition operations from knowledge graph embedding techniques. COMPGCN addresses the shortcomings of previously proposed GCN models by jointly learning vector representations for both nodes and relations in the graph. An overview of COMPGCN is presented in Figure 1. The contributions of our work can be summarized as follows:

![](images/7835852cbf4b3f42590345458dc4ee80f97989c0664083df75d8c6b466cb67bb.jpg)  
Figure 1: Overview of COMPGCN. Given node and relation embeddings, COMPGCN performs a composition operation $\phi ( \cdot )$ over each edge in the neighborhood of a central node (e.g. Christopher Nolan above). The composed embeddings are then convolved with specific filters $W _ { O }$ and $W _ { I }$ for original and inverse relations respectively. We omit self-loop in the diagram for clarity. The message from all the neighbors are then aggregated to get an updated embedding of the central node. Also, the relation embeddings are transformed using a separate weight matrix. Please refer to Section 4 for details.

1. We propose COMPGCN, a novel framework for incorporating multi-relational information in Graph Convolutional Networks which leverages a variety of composition operations from knowledge graph embedding techniques to jointly embed both nodes and relations in a graph. 2. We demonstrate that COMPGCN framework generalizes several existing multi-relational GCN methods (Proposition 4.1) and also scales with the increase in number of relations in the graph (Section 6.3). 3. Through extensive experiments on tasks such as node classification, link prediction, and graph classification, we demonstrate the effectiveness of our proposed method.

The source code of COMPGCN and datasets used in the paper have been made available at http: //github.com/malllabiisc/CompGCN.

# 2 RELATED WORK

Graph Convolutional Networks: GCNs generalize Convolutional Neural Networks (CNNs) to non-Euclidean data. GCNs were first introduced by Bruna et al. (2013) and later made scalable through efficient localized filters in the spectral domain (Defferrard et al., 2016). A first-order approximation of GCNs using Chebyshev polynomials has been proposed by Kipf & Welling (2016). Recently, several of its extensions have also been formulated (Hamilton et al., 2017; Velickovi ˇ c´ et al., 2018; Xu et al., 2019). Most of the existing GCN methods follow Message Passing Neural Networks (MPNN) framework (Gilmer et al., 2017) for node aggregation. Our proposed method can be seen as an instantiation of the MPNN framework. However, it is specialized for relational graphs.

GCNs for Multi-Relational Graph: An extension of GCNs for relational graphs is proposed by Marcheggiani & Titov (2017). However, they only consider direction-specific filters and ignore relations due to over-parameterization. Schlichtkrull et al. (2017) address this shortcoming by proposing basis and block-diagonal decomposition of relation specific filters. Weighted Graph Convolutional Network (Shang et al., 2019) utilizes learnable relational specific scalar weights during GCN aggregation. While these methods show performance gains on node classification and link prediction, they are limited to embedding only the nodes of the graph. Contemporary to our work, Ye et al. (2019) have also proposed an extension of GCNs for embedding both nodes and relations in multirelational graphs. However, our proposed method is a more generic framework which can leverage any KG composition operator. We compare against their method in Section 6.1.

Knowledge Graph Embedding: Knowledge graph (KG) embedding is a widely studied field (Nickel et al., 2016; Wang et al., 2017) with application in tasks like link prediction and question answering (Bordes et al., 2014). Most of KG embedding approaches define a score function and train node and relation embeddings such that valid triples are assigned a higher score than the invalid ones. Based on the type of score function, KG embedding method are classified as translational (Bordes et al., 2013; Wang et al., 2014b), semantic matching based (Yang et al., 2014; Nickel et al., 2016) and neural network based (Socher et al., 2013; Dettmers et al., 2018). In our work, we evaluate the performance of COMPGCN on link prediction with methods of all three types.

# 3 BACKGROUND

In this section, we give a brief overview of Graph Convolutional Networks (GCNs) for undirected graphs and its extension to directed relational graphs.

GCN on Undirected Graphs: Given a graph $\mathcal { G } = ( \nu , \mathcal { E } , \pmb { x } )$ , where $\nu$ denotes the set of vertices, $\mathcal { E }$ is the set of edges, and $\pmb { \chi } \in \mathbb { R } ^ { | \nu | \times d _ { 0 } }$ represents $d _ { 0 }$ -dimensional input features of each node. The node representation obtained from a single GCN layer is defined as: $\pmb { H } = f ( \hat { A } \pmb { \chi } \pmb { W } )$ . Here, $\pmb { \hat { A } } = \pmb { \widetilde { D } } ^ { - \frac 1 2 } ( \pmb { A } + \pmb { I } ) \pmb { \widetilde { D } } ^ { - \frac 1 2 }$ is the normalized adjacency matrix with added self-connections and $\widetilde { D }$ is defined as $\begin{array} { r } { \widetilde { D } _ { i i } = \sum _ { j } ( A + I ) _ { i j } } \end{array}$ . The model parameter is denoted by $W \in \mathbb { R } ^ { d _ { 0 } \times d _ { 1 } }$ and $f$ is some activation function. The GCN representation $\pmb { H }$ encodes the immediate neighborhood of each node in the graph. For capturing multi-hop dependencies in the graph, several GCN layers can be stacked, one on the top of another as follows: $\mathbf { \tilde { { H } } } ^ { \bar { k } + 1 } = f ( \hat { A } H ^ { k } \mathbf { \bar { { W } } } ^ { \bar { k } } )$ , where $k$ denotes the number of layers, $W ^ { k } \in \mathbb { R } ^ { d _ { k } \times \mathbf { \hat { d } } _ { k + 1 } }$ is layer-specific parameter and $H ^ { 0 } = \mathcal { X }$ .

GCN on Multi-Relational Graphs: For a multi-relational graph $\mathcal { G } = ( \mathcal { V } , \mathcal { R } , \mathcal { E } , \pmb { \mathcal { X } } )$ , where $\mathcal { R }$ denotes the set of relations, and each edge $( u , v , r )$ represents that the relation $r \in \mathcal { R }$ exist from node $u$ to $v$ . The GCN formulation as devised by Marcheggiani $\&$ Titov (2017) is based on the assumption that information in a directed edge flows along both directions. Hence, for each edge $( u , v , r ) \in \mathcal { E }$ , an inverse edge $( v , u , r ^ { - 1 } )$ is included in $\mathcal { G }$ . The representations obtained after $k$ layers of directed GCN is given by

$$
\begin{array} { r } { { H } ^ { k + 1 } = f ( \hat { A } { H } ^ { k } { W } _ { r } ^ { k } ) . } \end{array}
$$

Here, $W _ { r } ^ { k }$ denotes the relation specific parameters of the model. However, the above formulation leads to over-parameterization with an increase in the number of relations and hence, Marcheggiani & Titov (2017) use direction-specific weight matrices. Schlichtkrull et al. (2017) address overparameterization by proposing basis and block-diagonal decomposition of $W _ { r } ^ { k }$ .

# 4 COMPGCN DETAILS

In this section, we provide a detailed description of our proposed method, COMPGCN. The overall architecture is shown in Figure 1. We represent a multi-relational graph by $\mathcal { G } = ( \mathcal { V } , \mathcal { R } , \mathcal { E } , \mathcal { X } , \mathcal { Z } )$ as defined in Section 3 where $\mathcal { Z } \in \mathbb { R } ^ { | \mathcal { R } | \times d _ { 0 } }$ denotes the initial relation features. Our model is motivated by the first-order approximation of GCNs using Chebyshev polynomials (Kipf & Welling, 2016). Following Marcheggiani $\&$ Titov (2017), we also allow the information in a directed edge to flow along both directions. Hence, we extend $\mathcal { E }$ and $\mathcal { R }$ with corresponding inverse edges and relations, i.e.,

$$
\mathcal { E } ^ { \prime } = \mathcal { E } \cup \{ ( v , u , r ^ { - 1 } ) \mid ( u , v , r ) \in \mathcal { E } \} \cup \{ ( u , u , \top ) \mid u \in \mathcal { V } \} \} ,
$$

and $\mathcal { R } ^ { \prime } = \mathcal { R } \cup \mathcal { R } _ { i n v } \cup \{ \top \}$ , where $\mathcal { R } _ { i n v } = \{ r ^ { - 1 } | r \in \mathscr { R } \}$ denotes the inverse relations and $\top$ indicates the self loop.

<table><tr><td>Methods</td><td>Node Embeddings</td><td>Directions</td><td>Relations</td><td>Relation Embeddings</td><td>Number of Parameters</td></tr><tr><td>GCN Kipf &amp; Welling (2016)</td><td>√</td><td></td><td></td><td></td><td>O(Kd2)</td></tr><tr><td>Directed-GCN Marcheggiani &amp; Titov (2017)</td><td>✓</td><td>√</td><td></td><td></td><td>O(Kd2))</td></tr><tr><td>Weighted-GCN Shang et al. (2019)</td><td>√</td><td></td><td>√</td><td></td><td>O(Kd2 + K|R|)</td></tr><tr><td>Relational-GCN Schlichtkrull et al. (2017)</td><td>√</td><td>√</td><td>✓</td><td></td><td>O(BKd2 + BK|R|)</td></tr><tr><td>CoMPGCN (Proposed Method)</td><td>√</td><td>√</td><td>√</td><td>√</td><td>O(Kd2 + Bd + B|R|)</td></tr></table>

Table 1: Comparison of our proposed method, COMPGCN with other Graph Convolutional methods. Here, $K$ denotes the number of layers in the model, $d$ is the embedding dimension, $\boldsymbol { B }$ represents the number of bases and $| \mathcal { R } |$ indicates the total number of relations in the graph. Overall, COMPGCN is most comprehensive and is more parameter efficient than methods which encode relation and direction information.

# 4.1 RELATION-BASED COMPOSITION

Unlike most of the existing methods which embed only nodes in the graph, COMPGCN learns a $d$ -dimensional representation $h _ { r } \in \mathbb { R } ^ { d } , \forall r \in \mathcal { R }$ along with node embeddings $h _ { v } \in \mathbb R ^ { d } , \forall v \in \mathcal { V }$ . Representing relations as vectors alleviates the problem of over-parameterization while applying GCNs on relational graphs. Further, it allows COMPGCN to exploit any available relation features $( { \mathcal { Z } } )$ as initial representations. To incorporate relation embeddings into the GCN formulation, we leverage the entity-relation composition operations used in Knowledge Graph embedding approaches (Bordes et al., 2013; Nickel et al., 2016), which are of the form

$$
\boldsymbol { e } _ { o } = \phi ( e _ { s } , e _ { r } ) .
$$

Here, $\phi : \mathbb { R } ^ { d } \times \mathbb { R } ^ { d }  \mathbb { R } ^ { d }$ is a composition operator, $s , r$ , and $o$ denote subject, relation and object in the knowledge graph and $\boldsymbol { e } _ { ( \cdot ) } \in \mathbf { \hat { \mathbb { R } } } ^ { d }$ denotes their corresponding embeddings. In this paper, we restrict ourselves to non-parameterized operations like subtraction (Bordes et al., 2013), multiplication (Yang et al., 2014) and circular-correlation (Nickel et al., 2016). However, COMPGCN can be extended to parameterized operations like Neural Tensor Networks (NTN) (Socher et al., 2013) and ConvE (Dettmers et al., 2018). We defer their analysis as future work.

As we show in Section 6, the choice of composition operation is important in deciding the quality of the learned embeddings. Hence, superior composition operations for Knowledge Graphs developed in future can be adopted to improve COMPGCN’s performance further.

# 4.2 COMPGCN UPDATE EQUATION

The GCN update equation (Eq. 1) defined in Section 3 can be re-written as

$$
h _ { v } = f \left( \sum _ { \left( u , r \right) \in \mathcal { N } \left( v \right) } W _ { r } h _ { u } \right) ,
$$

where $\mathcal { N } ( v )$ is a set of immediate neighbors of $v$ for its outgoing edges. Since this formulation suffers from over-parameterization, in COMPGCN we perform composition $( \phi )$ of a neighboring node $u$ with respect to its relation $r$ as defined above. This allows our model to be relation aware while being linear $( \mathcal { O } ( | \mathcal { R } | d ) )$ in the number of feature dimensions. Moreover, for treating original, inverse, and self edges differently, we define separate filters for each of them. The update equation of COMPGCN is given as:

$$
\pmb { h } _ { v } = f \left( \sum _ { ( u , r ) \in \mathcal { N } ( v ) } W _ { \lambda ( r ) } \phi ( \pmb { x } _ { u } , z _ { r } ) \right) ,
$$

where $\mathbf { \boldsymbol { x } } _ { u } , z _ { r }$ denotes initial features for node $u$ and relation $r$ respectively, $ { \boldsymbol { h } } _ { v }$ denotes the updated representation of node $v$ , and $W _ { \lambda ( r ) } \in \mathbb { R } ^ { d _ { 1 } \times d _ { 0 } }$ is a relation-type specific parameter. In COMPGCN, we use direction specific weights, i.e., $\lambda ( r ) = \dim ( r )$ , given as:

$$
W _ { \mathrm { d i r } ( r ) } = \left\{ \begin{array} { l l } { W _ { O } , } & { r \in \mathscr { R } } \\ { W _ { I } , } & { r \in \mathscr { R } _ { i n v } } \\ { W _ { S } , } & { r = \top ( s e l f - l o o p ) } \end{array} \right.
$$

<table><tr><td>Methods</td><td>W ()</td><td>φ(hκ, hk)</td></tr><tr><td>Kipf-GCN (Kipf &amp; Welling, 2016)</td><td>Wk</td><td>hκ</td></tr><tr><td>Relational-GCN (Schlichtkrull et al., 2017)</td><td>W </td><td>hk</td></tr><tr><td>Directed-GCN (Marcheggiani &amp; Titov, 2017)</td><td>Wkir(r)</td><td>hh</td></tr><tr><td>Weighted-GCN (Shang et al., 2019)</td><td>Wk</td><td>αkh</td></tr></table>

Table 2: Reduction of COMPGCN to several existing Graph Convolutional methods. Here, $\alpha _ { r } ^ { k }$ is a relation specific scalar, $\boldsymbol { W } _ { r } ^ { k }$ denotes a separate weight for each relation, and $W _ { \mathrm { d i r } ( r ) } ^ { k }$ r is as defined in Equation 3. Please refer to Proposition 4.1 for more details.

Further, in COMPGCN, after the node embedding update defined in Eq. 2, the relation embeddings are also transformed as follows:

$$
\begin{array} { r } { \pmb { h } _ { r } = \pmb { W } _ { \mathrm { r e l } } \pmb { z } _ { r } , } \end{array}
$$

where $W _ { \mathrm { r e l } } \in \mathbb { R } ^ { d _ { 1 } \times d _ { 0 } }$ is a learnable transformation matrix which projects all the relations to the same embedding space as nodes and allows them to be utilized in the next COMPGCN layer. In Table 1, we present a contrast between COMPGCN and other existing methods in terms of their features and parameter complexity.

Scaling with Increasing Number of Relations To ensure that COMPGCN scales with the increasing number of relations, we use a variant of the basis formulations proposed in Schlichtkrull et al. (2017). Instead of independently defining an embedding for each relation, they are expressed as a linear combination of a set of basis vectors. Formally, let $\{ \pmb { v } _ { 1 } , \pmb { v } _ { 2 } , . . . , \pmb { v } _ { B } \}$ be a set of learnable basis vectors. Then, initial relation representation is given as:

$$
z _ { r } = \sum _ { b = 1 } ^ { B } \alpha _ { b r } { v } _ { b } .
$$

Here, $\alpha _ { b r } \in \mathbb { R }$ is relation and basis specific learnable scalar weight.

On Comparison with Relational-GCN Note that this is different from the basis formulation in Schlichtkrull et al. (2017), where a separate set of basis matrices is defined for each GCN layer. In contrast, COMPGCN uses embedding vectors instead of matrices, and defines basis vectors only for the first layer. The later layers share the relations through transformations according to Equation 4. This makes our model more parameter efficient than Relational-GCN.

We can extend the formulation of Equation 2 to the case where we have $k$ -stacked COMPGCN layers. Let $\boldsymbol { h } _ { v } ^ { k + 1 }$ denote the representation of a node $v$ obtained after $k$ layers which is defined as

$$
\pmb { h } _ { v } ^ { k + 1 } = f \left( \sum _ { ( u , r ) \in \mathcal { N } ( v ) } W _ { \lambda ( r ) } ^ { k } \phi ( \pmb { h } _ { u } ^ { k } , \pmb { h } _ { r } ^ { k } ) \right) .
$$

Similarly, let $\boldsymbol { h } _ { r } ^ { k + 1 }$ denote the representation of a relation $r$ after $k$ layers. Then,

$$
\begin{array} { r } { \pmb { h } _ { r } ^ { k + 1 } = \pmb { W } _ { \mathrm { r e l } } ^ { k } \pmb { h } _ { r } ^ { k } . } \end{array}
$$

Here, $h _ { v } ^ { 0 }$ and ${ h _ { r } ^ { 0 } }$ are the initial node $( { \pmb x } _ { v } )$ and relation $\textstyle ( z _ { r } )$ features respectively.

Proposition 4.1. COMPGCN generalizes the following Graph Convolutional based methods: Kipf-GCN (Kipf & Welling, 2016), Relational GCN (Schlichtkrull et al., 2017), Directed GCN (Marcheggiani & Titov, 2017), and Weighted GCN (Shang et al., 2019).

Proof. For Kipf-GCN, this can be trivially obtained by making weights $\left( W _ { \lambda ( r ) } \right)$ and composition function $\left( \phi \right)$ relation agnostic in Equation 5, i.e., $W _ { \lambda ( r ) } = W$ and $\phi ( h _ { u } , \dot { h _ { r } } ) ~ = ~ h _ { u }$ . Similar reductions can be obtained for other methods as shown in Table 2. □

<table><tr><td rowspan="2"></td><td colspan="5">FB15k-237</td><td colspan="5">WN18RR</td></tr><tr><td>MRR</td><td>MR</td><td>H@10</td><td>H@3</td><td>H@1</td><td>MRR</td><td>MR</td><td>H@10</td><td>H@3</td><td>H@1</td></tr><tr><td>TransE (Bordes et al., 2013)</td><td>.294</td><td>357</td><td>.465</td><td>-</td><td>-</td><td>.226</td><td>3384</td><td>.501</td><td>-</td><td>-</td></tr><tr><td>DistMult (Yang et al., 2014)</td><td>.241</td><td>254</td><td>.419</td><td>.263</td><td>.155</td><td>.43</td><td>5110</td><td>.49</td><td>.44</td><td>.39</td></tr><tr><td>ComplEx (Trouillon et al, 2016)</td><td>.247</td><td>339</td><td>.428</td><td>.275</td><td>.158</td><td>.44</td><td>5261</td><td>.51</td><td>.46</td><td>.41</td></tr><tr><td>R-GCN (Schlichtkrull et al, 2017)</td><td>.248</td><td>-</td><td>.417</td><td></td><td>.151</td><td>-</td><td>-</td><td>-</td><td></td><td>-</td></tr><tr><td>KBGAN (Cai &amp; Wang, 2018)</td><td>.278</td><td>-</td><td>.458</td><td></td><td>-</td><td>.214</td><td>-</td><td>.472</td><td>-</td><td>-</td></tr><tr><td>ConvE (Dettmers et al., 2018)</td><td>.325</td><td>244</td><td>.501</td><td>.356</td><td>.237</td><td>.43</td><td>4187</td><td>.52</td><td>.44</td><td>.40</td></tr><tr><td>ConvKB (Nguyen et al., 2018)</td><td>.243</td><td>311</td><td>.421</td><td>.371</td><td>.155</td><td>.249</td><td>3324</td><td>.524</td><td>.417</td><td>.057</td></tr><tr><td>SACN (Shang et al., 2019)</td><td>.35</td><td>-</td><td>.54</td><td>.39</td><td>.26</td><td>.47</td><td>-</td><td>.54</td><td>.48</td><td>.43</td></tr><tr><td>HypER (Balažević et al., 2019)</td><td>.341</td><td>250</td><td>.520</td><td>.376</td><td>.252</td><td>.465</td><td>5798</td><td>.522</td><td>.477</td><td>.436</td></tr><tr><td>RotatE (Sun et al., 2019)</td><td>.338</td><td>177</td><td>.533</td><td>.375</td><td>.241</td><td>.476</td><td>3340</td><td>.571</td><td>.492</td><td>.428</td></tr><tr><td>ConvR (Jiang et al., 2019)</td><td>.350</td><td>-</td><td>.528</td><td>.385</td><td>.261</td><td>.475</td><td>-</td><td>.537</td><td>.489</td><td>.443</td></tr><tr><td>VR-GCN (Ye et al., 2019)</td><td>.248</td><td>-</td><td>.432</td><td>.272</td><td>.159</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td></tr><tr><td>CoMPGCN (Proposed Method)</td><td>.355</td><td>197</td><td>.535</td><td>.390</td><td>.264</td><td>.479</td><td>3533</td><td>.546</td><td>.494</td><td>.443</td></tr></table>

Table 3: Link prediction performance of COMPGCN and several recent models on FB15k-237 and WN18RR datasets. The results of all the baseline methods are taken directly from the previous papers $\because$ indicates missing values). We find that COMPGCN outperforms all the existing methods on 4 out of 5 metrics on FB15k-237 and 3 out of 5 metrics on WN18RR. Please refer to Section 6.1 for more details.

# 5 EXPERIMENTAL SETUP

# 5.1 EVALUATION TASKS

In our experiments, we evaluate COMPGCN on the below-mentioned tasks.

• Link Prediction is the task of inferring missing facts based on the known facts in Knowledge Graphs. In our experiments, we utilize FB15k-237 (Toutanova & Chen, 2015) and WN18RR (Dettmers et al., 2018) datasets for evaluation. Following Bordes et al. (2013), we use filtered setting for evaluation and report Mean Reciprocal Rank (MRR), Mean Rank (MR) and Hits $\textstyle { \mathfrak { Q } } \mathbf { N }$ .

• Node Classification is the task of predicting the labels of nodes in a graph based on node features and their connections. Similar to Schlichtkrull et al. (2017), we evaluate COMPGCN on MUTAG (Node) and AM (Ristoski & Paulheim, 2016) datasets.

• Graph Classification, where, given a set of graphs and their corresponding labels, the goal is to learn a representation for each graph which is fed to a classifier for prediction. We evaluate on 2 bioinformatics dataset: MUTAG (Graph) and PTC (Yanardag & Vishwanathan, 2015).

A summary statistics of the datasets used is provided in Appendix A.2

# 5.2 BASELINES

Across all tasks, we compare against the following GCN methods for relational graphs: (1) Relational-GCN (R-GCN) (Schlichtkrull et al., 2017) which uses relation-specific weight matrices that are defined as a linear combinations of a set of basis matrices. (2) Directed-GCN (D-GCN) (Marcheggiani & Titov, 2017) has separate weight matrices for incoming edges, outgoing edges, and self-loops. It also has relation-specific biases. (3) Weighted-GCN (W-GCN) (Shang et al., 2019) assigns a learnable scalar weight to each relation and multiplies an incoming "message" by this weight. Apart from this, we also compare with several task-specific baselines mentioned below.

Link prediction: For evaluating COMPGCN, we compare against several non-neural and neural baselines: TransE Bordes et al. (2013), DistMult (Yang et al., 2014), ComplEx (Trouillon et al., 2016), R-GCN (Schlichtkrull et al., 2017), KBGAN (Cai & Wang, 2018), ConvE (Dettmers et al., 2018), ConvKB (Nguyen et al., 2018), SACN (Shang et al., 2019), HypER (Balaževic et al., 2019), ´ RotatE (Sun et al., 2019), ConvR (Jiang et al., 2019), and VR-GCN (Ye et al., 2019).

Node and Graph Classification: For node classification, following Schlichtkrull et al. (2017), we compare with Feat (Paulheim & Fümkranz, 2012), WL (Shervashidze et al., 2011), and RDF2Vec (Ristoski & Paulheim, 2016). Finally, for graph classification, we evaluate against PACHYSAN (Niepert et al., 2016), Deep Graph CNN (DGCNN) (Zhang et al., 2018), and Graph Isomorphism Network (GIN) (Xu et al., 2019).

<table><tr><td>Scoring Function (=X) →</td><td colspan="3">TransE</td><td colspan="3">DistMult</td><td colspan="3">ConvE</td></tr><tr><td>Methods ↓</td><td>MRR</td><td>MR</td><td>H@ 10</td><td>MRR</td><td>MR</td><td>H@10</td><td>MRR</td><td>MR</td><td>H@10</td></tr><tr><td>X</td><td>0.294</td><td>357</td><td>0.465</td><td>0.241</td><td>354</td><td>0.419</td><td>0.325</td><td>244</td><td>0.501</td></tr><tr><td>X +D-GCN</td><td>0.299</td><td>351</td><td>0.469</td><td>0.321</td><td>225</td><td>0.497</td><td>0.344</td><td>200</td><td>0.524</td></tr><tr><td>X+R-GCN</td><td>0.281</td><td>325</td><td>0.443</td><td>0.324</td><td>230</td><td>0.499</td><td>0.342</td><td>197</td><td>0.524</td></tr><tr><td>X + W-GCN</td><td>0.267</td><td>1520</td><td>0.444</td><td>0.324</td><td>229</td><td>0.504</td><td>0.344</td><td>201</td><td>0.525</td></tr><tr><td>X + CoMPGCN (Sub)</td><td>0.335</td><td>194</td><td>0.514</td><td>0.336</td><td>231</td><td>0.513</td><td>0.352</td><td>199</td><td>0.530</td></tr><tr><td>X + CoMPGCN (Mult)</td><td>0.337</td><td>233</td><td>0.515</td><td>0.338</td><td>200</td><td>0.518</td><td>0.353</td><td>216</td><td>0.532</td></tr><tr><td>X+ CoMPGCN (Corr)</td><td>0.336</td><td>214</td><td>0.518</td><td>0.335</td><td>227</td><td>0.514</td><td>0.355</td><td>197</td><td>0.535</td></tr><tr><td>X + CoMPGCN (B = 50)</td><td>0.330</td><td>203</td><td>0.502</td><td>0.333</td><td>210</td><td>0.512</td><td>0.350</td><td>193</td><td>0.530</td></tr></table>

Table 4: Performance on link prediction task evaluated on FB15k-237 dataset. $\mathbf { \boldsymbol { X } } + \mathbf { \boldsymbol { M } }$ (Y) denotes that method $\mathbf { M }$ is used for obtaining entity (and relation) embeddings with $\mathrm { X }$ as the scoring function. In the case of COMPGCN, Y denotes the composition operator used. $\boldsymbol { B }$ indicates the number of relational basis vectors used. Overall, we find that COMPGCN outperforms all the existing methods across different scoring functions. C $\mathrm { \dot { \mathrm { { c o n v E } + \mathrm { { C O M P G C } } } } }$ N (Corr) gives the best performance across all settings (highlighted using $\boxdot$ . Please refer to Section 6.1 for more details.

![](images/571cfa19ee73704bfb24ddfb0fcabecffffaf458c0027e97c92a9a2abdff4f5c.jpg)  
Figure 2: Knowledge Graph link prediction with COMPGCN and other methods. COMPGCN generates both entity and relation embedding as opposed to just entity embeddings for other models. For more details, please refer to Section 6.2

![](images/e79d612953f5cc0f89c4d7e9a00e748cb6491131be788ba81eb31c8851da8ad0.jpg)  
Figure 3: Performance of COMPGCN with different number of relation basis vectors on link prediction task. We report the relative change in MRR on FB15k-237 dataset. Overall, COMPGCN gives comparable performance even with limited parameters. Refer to Section 6.3 for details.

# 6 RESULTS

In this section, we attempt to answer the following questions.

Q1. How does COMPGCN perform on link prediction compared to existing methods? (6.1) Q2. What is the effect of using different GCN encoders and choice of the compositional operator in COMPGCN on link prediction performance? (6.1) Q3. Does COMPGCN scale with the number of relations in the graph? (6.3) Q4. How does COMPGCN perform on node and graph classification tasks? (6.4)

# 6.1 PERFORMANCE COMPARISON ON LINK PREDICTION

In this section, we evaluate the performance of COMPGCN and the baseline methods listed in Section 5.2 on link prediction task. The results on FB15k-237 and WN18RR datasets are presented in Table 3. The scores of baseline methods are taken directly from the previous papers (Sun et al., 2019; Cai & Wang, 2018; Shang et al., 2019; Balaževic et al., 2019; Jiang et al., 2019; Ye et al., ´ 2019). However, for ConvKB, we generate the results using the corrected evaluation code2. Overall, we find that COMPGCN outperforms all the existing methods in 4 out of 5 metrics on FB15k-237 and in 3 out of 5 metrics on WN18RR dataset. We note that the best performing baseline RotatE uses rotation operation in complex domain. The same operation can be utilized in a complex variant of our proposed method to improve its performance further. We defer this as future work.

![](images/94639a4bfc02bcc9a7f6a97f2d2ec61d48636e8ab989e908c8e1beae2917cde0.jpg)  
Figure 4: Comparison of COMPGCN $\ B = 5$ ) with R-GCN for pruned versions of Fb15k-237 dataset containing different number of relations. COMPGCN with 5 relation basis vectors outperforms R-GCN across all setups. For more details, please refer to Section 6.2

![](images/3c25fac801e5392e41b2b2bce0ec3d0d0e0e658e59269ac228606233f1617182.jpg)  
Figure 5: Performance of COMPGCN with different number of relations on link prediction task. We report the relative change in MRR on pruned versions of FB15k-237 dataset. Overall, COMPGCN gives comparable performance even with limited parameters. Refer to Section 6.2 for details.

# 6.2 COMPARISON OF DIFFERENT GCN ENCODERS ON LINK PREDICTION PERFORMANCE

Next, we evaluate the effect of using different GCN methods as an encoder along with a representative score function (shown in Figure 2) from each category: TransE (translational), DistMult (semantic-based), and ConvE (neural network-based). In our results, $\mathbf { X } + \mathbf { M }$ (Y) denotes that method $\mathbf { M }$ is used for obtaining entity embeddings (and relation embeddings in the case of COMPGCN) with $\mathbf { X }$ as the score function as depicted in Figure 2. Y denotes the composition operator in the case of COMPGCN. We evaluate COMPGCN on three non-parametric composition operators inspired from TransE (Bordes et al., 2013), DistMult (Yang et al., 2014), and HolE (Nickel et al., 2016) defined as • Subtraction (Sub): $\phi ( e _ { s } , e _ { r } ) = e _ { s } - e _ { r }$ . • Multiplication (Mult): $\phi ( e _ { s } , e _ { r } ) = e _ { s } * e _ { r }$ . • Circular-correlation (Corr): $\phi ( e _ { s } , e _ { r } ) { = } e _ { s } \star e _ { r }$

The overall results are summarized in Table 4. Similar to Schlichtkrull et al. (2017), we find that utilizing Graph Convolutional based method as encoder gives a substantial improvement in performance for most types of score functions. We observe that although all the baseline GCN methods lead to some degradation with TransE score function, no such behavior is observed for COMPGCN. On average, COMPGCN obtains around $6 \%$ , $4 \%$ and $3 \%$ relative increase in MRR with TransE, DistMult, and ConvE objective respectively compared to the best performing baseline. The superior performance of COMPGCN can be attributed to the fact that it learns both entity and relation embeddings jointly thus providing more expressive power in learned representations. Overall, we find that COMPGCN with ConvE (highlighted using $\boxdot$ is the best performing method for link prediction.3

Effect of composition Operator: The results on link prediction with different composition operators are presented in Table 4. We find that with DistMult score function, multiplication operator (Mult) gives the best performance while with ConvE, circular-correlation surpasses all other operators. Overall, we observe that more complex operators like circular-correlation outperform or perform comparably to simpler operators such as subtraction.

# 6.3 SCALABILITY OF COMPGCN

In this section, we analyze the scalability of COMPGCN with varying numbers of relations and basis vectors. For analysis with changing number of relations, we create multiple subsets of FB15k-237 dataset by retaining triples corresponding to top- $m$ most frequent relations, where $m = \{ 1 0 , 2 5 , 5 0 , 1 0 0 , 2 3 7 \}$ . For all the experiments, we use our best performing model (ConvE $+ \mathrm { C O M P G C N } \left( \mathrm { C o r r } \right) ,$ ).

Effect of Varying Relation Basis Vectors: Here, we analyze the performance of COMPGCN on changing the number of relation basis vectors $( B )$ as defined in Section 4. The results are summarized in Figure 3. We find that our model performance improves with the increasing number of basis vectors. We note that with $B = 1 0 0$ , the performance of the model becomes comparable to the case where all relations have their individual embeddings. In Table 4, we report the results for the best performing model across all score function with $\boldsymbol { B }$ set to 50. We note that the parameter-efficient variant also gives a comparable performance and outperforms the baselines in all settings.

<table><tr><td></td><td>MUTAG (Graph)</td><td>PTC</td></tr><tr><td>PACHYSAN†</td><td>92.6 ± 4.2</td><td>60.0 ± 4.8</td></tr><tr><td>DGCNN†</td><td>85.8</td><td>58.6</td></tr><tr><td>GIN†</td><td>89.4 ±4.7</td><td>64.6 ± 7.0</td></tr><tr><td>R-GCN</td><td>82.3 ± 9.2</td><td>67.8 ± 13.2</td></tr><tr><td>SynGCN</td><td>79.3 ± 10.3</td><td>69.4 ± 11.5</td></tr><tr><td>WGCN</td><td>78.9 ± 12.0</td><td>67.3 ± 12.0</td></tr><tr><td>CoMPGCN</td><td>89.0 ± 11.1</td><td>71.6 ± 12.0</td></tr></table>

Table 5: Performance comparison on node classification (Left) and graph classification (Right) tasks. $^ *$ and $\dagger$ indicate that results are directly taken from Schlichtkrull et al. (2017) and Xu et al. (2019) respectively. Overall, we find that COMPGCN either outperforms or performs comparably compared to the existing methods. Please refer to Section 6.4 for more details.   

<table><tr><td></td><td>MUTAG (Node)</td><td>AM</td></tr><tr><td>Feat*</td><td>77.9</td><td>66.7</td></tr><tr><td>WL*</td><td>80.9</td><td>87.4</td></tr><tr><td>RDF2Vec*</td><td>67.2</td><td>88.3</td></tr><tr><td>R-GCN*</td><td>73.2</td><td>89.3</td></tr><tr><td>SynGCN</td><td>74.8 ±5.5</td><td>86.2 ± 1.9</td></tr><tr><td>WGCN</td><td>77.9 ± 3.2</td><td>90.2 ± 0.9</td></tr><tr><td>COMPGCN</td><td>85.3 ± 1.2</td><td>90.6 ± 0.2</td></tr></table>

Effect of Number of Relations: Next, we report the relative performance of COMPGCN using 5 relation basis vectors $\boldsymbol { B } = 5$ ) against COMPGCN, which utilizes a separate vector for each relation in the dataset. The results are presented in Figure 5. Overall, we find that across all different numbers of relations, COMPGCN, with a limited basis, gives comparable performance to the full model. The results show that a parameter-efficient variant of COMPGCN scales with the increasing number of relations.

Comparison with R-GCN: Here, we perform a comparison of a parameter-efficient variant of COMPGCN $\mathit { B } = 5$ ) against R-GCN on different number of relations. The results are depicted in Figure 4. We observe that COMPGCN with limited parameters consistently outperforms R-GCN across all settings. Thus, COMPGCN is parameter-efficient and more effective at encoding multirelational graphs than R-GCN.

# 6.4 EVALUATION ON NODE AND GRAPH CLASSIFICATION

In this section, we evaluate COMPGCN on node and graph classification tasks on datasets as described in Section 5.1. The experimental results are presented in Table 5. For node classification task, we report accuracy on test split provided by Ristoski et al. (2016), whereas for graph classification, following Yanardag & Vishwanathan (2015) and $\mathrm { X u }$ et al. (2019), we report the average and standard deviation of validation accuracies across the 10 folds cross-validation. Overall, we find that COMPGCN outperforms all the baseline methods on node classification and gives a comparable performance on graph classification task. This demonstrates the effectiveness of incorporating relations using COMPGCN over the existing GCN based models. On node classification, compared to the best performing baseline, we obtain an average improvement of $3 \%$ across both datasets while on graph classification, we obtain an improvement of $3 \%$ on PTC dataset.

# 7 CONCLUSION

In this paper, we proposed COMPGCN, a novel Graph Convolutional based framework for multirelational graphs which leverages a variety of composition operators from Knowledge Graph embedding techniques to jointly embed nodes and relations in a graph. Our method generalizes several existing multi-relational GCN methods. Moreover, our method alleviates the problem of over-parameterization by sharing relation embeddings across layers and using basis decomposition. Through extensive experiments on knowledge graph link prediction, node classification, and graph classification tasks, we showed the effectiveness of COMPGCN over existing GCN based methods and demonstrated its scalability with increasing number of relations.

# ACKNOWLEDGMENTS

We thank the anonymous reviewers for their constructive comments. This work is supported in part by the Ministry of Human Resource Development (Government of India) and Google PhD Fellowship.

# REFERENCES

Ivana Balaževic, Carl Allen, and Timothy M Hospedales. Hypernetwork knowledge graph embed-´ dings. In International Conference on Artificial Neural Networks, 2019.

Daniel Beck, Gholamreza Haffari, and Trevor Cohn. Graph-to-sequence learning using gated graph neural networks. In Iryna Gurevych and Yusuke Miyao (eds.), ACL 2018 - The 56th Annual Meeting of the Association for Computational Linguistics, pp. 273–283. Association for Computational Linguistics (ACL), 2018. ISBN 9781948087322.

Antoine Bordes, Nicolas Usunier, Alberto Garcia-Duran, Jason Weston, and Oksana Yakhnenko. Translating embeddings for modeling multi-relational data. In C. J. C. Burges, L. Bottou, M. Welling, Z. Ghahramani, and K. Q. Weinberger (eds.), Advances in Neural Information Processing Systems 26, pp. 2787–2795. Curran Associates, Inc., 2013. URL http://papers.nips.cc/paper/ 5071-translating-embeddings-for-modeling-multi-relational-data. pdf.

Antoine Bordes, Sumit Chopra, and Jason Weston. Question answering with subgraph embeddings. In Proceedings of the 2014 Conference on Empirical Methods in Natural Language Processing (EMNLP), pp. 615–620, Doha, Qatar, October 2014. Association for Computational Linguistics. doi: 10.3115/v1/D14-1067. URL https://www.aclweb.org/anthology/D14-1067.

Joan Bruna, Wojciech Zaremba, Arthur Szlam, and Yann LeCun. Spectral networks and locally connected networks on graphs. CoRR, abs/1312.6203, 2013. URL http://arxiv.org/ abs/1312.6203.

Liwei Cai and William Yang Wang. KBGAN: Adversarial learning for knowledge graph embeddings. In Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, pp. 1470–1480, 2018. URL https://www.aclweb.org/anthology/N18-1133.

Victor de Boer, Jan Wielemaker, Judith van Gent, Michiel Hildebrand, Antoine Isaac, Jacco van Ossenbruggen, and Guus Schreiber. Supporting linked data production for cultural heritage institutes: The amsterdam museum case study. In Proceedings of the 9th International Conference on The Semantic Web: Research and Applications, ESWC’12, pp. 733–747, Berlin, Heidelberg, 2012. Springer-Verlag. ISBN 978-3-642-30283-1. doi: 10.1007/978-3-642-30284-8_56. URL http://dx.doi.org/10.1007/978-3-642-30284-8_56.

Asim Kumar Debnath, Rosa L. Lopez de Compadre, Gargi Debnath, Alan J. Shusterman, and Corwin Hansch. Structure-activity relationship of mutagenic aromatic and heteroaromatic nitro compounds. correlation with molecular orbital energies and hydrophobicity. Journal of Medicinal Chemistry, 34(2):786–797, 1991. doi: 10.1021/jm00106a046. URL https://doi.org/10. 1021/jm00106a046.

Michaël Defferrard, Xavier Bresson, and Pierre Vandergheynst. Convolutional neural networks on graphs with fast localized spectral filtering. CoRR, abs/1606.09375, 2016. URL http: //arxiv.org/abs/1606.09375.

Tim Dettmers, Minervini Pasquale, Stenetorp Pontus, and Sebastian Riedel. Convolutional 2d knowledge graph embeddings. In Proceedings of the 32th AAAI Conference on Artificial Intelligence, pp. 1811–1818, February 2018. URL https://arxiv.org/abs/1707.01476.

Matthias Fey and Jan E. Lenssen. Fast graph representation learning with PyTorch Geometric. In ICLR Workshop on Representation Learning on Graphs and Manifolds, 2019.

Alex Fout, Jonathon Byrd, Basir Shariat, and Asa Ben-Hur. Protein interface prediction using graph convolutional networks. In I. Guyon, U. V. Luxburg, S. Bengio, H. Wallach, R. Fergus, S. Vishwanathan, and R. Garnett (eds.), Advances in Neural Information Processing Systems 30, pp. 6530–6539. Curran Associates, Inc., 2017. URL http://papers.nips.cc/paper/ 7231-protein-interface-prediction-using-graph-convolutional-networks. pdf.

Justin Gilmer, Samuel S. Schoenholz, Patrick F. Riley, Oriol Vinyals, and George E. Dahl. Neural message passing for quantum chemistry. In Proceedings of the 34th International Conference on Machine Learning - Volume 70, ICML’17, pp. 1263–1272. JMLR.org, 2017. URL http: //dl.acm.org/citation.cfm?id $=$ 3305381.3305512.

Xavier Glorot and Yoshua Bengio. Understanding the difficulty of training deep feedforward neural networks. In Yee Whye Teh and Mike Titterington (eds.), Proceedings of the Thirteenth International Conference on Artificial Intelligence and Statistics, volume 9 of Proceedings of Machine Learning Research, pp. 249–256, Chia Laguna Resort, Sardinia, Italy, 13–15 May 2010. PMLR. URL http://proceedings.mlr.press/v9/glorot10a.html.

William L. Hamilton, Rex Ying, and Jure Leskovec. Inductive representation learning on large graphs. In NIPS, 2017.

Sepp Hochreiter and Jürgen Schmidhuber. Long short-term memory. Neural Comput., 9(8):1735– 1780, November 1997. ISSN 0899-7667. doi: 10.1162/neco.1997.9.8.1735. URL http://dx. doi.org/10.1162/neco.1997.9.8.1735.

Xiaotian Jiang, Quan Wang, and Bin Wang. Adaptive convolution for multi-relational learning. In Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, 2019. URL https: //www.aclweb.org/anthology/N19-1103".

Diederik Kingma and Jimmy Ba. Adam: A method for stochastic optimization. 12 2014.

Thomas N. Kipf and Max Welling. Semi-supervised classification with graph convolutional networks. CoRR, abs/1609.02907, 2016. URL http://arxiv.org/abs/1609.02907.

Alex Krizhevsky, Ilya Sutskever, and Geoffrey E Hinton. Imagenet classification with deep convolutional neural networks. In F. Pereira, C. J. C. Burges, L. Bottou, and K. Q. Weinberger (eds.), Advances in Neural Information Processing Systems 25, pp. 1097– 1105. Curran Associates, Inc., 2012. URL http://papers.nips.cc/paper/ 4824-imagenet-classification-with-deep-convolutional-neural-networks. pdf.

Diego Marcheggiani and Ivan Titov. Encoding sentences with graph convolutional networks for semantic role labeling. In Proceedings of the 2017 Conference on Empirical Methods in Natural Language Processing, pp. 1506–1515. Association for Computational Linguistics, 2017. URL http://aclweb.org/anthology/D17-1159.

George A. Miller. Wordnet: A lexical database for english. Commun. ACM, 38(11):39–41, November 1995. ISSN 0001-0782. doi: 10.1145/219717.219748. URL http://doi.acm.org/ 10.1145/219717.219748.

Federico Monti, Oleksandr Shchur, Aleksandar Bojchevski, Or Litany, Stephan Günnemann, and Michael M. Bronstein. Dual-primal graph convolutional networks. CoRR, abs/1806.00770, 2018. URL http://arxiv.org/abs/1806.00770.

Dai Quoc Nguyen, Tu Dinh Nguyen, Dat Quoc Nguyen, and Dinh Phung. A novel embedding model for knowledge base completion based on convolutional neural network. In Proceedings of the 2018 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 2 (Short Papers), pp. 327–333. Association for Computational Linguistics, 2018. doi: 10.18653/v1/N18-2053. URL http://aclweb. org/anthology/N18-2053.

M. Nickel, K. Murphy, V. Tresp, and E. Gabrilovich. A review of relational machine learning for knowledge graphs. Proceedings of the IEEE, 104(1):11–33, Jan 2016. ISSN 0018-9219. doi: 10.1109/JPROC.2015.2483592.

Maximilian Nickel, Lorenzo Rosasco, and Tomaso Poggio. Holographic embeddings of knowledge graphs. In Proceedings of the Thirtieth AAAI Conference on Artificial Intelligence, AAAI’16, pp. 1955–1961. AAAI Press, 2016. URL http://dl.acm.org/citation.cfm?id= 3016100.3016172.

Mathias Niepert, Mohamed Ahmed, and Konstantin Kutzkov. Learning convolutional neural networks for graphs. In Proceedings of the 33rd International Conference on International Conference on Machine Learning - Volume 48, ICML’16, pp. 2014–2023. JMLR.org, 2016. URL http://dl.acm.org/citation.cfm?id=3045390.3045603.

Heiko Paulheim and Johannes Fümkranz. Unsupervised generation of data mining features from linked open data. In Proceedings of the 2Nd International Conference on Web Intelligence, Mining and Semantics, WIMS ’12, pp. 31:1–31:12, New York, NY, USA, 2012. ACM. ISBN 978-1- 4503-0915-8. doi: 10.1145/2254129.2254168. URL http://doi.acm.org/10.1145/ 2254129.2254168.

Bharath Ramsundar, Peter Eastman, Patrick Walters, Vijay Pande, Karl Leswing, and Zhenqin Wu. Deep Learning for the Life Sciences. O’Reilly Media, 2019. https://www.amazon.com/ Deep-Learning-Life-Sciences-Microscopy/dp/1492039837.

Petar Ristoski and Heiko Paulheim. Rdf2vec: Rdf graph embeddings for data mining. In International Semantic Web Conference, pp. 498–514. Springer, 2016.

Petar Ristoski, Gerben Klaas Dirk de Vries, and Heiko Paulheim. A collection of benchmark datasets for systematic evaluations of machine learning on the semantic web. In Paul Groth, Elena Simperl, Alasdair Gray, Marta Sabou, Markus Krötzsch, Freddy Lecue, Fabian Flöck, and Yolanda Gil (eds.), The Semantic Web – ISWC 2016, pp. 186–194, Cham, 2016. Springer International Publishing. ISBN 978-3-319-46547-0.

Soumya Sanyal, Janakiraman Balachandran, Naganand Yadati, Abhishek Kumar, Padmini Rajagopalan, Suchismita Sanyal, and Partha Talukdar. Mt-cgcnn: Integrating crystal graph convolutional neural network with multitask learning for material property prediction. arXiv preprint arXiv:1811.05660, 2018.

Michael Schlichtkrull, Thomas N Kipf, Peter Bloem, Rianne van den Berg, Ivan Titov, and Max Welling. Modeling relational data with graph convolutional networks. arXiv preprint arXiv:1703.06103, 2017.

Chao Shang, Yun Tang, Jing Huang, Jinbo Bi, Xiaodong He, and Bowen Zhou. End-to-end structureaware convolutional networks for knowledge base completion, 2019.

Nino Shervashidze, Pascal Schweitzer, Erik Jan van Leeuwen, Kurt Mehlhorn, and Karsten M. Borgwardt. Weisfeiler-lehman graph kernels. J. Mach. Learn. Res., 12:2539–2561, November 2011. ISSN 1532-4435. URL http://dl.acm.org/citation.cfm?id $\underline { { \underline { { \mathbf { \Pi } } } } } =$ 1953048. 2078187.

Richard Socher, Danqi Chen, Christopher D Manning, and Andrew Ng. Reasoning with neural tensor networks for knowledge base completion. In C. J. C. Burges, L. Bottou, M. Welling, Z. Ghahramani, and K. Q. Weinberger (eds.), Advances in Neural Information Processing Systems 26, pp. 926–934. Curran Associates, Inc., 2013. URL http://papers.nips.cc/paper/ 5028-reasoning-with-neural-tensor-networks-for-knowledge-base-completion. pdf.

A. Srinivasan, R. D. King, S. H. Muggleton, and M. J. E. Sternberg. The predictive toxicology evaluation challenge. In Proceedings of the 15th International Joint Conference on Artifical Intelligence - Volume 1, IJCAI’97, pp. 4–9, San Francisco, CA, USA, 1997. Morgan Kaufmann Publishers Inc. ISBN 1-555860-480-4. URL http://dl.acm.org/citation.cfm?id= 1624162.1624163.

Zhiqing Sun, Zhi-Hong Deng, Jian-Yun Nie, and Jian Tang. Rotate: Knowledge graph embedding by relational rotation in complex space. In International Conference on Learning Representations, 2019. URL https://openreview.net/forum?id $=$ HkgEQnRqYQ.

Kristina Toutanova and Danqi Chen. Observed versus latent features for knowledge base and text inference. In Proceedings of the 3rd Workshop on Continuous Vector Space Models and their Compositionality, pp. 57–66, 2015.

Théo Trouillon, Johannes Welbl, Sebastian Riedel, Éric Gaussier, and Guillaume Bouchard. Complex embeddings for simple link prediction. In Proceedings of the 33rd International Conference on International Conference on Machine Learning - Volume 48, ICML’16, pp. 2071– 2080. JMLR.org, 2016. URL http://dl.acm.org/citation.cfm?id $\underline { { \underline { { \mathbf { \Pi } } } } } =$ 3045390. 3045609.

Petar Velickovi ˇ c, Guillem Cucurull, Arantxa Casanova, Adriana Romero, Pietro Liò, and Yoshua ´ Bengio. Graph Attention Networks. International Conference on Learning Representations, 2018. URL https://openreview.net/forum?id ${ . } = { }$ rJXMpikCZ. accepted as poster.

Q. Wang, Z. Mao, B. Wang, and L. Guo. Knowledge graph embedding: A survey of approaches and applications. IEEE Transactions on Knowledge and Data Engineering, 29(12):2724–2743, Dec 2017. ISSN 1041-4347. doi: 10.1109/TKDE.2017.2754499.

Zhen Wang, Jianwen Zhang, Jianlin Feng, and Zheng Chen. Knowledge graph embedding by translating on hyperplanes, 2014a. URL https://www.aaai.org/ocs/index.php/AAAI/ AAAI14/paper/view/8531.

Zhen Wang, Jianwen Zhang, Jianlin Feng, and Zheng Chen. Knowledge graph embedding by translating on hyperplanes. In Proceedings of the Twenty-Eighth AAAI Conference on Artificial Intelligence, AAAI’14, pp. 1112–1119. AAAI Press, 2014b. URL http://dl.acm.org/ citation.cfm?id=2893873.2894046.

Keyulu Xu, Weihua Hu, Jure Leskovec, and Stefanie Jegelka. How powerful are graph neural networks? In International Conference on Learning Representations, 2019. URL https: //openreview.net/forum?id $=$ ryGs6iA5Km.

Pinar Yanardag and S.V.N. Vishwanathan. Deep graph kernels. In Proceedings of the 21th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, KDD ’15, pp. 1365–1374, New York, NY, USA, 2015. ACM. ISBN 978-1-4503-3664-2. doi: 10.1145/2783258. 2783417. URL http://doi.acm.org/10.1145/2783258.2783417.

Bishan Yang, Wen-tau Yih, Xiaodong He, Jianfeng Gao, and Li Deng. Embedding entities and relations for learning and inference in knowledge bases. CoRR, abs/1412.6575, 2014. URL http://arxiv.org/abs/1412.6575.

Rui Ye, Xin Li, Yujie Fang, Hongyu Zang, and Mingzhong Wang. A vectorized relational graph convolutional network for multi-relational network alignment. In Proceedings of the Twenty-Eighth International Joint Conference on Artificial Intelligence, IJCAI-19, pp. 4135–4141. International Joint Conferences on Artificial Intelligence Organization, 7 2019. doi: 10.24963/ijcai.2019/574. URL https://doi.org/10.24963/ijcai.2019/574.

Muhan Zhang, Zhicheng Cui, Marion Neumann, and Yixin Chen. An end-to-end deep learning architecture for graph classification. In AAAI, pp. 4438–4445, 2018.

# A APPENDIX

# A.1 EVALUATION BY RELATION CATEGORY

In this section, we investigate the performance of COMPGCN on link prediction for different relation categories on FB15k-237 dataset. Following Wang et al. (2014a); Sun et al. (2019), based on the average number of tails per head and heads per tail, we divide the relations into four categories: one-to-one, one-to-many, many-to-one and many-to-many. The results are summarized in Table 6. We observe that using GCN based encoders for obtaining entity and relation embeddings helps to improve performance on all types of relations. In the case of one-to-one relations, COMPGCN gives an average improvement of around $10 \%$ on MRR compared to the best performing baseline (ConvE $+ \mathbf { W } \mathbf { \mathrm { { - G C N } } } )$ . For one-to-many, many-to-one, and many-to-many the corresponding improvements are $1 0 . 5 \%$ , $7 . 5 \%$ , and $4 \%$ . These results show that COMPGCN is effective at handling both simple and complex relations.

<table><tr><td rowspan="2" colspan="2"></td><td colspan="3">ConvE</td><td colspan="3">ConvE + W-GCN</td><td colspan="3">ConvE + CoMPGCN (Corr)</td></tr><tr><td>MRR</td><td>MR</td><td>H@10</td><td>MRR</td><td>MR</td><td>H@10</td><td>MRR</td><td>MR</td><td>H@10</td></tr><tr><td> </td><td>1-1</td><td>0.193</td><td>459</td><td>0.385</td><td>0.422</td><td>238</td><td>0.547</td><td>0.457</td><td>150</td><td>0.604</td></tr><tr><td></td><td>1-N</td><td>0.068</td><td>922</td><td>0.116</td><td>0.093</td><td>612</td><td>0.187</td><td>0.112</td><td>604</td><td>0.190</td></tr><tr><td></td><td>N-1</td><td>0.438</td><td>123</td><td>0.638</td><td>0.454</td><td>101</td><td>0.647</td><td>0.471</td><td>99</td><td>0.656</td></tr><tr><td></td><td>N-N</td><td>0.246</td><td>189</td><td>0.436</td><td>0.261</td><td>169</td><td>0.459</td><td>0.275</td><td>179</td><td>0.474</td></tr><tr><td></td><td>1-1</td><td>0.177</td><td>402</td><td>0.391</td><td>0.406</td><td>319</td><td>0.531</td><td>0.453</td><td>193</td><td>0.589</td></tr><tr><td></td><td>1-N</td><td>0.756</td><td>66</td><td>0.867</td><td>0.771</td><td>43</td><td>0.875</td><td>0.779</td><td>34</td><td>0.885</td></tr><tr><td></td><td>N-1</td><td>0.049</td><td>783</td><td>0.09</td><td>0.068</td><td>747</td><td>0.139</td><td>0.076</td><td>792</td><td>0.151</td></tr><tr><td></td><td>N-N</td><td>0.369</td><td>119</td><td>0.587</td><td>0.385</td><td>107</td><td>0.607</td><td>0.395</td><td>102</td><td>0.616</td></tr></table>

Table 6: Results on link prediction by relation category on FB15k-237 dataset. Following Wang et al. (2014a), the relations are divided into four categories: one-to-one (1-1), one-to-many (1-N), manyto-one (N-1), and many-to-many (N-N). We find that COMPGCN helps to improve performance on all types of relations compared to existing methods. Please refer to Section A.1 for more details.

# A.2 DATASET DETAILS

In this section, we provide the details of the different datasets used in the experiments. For link prediction, we use the following two datasets:

• FB15k-237 (Toutanova & Chen, 2015) is a pruned version of FB15k (Bordes et al., 2013) dataset with inverse relations removed to prevent direct inference.   
• WN18RR (Dettmers et al., 2018), similar to FB15k-237, is a subset from WN18 (Bordes et al., 2013) dataset which is derived from WordNet (Miller, 1995).

For node classification, similar to Schlichtkrull et al. (2017), we evaluate on the following two datasets:

• MUTAG (Node) is a dataset from DL-Learner toolkit4. It contains relationship between complex molecules and the task is to identify whether a molecule is carcinogenic or not. • AM dataset contains relationship between different artifacts in Amsterdam Museum (de Boer et al., 2012). The goal is to predict the category of a given artifact based on its links and other attributes.

Finally, for graph classification, similar to Xu et al. (2019), we evaluate on the following datasets:

• MUTAG (Graph) Debnath et al. (1991) is a bioinformatics dataset of 188 mutagenic aromatic and nitro compounds. The graphs need to be categorized into two classes based on their mutagenic effect on a bacterium.

<table><tr><td></td><td colspan="2">Link Prediction</td><td colspan="2">Node Classification</td><td colspan="2">Graph Classification</td></tr><tr><td></td><td>FB15k-237</td><td>WN18RR</td><td>MUTAG (Node)</td><td>AM</td><td>MUTAG (Graph)</td><td>PTC</td></tr><tr><td>Graphs</td><td>1</td><td>1</td><td>1</td><td>1</td><td>188</td><td>344</td></tr><tr><td>Entities</td><td>14,541</td><td>40,943</td><td>23,644</td><td>1,666,764</td><td>17.9 (Avg)</td><td>25.5 (Avg)</td></tr><tr><td>Edges</td><td>310,116</td><td>93,003</td><td>74,227</td><td>5,988,321</td><td>39.6 (Avg)</td><td>29.5 (Avg)</td></tr><tr><td>Relations</td><td>237</td><td>11</td><td>23</td><td>133</td><td>4</td><td>4</td></tr><tr><td>Classes</td><td>-</td><td>-</td><td>2</td><td>11</td><td>2</td><td>2</td></tr></table>

Table 7: The details of the datasets used for node classification, link prediction, and graph classification tasks. Please refer to Section 5.1 for more details.

• PTC Srinivasan et al. (1997) is a dataset consisting of 344 chemical compounds which indicate carcinogenicity of male and female rats. The task is to label the graphs based on their carcinogenicity on rodents.

A summary statistics of all the datasets used is presented in Table 7.

# A.3 HYPERPARAMETERS

Here, we present the implementation details for each task used for evaluation in the paper. For all the tasks, we used COMPGCN build on PyTorch geometric framework (Fey & Lenssen, 2019).

Link Prediction: For evaluation, 200-dimensional embeddings for node and relation embeddings are used. For selecting the best model we perform a hyperparameter search using the validation data over the values listed in Table 8. For training link prediction models, we use the standard binary cross entropy loss with label smoothing Dettmers et al. (2018).

Node Classification: Following Schlichtkrull et al. (2017), we use $10 \%$ training data as validation for selecting the best model for both the datasets. We restrict the number of hidden units to 32. We use cross-entropy loss for training our model.

Graph Classification: Similar to Yanardag & Vishwanathan (2015); Xu et al. (2019), we report the mean and standard deviation of validation accuracies across the 10 folds cross-validation. Crossentropy loss is used for training the entire model. For obtaining the graph-level representation, we use simple averaging of embedding of all nodes as the readout function, i.e.,

$$
h _ { \mathcal { G } } = \frac { 1 } { | \mathcal { V } | } \sum _ { v \in \mathcal { V } } h _ { v } ,
$$

where $ { \boldsymbol { h } } _ { v }$ is the learned node representation for node $v$ in the graph.

For all the experiments, training is done using Adam optimizer (Kingma & Ba, 2014) and Xavier initialization (Glorot & Bengio, 2010) is used for initializing parameters.

<table><tr><td>Hyperparameter</td><td>Values</td></tr><tr><td>Number of GCN Layer (K)</td><td>{1, 2, 3}</td></tr><tr><td>Learning rate</td><td>{0.001, 0.0001}</td></tr><tr><td>Batch size</td><td>{128, 256}</td></tr><tr><td>Dropout</td><td>{0.0, 0.1, 0.2, 0.3}</td></tr></table>

Table 8: Details of hyperparameters used for link prediction task. Please refer to Section A.3 for more details.