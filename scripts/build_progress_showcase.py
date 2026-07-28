from __future__ import annotations

import html
import base64
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = ROOT / "review_workspace"
OUTPUT_PATH = ROOT / "docs" / "GLOBAL_TERMINAL_PROGRESS_KO.html"
LINKED_OUTPUT_PATH = ROOT / "docs" / "GLOBAL_TERMINAL_PROGRESS_KO_LINKED.html"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


PHASE_META: dict[str, tuple[str, str]] = {
    "4": ("지도 중심 War Room", "이벤트·레이어·출처 상태를 한 화면에 배치한 지도 제품 기반"),
    "5G": ("웹 제품 표면", "계약 기반 Next.js 상업용 웹 셸과 source-aware 화면 채택"),
    "5H": ("Global Risk Map", "지도·뉴스·시장 전이 관계를 출처와 함께 탐색"),
    "5I": ("Market Map", "Finviz형 히트맵·검색·필터·종목 drilldown"),
    "5J": ("Options Quant", "옵션 체인·IV 구조·Greeks·시나리오 연구"),
    "5K": ("Portfolio Risk", "성과·리스크·상관·요인·스트레스 분석"),
    "5L": ("Research Memory", "출처를 보존하는 메모·관심 목록·연구 기억"),
    "5M": ("Symbol Workstation", "주식·ETF·크립토의 정확한 심벌 워크스테이션"),
    "5N": ("Symbol Intelligence", "가격·기술·재무·촉매·뉴스를 묶은 종목 인텔리전스"),
    "5O": ("Market Discovery", "시장 탐색과 순위·진단·소스 상태 확장"),
    "5P": ("War Room Replay", "지도 시간창·비교·재생과 이벤트 선택 상태"),
    "5Q": ("Daily Brief", "클레임 원장·출처 레지스터·차트가 있는 일일 브리프"),
    "5R": ("Brief Depth", "브리프 비교·캡처·검토 흐름의 깊이 강화"),
    "5S": ("Route Parity", "주요 Streamlit 기능을 웹 경로와 탐색 체계로 가시화"),
    "5T": ("Reliability Closure", "BTC 첫 실행, Options, News의 실패·모바일 상태 보강"),
    "5U": ("Map Density", "첫 화면에서 지리·사건·뉴스 맥락을 더 빠르게 파악"),
    "5V": ("Workstation Depth", "차트·재무·기술·뉴스·소스 패널의 제품 깊이"),
    "5W": ("Runtime Orchestration", "온라인·캐시·오프라인 경계를 제품 상태로 통합"),
    "5X": ("Provider Breadth", "Alpha Vantage·Finnhub 등 무료 우선 공급자 폭 확대"),
    "5Y": ("Event Fusion", "29개 관측 마커와 뉴스·자산 맥락을 보수적으로 연결"),
    "5Z": ("Universe Breadth", "공식 상장 목록 기반 시장 유니버스와 발견 기능 확대"),
    "6A": ("SEC & Calendar", "SEC facts·실적 일정·시장 스냅샷의 materialization"),
    "6B": ("Broad Universe", "333개 종목·분류·제한된 refresh 운영 기반"),
    "6C": ("Dynamic Workstation", "333/333 정확 심벌 활성화와 격리된 캐시/LKG"),
    "6D": ("Watchlist Desk", "로컬 비공개 관심 목록·정렬·차트·연구 이유"),
    "6E": ("Progressive Delivery", "가벼운 초기 문서와 패널별 점진 로딩"),
    "6F": ("Research Snapshot", "비용이 제한된 다종목 연구 스냅샷"),
    "6G": ("Change Inbox", "저장 스냅샷 diff와 중요한 변화 검토"),
    "6H": ("Analyst Workspace", "차트·재무·기술·촉매·뉴스를 동기화한 분석 공간"),
    "6I": ("Research Operations", "관측·실패·quota·복구를 다루는 로컬 운영 흐름"),
    "6J": ("Identity & Tenancy", "익명 사용을 보존한 사용자 세션·격리 기반"),
    "6K": ("Account Research", "계정 소유 연구 저장·복원·충돌 처리"),
    "6L": ("Hosted Sync Readiness", "Watchlist 동기화 준비와 168px Research rail 교정"),
    "6M": ("Attention Desk", "시장·뉴스·지도·촉매 변화를 우선순위화한 일일 검토"),
    "6N": ("Observation Runs", "명시적 관측 실행·진행·취소·LKG·A/B RLS 증거"),
    "6O": ("Alert Manager", "규칙·평가·trigger·worker 복구와 감사 증거"),
    "6P": ("Hosted Continuity", "Supabase A/B 격리와 새 로컬 저장소 복구 검증"),
}


FEATURED_PATHS = [
    ("phase5h_visual/global-risk-map-desktop.png", "글로벌 리스크 지도", "사건, 뉴스, 출처, 시장 노출을 한 지도에서 탐색"),
    ("phase5i_visual/market-map-live-desktop.png", "시장 히트맵", "333개 공식 상장 목록 기반 발견 흐름의 핵심 표면"),
    ("phase5j_visual/options-live-chain-desktop.png", "옵션 퀀트", "체인 품질, IV, Greeks와 가정 경계를 함께 표시"),
    ("phase5k_visual/portfolio-live-stress-desktop.png", "포트폴리오 스트레스", "과거 재생과 가정 기반 충격을 구분한 리스크 분석"),
    ("phase5m_visual/msft-runtime-desktop.png", "심벌 워크스테이션", "주식·ETF·크립토를 같은 정확 심벌 계약으로 탐색"),
    ("phase5q_visual/daily-brief-fixture-desktop.png", "데일리 브리프", "주장, 차트, 출처 등록부와 검토 기록을 결합"),
    ("phase6h_visual/analyst-workspace-desktop.png", "애널리스트 워크스페이스", "차트·재무·기술·촉매·뉴스의 동기화된 연구"),
    ("phase6l_visual/phase6l-watchlist-nav-fixed-desktop.png", "Watchlist Desk", "관심 종목과 exact workstation을 연결한 일상 사용 흐름"),
    ("phase6m_visual/attention-daily-review-desktop.png", "Attention Desk", "마지막 검토 이후 중요한 변화만 우선순위화"),
    ("phase6n_visual/observation-run-completed-desktop.png", "관측 실행", "실행·quota·진행·완료·실패 상태를 명시적으로 기록"),
    ("phase6o_visual/alert-manager-lifecycle.png", "Alert Manager", "규칙 생명주기와 trigger·worker 복구를 설명 가능하게 표시"),
    ("phase6p_visual/account-continuity-restored-desktop.png", "Hosted 계정 연속성", "Supabase 저장 상태를 새 로컬 저장소에 정확히 복원"),
]


SCORECARD = [
    ("Finviz 히트맵·발견", 4, "333개 공식 목록 종목, 11개 섹터, 14개 필터", "산업 분류는 60개 수준이며 지수 편입 정보는 미지원"),
    ("TradingView 심벌 워크스테이션", 4, "정확 차트·심벌·기간·패널 상태와 모바일 점진 로딩", "드로잉과 멀티 차트 연구 저장은 미지원"),
    ("OpenBB 소스 인식형 워크스페이스", 4, "provider/SLO truth, Attention, 관측, 알림, hosted 복구", "실제 배포된 반복 스케줄 운영 증거가 남음"),
    ("Bloomberg형 고밀도 터미널", 4, "변화 우선순위, exact return, trigger와 감사 증거", "신뢰 가능한 스케줄 운영·관측성 이후 명령 확장 필요"),
    ("WorldMonitor/worldview 지도", 4, "29개 source-backed 마커와 뉴스·자산 맥락", "검증된 weather/AIS/flight/sanctions와 hosted history 부족"),
    ("한국형 컴팩트 분석", 4, "AAPL/BTC/옵션/포트폴리오 KPI와 전용 뉴스 데스크", "한국·글로벌 데스크와 공급자 범위 확장 필요"),
    ("데이터 실재성·투명성", 4, "retrieval/market/run/review clock 분리와 A/B 복구", "실제 recurring run에 같은 증거 체계를 적용해야 함"),
    ("시각 QA·레이아웃", 4, "Phase 6N 23장, 6O 18장, 6P 6장 독립 검증", "배포 런타임과 더 넓은 benchmark journey 증거 필요"),
    ("Streamlit → Web 기능 패리티", 4, "주요 경로와 지도·옵션·뉴스·워크스테이션 가시화", "lab의 전체 주식/크립토·재무·실적 깊이는 아직 차이"),
    ("리서치 보고서 생성", 4, "클레임 원장·출처·diff·로컬 append-only 검토", "예약 전달과 더 풍부한 공급자 범위가 남음"),
]


def phase_code(name: str) -> str:
    match = re.match(r"phase(?P<major>\d+)(?P<minor>[a-z]?)", name.lower())
    if not match:
        return "OTHER"
    return f"{match.group('major')}{match.group('minor').upper()}"


def phase_sort_key(code: str) -> tuple[int, int]:
    match = re.fullmatch(r"(?P<major>\d+)(?P<minor>[A-Z]?)", code)
    if not match:
        return (999, 999)
    minor = match.group("minor")
    return (int(match.group("major")), ord(minor) - 64 if minor else 0)


def screenshot_tags(bundle: str, name: str) -> list[str]:
    haystack = f"{bundle} {name}".lower()
    candidates = [
        "live",
        "online",
        "fixture",
        "cache",
        "stale",
        "offline",
        "failure",
        "blocked",
        "conflict",
        "mobile",
        "tablet",
        "desktop",
        "baseline",
        "final",
        "probe",
        "recovery",
    ]
    tags = [tag for tag in candidates if tag in haystack]
    return tags or ["evidence"]


def collect_screenshots() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    capture_dirs = sorted(
        (
            path
            for path in REVIEW_ROOT.iterdir()
            if path.is_dir()
            and path.name.lower().startswith("phase")
            and "benchmark" not in path.name.lower()
        ),
        key=lambda path: (phase_sort_key(phase_code(path.name)), path.name.lower()),
    )
    for capture_dir in capture_dirs:
        code = phase_code(capture_dir.name)
        title, summary = PHASE_META.get(code, ("제품 증거", "제품 캡처 및 상태 검증"))
        files = sorted(
            (
                path
                for path in capture_dir.rglob("*")
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            ),
            key=lambda path: path.relative_to(capture_dir).as_posix().lower(),
        )
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            src = f"../{relative}"
            rows.append(
                {
                    "id": f"shot-{len(rows) + 1}",
                    "phase": code,
                    "phase_label": f"Phase {code}",
                    "phase_title": title,
                    "phase_summary": summary,
                    "bundle": capture_dir.name,
                    "name": path.name,
                    "relative": relative,
                    "src": src,
                    "bytes": path.stat().st_size,
                    "tags": screenshot_tags(capture_dir.name, path.name),
                    "sort_key": phase_sort_key(code),
                }
            )
    return rows


def format_bytes(value: int) -> str:
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MiB"
    if value >= 1024:
        return f"{value / 1024:.1f} KiB"
    return f"{value} B"


def build_featured_html(screenshots: list[dict[str, object]]) -> str:
    by_relative = {str(row["relative"]): row for row in screenshots}
    cards: list[str] = []
    for relative_tail, title, description in FEATURED_PATHS:
        key = f"review_workspace/{relative_tail}"
        row = by_relative.get(key)
        if not row:
            continue
        cards.append(
            "\n".join(
                [
                    '<article class="feature-shot">',
                    f'  <button class="feature-shot__open" type="button" data-feature-id="{html.escape(str(row["id"]))}" aria-label="{html.escape(title)} 크게 보기">',
                    f'    <img data-feature-image="{html.escape(str(row["id"]))}" alt="{html.escape(title)} 화면" loading="lazy" decoding="async">',
                    "  </button>",
                    '  <div class="feature-shot__copy">',
                    f'    <span>{html.escape(str(row["phase_label"]))}</span>',
                    f'    <h3>{html.escape(title)}</h3>',
                    f'    <p>{html.escape(description)}</p>',
                    "  </div>",
                    "</article>",
                ]
            )
        )
    return "\n".join(cards)


def build_phase_rows(screenshots: list[dict[str, object]]) -> str:
    phase_counts = Counter(str(row["phase"]) for row in screenshots)
    rows: list[str] = []
    for code in sorted(phase_counts, key=phase_sort_key):
        title, summary = PHASE_META.get(code, ("제품 증거", "제품 캡처 및 상태 검증"))
        rows.append(
            f"""
            <tr>
              <td><button class="phase-jump" type="button" data-phase-jump="{html.escape(code)}">Phase {html.escape(code)}</button></td>
              <td><strong>{html.escape(title)}</strong><span>{html.escape(summary)}</span></td>
              <td><span class="status status--done">완료</span></td>
              <td>{phase_counts[code]:,}장</td>
            </tr>"""
        )
    return "\n".join(rows)


def build_scorecard_rows() -> str:
    rows: list[str] = []
    for category, score, evidence, gap in SCORECARD:
        rows.append(
            f"""
            <tr>
              <td><strong>{html.escape(category)}</strong></td>
              <td><span class="score-value">{score}/5</span><span class="score-track" aria-label="5점 만점에 {score}점"><i style="width:{score * 20}%"></i></span></td>
              <td>{html.escape(evidence)}</td>
              <td>{html.escape(gap)}</td>
            </tr>"""
        )
    return "\n".join(rows)


HTML_TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta name="description" content="Global Terminal의 현재 개발 진행상황, 검증 결과, 로드맵과 전체 제품 스크린샷을 담은 한국어 소개 문서">
  <title>Global Terminal · 제품 진행상황</title>
  <style>
    :root {
      --bg: #080a0d;
      --surface: #101419;
      --surface-2: #151b21;
      --surface-3: #1b232b;
      --line: #2b343e;
      --line-strong: #42505d;
      --text: #f3f6f8;
      --muted: #a7b2bd;
      --dim: #74808c;
      --cyan: #20dfc2;
      --green: #8cf0aa;
      --amber: #f0bd52;
      --red: #ff7180;
      --blue: #79a9ff;
      --max: 1480px;
    }

    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, Pretendard, "Noto Sans KR", "Malgun Gothic", Arial, sans-serif;
      line-height: 1.55;
      letter-spacing: 0;
    }
    button, input, select { font: inherit; letter-spacing: 0; }
    button, select { color: inherit; }
    a { color: var(--cyan); text-underline-offset: 3px; }
    a:hover { color: var(--green); }
    img { display: block; max-width: 100%; }
    :focus-visible { outline: 2px solid var(--cyan); outline-offset: 3px; }
    .skip-link { position: fixed; left: 12px; top: -60px; z-index: 100; padding: 10px 14px; background: var(--text); color: var(--bg); }
    .skip-link:focus { top: 12px; }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 30;
      border-bottom: 1px solid var(--line);
      background: rgba(8, 10, 13, .96);
      backdrop-filter: blur(12px);
    }
    .topbar__inner {
      max-width: var(--max);
      min-height: 54px;
      margin: 0 auto;
      padding: 0 24px;
      display: flex;
      align-items: center;
      gap: 22px;
    }
    .brand { display: flex; align-items: baseline; gap: 10px; white-space: nowrap; }
    .brand strong { font-size: 15px; }
    .brand span { color: var(--cyan); font: 700 11px/1 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .topnav { margin-left: auto; display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; }
    .topnav a { padding: 8px 10px; color: var(--muted); text-decoration: none; font-size: 13px; white-space: nowrap; border-bottom: 2px solid transparent; }
    .topnav a:hover { color: var(--text); border-color: var(--cyan); }

    main { overflow: hidden; }
    .section { border-bottom: 1px solid var(--line); }
    .section__inner { max-width: var(--max); margin: 0 auto; padding: 64px 24px; }
    .section--intro .section__inner { padding-top: 50px; padding-bottom: 40px; }
    .eyebrow { margin: 0 0 10px; color: var(--cyan); font: 700 11px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    h1, h2, h3 { margin: 0; line-height: 1.18; letter-spacing: 0; }
    h1 { max-width: 930px; font-size: 42px; font-weight: 740; }
    h2 { font-size: 27px; }
    h3 { font-size: 16px; }
    .lead { max-width: 900px; margin: 18px 0 0; color: var(--muted); font-size: 17px; }
    .truth-line { margin: 22px 0 0; padding: 14px 16px; border-left: 3px solid var(--amber); background: #15140f; color: #ddd6c6; }

    .status-strip {
      margin-top: 32px;
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      border: 1px solid var(--line);
      background: var(--surface);
    }
    .metric { min-width: 0; padding: 15px 16px; border-right: 1px solid var(--line); }
    .metric:last-child { border-right: 0; }
    .metric span { display: block; color: var(--dim); font: 700 10px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .metric strong { display: block; margin-top: 7px; font-size: 18px; overflow-wrap: anywhere; }
    .metric small { display: block; margin-top: 3px; color: var(--muted); font-size: 11px; }
    .good { color: var(--green); }
    .warn { color: var(--amber); }
    .bad { color: var(--red); }

    .section-head { display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, 520px); gap: 30px; align-items: end; margin-bottom: 30px; }
    .section-head p { margin: 0; color: var(--muted); }

    .architecture {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      border: 1px solid var(--line);
      background: var(--surface);
    }
    .arch-node { position: relative; min-width: 0; padding: 20px; border-right: 1px solid var(--line); }
    .arch-node:last-child { border-right: 0; }
    .arch-node b { display: block; color: var(--cyan); font: 700 11px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .arch-node strong { display: block; margin-top: 8px; font-size: 16px; }
    .arch-node p { margin: 8px 0 0; color: var(--muted); font-size: 13px; }
    .arch-node--lab { background: #15140f; }
    .arch-node--hosted { background: #10181a; }

    .capability-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--line); border-left: 1px solid var(--line); }
    .capability { min-width: 0; padding: 22px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); background: var(--surface); }
    .capability__index { color: var(--cyan); font: 700 11px/1 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .capability h3 { margin-top: 14px; font-size: 18px; }
    .capability p { margin: 8px 0 0; color: var(--muted); font-size: 14px; }
    .capability ul { margin: 15px 0 0; padding: 0; list-style: none; color: #d5dce2; font-size: 13px; }
    .capability li { padding: 5px 0; border-top: 1px solid #232b33; }

    .feature-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
    .feature-shot { min-width: 0; border: 1px solid var(--line); background: var(--surface); border-radius: 6px; overflow: hidden; }
    .feature-shot__open { width: 100%; padding: 0; border: 0; border-bottom: 1px solid var(--line); background: #050709; cursor: zoom-in; }
    .feature-shot__open img { width: 100%; aspect-ratio: 16 / 9; object-fit: contain; }
    .feature-shot__copy { padding: 15px; }
    .feature-shot__copy span { color: var(--cyan); font: 700 10px/1 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .feature-shot__copy h3 { margin-top: 8px; }
    .feature-shot__copy p { margin: 6px 0 0; color: var(--muted); font-size: 13px; }

    .table-wrap { overflow-x: auto; border: 1px solid var(--line); }
    table { width: 100%; border-collapse: collapse; min-width: 900px; background: var(--surface); }
    th, td { padding: 13px 15px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 13px; }
    th { color: var(--dim); background: #0d1115; font: 700 10px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    tr:last-child td { border-bottom: 0; }
    td strong { display: block; }
    td > span:not(.status):not(.score-value):not(.score-track) { display: block; margin-top: 3px; color: var(--muted); }
    .score-value { display: inline-block; min-width: 36px; color: var(--green); font-weight: 800; }
    .score-track { display: inline-block; width: 82px; height: 5px; margin-left: 8px; overflow: hidden; background: #252d35; vertical-align: middle; }
    .score-track i { display: block; height: 100%; background: var(--green); }
    .status { display: inline-flex; align-items: center; min-height: 24px; padding: 2px 8px; border: 1px solid var(--line-strong); border-radius: 3px; font-size: 11px; font-weight: 700; }
    .status--done { color: var(--green); border-color: #315e43; }
    .status--next { color: var(--amber); border-color: #685326; }
    .phase-jump { padding: 0; border: 0; background: transparent; color: var(--cyan); cursor: pointer; font: 700 12px/1.4 ui-monospace, SFMono-Regular, Consolas, monospace; text-decoration: underline; text-underline-offset: 3px; }

    .gap-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 1px solid var(--line); border-left: 1px solid var(--line); }
    .gap-item { padding: 20px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); background: var(--surface); }
    .gap-item b { color: var(--amber); font: 700 11px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .gap-item h3 { margin-top: 8px; }
    .gap-item p { margin: 7px 0 0; color: var(--muted); font-size: 13px; }

    .next-plan { display: grid; grid-template-columns: 260px minmax(0, 1fr); border: 1px solid #685326; background: #15140f; }
    .next-plan__label { padding: 22px; border-right: 1px solid #685326; }
    .next-plan__label span { color: var(--amber); font: 700 11px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; }
    .next-plan__label strong { display: block; margin-top: 8px; font-size: 21px; }
    .next-plan__body { padding: 22px; }
    .next-plan__body p { margin: 0; color: #ddd6c6; }
    .next-plan__body ol { margin: 14px 0 0; padding-left: 20px; color: #eee8dc; }
    .next-plan__body li { margin: 5px 0; }

    .gallery-tools {
      position: sticky;
      top: 54px;
      z-index: 20;
      display: grid;
      grid-template-columns: minmax(220px, 1.4fr) repeat(3, minmax(150px, .6fr));
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--line);
      background: rgba(16, 20, 25, .97);
    }
    .control { min-width: 0; }
    .control label { display: block; margin-bottom: 5px; color: var(--dim); font: 700 9px/1.2 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .control input, .control select { width: 100%; height: 38px; padding: 0 10px; border: 1px solid var(--line-strong); border-radius: 3px; background: #0b0f13; color: var(--text); }
    .gallery-meta { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 15px 0; color: var(--muted); font-size: 13px; }
    .gallery-meta strong { color: var(--text); }
    .gallery-actions { display: flex; gap: 7px; }
    .action { min-height: 34px; padding: 5px 10px; border: 1px solid var(--line-strong); border-radius: 3px; background: var(--surface); color: var(--text); cursor: pointer; }
    .action:hover { border-color: var(--cyan); }
    .shot-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .shot { min-width: 0; border: 1px solid var(--line); border-radius: 5px; overflow: hidden; background: var(--surface); }
    .shot__open { width: 100%; padding: 0; border: 0; border-bottom: 1px solid var(--line); background: #050709; cursor: zoom-in; }
    .shot__open img { width: 100%; height: 190px; object-fit: contain; color: var(--muted); font-size: 11px; }
    .shot__copy { padding: 11px; }
    .shot__meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--cyan); font: 700 9px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .shot__copy h3 { margin-top: 7px; font: 700 12px/1.35 ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap: anywhere; }
    .shot__copy p { margin: 5px 0 0; color: var(--dim); font-size: 11px; overflow-wrap: anywhere; }
    .load-row { display: flex; justify-content: center; gap: 8px; margin-top: 22px; }
    .load-row .action { min-width: 140px; }
    .empty { grid-column: 1 / -1; padding: 50px 20px; border: 1px dashed var(--line-strong); color: var(--muted); text-align: center; }

    .source-list { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-top: 1px solid var(--line); border-left: 1px solid var(--line); }
    .source-link { min-width: 0; padding: 16px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); color: var(--text); background: var(--surface); text-decoration: none; }
    .source-link b { display: block; color: var(--cyan); font: 700 10px/1.3 ui-monospace, SFMono-Regular, Consolas, monospace; text-transform: uppercase; }
    .source-link span { display: block; margin-top: 5px; overflow-wrap: anywhere; }

    .footer { max-width: var(--max); margin: 0 auto; padding: 28px 24px 42px; color: var(--dim); font-size: 12px; }
    .footer strong { color: var(--muted); }

    .lightbox { width: min(96vw, 1500px); max-width: none; height: min(94vh, 980px); padding: 0; border: 1px solid var(--line-strong); border-radius: 6px; background: var(--bg); color: var(--text); }
    .lightbox::backdrop { background: rgba(0, 0, 0, .88); }
    .lightbox__bar { min-height: 52px; padding: 9px 12px; border-bottom: 1px solid var(--line); display: flex; align-items: center; gap: 10px; }
    .lightbox__bar strong { min-width: 0; margin-right: auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .icon-button { width: 36px; height: 34px; padding: 0; border: 1px solid var(--line-strong); border-radius: 3px; background: var(--surface); color: var(--text); cursor: pointer; font-size: 18px; }
    .icon-button:hover { border-color: var(--cyan); }
    .lightbox__stage { height: calc(100% - 104px); display: grid; grid-template-columns: 44px minmax(0, 1fr) 44px; align-items: center; background: #030405; }
    .lightbox__stage img { width: 100%; height: 100%; object-fit: contain; }
    .lightbox__caption { min-height: 52px; padding: 10px 14px; border-top: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; gap: 16px; color: var(--muted); font-size: 12px; }
    .lightbox__caption a { white-space: nowrap; }

    @media (max-width: 1100px) {
      .status-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .metric:nth-child(3) { border-right: 0; }
      .metric:nth-child(-n+3) { border-bottom: 1px solid var(--line); }
      .architecture { grid-template-columns: 1fr 1fr; }
      .arch-node { border-bottom: 1px solid var(--line); }
      .arch-node:nth-child(2n) { border-right: 0; }
      .arch-node:last-child { grid-column: 1 / -1; border-bottom: 0; }
      .capability-grid, .feature-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .shot-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .source-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 760px) {
      .topbar__inner { padding: 0 14px; gap: 10px; }
      .brand span { display: none; }
      .topnav a { padding-inline: 7px; font-size: 12px; }
      .section__inner { padding: 48px 16px; }
      .section--intro .section__inner { padding-top: 34px; }
      h1 { font-size: 31px; }
      h2 { font-size: 23px; }
      .lead { font-size: 15px; }
      .section-head { grid-template-columns: 1fr; gap: 10px; }
      .status-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .metric, .metric:nth-child(3) { border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); }
      .metric:nth-child(2n) { border-right: 0; }
      .metric:nth-last-child(-n+2) { border-bottom: 0; }
      .architecture, .capability-grid, .feature-grid, .gap-grid, .source-list { grid-template-columns: 1fr; }
      .arch-node, .arch-node:nth-child(2n), .arch-node:last-child { grid-column: auto; border-right: 0; border-bottom: 1px solid var(--line); }
      .arch-node:last-child { border-bottom: 0; }
      .next-plan { grid-template-columns: 1fr; }
      .next-plan__label { border-right: 0; border-bottom: 1px solid #685326; }
      .gallery-tools { position: relative; top: auto; grid-template-columns: 1fr 1fr; }
      .gallery-tools .control:first-child { grid-column: 1 / -1; }
      .shot-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .shot__open img { height: 160px; }
      .gallery-meta { align-items: flex-start; flex-direction: column; }
      .lightbox { width: 100vw; height: 100vh; border: 0; border-radius: 0; }
      .lightbox__stage { grid-template-columns: 36px minmax(0, 1fr) 36px; }
    }

    @media (max-width: 460px) {
      .brand strong { font-size: 13px; }
      .topnav a:nth-child(-n+3) { display: none; }
      .status-strip, .gallery-tools, .shot-grid { grid-template-columns: 1fr; }
      .metric, .metric:nth-child(2n), .metric:nth-child(3), .metric:nth-last-child(-n+2) { border-right: 0; border-bottom: 1px solid var(--line); }
      .metric:last-child { border-bottom: 0; }
      .gallery-tools .control:first-child { grid-column: auto; }
      .shot__open img { height: 210px; }
      .gallery-actions { width: 100%; }
      .gallery-actions .action { flex: 1; }
    }

    @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
  </style>
</head>
<body data-evidence-count="__EVIDENCE_COUNT__" data-capture-bundle-count="__BUNDLE_COUNT__">
  <a class="skip-link" href="#main">본문으로 이동</a>
  <header class="topbar">
    <div class="topbar__inner">
      <div class="brand"><strong>Global Terminal</strong><span>Product Evidence / __REPORT_DATE__</span></div>
      <nav class="topnav" aria-label="문서 탐색">
        <a href="#status">현황</a>
        <a href="#capabilities">기능</a>
        <a href="#scorecard">벤치마크</a>
        <a href="#roadmap">로드맵</a>
        <a href="#gallery">전체 스크린샷</a>
      </nav>
    </div>
  </header>

  <main id="main">
    <section class="section section--intro" id="status">
      <div class="section__inner">
        <p class="eyebrow">Commercial Web Product · Current State</p>
        <h1>아키텍처 중심 프로토타입을 넘어, 매일 쓸 수 있는 금융 인텔리전스 터미널로 전환 중입니다.</h1>
        <p class="lead">현재 상업용 제품의 중심은 <strong>Next.js 웹</strong>이며, <strong>FastAPI + 재사용 가능한 lib 계약층 + 선택형 Supabase</strong>가 뒷받침합니다. Streamlit은 기능 실험과 검증을 위한 내부 lab으로 남아 있고, 웹이 최종 B2C 표면입니다.</p>
        <p class="truth-line"><strong>정직한 상태:</strong> Phase 6P의 hosted 계정 연속성·A/B RLS·새 저장소 복구는 검증됐습니다. 그러나 benchmark-grade 5점은 아직 없고, 실제 배포된 반복 scheduler는 <code>hosted_scheduler_verified=false</code>입니다.</p>
        <div class="status-strip" aria-label="핵심 진행 지표">
          <div class="metric"><span>Current phase</span><strong class="good">6P 완료</strong><small>6Q 계획 확정</small></div>
          <div class="metric"><span>Benchmark</span><strong>10 × 4/5</strong><small>strong internal beta</small></div>
          <div class="metric"><span>Python gates</span><strong class="good">1,088 PASS</strong><small>full suite</small></div>
          <div class="metric"><span>Product evidence</span><strong>__EVIDENCE_COUNT__장</strong><small>__BUNDLE_COUNT__개 캡처 묶음</small></div>
          <div class="metric"><span>Hosted recovery</span><strong class="good">검증 완료</strong><small>Account A/B 격리</small></div>
          <div class="metric"><span>Hosted scheduler</span><strong class="warn">미검증</strong><small>disabled until proof</small></div>
        </div>
      </div>
    </section>

    <section class="section" id="architecture">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Product Boundary</p><h2>무엇을 만들고 있는가</h2></div>
          <p>하나의 예쁜 목업이 아니라, 출처·신선도·실패·복구·사용자 격리까지 제품 화면에서 확인 가능한 B2C 금융 연구 플랫폼을 만들고 있습니다.</p>
        </div>
        <div class="architecture" aria-label="현재 시스템 구조">
          <div class="arch-node"><b>01 · Data</b><strong>무료 우선 공급자</strong><p>SEC, Yahoo/yfinance, Alpha Vantage, Finnhub, USGS, GDELT/RSS, CoinGecko, Binance 등</p></div>
          <div class="arch-node"><b>02 · Runtime</b><strong>lib 계약·정규화</strong><p>캐시, stale/LKG, provenance, confidence, caveat와 JSON-safe domain contract</p></div>
          <div class="arch-node"><b>03 · API</b><strong>FastAPI 경계</strong><p>웹과 테스트가 같은 소스 상태·종목·지도·연구·계정 계약을 소비</p></div>
          <div class="arch-node"><b>04 · Product</b><strong>Next.js 상업용 웹</strong><p>지도, 히트맵, 차트, 옵션, 포트폴리오, 브리프, Attention과 계정 흐름</p></div>
          <div class="arch-node arch-node--hosted"><b>05 · Hosted</b><strong>Supabase 선택 계층</strong><p>A/B RLS, 계정 문서, 감사, 복구는 검증. 반복 scheduler는 다음 gate</p></div>
          <div class="arch-node arch-node--lab"><b>Internal lab</b><strong>Streamlit</strong><p>기존 아이디어·분석 로직·운영 실험을 빠르게 검증하고 웹 계약으로 승격</p></div>
        </div>
      </div>
    </section>

    <section class="section" id="capabilities">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Daily-Use Surfaces</p><h2>현재 사용 가능한 핵심 기능</h2></div>
          <p>각 표면은 단순 fixture가 아니라 live/cache/stale/offline을 구분하고, 공급자·관측 시각·caveat·data gap을 유지하도록 설계됐습니다.</p>
        </div>
        <div class="capability-grid">
          <article class="capability"><span class="capability__index">01 / GLOBAL INTELLIGENCE</span><h3>지도·사건·뉴스 융합</h3><p>WorldMonitor/worldview형 상호작용을 clean-room으로 재구성합니다.</p><ul><li>29개 source-backed 관측 마커</li><li>시간창·레이어·비교·이벤트 drilldown</li><li>뉴스·지역·자산 전이와 no-match truth</li></ul></article>
          <article class="capability"><span class="capability__index">02 / MARKET DISCOVERY</span><h3>히트맵·스크리너</h3><p>Finviz형 밀도와 발견 속도를 제품 계약에 맞게 확장했습니다.</p><ul><li>333개 공식 상장 목록 매칭 종목</li><li>11개 섹터·14개 필터</li><li>333/333 exact workstation 연결</li></ul></article>
          <article class="capability"><span class="capability__index">03 / SYMBOL RESEARCH</span><h3>심벌·애널리스트 워크스페이스</h3><p>TradingView/OpenBB형 종목 연구 흐름을 출처 진실과 결합합니다.</p><ul><li>캔들·기간·간격·기술 패널</li><li>SEC facts·재무·실적·촉매·뉴스</li><li>점진 로딩·로컬 레이아웃·exact return</li></ul></article>
          <article class="capability"><span class="capability__index">04 / QUANT & RISK</span><h3>옵션·포트폴리오</h3><p>시장 관측과 모델 가정을 섞지 않는 연구용 분석 표면입니다.</p><ul><li>옵션 chain·IV·Greeks·scenario</li><li>성과·변동성·drawdown·correlation</li><li>factor·attribution·stress replay</li></ul></article>
          <article class="capability"><span class="capability__index">05 / RESEARCH LOOP</span><h3>브리프·메모리·변화 검토</h3><p>정보를 보는 것에서 끝내지 않고 다음 검토로 이어지는 기억을 만듭니다.</p><ul><li>claim ledger·source register</li><li>snapshot diff·Change Inbox</li><li>Daily Brief·Attention Desk·Analyst return</li></ul></article>
          <article class="capability"><span class="capability__index">06 / ACCOUNT OPERATIONS</span><h3>관심 목록·관측·알림·복구</h3><p>실사용자의 반복 업무와 소유권·실패 복구를 제품 수준으로 검증합니다.</p><ul><li>Watchlist Desk와 명시적 observation run</li><li>Alert rule·trigger·worker recovery</li><li>Supabase A/B RLS·conflict·fresh-repository restore</li></ul></article>
        </div>
      </div>
    </section>

    <section class="section" id="featured">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Representative Product Views</p><h2>대표 기능 화면</h2></div>
          <p>아래는 현재 제품의 주요 사용자 여정입니다. 각 이미지를 누르면 원본 크기로 검토할 수 있고, 이 문서 하단에는 모든 상태 증거가 포함됩니다.</p>
        </div>
        <div class="feature-grid">__FEATURED_HTML__</div>
      </div>
    </section>

    <section class="section" id="scorecard">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Benchmark Scorecard</p><h2>현재 수준: 10개 범주 모두 4/5</h2></div>
          <p>4점은 강한 내부 beta입니다. 시각적 유사성만으로 5점을 부여하지 않으며, 실제 데이터·사용자 여정·실패 복구·배포 운영 증거가 모두 있어야 benchmark-grade로 인정합니다.</p>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>범주</th><th>점수</th><th>현재 증거</th><th>5점까지 남은 핵심</th></tr></thead>
            <tbody>__SCORECARD_ROWS__</tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="section" id="roadmap">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Delivery Ledger</p><h2>단계별 완료 기록</h2></div>
          <p>표의 스크린샷 수는 해당 Phase code 아래의 baseline, online, cache, stale, offline, failure, mobile, recovery 캡처를 모두 합산한 값입니다.</p>
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>단계</th><th>제품 결과</th><th>상태</th><th>캡처</th></tr></thead>
            <tbody>__PHASE_ROWS__</tbody>
          </table>
        </div>

        <div class="next-plan" style="margin-top:24px">
          <div class="next-plan__label"><span>NEXT ACTIVE PLAN</span><strong>Phase 6Q</strong><span>Hosted Scheduler Operations Pilot</span></div>
          <div class="next-plan__body">
            <p>로컬 loop나 schema-only dashboard가 아니라, 실제 배포된 일정이 한 번 실행되고 tenant-qualified 결과·quota·audit·복구 증거를 남기는 최소 운영 pilot입니다.</p>
            <ol>
              <li>Account A가 소유한 제한된 schedule CRUD와 server-derived tenant scope</li>
              <li>lease, heartbeat, at-least-once invocation, idempotent effect, 중복 방지</li>
              <li>quota ceiling, kill switch, pause/resume/retry, controlled failure와 LKG</li>
              <li>Account B 격리, cleanup, immutable audit와 redacted owner handoff</li>
              <li>모든 증거가 통과한 뒤에만 <code>hosted_scheduler_verified=true</code></li>
            </ol>
          </div>
        </div>
      </div>
    </section>

    <section class="section" id="gaps">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Honest Gaps</p><h2>아직 완성이라고 부르지 않는 이유</h2></div>
          <p>화면이 존재한다는 사실과 상업적으로 신뢰할 수 있다는 사실을 구분합니다. 다음 항목은 현재 명시적으로 열려 있습니다.</p>
        </div>
        <div class="gap-grid">
          <article class="gap-item"><b>Operations</b><h3>Hosted 반복 실행</h3><p>관측·알림의 로컬 worker와 DB 계약은 있으나 실제 배포 scheduler의 lease·quota·kill·복구 증거는 Phase 6Q에서 검증해야 합니다.</p></article>
          <article class="gap-item"><b>Market breadth</b><h3>완전한 유니버스·분류</h3><p>333개 exact workstation은 강한 기반이지만, full-universe 산업 분류·지수 편입·더 넓은 licensed data는 아직 부족합니다.</p></article>
          <article class="gap-item"><b>Map layers</b><h3>Weather·AIS·Flight·Sanctions</h3><p>검증 가능한 공급자와 좌표·신선도 계약이 없는 레이어는 live로 주장하지 않습니다. 해당 범위는 계속 unavailable 또는 proxy입니다.</p></article>
          <article class="gap-item"><b>Advanced charting</b><h3>드로잉·멀티차트·연구 저장</h3><p>차트와 분석 패널은 usable하지만 TradingView급 드로잉, 다중 레이아웃, 사용자 study 저장은 아직 없습니다.</p></article>
          <article class="gap-item"><b>Commercial stack</b><h3>Billing·entitlement·외부 전달</h3><p>계정 연속성과 RLS는 검증됐지만 결제·구독 권한, email/webhook/SMS 전달, production SRE는 제품 완성 범위가 아닙니다.</p></article>
          <article class="gap-item"><b>Safety boundary</b><h3>주문·브로커·자동 행동 없음</h3><p>결과는 연구 계산과 정보 표시입니다. 투자 조언, 거래 승인, 자동 주문, 자율 실행을 제공하거나 암시하지 않습니다.</p></article>
        </div>
      </div>
    </section>

    <section class="section" id="gallery">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Complete First-Party Evidence</p><h2>전체 기능 스크린샷 · __EVIDENCE_COUNT__장</h2></div>
          <p>외부 benchmark 원본과 과거 archive 이미지는 제외했습니다. 현재 제품이 직접 생성한 Phase 캡처만 포함하며, 원본 합계는 __TOTAL_BYTES__입니다. __PORTABILITY_NOTE__</p>
        </div>
        <div class="gallery-tools" aria-label="스크린샷 필터">
          <div class="control"><label for="shot-search">검색</label><input id="shot-search" type="search" placeholder="기능, 파일명, 상태 검색" autocomplete="off"></div>
          <div class="control"><label for="phase-filter">Phase</label><select id="phase-filter"><option value="all">전체 Phase</option></select></div>
          <div class="control"><label for="state-filter">상태</label><select id="state-filter"><option value="all">전체 상태</option><option value="live">live</option><option value="fixture">fixture</option><option value="cache">cache</option><option value="stale">stale</option><option value="offline">offline</option><option value="failure">failure</option><option value="mobile">mobile</option><option value="desktop">desktop</option><option value="conflict">conflict</option><option value="baseline">baseline</option></select></div>
          <div class="control"><label for="sort-filter">정렬</label><select id="sort-filter"><option value="newest">최신 Phase 우선</option><option value="oldest">초기 Phase 우선</option><option value="name">파일명</option></select></div>
        </div>
        <div class="gallery-meta">
          <div><strong id="gallery-count">0</strong>장의 결과 · 화면에는 <strong id="gallery-visible">0</strong>장 표시</div>
          <div class="gallery-actions"><button class="action" id="expand-all" type="button">결과 전체 표시</button><button class="action" id="reset-filters" type="button">필터 초기화</button></div>
        </div>
        <div class="shot-grid" id="shot-grid" aria-live="polite"></div>
        <div class="load-row" id="load-row"><button class="action" id="load-more" type="button">48장 더 보기</button></div>
      </div>
    </section>

    <section class="section" id="evidence">
      <div class="section__inner">
        <div class="section-head">
          <div><p class="eyebrow">Source Of Truth</p><h2>이 문서가 참조한 내부 증거</h2></div>
          <p>HTML은 아래 문서와 <code>review_workspace/phase*</code>를 읽어 재생성할 수 있습니다. 비밀키·계정 식별자·payload row는 포함하지 않습니다.</p>
        </div>
        <div class="source-list">
          <a class="source-link" href="__ROADMAP_HREF__"><b>Roadmap</b><span>현재 완료 단계와 장기 제품 방향</span></a>
          <a class="source-link" href="__SCORECARD_HREF__"><b>Benchmark</b><span>10개 범주의 4/5 근거와 blocker</span></a>
          <a class="source-link" href="__NEXT_GOAL_HREF__"><b>Next Goal</b><span>Phase 6Q hosted scheduler acceptance</span></a>
          <a class="source-link" href="__VISUAL_REGISTRY_HREF__"><b>Visual Registry</b><span>버전별 캡처·검증 명령·증거 경로</span></a>
          <a class="source-link" href="__HOSTED_RECOVERY_HREF__"><b>Hosted Recovery</b><span>A/B RLS와 fresh-repository 복구 증거</span></a>
          <a class="source-link" href="__RELEASE_REPORT_HREF__"><b>Release Gates</b><span>테스트·빌드·audit·release 결과</span></a>
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    <strong>Global Terminal Product Progress</strong><br>
    생성일 __REPORT_DATE__ · __EVIDENCE_COUNT__개 first-party product screenshot · 외부 벤치마크 이미지 제외 · 연구/정보 표시 전용
  </footer>

  <dialog class="lightbox" id="lightbox" aria-labelledby="lightbox-title">
    <div class="lightbox__bar">
      <strong id="lightbox-title">스크린샷</strong>
      <button class="icon-button" id="lightbox-close" type="button" aria-label="닫기">×</button>
    </div>
    <div class="lightbox__stage">
      <button class="icon-button" id="lightbox-prev" type="button" aria-label="이전 스크린샷">‹</button>
      <img id="lightbox-image" alt="선택한 제품 스크린샷">
      <button class="icon-button" id="lightbox-next" type="button" aria-label="다음 스크린샷">›</button>
    </div>
    <div class="lightbox__caption"><span id="lightbox-meta"></span><a id="lightbox-original" href="#" target="_blank" rel="noreferrer">이미지 열기</a></div>
  </dialog>

  <script id="screenshot-manifest" type="application/json">__MANIFEST_JSON__</script>
  <script>
    (() => {
      const screenshots = JSON.parse(document.getElementById('screenshot-manifest').textContent);
      const grid = document.getElementById('shot-grid');
      const search = document.getElementById('shot-search');
      const phaseFilter = document.getElementById('phase-filter');
      const stateFilter = document.getElementById('state-filter');
      const sortFilter = document.getElementById('sort-filter');
      const countNode = document.getElementById('gallery-count');
      const visibleNode = document.getElementById('gallery-visible');
      const loadRow = document.getElementById('load-row');
      const lightbox = document.getElementById('lightbox');
      const lightboxImage = document.getElementById('lightbox-image');
      const lightboxTitle = document.getElementById('lightbox-title');
      const lightboxMeta = document.getElementById('lightbox-meta');
      const lightboxOriginal = document.getElementById('lightbox-original');
      let limit = 48;
      let currentRows = [];
      let lightboxIndex = 0;

      const escapeHtml = (value) => String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');

      const phaseCodes = [...new Set(screenshots.map((row) => row.phase))]
        .sort((a, b) => (Number(a.match(/\d+/)?.[0] || 999) - Number(b.match(/\d+/)?.[0] || 999)) || a.localeCompare(b));
      phaseCodes.forEach((phase) => {
        const row = screenshots.find((item) => item.phase === phase);
        const option = document.createElement('option');
        option.value = phase;
        option.textContent = `${row.phase_label} · ${row.phase_title}`;
        phaseFilter.append(option);
      });

      function filteredRows() {
        const query = search.value.trim().toLowerCase();
        const phase = phaseFilter.value;
        const state = stateFilter.value;
        const rows = screenshots.filter((row) => {
          const searchable = `${row.phase_label} ${row.phase_title} ${row.bundle} ${row.name} ${row.tags.join(' ')}`.toLowerCase();
          return (phase === 'all' || row.phase === phase)
            && (state === 'all' || row.tags.includes(state))
            && (!query || searchable.includes(query));
        });
        return rows.sort((a, b) => {
          if (sortFilter.value === 'name') return a.name.localeCompare(b.name);
          const direction = sortFilter.value === 'oldest' ? 1 : -1;
          return direction * ((a.sort_key[0] - b.sort_key[0]) || (a.sort_key[1] - b.sort_key[1]) || a.bundle.localeCompare(b.bundle) || a.name.localeCompare(b.name));
        });
      }

      function render() {
        currentRows = filteredRows();
        const visibleRows = currentRows.slice(0, limit);
        countNode.textContent = currentRows.length.toLocaleString('ko-KR');
        visibleNode.textContent = visibleRows.length.toLocaleString('ko-KR');
        loadRow.hidden = visibleRows.length >= currentRows.length;
        if (!visibleRows.length) {
          grid.innerHTML = '<p class="empty">조건에 맞는 스크린샷이 없습니다. 필터를 초기화해 보세요.</p>';
          return;
        }
        grid.innerHTML = visibleRows.map((row, index) => `
          <article class="shot">
            <button class="shot__open" type="button" data-shot-index="${index}" aria-label="${escapeHtml(row.name)} 크게 보기">
              <img src="${escapeHtml(row.src)}" alt="${escapeHtml(row.phase_label)} ${escapeHtml(row.phase_title)} · ${escapeHtml(row.name)}" loading="lazy" decoding="async">
            </button>
            <div class="shot__copy">
              <div class="shot__meta"><span>${escapeHtml(row.phase_label)} · ${escapeHtml(row.phase_title)}</span><span>${Math.max(1, Math.round(row.bytes / 1024))} KB</span></div>
              <h3>${escapeHtml(row.name)}</h3>
              <p>${escapeHtml(row.bundle)} · ${escapeHtml(row.tags.join(' / '))}</p>
            </div>
          </article>`).join('');
      }

      function openLightbox(row, rows = currentRows) {
        const index = Math.max(0, rows.findIndex((item) => item.id === row.id));
        currentRows = rows;
        lightboxIndex = index;
        updateLightbox();
        if (!lightbox.open) lightbox.showModal();
      }

      function updateLightbox() {
        const row = currentRows[lightboxIndex];
        if (!row) return;
        lightboxImage.src = row.src;
        lightboxImage.alt = `${row.phase_label} ${row.phase_title} · ${row.name}`;
        lightboxTitle.textContent = row.name;
        lightboxMeta.textContent = `${row.phase_label} · ${row.phase_title} · ${lightboxIndex + 1}/${currentRows.length}`;
        lightboxOriginal.href = row.src;
      }

      grid.addEventListener('click', (event) => {
        const button = event.target.closest('[data-shot-index]');
        if (!button) return;
        openLightbox(currentRows[Number(button.dataset.shotIndex)]);
      });
      document.querySelectorAll('[data-feature-id]').forEach((button) => {
        button.addEventListener('click', () => {
          const row = screenshots.find((item) => item.id === button.dataset.featureId);
          if (row) openLightbox(row, screenshots);
        });
      });
      document.querySelectorAll('[data-feature-image]').forEach((image) => {
        const row = screenshots.find((item) => item.id === image.dataset.featureImage);
        if (row) image.src = row.src;
      });
      document.querySelectorAll('[data-phase-jump]').forEach((button) => {
        button.addEventListener('click', () => {
          phaseFilter.value = button.dataset.phaseJump;
          stateFilter.value = 'all';
          search.value = '';
          limit = 48;
          document.getElementById('gallery').scrollIntoView();
          render();
        });
      });
      [search, phaseFilter, stateFilter, sortFilter].forEach((control) => control.addEventListener('input', () => { limit = 48; render(); }));
      document.getElementById('load-more').addEventListener('click', () => { limit += 48; render(); });
      document.getElementById('expand-all').addEventListener('click', () => { limit = Number.MAX_SAFE_INTEGER; render(); });
      document.getElementById('reset-filters').addEventListener('click', () => {
        search.value = '';
        phaseFilter.value = 'all';
        stateFilter.value = 'all';
        sortFilter.value = 'newest';
        limit = 48;
        render();
      });
      document.getElementById('lightbox-close').addEventListener('click', () => lightbox.close());
      document.getElementById('lightbox-prev').addEventListener('click', () => { lightboxIndex = (lightboxIndex - 1 + currentRows.length) % currentRows.length; updateLightbox(); });
      document.getElementById('lightbox-next').addEventListener('click', () => { lightboxIndex = (lightboxIndex + 1) % currentRows.length; updateLightbox(); });
      lightbox.addEventListener('click', (event) => { if (event.target === lightbox) lightbox.close(); });
      document.addEventListener('keydown', (event) => {
        if (!lightbox.open) return;
        if (event.key === 'ArrowLeft') document.getElementById('lightbox-prev').click();
        if (event.key === 'ArrowRight') document.getElementById('lightbox-next').click();
      });
      render();
    })();
  </script>
</body>
</html>
'''


def embed_screenshots(screenshots: list[dict[str, object]]) -> list[dict[str, object]]:
    try:
        from PIL import Image
    except ImportError:
        Image = None  # type: ignore[assignment]

    def embed_one(row: dict[str, object]) -> dict[str, object]:
        source_path = ROOT / str(row["relative"])
        mime = "image/png" if source_path.suffix.lower() == ".png" else "image/jpeg"
        payload = source_path.read_bytes()
        if Image is not None:
            with Image.open(source_path) as source:
                source.load()
                if source.mode in {"RGBA", "LA"}:
                    prepared = source.convert("RGBA")
                else:
                    prepared = source.convert("RGB")
                prepared.thumbnail((1920, 3200), Image.Resampling.LANCZOS)
                buffer = io.BytesIO()
                prepared.save(buffer, format="WEBP", quality=80, method=2)
                candidate = buffer.getvalue()
                if len(candidate) < len(payload):
                    payload = candidate
                    mime = "image/webp"
        embedded_row = dict(row)
        embedded_row["src"] = f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"
        embedded_row["embedded"] = True
        return embedded_row

    workers = min(8, max(2, os.cpu_count() or 2))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(embed_one, screenshots))


def render_document(
    screenshots: list[dict[str, object]],
    *,
    bundle_count: int,
    total_bytes: int,
    portable: bool,
) -> str:
    source_documents = {
        "__ROADMAP_HREF__": "ROADMAP.md",
        "__SCORECARD_HREF__": "GOAL_MASTER_BENCHMARK_SCORECARD.md",
        "__NEXT_GOAL_HREF__": "NEXT_ROADMAP_EXECUTION_PROMPT.md",
        "__VISUAL_REGISTRY_HREF__": "VISUAL_VERSION_REGISTRY.md",
        "__HOSTED_RECOVERY_HREF__": "PHASE_6P_HOSTED_ACCOUNT_RECOVERY_EVIDENCE.md",
        "__RELEASE_REPORT_HREF__": "PHASE_6P_TEST_AND_RELEASE_REPORT.md",
    }

    def source_href(filename: str) -> str:
        if not portable:
            return filename
        payload = (ROOT / "docs" / filename).read_bytes()
        return f"data:text/markdown;charset=utf-8;base64,{base64.b64encode(payload).decode('ascii')}"

    manifest_json = json.dumps(screenshots, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    document = HTML_TEMPLATE
    replacements = {
        "__REPORT_DATE__": date.today().isoformat(),
        "__EVIDENCE_COUNT__": f"{len(screenshots):,}",
        "__BUNDLE_COUNT__": f"{bundle_count:,}",
        "__TOTAL_BYTES__": format_bytes(total_bytes),
        "__PORTABILITY_NOTE__": (
            "이 portable 문서는 모든 이미지를 내부에 넣었으므로 HTML 파일 하나만 옮겨도 그대로 열립니다."
            if portable
            else "이 경량 문서는 저장소의 원본 이미지 상대경로를 사용합니다."
        ),
        "__FEATURED_HTML__": build_featured_html(screenshots),
        "__SCORECARD_ROWS__": build_scorecard_rows(),
        "__PHASE_ROWS__": build_phase_rows(screenshots),
        "__MANIFEST_JSON__": manifest_json,
    }
    replacements.update({marker: source_href(filename) for marker, filename in source_documents.items()})
    for marker, value in replacements.items():
        document = document.replace(marker, value)
    unresolved = re.findall(r"__[A-Z0-9_]+__", document)
    if unresolved:
        raise RuntimeError(f"Unresolved template markers: {sorted(set(unresolved))}")
    return document


def build_html() -> tuple[Path, int, int]:
    screenshots = collect_screenshots()
    if not screenshots:
        raise RuntimeError("No first-party product screenshots were found.")
    bundle_count = len({str(row["bundle"]) for row in screenshots})
    total_bytes = sum(int(row["bytes"]) for row in screenshots)
    linked_document = render_document(
        screenshots,
        bundle_count=bundle_count,
        total_bytes=total_bytes,
        portable=False,
    )
    LINKED_OUTPUT_PATH.write_text(linked_document, encoding="utf-8", newline="\n")

    portable_screenshots = embed_screenshots(screenshots)
    portable_document = render_document(
        portable_screenshots,
        bundle_count=bundle_count,
        total_bytes=total_bytes,
        portable=True,
    )
    OUTPUT_PATH.write_text(portable_document, encoding="utf-8", newline="\n")
    return OUTPUT_PATH, len(screenshots), bundle_count


if __name__ == "__main__":
    output, screenshot_count, capture_bundle_count = build_html()
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output),
                "linked_output": str(LINKED_OUTPUT_PATH),
                "screenshots": screenshot_count,
                "capture_bundles": capture_bundle_count,
                "portable_single_file": True,
                "external_benchmark_images_included": False,
                "secrets_included": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
