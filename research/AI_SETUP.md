# Zero-additional-subscription AI commentary: Cloudflare Workers AI

The intelligence engine runs without any AI account, and will still publish rule-based commentary if the optional AI request fails. Cloudflare Workers AI currently includes an allocation of 10,000 Neurons/day on Free accounts. No paid plan is required for usage within this allowance, but inspect your dashboard usage before enabling extensive calls.

## Secure one-time setup
1. Cloudflare dashboard → **Workers AI** → **Use REST API** (https://dash.cloudflare.com/).
2. Create a Workers AI API token with the official template and copy your **Account ID**. Never place the token in chat, frontend code or a Git commit.
3. GitHub repository → Settings → Secrets and variables → Actions → **New repository secret**:
   - `CLOUDFLARE_AI_TOKEN`: your token
   - `CLOUDFLARE_ACCOUNT_ID`: your Cloudflare account ID
4. Run GitHub Actions **Daily macro update** on branch `market-intelligence-foundation`.
5. Inspect `public/market_intelligence.json`, `editorialCommentary.mode`:
   - `AI_CURATED` — Cloudflare model selected 1–3 permitted evidence IDs;
   - `RULE_BASED` — fallback used because credentials are absent, model returned invalid JSON, or request failed;
   - `UNAVAILABLE` — data insufficient or stale.

The model is `@cf/meta/llama-3.1-8b-instruct` via Cloudflare's REST API. It only selects IDs of already-generated statements and cannot author published statistics or causal claims. The actual sentences shown in the website come from deterministic, auditable inputs.

References: https://developers.cloudflare.com/workers-ai/get-started/rest-api/ and https://developers.cloudflare.com/workers-ai/platform/pricing/

**Keep Pull Request #4 in draft.** No Cloudflare secret is needed in Pages, and the client-side site never receives credentials. The free daily usage allowance is subject to Cloudflare limits and may change.
