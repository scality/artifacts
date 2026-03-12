"""Shared constants for the artifacts end-to-end test suite."""

BUCKETS = ('artifacts-staging', 'artifacts-promoted', 'artifacts-prolonged')

# Build name examples that exercise each routing bucket.
STAGING_BUILD   = 'githost:owner:repo:staging-8e50acc6a1.pre-merge.28.1'
PROMOTED_BUILD  = 'githost:owner:repo:promoted-8e50acc6a1.rel.1'
PROLONGED_BUILD = 'githost:owner:repo:1.0.28.1'
