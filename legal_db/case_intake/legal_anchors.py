from __future__ import annotations

from dataclasses import dataclass

from legal_db.case_intake.analyzer import CaseAnalysis
from legal_db.retrieval.staging import SearchResult


BNS_SOURCE = "https://www.mha.gov.in/sites/default/files/250883_english_01042024.pdf"
BSA_SOURCE = "https://www.indiacode.nic.in/bitstream/123456789/20063/1/a2023-47.pdf"
BNSS_SOURCE = "https://www.indiacode.nic.in/bitstream/123456789/20335/1/a2023-46.pdf"


@dataclass(frozen=True)
class LegalAnchor:
    key: str
    issue_tags: tuple[str, ...]
    title: str
    snippet: str
    source_url: str
    priority: int

    def to_result(self) -> SearchResult:
        return SearchResult(
            source_type="LEGAL_ANCHOR",
            title=self.title,
            snippet=self.snippet,
            score=round(1.0 - (self.priority * 0.01), 6),
            source_url=self.source_url,
            metadata={"anchor_key": self.key, "priority": self.priority},
        )


LEGAL_ANCHORS: tuple[LegalAnchor, ...] = (
    LegalAnchor(
        key="bns_34_private_defence",
        issue_tags=("PRIVATE_DEFENCE",),
        title="BNS Section 34: Things done in private defence",
        snippet=(
            "Core defence provision: an act done in exercise of the right of private "
            "defence is not an offence, subject to the statutory limits."
        ),
        source_url=BNS_SOURCE,
        priority=1,
    ),
    LegalAnchor(
        key="bns_35_body_property",
        issue_tags=("PRIVATE_DEFENCE",),
        title="BNS Section 35: Right of private defence of body and property",
        snippet=(
            "Recognises the right to defend one's body and property, and the body and "
            "property of another person."
        ),
        source_url=BNS_SOURCE,
        priority=2,
    ),
    LegalAnchor(
        key="bns_37_limits",
        issue_tags=("PRIVATE_DEFENCE", "MURDER_CHARGE"),
        title="BNS Section 37: Limits on private defence",
        snippet=(
            "Critical prosecution issue: private defence does not extend to more harm "
            "than necessary and is restricted where there is time to seek public authority."
        ),
        source_url=BNS_SOURCE,
        priority=3,
    ),
    LegalAnchor(
        key="bns_38_body_death",
        issue_tags=("PRIVATE_DEFENCE", "MURDER_CHARGE"),
        title="BNS Section 38: Private defence of body extending to causing death",
        snippet=(
            "Applies when the assault reasonably causes apprehension of death or grievous "
            "hurt, subject to the limits in Section 37."
        ),
        source_url=BNS_SOURCE,
        priority=4,
    ),
    LegalAnchor(
        key="bns_41_property_death",
        issue_tags=("PRIVATE_DEFENCE", "NIGHT_HOUSE_BREAKING"),
        title="BNS Section 41: Private defence of property extending to causing death",
        snippet=(
            "Important for night break-in facts: the right may extend to causing death for "
            "robbery, house-breaking after sunset and before sunrise, and certain dangerous "
            "property offences."
        ),
        source_url=BNS_SOURCE,
        priority=5,
    ),
    LegalAnchor(
        key="bns_43_property_continuance",
        issue_tags=("PRIVATE_DEFENCE", "NIGHT_HOUSE_BREAKING"),
        title="BNS Section 43: Commencement and continuance of property defence",
        snippet=(
            "For house-breaking after sunset and before sunrise, the property-defence "
            "right continues while the house-trespass begun by that house-breaking continues."
        ),
        source_url=BNS_SOURCE,
        priority=6,
    ),
    LegalAnchor(
        key="bns_101_exception_2",
        issue_tags=("PRIVATE_DEFENCE", "MURDER_CHARGE", "CULPABLE_HOMICIDE"),
        title="BNS Section 101 Exception 2: Excess of private defence",
        snippet=(
            "Fallback defence: if private defence was exercised in good faith but exceeded "
            "legal power, without premeditation and without intent to do more harm than "
            "necessary, culpable homicide is not murder."
        ),
        source_url=BNS_SOURCE,
        priority=7,
    ),
    LegalAnchor(
        key="bns_103_murder_punishment",
        issue_tags=("MURDER_CHARGE",),
        title="BNS Section 103: Punishment for murder",
        snippet=(
            "Likely police charge provision where the allegation is murder; punishment is "
            "death or imprisonment for life and fine."
        ),
        source_url=BNS_SOURCE,
        priority=8,
    ),
    LegalAnchor(
        key="bns_105_culpable_homicide",
        issue_tags=("CULPABLE_HOMICIDE", "MURDER_CHARGE"),
        title="BNS Section 105: Punishment for culpable homicide not amounting to murder",
        snippet=(
            "Relevant if murder is reduced because an exception applies, including excess "
            "private defence or other facts showing no murder-level intention."
        ),
        source_url=BNS_SOURCE,
        priority=9,
    ),
    LegalAnchor(
        key="bns_329_330_331_house_breaking",
        issue_tags=("NIGHT_HOUSE_BREAKING",),
        title="BNS Sections 329-331: House-trespass, house-breaking and night house-breaking",
        snippet=(
            "Frames the intruder's conduct: criminal trespass, house-trespass, house-breaking "
            "and aggravated punishment for house-breaking after sunset and before sunrise."
        ),
        source_url=BNS_SOURCE,
        priority=10,
    ),
    LegalAnchor(
        key="bns_3_5_common_intention",
        issue_tags=("MURDER_CHARGE",),
        title="BNS Section 3(5): Common intention",
        snippet=(
            "May be alleged where more than one person participated. The defence should show "
            "the son's role was restraint/protection, not a shared intention to kill."
        ),
        source_url=BNS_SOURCE,
        priority=11,
    ),
    LegalAnchor(
        key="bsa_63_electronic_records",
        issue_tags=("PRIVATE_DEFENCE", "NIGHT_HOUSE_BREAKING"),
        title="BSA Section 63: Admissibility of electronic records",
        snippet=(
            "Relevant for CCTV/DVR footage. Preserve the original device/files and arrange "
            "the required electronic-record certificate through counsel."
        ),
        source_url=BSA_SOURCE,
        priority=12,
    ),
    LegalAnchor(
        key="bnss_340_341_defence_legal_aid",
        issue_tags=("CRIMINAL", "MURDER_CHARGE"),
        title="BNSS Sections 340-341: Defence by advocate and legal aid",
        snippet=(
            "An accused may be defended by an advocate of choice, and if lacking means, "
            "the Court can assign an advocate at State expense."
        ),
        source_url=BNSS_SOURCE,
        priority=13,
    ),
)


def anchor_results_for_analysis(analysis: CaseAnalysis, limit: int = 8) -> list[SearchResult]:
    issues = set(analysis.issue_tags)
    matched = [
        anchor
        for anchor in LEGAL_ANCHORS
        if issues.intersection(anchor.issue_tags)
    ]
    matched.sort(key=lambda anchor: anchor.priority)
    return [anchor.to_result() for anchor in matched[: max(limit, 0)]]


def anchor_query_terms(analysis: CaseAnalysis) -> list[str]:
    issues = set(analysis.issue_tags)
    terms: list[str] = []
    if {"PRIVATE_DEFENCE", "MURDER_CHARGE", "NIGHT_HOUSE_BREAKING"} & issues:
        terms.extend(
            [
                "BNS sections 34 35 37 38 41 43 private defence body property",
                "house-breaking after sunset before sunrise",
                "murder culpable homicide not amounting to murder sections 101 103 105",
                "CCTV electronic records BSA section 63",
                "legal aid accused BNSS sections 340 341",
            ]
        )
    return terms
