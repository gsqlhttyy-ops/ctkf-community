from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ctkf_community.cli import BLOCK, PASS, initialize, verify


class CommunityCliTests(unittest.TestCase):
    def test_long_plain_language_intake_materializes_mainline_and_atomic_backlog(self) -> None:
        requirement = """# 目标
开发一个可以收费的在线预约网站，用户注册后可以预约顾问并在线支付。

# 质量
支持手机和电脑，正式上线前完成测试。系统使用 AI 帮助整理咨询摘要。
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "requirements.txt"
            source.write_text(requirement, encoding="utf-8")
            project = root / "project"

            report = initialize(source, project, "codex")

            self.assertEqual(PASS, report["result"], report["findings"])
            self.assertEqual(19, report["stageCount"])
            self.assertEqual(57, report["taskCount"])
            self.assertEqual("BLOCK", report["questionGateStatus"])
            intake = json.loads((project / ".ctkf-community" / "intake.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(intake["questionGate"]["questions"]), 4)
            self.assertTrue((project / "RUNBOOK.md").is_file())

    def test_verify_detects_requirement_source_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "requirements.txt"
            source.write_text("开发一个公开内容网站。访客可以浏览文章，管理员可以发布文章。", encoding="utf-8")
            project = root / "project"
            initialize(source, project, "catpaw")
            managed_source = project / ".ctkf-community" / "source" / "requirements.txt"
            managed_source.write_text("tampered\n", encoding="utf-8")

            report = verify(project)

            self.assertEqual(BLOCK, report["result"])
            self.assertIn("source-hash", {item["id"] for item in report["findings"]})

    def test_initialize_refuses_an_unmanaged_nonempty_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "requirements.txt"
            source.write_text("开发一个预约系统，访客查看时间并提交预约，管理员处理预约。", encoding="utf-8")
            project = root / "project"
            project.mkdir()
            (project / "user-file.txt").write_text("preserve", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "non-empty"):
                initialize(source, project, "opencode")

            self.assertEqual("preserve", (project / "user-file.txt").read_text(encoding="utf-8"))

    def test_binary_or_tiny_requirement_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "binary.txt"
            binary.write_bytes(b"abc\x00def")
            with self.assertRaisesRegex(ValueError, "binary"):
                initialize(binary, root / "project", "codex")


if __name__ == "__main__":
    unittest.main()
