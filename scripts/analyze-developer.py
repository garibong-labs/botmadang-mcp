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

# 시각화는 선택적 의존성
try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

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
        "hours_detail": dict(working_hours["hours"]),
        "weekdays_detail": dict(working_hours["weekdays"]),
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


def generate_visualizations(profile: dict, output_dir: Path) -> list[str]:
    """시각화 차트 생성"""
    if not HAS_MATPLOTLIB:
        print("matplotlib이 설치되지 않았습니다. pip install matplotlib 실행 후 다시 시도하세요.")
        return []

    # 한글 폰트 설정 (macOS)
    plt.rcParams['font.family'] = ['AppleGothic', 'Malgun Gothic', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    # 1. 작업 유형 파이 차트
    if profile.get("task_types"):
        fig, ax = plt.subplots(figsize=(10, 8))
        task_types = profile["task_types"]
        labels = list(task_types.keys())
        sizes = list(task_types.values())
        colors = plt.cm.Pastel1(range(len(labels)))

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        ax.set_title('작업 유형 분포', fontsize=16, fontweight='bold')

        filepath = output_dir / "task_types_pie.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        generated_files.append(str(filepath))

    # 2. 활동 시간대 바 차트
    wp = profile.get("working_patterns", {})
    if "hours_detail" in profile:
        fig, ax = plt.subplots(figsize=(14, 6))
        hours_data = profile["hours_detail"]
        hours = list(range(24))
        counts = [hours_data.get(h, 0) for h in hours]

        bars = ax.bar(hours, counts, color='steelblue', edgecolor='navy', alpha=0.8)
        ax.set_xlabel('시간 (24시간)', fontsize=12)
        ax.set_ylabel('세션 수', fontsize=12)
        ax.set_title('시간대별 활동 패턴', fontsize=16, fontweight='bold')
        ax.set_xticks(hours)
        ax.set_xticklabels([f'{h}시' for h in hours], rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)

        # 피크 시간 강조
        peak_hours = wp.get("peak_hours", [])
        for i, bar in enumerate(bars):
            if i in peak_hours:
                bar.set_color('coral')
                bar.set_edgecolor('darkred')

        filepath = output_dir / "activity_hours.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        generated_files.append(str(filepath))

    # 3. 기술 스택 바 차트
    if profile.get("tech_stack"):
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        fig.suptitle('기술 스택 분석', fontsize=18, fontweight='bold')

        categories = ["languages", "frameworks", "tools", "databases"]
        titles = ["프로그래밍 언어", "프레임워크", "도구", "데이터베이스"]
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0']

        for idx, (cat, title, color) in enumerate(zip(categories, titles, colors)):
            ax = axes[idx // 2, idx % 2]
            data = profile["tech_stack"].get(cat, {})

            if data:
                techs = list(data.keys())[:8]
                counts = [data[t] for t in techs]

                bars = ax.barh(techs, counts, color=color, alpha=0.8, edgecolor='black')
                ax.set_xlabel('언급 횟수')
                ax.set_title(title, fontsize=14, fontweight='bold')
                ax.invert_yaxis()

                for bar, count in zip(bars, counts):
                    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                           str(count), va='center', fontsize=10)
            else:
                ax.text(0.5, 0.5, '데이터 없음', ha='center', va='center', fontsize=12)
                ax.set_title(title, fontsize=14, fontweight='bold')

        plt.tight_layout()
        filepath = output_dir / "tech_stack.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        generated_files.append(str(filepath))

    # 4. 요일별 활동 차트
    if "weekdays_detail" in profile:
        fig, ax = plt.subplots(figsize=(10, 6))
        weekdays_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
        weekdays_data = profile["weekdays_detail"]

        counts = [weekdays_data.get(d, 0) for d in weekdays_order]
        colors = ['#5DADE2'] * 5 + ['#F39C12'] * 2  # 주중은 파랑, 주말은 주황

        bars = ax.bar(weekdays_kr, counts, color=colors, edgecolor='black', alpha=0.8)
        ax.set_xlabel('요일', fontsize=12)
        ax.set_ylabel('세션 수', fontsize=12)
        ax.set_title('요일별 활동 패턴', fontsize=16, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                       str(count), ha='center', fontsize=11, fontweight='bold')

        filepath = output_dir / "activity_weekdays.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        generated_files.append(str(filepath))

    # 5. 종합 대시보드
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('개발자 프로필 대시보드', fontsize=20, fontweight='bold', y=0.98)

    # 메트릭 요약
    ax1 = fig.add_subplot(2, 3, 1)
    ax1.axis('off')
    m = profile["metrics"]
    metrics_text = f"""
    📊 활동 통계

    총 세션: {m['total_sessions']}
    총 메시지: {m['total_messages']}
    세션당 메시지: {m['avg_messages_per_session']:.1f}
    평균 메시지 길이: {m['avg_message_length']}자
    질문 비율: {m['question_ratio']}%
    프로젝트 수: {profile['project_count']}
    """
    ax1.text(0.1, 0.5, metrics_text, fontsize=12, verticalalignment='center',
             fontfamily='monospace', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))

    # 작업 유형 (파이)
    ax2 = fig.add_subplot(2, 3, 2)
    if profile.get("task_types"):
        task_types = profile["task_types"]
        ax2.pie(list(task_types.values()), labels=list(task_types.keys()),
               autopct='%1.0f%%', colors=plt.cm.Pastel1(range(len(task_types))))
    ax2.set_title('작업 유형', fontsize=14, fontweight='bold')

    # 주요 언어 (바)
    ax3 = fig.add_subplot(2, 3, 3)
    if profile.get("tech_stack", {}).get("languages"):
        langs = profile["tech_stack"]["languages"]
        ax3.barh(list(langs.keys())[:5], list(langs.values())[:5], color='#4CAF50')
        ax3.invert_yaxis()
    ax3.set_title('주요 언어', fontsize=14, fontweight='bold')

    # 시간대 (바)
    ax4 = fig.add_subplot(2, 3, 4)
    if "hours_detail" in profile:
        hours_data = profile["hours_detail"]
        hours = list(range(24))
        counts = [hours_data.get(h, 0) for h in hours]
        ax4.bar(hours, counts, color='steelblue', alpha=0.8)
        ax4.set_xticks([0, 6, 12, 18, 23])
        ax4.set_xticklabels(['0시', '6시', '12시', '18시', '23시'])
    ax4.set_title('활동 시간대', fontsize=14, fontweight='bold')

    # 요일 (바)
    ax5 = fig.add_subplot(2, 3, 5)
    if "weekdays_detail" in profile:
        weekdays_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
        weekdays_data = profile["weekdays_detail"]
        counts = [weekdays_data.get(d, 0) for d in weekdays_order]
        colors = ['#5DADE2'] * 5 + ['#F39C12'] * 2
        ax5.bar(weekdays_kr, counts, color=colors)
    ax5.set_title('활동 요일', fontsize=14, fontweight='bold')

    # 도구 (바)
    ax6 = fig.add_subplot(2, 3, 6)
    if profile.get("tech_stack", {}).get("tools"):
        tools = profile["tech_stack"]["tools"]
        ax6.barh(list(tools.keys())[:5], list(tools.values())[:5], color='#FF9800')
        ax6.invert_yaxis()
    ax6.set_title('주요 도구', fontsize=14, fontweight='bold')

    plt.tight_layout()
    filepath = output_dir / "dashboard.png"
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    generated_files.append(str(filepath))

    return generated_files


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code 사용 기록 기반 개발자 프로필 분석")
    parser.add_argument("--no-anonymize", action="store_true", help="익명화하지 않음")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    parser.add_argument("--output", "-o", help="출력 파일 경로")
    parser.add_argument("--visualize", "-v", action="store_true", help="시각화 차트 생성")
    parser.add_argument("--viz-output", default="./profile_charts", help="시각화 출력 디렉토리 (기본: ./profile_charts)")
    args = parser.parse_args()

    profile = generate_profile(anonymize=not args.no_anonymize)

    # 시각화 생성
    if args.visualize:
        output_dir = Path(args.viz_output)
        generated = generate_visualizations(profile, output_dir)
        if generated:
            print(f"시각화 생성 완료:")
            for f in generated:
                print(f"  - {f}")
            print()

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
