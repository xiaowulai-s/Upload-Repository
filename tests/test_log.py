"""测试日志功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from pathlib import Path

from src.core.changelog_gen import ChangelogGenerator, ChangelogEntry, ChangeItem


def test_changelog_generator():
    print("=" * 50)
    print("测试日志生成器...")
    print("=" * 50)
    
    generator = ChangelogGenerator()
    
    diff_content = """
diff --git a/src/main.py b/src/main.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/main.py
@@ -0,0 +1,10 @@
+def main():
+    print("Hello, World!")
+
+if __name__ == "__main__":
+    main()
diff --git a/README.md b/README.md
index abcdefg..1234567 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,5 @@
 # Project
 
+Added new feature for user authentication.
+
+Fixed bug in login flow.
"""
    
    changes = generator.analyze_diff(diff_content)
    print(f"[OK] 分析 diff: 发现 {len(changes)} 个变更")
    
    for change in changes[:3]:
        print(f"  - [{change.category}] {change.description[:40]}...")
    
    message = generator.generate_commit_message(diff_content, style="conventional")
    print(f"[OK] 生成 commit message: {message}")
    
    commits = [
        {
            "hash": "abc123",
            "author": "Developer",
            "date": "2024-01-15T10:30:00",
            "message": "feat: add user authentication",
            "files": ["src/auth.py", "src/models/user.py"]
        },
        {
            "hash": "def456",
            "author": "Developer",
            "date": "2024-01-14T15:45:00",
            "message": "fix: resolve login timeout issue",
            "files": ["src/auth.py"]
        },
        {
            "hash": "ghi789",
            "author": "Developer",
            "date": "2024-01-13T09:00:00",
            "message": "docs: update installation guide",
            "files": ["README.md"]
        }
    ]
    
    changelog = generator.generate_changelog(commits, version="1.0.0")
    print(f"[OK] 生成 CHANGELOG:")
    print("-" * 40)
    print(changelog[:300] + "..." if len(changelog) > 300 else changelog)
    print("-" * 40)
    
    existing = """# Changelog

## [0.9.0] - 2024-01-01

### Added
- Initial release
"""
    
    merged = generator.merge_changelog(existing, changelog)
    print(f"[OK] 合并 CHANGELOG: {len(merged)} 字符")
    
    files = [
        "src/main.py",
        "src/utils.py",
        "tests/test_main.py",
        "README.md",
        "config.yaml"
    ]
    
    categories = generator.categorize_files(files)
    print(f"[OK] 文件分类:")
    for cat, files in categories.items():
        print(f"  - {cat}: {len(files)} 个文件")
    
    print("\n日志生成器测试通过!\n")


def test_change_item():
    print("=" * 50)
    print("测试变更项...")
    print("=" * 50)
    
    item = ChangeItem(
        category="added",
        description="Add new feature for user authentication",
        file_path="src/auth.py"
    )
    
    print(f"[OK] 创建变更项: {item.category} - {item.description[:30]}...")
    
    entry = ChangelogEntry(
        version="1.0.0",
        date=datetime.now(),
        changes=[
            ChangeItem("added", "New feature A"),
            ChangeItem("added", "New feature B"),
            ChangeItem("fixed", "Bug fix for issue #123"),
            ChangeItem("changed", "Update configuration"),
        ]
    )
    
    markdown = entry.to_markdown()
    print(f"[OK] 生成 Markdown:")
    print("-" * 40)
    print(markdown)
    print("-" * 40)
    
    print("\n变更项测试通过!\n")


def test_message_styles():
    print("=" * 50)
    print("测试不同风格的 commit message...")
    print("=" * 50)
    
    generator = ChangelogGenerator()
    
    diff = """
+Added new API endpoint for user registration
+Fixed validation error in email field
+Updated database schema
"""
    
    conventional = generator.generate_commit_message(diff, style="conventional")
    print(f"[OK] Conventional: {conventional}")
    
    simple = generator.generate_commit_message(diff, style="simple")
    print(f"[OK] Simple: {simple}")
    
    print("\nCommit message 风格测试通过!\n")


def main():
    print("\n" + "=" * 50)
    print("GitHub 仓库同步工具 - 日志功能测试")
    print("=" * 50 + "\n")
    
    try:
        test_change_item()
        test_changelog_generator()
        test_message_styles()
        
        print("=" * 50)
        print("[OK] 所有日志测试通过!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
