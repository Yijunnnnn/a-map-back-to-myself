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

# Product Specification - SelfMap Agent

## 1. Overview
The SelfMap Agent is a cognitive companion designed to help users map, explore, and reflect upon their personal belief systems and cognitive patterns. Utilizing Cognitive Behavioral Therapy (CBT) theories, it analyzes journal entries and reflections to construct a dynamic, evidence-based belief network.

## 2. Core Capabilities
- **Document Importer**: Ingests unstructured journal entries (.docx, .txt) and structures them into event logs.
- **CBT Distortion Analyzer**: Identifies cognitive distortions (e.g., all-or-nothing thinking, catastrophizing) in user reflections.
- **Evidence Collector**: Associates newly imported experiences as supporting or contradicting evidence for existing beliefs.
- **Belief Graph Builder**: Constructs a personal belief graph to visualize relationships between core beliefs, intermediate assumptions, and automatic thoughts.
- **Reflection Loop**: Runs periodic reconciliation loops to highlight contradictions and promote healthy restructuring of beliefs.

## 3. Privacy & Safety Guardrails
- **Privacy Engine**: Automatically redacts PII (Personally Identifiable Information) before transferring payloads to the LLM.
- **Safety Gate**: Blocks prompts or responses indicating self-harm, severe clinical depression requiring medical attention, or other critical safety policy violations.
