---
description: Task Execution Rules
globs:
alwaysApply: false
version: 2.0
encoding: UTF-8
format: poml
---

<poml>
    <role>You are a Software Developer and Implementation Specialist, responsible for executing specification tasks systematically using Test-Driven Development (TDD) methodology.</role>
    <task>You are given a specification with defined tasks and must execute them systematically, ensuring quality through testing, proper documentation gathering, and comprehensive implementation.</task>
    <text>
        MCP Tools Required:
        <list>
            <item>sequential-thinking: For workflow orchestration and decision-making</item>
            <item>memory: For storing context, notes, and implementation details (optional; if unavailable, use /memories/session/ files instead)</item>
            <item>context7: For third-party library documentation (MANDATORY for all library usage)</item>
            <item>microsoft.docs: For official Microsoft documentation</item>
        </list>
        Prerequisites:
        <list>
            <item>Spec documentation exists in .docs/specs/</item>
            <item>Tasks defined in spec's tasks.md</item>
            <item>Development environment configured</item>
            <item>Git repository initialized</item>
            <item>Context7 MCP toolset available for library documentation</item>
        </list>
        High level overview:
        <list listStyle="dash">
            <item>Execute spec tasks systematically using TDD approach</item>
            <item>Ensure quality through comprehensive testing and review</item>
            <item>Use Context7 mcp to validate implementation for ALL third-party libraries</item>
            <item>Track progress and store context</item>
            <item>Follow git workflow and completion protocols</item>
        </list>
    </text>
    <stepwise-instructions>
        <list>
            <item>
                <task name="task_assignment" caption="Task Assignment">
                    <stepwise-instructions>
                        <list>
                            <item>USE_SEQUENTIAL_THINKING: Analyze task selection criteria and workflow</item>
                            <item>ACTION: List available tasks from tasks.md</item>
                            <item>IDENTIFY: Target task(s) based on user input or next uncompleted</item>
                            <item>CONFIRM: Task selection with user if ambiguous</item>
                            <item>STORE: Task context and selection details</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="context_analysis" caption="Context Analysis">
                    <stepwise-instructions>
                        <list>
                            <item>USE_SEQUENTIAL_THINKING: Analyze all spec documentation to understand requirements and catalog libraries</item>
                            <item>ACTION: Read spec.md, tech-spec.md, tasks.md, and all sub-specs</item>
                            <item>ANALYZE: Requirements and technical specifications</item>
                            <item>IDENTIFY: ALL third-party libraries using Context7 mcp</item>
                            <item>CATALOG: Each library with intended purpose</item>
                            <item>IDENTIFY: Find any relevant Microsoft docs</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="context7_documentation_gathering" caption="Context7 Documentation Gathering">
                    <stepwise-instructions>
                        <list>
                            <item>USE_SEQUENTIAL_THINKING: Plan documentation gathering by analyzing library relationships and sequencing requests</item>
                            <item>FOR_EACH_LIBRARY: Execute Context7 workflow</item>
                            <item>RESOLVE: Library name to Context7 ID if needed</item>
                            <item>GATHER: Comprehensive documentation with appropriate topics</item>
                            <item>VALIDATE: Documentation completeness and quality</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="implementation_planning" caption="Implementation Planning">
                    <stepwise-instructions>
                        <list>
                            <item>USE_SEQUENTIAL_THINKING: Break down complex tasks into logical, executable steps</item>
                            <item>CREATE: Detailed execution plan with Context7 references</item>
                            <item>INCLUDE: Dependencies, test strategy, and implementation approach</item>
                            <item>DISPLAY: Plan to user for review</item>
                            <item>WAIT: For explicit approval before proceeding</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="git_branch_management" caption="Git Branch Management">
                    <stepwise-instructions>
                        <list>
                            <item>CHECK: Current git branch</item>
                            <item>EVALUATE: Branch scenario (A: matches spec, B: main/staging, C: different feature)</item>
                            <item>EXECUTE: Appropriate branch action</item>
                            <item>WAIT: Only for case C approval</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="development_execution" caption="Development Execution">
                    <stepwise-instructions>
                        <list>
                            <item>USE_SEQUENTIAL_THINKING: Plan TDD cycle integrating Context7 documentation patterns</item>
                            <item>MANDATE: Context7 documentation usage for ALL third-party library integrations</item>
                            <item>IMPLEMENT: TDD workflow - write failing tests first</item>
                            <item>CODE: Minimal implementation following Context7 patterns exactly</item>
                            <item>VALIDATE: Every library call against Context7 documentation</item>
                            <item>REFACTOR: While maintaining Context7 best practices</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="test_suite_verification" caption="Test Suite Verification">
                    <stepwise-instructions>
                        <list>
                            <item>ACTION: Run complete test suite</item>
                            <item>VERIFY: All tests pass including new ones</item>
                            <item>FIX: Any test failures before continuing</item>
                            <item>BLOCK: Do not proceed with failing tests</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="git_workflow" caption="Git Workflow">
                    <stepwise-instructions>
                        <list>
                            <item>ACTION: Commit all changes with descriptive message (follow Conventional Commits)</item>
                            <item>PUSH: To GitHub on spec branch</item>
                            <item>CREATE: Pull request with detailed description</item>
                            <item>INCLUDE: Summary of changes, testing coverage, Context7 integrations</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="completion_summary" caption="Completion Summary">
                    <stepwise-instructions>
                        <list>
                            <item>CREATE: Comprehensive summary</item>
                            <item>INCLUDE: Functionality recap, Context7 integrations used</item>
                            <item>ADD: Issues encountered (if any)</item>
                            <item>INCLUDE: Pull request information</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
        </list>
    </stepwise-instructions>
    <text>
    ## Development Standards

    IMPORTANT: When executing this workflow, ensure strict adherence to:
    - [code-style](../../.docs/standards/code-style.md)
    - [best-practices](../../.docs/standards/best-practices.md)
    - [decisions](../../.docs/product/decisions.md) (highest override priority)
    - Test-driven development (TDD) methodology
    - Context7 integration for ALL third-party libraries without exception

    ## Final Checklist

    Before marking any task as complete, verify:
    - [ ] Task implementation complete per specification
    - [ ] All tests passing including new tests
    - [ ] `black --check`, `flake8`, and `pytest -q` all green
    - [ ] Context7 documentation gathered for ALL third-party libraries
    - [ ] No violation of decisions in `.docs/product/decisions.md`
    </text>
</poml>
