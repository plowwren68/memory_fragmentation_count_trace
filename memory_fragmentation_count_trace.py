"""memory_fragmentation_count_trace —— 追溯数据治理与血缘专家·显存碎片与分配策略里每一份贡献来自哪里。

统计各来源片段的贡献量与占比，标出数据治理与血缘专家·显存碎片与分配策略上最主要的来源

定位：
  贡献占比按字符量算而不是按出现次数，避免长句主导统计

岗位对应：
  目标岗位　腾讯 · 资深数据治理与血缘专家
  技能主线　SQL、Spark、数据标注
  领域标签　数据平台

设计约束：
  1. **只报告能定位到具体位置的结论**，不做语义猜测。
  2. **规则表公开**，每条命中都能对应到岗位要求的一条明示规则。
  3. **输入为空或格式不对时明确报错**，不静默返回空结果。

仅依赖 Python 标准库。

用法:
    python memory_fragmentation_count_trace.py --help
    python memory_fragmentation_count_trace.py --file input.txt
    python memory_fragmentation_count_trace.py --text "示例内容"
    python memory_fragmentation_count_trace.py --file input.txt --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# Windows 控制台可能使用 GBK；帮助和结果统一输出 UTF-8。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 岗位规则表：每条规则独立可核查，命中即报，不做推断。
# 规则由岗位 JD 的技能线与领域标签派生——每条都能对回岗位要求。
# 目标岗位：腾讯 · 资深数据治理与血缘专家
RULES: list[dict] = [
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·缺失",
        "why": "岗位要求「SQL」在输入里找不到对应内容",
        "severity": "high",
        "keywords": ['missing', 'absent', '缺少', '没有', '未提供', 'SQL'],
    },
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·冲突",
        "why": "两处关于「Spark」的描述互相矛盾",
        "severity": "high",
        "keywords": ['conflict', 'contradict', '矛盾', '不一致', '相反', 'Spark'],
    },
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·越界",
        "why": "「数据标注」的取值超出岗位场景的常规范围",
        "severity": "medium",
        "keywords": ['out of range', 'outlier', '越界', '超限', '超过', '数据标注'],
    },
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·退化",
        "why": "「数据平台」相关的信息量不足以支撑判断",
        "severity": "medium",
        "keywords": ['degrade', 'insufficient', '不足', '太少', '无法', '数据平台'],
    },
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·泄漏",
        "why": "「数据治理与血缘专家」相关的内容被意外暴露",
        "severity": "high",
        "keywords": ['leak', 'expose', '泄漏', '暴露', '明文', '数据治理与血缘专家'],
    },
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·重复#2",
        "why": "同一处「SQL」信息被反复传递",
        "severity": "low",
        "keywords": ['duplicate', 'repeat', '重复', 'again', 'SQL'],
    },
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·陈旧#2",
        "why": "「Spark」的时效性已过期",
        "severity": "medium",
        "keywords": ['stale', 'expired', '过期', '陈旧', '旧版', 'Spark'],
    },
    {
        "name": "数据治理与血缘专家·显存碎片与分配策略·不可核#2",
        "why": "关于「数据标注」的说法无法追溯到具体证据",
        "severity": "high",
        "keywords": ['unverifiable', 'no evidence', '无法追溯', '没有来源', '数据标注'],
    },
]


def memory_fragmentation_count_trace_read_numbers(text: str) -> list[float]:
    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))]


def memory_fragmentation_count_trace_analyze(text: str) -> dict:
    """主分析：来源与占比。"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if not blocks:
        return {"ok": False, "error": "没有内容", "count": 0}
    total = sum(len(b) for b in blocks)
    parts = []
    for i, b in enumerate(blocks):
        head = b.splitlines()[0][:60] if b.splitlines() else "(空)"
        parts.append({"index": i, "head": head, "size": len(b),
                      "share": round(len(b) / total, 4) if total else 0.0})
    return {
        "ok": True,
        "count": len(blocks),
        "total_size": total,
        "parts": parts,
        "largest": max(parts, key=lambda p: p["size"])["head"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(result: dict) -> str:
    """把结果渲染成人读的文本。每个工具的版式不同。"""
    out: list[str] = []
    if not result.get("ok", True):
        out.append(f"无法分析：{{result.get('error', '未知原因')}}")
        return "\n".join(out)
    out.append(f"片段数：{result['count']}  总量 {result['total_size']}")
    out.append("")
    for p_ in result["parts"]:
        out.append(f"  {p_['share']:>7.2%}  {p_['size']:>6}  {p_['head']}")
    out.append("")
    out.append(f"最大来源：{result['largest']}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="memory_fragmentation_count_trace",
        description="统计各来源片段的贡献量与占比，标出数据治理与血缘专家·显存碎片与分配策略上最主要的来源（仅依赖标准库）",
        epilog=(
            "示例:\n"
            "  python memory_fragmentation_count_trace.py --file input.txt\n"
            "  python memory_fragmentation_count_trace.py --text '示例内容'\n"
            "  python memory_fragmentation_count_trace.py --file input.txt --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="输入文件路径")
    src.add_argument("--text", help="直接给出输入内容")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"读不了文件：{{e}}", file=sys.stderr)
            return 2
    else:
        content = args.text

    if not content.strip():
        print("输入是空的。", file=sys.stderr)
        return 2

    result = memory_fragmentation_count_trace_analyze(content)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(render(result))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
