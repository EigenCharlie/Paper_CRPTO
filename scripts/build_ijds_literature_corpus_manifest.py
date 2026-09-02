"""Build the complete, deterministic IJDS literature-corpus manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from scripts.build_ijds_bibliography_views import (
    citation_keys,
    parse_bibtex_entries,
)
from src.utils.pipeline_runtime import atomic_write_text

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "Papers_tesis"
MASTER_BIBLIOGRAPHY = ROOT / "paper" / "references.bib"
CITATION_SOURCES = (
    ROOT / "paper" / "CRPTO_ijds.qmd",
    ROOT / "paper" / "supplement_ijds.qmd",
)
MANIFEST = ROOT / "configs" / "ijds_literature_corpus_manifest.json"

SNAPSHOT_DATE = "2026-09-01"
ALLOWED_OBJECT_STATUSES = {
    "current",
    "superseded",
    "companion",
    "watchlist",
    "quarantined",
    "legacy",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "under",
    "using",
    "via",
    "with",
    "without",
    "et",
    "al",
    "arxiv",
    "preprint",
    "paper",
    "proceedings",
}
ARXIV_IN_FILENAME = re.compile(r"arxiv[ _-]*(\d{4}\.\d{4,5})v(\d+)", re.IGNORECASE)
ARXIV_IN_TEXT = re.compile(r"arxiv(?:\.org/(?:abs|pdf)/|:)(\d{4}\.\d{4,5})v(\d+)", re.IGNORECASE)
MIN_AUTO_MATCH_SCORE = 0.60
MIN_AUTO_MATCH_MARGIN = 0.15


@dataclass(frozen=True)
class ObjectOverride:
    """Human-adjudicated identity or disposition for one local PDF object."""

    key: str | None
    status: str
    version: str
    note: str
    source_url: str | None = None


def _override(
    key: str | None,
    status: str = "current",
    version: str = "published",
    note: str = "Human-adjudicated filename-to-work identity.",
    source_url: str | None = None,
) -> ObjectOverride:
    return ObjectOverride(key, status, version, note, source_url)


AMBIGUOUS_MATCH_NOTE = (
    "Human-adjudicated title/author identity; the automatic candidate was below "
    "the declared score or runner-up-margin gate."
)


# Explicit overrides cover title abbreviations, close-title collisions, all
# multi-object papers, and every PDF that intentionally has no BibTeX key.
OBJECT_OVERRIDES: dict[str, ObjectOverride] = {
    # Every identity below was manually reconciled to the master title and
    # author list because the automatic score was <0.60 or its margin over the
    # runner-up was <0.15. They remain explicit so a future nearby title cannot
    # silently change the mapping.
    "paper/Angelopoulos et al 2024 - Conformal Risk Control.pdf": _override(
        "angelopoulos2024risk", version="unversioned local copy", note=AMBIGUOUS_MATCH_NOTE
    ),
    "paper/Barber et al 2021 - Limits of Distribution-Free Conditional Predictive Inference.pdf": _override(
        "barber2021limits", version="published version", note=AMBIGUOUS_MATCH_NOTE
    ),
    "paper/Donti et al 2017 - Task-Based End-to-End Model Learning.pdf": _override(
        "donti2017", version="unversioned local copy", note=AMBIGUOUS_MATCH_NOTE
    ),
    "paper/Patel et al 2024 - Conformal Contextual Robust Optimization.pdf": _override(
        "patel2024", version="unversioned local copy", note=AMBIGUOUS_MATCH_NOTE
    ),
    "supplement/Aldirawi Li Guo 2026 - Conformal Risk Control under Non-Monotone Losses - arXiv 2604.01502v2.pdf": _override(
        "aldirawi2026nonmonotone_crc",
        version="arXiv:2604.01502v2",
        note=AMBIGUOUS_MATCH_NOTE,
    ),
    "supplement/Bao et al 2025 - CROMS Optimal Model Selection for Conformalized Robust Optimization - arXiv 2507.04716v2.pdf": _override(
        "bao2025croms",
        version="arXiv:2507.04716v2",
        note="Downloaded exact v2 SHA-256 matched the pre-existing local bytes.",
        source_url="https://arxiv.org/abs/2507.04716v2",
    ),
    "supplement/Farinhas et al 2024 - Non-Exchangeable Conformal Risk Control.pdf": _override(
        "farinhas2024nonexchangeable_crc",
        version="unversioned local copy",
        note=AMBIGUOUS_MATCH_NOTE,
    ),
    "supplement/Gazin Heller Marandon Roquain 2025 - Informative Conformal Sets with FCR Control.pdf": _override(
        "gazin2025informative", version="published version", note=AMBIGUOUS_MATCH_NOTE
    ),
    "supplement/Gibbs Candes 2024 - Online Conformal Under Arbitrary Distribution Shifts.pdf": _override(
        "gibbs2024online", version="unversioned local copy", note=AMBIGUOUS_MATCH_NOTE
    ),
    "supplement/Guo 2026 - Learning Predictive Ambiguity Sets - arXiv 2607.09820v1.pdf": _override(
        "guo2026lpas", version="arXiv:2607.09820v1", note=AMBIGUOUS_MATCH_NOTE
    ),
    "supplement/Liu Grigas 2021 - Risk Bounds and Calibration for Smart Predict Then Optimize.pdf": _override(
        "liu2021riskbounds", version="unversioned local copy", note=AMBIGUOUS_MATCH_NOTE
    ),
    "supplement/Ovalle et al 2025 - Conformal Mixed-Integer Constraint Learning - NeurIPS.pdf": _override(
        "ovalle2025cmicl", version="published conference version", note=AMBIGUOUS_MATCH_NOTE
    ),
    "supplement/Xu et al 2024 - Profit- and risk-driven credit scoring under parameter uncertainty.pdf": _override(
        "xu2024profit_risk_credit", version="published version", note=AMBIGUOUS_MATCH_NOTE
    ),
    "supplement/Ziliaskopoulos Vinel Smith 2026 - Decision Value Attribution - arXiv 2606.29878v1.pdf": _override(
        "ziliaskopoulos2026dva",
        version="arXiv:2606.29878v1",
        note=AMBIGUOUS_MATCH_NOTE,
    ),
    "tesis/Cresswell et al 2024 - Conformal Prediction Sets Improve Human Decision Making.pdf": _override(
        "cresswell2024", version="unversioned local copy", note=AMBIGUOUS_MATCH_NOTE
    ),
    "paper/Angelopoulos et al 2025 - Learn Then Test.pdf": _override("angelopoulos2025ltt"),
    "paper/Delage Ye 2010 - Distributionally Robust Optimization Under Moment Uncertainty.pdf": _override(
        "delage2010dro"
    ),
    "paper/Hu et al 2026 - Conformal Robustness Control.pdf": _override("hu2026crc"),
    "paper/Serrano-Cinca Gutierrez-Nieto 2016 - Profit Scoring in P2P Lending.pdf": _override(
        "serrano2016profitscoring"
    ),
    "paper/Sun et al 2024 - Predict-then-Calibrate.pdf": _override("sun2024ptc"),
    "paper/Torkian Bamdad Sarfaraz 2025 - AI OR Investment Decisions in Digital Lending.pdf": _override(
        "aior2025lendingclub"
    ),
    "paper/Zhao et al 2026 - Conformal Robust Optimization and Satisficing.pdf": _override(
        "zhao2025robust"
    ),
    "paper/Zhao et al 2016 - Portfolio Selections in P2P Lending.pdf": _override(
        "zhao2016p2pportfolio"
    ),
    "supplement/Angelopoulos et al 2026 - Conformal Risk Control for Non-Monotonic Losses.pdf": _override(
        "angelopoulos2026nonmonotonic"
    ),
    "supplement/Ben-Tal Teboulle 2007 - Optimized Certainty Equivalent.pdf": _override(
        "bental2007oce"
    ),
    "supplement/CFPB 2014 - Public Information Proxy Race Ethnicity.pdf": _override("cfpb2014bisg"),
    "supplement/Cortes-Gomez et al 2025 - Utility-Directed Conformal Prediction - ICLR.pdf": _override(
        "cortesgomez2025utility",
        version="ICLR 2025",
        source_url="https://openreview.net/forum?id=iOMnn1hSBO",
    ),
    "supplement/Djeundje Crook Andreeva 2025 - Dynamic prediction of loan portfolio profitability.pdf": _override(
        "djeundje2025dynamic_loan_portfolio_profitability"
    ),
    "supplement/Guan 2023 - Localized Conformal Prediction.pdf": _override("guan2023localized"),
    "supplement/Gui Hore Ren Barber 2024 - Conformalized Survival Analysis with Adaptive Cutoffs.pdf": _override(
        "gui2024adaptive"
    ),
    "supplement/Gui Hore Ren Barber 2024 - Adaptive Cutoffs Supplementary Material.pdf": _override(
        "gui2024adaptive",
        status="companion",
        note="Published supplementary material accompanying the current article PDF.",
    ),
    "supplement/Kiyani et al 2025 - Decision Theoretic Foundations for Conformal Prediction.pdf": _override(
        "kiyani2025"
    ),
    "supplement/Kull Silva Filho Flach 2017 - Beta Calibration.pdf": _override("kull2017"),
    "supplement/Lakkaraju et al 2017 - The Selective Labels Problem.pdf": _override(
        "lakkaraju2017selective"
    ),
    "supplement/Lekeufack et al 2023 - Conformal Decision Theory.pdf": _override(
        "lekeufack2023cdt",
        version="ICRA 2024",
    ),
    "supplement/Lutzow et al 2026 - Multi-Variable Conformal Prediction - arXiv 2605.12341v1.pdf": _override(
        "lutzow2026mcp", version="arXiv:2605.12341v1"
    ),
    "supplement/Mandi et al 2024 - Decision-Focused Learning Survey.pdf": _override("mandi2024"),
    "supplement/Navas-Palencia 2020 - Optimal Binning - arXiv 2001.08025v3.pdf": _override(
        "navaspalencia2020", version="arXiv:2001.08025v3"
    ),
    "supplement/Sadana et al 2025 - A survey of contextual optimization methods.pdf": _override(
        "sadana2025contextual"
    ),
    "supplement/Van der Laan Alaa 2025 - Generalized Venn and Venn-Abers Calibration - ICML.pdf": _override(
        "vanderlaan2025generalized_venn", version="ICML 2025"
    ),
    "supplement/Wiberg Dai Lam Kulkarni 2025 - Synergizing AI and OR.pdf": _override(
        "wiberg2025ai_or"
    ),
    "supplement/Yeh et al 2025 - Conformal Risk Training.pdf": _override(
        "yeh2025training", version="NeurIPS 2025"
    ),
    "supplement/Zhao et al 2021 - Calibrating Predictions to Decisions.pdf": _override(
        "zhao2021decisioncalibration", version="NeurIPS 2021"
    ),
    "tesis/Babaei Bamdad 2020 - Multi-Objective Investment Recommendation in P2P Lending.pdf": _override(
        "babaei2020p2p"
    ),
    # Current exact versions pinned or promoted through 2026-08-09.
    "supplement/Liang Zhu Barber 2026 - Conformal Prediction after Data-Dependent Model Selection - arXiv 2408.07066v4 JASA.pdf": _override(
        "liang2026model_selection_conformal",
        version="arXiv:2408.07066v4 / JASA 2026 online first",
        source_url="https://arxiv.org/abs/2408.07066v4",
    ),
    "supplement/Yang Kuchibhotla 2025 - Selection and Aggregation of Conformal Prediction Sets - arXiv 2104.13871v3 JASA.pdf": _override(
        "yang2025selection_aggregation_conformal",
        version="arXiv:2104.13871v3 / JASA 2025",
        source_url="https://arxiv.org/abs/2104.13871v3",
    ),
    "supplement/Zhu Kiyani Pappas Hassani 2026 - Conformal Risk-Averse Decision Making with Action Conditional Guarantee - arXiv 2606.05551v2.pdf": _override(
        "zhu2026action_conditional_risk_averse",
        version="arXiv:2606.05551v2",
        source_url="https://arxiv.org/abs/2606.05551v2",
    ),
    "supplement/Hegazy et al 2025 - Valid Selection among Conformal Sets - arXiv 2506.20173v1.pdf": _override(
        "hegazy2025valid_selection_conformal_sets",
        status="superseded",
        version="arXiv:2506.20173v1",
        note="Superseded by the co-located NeurIPS 2025 proceedings object.",
        source_url="https://arxiv.org/abs/2506.20173v1",
    ),
    "supplement/Hegazy et al 2025 - Valid Selection among Conformal Sets - NeurIPS 2025.pdf": _override(
        "hegazy2025valid_selection_conformal_sets",
        version="NeurIPS 2025 proceedings / DOI 10.52202/085713-5812",
        source_url="https://proceedings.neurips.cc/paper_files/paper/2025/hash/ff9386992bb2b9cee1dddf0bd5f328de-Abstract-Conference.html",
    ),
    "supplement/Yeh et al 2025 - End-to-End Conformal Calibration for Optimization Under Uncertainty - arXiv 2409.20534v2 TMLR.pdf": _override(
        "yeh2026",
        version="arXiv:2409.20534v2 / TMLR December 2025",
        note="Downloaded exact v2 SHA-256 matched the pre-existing TMLR-banner local bytes.",
        source_url="https://arxiv.org/abs/2409.20534v2",
    ),
    "supplement/Zhou Orfanoudaki Zhu 2026 - Conformalized Decision Risk Assessment - arXiv 2505.13243v3.pdf": _override(
        "zhou2025credo",
        version="arXiv:2505.13243v3 / ICLR 2026",
        source_url="https://arxiv.org/abs/2505.13243v3",
    ),
    "supplement/Chen Zhou Zhu 2026 - Learning Polyhedral Conformal Sets for Robust Optimization - arXiv 2605.08506v2.pdf": _override(
        "chen2026polyhedral_conformal_ro",
        version="arXiv:2605.08506v2",
        source_url="https://arxiv.org/abs/2605.08506v2",
    ),
    "supplement/Wang Dobriban 2026 - Optimal Decision-Making Based on Prediction Sets - arXiv 2602.00989v3.pdf": _override(
        "wang2026optimal_decision_prediction_sets",
        version="arXiv:2602.00989v3",
        source_url="https://arxiv.org/abs/2602.00989v3",
    ),
    "supplement/Joshi Wang Hassani Dobriban 2026 - Risk-Controlled Post-Processing of Decision Policies - arXiv 2605.06479v1.pdf": _override(
        "joshi2026risk_controlled_postprocessing",
        version="arXiv:2605.06479v1",
        source_url="https://arxiv.org/abs/2605.06479v1",
    ),
    "supplement/Prinster et al 2026 - Conformal Policy Control - arXiv 2603.02196v3.pdf": _override(
        "cpc2026",
        version="arXiv:2603.02196v3 / ICML 2026",
        source_url="https://arxiv.org/abs/2603.02196v3",
    ),
    "supplement/Fannjiang et al 2022 - Conformal Prediction Under Feedback Covariate Shift - arXiv 2202.03613v5.pdf": _override(
        "fannjiang2022feedback",
        version="arXiv:2202.03613v5 / PNAS 2022",
        source_url="https://arxiv.org/abs/2202.03613v5",
    ),
    "supplement/Stanton Maddox Wilson 2023 - Bayesian Optimization with Conformal Prediction Sets - AISTATS.pdf": _override(
        "stanton2023feedback",
        version="AISTATS 2023 / PMLR 206",
        source_url="https://proceedings.mlr.press/v206/stanton23a.html",
    ),
    "supplement/Prinster Stanton Liu Saria 2024 - Conformal Validity Guarantees for Any Data Distribution - ICML.pdf": _override(
        "prinster2024feedback",
        version="ICML 2024 / PMLR 235",
        source_url="https://proceedings.mlr.press/v235/prinster24a.html",
    ),
    # Exact historical versions retained without being current evidence objects.
    "supplement/Baesens et al 2026 - Foundation Models for Credit Risk Prediction - arXiv 2605.18147v1.pdf": _override(
        "baesens2026foundation_credit_risk",
        status="superseded",
        version="arXiv:2605.18147v1",
        note="Superseded by the co-located v2 object.",
    ),
    "supplement/Baesens et al 2026 - Foundation Models for Credit Risk Prediction - arXiv 2605.18147v2.pdf": _override(
        "baesens2026foundation_credit_risk", version="arXiv:2605.18147v2"
    ),
    "supplement/Peng Lessmann 2026 - Incorporating Data Drift to Perform Survival Analysis on Credit Risk - arXiv 2601.20533v1.pdf": _override(
        "peng2026drift_survival",
        status="superseded",
        version="arXiv:2601.20533v1",
        note="Superseded by the co-located v2 object.",
    ),
    "supplement/Peng Lessmann 2026 - Incorporating Data Drift to Perform Survival Analysis on Credit Risk - arXiv 2601.20533v2.pdf": _override(
        "peng2026drift_survival", version="arXiv:2601.20533v2"
    ),
    "supplement/Yang Jin 2026 - Multi-Distribution Robust Conformal Prediction - arXiv 2601.02998v1.pdf": _override(
        "yang2026multidistribution",
        status="superseded",
        version="arXiv:2601.02998v1",
        note="Superseded by the co-located v2 object.",
    ),
    "supplement/Yang Jin 2026 - Multi-Distribution Robust Conformal Prediction - arXiv 2601.02998v2.pdf": _override(
        "yang2026multidistribution", version="arXiv:2601.02998v2"
    ),
    "supplement/Zhou Zhu 2025 - Calibrating Decision Robustness via Inverse Conformal Risk Control.pdf": _override(
        "zhou2026creme",
        status="superseded",
        version="arXiv:2510.07750v2",
        note="Superseded by the co-located exact v3 object.",
    ),
    "supplement/Zhou Zhu 2025 - Calibrating Decision Robustness via Inverse Conformal Risk Control - arXiv 2510.07750v3.pdf": _override(
        "zhou2026creme", version="arXiv:2510.07750v3"
    ),
    "supplement/Podkopaev Ramdas 2021 - Distribution-Free Uncertainty Quantification for Classification under Label Shift - UAI PMLR 161.pdf": _override(
        "podkopaev2021labelshift",
        version="UAI 2021 / PMLR 161:844--853",
        note="Official PMLR proceedings object; venue and pagination verified on the primary record.",
        source_url="https://proceedings.mlr.press/v161/podkopaev21a.html",
    ),
    "supplement/Ramos Graziadei Cabezas 2026 - Conformal Prediction via Transported Beta Laws - arXiv 2605.19024v1.pdf": _override(
        "ramos2026transported_beta",
        version="arXiv:2605.19024v1",
        source_url="https://arxiv.org/abs/2605.19024v1",
    ),
    "supplement/Xu Guo Wei 2026 - Selective Conformal Risk Control - arXiv 2512.12844v2.pdf": _override(
        "xu2026selective_crc",
        version="arXiv:2512.12844v2",
        source_url="https://arxiv.org/abs/2512.12844v2",
    ),
    "supplement/Zhou Fathony Nguyen Sesia 2026 - Audited Conformal Prediction for Classification under Unknown Distribution Shift - arXiv 2606.14909v1.pdf": _override(
        "zhou2026audited_cp",
        version="arXiv:2606.14909v1",
        note="Exact v1 bytes matched the previously local unversioned watchlist object.",
        source_url="https://arxiv.org/abs/2606.14909v1",
    ),
    # Audited nearby PDFs intentionally not promoted to the master bibliography.
    "supplement/Ding Fermanian Salmon 2026 - Conformal Prediction for Long-Tailed Classification.pdf": _override(
        None, "watchlist", "unkeyed local PDF", "Audited B-grade nearby method; not promoted."
    ),
    "supplement/Liu de Paula Tamer 2026 - Conformal Prediction with Interval Outcomes.pdf": _override(
        None, "watchlist", "unkeyed local PDF", "Audited B-grade nearby method; not promoted."
    ),
    "supplement/Solomon Roquain Rosset Heller 2026 - Informative Conformal Sets with FCR Control.pdf": _override(
        None, "watchlist", "unkeyed local PDF", "Audited B-grade nearby method; not promoted."
    ),
    "supplement/Wang Qiao 2025 - Conformal Prediction Under Generalized Covariate Shift.pdf": _override(
        None, "watchlist", "unkeyed local PDF", "Audited B-grade nearby method; not promoted."
    ),
    "supplement/Zecchin et al 2025 - Weighted Conformal Risk Control Under Covariate Shift.pdf": _override(
        None, "watchlist", "unkeyed local PDF", "Audited B-grade nearby method; not promoted."
    ),
    "supplement/Alberge et al 2026 - Calibration of Survival Models with Competing Risks.pdf": _override(
        None, "quarantined", "unkeyed local PDF", "C-grade corpus object; supports no active claim."
    ),
    "supplement/Farina Tchetgen Tchetgen Kuchibhotla 2026 - Doubly Robust Calibration for Right-Censored Outcomes.pdf": _override(
        None, "quarantined", "unkeyed local PDF", "C-grade corpus object; supports no active claim."
    ),
    "supplement/Sesia Svetnik 2025 - Conformal Survival Bands Under Right Censoring.pdf": _override(
        None, "quarantined", "unkeyed local PDF", "C-grade corpus object; supports no active claim."
    ),
    # Six legacy objects are now explicitly resolved rather than silently orphaned.
    "supplement/Deprez et al 2026 - Network Analytics for Anti-money Laundering.pdf": _override(
        None,
        "legacy",
        "unkeyed local PDF",
        "Legacy domain-context object; not used by the IJDS manuscript.",
    ),
    "supplement/Fuk Nagaev 1971 - Probability Inequalities for Sums of Independent Random Variables.pdf": _override(
        None,
        "legacy",
        "unkeyed local PDF",
        "Legacy probability reference; not used by the IJDS manuscript.",
    ),
    "supplement/Hand Henley 1997 - Statistical Classification Methods in Consumer Credit Scoring.pdf": _override(
        None,
        "legacy",
        "unkeyed local PDF",
        "Legacy credit-scoring review; not used by the IJDS manuscript.",
    ),
    "supplement/Izbicki Shimizu Stern 2022 - CD-split and HPD-split.pdf": _override(
        None,
        "legacy",
        "unkeyed local PDF",
        "Legacy conformal reference; not used by the IJDS manuscript.",
    ),
    "supplement/Lei et al 2018 - Distribution-Free Predictive Inference for Regression.pdf": _override(
        None,
        "legacy",
        "unkeyed local PDF",
        "Legacy conformal reference; not used by the IJDS manuscript.",
    ),
    "supplement/Shafer Vovk 2008 - A Tutorial on Conformal Prediction.pdf": _override(
        None, "legacy", "unkeyed local PDF", "Legacy tutorial; not used by the IJDS manuscript."
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _field(entry_text: str, name: str) -> str:
    match = re.search(
        rf"(?ims)^\s*{re.escape(name)}\s*=\s*\{{(.*?)\}}\s*,?\s*$",
        entry_text,
    )
    return match.group(1).strip() if match is not None else ""


def _words(value: str) -> tuple[str, ...]:
    value = re.sub(r"\\[A-Za-z]+\s*", " ", value)
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return tuple(re.findall(r"[a-z0-9]+", normalized.casefold()))


def _title_tokens(value: str) -> set[str]:
    return set(_words(value)).difference(STOPWORDS)


def _surnames(author_field: str) -> set[str]:
    surnames: set[str] = set()
    for person in re.split(r"\s+and\s+", author_field):
        person = person.strip("{} ")
        if not person:
            continue
        surname = person.split(",", 1)[0] if "," in person else person.split()[-1]
        surnames.update(_words(surname))
    return surnames


def _default_version(path: Path, entry_text: str) -> str:
    if match := ARXIV_IN_FILENAME.search(path.stem):
        return f"arXiv:{match.group(1)}v{match.group(2)}"
    joined = " ".join((_field(entry_text, "url"), _field(entry_text, "note")))
    if match := ARXIV_IN_TEXT.search(joined):
        return f"arXiv:{match.group(1)}v{match.group(2)}"
    if any(token in path.stem.casefold() for token in ("icml", "neurips", "aistats")):
        return "published conference version"
    if _field(entry_text, "doi"):
        return "published version"
    return "unversioned local copy"


def _match_key(
    path: Path,
    metadata: dict[str, dict[str, Any]],
) -> tuple[str, float, float]:
    filename_tokens = _title_tokens(path.stem)
    candidates: list[tuple[float, str]] = []
    for key, fields in metadata.items():
        title_tokens = fields["title_tokens"]
        if not title_tokens:
            continue
        overlap = title_tokens.intersection(filename_tokens)
        title_recall = len(overlap) / len(title_tokens)
        title_precision = len(overlap) / max(1, len(filename_tokens))
        author_recall = len(fields["surnames"].intersection(filename_tokens)) / max(
            1, len(fields["surnames"])
        )
        score = 0.65 * title_recall + 0.10 * title_precision + 0.25 * author_recall
        candidates.append((score, key))
    if len(candidates) < 2:
        raise RuntimeError("The bibliography does not contain enough candidates to match PDFs.")
    candidates.sort(reverse=True)
    best_score, best_key = candidates[0]
    margin = best_score - candidates[1][0]
    if best_score < MIN_AUTO_MATCH_SCORE or margin < MIN_AUTO_MATCH_MARGIN:
        raise RuntimeError(
            f"Low-confidence PDF identity for {_relative(path)}: {best_key} "
            f"(score={best_score:.3f}, margin={margin:.3f}; required "
            f"score>={MIN_AUTO_MATCH_SCORE:.2f}, margin>={MIN_AUTO_MATCH_MARGIN:.2f}). "
            "Add an explicit OBJECT_OVERRIDES adjudication."
        )
    return best_key, best_score, margin


def _inspect_pdf(path: Path) -> tuple[int, bool]:
    reader = PdfReader(path, strict=True)
    pages = len(reader.pages)
    if pages < 1:
        raise RuntimeError(f"PDF has no pages: {_relative(path)}")
    # Touch every page dictionary so malformed page trees fail during generation.
    for page in reader.pages:
        _ = page.mediabox
    return pages, bool(reader.is_encrypted)


def build_manifest(*, root: Path = ROOT, check: bool = False) -> bool:
    """Build or check the complete local-PDF and bibliography projection."""
    corpus_root = root / CORPUS_ROOT.relative_to(ROOT)
    master = root / MASTER_BIBLIOGRAPHY.relative_to(ROOT)
    citation_sources = tuple(root / path.relative_to(ROOT) for path in CITATION_SOURCES)
    output = root / MANIFEST.relative_to(ROOT)

    entries = parse_bibtex_entries(master.read_text(encoding="utf-8"))
    metadata: dict[str, dict[str, Any]] = {}
    for entry in entries:
        title = _field(entry.text, "title")
        author = _field(entry.text, "author")
        metadata[entry.key] = {
            "title": title,
            "year": _field(entry.text, "year"),
            "url": _field(entry.text, "url") or None,
            "title_tokens": _title_tokens(title),
            "surnames": _surnames(author),
            "entry_text": entry.text,
        }

    cited = {
        key
        for source in citation_sources
        for key in citation_keys(source.read_text(encoding="utf-8"))
    }
    missing_citations = sorted(cited.difference(metadata))
    if missing_citations:
        raise RuntimeError(f"Citations missing from master bibliography: {missing_citations!r}")

    objects: list[dict[str, Any]] = []
    for path in sorted(corpus_root.rglob("*.pdf"), key=lambda item: item.as_posix().casefold()):
        corpus_relative = path.relative_to(corpus_root).as_posix()
        override = OBJECT_OVERRIDES.get(corpus_relative)
        if override is not None:
            key = override.key
            status = override.status
            version = override.version
            note = override.note
            source_url = override.source_url or (metadata[key]["url"] if key is not None else None)
            match_method = "explicit"
            match_score: float | None = None
            match_margin: float | None = None
        else:
            key, match_score, match_margin = _match_key(path, metadata)
            status = "current"
            version = _default_version(path, metadata[key]["entry_text"])
            note = "Deterministic title-and-author match; unique current object enforced below."
            source_url = metadata[key]["url"]
            match_method = "title-author"

        if status not in ALLOWED_OBJECT_STATUSES:
            raise RuntimeError(f"Unsupported object status {status!r} for {corpus_relative}")
        if key is not None and key not in metadata:
            raise RuntimeError(f"Unknown BibTeX key {key!r} for {corpus_relative}")
        if key is None and status not in {"watchlist", "quarantined", "legacy"}:
            raise RuntimeError(f"Unkeyed object has invalid status {status!r}: {corpus_relative}")

        pages, encrypted = _inspect_pdf(path)
        if encrypted:
            raise RuntimeError(f"Encrypted corpus PDF: {corpus_relative}")
        objects.append(
            {
                "path": _relative(path),
                "bibtex_key": key,
                "status": status,
                "version": version,
                "bytes": path.stat().st_size,
                "pages": pages,
                "sha256": _sha256(path),
                "strict_pypdf": "pass",
                "encrypted": encrypted,
                "source_url": source_url,
                "match_method": match_method,
                "match_score": round(match_score, 6) if match_score is not None else None,
                "match_margin": round(match_margin, 6) if match_margin is not None else None,
                "note": note,
            }
        )

    override_paths = set(OBJECT_OVERRIDES)
    object_paths = {
        Path(item["path"]).relative_to(CORPUS_ROOT.relative_to(ROOT)).as_posix() for item in objects
    }
    stale_overrides = sorted(override_paths.difference(object_paths))
    if stale_overrides:
        raise RuntimeError(f"Manifest overrides reference missing PDFs: {stale_overrides!r}")

    hash_counts = Counter(item["sha256"] for item in objects)
    duplicate_hashes = sorted(value for value, count in hash_counts.items() if count > 1)
    current_by_key: dict[str, list[str]] = defaultdict(list)
    all_by_key: dict[str, list[str]] = defaultdict(list)
    for item in objects:
        key = item["bibtex_key"]
        if key is None:
            continue
        all_by_key[key].append(item["path"])
        if item["status"] == "current":
            current_by_key[key].append(item["path"])
    duplicate_current_keys = {
        key: paths for key, paths in sorted(current_by_key.items()) if len(paths) != 1
    }
    if duplicate_hashes:
        raise RuntimeError(f"Duplicate PDF hashes in corpus: {duplicate_hashes!r}")
    if duplicate_current_keys:
        raise RuntimeError(f"Keys without exactly one current PDF: {duplicate_current_keys!r}")

    bibliography: list[dict[str, Any]] = []
    for entry in entries:
        current_paths = current_by_key.get(entry.key, [])
        paths = sorted(all_by_key.get(entry.key, []))
        bibliography.append(
            {
                "bibtex_key": entry.key,
                "title": metadata[entry.key]["title"],
                "year": metadata[entry.key]["year"],
                "citation_state": "active" if entry.key in cited else "reserve",
                "corpus_status": "current" if current_paths else "metadata-only",
                "current_pdf": current_paths[0] if current_paths else None,
                "object_paths": paths,
                "metadata_only_reason": (
                    None
                    if current_paths
                    else (
                        "Approved active historical or foundational metadata-only exception."
                        if entry.key in cited
                        else "Reserve entry; acquire and validate an exact PDF only upon promotion."
                    )
                ),
            }
        )

    status_counts = Counter(item["status"] for item in objects)
    citation_counts = Counter(item["citation_state"] for item in bibliography)
    corpus_counts = Counter(item["corpus_status"] for item in bibliography)
    active_without_current = sorted(
        item["bibtex_key"]
        for item in bibliography
        if item["citation_state"] == "active" and item["corpus_status"] == "metadata-only"
    )
    payload = {
        "schema_version": "1.0",
        "snapshot_date": SNAPSHOT_DATE,
        "generated_by": "scripts/build_ijds_literature_corpus_manifest.py",
        "scope": {
            "corpus_root": _relative(corpus_root),
            "master_bibliography": _relative(master),
            "citation_sources": [_relative(path) for path in citation_sources],
            "protected_extraction_manifest_modified": False,
        },
        "summary": {
            "pdf_objects": len(objects),
            "pdf_pages": sum(item["pages"] for item in objects),
            "pdf_bytes": sum(item["bytes"] for item in objects),
            "unique_sha256": len(hash_counts),
            "object_status_counts": dict(sorted(status_counts.items())),
            "bibliography_entries": len(bibliography),
            "citation_state_counts": dict(sorted(citation_counts.items())),
            "bibliography_corpus_status_counts": dict(sorted(corpus_counts.items())),
            "active_metadata_only_keys": active_without_current,
        },
        "validation": {
            "all_pdf_objects_in_manifest": len(objects) == len(list(corpus_root.rglob("*.pdf"))),
            "all_object_paths_unique": len(objects) == len({item["path"] for item in objects}),
            "all_hashes_unique": not duplicate_hashes,
            "all_pdfs_parse_strictly": all(item["strict_pypdf"] == "pass" for item in objects),
            "no_encrypted_pdfs": not any(item["encrypted"] for item in objects),
            "all_keyed_current_objects_unique": not duplicate_current_keys,
            "all_active_keys_current_or_explicit_metadata_only": all(
                item["corpus_status"] in {"current", "metadata-only"}
                for item in bibliography
                if item["citation_state"] == "active"
            ),
            "missing_citation_keys": missing_citations,
            "stale_object_overrides": stale_overrides,
        },
        "bibliography": bibliography,
        "objects": objects,
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if check:
        return output.is_file() and output.read_text(encoding="utf-8") == rendered
    atomic_write_text(output, rendered)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the manifest is stale")
    args = parser.parse_args(argv)
    current = build_manifest(check=args.check)
    if args.check and not current:
        print("stale IJDS literature corpus manifest")
        return 1
    print(
        "IJDS literature corpus manifest is current"
        if args.check
        else "IJDS literature corpus manifest generated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
