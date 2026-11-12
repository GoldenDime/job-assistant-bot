"""Проверка честности: не появилось ли в адаптированном резюме цифр и названий,
которых нет в исходнике. Эвристика, не доказательство: флаг = повод посмотреть глазами.
"""
import re
from dataclasses import dataclass, field

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
# Слова с заглавной буквы или латиница внутри кавычек/после «в/at» — кандидаты в названия компаний
ORG_RE = re.compile(r"[«\"]([^»\"]{2,60})[»\"]")


def resume_section(answer: str) -> str:
    """Берём только блок «Адаптированное резюме»: в «Пробелах» цифры из вакансии законны."""
    m = re.search(r"##\s*Адаптированное резюме(.*?)(?:\n##\s|\Z)", answer, re.S | re.I)
    return m.group(1) if m else answer


def _norm_num(s: str) -> str:
    return s.replace(",", ".").lstrip("0") or "0"


@dataclass
class FaithReport:
    new_numbers: list[str] = field(default_factory=list)
    new_quoted_names: list[str] = field(default_factory=list)

    @property
    def flags(self) -> int:
        return len(self.new_numbers) + len(self.new_quoted_names)


def check(source_resume: str, answer: str) -> FaithReport:
    out = resume_section(answer)
    src_nums = {_norm_num(n) for n in NUM_RE.findall(source_resume)}
    src_low = source_resume.lower()
    report = FaithReport()
    for n in NUM_RE.findall(out):
        if _norm_num(n) not in src_nums and n not in report.new_numbers:
            report.new_numbers.append(n)
    for name in ORG_RE.findall(out):
        if name.lower() not in src_low and name not in report.new_quoted_names:
            report.new_quoted_names.append(name)
    return report
