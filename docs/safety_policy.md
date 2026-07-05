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

# Safety Policy - SelfMap Agent

## 1. Safety Intent
SelfMap is a reflection aid, NOT a clinical therapy application or medical device. It is critical that the agent operates safely when users share thoughts related to acute distress, mental illness, or self-harm.

## 2. Policy Constraints

### Medical Advice & Diagnosis
- **Rule**: The agent MUST NOT diagnose any medical or psychiatric condition.
- **Rule**: The agent MUST NOT prescribe treatment, therapy plans, or medication.
- **Rule**: The agent MUST suggest consulting a professional when clinical themes arise.

### Self-Harm & Crisis Intervention
- **Rule**: If any input or processed thought suggests self-harm, suicide, or violence:
  1. Immediately trigger the crisis mitigation protocol.
  2. Override regular response with a standard supportive message and helpline resources (e.g., 988 Suicide & Crisis Lifeline).
  3. Log the incident in `data/safety_events.jsonl` (omitting full PII).
  4. Terminate the processing chain immediately without sending the query to any external standard LLM APIs if pre-intercepted.
