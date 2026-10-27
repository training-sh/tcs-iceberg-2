# Execution results

The complete OpenShift notebook passed on both representative installations using the real, checksummed MovieLens small dataset. All code cells executed in Jupyter against the standalone Spark worker.

| Check | Result |
|---|---|
| Bronze CSV preparation and S3A read | Passed: 9,742 movies, 100,836 ratings |
| Silver movie/rating Iceberg writes and readback | Passed |
| Gold filtering and join | Passed: 48 movies |
| Independent source-CSV comparison | Passed: exact movie IDs, counts and average ratings |
| Iceberg snapshots and physical S3 paths | Passed |
| Reuse existing identical bronze without overwrite | Passed on both installations |
| SeaweedFS admin form login and session | Passed |
| Admin static asset and navigation | Passed |
| Master UI and filer bucket pages | Passed |
| Download an actual bronze CSV through the filer | Passed: HTTP 200 with the expected CSV header |

Browser-facing checks used HTTP requests with the login form's CSRF token and session cookies. They verified page responses, a static asset, bucket listing and a real CSV download; visual browser rendering was not automated.

Missing localhost forwards were opened with the forwarding helper; existing working forwards were preserved. These processes need restarting after a reboot or forwarding failure. No image, manifest, Secret, PVC or installed system service was changed for this exercise.

The notebook downloads the real dataset rather than generating synthetic records. The original Docker paths/catalog were replaced with the existing warehouse bucket and Polaris catalog. Existing bronze is verified before reuse; each run's silver/gold namespaces are isolated. Source notebooks contain no fabricated execution outputs.

The existing-data mode is configurable, but arbitrary external datasets and schemas were not certified. The exact downloaded archive, expected input counts and SHA-256 are documented in README.md. Executed notebooks and detailed logs are retained separately from the clean course sources.
