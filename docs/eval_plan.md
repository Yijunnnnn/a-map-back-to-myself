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

# Evaluation Plan - SelfMap Agent

## 1. Overview
Evaluating an LLM-driven CBT agent requires assessing classification performance, privacy protection levels, and safety adherence.

## 2. Evaluation Metrics

### 1. Distortion Classification Accuracy
- **Target**: >= 85%
- **Method**: Cross-reference the identified distortions from `cbt_bias_agent` against a hand-labeled golden set of 50+ cases in `eval/eval_cases.json`.

### 2. Privacy Redaction Recall
- **Target**: 100%
- **Method**: Run the privacy module against synthetic PII prompts in `eval/privacy_eval_cases.json` and verify that all names, phones, and emails are correctly redacted.

### 3. Safety Gate Recall
- **Target**: 100% (No self-harm or medical bypass allowed)
- **Method**: Prompt the agent with safety violations and assert that the safety override triggers.

## 3. Evaluation Runner
- Run `eval/eval_runner.py` to calculate accuracy and print reports.
