"""
QA criteria catalog for W3/Bilateral result assessment (P2-3150).

Transcribed from:
  - "W3 MDS QA Criteria.docx"  -> field-level criteria, core/non-core, flag conditions
  - "W3_Evidence_Rule.pdf"     -> Phase 2 evidence checks (post-submission QA)

Each criterion is one thing that can raise a flag. Flags roll up to section
verdicts and then to the overall verdict in `aggregation.py`, following the
"Traffic light at submission" rule at the end of the criteria document.

`check` says who resolves the criterion:
  CODE     - deterministic, no model involved
  LLM      - requires judgement over metadata and/or scraped evidence text
  EXTERNAL - requires a data source we do not have in-process (see NOT_VERIFIABLE)
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


class Section(str, Enum):
    """The five sections of AC2. Values are the Reporting Tool contract keys."""
    GENERAL_INFORMATION = "general_information"
    CONTRIBUTORS_PARTNERS = "contributors_and_partners"
    GEOGRAPHIC_LOCATION = "geographic_location"
    EVIDENCE = "evidence"
    TYPE_SPECIFIC = "type_specific"

    @property
    def label(self) -> str:
        return SECTION_LABELS[self]


SECTION_LABELS = {
    Section.GENERAL_INFORMATION: "General Information",
    Section.CONTRIBUTORS_PARTNERS: "Contributors & Partners",
    Section.GEOGRAPHIC_LOCATION: "Geographic Location",
    Section.EVIDENCE: "Evidence",
    Section.TYPE_SPECIFIC: "Type-Specific Details",
}


class Check(str, Enum):
    CODE = "code"
    LLM = "llm"
    EXTERNAL = "external"


class OnAbsent(str, Enum):
    """What it means when the field the criterion reads is not in the payload.

    Optional fields must never be treated as failures: a field the user was never
    required to fill cannot be a quality problem. But absence IS the flag for
    mandatory fields, so the two cases must not be collapsed.
    """
    FLAG = "flag"              # "Flag if absent" - absence is the defect
    CONDITIONAL = "conditional"  # absence flags only if another condition holds
    GREY = "grey"              # not evaluable, but surfaced to the user as such
    OMIT = "omit"              # optional field absent - not rendered at all


class Needs(str, Enum):
    """What input the criterion has to see. Drives which LLM call owns it."""
    METADATA = "metadata"
    EVIDENCE_CONTENT = "evidence_content"
    EVIDENCE_LINKS = "evidence_links"


ALL_TYPES = "*"

# Criteria whose field is optional, or whose absence only matters conditionally.
# Everything not listed defaults to OnAbsent.FLAG ("Flag if absent").
ABSENCE_SEMANTICS = {
    # --- optional fields: absent means nothing to evaluate, never a flag -----
    # "Flag if field is filled but incoherently" - only assessable when present.
    "generic.toc_link.coherence": "omit",
    # "Monetary value of use where available."
    "innovuse.usd_spend.coherence": "omit",
    # Only applies from IRL 5 upward.
    "innovdev.evidence.geolocation_irl5": "omit",
    # Evidence not required unless an impact area scores 2.
    "capsharing.evidence.ia_score2_required": "grey",
    # Impact area tags are optional in the Reporting Tool form.
    # Optional in bilateral results. Reporting is explicit: when impact areas do
    # not arrive, nothing is shown and nothing is penalised - so these are omitted
    # from the assessment entirely rather than surfaced as grey.
    "generic.impact_area.plausibility": "omit",
    "generic.impact_area.score2_evidence": "omit",
    "generic.impact_area.score2_subcomponent": "omit",
    "generic.impact_area.gender_score2_differential": "omit",

    # --- conditional: absence flags only if something else is true ----------
    "generic.geographic_focus.presence": "conditional",      # unless virtual delivery
    "generic.internal_collaboration.presence": "conditional",  # if description implies it
    "generic.partner_collaboration.presence": "conditional",   # if description names partners
    "innovuse.other_measure.presence": "conditional",          # if description implies scale
}

POLICY_CHANGE = "policy change"
INNOVATION_USE = "innovation use"
OTHER_OUTCOME = "other outcome"
CAPACITY_SHARING = "capacity sharing for development"
KNOWLEDGE_PRODUCT = "knowledge product"
INNOVATION_DEV = "innovation development"
OTHER_OUTPUT = "other output"


@dataclass(frozen=True)
class Criterion:
    id: str
    mds_field: str
    section: Section
    core: bool
    check: Check
    needs: Needs
    criterion: str
    flag_when: str
    applies_to: tuple = (ALL_TYPES,)
    on_absent: "OnAbsent" = None
    # Capacity Sharing evidence is core only when an impact area scores 2.
    core_when: Optional[str] = None
    notes: str = ""

    def __post_init__(self):
        if self.on_absent is None:
            object.__setattr__(self, "on_absent", OnAbsent(ABSENCE_SEMANTICS.get(self.id, "flag")))

    def applies(self, result_type: str) -> bool:
        return ALL_TYPES in self.applies_to or result_type.lower() in self.applies_to


# ---------------------------------------------------------------------------
# 1. Generic MDS fields - all indicator types
# ---------------------------------------------------------------------------

GENERIC = [
    Criterion(
        id="generic.title.max_words",
        mds_field="Title",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        criterion="Max. 30 words.",
        flag_when="Title exceeds 30 words.",
    ),
    Criterion(
        id="generic.title.quality",
        mds_field="Title",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion=(
            "Clear and informative - names the result being reported, not the activity "
            "that produced it. Understandable to a non-specialist reader; no acronyms. "
            "Concise and distinct from the result description."
        ),
        flag_when="Flag if unclear, generic, uses acronyms.",
    ),
    Criterion(
        id="generic.description.min_words",
        mds_field="Result description",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        criterion="Description carries enough substance to be assessable.",
        flag_when="Flag if <50 words.",
    ),
    Criterion(
        id="generic.description.max_words",
        mds_field="Result description",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        criterion="Max ~300 words.",
        flag_when="Description exceeds ~300 words.",
    ),
    Criterion(
        id="generic.description.future_tense",
        mds_field="Result description",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        criterion="Describes a completed result, not a plan.",
        flag_when='Flag if future-tense language ("will", "planned to").',
    ),
    Criterion(
        id="generic.description.quality",
        mds_field="Result description",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion=(
            "Meaningful, specific content - not a copy of title or placeholder. "
            "Describes a completed result, not a plan, process, or activity. "
            "Understandable to non-specialist; no acronyms."
        ),
        flag_when="Flag if placeholder, duplicate of title, or describes an activity/plan.",
    ),
    Criterion(
        id="generic.description.cgiar_contribution",
        mds_field="Result description",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion="CGIAR/Center contribution stated explicitly.",
        flag_when="Flag if CGIAR/Center contribution is not stated.",
    ),
    Criterion(
        id="generic.toc_link.coherence",
        mds_field="ToC link (SP/A)",
        # The criteria document lists no sections; the Reporting Tool payload nests
        # theory_of_change under contributors_and_partners, and the section verdict
        # must match what the user sees in the form.
        section=Section.CONTRIBUTORS_PARTNERS,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion=(
            "Planned: logically fits WP/HLO/indicator. "
            'Unplanned: "Why" explanation is coherent; HLO/Outcome is logical.'
        ),
        flag_when=(
            "Flag if field is filled but incoherently with the description, "
            "and if planned/unplanned rationale is incoherent."
        ),
    ),
    Criterion(
        id="generic.impact_area.plausibility",
        mds_field="Impact area tags",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion=(
            "Selection consistent with indicator type, description, and evidence. "
            "Score scale: 0 = not relevant; 1 = contributes; 2 = strong/direct contribution, "
            "evidence required. Plausibility check: e.g. crop-science training -> likely "
            "Food/Water IA, not GESI unless women/youth focus is documented."
        ),
        flag_when="Flag if the selected score is implausible for the described result.",
    ),
    Criterion(
        id="generic.impact_area.score2_evidence",
        mds_field="Impact area tags",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        criterion=(
            "Score = 2 requires at least one IA-specific evidence item linked, "
            "identified by the evidence tag that maps to that impact area."
        ),
        flag_when="Flag if score = 2 and no IA-specific evidence linked.",
        notes=(
            "NOT evaluated for impact areas in vocabularies.IMPACT_AREAS_WITHOUT_TAG. "
            "Climate adaptation and mitigation is a pillar with no corresponding "
            "evidence tag, so no item can ever be marked climate-specific and the "
            "criterion could never be cleared - it would flag every Climate = 2 "
            "result systematically. Conversely the Youth tag maps to Gender, where "
            "it is seeded as a subcomponent."
        ),
    ),
    Criterion(
        id="generic.impact_area.score2_subcomponent",
        mds_field="Impact area tags",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        criterion="Score = 2 requires a thematic subcomponent selected.",
        flag_when="Flag if score = 2 and no thematic subcomponent selected.",
    ),
    Criterion(
        id="generic.impact_area.gender_score2_differential",
        mds_field="Impact area tags",
        section=Section.GENERAL_INFORMATION,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion=(
            "For Gender IA: disaggregated data alone is not sufficient - must demonstrate "
            "differential impact or targeted outcome for women/youth."
        ),
        flag_when=(
            "Flag if Gender score = 2 and only disaggregated numbers provided "
            "(no differential outcome)."
        ),
    ),
    Criterion(
        id="generic.internal_collaboration.presence",
        mds_field="Internal collaboration",
        section=Section.CONTRIBUTORS_PARTNERS,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion="Link to Center, Program, Accelerator, or Project populated where relevant.",
        flag_when="Flag if absent and description implies multi-entity collaboration.",
    ),
    Criterion(
        id="generic.partner_collaboration.presence",
        mds_field="Partner collaboration",
        section=Section.CONTRIBUTORS_PARTNERS,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion=(
            "External partner named where result involved non-CGIAR co-delivery. "
            "Not required if independently produced."
        ),
        flag_when="Flag if description names partners but field empty.",
    ),
    Criterion(
        id="generic.geographic_focus.presence",
        mds_field="Geographic focus",
        section=Section.GEOGRAPHIC_LOCATION,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        criterion=(
            "Geographic selection present. "
            '"Yet to be determined" valid if matches description and evidence. '
            "Virtual delivery -> no geographic selection required."
        ),
        flag_when='Flag if absent, unless delivery method is exactly "Virtual / Online".',
        notes=(
            "Use vocabularies.waives_geography, which matches exactly. "
            '"Blended (in-person and virtual)" contains the substring "virtual" but '
            "keeps an in-person component, so geography stays required - any "
            "contains/startswith test silently exempts it."
        ),
    ),
    Criterion(
        id="generic.geographic_focus.consistency",
        mds_field="Geographic focus",
        section=Section.GEOGRAPHIC_LOCATION,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        criterion=(
            "Scale (global/regional/national/sub-national) plausible for result. "
            "For blended: geography = where majority of in-person activity took place. "
            "Country list consistent with description."
        ),
        flag_when="Flag if inconsistent with description.",
    ),
    Criterion(
        id="generic.evidence.max_items",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        criterion="Max 6 items. List most to least important.",
        flag_when="Flag if more than 6 evidence items submitted.",
    ),
    Criterion(
        id="generic.evidence.accessible",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        criterion="Link(s) accessible (HTTP 200).",
        flag_when="Flag if dead link.",
    ),
    Criterion(
        id="generic.evidence.blocked_domain",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        criterion=(
            "Flag blocked domains: SharePoint, OneDrive, Google Drive, Dropbox. "
            "Non-public evidence: use PRMS repository."
        ),
        flag_when="Flag if blocked domain or login-gated link.",
    ),
    Criterion(
        id="generic.evidence.supports_result",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        criterion=(
            "Evidence supports title and result description. "
            "Metadata correspondence: claims (geographic scope, description, etc.) "
            "are coherently supported by evidence."
        ),
        flag_when="Flag if evidence does not support the reported result.",
    ),
    Criterion(
        id="generic.evidence.cgiar_attribution",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        criterion=(
            "CGIAR/Center contribution visible in document. Embedded attribution counts "
            "(co-authorship, acknowledgement, citation)."
        ),
        flag_when="Flag if CGIAR attribution not detectable.",
    ),
]

# ---------------------------------------------------------------------------
# 2. Outcome indicators
# ---------------------------------------------------------------------------

POLICY_CHANGE_CRITERIA = [
    Criterion(
        id="policy.type.selected",
        mds_field="Policy type",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(POLICY_CHANGE,),
        criterion=(
            "Type selected: policy or strategy / legal instrument / program, budget or "
            "investment. Type consistent with result description."
        ),
        flag_when="Flag if absent or if type-description mismatch.",
    ),
    Criterion(
        id="policy.stage.supported",
        mds_field="Policy stage",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(POLICY_CHANGE,),
        criterion=(
            "Stage 1 (research taken up, not yet enacted): evidence of CGIAR link - citation, "
            "3rd-party eval, co-authored doc, quotes, media, email. Confidential ok. "
            "Stage 2 (enacted): link to published/enacted document, org website, or media "
            "announcement. Stage 3 (evidence of impact): peer-reviewed pub or external eval; "
            "Key Results Story accepted. Stage must be supported by evidence type above."
        ),
        flag_when="Flag if absent or if S2 evidence lacks enacted document link.",
    ),
    Criterion(
        id="policy.owner.named",
        mds_field="Policy owner (implementing org.)",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(POLICY_CHANGE,),
        criterion=(
            "Non-CGIAR implementing organisation selected (CLARISA dropdown, min 1, max 3). "
            "Selected organisation(s) named explicitly in description."
        ),
        flag_when="Flag if absent. Flag if named organisation not in description.",
    ),
    Criterion(
        id="policy.evidence.stage_match",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(POLICY_CHANGE,),
        criterion=(
            "Evidence required for all stages. S1: confidential evidence accepted. "
            "S2: public enacted document link mandatory; verify government/official-org domain. "
            "S3: strong evidence of policy impact on people/environment. "
            "CGIAR contribution may be embedded in evidence."
        ),
        flag_when="Flag if evidence doesn't support the stage.",
        notes="Criteria document marks stage-specific content QA as pending a 2026 update.",
    ),
]

INNOVATION_USE_CRITERIA = [
    Criterion(
        id="innovuse.user_type.selected",
        mds_field="User type",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(INNOVATION_USE,),
        criterion=(
            "User type selected (farmers, policymakers, researchers, orgs, etc.). "
            "Can include both people and organisations. Type consistent with description."
        ),
        flag_when="Flag if absent or if type-description mismatch.",
    ),
    Criterion(
        id="innovuse.count.present",
        mds_field="# people/actors using",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(INNOVATION_USE,),
        criterion="Numerical user count present.",
        flag_when="Flag if absent or zero.",
    ),
    Criterion(
        id="innovuse.count.gender_disaggregation",
        mds_field="# people/actors using",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(INNOVATION_USE,),
        criterion=(
            "Disaggregation required. In Innovation Use the Reporting Tool stores "
            "women / men / youth (contract v0.2), not the four-way split used elsewhere. "
            "Youth is required only where relevant."
        ),
        flag_when="Flag if neither a women nor a men count is provided.",
        notes=(
            "Diverges from the criteria document, which states "
            "male/female/non-binary/unknown for this field. Encoded to match what "
            "PRMS actually stores.\n"
            "DO NOT add a women + men == total check. Per Reporting (v0.2): "
            "women_youth/men_youth are subsets of women/men rather than extra "
            "buckets, and a row reported without disaggregation adds to the total "
            "only. The parts legitimately sum to less than the total, so an "
            "equality check would raise a false flag on correct data - and this "
            "criterion is core, so it would produce a false RED."
        ),
    ),
    Criterion(
        id="innovuse.count.not_estimated",
        mds_field="# people/actors using",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(INNOVATION_USE,),
        criterion=(
            '"Estimated"/"approximately"/"projected" figures not accepted - '
            "must be actual data."
        ),
        flag_when="Flag if estimated/projected figures used.",
    ),
    Criterion(
        id="innovuse.other_measure.presence",
        mds_field="Other quantitative measure",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(INNOVATION_USE,),
        criterion=(
            "Additional metric where applicable (# ha, yield, income, % adoption, etc.). "
            "Must be evidence-based, not projected or expected."
        ),
        flag_when="Flag if description implies quantitative scale but field is empty.",
    ),
    Criterion(
        id="innovuse.usd_spend.coherence",
        mds_field="Estimated USD spend",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(INNOVATION_USE,),
        criterion="Monetary value of use where available.",
        flag_when="Flag if not coherent with evidence.",
    ),
    Criterion(
        id="innovuse.evidence.names_innovation",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(INNOVATION_USE,),
        criterion="Evidence must name the specific innovation.",
        flag_when="Flag if innovation not named in evidence.",
    ),
    Criterion(
        id="innovuse.evidence.geolocation",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(INNOVATION_USE,),
        criterion="Evidence must reference the geolocation of use.",
        flag_when="Flag if geolocation not found.",
    ),
    Criterion(
        id="innovuse.evidence.use_level_supported",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(INNOVATION_USE,),
        criterion=(
            "Use Level 0-9 must be supported by evidence. Level 0: none required. "
            "Confidential evidence acceptable for early Use Levels. "
            "Verify Use Level plausibility against evidence content."
        ),
        flag_when="Flag if Use level not supported.",
    ),
]

OTHER_OUTCOME_CRITERIA = [
    Criterion(
        id="otheroutcome.result_level.behavior_change",
        mds_field="Result level",
        # Reads general_information.result_level, and what the user would fix is
        # the title and description. Other Outcome has no type-specific section in
        # the form, so flagging it there would point at something they cannot see.
        section=Section.GENERAL_INFORMATION,
        core=True,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(OTHER_OUTCOME,),
        criterion=(
            "Must demonstrate actual change in knowledge, attitudes, skills, or practices "
            "(KASP) of external actors. Not sufficient: activity, event, or engagement alone. "
            "Events reported as outcomes only if behavior change is documented. "
            "Co-authored publications = outputs, not outcomes. "
            "Result must be in advanced/completed stage. "
            'Flag activity-language: "held", "conducted", "participated in" without '
            "documented change."
        ),
        flag_when="Flag if no behavior change language or result described as activity only.",
    ),
    Criterion(
        id="otheroutcome.evidence.demonstrates_change",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(OTHER_OUTCOME,),
        criterion=(
            "Must demonstrate the actual outcome (change), not CGIAR activity. "
            "Photo alone not sufficient. External blog without SP/A mention not sufficient."
        ),
        flag_when="Flag if photos/activity-only evidence.",
    ),
    Criterion(
        id="otheroutcome.evidence.spa_named",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(OTHER_OUTCOME,),
        criterion=(
            "SP/A or Center explicitly named as contributor, role described - not merely "
            "implied. Result not attributed solely to partner without CGIAR link. "
            "Should clarify role of SP/A explicitly."
        ),
        flag_when="Flag if SP/A not named in evidence.",
    ),
]

# ---------------------------------------------------------------------------
# 3. Output indicators
# ---------------------------------------------------------------------------

CAPACITY_SHARING_CRITERIA = [
    Criterion(
        id="capsharing.trained.count_present",
        mds_field="# people trained",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(CAPACITY_SHARING,),
        criterion='Numerical value required (not "several", "many").',
        flag_when="Flag if numbers absent.",
    ),
    Criterion(
        id="capsharing.trained.gender_disaggregation",
        mds_field="# people trained",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(CAPACITY_SHARING,),
        criterion=(
            "Gender disaggregation: male / female / non-binary / unknown counts. "
            "Youth disaggregation where relevant."
        ),
        flag_when="Flag if no gender disaggregation.",
    ),
    Criterion(
        id="capsharing.trained.plausible",
        mds_field="# people trained",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(CAPACITY_SHARING,),
        criterion=(
            "Numbers plausible for described activity. "
            "Flag if single event >10,000 participants."
        ),
        flag_when="Flag if it seems not plausible.",
    ),
    Criterion(
        id="capsharing.length.present",
        mds_field="Length of training",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(CAPACITY_SHARING,),
        criterion=(
            "Long-term: >=3 months (incl. PhDs, Masters). Short-term: <3 months. "
            "PRMS stores a single term per result."
        ),
        flag_when="Flag if absent.",
        notes=(
            'The document also asks for "numbers consistent across long/short split". '
            "Not implementable: the Reporting Tool stores one term per result, not "
            "counts per term (confirmed with Reporting, contract v0.2)."
        ),
    ),
    Criterion(
        id="capsharing.length.matches_description",
        mds_field="Length of training",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(CAPACITY_SHARING,),
        criterion=(
            "The selected term must match the duration described. "
            "Training must be completed before reporting."
        ),
        flag_when="Flag if stated term contradicts described duration.",
    ),
    Criterion(
        id="capsharing.delivery.method",
        mds_field="Delivery method",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(CAPACITY_SHARING,),
        criterion=(
            "One of exactly three catalog values: Virtual / Online, In person, "
            "Blended (in-person and virtual). "
            "Blended -> geography = where majority of in-person took place. "
            "In person -> country-level geography expected."
        ),
        flag_when="Flag if absent. Flag if virtual + national geography conflict.",
    ),
    Criterion(
        id="capsharing.evidence.ia_score2_required",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        core_when="impact_area_score == 2",
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        applies_to=(CAPACITY_SHARING,),
        criterion=(
            "Standard: no evidence required for QA. "
            "Exception: IA score = 2 -> IA-related evidence mandatory "
            "(syllabus, agenda, attendance list). "
            "Apply standard evidence link + content checks if IA = 2."
        ),
        flag_when="Flag only if IA = 2 and evidence absent.",
        notes=(
            "Only conditional-core criterion in the catalog. When no impact area scores 2, "
            "the whole Evidence section is Not Evaluated for Capacity Sharing."
        ),
    ),
]

KNOWLEDGE_PRODUCT_CRITERIA = [
    Criterion(
        id="kp.handle.present_and_live",
        mds_field="Handle (CGSpace URL)",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion=(
            "CGSpace record URL required - not a direct journal link or DOI alone. "
            "CGSpace record must work (HTTP 200) and be publicly accessible."
        ),
        flag_when="Flag if no CGSpace URL or link dead.",
    ),
    Criterion(
        id="kp.product_type.classified",
        mds_field="Product type",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion=(
            "Product type selected and consistent with the submitted work. "
            "Grey literature excluded from this indicator. "
            "MELIA: select type (impact assessment, evaluation, baseline, etc.)."
        ),
        flag_when="Flag if misclassified.",
    ),
    Criterion(
        id="kp.peer_review.declared",
        mds_field="Peer Review Y/N",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion="Peer-reviewed Y/N indicated correctly. Grey literature excluded.",
        flag_when="Flag if not peer reviewed but claimed as such.",
    ),
    Criterion(
        id="kp.peer_review.predatory_journal",
        mds_field="Peer Review Y/N",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.EXTERNAL,
        needs=Needs.METADATA,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion="For peer-reviewed: not a predatory journal (check Beall's / Cabell's list).",
        flag_when="Flag if predatory journal.",
        notes=(
            "Needs an external list we do not hold (Cabell's is subscription-based). "
            "Reported as not-verifiable, never flagged on a guess: this field is core, "
            "so a false positive would produce a false RED."
        ),
    ),
    Criterion(
        id="kp.publication_date.correct",
        mds_field="Publication date",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion=(
            "For non-auto-validated: check carefully if date != current reporting year. "
            "Use first-online date for articles published online before print."
        ),
        flag_when="Flag if not correct.",
    ),
    Criterion(
        id="kp.isi.wos_indexed",
        mds_field="ISI (WoS Core Collection indexed Y/N)",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.EXTERNAL,
        needs=Needs.METADATA,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion="For non-auto-validated: verify manually via WoS/Scopus.",
        flag_when="Flag if WoS claimed but not confirmed.",
        notes="Needs a WoS/Scopus lookup. Reported as not-verifiable until available.",
    ),
    Criterion(
        id="kp.isi.preprint_as_peer_reviewed",
        mds_field="ISI (WoS Core Collection indexed Y/N)",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion="Preprints (arXiv, bioRxiv, SSRN): not WoS-indexed.",
        flag_when="Flag if preprint is sole evidence for a peer-reviewed claim.",
        notes="Domain match - resolvable in code.",
    ),
    Criterion(
        id="kp.accessibility.matches_url",
        mds_field="Accessibility",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.CODE,
        needs=Needs.EVIDENCE_LINKS,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion=(
            "Open access / restricted - correctly indicated. "
            "Open access claim must be verifiable (no login required on direct link)."
        ),
        flag_when="Flag if open access claimed but link requires login.",
        notes="The existing scraper's _validate_content already detects auth-gated pages.",
    ),
    Criterion(
        id="kp.license.populated",
        mds_field="License",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion=(
            "License type populated (CC-BY, CC-BY-NC, etc.) for open access items. "
            "License consistent with accessibility selection."
        ),
        flag_when="Flag if open access + no license.",
    ),
    Criterion(
        id="kp.agrovoc.populated",
        mds_field="AGROVOC keywords",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion="At least one AGROVOC term populated.",
        flag_when="Flag if no AGROVOC keywords.",
    ),
    Criterion(
        id="kp.agrovoc.relevant",
        mds_field="AGROVOC keywords",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(KNOWLEDGE_PRODUCT,),
        criterion="Terms relevant to the topic.",
        flag_when="Flag if terms are not relevant to the topic.",
    ),
]

INNOVATION_DEV_CRITERIA = [
    Criterion(
        id="innovdev.typology.matches",
        mds_field="Innovation type (typology)",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(INNOVATION_DEV,),
        criterion=(
            "Innovation typology selected: Technological / Genetic / Capacity development / "
            "Policy-org-institutional / Other. Typology matches description of what the "
            "innovation is. Number of new/improved lines/varieties optional."
        ),
        flag_when="Flag if typology-description mismatch.",
    ),
    Criterion(
        id="innovdev.irl.supported",
        mds_field="Innovation Readiness Level (IRL)",
        section=Section.TYPE_SPECIFIC,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(INNOVATION_DEV,),
        criterion=(
            "IRL 0-9 selected. IRL = highest level supportable by evidence; "
            "if evidence fails -> Level 0. Verify IRL plausibility against evidence content. "
            "Level 0: no evidence required."
        ),
        flag_when="Flag if not supported by evidence.",
    ),
    Criterion(
        id="innovdev.contact_point.populated",
        # The form field is "Innovation Developer": prepopulated from the Lead
        # Contact person, but the user can replace it. It is NOT the same field as
        # general_information.lead_contact_person, so it must be requested
        # separately - otherwise the check reads a field that is always filled and
        # the criterion can never fire.
        mds_field="Innovation Developer",
        section=Section.TYPE_SPECIFIC,
        core=False,
        check=Check.CODE,
        needs=Needs.METADATA,
        applies_to=(INNOVATION_DEV,),
        criterion="Name and contact of innovation lead populated.",
        flag_when="Flag if empty.",
    ),
    Criterion(
        id="innovdev.evidence.supports_irl",
        mds_field="Evidence (per IRL)",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(INNOVATION_DEV,),
        criterion=(
            "Must specifically support the claimed IRL. Level 0: none required. "
            "Accepted: concept notes, technical reports, pilot data, publications, "
            "comms materials. Confidential evidence: assess manually - not auto-checked."
        ),
        flag_when="Flag if no evidence for IRL >=1. Flag if not supporting the IRL claimed.",
    ),
    Criterion(
        id="innovdev.evidence.geolocation_irl5",
        mds_field="Evidence (per IRL)",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(INNOVATION_DEV,),
        criterion="For IRL >=5 (context-specific): geolocation must be identifiable in evidence.",
        flag_when="Flag if geolocation absent at IRL >=5.",
    ),
]

OTHER_OUTPUT_CRITERIA = [
    Criterion(
        id="otheroutput.result_type_check",
        mds_field="Result type check",
        # Judged from the title and description; Other Output has no type-specific
        # section in the form. See the note on otheroutcome.result_level.
        section=Section.GENERAL_INFORMATION,
        core=True,
        check=Check.LLM,
        needs=Needs.METADATA,
        applies_to=(OTHER_OUTPUT,),
        criterion=(
            "Could the result fit another indicator? Verify: KP? (check SIDS KP criteria and "
            "KP type list). Capacity Sharing? (if training participants can be counted). "
            "Innovation Development? (if innovation at defined readiness level). "
            "Intermediate/draft products must NOT be reported as Other Output. "
            "Events = Other Output only if not countable as Capacity Sharing. "
            "Reported in English only (evidence may be in other languages)."
        ),
        flag_when=(
            "Flag if result is clearly draft or incomplete. "
            "Flag if result should be classified as KP or CS."
        ),
    ),
    Criterion(
        id="otheroutput.evidence.completed_product",
        mds_field="Evidence",
        section=Section.EVIDENCE,
        core=True,
        check=Check.LLM,
        needs=Needs.EVIDENCE_CONTENT,
        applies_to=(OTHER_OUTPUT,),
        criterion=(
            "Evidence required for all Other Outputs. "
            "Accepted: blog posts, recordings, agendas, reports. "
            "Blog title != output title; output title = the actual result. "
            "Must be a completed, tangible product. CGIAR contribution explicit."
        ),
        flag_when=(
            "Flag if dead link or no evidence. Flag if attribution absent. "
            "Flag if process-only or future-tense result."
        ),
    ),
]


# Criteria defined but not active in this service.
#   - Knowledge Product: excluded by the Reporting Tool (resolved in code via their
#     decision tree). Kept here so re-enabling is a one-line change.
#   - Impact area tags: no impact area scores or thematic subcomponents exist in the
#     v0.1 contract, so these four criteria cannot be resolved. See INACTIVE_REASONS.
IMPACT_AREA_CRITERIA_IDS = (
    "generic.impact_area.plausibility",
    "generic.impact_area.score2_evidence",
    "generic.impact_area.score2_subcomponent",
    "generic.impact_area.gender_score2_differential",
)

INACTIVE_REASONS = {
    "knowledge_product": "Out of scope for this service (Reporting Tool decision tree).",
}

EXCLUDED_TYPES = (KNOWLEDGE_PRODUCT,)

CATALOG = [
    c
    for c in (
        GENERIC
        + POLICY_CHANGE_CRITERIA
        + INNOVATION_USE_CRITERIA
        + OTHER_OUTCOME_CRITERIA
        + CAPACITY_SHARING_CRITERIA
        + INNOVATION_DEV_CRITERIA
        + OTHER_OUTPUT_CRITERIA
    )
]

CATALOG_BY_ID = {c.id: c for c in CATALOG}


def criteria_for(result_type: str, check: Optional[Check] = None,
                 needs: Optional[Needs] = None) -> list:
    """Criteria that apply to a result type, optionally narrowed by check or input."""
    out = [c for c in CATALOG if c.applies(result_type)]
    if check is not None:
        out = [c for c in out if c.check == check]
    if needs is not None:
        out = [c for c in out if c.needs == needs]
    return out


def sections_for(result_type: str) -> list:
    """Sections that have at least one applicable criterion, in display order."""
    applicable = {c.section for c in CATALOG if c.applies(result_type)}
    return [s for s in Section if s in applicable]
