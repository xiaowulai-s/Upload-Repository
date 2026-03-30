"""更新日志生成器"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ChangeItem:
    category: str
    description: str
    file_path: Optional[str] = None


@dataclass
class ChangelogEntry:
    version: str
    date: datetime
    changes: List[ChangeItem] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        lines = [f"## [{self.version}] - {self.date.strftime('%Y-%m-%d')}", ""]
        
        categories = {}
        for change in self.changes:
            if change.category not in categories:
                categories[change.category] = []
            categories[change.category].append(change)
        
        category_names = {
            "added": "Added",
            "changed": "Changed",
            "fixed": "Fixed",
            "removed": "Removed",
            "deprecated": "Deprecated",
            "security": "Security"
        }
        
        for cat, items in categories.items():
            cat_name = category_names.get(cat, cat.title())
            lines.append(f"### {cat_name}")
            for item in items:
                lines.append(f"- {item.description}")
            lines.append("")
        
        return "\n".join(lines)


class ChangelogGenerator:
    """更新日志生成器"""
    
    CATEGORY_PATTERNS = {
        "added": [
            r"add(ed)?\s+",
            r"new\s+(feature|option|method|class|function)",
            r"implement(ed)?\s+",
            r"create(d)?\s+",
            r"introduce(d)?\s+",
        ],
        "changed": [
            r"change(d)?\s+",
            r"update(d)?\s+",
            r"modify(ied)?\s+",
            r"improve(d)?\s+",
            r"refactor(ed)?\s+",
            r"rename(d)?\s+",
            r"move(d)?\s+",
        ],
        "fixed": [
            r"fix(ed)?\s+",
            r"resolve(d)?\s+",
            r"correct(ed)?\s+",
            r"repair(ed)?\s+",
            r"bug\s*fix",
        ],
        "removed": [
            r"remove(d)?\s+",
            r"delete(d)?\s+",
            r"drop(ped)?\s+",
            r"eliminate(d)?\s+",
        ],
        "deprecated": [
            r"deprecate(d)?\s+",
            r"obsolete\s+",
            r"will\s+be\s+removed",
        ],
        "security": [
            r"security\s+",
            r"vulnerability\s+",
            r"exploit\s+",
            r"secure(d)?\s+",
        ]
    }
    
    FILE_TYPE_CATEGORIES = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React",
        ".tsx": "React",
        ".vue": "Vue",
        ".css": "Styles",
        ".scss": "Styles",
        ".html": "HTML",
        ".md": "Documentation",
        ".json": "Configuration",
        ".yaml": "Configuration",
        ".yml": "Configuration",
        ".toml": "Configuration",
        ".txt": "Text",
        ".sh": "Script",
        ".bat": "Script",
        ".ps1": "Script",
    }
    
    def __init__(self, template_path: Optional[Path] = None):
        self.template_path = template_path
    
    def analyze_diff(self, diff_content: str) -> List[ChangeItem]:
        """分析 diff 内容，提取变更项"""
        changes = []
        
        lines = diff_content.split("\n")
        
        current_file = None
        for line in lines:
            if line.startswith("diff --git"):
                match = re.search(r"diff --git a/(.+?) b/(.+)", line)
                if match:
                    current_file = match.group(2)
            elif line.startswith("+") and not line.startswith("+++"):
                content = line[1:].strip()
                if content and not content.startswith("#"):
                    change = self._analyze_line(content, current_file)
                    if change:
                        changes.append(change)
        
        return changes
    
    def _analyze_line(self, line: str, file_path: Optional[str]) -> Optional[ChangeItem]:
        """分析单行内容"""
        line_lower = line.lower()
        
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    return ChangeItem(
                        category=category,
                        description=line,
                        file_path=file_path
                    )
        
        return ChangeItem(
            category="changed",
            description=line,
            file_path=file_path
        )
    
    def generate_commit_message(
        self, 
        diff_content: str,
        style: str = "conventional"
    ) -> str:
        """根据 diff 生成 commit message"""
        changes = self.analyze_diff(diff_content)
        
        if not changes:
            return "chore: update files"
        
        category_counts: Dict[str, int] = {}
        for change in changes:
            category_counts[change.category] = category_counts.get(change.category, 0) + 1
        
        main_category = max(category_counts, key=category_counts.get)
        
        file_types: Dict[str, int] = {}
        for change in changes:
            if change.file_path:
                ext = Path(change.file_path).suffix
                file_type = self.FILE_TYPE_CATEGORIES.get(ext, "Other")
                file_types[file_type] = file_types.get(file_type, 0) + 1
        
        main_file_type = max(file_types, key=file_types.get) if file_types else "files"
        
        count = len(changes)
        
        if style == "conventional":
            type_map = {
                "added": "feat",
                "changed": "refactor",
                "fixed": "fix",
                "removed": "refactor",
                "deprecated": "refactor",
                "security": "fix"
            }
            prefix = type_map.get(main_category, "chore")
            
            if count == 1:
                desc = changes[0].description[:50]
                return f"{prefix}: {desc}"
            else:
                return f"{prefix}: update {count} {main_file_type.lower()} files"
        
        elif style == "simple":
            if count == 1:
                return changes[0].description[:72]
            else:
                return f"Update {count} files ({main_category})"
        
        else:
            return f"Update {count} files"
    
    def generate_changelog(
        self,
        commits: List[Dict[str, Any]],
        version: str = "Unreleased"
    ) -> str:
        """生成 CHANGELOG 内容"""
        entry = ChangelogEntry(
            version=version,
            date=datetime.now()
        )
        
        for commit in commits:
            message = commit.get("message", "")
            files = commit.get("files", [])
            
            change = self._parse_commit_message(message, files)
            if change:
                entry.changes.append(change)
        
        return entry.to_markdown()
    
    def _parse_commit_message(
        self, 
        message: str, 
        files: List[str]
    ) -> Optional[ChangeItem]:
        """解析 commit message"""
        message = message.strip()
        
        conventional_pattern = r"^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?:\s*(.+)"
        match = re.match(conventional_pattern, message)
        
        if match:
            commit_type = match.group(1)
            description = match.group(3)
            
            type_to_category = {
                "feat": "added",
                "fix": "fixed",
                "docs": "changed",
                "style": "changed",
                "refactor": "changed",
                "test": "changed",
                "chore": "changed"
            }
            
            return ChangeItem(
                category=type_to_category.get(commit_type, "changed"),
                description=description,
                file_path=files[0] if files else None
            )
        
        for category, patterns in self.CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message.lower()):
                    return ChangeItem(
                        category=category,
                        description=message,
                        file_path=files[0] if files else None
                    )
        
        return ChangeItem(
            category="changed",
            description=message,
            file_path=files[0] if files else None
        )
    
    def merge_changelog(
        self,
        existing_content: str,
        new_entry: str
    ) -> str:
        """合并新的 changelog 条目到现有内容"""
        lines = existing_content.split("\n")
        
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith("## ["):
                header_end = i
                break
        
        if header_end == 0:
            if existing_content.strip():
                return existing_content + "\n\n" + new_entry
            else:
                return "# Changelog\n\n" + new_entry
        
        return (
            "\n".join(lines[:header_end]) + 
            "\n" + 
            new_entry + 
            "\n" + 
            "\n".join(lines[header_end:])
        )
    
    def categorize_files(
        self, 
        files: List[str]
    ) -> Dict[str, List[str]]:
        """按类型分类文件"""
        categories: Dict[str, List[str]] = {}
        
        for file_path in files:
            ext = Path(file_path).suffix
            category = self.FILE_TYPE_CATEGORIES.get(ext, "Other")
            
            if category not in categories:
                categories[category] = []
            categories[category].append(file_path)
        
        return categories
