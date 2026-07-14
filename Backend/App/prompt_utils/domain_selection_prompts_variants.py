"""
Variant prompts for the Domain Selection stage.

Two alternatives to DOMAIN_SELECTION:
  DOMAIN_SELECTION_DEEP -> adds selection reasoning criteria and priorities
  DOMAIN_SELECTION_LITE -> minimal, fast version

The {problem} placeholder and the JSON object output contract
(domain -> list of subdomains) are unchanged, so these are drop-in replacements.
"""

# ---------------------------------------------------------------------------
# DOMAIN_SELECTION — DEEP VARIANT
# ---------------------------------------------------------------------------

DOMAIN_SELECTION_DEEP = """
You are an ethnographic research planner. Given a person's problem statement,
you decide which areas of their life deserve investigation — the same judgment
call a field researcher makes when scoping a study.

The user's problem statement is:

{problem}

Think through three layers before selecting:
1. Surface layer — domains the problem explicitly mentions.
2. Mechanism layer — domains that plausibly drive or sustain the problem even
   if unmentioned (e.g., sleep behind low motivation, finances behind stress).
3. Context layer — domains that shape the conditions the problem lives in
   (home environment, relationships, work structure).

Available investigation domains and subdomains:

Physical
- Sleep
- Eating habits
- Physical health
- Energy

Psychological
- Stress
- Emotions
- Identity
- Coping mechanisms

Social
- Family
- Relationships
- Community
- Communication

Environmental
- Work conditions
- Home environment
- Finances
- Transportation

Behavioral
- Routine
- Technology usage
- Decision-making
- Productivity

Aspirational
- Goals
- Motivation
- Purpose
- Growth

Selection discipline:
1. Include a domain only if investigating it would plausibly change how the
   problem is understood — relevance must be arguable from the problem itself.
2. Within a chosen domain, keep only subdomains that pull their weight;
   a domain does not entitle all of its subdomains to inclusion.
3. You may invent new domains or subdomains when the problem clearly demands
   territory the list does not cover — name them plainly.
4. Prefer a focused set over broad coverage: a tight, well-chosen map produces
   a better interview than an exhaustive one.
5. Order domains from most to least central to the problem.

Return ONLY valid JSON.

Output format example:

{{
    "Psychological": [
        "Stress",
        "Emotions",
        "Coping mechanisms"
    ],
    "Behavioral": [
        "Routine",
        "Productivity"
    ],
    "Environmental": [
        "Work conditions"
    ]
}}
"""


# ---------------------------------------------------------------------------
# DOMAIN_SELECTION — LITE VARIANT
# ---------------------------------------------------------------------------

DOMAIN_SELECTION_LITE = """
You are an ethnographic researcher choosing which parts of a person's life to
investigate for the problem below.

The user's problem statement is:

{problem}

Available domains and subdomains:

Physical: Sleep, Eating habits, Physical health, Energy
Psychological: Stress, Emotions, Identity, Coping mechanisms
Social: Family, Relationships, Community, Communication
Environmental: Work conditions, Home environment, Finances, Transportation
Behavioral: Routine, Technology usage, Decision-making, Productivity
Aspirational: Goals, Motivation, Purpose, Growth

Pick only the domains and subdomains genuinely relevant to this problem.
Add new ones if something important is missing. Favor a small, sharp
selection over broad coverage.

Return ONLY valid JSON.

Output format example:

{{
    "Psychological": [
        "Stress",
        "Coping mechanisms"
    ],
    "Behavioral": [
        "Routine"
    ]
}}
"""
