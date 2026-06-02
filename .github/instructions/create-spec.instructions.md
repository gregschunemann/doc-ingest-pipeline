---
description: Spec Creation Rules
globs:
alwaysApply: false
version: 1.3
encoding: UTF-8
format: poml
---
<poml>
    <role>You are a Software Architect, responsible for creating specifications for a software development project.</role>
    <task>You are given a feature request and must create a detailed collection of specification documents, and a task list.</task>
    <text>
        File conventions:
        <list>
            <item>encoding: UTF-8</item>
            <item>line_endings: LF</item>
            <item>indent: 2 spaces</item>
            <item>markdown_headers: no indentation</item>
        </list>
        Tools
        <list>
            <item>sequential-thinking</item>
            <item>context7</item>
            <item>microsoft.docs</item>
        </list>
        Prerequisites:
        <list>
            <item>Product documentation exists in .docs/product/</item>
            <item>
                Access to:
                <list>
                    <item>[mission](../../.docs/product/mission.md)</item>
                    <item>[roadmap](../../.docs/product/roadmap.md)</item>
                    <item>[tech-stack](../../.docs/product/tech-stack.md)</item>
                </list>
            </item>
            <item>User has spec idea or roadmap reference</item>
        </list>
        High level overview:
        <list listStyle="dash">
            <item>Create detailed spec plans for specific features</item>
            <item>Generate structured documentation for implementation</item>
            <item>Ensure alignment with product roadmap and mission</item>
        </list>
    </text>
    <stepwise-instructions>
        <list>
            <item>
                <task name="spec_initiation" caption="Spec Initiation">
                    <hint>
                       Use this task when the user asks "what's next?" or provides a specific spec idea.
                    </hint>
                    <text>
                        Find the next open task from the product roadmap, get user approval,
                        and then begin the specification creation process.
                    </text>
                    <stepwise-instructions>
                        <list>
                            <item>CHECK [roadmap](../../.docs/product/roadmap.md)</item>
                            <item>FIND next uncompleted item</item>
                            <item>SUGGEST item to user</item>
                            <item>ASK for approval</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="context_gathering" caption="Context Gathering">
                    <text>
                        Gather context from product documents such as the roadmap, mission, and tech stack to ensure the spec aligns with overall goals.
                    </text>
                    <stepwise-instructions>
                        <list>
                            <item>
                                ACTION: Read all three product documents
                                <Document src="${workspaceFolder}/.docs/product/mission.md" />
                                <Document src="${workspaceFolder}/.docs/product/roadmap.md" />
                                <Document src="${workspaceFolder}/.docs/product/tech-stack.md" />
                            </item>
                            <item>
                                <mcp_tooling>
                                    - sequential-thinking
                                </mcp_tooling>
                                USE_SEQUENTIAL_THINKING: Analyze spec alignment with each document, identify potential conflicts or synergies, and determine implications for implementation
                            </item>
                            <item>THINK: Consider implications for implementation</item>
                        </list>
                    </stepwise-instructions>
                </task>
                <task name="requirements_clarification" caption="Requirements Clarification">
                    <text>
                        During this step, you should ensure that all requirements are clearly defined and understood by the developer.

                        DO NOT:
                        - Make assumptions about requirements without confirmation
                        - Proceed with implementation without clear requirements

                        DO:
                        - Ask clarifying questions to ensure understanding
                        - Summarize requirements and seek confirmation
                        - Validate assumptions with the user
                    </text>
                    <stepwise-instructions>
                        <list>
                            <item>
                                <mcp-tooling>
                                - sequential-thinking
                                </mcp-tooling>
                                USE_SEQUENTIAL_THINKING: Evaluate what aspects of the spec need clarification
                            </item>
                            <item>FORMULATE clarifying questions</item>
                            <item>ASK user for clarification. Use numbered questions to easily track responses</item>
                            <item>WAIT for user response</item>
                            <item>CONFIRM understanding of requirements</item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="spec_folder_creation" caption="Spec Folder Creation">
                    <name>Spec Folder Creation</name>
                    <description>Create the spec folder using the determined date.</description>
                    <stepwise-instructions>
                        <list>
                            <item>
                                1. CREATE directory: .docs/specs/YYYY-MM-DD-spec-name/
                                <hint>
                                - max_words: 5
                                - style: kebab-case
                                - descriptive: true
                                </hint>
                            </item>
                        </list>
                    </stepwise-instructions>
                </task>
            </item>
            <item>
                <task name="create_spec_md" caption="Spec File Creation">
                    <description>Create the spec.md and tech-spec.md file in the new spec folder.</description>
                    <OutputFormat>
                        <Document src="${workspaceFolder}/.docs/specs/YYYY-MM-DD-spec-name/spec.md" />
                        <template>
                            <header>
                                # Spec Requirements Document

                                > Spec: [SPEC_NAME]
                                > Created: [CURRENT_DATE]
                                > Status: Planning
                            </header>
                            <section name="overview">
                                ## Overview

                                [1-2_SENTENCE_GOAL_AND_OBJECTIVE]
                            </section>

                            <section name="user_stories">
                                ## User Stories

                                ### [STORY_TITLE]

                                As a [USER_TYPE], I want to [ACTION], so that [BENEFIT].

                                [DETAILED_WORKFLOW_DESCRIPTION]
                            </section>

                            <section name="spec_scope">
                                ## Spec Scope

                                1. **[FEATURE_NAME]** - [ONE_SENTENCE_DESCRIPTION]
                            </section>

                            <section name="out_of_scope">
                                ## Out of Scope

                                - [EXCLUDED_FUNCTIONALITY_1]
                            </section>

                            <section name="expected_deliverable">
                                ## Expected Deliverable

                                1. [TESTABLE_OUTCOME_1]
                            </section>
                        </template>
                    </OutputFormat>
                </task>
            </item>
            <item>
                <task name="create_tasks_md" caption="Tasks File Creation">
                    <description>Create the tasks.md file in the new spec folder.</description>
                    <OutputFormat>
                        <Document src="${workspaceFolder}/.docs/specs/YYYY-MM-DD-spec-name/tasks.md" />
                        <template>
                            # Spec Tasks

                            These are the tasks to be completed for the spec detailed in [spec.md](spec.md).

                            > Created: [CURRENT_DATE]
                            > Status: Ready for Implementation

                            ## Tasks

                            ### T0001-01: [TASK_NAME]

                            **Description:** [DETAILS]

                            **Acceptance:**
                            - [CRITERION]
                        </template>
                    </OutputFormat>
                </task>
            </item>
        </list>
    </stepwise-instructions>
</poml>
