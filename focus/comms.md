# Focus lens: comms (voice, SMS and dialers)

Use this lens when the work places or receives calls or texts: click-to-call, power dialers,
inbound routing and screen pop, SMS, call recording, AI call notes, call tracking. It separates
the phone system (UCaaS: seats, desk and mobile apps, IVR) from the programmable layer (CPaaS:
per-minute APIs), because most "which vendor" answers turn on that split. Pair it with `legal`:
dialing is regulated.

Added 2026-10-01 after the first live v3 run (a RingCentral dialer for a custom CRM): no lens
fired on that topic, and every telephony vendor's docs scored as an unknown source.

## Triggers

Suggested when the topic mentions dialers, dialing, telephony, VoIP, phone systems, softphones,
WebRTC, SMS or text messaging, IVR, call centers, call recording, tracking, routing or queues,
cold calling, click-to-call, voicemail, caller ID, 10DLC, CPaaS or UCaaS, or names RingCentral,
Twilio, Aircall, Dialpad or Telnyx.

## Sub-question lens

1. **Mode coverage:** which product and API delivers each calling mode needed (click-to-call,
   power or parallel dialing, inbound with screen pop, SMS, recording, AI notes), and which modes
   need building ourselves?
2. **Event reliability:** how do call and message events reach our system (webhook validation,
   expiry and renewal, retry or blacklist behaviour, rate limits), and what reconciles missed
   events?
3. **Compliance plumbing:** what the carrier and regulator side requires before the first call
   or text (10DLC registration, STIR/SHAKEN attestation, caller-name and spam-label
   registration, recording disclosure).

## Tool stack

| Tool          | Tier       | Use it for                                                                  | Skip when                         |
| ------------- | ---------- | --------------------------------------------------------------------------- | --------------------------------- |
| `ringcentral` | paid (API) | UCaaS plus API: RingOut, WebPhone 2.x, Embeddable, telephony-session webhooks, SMS, ACE AI | the team wants no phone system |
| `twilio`      | paid (API) | Programmable voice and SMS, AMD, number pools, per-minute AI                | the team needs desk phones and IVR out of the box |
| `telnyx`      | paid (API) | Cheapest per-minute CPaaS, WebRTC SDK                                       | ecosystem breadth matters more than cost |
| `aircall`     | paid (API) | Packaged power dialer, voicemail drop, AI notes                             | a fully custom UI is required     |
| `dialpad`     | paid (API) | UCaaS with AI recaps                                                        | a power dialer is required (verify tier) |
| `callrail`    | paid (API) | Call tracking numbers (DNI), session attribution, pre and post-call webhooks | no marketing attribution in scope |
| `fcc-telecom` | free       | TCPA, consent revocation, calling hours, STIR/SHAKEN, CTIA messaging rules  | never for an outbound program     |

**Free-only path:** every vendor here publishes its developer docs and pricing pages openly.
Read them with web search and page fetch (`[FC:developers.ringcentral.com]`), plus the eCFR and
FCC texts. Tag vendor-doc findings with the vendor's tag (`[RC]`, `[TW]`) when the docs are the
source, even on a free run.

## Authorities

Each vendor's own developer docs, release notes and pricing pages are primary for that vendor
(developers.ringcentral.com, twilio.com/docs, developers.telnyx.com, developer.aircall.io,
apidocs.callrail.com). The vendor's community forum counts when vendor staff answer. The eCFR, the FCC
and CTIA are primary for rules. Comparison blogs written by a vendor about its rivals count as
one source each and are labelled as vendor-authored.

## Freshness

- Cache TTL: 30 days for APIs and SDK versions, 7 days for pricing, 7 days for FCC rules during
  an open rule-making window.
- Dated traps:
  - RingCentral closed its free sandbox on 2025-01-01, and its old AI API is deprecated in favour
    of the ACE API (beta).
  - Unregistered A2P SMS has been blocked by carriers since 2025-02-03.
  - The FCC rewrote the "revoke-all" opt-out rule on 2026-09-30.
  - WebPhone 1.x to 2.x was a full rewrite (2024-11-21). Read the docs for the version you will
    install.

## Audit mode

With `--target <repo>`, check the following:
- Find telephony SDKs and webhook routes.
- Check that the Content-Security-Policy `connect-src` and the `Permissions-Policy` header allow
  the microphone and the vendor's WebRTC endpoints.
- Check that webhook handlers acknowledge fast (under 3 s) and deduplicate.
- Check that consent, opt-out and do-not-call data exist for phone numbers, not just email.

Tag results `[AUDIT:comms]`. Never place a call or send a message during an audit.

## Report addendum

Add a **Telephony and messaging plan** section:

```text
### Telephony and messaging plan
| Mode             | Vendor capability (date)              | Build or buy | Event path and reconcile        | Compliance prerequisite   | Source       |
| ---------------- | ------------------------------------- | ------------ | ------------------------------- | ------------------------- | ------------ |
| Power dialer     | not native on RingEX; RingCX $65+     | build        | session webhook -> queue; nightly call-log sync | per-state pre-dial rules | [RC + FCC] |
```

## Pathway mapping

- pathway-operating-layer: `data`, `security`, plus the `privacy-evidence` overlay (recordings,
  transcripts, consent).
- development-protocol rows: `research`, `spec` (each mode becomes an acceptance criterion),
  `premortem` (lost webhooks, blacklisting, carrier blocking).
