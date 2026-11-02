# Analytics configuration and public notice contract

Plausible is optional. An empty `params.plausible.domain` and `src` disables it.
Enabling it requires an explicit domain identifier and HTTPS script URL. The
shared head has no service-provider fallback and fails a build when only one
field is set. Existing active Boulingua sites use the explicitly configured
`https://analytics.hellebo.de/js/script.file-downloads.outbound-links.js` endpoint.
Changing that endpoint is a deliberate configuration and notice change.

Every privacy page declares three small front-matter fields:

```yaml
analytics_policy: disabled # or plausible
analytics_notice_language: de # en and fr are also supported
analytics_notice_path: /datenschutz/ # relative to the site's built root
```

The public text must state the actual state. Active notices additionally name
the exact configured script URL and domain identifier. Inactive notices must
not retain copied claims that Plausible measurement is active. Multilingual
notices each declare their own URL and language. These fields are assertions
checked against rendered text, not a replacement for that text.

Run C9 after building the site:

```sh
python3 scripts/verify_analytics.py /path/to/course --built /path/to/course/public
```

The check scans all HTML pages for missing, duplicate, unexpected or mismatched
Plausible scripts and reads the actual rendered privacy statements. Redirect-only
alias pages are exempt from a required script. Unit tests cover both states,
bad/missing/duplicate script tags, missing visible statements/endpoints,
contradictory old text and a reintroduced implicit service fallback.

This contract verifies declared configuration and generated HTML. It cannot
prove the analytics server's retention settings, permissions, jurisdiction,
runtime event delivery or legal compliance. Those remain operational and
operator review matters. Public notices should not infer them from a script
URL or repeat broad vendor assurances as verified properties of this instance.
The [Plausible data policy](https://plausible.io/data-policy) and
[measurement documentation](https://plausible.io/docs/script-extensions)
describe the software, not the verified operation of a particular self-hosted
deployment. Browser regression tests block analytics requests rather than
sending test pageviews.
