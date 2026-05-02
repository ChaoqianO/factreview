## **1. Metadata**
- Title: BEIT: BERT Pre-Training of Image Transformers
- Task: Self-supervised pre-training for vision Transformers; downstream image classification and semantic segmentation
- Code: https://aka.ms/beit

## **2. Technical Positioning**
![](./overview_figure.jpg)

Overview of ADE20K.

BEIT pre-training uses masked image modeling with image patches as input and dVAE visual tokens as prediction targets.

| **Research domain** | **Method** | **Masked autoencoding objective** | **Discrete visual token prediction** | **Contrastive/self-distillation paradigm** | **VAE-theoretic formulation** |
| --- | --- | --- | --- | --- | --- |
| Self-supervised vision Transformer | iGPT | √ | × | × | × |
| Self-supervised vision Transformer | ViT masked patch prediction | √ | × | × | × |
| Self-supervised vision Transformer | MoCo v3 | × | × | √ | × |
| Self-supervised vision Transformer | DINO | × | × | √ | × |
| This Work | masked image modeling (MIM) with dVAE visual tokens | √ | √ | × | √ |

## **3. Claims**
**Paper scope:** Self-supervised pre-training method (BEIT) for vision Transformers via masked image modeling with visual-token targets.
**Evaluation scope:** Fine-tuning on image classification (ImageNet-1K) and semantic segmentation (ADE20K), plus ablations and attention-map analysis.
(Status legend: <span style="color: green;">✓ Supported</span>, <span style="color: #E6B800;">⚠ Partially supported</span>, <span style="color: red;">✗ In conflict</span>.)
| **Claim** | **Evidence** | **Assessment** | **Status** | **Location** |
|---|---|---|---|---|
| BEIT matches or outperforms prior self-supervised Transformer methods on ImageNet-1K fine-tuning, with clear gains in several settings (especially higher resolution and larger models). | Table 1: BEiT-B (224) 83.2 ties MoCo v3-B (224) 83.2; BEiT384-B 84.6 > DINO-B 82.8 and MoCo v3-B 83.2; BEiT-L 85.2 and BEiT384-L 86.3 > MoCo v3-L 84.1. | The paper cites experimental tables or figures as evidence. Concrete numeric values are present in the evidence. The cited location is Sec. 3.1, Table 1. | <span style="color: green;">✓ Supported</span> | Sec. 3.1, Table 1 |
| Predicting discrete visual tokens is a key design; replacing with pixel recovery degrades results. | Table 4: BEiT (300 epochs) 82.86/44.65 (ImageNet/ADE20K) vs “- Visual tokens (recover masked pixels)” 81.04/41.38 and “- Visual tokens - Blockwise masking” 80.50/37.09. | The paper cites experimental tables or figures as evidence. Concrete numeric values are present in the evidence. The cited location is Sec. 3.3, Table 4. | <span style="color: green;">✓ Supported</span> | Sec. 3.3, Table 4 |
| The BEIT objective can be interpreted as two-stage VAE training with MIM as prior learning. | Sec. 2.4 derives ELBO form (Eq. 2) and rewrites objective into Stage 1 visual token reconstruction + Stage 2 masked image modeling term (Eq. 3). | The paper gives no clear theorem/proposition/proof anchor. The evidence contains explicit mathematical derivation signals. The cited location is Sec. 2.4, Eq. (2), Eq. (3). | <span style="color: #E6B800;">⚠ Partially supported</span> | Sec. 2.4, Eq. (2), Eq. (3) |

## **4. Summary**
The paper presents BEIT, a self-supervised pre-training framework for vision Transformers that masks image patches and predicts dVAE-based discrete visual tokens. It formulates the objective in a VAE perspective, pretrains on ImageNet-1K without labels, and reports downstream gains on ImageNet classification and ADE20K segmentation with additional ablations and attention-map analysis.

**Strengths:** - Clear problem framing for data-hungry vision Transformers and a concrete BERT-style pre-training adaptation.
- Method design is explicitly specified (two image views, masking strategy, token prediction objective, training setup).
- Empirical evidence spans two downstream tasks with direct baseline comparisons (Table 1 and Table 3).
- Ablation section (Table 4) links key components (visual tokens, blockwise masking, masking ratio behavior) to performance changes.
- Includes a theoretical interpretation via ELBO decomposition (Eq. 2–3) and qualitative analysis of learned attention regions.

**Weaknesses:** - Main comparisons in core sections are concentrated on selected baselines and settings; broader objective related-work coverage is limited here.
- Some strong claims (e.g., efficiency/throughput advantages) are mainly supported in appendices rather than the main experimental section.
- Theoretical part is an interpretation/derivation and does not provide formal guarantees beyond the presented formulation.
- Several analyses are qualitative (attention maps) and do not include quantitative localization or boundary metrics in the main text.

## **5. Experiment**
### **Main Result**
(Status legend: <span style="color: green;">✓ Supported</span>, <span style="color: #E6B800;">⚠ Inconclusive</span>, <span style="color: red;">✗ In conflict</span>.)
**Location:** Section 3.1 Table 1 (ImageNet-1K classification, top-1 accuracy); Section 3.2 Table 3 (ADE20K semantic segmentation, mIoU, single-scale inference).
| **Task** | **Dataset** | **Metric** | **Best Baseline** | **Paper Result** | **Difference (Δ)** | **Evaluation Status** |
| --- | --- | --- | --- | --- | --- | --- |
| Image classification | ImageNet-1K | Top-1 accuracy | 81.8(DeiT-B training from scratch) | BEiT-B 83.2 | <span style="color: green;">+1.4</span> | <span style="color: #E6B800;">⚠()</span> |
| Image classification | ImageNet-1K | Top-1 accuracy | 83.1(DeiT3 -B training from scratch) | BEiT384-B 84.6 | <span style="color: green;">+1.5</span> | <span style="color: #E6B800;">⚠()</span> |
| Image classification | ImageNet-1K | Top-1 accuracy | 84(ViT3 -B supervised pre-training on ImageNet- 2K) | BEiT384-B 84.6 | <span style="color: green;">+0.6</span> | <span style="color: #E6B800;">⚠()</span> |
| Image classification | ImageNet-1K | Top-1 accuracy | 85.2(ViT3 -L supervised pre-training on ImageNet- 2K) | BEiT384-L 86.3 | <span style="color: green;">+1.1</span> | <span style="color: #E6B800;">⚠()</span> |
| Image classification | ImageNet-1K | Top-1 accuracy | 83.2(MoCo v3-B self-supervised) | BEiT384-B 84.6 | <span style="color: green;">+1.4</span> | <span style="color: #E6B800;">⚠()</span> |
| Image classification | ImageNet-1K | Top-1 accuracy | 84.1(MoCo v3-L self-supervised) | BEiT384-L 86.3 | <span style="color: green;">+2.2</span> | <span style="color: #E6B800;">⚠()</span> |
| Image classification | ImageNet-1K | Top-1 accuracy | 82.8(DINO-B self-supervised) | BEiT384-B 84.6 | <span style="color: green;">+1.8</span> | <span style="color: #E6B800;">⚠()</span> |
| Semantic segmentation | ADE20K | mIoU (single-scale) | 45.3(Supervised pre-training on ImageNet) | BEiT 45.6 | <span style="color: green;">+0.3</span> | <span style="color: #E6B800;">⚠()</span> |
| Semantic segmentation | ADE20K | mIoU (single-scale) | 45.3(Supervised pre-training on ImageNet) | BEiT + Intermediate Fine-Tuning 47.7 | <span style="color: green;">+2.4</span> | <span style="color: #E6B800;">⚠()</span> |
| Semantic segmentation | ADE20K | mIoU (single-scale) | 44.1(DINO) | BEiT 45.6 | <span style="color: green;">+1.5</span> | <span style="color: #E6B800;">⚠()</span> |
| Semantic segmentation | ADE20K | mIoU (single-scale) | 44.1(DINO) | BEiT + Intermediate Fine-Tuning 47.7 | <span style="color: green;">+3.6</span> | <span style="color: #E6B800;">⚠()</span> |
### **Ablation Result**
(Status legend: <span style="color: green;">✓ Supported</span>, <span style="color: #E6B800;">⚠ Inconclusive</span>, <span style="color: red;">✗ In conflict</span>.)
**Location:** Section 3.3 Ablation Studies, Table 4; datasets: ImageNet (top-1 accuracy) and ADE20K (mIoU).
| **Ablation Dimension** | **Configuration** | **Full Model** | **Paper Result** | **Difference (Δ)** | **Evaluation Status** |
| --- | --- | --- | --- | --- | --- |
| Optimal setup | BEiT (300 Epochs) | 82.86 (ImageNet) | 82.86 (ImageNet) | **0** | <span style="color: #E6B800;">⚠()</span> |
| Blockwise masking | - Blockwise masking | 82.86 (ImageNet) | 82.77 (ImageNet) | <span style="color: green;">-0.09</span> | <span style="color: #E6B800;">⚠()</span> |
| Visual token target | - Visual tokens (recover masked pixels) | 82.86 (ImageNet) | 81.04 (ImageNet) | <span style="color: green;">-1.82</span> | <span style="color: #E6B800;">⚠()</span> |
| Visual token target + masking strategy | - Visual tokens - Blockwise masking | 82.86 (ImageNet) | 80.50 (ImageNet) | <span style="color: green;">-2.36</span> | <span style="color: #E6B800;">⚠()</span> |
| Prediction coverage | + Recover 100% visual tokens | 82.86 (ImageNet) | 82.59 (ImageNet) | <span style="color: green;">-0.27</span> | <span style="color: #E6B800;">⚠()</span> |
| Masking + prediction coverage | - Masking + Recover 100% visual tokens | 82.86 (ImageNet) | 81.67 (ImageNet) | <span style="color: green;">-1.19</span> | <span style="color: #E6B800;">⚠()</span> |
| Training duration | Pretrain longer (800 epochs) | 82.86 (ImageNet) | 83.19 (ImageNet) | <span style="color: red;">+0.33</span> | <span style="color: #E6B800;">⚠()</span> |

| **Ablation Dimension** | **Configuration** | **Full Model** | **Paper Result** | **Difference (Δ)** | **Evaluation Status** |
| --- | --- | --- | --- | --- | --- |
| Optimal setup | BEiT (300 Epochs) | 44.65 (ADE20K) | 44.65 (ADE20K) | **0** | <span style="color: #E6B800;">⚠()</span> |
| Blockwise masking | - Blockwise masking | 44.65 (ADE20K) | 42.93 (ADE20K) | <span style="color: green;">-1.72</span> | <span style="color: #E6B800;">⚠()</span> |
| Visual token target | - Visual tokens (recover masked pixels) | 44.65 (ADE20K) | 41.38 (ADE20K) | <span style="color: green;">-3.27</span> | <span style="color: #E6B800;">⚠()</span> |
| Visual token target + masking strategy | - Visual tokens - Blockwise masking | 44.65 (ADE20K) | 37.09 (ADE20K) | <span style="color: green;">-7.56</span> | <span style="color: #E6B800;">⚠()</span> |
| Prediction coverage | + Recover 100% visual tokens | 44.65 (ADE20K) | 40.93 (ADE20K) | <span style="color: green;">-3.72</span> | <span style="color: #E6B800;">⚠()</span> |
| Masking + prediction coverage | - Masking + Recover 100% visual tokens | 44.65 (ADE20K) | 36.73 (ADE20K) | <span style="color: green;">-7.92</span> | <span style="color: #E6B800;">⚠()</span> |
| Training duration | Pretrain longer (800 epochs) | 44.65 (ADE20K) | 45.58 (ADE20K) | <span style="color: red;">+0.93</span> | <span style="color: #E6B800;">⚠()</span> |