"""Zero-dependency CTKF Community command line interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from ctkf_community import __version__

PASS = "PASS"  # noqa: S105 - governance result token, not a credential.
BLOCK = "BLOCK"
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
SUPPORTED_IDES = ("codex", "catpaw", "opencode")
MAINLINE = (
    ("STAGE-01", "Requirement Intake", "01-requirement-intake.md"),
    ("STAGE-02", "Requirement Analysis", "02-requirement-analysis.md"),
    ("STAGE-03", "Acceptance Criteria", "03-acceptance-criteria.md"),
    ("STAGE-04", "Architecture Blueprint", "04-architecture-blueprint.md"),
    ("STAGE-05", "UI/UX Inventory", "05-uiux-inventory.md"),
    ("STAGE-06", "UI/UX Prototype", "06-uiux-prototype.md"),
    ("STAGE-07", "API Contract", "07-api-contract.md"),
    ("STAGE-08", "Data Model / DB Migration Plan", "08-data-model.md"),
    ("STAGE-09", "Frontend Plan", "09-frontend-plan.md"),
    ("STAGE-10", "Backend Plan", "10-backend-plan.md"),
    ("STAGE-11", "Atomic Task DAG", "11-atomic-task-dag.json"),
    ("STAGE-12", "Commander Plan", "12-commander-plan.json"),
    ("STAGE-13", "Agent Execution", "13-agent-execution.json"),
    ("STAGE-14", "Tests / Browser Preview", "14-test-browser-evidence.json"),
    ("STAGE-15", "Evidence Gate", "15-evidence-gate.json"),
    ("STAGE-16", "Review Gate", "16-review-gate.md"),
    ("STAGE-17", "Deploy / Rollback", "17-deploy-rollback.md"),
    ("STAGE-18", "Production Observation", "18-production-observation.json"),
    ("STAGE-19", "Feedback / Learning", "19-feedback-learning.md"),
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_document(path: Path) -> tuple[str, str, str]:
    if not path.is_file():
        raise ValueError(f"requirement document does not exist: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError("requirement document must be 1 byte to 2 MiB")
    if b"\x00" in raw:
        raise ValueError("binary requirement documents are not supported")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("requirement document must be UTF-8, UTF-8 BOM, or GB18030 text")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"
    if len(normalized.strip()) < 20:
        raise ValueError("requirement document is too short to create a governed delivery plan")
    return normalized, _sha256(raw), encoding


def _sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    heading = "Unsectioned requirements"
    buffer: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^\s*(?:#{1,6}\s+|(?:\d+[.、]|[一二三四五六七八九十]+、)\s*)(.+?)\s*$", line)
        if match:
            if any(item.strip() for item in buffer):
                sections.append(_section_record(len(sections) + 1, heading, buffer))
            heading = match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    if any(item.strip() for item in buffer):
        sections.append(_section_record(len(sections) + 1, heading, buffer))
    if not sections:
        sections.append(_section_record(1, heading, text.splitlines()))
    return sections


def _section_record(index: int, title: str, lines: list[str]) -> dict[str, Any]:
    content = "\n".join(lines).strip()
    return {
        "id": f"REQ-SECTION-{index:03d}",
        "title": title,
        "contentSha256": _sha256(content.encode("utf-8")),
        "characterCount": len(content),
        "lineCount": len(content.splitlines()),
    }


def _question_gate(text: str) -> list[dict[str, str]]:
    lowered = text.casefold()
    rules = (
        (
            "Q-PAYMENT-REFUND",
            ("支付", "付费", "收费", "订单", "订阅", "payment", "subscription"),
            ("退款", "退订", "refund", "cancel"),
            "涉及付款，但缺少退款、取消和异常对账规则。请明确退款条件、时限、责任方和失败处理。",
        ),
        (
            "Q-AUTHORIZATION",
            ("登录", "注册", "用户", "账号", "login", "account", "user"),
            ("角色", "权限", "管理员", "rbac", "permission", "role"),
            "涉及用户身份，但缺少角色和权限边界。请列出角色、可访问数据和禁止操作。",
        ),
        (
            "Q-PRIVACY",
            ("手机号", "身份证", "实名", "地址", "隐私", "phone", "identity", "personal data"),
            ("保留", "删除", "脱敏", "加密", "retention", "deletion", "encryption"),
            "涉及个人信息，但缺少收集目的、保留期限、删除和加密要求。",
        ),
        (
            "Q-DEPLOYMENT",
            ("上线", "发布", "生产", "deploy", "production", "launch"),
            ("回滚", "备份", "恢复", "rollback", "backup", "restore"),
            "要求上线，但缺少回滚、备份和恢复目标。请明确 RTO、RPO 和回滚触发条件。",
        ),
        (
            "Q-AI-BOUNDARY",
            ("ai", "模型", "大模型", "智能生成", "agent"),
            ("预算", "人工审核", "模型路由", "降级", "budget", "human review", "fallback"),
            "包含 AI 能力，但缺少模型预算、人工审核、失败降级和输出安全边界。",
        ),
    )
    questions = []
    for question_id, triggers, evidence, prompt in rules:
        if any(item in lowered for item in triggers) and not any(item in lowered for item in evidence):
            questions.append({"id": question_id, "severity": "HIGH", "question": prompt})
    return questions


def _mainline() -> list[dict[str, Any]]:
    result = []
    previous: str | None = None
    for stage_id, title, artifact in MAINLINE:
        result.append(
            {
                "id": stage_id,
                "title": title,
                "status": "PENDING",
                "dependsOn": [previous] if previous else [],
                "requiredArtifact": f".ctkf-community/artifacts/{artifact}",
                "owner": "commander" if stage_id in {"STAGE-01", "STAGE-11", "STAGE-12", "STAGE-15", "STAGE-16"} else "specialist-agent",
                "failureRoute": "stop, preserve evidence, and ask the operator when a high-impact fact is missing",
            }
        )
        previous = stage_id
    return result


def _atomic_backlog() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    previous_evidence: str | None = None
    for index, (stage_id, title, artifact) in enumerate(MAINLINE, start=1):
        draft_id = f"ATOM-{index:03d}-DRAFT"
        verify_id = f"ATOM-{index:03d}-VERIFY"
        evidence_id = f"ATOM-{index:03d}-EVIDENCE"
        target = f".ctkf-community/artifacts/{artifact}"
        tasks.extend(
            [
                {
                    "id": draft_id,
                    "stageId": stage_id,
                    "title": f"Produce {title}",
                    "objective": f"Create the bounded {title} artifact without silently inventing high-impact facts.",
                    "inputs": [".ctkf-community/source/requirements.txt", ".ctkf-community/intake.json"],
                    "outputs": [target],
                    "dependsOn": [previous_evidence] if previous_evidence else [],
                    "acceptanceCriteria": [
                        "Every material statement traces to the requirement source or is marked as an assumption.",
                        "Roles, data, failure modes, security, privacy, operations, and accessibility are addressed when applicable.",
                        "High-impact ambiguity causes an operator question instead of an implementation guess.",
                    ],
                    "verificationCommands": ["ctkf-community verify --project ."],
                    "risk": "MEDIUM",
                    "approvalRequired": stage_id in {"STAGE-03", "STAGE-04", "STAGE-12", "STAGE-16", "STAGE-17"},
                },
                {
                    "id": verify_id,
                    "stageId": stage_id,
                    "title": f"Verify {title}",
                    "objective": f"Validate completeness, internal consistency, and requirement traceability for {title}.",
                    "inputs": [target],
                    "outputs": [f".ctkf-community/evidence/{stage_id.lower()}-verification.json"],
                    "dependsOn": [draft_id],
                    "acceptanceCriteria": [
                        "The required artifact exists and is non-empty.",
                        "Negative, empty, unauthorized, degraded, and recovery paths are covered when relevant.",
                        "Verification evidence identifies the command, result, revision, and remaining limitations.",
                    ],
                    "verificationCommands": ["ctkf-community verify --project ."],
                    "risk": "MEDIUM",
                    "approvalRequired": False,
                },
                {
                    "id": evidence_id,
                    "stageId": stage_id,
                    "title": f"Seal {title} evidence",
                    "objective": f"Record reviewable evidence and route failures before allowing the next stage after {title}.",
                    "inputs": [target, f".ctkf-community/evidence/{stage_id.lower()}-verification.json"],
                    "outputs": [f".ctkf-community/evidence/{stage_id.lower()}-gate.json"],
                    "dependsOn": [verify_id],
                    "acceptanceCriteria": [
                        "Evidence is bound to its inputs and does not claim checks that were not executed.",
                        "Any BLOCK routes back to the producing atom or to the operator question gate.",
                        "The next stage remains blocked until this evidence gate passes.",
                    ],
                    "verificationCommands": ["ctkf-community verify --project ."],
                    "risk": "LOW",
                    "approvalRequired": False,
                },
            ]
        )
        previous_evidence = evidence_id
    return tasks


def _runbook(ide: str, questions: list[dict[str, str]]) -> str:
    question_text = "\n".join(f"- {item['id']}: {item['question']}" for item in questions) or "- No high-impact question was detected automatically."
    return f"""# CTKF Community AI Development Runbook

Executor: `{ide}`

## Mandatory start

1. Read `.ctkf-community/source/requirements.txt` without summarizing away details.
2. Read `.ctkf-community/intake.json`, `delivery-mainline.json`, and `atomic-backlog.json`.
3. If the question gate contains unresolved HIGH questions, ask the operator and stop implementation.
4. Execute one atom at a time in dependency order.
5. Produce the declared artifact and verification evidence before moving to the next atom.
6. Never invent payment, authorization, privacy, destructive data, production, or legal facts.
7. Run `ctkf-community verify --project .` after changing CTKF Community control files.

## Current high-impact questions

{question_text}

## Initial prompt for the AI IDE

```text
You are the implementation executor. CTKF Community is the control envelope.
Read the original requirement document and all files under .ctkf-community/.
Do not bypass question gates or approvals. Work only on the next unblocked atom,
write its required artifact, run its verification, and report concrete evidence.
Ask me only when a missing answer changes billing, authorization, privacy,
architecture, destructive data behavior, or production release scope.
```
"""


def initialize(requirements: Path, project: Path, ide: str, force: bool = False) -> dict[str, Any]:
    if ide not in SUPPORTED_IDES:
        raise ValueError(f"unsupported IDE: {ide}")
    text, original_hash, encoding = _read_document(requirements.resolve())
    control = project.resolve() / ".ctkf-community"
    if project.exists() and any(project.iterdir()) and not control.exists():
        raise ValueError("project directory is non-empty and is not managed by CTKF Community")
    if control.exists() and not force:
        raise ValueError("CTKF Community project already exists; use --force to regenerate managed planning files")

    normalized_raw = text.encode("utf-8")
    questions = _question_gate(text)
    intake: dict[str, Any] = {
        "schemaVersion": "ctkf.community-intake.v1",
        "result": PASS,
        "source": {
            "originalPath": str(requirements.resolve()),
            "originalEncoding": encoding,
            "originalSha256": original_hash,
            "normalizedSha256": _sha256(normalized_raw),
            "characterCount": len(text),
            "lineCount": len(text.splitlines()),
        },
        "sections": _sections(text),
        "questionGate": {
            "status": "BLOCK" if questions else "PASS",
            "implementationReady": not questions,
            "questions": questions,
        },
        "claimBoundary": "This package plans and validates a local workflow; it does not prove production readiness or replace human product, security, legal, or operational judgment.",
    }
    mainline: dict[str, Any] = {
        "schemaVersion": "ctkf.community-delivery-mainline.v1",
        "result": PASS,
        "authoritative": True,
        "stageCount": len(MAINLINE),
        "stages": _mainline(),
    }
    tasks = _atomic_backlog()
    backlog: dict[str, Any] = {
        "schemaVersion": "ctkf.community-atomic-backlog.v1",
        "result": PASS,
        "taskCount": len(tasks),
        "tasks": tasks,
    }

    source_target = control / "source" / "requirements.txt"
    _write_text(source_target, text)
    _write_json(control / "intake.json", intake)
    _write_json(control / "delivery-mainline.json", mainline)
    _write_json(control / "atomic-backlog.json", backlog)
    _write_text(project.resolve() / "RUNBOOK.md", _runbook(ide, questions))
    report = verify(project)
    report.update(
        {
            "command": "init",
            "ide": ide,
            "questionGateStatus": intake["questionGate"]["status"],
            "nextAction": "Answer the HIGH questions in RUNBOOK.md before implementation." if questions else "Start the first unblocked atom in RUNBOOK.md.",
        }
    )
    return report


def verify(project: Path) -> dict[str, Any]:
    root = project.resolve()
    control = root / ".ctkf-community"
    findings: list[dict[str, str]] = []
    required = (
        control / "source" / "requirements.txt",
        control / "intake.json",
        control / "delivery-mainline.json",
        control / "atomic-backlog.json",
        root / "RUNBOOK.md",
    )
    for path in required:
        if not path.is_file() or path.stat().st_size == 0:
            findings.append({"id": "required-file", "path": str(path), "message": "required managed file is missing or empty"})
    if findings:
        return _verification_report(root, findings, 0, 0)
    try:
        intake = _read_json(control / "intake.json")
        mainline = _read_json(control / "delivery-mainline.json")
        backlog = _read_json(control / "atomic-backlog.json")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        findings.append({"id": "json-contract", "path": str(control), "message": str(exc)})
        return _verification_report(root, findings, 0, 0)

    source_hash = _sha256((control / "source" / "requirements.txt").read_bytes())
    if source_hash != intake.get("source", {}).get("normalizedSha256"):
        findings.append({"id": "source-hash", "path": "requirements.txt", "message": "normalized requirement source hash has drifted"})
    stages = mainline.get("stages", [])
    expected_stage_ids = [item[0] for item in MAINLINE]
    if [item.get("id") for item in stages] != expected_stage_ids or mainline.get("stageCount") != len(MAINLINE):
        findings.append({"id": "mainline", "path": "delivery-mainline.json", "message": "the authoritative 19-stage mainline has drifted"})
    tasks = backlog.get("tasks", [])
    task_ids = [item.get("id") for item in tasks]
    if len(tasks) != len(MAINLINE) * 3 or len(task_ids) != len(set(task_ids)) or backlog.get("taskCount") != len(tasks):
        findings.append({"id": "atomic-count", "path": "atomic-backlog.json", "message": "the 57-task atomic backlog is incomplete or duplicated"})
    known = set(task_ids)
    for task in tasks:
        if task.get("stageId") not in expected_stage_ids:
            findings.append({"id": "task-stage", "path": str(task.get("id")), "message": "task references an unknown stage"})
        if any(dependency not in known for dependency in task.get("dependsOn", [])):
            findings.append({"id": "task-dependency", "path": str(task.get("id")), "message": "task dependency is unknown"})
        for field in ("objective", "inputs", "outputs", "acceptanceCriteria", "verificationCommands"):
            if not task.get(field):
                findings.append({"id": "task-contract", "path": str(task.get("id")), "message": f"task field is empty: {field}"})
    return _verification_report(root, findings, len(stages), len(tasks))


def status(project: Path) -> dict[str, Any]:
    report = verify(project)
    intake_path = project.resolve() / ".ctkf-community" / "intake.json"
    if intake_path.is_file():
        intake = _read_json(intake_path)
        report["questionGate"] = intake.get("questionGate", {})
    report["command"] = "status"
    return report


def doctor() -> dict[str, Any]:
    checks: list[dict[str, str]] = []

    python_supported = sys.version_info >= (3, 10)
    checks.append(
        {
            "id": "python-version",
            "result": PASS if python_supported else BLOCK,
            "message": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }
    )

    declared_output_encoding = sys.stdout.encoding
    output_encoding = declared_output_encoding or "utf-8"
    try:
        "CTKF 中文输出".encode(output_encoding)
        encoding_supported = True
    except (LookupError, UnicodeEncodeError):
        encoding_supported = False
    checks.append(
        {
            "id": "stdout-encoding",
            "result": PASS if encoding_supported else BLOCK,
            "message": declared_output_encoding or "unicode-native redirected stream",
        }
    )

    atomic_write_supported = False
    try:
        with tempfile.TemporaryDirectory(prefix="ctkf-community-doctor-") as temporary:
            probe = Path(temporary) / "atomic-write.txt"
            _write_text(probe, "ctkf-community-doctor")
            atomic_write_supported = probe.read_text(encoding="utf-8").strip() == "ctkf-community-doctor"
    except OSError:
        atomic_write_supported = False
    checks.append(
        {
            "id": "atomic-write",
            "result": PASS if atomic_write_supported else BLOCK,
            "message": "temporary-directory atomic replace is available" if atomic_write_supported else "temporary-directory atomic replace failed",
        }
    )

    checks.append(
        {
            "id": "runtime-version",
            "result": PASS if re.fullmatch(r"\d+\.\d+\.\d+", __version__) else BLOCK,
            "message": __version__,
        }
    )
    result = PASS if all(item["result"] == PASS for item in checks) else BLOCK
    return {
        "schemaVersion": "ctkf.community-doctor.v1",
        "result": result,
        "version": __version__,
        "supportedIdes": list(SUPPORTED_IDES),
        "maxRequirementBytes": MAX_DOCUMENT_BYTES,
        "checks": checks,
        "claimBoundary": "PASS proves that this local CTKF Community runtime can execute its basic filesystem and output contracts; it does not prove generated-application or production readiness.",
    }


def _verification_report(root: Path, findings: list[dict[str, str]], stage_count: int, task_count: int) -> dict[str, Any]:
    return {
        "schemaVersion": "ctkf.community-verification.v1",
        "result": BLOCK if findings else PASS,
        "project": str(root),
        "stageCount": stage_count,
        "taskCount": task_count,
        "findings": findings,
        "claimBoundary": "PASS proves planning package integrity only, not implementation or production readiness.",
    }


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content.rstrip() + "\n")
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ctkf-community", description="Govern plain-language requirements before AI implementation")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a governed planning package from a long text requirement")
    init.add_argument("--requirements", required=True, type=Path)
    init.add_argument("--project", required=True, type=Path)
    init.add_argument("--ide", choices=SUPPORTED_IDES, default="codex")
    init.add_argument("--force", action="store_true")
    verify_command = sub.add_parser("verify", help="Verify the generated planning package")
    verify_command.add_argument("--project", required=True, type=Path)
    status_command = sub.add_parser("status", help="Show package integrity and unresolved question gates")
    status_command.add_argument("--project", required=True, type=Path)
    sub.add_parser("doctor", help="Check local runtime compatibility without reading project or customer data")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            report = initialize(args.requirements, args.project, args.ide, args.force)
        elif args.command == "verify":
            report = verify(args.project)
        elif args.command == "status":
            report = status(args.project)
        else:
            report = doctor()
    except (OSError, ValueError) as exc:
        report = {"schemaVersion": "ctkf.community-error.v1", "result": BLOCK, "error": str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("result") == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
