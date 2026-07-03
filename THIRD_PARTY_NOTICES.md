# Third Party Notices

This file records third-party open source components, standards, and reference materials used by AIHelms features.

## AI Policies Skill Security Audit

### SkillSpector

- Project: SkillSpector
- Source: https://github.com/NVIDIA/SkillSpector
- License: Apache License 2.0
- Use in AIHelms: internal static Skill package scanner, packaged as a sidecar scanner image.
- Compliance notes:
  - Keep the Apache License 2.0 text available in this repository or product distribution.
  - Preserve upstream copyright, license, and NOTICE files when redistributing source or binary artifacts that include the component.
  - Do not imply NVIDIA endorsement of AIHelms or AIHelms audit results.

### LiteLLM

- Project: LiteLLM
- Source: https://github.com/BerriAI/litellm
- License: MIT License for content outside LiteLLM enterprise-specific directories; enterprise-specific content follows its own upstream license.
- Use in AIHelms: platform model gateway used by AI Policies LLM review engine when the administrator enables LLM review.
- Compliance notes:
  - Keep the MIT License text available in this repository or product distribution when redistributing LiteLLM-related binaries or images.
  - Preserve upstream copyright and license notices.
  - Re-check the upstream image/source contents before release if packaging enterprise-specific LiteLLM files.
  - Do not expose provider API keys in AI Policies reports, logs, or exported audit artifacts.

### OWASP Agentic Skills Top 10

- Project: OWASP Agentic Skills Top 10
- License: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)
- Use in AIHelms: risk classification reference for AI Policies report categories and explanatory wording.
- Compliance notes:
  - Attribute OWASP when referencing the taxonomy or adapted explanatory content.
  - State that OWASP does not certify, recommend, or endorse AIHelms or AIHelms audit results.
  - Keep derivative report wording compatible with CC BY-SA 4.0 when it substantially adapts OWASP text.

