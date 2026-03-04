"""md-mid: 学术写作中间格式与多目标转换工具。

Academic Markdown intermediate format and multi-target conversion tool.
"""

from md_mid.api import (
    ConversionError,
    ConvertResult,
    convert,
    format_text,
    parse_document,
    validate_text,
)
from md_mid.config import MdMidConfig
from md_mid.diagnostic import Diagnostic
from md_mid.nodes import Document

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "convert",
    "validate_text",
    "format_text",
    "parse_document",
    "ConvertResult",
    "ConversionError",
    "MdMidConfig",
    "Diagnostic",
    "Document",
]
