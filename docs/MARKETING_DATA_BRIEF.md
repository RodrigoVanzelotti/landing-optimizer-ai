# Landing Optimizer AI: data brief for POC videos

**Purpose:** explain what the website script collects and what the API/AI turns into optimization insights.
**Basis:** [Data science handoff](DATA_SCIENCE_HANDOFF.md), dated October 6, 2026. Describes the current implementation; live collection has not been verified.

## 1. What the script collects from the website

| Data | What it tells us |
| --- | --- |
| **Page structure and short text snippets** | Identifies elements such as the hero, headings, calls to action (CTAs), forms, pricing, testimonials and FAQs. Records element references so suggestions can target specific text. |
| **Page visits and navigation behavior** | Records page views, scroll depth and dropoff events. |
| **Clicks and friction signals** | Records CTA clicks, clicks on elements that do not respond, and repeated rapid clicks that may indicate frustration. |
| **Attention signals** | Records section visibility, hover activity and time spent. These are different signals, not direct measures of interest or satisfaction. |
| **Forms and conversions** | Records form starts, form submissions and instrumented conversion events. Conversion goals must be configured; the script does not automatically know what counts as business success. |
| **Basic visit context** | Records page path, broad device/browser categories, referring website and a pseudonymous session identifier scoped to the site and day. |

The page map is a compact representation, not a full website scrape: up to 60 elements with up to 80 characters of text each. Element roles are detected heuristically.

## 2. What the API prepares for the AI

The API combines three inputs:

- **Page map:** the latest captured map from the website.
- **Behavior summaries:** site-wide page views, conversions, conversion event ratio, CTA clicks and form submissions for the last 30 days; plus section views, frustration clicks and accumulated dwell time.
- **Configured brand rules:** tone, banned words, copy length limits and claims to preserve. These come from configuration, not visitor behavior.

**Scope matters:** the latest map may represent one page while metrics cover the whole site. Section metrics also use a different time window. Present insights as optimization hypotheses, not precise proof that one element caused visitor behavior.

## 3. What the AI/API generates

| Output | Marketing meaning |
| --- | --- |
| **Page score** | A summary assessment intended for a 0–100 scale. It is not a predicted conversion rate or a validated performance benchmark. |
| **Optimization hypotheses** | Possible explanations of friction and opportunities to improve page structure or messaging. |
| **Headline and CTA suggestions** | Proposed replacement copy, sometimes tied to a specific page element. |
| **Recommendations with risk labels** | A title, explanation and low/medium/high risk label; some include an expected-impact statement. Impact is an estimate, not measured uplift. |
| **Draft experiments** | Eligible headline/CTA suggestions can become draft tests comparing original and proposed text. Human approval is required before publication. |

Generation can use OpenAI, with a rule-based fallback if generation fails. The standalone scoring endpoint currently uses rules. Proposed copy is checked for banned words and length; brand compliance still needs review.

## 4. How to describe it in a video

**Suggested narration:**

> Landing Optimizer AI maps key page elements and collects visitor interaction signals. It combines page content, behavior summaries and brand rules to suggest clearer headlines, stronger calls to action and opportunities to reduce friction. Teams review recommendations and can turn selected copy changes into draft experiments.

**Suggested visual sequence:** page elements → visitor interaction signals → aggregated metrics → AI recommendation → human review → draft experiment.

**Illustrative insight, not a measured finding:** “Visitors click this CTA, but form submissions are low across the site. Review the CTA message and form experience, then test a clearer version.”

## 5. Claims to keep out of the POC

- **“The AI sees the entire website.”** It receives a limited page map and short text snippets. Screenshots can be stored, but are not currently sent to the AI; neither are raw sessions or heatmaps.
- **“The AI proves what increases conversions.”** Recommendations and expected impact are hypotheses. Experiment conversion attribution has known gaps, so reliable uplift or winner claims are premature.
- **“It knows each customer or predicts revenue.”** Current inputs do not support persistent customer identity, lifetime value, revenue forecasting or churn prediction.
- **“It optimizes the site automatically.”** Selected changes require human approval before publication.
