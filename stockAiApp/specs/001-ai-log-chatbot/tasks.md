# Tasks: AI Log Insights Chatbot

**Input**: Design documents from `/specs/001-ai-log-chatbot/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Manual quickstart validation per quickstart.md (no automated test suite required for POC).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md: `src/`, `data/`, `output/`
- [x] T002 Create `requirements.txt` with pandas, matplotlib, python-dateutil in `stockAiApp/requirements.txt`
- [x] T003 [P] Create `.gitignore` for Python artifacts and `output/` in `stockAiApp/.gitignore`
- [x] T004 [P] Create sample log dataset in `stockAiApp/data/sample_logs.csv` with Timestamp, system_name, component, log_level, corr_id, user_ID, message columns

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Implement CSV data loader with validation in `stockAiApp/src/data_loader.py`
- [x] T006 Implement QueryIntent dataclass and session state in `stockAiApp/src/session.py`
- [x] T007 Implement rule-based intent parser in `stockAiApp/src/intent_parser.py`
- [x] T008 Implement filter and aggregation query engine in `stockAiApp/src/query_engine.py`
- [x] T009 Implement conversational response builder in `stockAiApp/src/response_builder.py`
- [x] T010 Create CLI entry point with argument parsing in `stockAiApp/src/main.py`
- [x] T011 [P] Add package init in `stockAiApp/src/__init__.py`

**Checkpoint**: Foundation ready — query pipeline callable from CLI

---

## Phase 3: User Story 1 - Natural Language Log Queries (Priority: P1) 🎯 MVP

**Goal**: Analysts ask NL questions and receive filtered log results with summaries

**Independent Test**: Run scenarios 1–2 from quickstart.md

### Implementation for User Story 1

- [x] T012 [US1] Add log_level filter patterns (ERROR, WARN, INFO, etc.) in `stockAiApp/src/intent_parser.py`
- [x] T013 [US1] Add component, system_name, user_id, keyword, and date filter patterns in `stockAiApp/src/intent_parser.py`
- [x] T014 [US1] Implement row filtering and timestamp sorting in `stockAiApp/src/query_engine.py`
- [x] T015 [US1] Implement table formatting with row truncation in `stockAiApp/src/response_builder.py`
- [x] T016 [US1] Wire filter query flow in interactive loop in `stockAiApp/src/main.py`
- [x] T017 [US1] Add empty-result and unknown-intent messages per cli-contract.md in `stockAiApp/src/response_builder.py`

**Checkpoint**: User Story 1 independently functional

---

## Phase 4: User Story 2 - Aggregations and Trend Summaries (Priority: P2)

**Goal**: Analysts get counts, groupings, and health-style summaries

**Independent Test**: Run scenarios 3–4 from quickstart.md

### Implementation for User Story 2

- [x] T018 [US2] Add aggregation intent patterns (count by level/component, trend) in `stockAiApp/src/intent_parser.py`
- [x] T019 [US2] Implement group-by and time-bucket aggregations in `stockAiApp/src/query_engine.py`
- [x] T020 [US2] Implement health summary template (error rate as index health) in `stockAiApp/src/response_builder.py`
- [x] T021 [US2] Wire aggregation flow and store last aggregation in session in `stockAiApp/src/main.py`

**Checkpoint**: User Stories 1 and 2 independently functional

---

## Phase 5: User Story 3 - Visualizations and Follow-Up Context (Priority: P3)

**Goal**: Analysts request charts and refine prior results with follow-up questions

**Independent Test**: Run scenarios 5–6 from quickstart.md

### Implementation for User Story 3

- [x] T022 [P] [US3] Implement matplotlib chart generator in `stockAiApp/src/visualizer.py`
- [x] T023 [US3] Add visualize and follow-up intent patterns in `stockAiApp/src/intent_parser.py`
- [x] T024 [US3] Implement follow-up refinement on session last_result in `stockAiApp/src/query_engine.py`
- [x] T025 [US3] Wire chart and follow-up flows in `stockAiApp/src/main.py`
- [x] T026 [US3] Add help command with example queries in `stockAiApp/src/main.py`

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [x] T027 [P] Add README with setup and usage in `stockAiApp/README.md`
- [x] T028 Run all quickstart.md validation scenarios and fix any failures
- [x] T029 Mark all completed tasks as [X] in `specs/001-ai-log-chatbot/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–5)**: Depend on Foundational
- **Polish (Phase 6)**: Depends on all user stories

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on other stories
- **US2 (P2)**: After Foundational — extends parser/engine; independently testable
- **US3 (P3)**: After Foundational — uses session from US1/US2; independently testable

### Parallel Opportunities

- T003, T004 can run in parallel (Phase 1)
- T011 can run parallel with T005–T010 (Phase 2)
- T022 can start once T019 completes (Phase 5)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 + Phase 2
2. Complete Phase 3 (User Story 1)
3. Validate quickstart scenarios 1–2
4. Demo if ready

### Incremental Delivery

1. Add User Story 2 → validate scenarios 3–4
2. Add User Story 3 → validate scenarios 5–7
3. Polish and README

---

## Phase 7: Convergence

**Purpose**: Close gaps identified by `/speckit.converge` between spec intent and implementation

- [x] T030 Add system_name filter parsing for NL queries in `stockAiApp/src/intent_parser.py` per FR-003 (partial)
- [x] T031 Enhance zero-result responses with available component/user suggestions and date-range hints in `stockAiApp/src/query_engine.py` per spec edge cases (missing)
- [x] T032 Add trend direction interpretation to time-bucket aggregations in `stockAiApp/src/query_engine.py` per US2/AC2 (partial)
- [x] T033 Add user activity summary breakdown when filtering by user_ID in `stockAiApp/src/query_engine.py` per US1/AC2 (partial)
- [x] T034 Re-run quickstart.md validation scenarios after convergence fixes in `stockAiApp/`