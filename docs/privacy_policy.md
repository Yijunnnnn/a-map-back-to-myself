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

# Privacy Policy - SelfMap Agent

## 1. Information Security Goal
Since SelfMap processes highly personal journal entries and reflection history, protecting user privacy is paramount.

## 2. Privacy Policy Rules

### PII Redaction
- **Rule**: All inputs MUST be scanned for Personally Identifiable Information (PII) before being transmitted to the external Gemini API.
- **Scrubbing Scope**:
  - Full Names
  - Addresses / Locations (excluding general city if relevant)
  - Phone Numbers
  - Email Addresses
  - Social Security Numbers or other Identification numbers
- **Replacement pattern**: Redact with tokens (e.g. `[NAME_1]`, `[PHONE_1]`).

### Storage Policies
- **Rule**: All raw imported files and database caches (`derived/`) must be stored strictly within the local environment.
- **Rule**: No unencrypted remote syncing of journals without explicit configuration.
- **Rule**: Privacy redaction events must be recorded in `data/privacy_events.jsonl` for compliance testing.
