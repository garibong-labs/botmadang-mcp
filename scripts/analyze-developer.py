#!/usr/bin/env python3
"""
개발자 프로필 분석기
~/.claude/projects/ 디렉토리의 대화 기록을 분석하여 개발자 프로필을 생성합니다.
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# 기술 스택 키워드 매핑
TECH_KEYWORDS = {
    "languages": {
        "python": ["python", ".py", "pip", "pytest", "django", "flask", "fastapi"],
        "typescript": ["typescript", ".ts", ".tsx", "tsc"],
        "javascript": ["javascript", ".js", ".jsx", "node", "npm", "yarn"],
        "rust": ["rust", ".rs", "cargo", "rustc"],
        "go": ["golang", ".go", "go build", "go run"],
        "java": ["java", ".java", "maven", "gradle", "spring"],
        "kotlin": [".kt", "kotlin"],
        "swift": [".swift", "swiftui", "xcode"],
        "c++": [".cpp", ".hpp", "cmake"],
        "c#": [".cs", "dotnet", "csharp"],
    },
    "frameworks": {
        "react": ["react", "jsx", "tsx", "next.js", "nextjs"],
        "vue": ["vue", "vuex", "nuxt"],
        "angular": ["angular", "ng "],
        "express": ["express", "expressjs"],
        "fastapi": ["fastapi"],
        "django": ["django"],
        "flask": ["flask"],
        "spring": ["spring", "springboot"],
    },
    "tools": {
        "git": ["git ", "commit", "push", "pull", "branch", "merge"],
        "docker": ["docker", "dockerfile", "container"],
        "kubernetes": ["kubernetes", "k8s", "kubectl", "helm"],
        "aws": ["aws", "s3", "ec2", "lambda", "cloudformation"],
        "terraform": ["terraform", ".tf"],
        "github_actions": ["github actions", ".github/workflows"],
    },
    "databases": {
        "postgresql": ["postgres", "postgresql", "psql"],
        "mysql": ["mysql", "mariadb"],
        "mongodb": ["mongodb", "mongo"],
        "redis": ["redis"],
        "sqlite": ["sqlite"],
    },
}

# 작업 유형 키워드
TASK_PATTERNS = {
    "debugging": ["fix", "bug", "error", "issue", "broken", "not working", "debug", "왜 안", "에러", "버그"],
    "new_feature": ["add", "create", "implement", "new", "build", "만들어", "추가", "구현"],
    "refactoring": ["refactor", "clean", "improve", "optimize", "리팩토링", "개선", "정리"],
    "learning": ["how to", "what is", "explain", "어떻게", "뭐야", "설명", "알려줘"],
    "review": ["review", "check", "look at", "리뷰", "확인", "검토"],
    "testing": ["test", "spec", "테스트", "검증"],
    "documentation": ["document", "readme", "comment", "문서", "주석"],
}


def load_sessions_index(project_dir: Path) -> list[dict]:
    """세션 인덱스 파일 로드"""
    index_file = project_dir / "sessions-index.json"
    if not index_file.exists():
        return []

    with open(index_file) as f:
        data = json.load(f)
        return data.get("entries", [])


def load_session_messages(jsonl_path: Path) -> list[dict]:
    """JSONL 파일에서 메시지 로드"""
    messages = []
    if not jsonl_path.exists():
        return messages

    with open(jsonl_path) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("type") in ["user", "assistant"]:
                    messages.append(entry)
            except json.JSONDecodeError:
                continue

    return messages


def extract_user_messages(messages: list[dict]) -> list[str]:
    """사용자 메시지만 추출"""
    user_texts = []
    for msg in messages:
        if msg.get("type") == "user":
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, str):
                user_texts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        user_texts.append(item.get("text", ""))
    return user_texts


def extract_file_changes(messages: list[dict]) -> list[str]:
    """파일 변경 내역 추출"""
    files = []
    for msg in messages:
        if msg.get("type") == "file-history-snapshot":
            snapshot = msg.get("snapshot", {})
            tracked = snapshot.get("trackedFileBackups", {})
            files.extend(tracked.keys())
    return files


def analyze_tech_stack(texts: list[str], files: list[str]) -> dict[str, Counter]:
    """기술 스택 분석"""
    combined_text = " ".join(texts + files).lower()

    results = {}
    for category, techs in TECH_KEYWORDS.items():
        counter = Counter()
        for tech, keywords in techs.items():
            count = sum(1 for kw in keywords if kw.lower() in combined_text)
            if count > 0:
                counter[tech] = count
        results[category] = counter

    return results


def analyze_task_types(texts: list[str]) -> Counter:
    """작업 유형 분석"""
    combined_text = " ".join(texts).lower()
    counter = Counter()

    for task_type, patterns in TASK_PATTERNS.items():
        count = sum(1 for p in patterns if p.lower() in combined_text)
        if count > 0:
            counter[task_type] = count

    return counter


def analyze_working_hours(sessions: list[dict]) -> dict:
    """작업 시간대 분석"""
    hours = Counter()
    weekdays = Counter()

    for session in sessions:
        created = session.get("created")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                hours[dt.hour] += 1
                weekdays[dt.strftime("%A")] += 1
            except:
                continue

    return {"hours": hours, "weekdays": weekdays}


def calculate_metrics(sessions: list[dict], all_user_messages: list[str]) -> dict:
    """주요 메트릭 계산"""
    total_sessions = len(sessions)
    total_messages = sum(s.get("messageCount", 0) for s in sessions)

    # 평균 메시지 길이
    avg_message_length = (
        sum(len(m) for m in all_user_messages) / len(all_user_messages)
        if all_user_messages else 0
    )

    # 질문형 메시지 비율
    question_count = sum(1 for m in all_user_messages if "?" in m or "?" in m)
    question_ratio = question_count / len(all_user_messages) if all_user_messages else 0

    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "avg_messages_per_session": total_messages / total_sessions if total_sessions else 0,
        "avg_message_length": round(avg_message_length),
        "question_ratio": round(question_ratio * 100, 1),
    }


def generate_profile(anonymize: bool = True) -> dict[str, Any]:
    """개발자 프로필 생성"""
    all_sessions = []
    all_user_messages = []
    all_files = []
    project_names = []

    # 모든 프로젝트 순회
    for project_dir in CLAUDE_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        sessions = load_sessions_index(project_dir)
        all_sessions.extend(sessions)

        # 프로젝트 이름 추출 (익명화 시 해시)
        project_name = project_dir.name
        if anonymize:
            project_name = f"project_{hash(project_name) % 10000:04d}"
        project_names.append(project_name)

        # 세션별 메시지 로드
        for session in sessions:
            jsonl_path = Path(session.get("fullPath", ""))
            messages = load_session_messages(jsonl_path)
            all_user_messages.extend(extract_user_messages(messages))
            all_files.extend(extract_file_changes(messages))

    # 분석 실행
    tech_stack = analyze_tech_stack(all_user_messages, all_files)
    task_types = analyze_task_types(all_user_messages)
    working_hours = analyze_working_hours(all_sessions)
    metrics = calculate_metrics(all_sessions, all_user_messages)

    # 프로필 생성
    profile = {
        "generated_at": datetime.now().isoformat(),
        "anonymized": anonymize,
        "metrics": metrics,
        "tech_stack": {
            category: dict(counter.most_common(5))
            for category, counter in tech_stack.items()
            if counter
        },
        "task_types": dict(task_types.most_common()),
        "working_patterns": {
            "peak_hours": [h for h, _ in working_hours["hours"].most_common(3)],
            "active_days": [d for d, _ in working_hours["weekdays"].most_common(3)],
        },
        "project_count": len(set(project_names)),
    }

    return profile


def generate_summary(profile: dict) -> str:
    """프로필 요약 텍스트 생성"""
    lines = ["## 개발자 프로필 분석 결과\n"]

    # 메트릭
    m = profile["metrics"]
    lines.append(f"### 활동 통계")
    lines.append(f"- 총 세션 수: {m['total_sessions']}")
    lines.append(f"- 총 메시지 수: {m['total_messages']}")
    lines.append(f"- 세션당 평균 메시지: {m['avg_messages_per_session']:.1f}")
    lines.append(f"- 평균 메시지 길이: {m['avg_message_length']} 자")
    lines.append(f"- 질문형 메시지 비율: {m['question_ratio']}%")
    lines.append(f"- 프로젝트 수: {profile['project_count']}\n")

    # 기술 스택
    if profile["tech_stack"]:
        lines.append("### 주요 기술 스택")
        for category, techs in profile["tech_stack"].items():
            if techs:
                tech_list = ", ".join(f"{t}({c})" for t, c in techs.items())
                lines.append(f"- **{category}**: {tech_list}")
        lines.append("")

    # 작업 유형
    if profile["task_types"]:
        lines.append("### 작업 유형 분포")
        for task, count in profile["task_types"].items():
            lines.append(f"- {task}: {count}")
        lines.append("")

    # 작업 패턴
    wp = profile["working_patterns"]
    if wp["peak_hours"]:
        lines.append("### 작업 패턴")
        lines.append(f"- 주요 활동 시간대: {', '.join(f'{h}시' for h in wp['peak_hours'])}")
        if wp["active_days"]:
            lines.append(f"- 주요 활동 요일: {', '.join(wp['active_days'])}")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code 사용 기록 기반 개발자 프로필 분석")
    parser.add_argument("--no-anonymize", action="store_true", help="익명화하지 않음")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    parser.add_argument("--output", "-o", help="출력 파일 경로")
    args = parser.parse_args()

    profile = generate_profile(anonymize=not args.no_anonymize)

    if args.json:
        output = json.dumps(profile, indent=2, ensure_ascii=False)
    else:
        output = generate_summary(profile)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"저장됨: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
