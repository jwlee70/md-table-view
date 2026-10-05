# md-table-view

Markdown 파일을 **표가 읽기 편한 HTML**로 변환해 주는 작은 파이썬 스크립트입니다.
넓은 표(열 10개 · 행 수십 개)가 든 `.md`를 편집기나 일반 뷰어로 보면 열이 찌그러져 읽기 어렵습니다. 이 도구는 그 파일을 브라우저에서 엑셀처럼 볼 수 있게 만듭니다.

*A single-file Python script that bakes Markdown into standalone HTML pages with sortable, resizable, filterable tables. English summary below.*

## 표에 붙는 기능

| 기능 | 사용법 |
|---|---|
| 열 정렬 | 머리글 클릭 — 오름 → 내림 → 원래 순서 |
| 열 너비 조정 | 머리글 오른쪽 경계를 드래그. 경계 더블클릭 = 초기화. 너비는 브라우저가 기억합니다 |
| 머리 행 · 첫 열 고정 | 스크롤해도 머리글과 첫 열이 따라옵니다 |
| 표 안에서 찾기 | 15행 이상인 표 위에 입력칸이 생깁니다 |
| 밝은 · 어두운 화면 | 브라우저/OS 설정을 따릅니다(`--theme`으로 고정 가능) |

## 설치

파이썬 3.8 이상과 `markdown-it-py` 하나가 필요합니다.

```bash
pip install markdown-it-py
```

`mdtableview.py` 파일 하나만 받아서 써도 됩니다.

## 사용

```bash
python mdtableview.py notes.md
```

`notes.md` 옆의 `_html/notes.html`로 변환됩니다.

```bash
python mdtableview.py docs/ -o site/ --open
```

폴더를 주면 그 안의 `.md`를 전부(하위 폴더 포함) 같은 폴더 구조로 변환하고, 목록 페이지 `index.html`을 만들어 브라우저로 엽니다.

| 옵션 | 뜻 |
|---|---|
| `-o`, `--out` | 출력 폴더 (기본 = 입력 폴더 안의 `_html`) |
| `--theme auto\|dark\|light` | 화면 색 (기본 `auto`) |
| `--index-title` | 목록 페이지 제목 |
| `--open` | 변환이 끝나면 시작 페이지를 브라우저로 엽니다 |

예제: `python mdtableview.py examples --open`

## 동작 방식

- **원본은 `.md` 하나입니다.** HTML은 다시 만들 수 있는 보기용 사본이라, `.md`를 고친 뒤 다시 변환하면 됩니다. 같은 입력이면 같은 출력이 나옵니다(실행 시각을 쓰지 않습니다).
- 함께 변환되는 `.md`끼리의 링크는 `.html`로 바뀝니다. 그 밖의 상대 링크와 이미지는 원본 위치를 가리키도록 다시 계산됩니다.
- 맨 위의 YAML 프런트매터(`---` 블록)는 빼고 변환합니다.
- `.`으로 시작하는 폴더, `node_modules`, `_html`은 훑지 않습니다.
- 페이지 하나가 CSS·JS를 모두 품고 있어 외부 파일이나 인터넷 연결이 필요 없습니다.

## 정렬 기준

칸의 글자에서 정렬 키를 뽑습니다.

1. 날짜 — `2026-10-02`, `10-02`
2. 맨 앞 숫자 — `#1`, `+164.4`, `−4.4%`, `$14.3B`, `1,234`
3. 첫 번째 부호 달린 퍼센트 — `Q3 +20.7% / +2.3%` → 20.7

채워진 칸의 80% 이상에서 숫자가 뽑히면 숫자 열로, 아니면 글자순으로 정렬합니다. 빈 칸과 숫자 열 안의 숫자 없는 칸은 방향과 상관없이 맨 아래로 갑니다.

**한계**
- 연도 없는 `MM-DD`는 해를 넘기는 순서를 모릅니다(12월 뒤의 1월이 앞에 옵니다).
- `B 71`처럼 글자로 시작하는 칸은 글자순입니다.
- 병합된 칸(HTML `rowspan`/`colspan`)이 있는 표는 정렬 결과가 어긋날 수 있습니다.

## 테스트

```bash
python -m unittest discover tests
```

## English summary

```bash
pip install markdown-it-py
python mdtableview.py docs/ -o site/ --open
```

Every `.md` under the input is baked into a self-contained HTML page (no external assets). Tables get a sticky header and first column, click-to-sort headers (asc → desc → original), drag-to-resize columns (remembered in `localStorage`, double-click the edge to reset), and a filter box when a table has 15+ rows. Links between baked pages are rewritten to `.html`; other relative links and images are re-based onto the source location. Output is deterministic.

## License

MIT
