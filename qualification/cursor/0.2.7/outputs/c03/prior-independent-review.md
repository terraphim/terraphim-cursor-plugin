# Independent review of native retrieval and host change

Reviewer: `review_oauth_lifetime_repair`, 16 October 2026. Read-only disk,
receipt and screenshot review; no native UI or account tools used.

Verdict: **native C-03 positive retrieval output passes review**. This is actual
retained MCP output, separately identified from model narrative and the earlier
direct stdio diagnostic. It does not qualify the remaining native scenarios or
authorize release.

## Checks performed

- The native saved file at
  `/private/tmp/terraphim-cursor-validation-20261016/public-project/outputs/native-retrieval.json`
  is byte-identical to the publication copy. Its SHA256 matches the receipt:
  `35d5ef9402b778520f411ee08505aec047800f36ade886293bf48a232a3f02b0`.
- The expanded-call screenshot shows `terraphim_retrieve` with query `Concern`
  and limit `3`, its returned JSON, and the saved `native-retrieval.json` tab.
  The capture receipt describes Copy output followed by native Save As.
- Rehashing the executable named in returned argv matches
  `95491857b6a115ce7f4ec2a9d24bd0f7b8efcc1a52bd1403b34a62dd704012ab`.
- Rehashing the actual graph matches
  `f8648b16470e764bdff5c95064078419d71e8d41d2ca30d4b1508017c166a45d`.
  It is byte-identical to the C-02 exported graph. `concern` and `risk` still
  bind to concept ID 1 and normalized term `risk`.
- Returned argv uses the expected binary, graph, owned corpus, `--search-only`,
  JSON output, limit three and literal query `Concern`. `mode` is
  `retrieval-only`, `answer` is null and three chunks are returned.
- Every returned snippet exactly matches line 1 of its actual corpus file:
  `brief.md`, `decision.md` and `review.md`. These files contain Risk passages
  and no literal Concern text.
- The earlier native literal-baseline file remains byte-identical to its saved
  copy and recorded digest, with zero chunks and null answer. It remains an
  observed earlier-host fact, not a newly executed 3.25.6 baseline.
- All 45 original main-candidate files still match their previously admitted
  byte counts and hashes; no package rebuild is necessary for this host change.
- Current installed bundle metadata reports Cursor 3.25.6. The retained
  per-command signature receipt records successful strict/deep `codesign`
  verification and Gatekeeper assessment. The resumption receipt identifies
  commit `f0df777c412b670d09e3eaf214967d779e67c080` and the retained isolated
  profile. Process inspection was sandbox-denied in this review, so its PID
  binding is attributed to the parent's resumption observation.

## Bounded rechecks after Cursor 3.24.18 → 3.25.6

Preserve the earlier successful C-01/C-02 observations and their host identity.
Do not recreate the authored synonym or overwrite those evidence files merely
to change the host label. For a final qualification covering 3.25.6:

1. Confirm the same candidate is discovered by the retained isolated host, with
   its four skills and nested setup command accessible from the admitted path.
   Existing optional MCP opt-in is intentional; the earlier inert-install
   evidence should retain its original host/version context.
2. Reopen the already saved annotated brief, confirm the original Risk and
   authored Concern, swap Concern → Risk → Concern, save, and export clean text
   and graph to fresh output paths. Compare actual disk contents and graph IDs.
   This checks the upgraded host's editor boundary without repeating prior
   authoring and unit/protocol work.
3. Continue the uncompleted synthesis, memory and hook scenarios on 3.25.6.
   Before hook tests, recheck the actual isolated hook-discovery boundary because
   account sign-in and a host update may affect inherited configuration. Keep
   normal user profiles and unrelated account plugins intact.
4. Record exact host identity per scenario in the final capability record.
   The prior literal baseline and saved source facts remain valid; no fresh
   literal grep run or full Rust suite is required solely for this host update.

The eight invalid/disabled-input and drift/restart observations remain direct
stdio evidence. C-03's positive native retrieval now has its own proof, but do
not relabel the direct negative cases as native UI execution. If final acceptance
requires those refusals through Cursor itself, retain those actual native calls
before giving the entire row an unqualified native PASS. C-04 and C-05–C-10 remain
separate gates; release remains held until their required evidence is complete.
