import json
import re
from copy import deepcopy
from typing import Callable, Dict, List, Optional, Union

from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from module.tools.external_queries import OpenScholarClient


"""
Decoupled DeepReview module mirroring the behavior of the reference DeepReviewer.

Usage example:
    import deepreview
    dr = deepreview.DeepReview(mode="best")
    result = dr(paper_text)  # Returns a dict for single-string input
"""

PaperInput = Union[str, List[str]]
ReviewOutput = Union[Dict, List[Dict]]


def _extract_questions_from_content(content: str) -> List[str]:
    """
    Extract questions from the LLM intermediate output.
    Mirrors the reference logic with a few fallbacks.
    """
    questions: List[str] = []
    boxed = re.search(r"\\boxed_questions\{(.*?)\}", content, re.DOTALL)
    lines: List[str] = []
    if boxed:
        lines = [line.strip() for line in boxed.group(1).split("\n") if line.strip()]
    elif "❓ Questions" in content:
        lines = [line.strip() for line in content.split("❓ Questions", 1)[-1].split("\n") if line.strip()]
    elif "## Questions" in content:
        lines = [line.strip() for line in content.split("## Questions", 1)[-1].split("\n") if line.strip()]
    else:
        lines = [line.strip() for line in content.split("\n") if line.strip()]

    for line in lines:
        cleaned = line.lstrip("0123456789. ").strip()
        if cleaned and cleaned != "}":
            questions.append(cleaned)
    return list(dict.fromkeys(questions))


def _format_qa_text(questions: List[str], results: List[Dict]) -> str:
    parts: List[str] = []
    for idx, question in enumerate(questions):
        parts.append(f"## Question {idx + 1}:\n{question}")
        if idx < len(results) and results[idx]:
            result = results[idx]
            passages = result.get("final_passages", "N/A")
            answer = result.get("output", "N/A")
            parts.append(f"### Retrieved Passages:\n{passages}")
            parts.append(f"### Answer from OpenScholar:\n{answer}")
        else:
            parts.append("### Retrieved Passages:\nNo information retrieved.")
            parts.append("### Answer from OpenScholar:\nNo answer retrieved.")
        parts.append("**********")
    return "\n\n".join(parts)


class DeepReview:
    """
    Drop-in reimplementation of the DeepReviewer component.
    """

    def __init__(
        self,
        mode: str = "standard",
        model_size: str = "14B",
        custom_model_name: Optional[str] = None,
        device: str = "cuda",
        tensor_parallel_size: int = 1,
        gpu_memory_utilization: float = 0.95,
        max_model_len: int = 90000,
        retrieval_client: Optional[OpenScholarClient] = None,
        sampling_params_factory: Optional[Callable[[int], SamplingParams]] = None,
    ):
        self.default_mode = self._normalize_mode(mode)
        model_mapping = {
            "14B": "WestlakeNLP/DeepReviewer-14B",
            "7B": "WestlakeNLP/DeepReviewer-7B",
        }
        if custom_model_name:
            model_name = custom_model_name
        else:
            if model_size not in model_mapping:
                raise ValueError(f"Invalid model size. Choose from {list(model_mapping.keys())}")
            model_name = model_mapping[model_size]

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = LLM(
            model=model_name,
            tensor_parallel_size=tensor_parallel_size,
            max_model_len=max_model_len,
            gpu_memory_utilization=gpu_memory_utilization,
        )
        self.model_config = {
            "tensor_parallel_size": tensor_parallel_size,
            "gpu_memory_utilization": gpu_memory_utilization,
        }
        self.retrieval_client = retrieval_client or OpenScholarClient()
        self._sampling_params_factory = sampling_params_factory

    def __call__(self, paper_context: PaperInput, mode: Optional[str] = None, reviewer_num: int = 4, max_tokens: int = 35000) -> ReviewOutput:  # noqa: D401
        """
        Alias for evaluate to allow `dr(paper_text)`.
        """
        return self.evaluate(paper_context, mode=mode, reviewer_num=reviewer_num, max_tokens=max_tokens)

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        m = mode.strip().lower()
        if "fast" in m:
            return "Fast Mode"
        if "best" in m:
            return "Best Mode"
        return "Standard Mode"

    def _generate_system_prompt(self, mode: str, reviewer_num: int) -> str:
        simreviewer_prompt = "When you simulate different reviewers, write the sections in this order: Summary, Soundness, Presentation, Contribution, Strengths, Weaknesses, Suggestions, Questions, Rating and Confidence."
        if mode == "Best Mode":
            return (
                f"You are an expert academic reviewer tasked with providing a thorough and balanced evaluation of research papers. "
                f"Your thinking mode is Best Mode. In this mode, you should aim to provide the most reliable review results by conducting a thorough analysis of the paper. "
                f"I allow you to use search tools to obtain background knowledge about the paper - please provide three different questions. "
                f"I will help you with the search. After you complete your thinking, you should review by simulating {reviewer_num} different reviewers, "
                f"and use self-verification to double-check any paper deficiencies identified. Finally, provide complete review results."
            ) + simreviewer_prompt
        if mode == "Standard Mode":
            return (
                f"You are an expert academic reviewer tasked with providing a thorough and balanced evaluation of research papers. "
                f"Your thinking mode is Standard Mode. In this mode, you should review by simulating {reviewer_num} different reviewers, "
                f"and use self-verification to double-check any paper deficiencies identified. Finally, provide complete review results."
            ) + simreviewer_prompt
        if mode == "Fast Mode":
            return "You are an expert academic reviewer tasked with providing a thorough and balanced evaluation of research papers. Your thinking mode is Fast Mode. In this mode, you should quickly provide the review results."
        return "You are an expert academic reviewer tasked with providing a thorough and balanced evaluation of research papers."

    def _sampling_params(self, max_tokens: int) -> SamplingParams:
        if self._sampling_params_factory:
            return self._sampling_params_factory(max_tokens)
        return SamplingParams(temperature=0.4, top_p=0.95, max_tokens=max_tokens)

    def evaluate(self, paper_context: PaperInput, mode: Optional[str] = None, reviewer_num: int = 4, max_tokens: int = 35000) -> ReviewOutput:
        mode_used = self._normalize_mode(mode or self.default_mode)
        system_prompt = self._generate_system_prompt(mode_used, reviewer_num)

        if isinstance(paper_context, str):
            contexts = [paper_context]
            single_input = True
        elif isinstance(paper_context, list):
            contexts = paper_context
            single_input = False
        else:
            raise TypeError("paper_context must be a string or a list of strings.")

        results: List[Dict] = []
        batch_size = 10

        for idx in range(0, len(contexts), batch_size):
            batch = contexts[idx : idx + batch_size]
            if mode_used != "Best Mode":
                prompts = []
                for ctx in batch:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": ctx},
                    ]
                    prompts.append(
                        self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    )
                sampling_params = self._sampling_params(max_tokens)
                outputs = self.model.generate(prompts, sampling_params)
                for output in outputs:
                    generated_text = output.outputs[0].text
                    results.append(self._parse_review(generated_text))
            else:
                for ctx in batch:
                    step1_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": ctx},
                    ]
                    input_text_step1 = self.tokenizer.apply_chat_template(
                        step1_messages, tokenize=False, add_generation_prompt=True
                    )
                    outputs_step1 = self.model.generate([input_text_step1], self._sampling_params(max_tokens))
                    generated_text_step1 = outputs_step1[0].outputs[0].text

                    questions = _extract_questions_from_content(generated_text_step1)
                    if not questions:
                        results.append(self._parse_review(generated_text_step1))
                        continue

                    retrieved = self.retrieval_client.fetch(questions)
                    qa_text = _format_qa_text(questions, retrieved)

                    step2_messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": ctx},
                        {"role": "assistant", "content": generated_text_step1},
                        {"role": "user", "content": qa_text},
                    ]
                    input_text_step2 = self.tokenizer.apply_chat_template(
                        step2_messages, tokenize=False, add_generation_prompt=True
                    )
                    outputs_step2 = self.model.generate([input_text_step2], self._sampling_params(max_tokens))
                    generated_text_step2 = outputs_step2[0].outputs[0].text
                    results.append(self._parse_review(generated_text_step2))

        return results[0] if single_input else results

    def _parse_review(self, generated_text: str) -> Dict:
        result: Dict[str, Union[str, List, Dict]] = {"raw_text": generated_text, "reviews": [], "meta_review": {}, "decision": ""}

        meta_review_match = re.search(r"\\boxed_review\{(.*?)\n}", generated_text, re.DOTALL)
        if meta_review_match:
            section = meta_review_match.group(1).strip()
            result["meta_review"]["content"] = section
            summary_match = re.search(r"## Summary:\s+(.*?)(?=##|\Z)", section, re.DOTALL)
            if summary_match:
                result["meta_review"]["summary"] = summary_match.group(1).strip()
            rating_match = re.search(r"## Rating:\s+(.*?)(?=##|\Z)", section, re.DOTALL)
            if rating_match:
                rating_text = rating_match.group(1).strip()
                number_match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
                result["meta_review"]["rating"] = float(number_match.group(1)) if number_match else rating_text
            for section_name in ["Soundness", "Presentation", "Contribution", "Strengths", "Weaknesses", "Suggestions", "Questions"]:
                match = re.search(fr"## {section_name}:\s+(.*?)(?=##|\Z)", section, re.DOTALL)
                if match:
                    result["meta_review"][section_name.lower()] = match.group(1).strip()

        simreviewer_match = re.search(r"\\boxed_simreviewers\{(.*?)\n}", generated_text, re.DOTALL)
        if simreviewer_match:
            sim_text = simreviewer_match.group(1).strip()
            reviewer_sections = re.split(r"## Reviewer \d+", sim_text)
            if reviewer_sections and not reviewer_sections[0].strip():
                reviewer_sections = reviewer_sections[1:]
            for idx, section in enumerate(reviewer_sections):
                review: Dict[str, Union[str, float, int]] = {"reviewer_id": idx + 1, "text": section.strip()}
                summary_match = re.search(r"## Summary:\s+(.*?)(?=##|\Z)", section, re.DOTALL)
                if summary_match:
                    review["summary"] = summary_match.group(1).strip()
                rating_match = re.search(r"## Rating:\s+(.*?)(?=##|\Z)", section, re.DOTALL)
                if rating_match:
                    rating_text = rating_match.group(1).strip()
                    number_match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
                    review["rating"] = float(number_match.group(1)) if number_match else rating_text
                for section_name in ["Soundness", "Presentation", "Contribution", "Strengths", "Weaknesses", "Suggestions", "Questions"]:
                    match = re.search(fr"## {section_name}:\s+(.*?)(?=##|\Z)", section, re.DOTALL)
                    if match:
                        review[section_name.lower()] = match.group(1).strip()
                result["reviews"].append(review)

        decision_match = re.search(r"## Decision:\s*\n\s*(\w+)", generated_text)
        if decision_match:
            result["decision"] = decision_match.group(1).strip()

        return result