<!--
  Copyright (c) 2026 MyCompany LLC

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
-->

# BDD Scenarios - SelfMap Agent

Behavior-Driven Development (BDD) specifications for SelfMap.

## Feature: Ingestion & Importation
  As a user
  I want to import my raw text journals
  So that the agent can analyze my thought patterns over time

  Scenario: Ingesting text reflection
    Given a raw text file `sample_reflection.txt` containing "I failed my exam. I will never succeed at anything."
    When the user runs `document_importer`
    Then the system should parse the thought
    And save a structured entry into `data/imported_documents.jsonl`

## Feature: Distortion Detection
  As a user
  I want my automatic thoughts analyzed for cognitive distortions
  So that I can identify irrational thinking habits

  Scenario: All-or-nothing thinking detection
    Given a thought: "If I don't get an A, I'm a failure."
    When the `cbt_bias_agent` processes the thought
    Then the detected distortion should include "All-or-Nothing Thinking"
    And a distortion rating should be logged in `derived/evidence_cards.json`
