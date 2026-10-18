"""Education Wiki Template Catalog and Enforcement [CARD-322, CARD-714].

Re-exports domain-level education templates so application callers continue
using their existing import paths while src/domain/wiki/ never imports upward.
"""

from __future__ import annotations

from src.domain.wiki.education_templates import (
    EDUCATION_TEMPLATES,
    STEP_TO_TEMPLATE_MAP,
    EducationTemplateRequiredError,
    assert_education_template_required,
    get_education_template,
    get_template_for_step,
    list_education_templates,
)

__all__ = [
    "EDUCATION_TEMPLATES",
    "STEP_TO_TEMPLATE_MAP",
    "EducationTemplateRequiredError",
    "assert_education_template_required",
    "get_education_template",
    "get_template_for_step",
    "list_education_templates",
]
