# PintsNow BETA (test build, not for users)
Built every 30 min (and on "Run workflow") from TuNeLA/Beer-map branch `big-update`. Same Supabase backend as the live app.
Not installable (no manifest), noindex, a "BETA" badge on top. Live app: https://tunela.github.io/Beer-map/docs/

## /test/ = TESTLÄGE (staging)
https://tunela.github.io/pintsnow-beta/test/ is the same big-update code pointed at the STAGING Supabase project
(`vdtmzsxajpvzwwbhnfmr`), with a "TESTLÄGE · staging" badge and the test panel (Beer-map `testenv/`). Its storage is
separate from the beta (keys `pnt<slot>:…`), so the beta account on the same phone is never touched. Fake test bots:
Actions → bots → Run workflow. The normal beta build never contains the test panel (the workflow checks it).
