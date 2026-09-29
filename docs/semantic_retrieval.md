# Local semantic retrieval (optional)

This extends the existing evidence-to-reflection flow. It does not change the Gemini reflection provider.

## Setup on the computer/server running SelfMap

Install the existing app dependencies first, then:

```sh
python -m pip install -r requirements-semantic.txt
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', trust_remote_code=False)"
```

The second command downloads model weights; no personal records are needed.
Use the same operating-system account/cache for setup and for the app.

Add to your local .env (do not commit personal settings):

```dotenv
SELFMAP_RETRIEVAL_MODE=hybrid
SELFMAP_SEMANTIC_THRESHOLD=0.55
```

Restart Streamlit. Default mode is lexical, so existing installations keep working.
Hybrid mode loads only already-cached weights, on CPU. Missing dependencies/model
or invalid settings cause a warning in server logs and lexical fallback.
Set SELFMAP_RETRIEVAL_MODE=lexical to disable.

## Behavior and limits

- Existing profile/privacy filters run before embedding.
- Hidden, disallowed and other-profile records are not embedded; sensitive records
  still require the existing explicit allow_sensitive path.
- Query and eligible card texts are encoded locally. No new hosted embedding API
  receives them. Existing Gemini processing remains separate.
- Scores must reach the configured cosine-similarity threshold; lexical overlap
  helps rank accepted candidates but cannot bypass the semantic threshold.
- 0.55 is an initial heuristic, NOT a calibrated quality guarantee.
- Similarity is topical relatedness, not truth, clinical validity or whether the
  evidence supports a claim.
- Both positive and negative relevant events remain eligible.
- No text/embedding cache is persisted. All eligible cards are encoded per query,
  suitable for a small prototype, not a large archive.
- Long cards can be truncated by the model; chunking is not implemented.
- The full Streamlit/Gemini flow and safe no-evidence response remain to validate.

## Verification

```sh
python -m unittest discover -s tests -v
```

The 16 offline tests cover lexical regressions and hybrid selection/filtering/
fallback logic. Semantic scores are stubbed in the hybrid tests: passing them
does NOT establish real-model accuracy.

After setup, run this synthetic check with the actual model:

```sh
python -c "from app.semantic_retriever import semantic_scores; print(semantic_scores('Meine Präsentation war verständlich', ['Mein Vortrag war gut nachvollziehbar.', 'Heute habe ich Blumen gegossen.']))"
```

The first score should exceed the second. Then repeat with your own synthetic
positive, negative and no-match cases in the intended languages. Inspect real
scores before choosing a threshold. Check that the app abstains without a
relevant card and cites actual sources. No private notes are necessary.

Model reference: https://www.sbert.net/docs/sentence_transformer/pretrained_models.html
API reference: https://sbert.net/docs/package_reference/sentence_transformer/model.html
